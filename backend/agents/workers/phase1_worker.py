"""
Phase 1 Worker - Discovery & Analysis Agents
Handles: Requirements Analysis, Research, Tech Stack Decision
"""
import os
from celery import Celery
import structlog

logger = structlog.get_logger()

# Initialize Celery
celery_app = Celery(
    'phase1_worker',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis-service:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis-service:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Import Phase 1 agents
from agents.phase1_discovery.requirements_analyst_agent import RequirementsAnalystAgent
from agents.phase1_discovery.requirements_analyst_interactive import InteractiveRequirementsAnalystAgent
from agents.phase1_discovery.research_agent import ResearchAgent
from agents.phase1_discovery.tech_stack_decision_agent import TechStackDecisionAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient


@celery_app.task(name='phase1.requirements_analysis', bind=True)
def requirements_analysis_task(self, task_data: dict) -> dict:
    """Process requirements analysis"""
    try:
        logger.info("Phase1: Requirements analysis started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = RequirementsAnalystAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase1: Requirements analysis completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase1: Requirements analysis failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase1.interactive_requirements', bind=True)
def interactive_requirements_task(self, task_data: dict) -> dict:
    """Process interactive requirements with clarifications"""
    try:
        logger.info("Phase1: Interactive requirements started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = InteractiveRequirementsAnalystAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.analyze_and_generate_questions(task_data))
        
        logger.info("Phase1: Interactive requirements completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase1: Interactive requirements failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase1.research', bind=True)
def research_task(self, task_data: dict) -> dict:
    """Process research task"""
    try:
        logger.info("Phase1: Research started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = ResearchAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase1: Research completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase1: Research failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase1.tech_stack_decision', bind=True)
def tech_stack_decision_task(self, task_data: dict) -> dict:
    """Process tech stack decision"""
    try:
        logger.info("Phase1: Tech stack decision started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = TechStackDecisionAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase1: Tech stack decision completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase1: Tech stack decision failed", error=str(e), task_id=self.request.id)
        raise


# Task routing
celery_app.conf.task_routes = {
    'phase1.*': {'queue': 'phase1_queue'},
}


if __name__ == '__main__':
    celery_app.start()

