# Bala Aparna - 29485442

"""
MCP Server - Model Context Protocol Server Implementation
Handles message routing between agents
"""
import asyncio
import json
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
import uuid
import structlog
from models.schemas import AgentMessage, AgentRole, MessageType

logger = structlog.get_logger()


class MCPServer:
    """
    Model Context Protocol Server
    Routes messages between agents and maintains communication state
    """

    def __init__(self):
        self.agents: Dict[AgentRole, 'BaseAgent'] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_history: List[AgentMessage] = []
        self.active_conversations: Dict[str, List[AgentMessage]] = {}
        self.subscriptions: Dict[AgentRole, Set[MessageType]] = {}

        logger.info("mcp_server_initialized")

    def register_agent(self, agent_role: AgentRole, agent: 'BaseAgent'):
        """Register an agent with the MCP server"""
        self.agents[agent_role] = agent
        self.subscriptions[agent_role] = set()
        logger.info("agent_registered", role=agent_role.value)

    def subscribe(self, agent_role: AgentRole, message_types: List[MessageType]):
        """Subscribe an agent to specific message types"""
        if agent_role not in self.subscriptions:
            self.subscriptions[agent_role] = set()

        self.subscriptions[agent_role].update(message_types)
        logger.info(
            "agent_subscribed",
            role=agent_role.value,
            message_types=[mt.value for mt in message_types]
        )

    async def send_message(
        self,
        sender: AgentRole,
        content: Dict,
        recipient: Optional[AgentRole] = None,
        message_type: MessageType = MessageType.REQUEST,
        parent_id: Optional[str] = None
    ) -> AgentMessage:
        """
        Send a message through the MCP

        Args:
            sender: Agent sending the message
            content: Message content
            recipient: Target agent (None for broadcast)
            message_type: Type of message
            parent_id: ID of parent message (for threading)

        Returns:
            The created AgentMessage
        """
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(timezone.utc),
            parent_id=parent_id
        )

        # Add to history
        self.message_history.append(message)

        # Add to queue for processing
        await self.message_queue.put(message)

        logger.info(
            "message_sent",
            message_id=message.id,
            sender=sender.value,
            recipient=recipient.value if recipient else "broadcast",
            type=message_type.value
        )

        return message

    async def process_messages(self):
        """Process messages from the queue (run as background task)"""
        logger.info("mcp_message_processor_started")

        while True:
            try:
                message = await self.message_queue.get()
                await self._route_message(message)
                self.message_queue.task_done()
            except Exception as e:
                logger.error("message_processing_error", error=str(e))

    async def _route_message(self, message: AgentMessage):
        """Route a message to the appropriate agent(s)"""
        if message.recipient:
            # Direct message to specific agent
            if message.recipient in self.agents:
                await self._deliver_to_agent(message.recipient, message)
            else:
                logger.warning(
                    "recipient_not_found",
                    recipient=message.recipient.value,
                    message_id=message.id
                )
        else:
            # Broadcast to subscribed agents
            for agent_role, message_types in self.subscriptions.items():
                if message.message_type in message_types and agent_role != message.sender:
                    await self._deliver_to_agent(agent_role, message)

    async def _deliver_to_agent(self, agent_role: AgentRole, message: AgentMessage):
        """Deliver a message to a specific agent"""
        if agent_role in self.agents:
            agent = self.agents[agent_role]
            try:
                await agent.receive_message(message)
                logger.debug(
                    "message_delivered",
                    agent=agent_role.value,
                    message_id=message.id
                )
            except Exception as e:
                logger.error(
                    "message_delivery_error",
                    agent=agent_role.value,
                    error=str(e)
                )

    def get_conversation(self, conversation_id: str) -> List[AgentMessage]:
        """Get all messages for a specific conversation"""
        return self.active_conversations.get(conversation_id, [])

    def get_agent_messages(
        self,
        agent_role: AgentRole,
        limit: Optional[int] = None
    ) -> List[AgentMessage]:
        """Get messages sent by a specific agent"""
        messages = [
            msg for msg in self.message_history
            if msg.sender == agent_role
        ]

        if limit:
            messages = messages[-limit:]

        return messages

    def clear_history(self):
        """Clear message history"""
        self.message_history.clear()
        self.active_conversations.clear()
        logger.info("message_history_cleared")


# Global MCP server instance
mcp_server = MCPServer()
