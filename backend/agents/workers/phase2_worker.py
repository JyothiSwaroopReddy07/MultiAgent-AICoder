"""
Phase 2 Worker - Design & Planning Agents
Handles: Architect, Module Designer, Component Designer, UI Designer
"""
import os
from celery import Celery
import structlog

logger = structlog.get_logger()

celery_app = Celery(
    'phase2_worker',
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

from agents.phase2_design.architect_agent import ArchitectAgent
from agents.phase2_design.module_designer_agent import ModuleDesignerAgent
from agents.phase2_design.component_designer_agent import ComponentDesignerAgent
from agents.phase2_design.ui_designer_agent import UIDesignerAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient


@celery_app.task(name='phase2.architecture_design', bind=True)
def architecture_design_task(self, task_data: dict) -> dict:
    """Process architecture design (HLD)"""
    try:
        logger.info("Phase2: Architecture design started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = ArchitectAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase2: Architecture design completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase2: Architecture design failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase2.module_design', bind=True)
def module_design_task(self, task_data: dict) -> dict:
    """Process module design"""
    try:
        logger.info("Phase2: Module design started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = ModuleDesignerAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase2: Module design completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase2: Module design failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase2.component_design', bind=True)
def component_design_task(self, task_data: dict) -> dict:
    """Process component design (LLD)"""
    try:
        logger.info("Phase2: Component design started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = ComponentDesignerAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase2: Component design completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase2: Component design failed", error=str(e), task_id=self.request.id)
        raise


@celery_app.task(name='phase2.ui_design', bind=True)
def ui_design_task(self, task_data: dict) -> dict:
    """Process UI/UX design"""
    try:
        logger.info("Phase2: UI design started", task_id=self.request.id)
        
        mcp_server = MCPServer()
        openai_client = OpenAIClient()
        agent = UIDesignerAgent(mcp_server, openai_client)
        
        import asyncio
        result = asyncio.run(agent.process_task(task_data))
        
        logger.info("Phase2: UI design completed", task_id=self.request.id)
        return result
    except Exception as e:
        logger.error("Phase2: UI design failed", error=str(e), task_id=self.request.id)
        raise


celery_app.conf.task_routes = {
    'phase2.*': {'queue': 'phase2_queue'},
}


if __name__ == '__main__':
    celery_app.start()

