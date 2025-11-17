"""
Base Agent class - Foundation for all specialized agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import structlog
from models.schemas import AgentRole, AgentMessage, MessageType, AgentActivity
from utils.openai_client import OpenAIClient
from datetime import datetime, timezone

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-agent system
    Each agent has specific capabilities and communicates via MCP
    """

    def __init__(
        self,
        role: AgentRole,
        mcp_server: 'MCPServer',
        openai_client: OpenAIClient
    ):
        self.role = role
        self.mcp = mcp_server
        self.openai = openai_client
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.current_activity: Optional[AgentActivity] = None

        # Register with MCP server
        self.mcp.register_agent(self.role, self)

        logger.info("agent_initialized", role=role.value)

    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main task processing method - must be implemented by each agent

        Args:
            task_data: Data needed to perform the task

        Returns:
            Result of the task processing
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent

        Returns:
            System prompt string
        """
        pass

    async def receive_message(self, message: AgentMessage):
        """Receive and queue a message from MCP"""
        await self.message_queue.put(message)
        logger.debug(
            "message_received",
            agent=self.role.value,
                from_=message.sender.value,
            message_id=message.id
        )

    async def send_message(
        self,
        content: Dict[str, Any],
        recipient: Optional[AgentRole] = None,
        message_type: MessageType = MessageType.RESPONSE,
        parent_id: Optional[str] = None
    ) -> AgentMessage:
        """Send a message via MCP"""
        return await self.mcp.send_message(
            sender=self.role,
            content=content,
            recipient=recipient,
            message_type=message_type,
            parent_id=parent_id
        )

    async def start_activity(self, action: str) -> AgentActivity:
        """Start tracking a new activity"""
        self.current_activity = AgentActivity(
            agent=self.role,
            action=action,
            status="in_progress",
            start_time=datetime.now(timezone.utc)
        )

        logger.info(
            "activity_started",
            agent=self.role.value,
            action=action
        )

        return self.current_activity

    async def complete_activity(self, status: str = "completed"):
        """Complete the current activity"""
        if self.current_activity:
            self.current_activity.status = status
            self.current_activity.end_time = datetime.now(timezone.utc)

            logger.info(
                "activity_completed",
                agent=self.role.value,
                action=self.current_activity.action,
                status=status
            )

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Call LLM with automatic tracking

        Args:
            messages: Conversation messages
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override

        Returns:
            LLM response content
        """
        system_prompt = self.get_system_prompt()

        response = await self.openai.chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Track usage in current activity
        if self.current_activity:
            self.current_activity.llm_usage = response["usage"]

        return response["content"]

    async def run(self):
        """Run the agent's message processing loop"""
        self.is_running = True
        logger.info("agent_started", agent=self.role.value)

        while self.is_running:
            try:
                message = await self.message_queue.get()
                await self._handle_message(message)
                self.message_queue.task_done()
            except Exception as e:
                logger.error(
                    "agent_error",
                    agent=self.role.value,
                    error=str(e)
                )

    async def _handle_message(self, message: AgentMessage):
        """Handle an incoming message"""
        logger.debug(
            "handling_message",
            agent=self.role.value,
            message_type=message.message_type.value
        )

        if message.message_type == MessageType.REQUEST:
            try:
                result = await self.process_task(message.content)

                # Send response
                await self.send_message(
                    content=result,
                    recipient=message.sender,
                    message_type=MessageType.RESPONSE,
                    parent_id=message.id
                )
            except Exception as e:
                # Send error response
                await self.send_message(
                    content={"error": str(e)},
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    parent_id=message.id
                )

    def stop(self):
        """Stop the agent"""
        self.is_running = False
        logger.info("agent_stopped", agent=self.role.value)
