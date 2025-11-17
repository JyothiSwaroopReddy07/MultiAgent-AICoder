"""
OpenAI client wrapper with usage tracking
"""
import os
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
import structlog
from utils.llm_tracker import tracker

logger = structlog.get_logger()


class OpenAIClient:
    """Wrapper for OpenAI API with automatic usage tracking"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        self.fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo")
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info("openai_client_initialized", model=self.model)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Create a chat completion with usage tracking

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            use_fallback: Use fallback model instead

        Returns:
            Dict with 'content' and 'usage' keys
        """
        # Prepend system message if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        model = self.fallback_model if use_fallback else self.model
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            logger.info(
                "openai_api_call",
                model=model,
                message_count=len(messages),
                temperature=temp
            )

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok
            )

            # Validate response has choices
            if not response.choices or len(response.choices) == 0:
                logger.error("openai_empty_response", model=model)
                raise ValueError("OpenAI API returned empty choices array")

            # Extract usage information
            usage_data = response.usage
            content = response.choices[0].message.content
            
            # Validate content is not None (can happen with function calls only)
            if content is None:
                logger.warning("openai_null_content", model=model, finish_reason=response.choices[0].finish_reason)
                content = ""  # Default to empty string

            # Track usage
            usage = tracker.track_usage(
                model=model,
                prompt_tokens=usage_data.prompt_tokens,
                completion_tokens=usage_data.completion_tokens
            )

            return {
                "content": content,
                "usage": usage,
                "model": model,
                "finish_reason": response.choices[0].finish_reason
            }

        except Exception as e:
            logger.error(
                "openai_api_error",
                error=str(e),
                model=model
            )

            # Try fallback model if not already using it
            if not use_fallback and model != self.fallback_model:
                logger.info("retrying_with_fallback_model", fallback=self.fallback_model)
                return await self.chat_completion(
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                    use_fallback=True
                )

            raise

    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate completion with function/tool calling

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            system_prompt: Optional system prompt

        Returns:
            Dict with completion and tool calls
        """
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.temperature
            )

            # Validate response has choices
            if not response.choices or len(response.choices) == 0:
                logger.error("openai_empty_response_tools", model=self.model)
                raise ValueError("OpenAI API returned empty choices array")

            # Track usage
            usage_data = response.usage
            usage = tracker.track_usage(
                model=self.model,
                prompt_tokens=usage_data.prompt_tokens,
                completion_tokens=usage_data.completion_tokens
            )

            message = response.choices[0].message
            
            # Validate content (can be None when only tool calls are present)
            content = message.content if message.content is not None else ""
            if message.content is None:
                logger.debug("openai_null_content_with_tools", model=self.model, has_tool_calls=hasattr(message, 'tool_calls'))

            return {
                "content": content,
                "tool_calls": message.tool_calls if hasattr(message, 'tool_calls') else None,
                "usage": usage,
                "finish_reason": response.choices[0].finish_reason
            }

        except Exception as e:
            logger.error("openai_tools_api_error", error=str(e))
            raise


# Global client instance (singleton pattern)
_client_instance: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """
    Get or create the global OpenAI client instance (singleton)
    
    Returns:
        OpenAIClient: The global client instance
    """
    global _client_instance
    if _client_instance is None:
        # Import here to avoid circular dependency
        from config import get_settings
        settings = get_settings()
        
        _client_instance = OpenAIClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        logger.info("openai_client_singleton_created", model=settings.openai_model)
    return _client_instance
