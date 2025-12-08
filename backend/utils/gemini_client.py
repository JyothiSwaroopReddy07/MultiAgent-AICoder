# edited by Kunwarjeet

"""
Gemini client wrapper with usage tracking, retry logic, and error handling
"""
import os
import asyncio
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions
import structlog

from utils.llm_tracker import tracker
from utils.decorators import retry_with_backoff, timeout, log_execution_time
from constants import REQUEST_TIMEOUT, MAX_RETRIES

logger = structlog.get_logger()

# Global safety settings to disable all content filtering
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


class GeminiClient:
    """Wrapper for Google Gemini API with automatic usage tracking"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-pro")
        self.fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-pro")
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        # Map old model names to new ones for backward compatibility
        model_mapping = {
            "gemini-pro": "gemini-2.5-flash",
            "gemini-1.5-pro": "gemini-2.5-pro",
            "gemini-1.5-flash": "gemini-2.5-flash",
            "gpt-4": "gemini-2.5-pro",  # For migration from OpenAI
            "gpt-3.5-turbo": "gemini-2.5-flash"
        }
        self.model = model_mapping.get(self.model, self.model)
        self.fallback_model = model_mapping.get(self.fallback_model, self.fallback_model)
        logger.info("gemini_client_initialized", model=self.model)

    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> tuple:
        """
        Convert OpenAI-style messages to Gemini format
        
        Returns:
            tuple: (system_instruction, conversation_history)
        """
        system_instruction = None
        conversation_history = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                conversation_history.append({
                    "role": "user",
                    "parts": [content]
                })
            elif role == "assistant":
                conversation_history.append({
                    "role": "model",
                    "parts": [content]
                })
        
        return system_instruction, conversation_history

    @retry_with_backoff(
        max_retries=MAX_RETRIES,
        exceptions=(google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)
    )
    @timeout(REQUEST_TIMEOUT)
    @log_execution_time(log_level="debug")
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Create a chat completion with usage tracking, retry logic, and timeout

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            use_fallback: Use fallback model instead

        Returns:
            Dict with 'content' and 'usage' keys
            
        Raises:
            TimeoutError: If request exceeds timeout
            ResourceExhausted: If rate limit is exceeded after retries
            APIError: For other API errors
        """
        # Prepend system message if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        model_name = self.fallback_model if use_fallback else self.model
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        try:
            logger.info(
                "gemini_api_call",
                model=model_name,
                message_count=len(messages),
                temperature=temp
            )

            # Convert messages to Gemini format
            system_instruction, conversation_history = self._convert_messages_to_gemini_format(messages)
            
            # Create model with configuration
            generation_config = genai.types.GenerationConfig(
                temperature=temp,
                max_output_tokens=max_tok,
            )
            
            # Create model instance with safety settings
            model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings=SAFETY_SETTINGS  # Pass safety settings to constructor
            )

            # Build the prompt from conversation history
            if len(conversation_history) == 0:
                raise ValueError("No messages to send to Gemini")
            
            # Prepend system instruction to the first user message if it exists
            # Create a COPY to avoid modifying the original
            if system_instruction:
                first_message = f"{system_instruction}\n\n{conversation_history[0]['parts'][0]}"
                conversation_history = [{"role": "user", "parts": [first_message]}] + conversation_history[1:]
            
            # IMPORTANT: Gemini's generate_content is synchronous, need to run in executor
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            # For single user message
            if len(conversation_history) == 1:
                full_prompt = conversation_history[0]["parts"][0]
                logger.info("CALLING_GEMINI_API", 
                           safety_settings_count=len(SAFETY_SETTINGS),
                           prompt_length=len(full_prompt),
                           system_instruction_length=len(system_instruction) if system_instruction else 0,
                           FULL_PROMPT=full_prompt[:1000])  # Log more to see what's triggering
                
                # Create a proper function instead of lambda to ensure safety_settings are captured
                def _generate():
                    return model.generate_content(
                        conversation_history[0]["parts"][0],
                        generation_config=generation_config,
                        safety_settings=SAFETY_SETTINGS
                    )
                
                response = await loop.run_in_executor(None, _generate)
                logger.debug("response_received",
                           has_candidates=hasattr(response, 'candidates'),
                           finish_reason=response.candidates[0].finish_reason if hasattr(response, 'candidates') and response.candidates else None)
            else:
                # For conversation history, use chat
                chat = model.start_chat(history=conversation_history[:-1])
                
                def _send_message():
                    return chat.send_message(
                        conversation_history[-1]["parts"][0],
                        generation_config=generation_config,
                        safety_settings=SAFETY_SETTINGS
                    )
                
                response = await loop.run_in_executor(None, _send_message)

            # Validate and extract response content
            if not response:
                logger.error("gemini_empty_response", model=model_name)
                raise ValueError("Gemini API returned empty response")

            # Handle different response formats from Gemini - try multiple methods
            content = None
            
            # Method 1: Try response.text (works for simple responses)
            try:
                content = response.text
                if content:
                    logger.debug("extracted_via_text_property")
            except (AttributeError, ValueError) as e:
                logger.debug("text_property_failed", error=str(e)[:100])
            
            # Method 2: Extract from candidates manually (for multi-part responses)
            if not content and hasattr(response, 'candidates') and response.candidates:
                try:
                    candidate = response.candidates[0]
                    logger.debug("checking_candidate", 
                               has_content=hasattr(candidate, 'content'),
                               finish_reason=str(candidate.finish_reason) if hasattr(candidate, 'finish_reason') else None)
                    
                    if hasattr(candidate, 'content'):
                        content_obj = candidate.content
                        if hasattr(content_obj, 'parts') and content_obj.parts:
                            content_parts = []
                            for i, part in enumerate(content_obj.parts):
                                logger.debug(f"checking_part_{i}", 
                                           has_text=hasattr(part, 'text'),
                                           part_type=type(part).__name__)
                                # Try to get text from part
                                if hasattr(part, 'text'):
                                    try:
                                        part_text = part.text
                                        if part_text:
                                            content_parts.append(part_text)
                                            logger.debug(f"extracted_part_{i}", length=len(part_text))
                                    except Exception as e:
                                        logger.warning(f"part_{i}_text_access_failed", error=str(e))
                            if content_parts:
                                content = "\n".join(content_parts)
                                logger.debug("extracted_from_parts", num_parts=len(content_parts))
                        else:
                            logger.warning("no_parts_in_content", 
                                         has_parts=hasattr(content_obj, 'parts'),
                                         parts_count=len(content_obj.parts) if hasattr(content_obj, 'parts') else 0)
                except Exception as e:
                    logger.error("manual_extraction_failed", error=str(e), error_type=type(e).__name__)
            
            # Final validation - DO NOT fallback to str(response)
            if not content or len(content.strip()) == 0:
                logger.error("gemini_content_extraction_failed", 
                           model=model_name,
                           has_candidates=hasattr(response, 'candidates'),
                           num_candidates=len(response.candidates) if hasattr(response, 'candidates') else 0,
                           response_type=type(response).__name__)
                
                # Try one more method: check if it's blocked
                if hasattr(response, 'prompt_feedback'):
                    logger.error("gemini_blocked_response", 
                               feedback=str(response.prompt_feedback),
                               safety_ratings=str(response.prompt_feedback.safety_ratings) if hasattr(response.prompt_feedback, 'safety_ratings') else None)
                
                raise ValueError(f"Gemini API returned empty/unusable content. Response type: {type(response).__name__}")

            # Extract usage information (Gemini provides token counts)
            prompt_tokens = 0
            completion_tokens = 0
            
            if hasattr(response, 'usage_metadata'):
                usage_meta = response.usage_metadata
                
                # Log all available fields for debugging
                logger.debug(
                    "usage_metadata_available",
                    fields=dir(usage_meta),
                    str_repr=str(usage_meta)
                )
                
                # Try different possible field names
                prompt_tokens = (
                    getattr(usage_meta, 'prompt_token_count', None) or
                    getattr(usage_meta, 'input_token_count', None) or
                    getattr(usage_meta, 'prompt_tokens', None) or
                    0
                )
                
                completion_tokens = (
                    getattr(usage_meta, 'candidates_token_count', None) or
                    getattr(usage_meta, 'output_token_count', None) or
                    getattr(usage_meta, 'completion_tokens', None) or
                    0
                )
                
                logger.info(
                    "token_usage_extracted",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total=prompt_tokens + completion_tokens,
                    model=model_name
                )
            else:
                logger.warning("no_usage_metadata_in_response", model=model_name)

            # Track usage
            usage = tracker.track_usage(
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            return {
                "content": content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cost": usage.cost
                },
                "model": model_name,
                "finish_reason": "stop"
            }

        except Exception as e:
            logger.error(
                "gemini_api_error",
                error=str(e),
                model=model_name
            )

            # Try fallback model if not already using it
            if not use_fallback and model_name != self.fallback_model:
                logger.info("retrying_with_fallback_model", fallback=self.fallback_model)
                return await self.chat_completion(
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                    use_fallback=True
                )

            raise

    @retry_with_backoff(
        max_retries=MAX_RETRIES,
        exceptions=(google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)
    )
    @timeout(REQUEST_TIMEOUT)
    @log_execution_time(log_level="debug")
    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate completion with function/tool calling, retry logic, and timeout

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            system_prompt: Optional system prompt

        Returns:
            Dict with completion and tool calls
            
        Raises:
            TimeoutError: If request exceeds timeout
            ResourceExhausted: If rate limit is exceeded after retries
            APIError: For other API errors
        """
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            # Convert messages to Gemini format
            system_instruction, conversation_history = self._convert_messages_to_gemini_format(messages)
            
            # Convert OpenAI tool format to Gemini function format
            gemini_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    gemini_tools.append({
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": func.get("parameters", {})
                    })
            
            # Create model with tools
            generation_config = genai.types.GenerationConfig(
                temperature=self.temperature,
            )
            
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=generation_config,
                    system_instruction=system_instruction,
                    tools=gemini_tools if gemini_tools else None
                )
            else:
                model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=generation_config,
                    tools=gemini_tools if gemini_tools else None
                )

            # Build the prompt
            if len(conversation_history) == 0:
                raise ValueError("No messages to send to Gemini")
            
            # For single user message
            if len(conversation_history) == 1:
                response = model.generate_content(
                    conversation_history[0]["parts"][0],
                    generation_config=generation_config
                )
            else:
                # For conversation history
                chat = model.start_chat(history=conversation_history[:-1])
                response = chat.send_message(
                    conversation_history[-1]["parts"][0],
                    generation_config=generation_config
                )

            # Extract usage information
            prompt_tokens = 0
            completion_tokens = 0
            
            if hasattr(response, 'usage_metadata'):
                usage_meta = response.usage_metadata
                
                # Try different possible field names
                prompt_tokens = (
                    getattr(usage_meta, 'prompt_token_count', None) or
                    getattr(usage_meta, 'input_token_count', None) or
                    getattr(usage_meta, 'prompt_tokens', None) or
                    0
                )
                
                completion_tokens = (
                    getattr(usage_meta, 'candidates_token_count', None) or
                    getattr(usage_meta, 'output_token_count', None) or
                    getattr(usage_meta, 'completion_tokens', None) or
                    0
                )
                
                logger.info(
                    "token_usage_extracted_tools",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total=prompt_tokens + completion_tokens,
                    model=self.model
                )
            else:
                logger.warning("no_usage_metadata_in_response_tools", model=self.model)

            # Track usage
            usage = tracker.track_usage(
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            content = response.text if response.text else ""
            
            # Extract function calls if present
            tool_calls = None
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            # Convert Gemini function call to OpenAI format
                            if tool_calls is None:
                                tool_calls = []
                            tool_calls.append({
                                "id": f"call_{len(tool_calls)}",
                                "type": "function",
                                "function": {
                                    "name": part.function_call.name,
                                    "arguments": str(part.function_call.args)
                                }
                            })

            return {
                "content": content,
                "tool_calls": tool_calls,
                "usage": usage,
                "finish_reason": "stop"
            }

        except Exception as e:
            logger.error("gemini_tools_api_error", error=str(e))
            raise


# Global client instance (singleton pattern)
_client_instance: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Get or create the global Gemini client instance (singleton)
    
    Returns:
        GeminiClient: The global client instance
    """
    global _client_instance
    if _client_instance is None:
        # Import here to avoid circular dependency
        from config import get_settings
        settings = get_settings()
        
        _client_instance = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        logger.info("gemini_client_singleton_created", model=settings.gemini_model)
    return _client_instance

