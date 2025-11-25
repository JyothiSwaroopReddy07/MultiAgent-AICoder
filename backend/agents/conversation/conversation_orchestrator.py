"""
Conversation Orchestrator - Manages chat-based code generation workflow
Handles multi-turn conversations with state management

Uses LLM-based routing via RouterAgent for intelligent agent-to-agent control transfer.
"""
from typing import Dict, Any, AsyncGenerator, Optional, List
import uuid
import json
from datetime import datetime, timezone
import structlog

from models.conversation_schemas import (
    ConversationState,
    ConversationPhase,
    ConversationMessage,
    MessageRole,
    Feature,
    FeaturePlan,
    GeneratedCode,
    StreamEvent
)
from agents.conversation.feature_planner_agent import FeaturePlannerAgent
from agents.conversation.code_modifier_agent import CodeModifierAgent
from agents.advanced_orchestrator import AdvancedOrchestrator
from agents.routing import RouterAgent, RoutingAction

logger = structlog.get_logger()


class ConversationOrchestrator:
    """
    Orchestrates conversational code generation with iterative refinement
    
    Workflow:
    1. User describes problem → AI proposes features
    2. User refines features → AI updates plan
    3. User approves → AI implements code
    4. User requests modifications → AI updates code
    """
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.conversations: Dict[str, ConversationState] = {}
        
        # Initialize specialized agents
        from mcp.server import MCPServer
        self.mcp = MCPServer()
        
        # Initialize LLM-based router for intelligent agent control transfer
        # RouterAgent needs the raw AsyncOpenAI client, not the wrapper
        self.router = RouterAgent(openai_client.client)
        
        self.feature_planner = FeaturePlannerAgent(self.mcp, openai_client)
        self.code_modifier = CodeModifierAgent(self.mcp, openai_client)
        # Use simplified orchestrator for faster code generation
        from agents.simple_orchestrator import SimpleOrchestrator
        self.code_generator = SimpleOrchestrator(openai_client)
        
        logger.info("conversation_orchestrator_initialized", routing="llm_based")
    
    async def process_message(
        self,
        conversation_id: Optional[str],
        user_message: str,
        action: Optional[str] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process user message and stream responses
        
        Args:
            conversation_id: Existing conversation or None for new
            user_message: User's message
            action: Explicit action (plan, approve, implement, modify)
            
        Yields:
            StreamEvent objects for real-time updates
        """
        # Get or create conversation
        if conversation_id and conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            logger.info("continuing_conversation", conversation_id=conversation_id)
        else:
            conversation_id = str(uuid.uuid4())
            conversation = ConversationState(conversation_id=conversation_id)
            self.conversations[conversation_id] = conversation
            logger.info("new_conversation_started", conversation_id=conversation_id)
        
        # Add user message to history
        user_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=user_message,
            timestamp=datetime.now(timezone.utc)
        )
        conversation.messages.append(user_msg)
        conversation.updated_at = datetime.now(timezone.utc)
        
        # Use LLM-based routing to determine next action
        # This replaces keyword matching with intelligent intent understanding
        try:
            # Build context for router
            routing_context = {
                "proposed_features": conversation.proposed_features,
                "generated_code": conversation.generated_code,
                "last_action": conversation.metadata.get("last_action") if conversation.metadata else None
            }
            
            # Use Router Agent to make intelligent routing decision
            routing_decision = await self.router.route_message(
                user_message=user_message,
                current_phase=conversation.phase,
                conversation_history=conversation.messages,
                context=routing_context
            )
            
            logger.info(
                "llm_routing_decision",
                conversation_id=conversation_id,
                phase=conversation.phase,
                action=routing_decision.action,
                confidence=routing_decision.confidence,
                reasoning=routing_decision.reasoning
            )
            
            # Store routing decision in metadata for debugging
            if not conversation.metadata:
                conversation.metadata = {}
            conversation.metadata["last_routing_decision"] = {
                "action": routing_decision.action,
                "confidence": routing_decision.confidence,
                "reasoning": routing_decision.reasoning
            }
            
            # Route to appropriate handler based on LLM decision
            if routing_decision.action == RoutingAction.PLAN_FEATURES:
                async for event in self._handle_feature_planning(conversation, user_message):
                    yield event
            
            elif routing_decision.action == RoutingAction.REFINE_FEATURES:
                async for event in self._handle_feature_refinement(conversation, user_message):
                    yield event
            
            elif routing_decision.action == RoutingAction.APPROVE_FEATURES:
                async for event in self._handle_feature_approval(conversation):
                    yield event
            
            elif routing_decision.action == RoutingAction.IMPLEMENT_CODE:
                async for event in self._handle_implementation(conversation):
                    yield event
            
            elif routing_decision.action == RoutingAction.MODIFY_CODE:
                async for event in self._handle_code_modification(conversation, user_message):
                    yield event
            
            elif routing_decision.action == RoutingAction.CLARIFY:
                async for event in self._handle_clarification(conversation, routing_decision):
                    yield event
            
            elif routing_decision.action == RoutingAction.CHAT:
                async for event in self._handle_general_conversation(conversation, user_message):
                    yield event
            
            else:
                # Fallback (should never happen)
                logger.warning("unknown_routing_action", action=routing_decision.action)
                async for event in self._handle_general_conversation(conversation, user_message):
                    yield event
        
        except Exception as e:
            logger.error("conversation_error", error=str(e), conversation_id=conversation_id)
            yield StreamEvent(
                type="error",
                data={"error": str(e), "conversation_id": conversation_id}
            )
    
    async def _handle_feature_planning(
        self,
        conversation: ConversationState,
        user_message: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle initial feature planning phase"""
        
        yield StreamEvent(
            type="phase_change",
            data={
                "conversation_id": conversation.conversation_id,
                "phase": ConversationPhase.FEATURE_PLANNING,
                "message": "Analyzing your requirements and planning features..."
            }
        )
        
        conversation.phase = ConversationPhase.FEATURE_PLANNING
        conversation.problem_statement = user_message
        
        # Call feature planner
        result = await self.feature_planner.process_task({
            "problem_statement": user_message,
            "conversation_history": [
                {"role": msg.role.value, "content": msg.content}
                for msg in conversation.messages[-10:]
            ]
        })
        
        feature_plan_data = result.get("feature_plan", {})
        
        # Create FeaturePlan object
        features = [
            Feature(**feat) for feat in feature_plan_data.get("features", [])
        ]
        
        # Pass values directly to FeaturePlan - field validators will handle normalization
        feature_plan = FeaturePlan(
            features=features,
            tech_stack=feature_plan_data.get("tech_stack", {}),
            database_type=feature_plan_data.get("database_type", "auto"),
            estimated_complexity=feature_plan_data.get("estimated_complexity", "medium"),
            notes=feature_plan_data.get("notes")
        )
        
        conversation.proposed_features = feature_plan
        conversation.phase = ConversationPhase.FEATURE_REFINEMENT
        
        # Send features to user
        yield StreamEvent(
            type="features_proposed",
            data={
                "conversation_id": conversation.conversation_id,
                "features": [feat.dict() for feat in features],
                "tech_stack": feature_plan.tech_stack,
                "reasoning": feature_plan_data.get("reasoning", "")
            }
        )
        
        # Generate response message
        response_message = self._format_feature_plan_message(feature_plan_data)
        
        # Add assistant message
        assistant_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=response_message,
            timestamp=datetime.now(timezone.utc),
            metadata={"features": [feat.dict() for feat in features]}
        )
        conversation.messages.append(assistant_msg)
        
        yield StreamEvent(
            type="message_end",
            data={
                "conversation_id": conversation.conversation_id,
                "message": response_message,
                "awaiting_approval": True
            }
        )
    
    async def _handle_feature_refinement(
        self,
        conversation: ConversationState,
        user_feedback: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle feature plan refinement"""
        
        yield StreamEvent(
            type="message_start",
            data={
                "conversation_id": conversation.conversation_id,
                "message": "Refining features based on your feedback..."
            }
        )
        
        # Get previous features for comparison
        previous_features = conversation.proposed_features.features if conversation.proposed_features else []
        previous_feature_count = len(previous_features)
        
        # Call feature planner with refinement
        result = await self.feature_planner.process_task({
            "problem_statement": conversation.problem_statement,
            "previous_plan": conversation.proposed_features.dict() if conversation.proposed_features else {},
            "user_feedback": user_feedback,
            "conversation_history": [
                {"role": msg.role.value, "content": msg.content}
                for msg in conversation.messages[-10:]
            ]
        })
        
        feature_plan_data = result.get("feature_plan", {})
        
        # Update feature plan
        new_features = [
            Feature(**feat) for feat in feature_plan_data.get("features", [])
        ]
        
        # Safety check: If user is adding features, ensure we didn't lose existing ones
        feedback_lower = user_feedback.lower()
        is_adding = any(word in feedback_lower for word in [
            'add', 'also', 'more', 'additional', 'another', 'include', 
            'plus', 'and also', 'want also', 'need also'
        ])
        is_removing = any(word in feedback_lower for word in [
            'remove', 'delete', 'don\'t want', 'skip', 'exclude', 'without'
        ])
        
        if is_adding and not is_removing:
            # User wants to ADD features
            if len(new_features) < previous_feature_count:
                # Agent accidentally removed features! Merge them back
                logger.warning(
                    "feature_count_decreased_on_add",
                    previous=previous_feature_count,
                    new=len(new_features),
                    feedback=user_feedback
                )
                
                # Keep all previous features that aren't in new features
                new_feature_titles = {f.title.lower() for f in new_features}
                for prev_feat in previous_features:
                    if prev_feat.title.lower() not in new_feature_titles:
                        # This feature was lost, add it back
                        new_features.append(prev_feat)
                        logger.info("restored_missing_feature", title=prev_feat.title)
        
        # Pass values directly to FeaturePlan - field validators will handle normalization
        conversation.proposed_features = FeaturePlan(
            features=new_features,
            tech_stack=feature_plan_data.get("tech_stack", {}),
            database_type=feature_plan_data.get("database_type", "auto"),
            estimated_complexity=feature_plan_data.get("estimated_complexity", "medium"),
            notes=feature_plan_data.get("notes")
        )
        
        yield StreamEvent(
            type="features_proposed",
            data={
                "conversation_id": conversation.conversation_id,
                "features": [feat.dict() for feat in new_features]
            }
        )
        
        # Generate a contextual message based on what changed
        change_summary = self._generate_change_summary(
            previous_features, 
            new_features, 
            is_adding, 
            is_removing
        )
        
        response_message = f"{change_summary}\n\n{self._format_feature_plan_message(feature_plan_data)}"
        
        assistant_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=response_message,
            timestamp=datetime.now(timezone.utc)
        )
        conversation.messages.append(assistant_msg)
        
        yield StreamEvent(
            type="message_end",
            data={
                "conversation_id": conversation.conversation_id,
                "message": response_message
            }
        )
    
    async def _handle_feature_approval(
        self,
        conversation: ConversationState
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle feature approval"""
        
        conversation.approved_features = conversation.proposed_features
        conversation.phase = ConversationPhase.FEATURES_APPROVED
        
        response = "Great! I'll start implementing the approved features. This may take a few minutes..."
        
        assistant_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=response,
            timestamp=datetime.now(timezone.utc)
        )
        conversation.messages.append(assistant_msg)
        
        yield StreamEvent(
            type="message_end",
            data={
                "conversation_id": conversation.conversation_id,
                "message": response
            }
        )
        
        # Auto-trigger implementation
        async for event in self._handle_implementation(conversation):
            yield event
    
    async def _handle_implementation(
        self,
        conversation: ConversationState
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle code implementation"""
        
        yield StreamEvent(
            type="implementation_started",
            data={
                "conversation_id": conversation.conversation_id,
                "message": "Starting implementation..."
            }
        )
        
        conversation.phase = ConversationPhase.IMPLEMENTATION
        
        # Prepare data for code generator
        if not conversation.approved_features:
            raise ValueError("No approved features to implement")
        
        features = conversation.approved_features.features
        feature_descriptions = "\n".join([
            f"- {feat.title}: {feat.description}"
            for feat in features
        ])
        
        implementation_description = f"""{conversation.problem_statement}

APPROVED FEATURES:
{feature_descriptions}

TECH STACK:
{json.dumps(conversation.approved_features.tech_stack, indent=2)}

DATABASE: {conversation.approved_features.database_type}
"""
        
        # Stream implementation progress
        try:
            async for event in self.code_generator.generate_with_streaming({
                "description": implementation_description,
                "database": conversation.approved_features.database_type,
                "language": "nextjs"
            }):
                # Forward events
                event_type = event.get("type")
                
                if event_type == "file_generated":
                    # Backend sends 'file' key, not 'data'
                    file_data = event.get("file", event.get("data", {}))
                    yield StreamEvent(
                        type="file_generated",
                        data={
                            "conversation_id": conversation.conversation_id,
                            **file_data
                        }
                    )
                elif event_type == "phase_started":
                    yield StreamEvent(
                        type="phase_change",
                        data={
                            "conversation_id": conversation.conversation_id,
                            "phase": event.get("phase", ""),
                            "message": event.get("phase", "Processing...")
                        }
                    )
                elif event_type == "agent_started":
                    # Forward agent progress
                    yield StreamEvent(
                        type="phase_change",
                        data={
                            "conversation_id": conversation.conversation_id,
                            "phase": event.get("agent", ""),
                            "message": event.get("activity", "Working...")
                        }
                    )
                elif event_type == "completed":
                    # Store generated code
                    code_data = event.get("data", {})
                    conversation.generated_code = GeneratedCode(
                        files=code_data.get("code_files", []),
                        file_structure=code_data.get("file_structure", {}),
                        setup_instructions=code_data.get("setup_instructions", [])
                    )
                    conversation.phase = ConversationPhase.CODE_GENERATED
                    
                    yield StreamEvent(
                        type="code_generated",
                        data={
                            "conversation_id": conversation.conversation_id,
                            "message": "Implementation complete! You can now request modifications if needed.",
                            "files": code_data.get("code_files", [])
                        }
                    )
                elif event_type == "error":
                    # Forward errors
                    yield StreamEvent(
                        type="error",
                        data={
                            "conversation_id": conversation.conversation_id,
                            "error": event.get("error", "Unknown error occurred")
                        }
                    )
        except Exception as e:
            logger.error("implementation_error", error=str(e), conversation_id=conversation.conversation_id)
            yield StreamEvent(
                type="error",
                data={
                    "conversation_id": conversation.conversation_id,
                    "error": f"Implementation failed: {str(e)}"
                }
            )
    
    async def _handle_code_modification(
        self,
        conversation: ConversationState,
        modification_request: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle code modification requests"""
        
        if not conversation.generated_code:
            yield StreamEvent(
                type="error",
                data={
                    "conversation_id": conversation.conversation_id,
                    "error": "No code has been generated yet"
                }
            )
            return
        
        yield StreamEvent(
            type="message_start",
            data={
                "conversation_id": conversation.conversation_id,
                "message": "Analyzing modification request..."
            }
        )
        
        conversation.phase = ConversationPhase.MODIFICATION
        
        # Call code modifier
        result = await self.code_modifier.process_task({
            "modification_request": modification_request,
            "current_codebase": {
                "files": conversation.generated_code.files
            },
            "context": {
                "database_type": conversation.approved_features.database_type if conversation.approved_features else "postgresql",
                "features": [f.title for f in conversation.approved_features.features] if conversation.approved_features else []
            }
        })
        
        modifications = result.get("modifications", {})
        
        # Update conversation with modified files
        modified_files = modifications.get("modified_files", [])
        new_files = modifications.get("new_files", [])
        
        # Merge modifications into generated code
        for mod_file in modified_files + new_files:
            # Update or add file
            existing_idx = next(
                (i for i, f in enumerate(conversation.generated_code.files)
                 if f.get("filepath") == mod_file.get("filepath")),
                None
            )
            
            if existing_idx is not None:
                conversation.generated_code.files[existing_idx] = mod_file
            else:
                conversation.generated_code.files.append(mod_file)
        
        yield StreamEvent(
            type="modification_applied",
            data={
                "conversation_id": conversation.conversation_id,
                "modified_files": modified_files,
                "new_files": new_files,
                "summary": modifications.get("modification_summary", "")
            }
        )
        
        response_message = f"""Modifications applied successfully!

{modifications.get('modification_summary', '')}

Modified {len(modified_files)} file(s) and added {len(new_files)} new file(s).
"""
        
        assistant_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=response_message,
            timestamp=datetime.now(timezone.utc)
        )
        conversation.messages.append(assistant_msg)
        
        yield StreamEvent(
            type="message_end",
            data={
                "conversation_id": conversation.conversation_id,
                "message": response_message
            }
        )
    
    async def _handle_clarification(
        self,
        conversation: ConversationState,
        routing_decision
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle requests that need clarification"""
        
        # Ask for clarification based on routing reasoning
        clarification_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=f"I need a bit more information to help you effectively. {routing_decision.reasoning}\n\n"
                   f"Could you please provide more details about what you'd like to build?",
            timestamp=datetime.now(timezone.utc)
        )
        conversation.messages.append(clarification_msg)
        
        yield StreamEvent(
            type="message_end",
            data={
                "conversation_id": conversation.conversation_id,
                "message": clarification_msg.content
            }
        )
    
    async def _handle_general_conversation(
        self,
        conversation: ConversationState,
        user_message: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle general conversation (clarifications, questions)"""
        
        # Build context
        context_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in conversation.messages[-10:]
        ]
        
        # Call LLM for conversational response
        response = await self.openai_client.chat_completion(
            messages=context_messages + [
                {"role": "user", "content": user_message}
            ],
            system_prompt="""You are a helpful AI software architect assistant. 
You're having a conversation with a user about their software project.
Be helpful, ask clarifying questions, and guide them toward a clear problem statement.
If they seem ready to start planning features, suggest they describe what they want to build.""",
            temperature=0.7
        )
        
        assistant_msg = ConversationMessage(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=response["content"],
            timestamp=datetime.now(timezone.utc)
        )
        conversation.messages.append(assistant_msg)
        
        yield StreamEvent(
            type="message_end",
            data={
                "conversation_id": conversation.conversation_id,
                "message": response["content"]
            }
        )
    
    # REMOVED: _infer_action method - replaced with LLM-based RouterAgent
    # All routing decisions are now made by the RouterAgent using LLM intelligence
    # instead of keyword matching. See router_agent.py for the implementation.
    
    def _generate_change_summary(
        self,
        previous_features: List[Feature],
        new_features: List[Feature],
        is_adding: bool,
        is_removing: bool
    ) -> str:
        """Generate a summary of what changed in the feature plan"""
        
        prev_titles = {f.title.lower(): f for f in previous_features}
        new_titles = {f.title.lower(): f for f in new_features}
        
        # Find added, removed, and kept features
        added = [f for f in new_features if f.title.lower() not in prev_titles]
        removed = [f for f in previous_features if f.title.lower() not in new_titles]
        kept_count = len([f for f in new_features if f.title.lower() in prev_titles])
        
        # Generate appropriate message
        if is_adding and added and not removed:
            added_titles = ", ".join([f.title for f in added])
            return f"✅ I've **added {len(added)} new feature(s)** to your plan: **{added_titles}**\n\nYour plan now has **{len(new_features)} total features** ({kept_count} existing + {len(added)} new)."
        elif is_removing and removed:
            removed_titles = ", ".join([f.title for f in removed])
            return f"✅ I've **removed {len(removed)} feature(s)**: {removed_titles}\n\nYour plan now has **{len(new_features)} features**."
        elif added and removed:
            return f"✅ I've updated your plan: **Added {len(added)}** feature(s), **Removed {len(removed)}** feature(s).\n\nYour plan now has **{len(new_features)} total features**."
        elif added and not removed:
            return f"✅ I've added **{len(added)} new feature(s)** to your plan.\n\nYour plan now has **{len(new_features)} total features**."
        else:
            return f"✅ I've updated the feature plan based on your feedback."
    
    def _format_feature_plan_message(self, feature_plan: Dict[str, Any]) -> str:
        """Format feature plan as conversational message"""
        features = feature_plan.get("features", [])
        tech_stack = feature_plan.get("tech_stack", {})
        
        message = f"""Based on your requirements, here's what I propose to build:

**{feature_plan.get('problem_summary', 'Your Application')}**

**Features ({len(features)} total):**
"""
        
        # Group by priority
        high = [f for f in features if f.get("priority") == "high"]
        medium = [f for f in features if f.get("priority") == "medium"]
        low = [f for f in features if f.get("priority") == "low"]
        
        if high:
            message += "\n**High Priority (Must-have):**\n"
            for i, feat in enumerate(high, 1):
                message += f"{i}. **{feat.get('title')}**: {feat.get('description')}\n"
        
        if medium:
            message += "\n**Medium Priority (Important):**\n"
            for i, feat in enumerate(medium, 1):
                message += f"{i}. **{feat.get('title')}**: {feat.get('description')}\n"
        
        if low:
            message += "\n**Low Priority (Nice-to-have):**\n"
            for i, feat in enumerate(low, 1):
                message += f"{i}. **{feat.get('title')}**: {feat.get('description')}\n"
        
        message += f"""
**Tech Stack:**
- Frontend: {tech_stack.get('frontend', 'Next.js 14')}
- Backend: {tech_stack.get('backend', 'Next.js API Routes')}
- Database: {tech_stack.get('database', 'PostgreSQL')}
- Styling: {tech_stack.get('styling', 'Tailwind CSS')}

{feature_plan.get('notes', '')}

**What do you think?** Feel free to:
- Request changes to any features
- Add new features
- Remove features you don't need
- Change priorities
- Or approve to start implementation!
"""
        
        return message
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state"""
        return self.conversations.get(conversation_id)

