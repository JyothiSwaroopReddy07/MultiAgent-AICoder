"""
Phase 4 Worker - Quality Assurance Agents
Handles: Security Auditor, Debugger, Code Reviewer
"""
import os
from celery import Celery
import structlog

logger = structlog.get_logger()

celery_app = Celery(
    'phase4_worker',
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

from agents.phase4_qa.security_auditor_agent import SecurityAuditorAgent
from agents.phase4_qa.debugger_agent import DebuggerAgent
from agents.reviewer_agent import ReviewerAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient


@celery_app.task(name='phase4.security_audit', bind=True)
def security_audit_task(self, task_data: dict) -> dict:
    """Process security audit"""
    try:
        logger.info("Phase4: Security audit started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = SecurityAuditorAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase4: Security audit completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase4: Security audit failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase4.debugging', bind=True)
def debugging_task(self, task_data: dict) -> dict:
    """Process debugging analysis"""
    try:
        logger.info("Phase4: Debugging started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = DebuggerAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase4: Debugging completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase4: Debugging failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase4.code_review', bind=True)
def code_review_task(self, task_data: dict) -> dict:
    """Process code review"""
    try:
        logger.info("Phase4: Code review started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = ReviewerAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase4: Code review completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase4: Code review failed", error=str(e), task_id=self.request.id)
        raise


celery_app.conf.task_routes = {
    'phase4.*': {'queue': 'phase4_queue'},
}


if __name__ == '__main__':
    celery_app.start()

