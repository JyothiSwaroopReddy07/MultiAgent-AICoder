# Jyothi Swaroop - 59607464

"""
Base Agent - Abstract base class for all agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import structlog

from models.schemas import AgentRole, AgentActivity, LLMUsage
from utils.gemini_client import get_gemini_client
from utils.llm_tracker import tracker

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.
    
    Provides common functionality:
    - LLM interaction via Gemini
    - Activity tracking
    - MCP server integration
    - Logging
    """

    def __init__(
        self,
        role: AgentRole,
        mcp_server: Optional[Any] = None,
        openai_client: Optional[Any] = None  # Legacy parameter, using Gemini
    ):
        """
        Initialize the base agent.
        
        Args:
            role: The agent's role
            mcp_server: Optional MCP server for inter-agent communication
            openai_client: Legacy parameter, ignored (using Gemini instead)
        """
        self.role = role
        self.mcp_server = mcp_server
        self.gemini_client = get_gemini_client()
        self.current_activity: Optional[AgentActivity] = None
        self.activities: List[AgentActivity] = []
        
        logger.info("agent_initialized", role=role.value)

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Must be implemented by subclasses.
        
        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task.
        Must be implemented by subclasses.
        
        Args:
            task_data: Task data dictionary
            
        Returns:
            Result dictionary
        """
        pass

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        Call the LLM (Gemini) with messages and retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            system_prompt: Optional system prompt override
            max_retries: Maximum number of retry attempts
            
        Returns:
            LLM response content string
        """
        import asyncio
        
        sys_prompt = system_prompt or self.get_system_prompt()
        last_error = None
        
        # Set agent context for usage tracking
        tracker.set_current_agent(self.role.value)
        
        for attempt in range(max_retries):
            try:
                response = await self.gemini_client.chat_completion(
                    messages=messages,
                    system_prompt=sys_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                content = response.get("content", "")
                
                if not content or content.strip() == "":
                    raise ValueError("Empty response from LLM")
                
                if self.current_activity:
                    self.current_activity.llm_usage = LLMUsage(
                        model=response.get("model", "gemini-2.5-flash"),
                        prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                        completion_tokens=response.get("usage", {}).get("completion_tokens", 0),
                        total_tokens=response.get("usage", {}).get("total_tokens", 0),
                        cost=response.get("usage", {}).get("cost", 0.0)
                    )
                
                return content
                
            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) + 1
                error_msg = str(e)
                error_type = type(e).__name__

                # Console logging for debugging
                print(f"\n⚠️  LLM Call Failed (Attempt {attempt + 1}/{max_retries})")
                print(f"   Agent: {self.role.value}")
                print(f"   Error Type: {error_type}")
                print(f"   Error: {error_msg[:200]}")
                if "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                    print(f"   ⚠️  RATE LIMIT/QUOTA ISSUE DETECTED")
                print(f"   Retrying in {wait_time}s...\n")

                logger.warning(
                    "llm_call_retry",
                    agent=self.role.value,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=error_msg,
                    error_type=error_type,
                    wait_time=wait_time
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
        
        logger.error(
            "llm_call_failed_after_retries",
            agent=self.role.value,
            error=str(last_error),
            attempts=max_retries
        )
        raise last_error

    async def start_activity(self, action: str) -> AgentActivity:
        """
        Start tracking an activity.
        
        Args:
            action: Description of the action being performed
            
        Returns:
            The created AgentActivity
        """
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

    async def complete_activity(self, status: str = "completed") -> Optional[AgentActivity]:
        """
        Complete the current activity.
        
        Args:
            status: Final status (completed/failed)
            
        Returns:
            The completed AgentActivity
        """
        if self.current_activity:
            self.current_activity.status = status
            self.current_activity.end_time = datetime.now(timezone.utc)
            self.activities.append(self.current_activity)
            
            logger.info(
                "activity_completed",
                agent=self.role.value,
                action=self.current_activity.action,
                status=status
            )
            
            activity = self.current_activity
            self.current_activity = None
            return activity
            
        return None

    async def receive_message(self, message: Any) -> None:
        """
        Receive a message from the MCP server.
        This enforces strict communication protocols via MCP.
        
        Args:
            message: The received AgentMessage
        """
        logger.info(
            "mcp_message_received",
            agent=self.role.value,
            message_id=getattr(message, 'id', 'unknown'),
            sender=getattr(message, 'sender', 'unknown'),
            message_type=getattr(message, 'message_type', 'unknown')
        )
        
        # Handle REQUEST messages
        if hasattr(message, 'message_type') and message.message_type.value == "request":
            try:
                # Process the request
                result = await self.process_task(message.content)
                
                # Send response back through MCP
                if self.mcp_server:
                    from models.schemas import MessageType
                    # Wrap list results in dict for MCP compatibility
                    mcp_content = result if isinstance(result, dict) else {"data": result}
                    await self.mcp_server.send_message(
                        sender=self.role,
                        recipient=message.sender,
                        content=mcp_content,
                        message_type=MessageType.RESPONSE,
                        parent_id=message.id
                    )
                    
                logger.info(
                    "mcp_request_processed",
                    agent=self.role.value,
                    message_id=message.id
                )
            except Exception as e:
                logger.error(
                    "mcp_request_failed",
                    agent=self.role.value,
                    error=str(e),
                    message_id=getattr(message, 'id', 'unknown')
                )
                
                # Send error response
                if self.mcp_server:
                    from models.schemas import MessageType
                    await self.mcp_server.send_message(
                        sender=self.role,
                        recipient=message.sender,
                        content={"error": str(e)},
                        message_type=MessageType.ERROR,
                        parent_id=message.id
                    )

    def get_activities(self) -> List[AgentActivity]:
        """
        Get all completed activities.
        
        Returns:
            List of AgentActivity objects
        """
        return self.activities

    def reset_activities(self) -> None:
        """Reset all tracked activities."""
        self.activities = []
        self.current_activity = None

