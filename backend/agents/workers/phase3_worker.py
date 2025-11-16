"""
Phase 3 Worker - Implementation Agents
Handles: Code Generator, Test Generator
"""
import os
from celery import Celery
import structlog

logger = structlog.get_logger()

celery_app = Celery(
    'phase3_worker',
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

from agents.coder_agent import CoderAgent
from agents.tester_agent import TesterAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient


@celery_app.task(name='phase3.code_generation', bind=True)
def code_generation_task(self, task_data: dict) -> dict:
    """Process code generation"""
    try:
        logger.info("Phase3: Code generation started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = CoderAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase3: Code generation completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase3: Code generation failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase3.test_generation', bind=True)
def test_generation_task(self, task_data: dict) -> dict:
    """Process test generation"""
    try:
        logger.info("Phase3: Test generation started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = TesterAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase3: Test generation completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase3: Test generation failed", error=str(e), task_id=self.request.id)
        raise


celery_app.conf.task_routes = {
    'phase3.*': {'queue': 'phase3_queue'},
}


if __name__ == '__main__':
    celery_app.start()

