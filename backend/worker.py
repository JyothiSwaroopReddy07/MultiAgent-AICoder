"""
Celery Worker for distributed agent processing
Allows scaling of agent tasks across multiple worker instances
"""
import os
from celery import Celery
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

# Initialize Celery
celery_app = Celery(
    'ai_coder_workers',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    broker_connection_retry_on_startup=True,
)

# Import agents when worker starts
from agents.phase1_discovery.requirements_analyst_agent import RequirementsAnalystAgent
from agents.phase1_discovery.research_agent import ResearchAgent
from agents.phase2_design.architect_agent import ArchitectAgent
from agents.phase2_design.module_designer_agent import ModuleDesignerAgent
from agents.coder_agent import CoderAgent
from agents.tester_agent import TesterAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient


@celery_app.task(name='ai_coder_workers.process_agent_task', bind=True)
def process_agent_task(self, agent_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a task for a specific agent type
    
    Args:
        agent_type: Type of agent to use (requirements, research, architect, etc.)
        task_data: Data for the agent to process
        
    Returns:
        Agent processing result
    """
    try:
        logger.info(f"Worker processing {agent_type} task", task_id=self.request.id)
        
        # Initialize MCP server and OpenAI client
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        
        # Map agent type to agent class
        agent_map = {
            'requirements': RequirementsAnalystAgent,
            'research': ResearchAgent,
            'architect': ArchitectAgent,
            'module_designer': ModuleDesignerAgent,
            'coder': CoderAgent,
            'tester': TesterAgent,
        }
        
        if agent_type not in agent_map:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Instantiate and run agent
        agent_class = agent_map[agent_type]
        agent = agent_class(mcp_server, openai_client)
        
        # Process task asynchronously
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info(f"Worker completed {agent_type} task", task_id=self.request.id)
        return result
        
    except Exception as e:
        logger.error(f"Worker failed {agent_type} task", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='ai_coder_workers.health_check')
def health_check() -> Dict[str, str]:
    """Health check task for worker monitoring"""
    return {"status": "healthy", "worker": "ai_coder_worker"}


# Task routing for different queues
celery_app.conf.task_routes = {
    'ai_coder_workers.process_agent_task': {'queue': 'agent_tasks'},
    'ai_coder_workers.health_check': {'queue': 'health'},
}

# Worker event handlers
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks (e.g., health checks, cleanup)"""
    # Run health check every 60 seconds
    sender.add_periodic_task(60.0, health_check.s(), name='worker-health-check')


if __name__ == '__main__':
    celery_app.start()

