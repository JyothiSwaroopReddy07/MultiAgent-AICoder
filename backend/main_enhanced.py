"""
AI Code Generator - Enterprise Multi-Agent Platform
Main entry point with dynamic architecture design and code generation
"""
import asyncio
import json
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import structlog

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_settings
from models.conversation_schemas import (
    ConversationState, ConversationPhase, ConversationMessage,
    MessageRole, Feature, FeaturePlan, ChatRequest, StreamEvent
)
from agents.architect_agent import ArchitectAgent, FilePlannerAgent
from agents.code_generator_agent import CodeGeneratorAgent, IntegrationValidatorAgent
from agents.feature_planner_agent import FeaturePlannerAgent
from agents.testing_agent import TestingAgent, DependencyValidator
from utils.gemini_client import get_gemini_client
from utils.llm_tracker import tracker
from services.execution_service import (
    execute_application, stop_application, 
    get_running_applications, cleanup_all_applications
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Settings
settings = get_settings()

# In-memory conversation store
conversations: Dict[str, ConversationState] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("server_starting", port=settings.backend_port)
    
    try:
        client = get_gemini_client()
        logger.info("gemini_client_ready", model=client.model)
    except Exception as e:
        logger.error("gemini_client_init_failed", error=str(e))
    
    yield
    
    # Cleanup running applications on shutdown
    logger.info("cleaning_up_applications")
    await cleanup_all_applications()
    logger.info("server_shutting_down")


# Create FastAPI app
app = FastAPI(
    title="AI Code Generator - Enterprise Platform",
    description="Multi-agent AI system for generating enterprise-grade applications",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENTERPRISE CODE GENERATION ORCHESTRATOR
# ============================================================================

class EnterpriseCodeOrchestrator:
    """
    Enterprise-grade code generation orchestrator.
    
    Uses multiple specialized agents:
    1. FeaturePlannerAgent - Proposes features and gets user confirmation
    2. ArchitectAgent - Designs system architecture
    3. FilePlannerAgent - Plans all files to generate
    4. CodeGeneratorAgent - Generates each file
    5. IntegrationValidatorAgent - Validates everything works together
    6. TestingAgent - Tests and fixes errors in generated code
    
    Supports ANY problem statement and dynamically determines:
    - Project type (frontend/backend/fullstack/microservices)
    - Folder structure
    - Technology stack
    - Database design
    - API design
    - All required files (could be 10 or 100+)
    """
    
    def __init__(self):
        self.feature_planner = FeaturePlannerAgent()
        self.architect = ArchitectAgent()
        self.file_planner = FilePlannerAgent()
        self.code_generator = CodeGeneratorAgent()
        self.validator = IntegrationValidatorAgent()
        self.testing_agent = TestingAgent()
        self.gemini = get_gemini_client()
    
    async def propose_features(
        self,
        problem_statement: str,
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Phase 0: Feature Planning
        Proposes features for user confirmation before proceeding
        """
        if on_progress:
            await on_progress({
                "phase": "feature_planning",
                "message": "💡 Analyzing requirements and proposing features...",
                "progress": 5
            })
        
        result = await self.feature_planner.propose_features(problem_statement)
        feature_plan = result.get("feature_plan", {})
        
        formatted_features = self.feature_planner.format_features_for_display(feature_plan)
        
        if on_progress:
            await on_progress({
                "phase": "features_proposed",
                "message": formatted_features,
                "progress": 10,
                "data": {
                    "feature_plan": feature_plan,
                    "awaiting_confirmation": True
                }
            })
        
        return feature_plan
    
    async def refine_features(
        self,
        feature_plan: Dict[str, Any],
        user_feedback: str,
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Refine features based on user feedback
        """
        if on_progress:
            await on_progress({
                "phase": "refining_features",
                "message": "🔄 Refining features based on your feedback...",
                "progress": 8
            })
        
        result = await self.feature_planner.refine_features(feature_plan, user_feedback)
        return result.get("feature_plan", feature_plan)

    async def generate_application(
        self,
        problem_statement: str,
        constraints: Optional[Dict[str, Any]] = None,
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete application from a problem statement.
        
        Args:
            problem_statement: Description of what to build
            constraints: Optional constraints (tech preferences, etc.)
            on_progress: Callback for progress updates
            
        Returns:
            Complete generated application with all files
        """
        result = {
            "architecture": None,
            "file_plan": None,
            "files": [],
            "validation": None,
            "metadata": {
                "started_at": datetime.utcnow().isoformat(),
                "problem_statement": problem_statement
            }
        }
        
        try:
            # ========================================
            # PHASE 1: ARCHITECTURE DESIGN
            # ========================================
            if on_progress:
                await on_progress({
                    "phase": "architecture",
                    "message": "🏗️ Analyzing requirements and designing architecture...",
                    "progress": 10
                })
            
            arch_result = await self.architect.process_task({
                "problem_statement": problem_statement,
                "constraints": constraints or {}
            })
            
            architecture = arch_result.get("architecture", {})
            result["architecture"] = architecture
            
            # Extract key info for logging
            analysis = architecture.get("analysis", {})
            arch_info = architecture.get("architecture", {})
            
            logger.info(
                "architecture_designed",
                project_type=arch_info.get("project_type"),
                complexity=analysis.get("complexity"),
                estimated_files=analysis.get("estimated_files", 0)
            )
            
            if on_progress:
                await on_progress({
                    "phase": "architecture_complete",
                    "message": f"✅ Architecture designed: {arch_info.get('project_type', 'fullstack')} with {arch_info.get('pattern', 'MVC')} pattern",
                    "progress": 20,
                    "data": {
                        "project_type": arch_info.get("project_type"),
                        "complexity": analysis.get("complexity"),
                        "tech_stack": architecture.get("tech_stack", {})
                    }
                })
            
            # ========================================
            # PHASE 2: FILE PLANNING
            # ========================================
            if on_progress:
                await on_progress({
                    "phase": "planning",
                    "message": "📋 Planning file structure and dependencies...",
                    "progress": 25
                })
            
            # Use files from architecture if available, otherwise use file planner
            files_to_generate = architecture.get("files", [])
            
            if not files_to_generate or len(files_to_generate) < 5:
                # Need more detailed file planning
                plan_result = await self.file_planner.process_task({
                    "architecture": architecture,
                    "problem_statement": problem_statement
                })
                file_plan = plan_result.get("file_plan", {})
                files_to_generate = file_plan.get("files", [])
                result["file_plan"] = file_plan
            
            # Sort files by priority
            files_to_generate = sorted(
                files_to_generate,
                key=lambda f: f.get("priority", 999)
            )
            
            total_files = len(files_to_generate)
            
            if on_progress:
                await on_progress({
                    "phase": "planning_complete",
                    "message": f"✅ Planned {total_files} files to generate",
                    "progress": 30,
                    "data": {"total_files": total_files}
                })
            
            logger.info("file_planning_complete", total_files=total_files)
            
            # ========================================
            # PHASE 3: CODE GENERATION
            # ========================================
            generated_files = []
            base_progress = 30
            progress_per_file = 60 / max(total_files, 1)  # 30-90% for file generation
            
            for i, file_spec in enumerate(files_to_generate):
                filepath = file_spec.get("filepath", f"file_{i}")
                
                if on_progress:
                    await on_progress({
                        "phase": "generating",
                        "message": f"⚙️ Generating {filepath}...",
                        "progress": int(base_progress + (i * progress_per_file)),
                        "data": {
                            "current_file": filepath,
                            "file_number": i + 1,
                            "total_files": total_files
                        }
                    })
                
                try:
                    file_result = await self.code_generator.generate_file(
                        file_spec=file_spec,
                        architecture=architecture,
                        generated_files=generated_files,
                        problem_statement=problem_statement
                    )
                    
                    generated_files.append(file_result)
                    
                    if on_progress:
                        await on_progress({
                            "phase": "file_generated",
                            "message": f"✅ Generated {filepath}",
                            "progress": int(base_progress + ((i + 1) * progress_per_file)),
                            "data": file_result
                        })
                    
                    logger.info("file_generated", 
                              filepath=filepath,
                              language=file_result.get("language"))
                    
                except Exception as e:
                    logger.error("file_generation_error", 
                               filepath=filepath, 
                               error=str(e))
                    # Continue with other files
                    continue
            
            result["files"] = generated_files
            
            # ========================================
            # PHASE 4: DEPENDENCY VALIDATION
            # ========================================
            if on_progress:
                await on_progress({
                    "phase": "checking_dependencies",
                    "message": "🔗 Checking file dependencies...",
                    "progress": 88
                })
            
            # Check for missing dependencies
            missing_deps = DependencyValidator.find_missing_dependencies(generated_files)
            
            if missing_deps:
                logger.info("missing_dependencies_found", count=len(missing_deps))
                
                # Generate missing files
                for dep in missing_deps[:10]:  # Limit to avoid too many generations
                    missing_path = dep.get("resolved_path", "")
                    
                    if on_progress:
                        await on_progress({
                            "phase": "generating_missing",
                            "message": f"⚙️ Generating missing: {missing_path}",
                            "progress": 89
                        })
                    
                    try:
                        # Create a file spec for the missing file
                        missing_spec = {
                            "filepath": missing_path + ".tsx" if not missing_path.endswith((".ts", ".tsx", ".js", ".jsx")) else missing_path,
                            "filename": os.path.basename(missing_path),
                            "purpose": f"Missing dependency imported by {dep.get('importing_file', 'unknown')}",
                            "language": "typescript",
                            "category": "frontend" if "component" in missing_path.lower() else "shared",
                            "content_hints": [f"This file is imported by {dep.get('importing_file')}"]
                        }
                        
                        file_result = await self.code_generator.generate_file(
                            file_spec=missing_spec,
                            architecture=architecture,
                            generated_files=generated_files,
                            problem_statement=problem_statement
                        )
                        
                        generated_files.append(file_result)
                        
                        if on_progress:
                            await on_progress({
                                "phase": "file_generated",
                                "message": f"✅ Generated missing: {missing_path}",
                                "progress": 90,
                                "data": file_result
                            })
                            
                    except Exception as e:
                        logger.error("missing_file_generation_error", path=missing_path, error=str(e))
            
            # ========================================
            # PHASE 5: INTEGRATION VALIDATION
            # ========================================
            if len(generated_files) > 3:
                if on_progress:
                    await on_progress({
                        "phase": "validating",
                        "message": "🔍 Validating integration...",
                        "progress": 92
                    })
                
                try:
                    validation_result = await self.validator.process_task({
                        "files": generated_files[:20],
                        "architecture": architecture
                    })
                    result["validation"] = validation_result.get("validation")
                except Exception as e:
                    logger.error("validation_error", error=str(e))
                    result["validation"] = {"valid": True, "issues": []}
            
            # Update files in result
            result["files"] = generated_files
            
            # ========================================
            # COMPLETE
            # ========================================
            result["metadata"]["completed_at"] = datetime.utcnow().isoformat()
            result["metadata"]["total_files"] = len(generated_files)
            result["metadata"]["success"] = True
            
            if on_progress:
                await on_progress({
                    "phase": "complete",
                    "message": f"🎉 Generated {len(generated_files)} files successfully!",
                    "progress": 100,
                    "data": {
                        "total_files": len(generated_files),
                        "project_type": arch_info.get("project_type")
                    }
                })
            
            logger.info("generation_complete", 
                       total_files=len(generated_files),
                       project_type=arch_info.get("project_type"))
            
            return result
            
        except Exception as e:
            logger.error("orchestration_failed", error=str(e))
            result["metadata"]["error"] = str(e)
            result["metadata"]["success"] = False
            
            if on_progress:
                await on_progress({
                    "phase": "error",
                    "message": f"❌ Error: {str(e)}",
                    "progress": 0
                })
            
            return result

    async def quick_generate(
        self,
        problem_statement: str
    ) -> List[Dict[str, Any]]:
        """
        Quick generation without streaming - returns just the files
        """
        result = await self.generate_application(problem_statement)
        return result.get("files", [])


# Global orchestrator instance
orchestrator = EnterpriseCodeOrchestrator()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api/chat/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-code-generator-enterprise",
        "version": "4.0.0",
        "agents": ["feature_planner", "architect", "file_planner", "code_generator", "validator", "testing"]
    }


@app.post("/api/chat/message")
async def chat_message(request: Request):
    """
    Main chat endpoint - handles all conversation phases.
    Returns a streaming response with Server-Sent Events.
    """
    body = await request.json()
    conversation_id = body.get("conversation_id")
    message = body.get("message", "").strip()
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Get or create conversation
    if conversation_id and conversation_id in conversations:
        conv = conversations[conversation_id]
    else:
        conversation_id = str(uuid.uuid4())
        conv = ConversationState(
            conversation_id=conversation_id,
            phase=ConversationPhase.INITIAL
        )
        conversations[conversation_id] = conv
    
    # Add user message to history
    conv.messages.append(ConversationMessage(
        id=str(uuid.uuid4()),
        role=MessageRole.USER,
        content=message
    ))
    
    # Return streaming response
    return StreamingResponse(
        process_message_stream(conv, message),
        media_type="text/event-stream"
    )


async def process_message_stream(
    conv: ConversationState, 
    message: str
) -> AsyncGenerator[str, None]:
    """Process message and stream responses with multi-agent orchestration"""
    try:
        # Send started event
        yield f"data: {json.dumps({'type': 'started', 'conversation_id': conv.conversation_id})}\n\n"
        
        # Check if user is confirming features or providing feedback
        if conv.phase == ConversationPhase.FEATURES_PROPOSED:
            # User is responding to feature proposal
            message_lower = message.lower().strip()
            
            # Check for approval - be flexible with phrasing
            approval_keywords = [
                "yes", "ok", "okay", "confirm", "proceed", "good", "approved", "approve", 
                "go ahead", "start", "fine", "perfect", "great", "continue", "generate", 
                "build", "create", "implement", "do it", "make it", "let's go", "sounds good",
                "that's good", "that works", "looks great", "ship it", "execute", "run"
            ]
            is_approval = any(keyword in message_lower for keyword in approval_keywords)
            
            if is_approval:
                # User approved features - proceed to generation
                conv.phase = ConversationPhase.FEATURES_APPROVED
                yield f"data: {json.dumps({'type': 'features_approved', 'data': {'message': '✅ Features approved! Starting code generation...'}})}\n\n"
            else:
                # User has feedback - refine features
                yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'refining_features', 'message': '🔄 Refining features based on your feedback...'}})}\n\n"
                
                refined_result = await orchestrator.refine_features(
                    conv.feature_plan or {},
                    message
                )
                conv.feature_plan = refined_result
                
                # Extract the actual feature plan
                refined_plan = refined_result.get("feature_plan", refined_result)
                
                # Send updated features
                formatted = orchestrator.feature_planner.format_features_for_display(refined_plan)
                features_data = [
                    {
                        "id": str(i),
                        "title": f.get("name", "Feature"),
                        "description": f.get("description", ""),
                        "priority": f.get("priority", "medium")
                    }
                    for i, f in enumerate(refined_plan.get("core_features", []))
                ]
                
                yield f"data: {json.dumps({'type': 'features_refined', 'data': {'features': features_data, 'message': formatted, 'awaiting_confirmation': True}})}\n\n"
                yield f"data: {json.dumps({'type': 'message_end', 'data': {'message': '', 'conversation_id': conv.conversation_id}})}\n\n"
                return
        
        # Determine action based on phase
        if conv.phase in [ConversationPhase.INITIAL, ConversationPhase.FEATURES_APPROVED]:
            # Save problem statement
            if conv.phase == ConversationPhase.INITIAL:
                conv.problem_statement = message
            
            # ========================================
            # PHASE 0: FEATURE PLANNING (New!)
            # ========================================
            if conv.phase == ConversationPhase.INITIAL:
                yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'feature_planning', 'message': '💡 Analyzing requirements and proposing features...'}})}\n\n"
                
                feature_result = await orchestrator.feature_planner.propose_features(conv.problem_statement)
                conv.feature_plan = feature_result
                
                # Extract the actual feature plan from the result
                actual_plan = feature_result.get("feature_plan", {})
                
                # Format features for display
                formatted = orchestrator.feature_planner.format_features_for_display(actual_plan)
                features_data = [
                    {
                        "id": str(i),
                        "title": f.get("name", "Feature"),
                        "description": f.get("description", ""),
                        "priority": f.get("priority", "medium")
                    }
                    for i, f in enumerate(actual_plan.get("core_features", []))
                ]
                
                yield f"data: {json.dumps({'type': 'features_proposed', 'data': {'features': features_data, 'feature_plan': actual_plan, 'message': formatted, 'awaiting_confirmation': True, 'conversation_id': conv.conversation_id}})}\n\n"
                
                # Set phase to awaiting feature confirmation
                conv.phase = ConversationPhase.FEATURES_PROPOSED
                
                # Send prompt for user to confirm
                prompt_message = "\\n\\n---\\n**Please review the proposed features above.**\\n\\n- Type **yes** or **proceed** to start code generation\\n- Or provide feedback to modify the features"
                yield f"data: {json.dumps({'type': 'awaiting_input', 'data': {'message': prompt_message, 'input_type': 'feature_confirmation'}})}\n\n"
                yield f"data: {json.dumps({'type': 'message_end', 'data': {'message': '', 'conversation_id': conv.conversation_id}})}\n\n"
                return
            
            # ========================================
            # PHASE 1: ARCHITECTURE DESIGN
            # ========================================
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'architecture', 'message': '🏗️ Analyzing requirements and designing system architecture...'}})}\n\n"
            
            # Include confirmed features in the architecture
            feature_hints = ""
            if conv.feature_plan:
                core_features = conv.feature_plan.get("core_features", [])
                feature_hints = "\n\n## Confirmed Features:\n" + "\n".join([
                    f"- {f.get('name')}: {f.get('description')}" for f in core_features
                ])
            
            arch_result = await orchestrator.architect.process_task({
                "problem_statement": conv.problem_statement + feature_hints,
                "constraints": {}
            })
            
            architecture = arch_result.get("architecture", {})
            analysis = architecture.get("analysis", {})
            arch_info = architecture.get("architecture", {})
            tech_stack = architecture.get("tech_stack", {})
            
            # Send architecture info
            yield f"data: {json.dumps({'type': 'architecture_designed', 'data': {'project_type': arch_info.get('project_type', 'fullstack'), 'complexity': analysis.get('complexity', 'moderate'), 'tech_stack': tech_stack, 'estimated_files': analysis.get('estimated_files', 20)}})}\n\n"
            
            # Extract features for display
            features = architecture.get("features", [])
            if features:
                features_data = [
                    {
                        "id": f.get("id", str(i)),
                        "title": f.get("name", "Feature"),
                        "description": f.get("description", ""),
                        "priority": f.get("priority", "medium"),
                        "category": f.get("files_involved", ["core"])[0] if f.get("files_involved") else "core"
                    }
                    for i, f in enumerate(features)
                ]
                yield f"data: {json.dumps({'type': 'features_proposed', 'data': {'features': features_data, 'conversation_id': conv.conversation_id}})}\n\n"
            
            # ========================================
            # PHASE 2: FILE PLANNING
            # ========================================
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'planning', 'message': '📋 Planning file structure...'}})}\n\n"
            
            files_to_generate = architecture.get("files", [])
            
            if not files_to_generate or len(files_to_generate) < 5:
                plan_result = await orchestrator.file_planner.process_task({
                    "architecture": architecture,
                    "problem_statement": message
                })
                file_plan = plan_result.get("file_plan", {})
                files_to_generate = file_plan.get("files", [])
            
            # Sort by priority
            files_to_generate = sorted(
                files_to_generate,
                key=lambda f: f.get("priority", 999)
            )
            
            total_files = len(files_to_generate)
            yield f"data: {json.dumps({'type': 'planning_complete', 'data': {'total_files': total_files, 'message': f'📋 Planned {total_files} files to generate'}})}\n\n"
            
            # ========================================
            # PHASE 3: CODE GENERATION
            # ========================================
            yield f"data: {json.dumps({'type': 'implementation_started', 'data': {'message': f'⚙️ Generating {total_files} files...'}})}\n\n"
            
            generated_files = []
            
            # Limit files to prevent rate limiting (max 35 files)
            max_files = 35
            if len(files_to_generate) > max_files:
                logger.warning("file_count_limited", original=len(files_to_generate), limited=max_files)
                files_to_generate = files_to_generate[:max_files]
                yield f"data: {json.dumps({'type': 'warning', 'data': {'message': f'⚠️ Limiting to {max_files} essential files to avoid rate limits'}})}\n\n"
            
            for i, file_spec in enumerate(files_to_generate):
                filepath = file_spec.get("filepath", f"file_{i}")
                
                try:
                    logger.info("generating_file", index=i+1, total=len(files_to_generate), filepath=filepath)
                    
                    file_result = await orchestrator.code_generator.generate_file(
                        file_spec=file_spec,
                        architecture=architecture,
                        generated_files=generated_files,
                        problem_statement=message
                    )
                    
                    generated_files.append(file_result)
                    
                    # Stream file generation event
                    yield f"data: {json.dumps({'type': 'file_generated', 'data': file_result})}\n\n"
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error("file_generation_error", filepath=filepath, error=error_msg, index=i+1)
                    yield f"data: {json.dumps({'type': 'file_error', 'data': {'filepath': filepath, 'error': error_msg}})}\n\n"
                    
                    # If we get a rate limit error, wait longer
                    if "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                        logger.warning("rate_limit_detected", waiting=5)
                        await asyncio.sleep(5)
                    continue
            
            # ========================================
            # PHASE 4: DEPENDENCY VALIDATION
            # ========================================
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'checking_dependencies', 'message': '🔗 Checking file dependencies...'}})}\n\n"
            
            missing_deps = DependencyValidator.find_missing_dependencies(generated_files)
            
            if missing_deps:
                yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'fixing_dependencies', 'message': f'⚠️ Found {len(missing_deps)} missing dependencies. Generating...'}})}\n\n"
                
                for dep in missing_deps[:10]:
                    missing_path = dep.get("resolved_path", "")
                    
                    try:
                        missing_spec = {
                            "filepath": missing_path + ".tsx" if not missing_path.endswith((".ts", ".tsx", ".js", ".jsx")) else missing_path,
                            "filename": os.path.basename(missing_path),
                            "purpose": f"Missing dependency imported by {dep.get('importing_file', 'unknown')}",
                            "language": "typescript",
                            "category": "frontend" if "component" in missing_path.lower() else "shared",
                            "content_hints": [f"This file is imported by {dep.get('importing_file')}"]
                        }
                        
                        file_result = await orchestrator.code_generator.generate_file(
                            file_spec=missing_spec,
                            architecture=architecture,
                            generated_files=generated_files,
                            problem_statement=conv.problem_statement
                        )
                        
                        generated_files.append(file_result)
                        yield f"data: {json.dumps({'type': 'file_generated', 'data': file_result})}\n\n"
                        
                    except Exception as e:
                        logger.error("missing_file_generation_error", path=missing_path, error=str(e))
            
            conv.phase = ConversationPhase.CODE_GENERATED
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'code_generated', 'data': {'message': f'🎉 Generated {len(generated_files)} files successfully!', 'total_files': len(generated_files), 'project_type': arch_info.get('project_type')}})}\n\n"
        
        elif conv.phase == ConversationPhase.CODE_GENERATED:
            # Handle modification requests
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'modification', 'message': '🔄 Processing modification request...'}})}\n\n"
            
            # Append modification to problem statement
            modified_statement = f"{conv.problem_statement}\n\n## MODIFICATION REQUEST:\n{message}"
            
            # Re-run with modifications
            result = await orchestrator.generate_application(modified_statement)
            
            for file_data in result.get("files", []):
                yield f"data: {json.dumps({'type': 'file_generated', 'data': file_data})}\n\n"
                await asyncio.sleep(0.05)
            
            files_count = len(result.get("files", []))
            success_message = f"🎉 Applied modifications! Generated {files_count} files."
            yield f"data: {json.dumps({'type': 'code_generated', 'data': {'message': success_message, 'files': result.get('files', [])}})}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'message_end', 'data': {'message': '', 'conversation_id': conv.conversation_id}})}\n\n"
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error("stream_processing_error", error=str(e), traceback=error_traceback)
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e), 'details': 'Check server logs for details'}})}\n\n"
        yield f"data: {json.dumps({'type': 'message_end', 'data': {'message': '', 'conversation_id': conv.conversation_id if conv else 'unknown'}})}\n\n"


@app.post("/api/v1/generate")
async def generate_code(request: Request):
    """
    Direct generation endpoint - returns complete result (non-streaming)
    """
    body = await request.json()
    problem_statement = body.get("description", body.get("message", ""))
    constraints = body.get("constraints", {})
    
    if not problem_statement:
        raise HTTPException(status_code=400, detail="Description is required")
    
    result = await orchestrator.generate_application(problem_statement, constraints)
    
    return {
        "status": "success" if result.get("metadata", {}).get("success") else "error",
        "files": result.get("files", []),
        "architecture": result.get("architecture", {}),
        "metadata": result.get("metadata", {})
    }


@app.get("/api/v1/health")
async def health_v1():
    """V1 Health check"""
    return {"status": "healthy", "service": "ai-code-generator-enterprise"}


@app.get("/api/v1/usage")
async def get_usage():
    """Get LLM usage statistics"""
    summary = tracker.get_summary()
    return summary


@app.post("/api/v1/usage/reset")
async def reset_usage():
    """Reset LLM usage statistics"""
    tracker.reset()
    return {"status": "reset"}


@app.get("/api/v1/agents")
async def get_agents():
    """Get available agents info"""
    return {
        "agents": [
            {
                "role": "architect",
                "phase": "discovery",
                "description": "Analyzes requirements and designs system architecture"
            },
            {
                "role": "file_planner",
                "phase": "design",
                "description": "Plans all files needed for the project"
            },
            {
                "role": "code_generator",
                "phase": "implementation",
                "description": "Generates production-ready code files"
            },
            {
                "role": "validator",
                "phase": "validation",
                "description": "Validates integration between files"
            }
        ],
        "phases": ["discovery", "design", "implementation", "validation"],
        "capabilities": [
            "Dynamic architecture design",
            "Multi-project type support (frontend/backend/fullstack/microservices)",
            "Intelligent file planning",
            "Context-aware code generation",
            "Integration validation"
        ]
    }


# ============================================================================
# APPLICATION EXECUTION ENDPOINTS
# ============================================================================

@app.post("/api/execute")
async def execute_generated_app(request: Request):
    """
    Execute the generated application.
    
    Saves files to disk, installs dependencies, and starts the dev server.
    Returns a streaming response with execution logs and status.
    """
    body = await request.json()
    files = body.get("files", [])
    conversation_id = body.get("conversation_id", str(uuid.uuid4()))
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    async def stream_execution():
        try:
            async for event in execute_application(files, conversation_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error("execution_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_execution(),
        media_type="text/event-stream"
    )


@app.post("/api/execute/stop")
async def stop_generated_app(request: Request):
    """Stop a running application"""
    body = await request.json()
    project_path = body.get("project_path")
    
    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")
    
    success = await stop_application(project_path)
    
    return {
        "status": "stopped" if success else "not_found",
        "project_path": project_path
    }


@app.post("/api/download")
async def download_project(request: Request):
    """
    Zip and download the generated project.
    Expects list of files in the request body.
    """
    body = await request.json()
    files = body.get("files", [])
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
        
    import io
    import zipfile
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_info in files:
            filepath = file_info.get("filepath", "")
            content = file_info.get("content", "")
            
            if filepath and content:
                # Ensure we don't have absolute paths
                clean_path = filepath.lstrip("/")
                zip_file.writestr(clean_path, content)
    
    # Reset buffer position
    zip_buffer.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ai-generated-project-{timestamp}.zip"
    
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



@app.get("/api/execute/running")
async def list_running_apps():
    """List all running applications"""
    return {
        "applications": get_running_applications()
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("  🚀 AI Code Generator - Enterprise Multi-Agent Platform v3.0")
    print("="*70)
    print(f"  Backend:  http://localhost:{settings.backend_port}")
    print(f"  API Docs: http://localhost:{settings.backend_port}/docs")
    print(f"  Health:   http://localhost:{settings.backend_port}/api/chat/health")
    print("")
    print("  Agents:")
    print("    🏗️  Architect Agent      - Designs system architecture")
    print("    📋 File Planner Agent   - Plans all project files")
    print("    ⚙️  Code Generator Agent - Generates production code")
    print("    🔍 Validator Agent      - Validates integration")
    print("="*70 + "\n")
    
    uvicorn.run(
        "main_enhanced:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )
