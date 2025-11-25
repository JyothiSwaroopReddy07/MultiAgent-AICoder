"""
Router Agent - LLM-based intelligent routing for agentic workflows

This agent uses an LLM to analyze user messages and conversation context
to determine which agent should handle the request next.

Industry-standard approach used by LangGraph, AutoGPT, CrewAI, etc.
"""
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
import json
import structlog
from pydantic import BaseModel, Field

from models.conversation_schemas import ConversationPhase, ConversationMessage
from utils.openai_client import OpenAIClient

logger = structlog.get_logger()


class RoutingAction(str, Enum):
    """Available routing actions"""
    PLAN_FEATURES = "plan_features"           # Create initial feature plan
    REFINE_FEATURES = "refine_features"       # Modify/add/remove features
    APPROVE_FEATURES = "approve_features"     # User approves, ready to implement
    IMPLEMENT_CODE = "implement_code"         # Generate code
    MODIFY_CODE = "modify_code"              # Change generated code
    CLARIFY = "clarify"                      # Need more information
    CHAT = "chat"                            # General conversation


class RoutingDecision(BaseModel):
    """Structured output from Router Agent"""
    action: RoutingAction = Field(..., description="Which action/agent to route to")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in routing decision (0-1)")
    reasoning: str = Field(..., description="Why this routing decision was made")
    extracted_intent: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted parameters for the target agent"
    )


class RouterAgent:
    """
    LLM-based routing agent for intelligent conversation flow management
    
    This replaces keyword-based routing with intelligent LLM decision making.
    The LLM analyzes:
    - Current conversation phase
    - User message content and intent
    - Conversation history
    - Available context (features, code, etc.)
    
    And decides which agent should handle the request next.
    """
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
        logger.info("router_agent_initialized")
    
    async def route_message(
        self,
        user_message: str,
        current_phase: ConversationPhase,
        conversation_history: List[ConversationMessage],
        context: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Use LLM to determine routing decision
        
        Args:
            user_message: Latest message from user
            current_phase: Current conversation phase
            conversation_history: Recent conversation messages
            context: Additional context (proposed features, generated code, etc.)
            
        Returns:
            RoutingDecision with action, confidence, and reasoning
        """
        logger.info(
            "routing_decision_requested",
            phase=current_phase,
            message_preview=user_message[:50]
        )
        
        # Build context summary
        context_summary = self._build_context_summary(context or {})
        
        # Build conversation history for LLM
        history_text = self._format_conversation_history(conversation_history)
        
        # Create routing prompt
        system_prompt = self._build_routing_system_prompt()
        user_prompt = self._build_routing_user_prompt(
            user_message=user_message,
            current_phase=current_phase,
            history_text=history_text,
            context_summary=context_summary
        )
        
        # Call LLM with structured output
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",  # Use model that supports JSON mode
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent routing
                response_format={"type": "json_object"}
            )
            
            # Parse structured response
            routing_data = json.loads(response.choices[0].message.content)
            decision = RoutingDecision(**routing_data)
            
            logger.info(
                "routing_decision_made",
                action=decision.action,
                confidence=decision.confidence,
                reasoning=decision.reasoning[:100]
            )
            
            return decision
            
        except Exception as e:
            logger.error("routing_error", error=str(e))
            # Fallback to safe default
            return RoutingDecision(
                action=RoutingAction.CLARIFY,
                confidence=0.5,
                reasoning=f"Error during routing: {str(e)}. Falling back to clarification.",
                extracted_intent={}
            )
    
    def _build_routing_system_prompt(self) -> str:
        """System prompt for routing LLM"""
        return """You are an expert Router Agent for an AI code generation system.

Your job is to analyze the user's message and conversation context to determine which agent should handle the request next.

**Available Actions:**

1. **plan_features** - User is describing what they want to build (initial request)
   - Use when: User describes a new project/feature for the first time
   - Examples: "build a todo app", "create a blog", "I need a dashboard"

2. **refine_features** - User wants to modify the proposed features
   - Use when: User asks to add/remove/modify features
   - Examples: "add user authentication", "remove the admin panel", "make it simpler"

3. **approve_features** - User approves the plan and wants implementation
   - Use when: User indicates they're satisfied and want code generated
   - Examples: "implement it", "looks good", "start coding", "build it", "yes", "ok"

4. **implement_code** - Ready to generate code (typically after approval)
   - Use when: Features are approved and code generation should begin
   - Usually triggered automatically after approve_features

5. **modify_code** - User wants to change generated code
   - Use when: Code exists and user requests changes
   - Examples: "change the database to MongoDB", "add error handling", "fix the login bug"

6. **clarify** - Need more information from user
   - Use when: User message is too vague or ambiguous
   - Examples: "make it better", "fix it", unclear requests

7. **chat** - General conversation (not a task)
   - Use when: User asks questions, thanks, or casual chat
   - Examples: "how does this work?", "thanks", "what technologies do you support?"

**Current Context Fields:**
- `current_phase`: Where we are in the workflow (INITIAL, FEATURE_REFINEMENT, etc.)
- `has_proposed_features`: Whether features have been proposed
- `has_generated_code`: Whether code has been generated
- `conversation_history`: Recent messages

**Output Format (JSON):**
```json
{
  "action": "approve_features",
  "confidence": 0.95,
  "reasoning": "User said 'implement them' which indicates approval of proposed features",
  "extracted_intent": {
    "user_wants_changes": false,
    "urgency": "normal"
  }
}
```

**Rules:**
1. Be decisive - choose the most appropriate action
2. Confidence should reflect certainty (0.0 to 1.0)
3. Provide clear reasoning for your decision
4. Extract any useful parameters in extracted_intent
5. Consider conversation context, not just the last message
6. When in doubt between approve and refine, lean toward refine (safer)

Respond ONLY with valid JSON matching the schema above."""

    def _build_routing_user_prompt(
        self,
        user_message: str,
        current_phase: ConversationPhase,
        history_text: str,
        context_summary: str
    ) -> str:
        """Build the user prompt with all context"""
        return f"""**ROUTING DECISION REQUEST**

**Current Phase:** {current_phase.value}

**Current Context:**
{context_summary}

**Recent Conversation History:**
{history_text}

**Latest User Message:**
"{user_message}"

---

Analyze the above and determine which action should handle this request.
Respond with JSON containing: action, confidence, reasoning, extracted_intent."""

    def _format_conversation_history(
        self,
        messages: List[ConversationMessage],
        max_messages: int = 5
    ) -> str:
        """Format recent conversation history for LLM"""
        if not messages:
            return "(No conversation history)"
        
        # Get last N messages
        recent = messages[-max_messages:]
        
        formatted = []
        for msg in recent:
            role = "User" if msg.role.value == "user" else "Assistant"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """Build a summary of current context"""
        summary_parts = []
        
        # Check for proposed features
        if context.get("proposed_features"):
            features = context["proposed_features"]
            if hasattr(features, "features"):
                count = len(features.features)
                summary_parts.append(f"- Proposed features: {count} features have been proposed")
            else:
                summary_parts.append("- Proposed features: Features have been proposed")
        else:
            summary_parts.append("- Proposed features: None yet")
        
        # Check for generated code
        if context.get("generated_code"):
            summary_parts.append("- Generated code: Code has been generated")
        else:
            summary_parts.append("- Generated code: None yet")
        
        # Add any other relevant context
        if context.get("last_action"):
            summary_parts.append(f"- Last action: {context['last_action']}")
        
        return "\n".join(summary_parts) if summary_parts else "(No context available)"


# Singleton instance
_router_instance: Optional[RouterAgent] = None


def get_router_agent(openai_client: OpenAIClient) -> RouterAgent:
    """Get or create router agent singleton"""
    global _router_instance
    if _router_instance is None:
        _router_instance = RouterAgent(openai_client)
    return _router_instance

