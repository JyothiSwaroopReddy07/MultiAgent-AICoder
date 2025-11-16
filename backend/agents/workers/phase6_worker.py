"""
Phase 6 Worker - Monitoring Agents
Handles: Monitor
"""
import os
from celery import Celery
import structlog

logger = structlog.get_logger()

celery_app = Celery(
    'phase6_worker',
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

from agents.phase6_monitoring.monitor_agent import MonitorAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient


@celery_app.task(name='phase6.monitoring', bind=True)
def monitoring_task(self, task_data: dict) -> dict:
    """Process agent monitoring"""
    try:
        logger.info("Phase6: Monitoring started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = MonitorAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase6: Monitoring completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase6: Monitoring failed", error=str(e), task_id=self.request.id)
        raise


celery_app.conf.task_routes = {
    'phase6.*': {'queue': 'phase6_queue'},
}


if __name__ == '__main__':
    celery_app.start()

