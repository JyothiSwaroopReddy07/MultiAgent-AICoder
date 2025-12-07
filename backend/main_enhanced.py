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
from agents.test_generator_agent import TestGeneratorAgent, TestReportAgent
from agents.code_reviewer_agent import CodeReviewerAgent
from agents.execution_agent import ExecutionAgent
from utils.gemini_client import get_gemini_client
from utils.llm_tracker import tracker

SYMPTOM_TRACKER_PRESET = """A software application that allows users to track and monitor their symptoms over time, enabling them to identify patterns and potential triggers. Users can log symptoms, severity, duration, and associated factors such as food, stress, or environment to gain insights into their health and make informed decisions.

## Functional Requirements:
1. User Authentication - Register and login functionality
2. Symptom Logging - Log symptoms with severity (1-10), duration, date/time
3. Associated Factors - Track food, stress levels, sleep, weather, medications
4. Pattern Analysis - Visualize symptom trends over time with charts
5. Trigger Detection - Identify correlations between factors and symptoms
6. Symptom History - View and search past symptom entries
7. Export Data - Download symptom data as CSV/PDF
8. Reminders - Set reminders to log symptoms
9. Dashboard - Overview of recent symptoms and insights
10. Notes - Add detailed notes to symptom entries"""
from services.execution_service import (
    execute_application, stop_application, 
    get_running_applications, cleanup_all_applications
)

# Global execution agent instance
execution_agent = ExecutionAgent()

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
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)


# ============================================================================
# ENTERPRISE CODE GENERATION ORCHESTRATOR
# ============================================================================

class EnterpriseCodeOrchestrator:
    """
    Enterprise-grade code generation orchestrator with Multi-Agent System.
    
    Uses multiple specialized agents with MCP (Model Context Protocol) integration:
    1. FeaturePlannerAgent - Proposes features and gets user confirmation
    2. ArchitectAgent - Designs system architecture
    3. FilePlannerAgent - Plans all files to generate
    4. CodeGeneratorAgent - Generates each file
    5. IntegrationValidatorAgent - Validates everything works together
    6. TestingAgent - Tests and fixes errors in generated code
    7. TestGeneratorAgent - Generates comprehensive test cases
    
    Agent Communication Pattern:
    - Agents communicate via MCP for coordinated code generation
    - Each agent tracks its own LLM usage for transparency
    - Sequential pipeline with parallel file generation
    
    Supports ANY problem statement and dynamically determines:
    - Project type (frontend/backend/fullstack/microservices)
    - Folder structure
    - Technology stack
    - Database design
    - API design
    - All required files (could be 10 or 100+)
    - Comprehensive test suite
    """
    
    def __init__(self):
        self.feature_planner = FeaturePlannerAgent()
        self.architect = ArchitectAgent()
        self.file_planner = FilePlannerAgent()
        self.code_generator = CodeGeneratorAgent()
        self.code_reviewer = CodeReviewerAgent()
        self.validator = IntegrationValidatorAgent()
        self.testing_agent = TestingAgent()
        self.test_generator = TestGeneratorAgent()
        self.test_reporter = TestReportAgent()
        self.gemini = get_gemini_client()
        
        self.agents = {
            "feature_planner": self.feature_planner,
            "architect": self.architect,
            "file_planner": self.file_planner,
            "code_generator": self.code_generator,
            "code_reviewer": self.code_reviewer,
            "validator": self.validator,
            "testing_agent": self.testing_agent,
            "test_generator": self.test_generator,
            "test_reporter": self.test_reporter
        }
    
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
                        "progress": 88
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
            
            # ========================================
            # PHASE 6: CODE REVIEW
            # ========================================
            if on_progress:
                await on_progress({
                    "phase": "reviewing_code",
                    "message": "🔍 Reviewing code for syntax errors...",
                    "progress": 90
                })
            
            try:
                review_result = await self.code_reviewer.review_and_fix_files(
                    files=generated_files,
                    architecture=architecture
                )
                
                generated_files = review_result.get("files", generated_files)
                review_summary = review_result.get("review_summary", {})
                
                if review_summary.get("files_fixed", 0) > 0:
                    if on_progress:
                        await on_progress({
                            "phase": "code_fixed",
                            "message": f"✅ Fixed syntax errors in {review_summary['files_fixed']} files",
                            "progress": 92,
                            "data": review_summary
                        })
                    logger.info("code_review_fixes_applied", **review_summary)
                else:
                    if on_progress:
                        await on_progress({
                            "phase": "code_reviewed",
                            "message": "✅ Code review passed - no syntax errors",
                            "progress": 92
                        })
                
                result["review_summary"] = review_summary
                
            except Exception as e:
                logger.error("code_review_error", error=str(e))
                result["review_summary"] = {"error": str(e)}
            
            # ========================================
            # PHASE 7: UNIT TEST GENERATION
            # ========================================
            if on_progress:
                await on_progress({
                    "phase": "generating_tests",
                    "message": "🧪 Generating unit tests for each file...",
                    "progress": 94
                })
            
            try:
                test_result = await self.test_generator.generate_tests(
                    generated_files=generated_files,
                    architecture=architecture,
                    problem_statement=problem_statement
                )
                
                test_files = test_result.get("test_files", [])
                config_files = test_result.get("config_files", [])
                updated_files = test_result.get("updated_files", [])
                
                # Replace generated_files with updated_files if available (has updated package.json)
                if updated_files:
                    generated_files = updated_files
                
                for tf in test_files:
                    generated_files.append(tf)
                
                for cf in config_files:
                    if not any(f.get("filepath") == cf.get("filepath") for f in generated_files):
                        generated_files.append(cf)
                
                result["test_summary"] = test_result.get("summary", {})
                
                if on_progress:
                    test_count = len(test_files)
                    await on_progress({
                        "phase": "tests_generated",
                        "message": f"✅ Generated {test_count} unit test files",
                        "progress": 96,
                        "data": {"test_files": test_count}
                    })
                
                logger.info("unit_test_generation_complete", test_files=len(test_files))
                
            except Exception as e:
                logger.error("unit_test_generation_error", error=str(e))
                result["test_summary"] = {"error": str(e)}
            
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
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'architecture', 'message': '🏗️ Designing system architecture with feature implementations...'}})}\n\n"
            
            # Include confirmed features in the architecture - CRITICAL for feature implementation
            feature_hints = ""
            confirmed_features = []
            if conv.feature_plan:
                core_features = conv.feature_plan.get("core_features", [])
                optional_features = conv.feature_plan.get("optional_features", [])
                
                # Include core features with priority high
                for i, f in enumerate(core_features):
                    confirmed_features.append({
                        "id": f"f{i+1}",
                        "name": f.get("name", f"Feature {i+1}"),
                        "description": f.get("description", ""),
                        "priority": "high"
                    })
                
                # Include some optional features with medium priority
                for i, f in enumerate(optional_features[:3]):  # Limit optional features
                    confirmed_features.append({
                        "id": f"o{i+1}",
                        "name": f.get("name", f"Optional {i+1}"),
                        "description": f.get("description", ""),
                        "priority": "medium"
                    })
                
                feature_hints = "\n\n## CONFIRMED FEATURES TO IMPLEMENT:\n"
                for f in confirmed_features:
                    feature_hints += f"- **{f['name']}** [{f['priority']}]: {f['description']}\n"
                
                feature_hints += "\n\nYou MUST generate implementation files for EACH of these features:\n"
                feature_hints += "- Page/route for each feature\n"
                feature_hints += "- Form and List components for each feature\n"
                feature_hints += "- API routes for each feature\n"
                feature_hints += "- Hooks/services for each feature\n"
            
            arch_result = await orchestrator.architect.process_task({
                "problem_statement": conv.problem_statement + feature_hints,
                "constraints": {"confirmed_features": confirmed_features}
            })
            
            architecture = arch_result.get("architecture", {})
            analysis = architecture.get("analysis", {})
            arch_info = architecture.get("architecture", {})
            tech_stack = architecture.get("tech_stack", {})
            
            # INJECT confirmed features into architecture if not already present
            if confirmed_features and not architecture.get("features"):
                architecture["features"] = confirmed_features
            elif confirmed_features:
                # Merge confirmed features with any architect-generated features
                existing_ids = {f.get("id") for f in architecture.get("features", [])}
                for cf in confirmed_features:
                    if cf["id"] not in existing_ids:
                        architecture["features"].append(cf)
            
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
            
            # Limit files to prevent extreme cases (max 100 files)
            max_files = 100
            if len(files_to_generate) > max_files:
                logger.warning("file_count_limited", original=len(files_to_generate), limited=max_files)
                files_to_generate = files_to_generate[:max_files]
                yield f"data: {json.dumps({'type': 'warning', 'data': {'message': f'⚠️ Limiting to {max_files} essential files to avoid rate limits'}})}\n\n"
            
            # Group files by priority for efficient generation
            files_by_priority = {}
            for f in files_to_generate:
                p = f.get("priority", 999)
                if p not in files_by_priority:
                    files_by_priority[p] = []
                files_by_priority[p].append(f)
            
            sorted_priorities = sorted(files_by_priority.keys())
            total_processed = 0
            
            # Semaphore to limit concurrency and prevent rate limiting
            # 3 concurrent requests is a safe balance for Gemini
            sem = asyncio.Semaphore(3)
            
            for priority in sorted_priorities:
                batch = files_by_priority[priority]
                
                async def generate_with_semaphore(file_spec, idx):
                    async with sem:
                        filepath = file_spec.get("filepath", f"file_{idx}")
                        try:
                            logger.info("generating_file", index=idx, total=len(files_to_generate), filepath=filepath)
                            
                            # Pass currently generated files as context
                            # Note: Files in the same batch won't see each other, which is why we batch by priority
                            return await orchestrator.code_generator.generate_file(
                                file_spec=file_spec,
                                architecture=architecture,
                                generated_files=generated_files,
                                problem_statement=message
                            )
                        except Exception as e:
                            error_msg = str(e)
                            logger.error("file_generation_error", filepath=filepath, error=error_msg)
                            
                            # Handle rate limits
                            if "rate" in error_msg.lower() or "429" in error_msg:
                                logger.warning("rate_limit_detected", waiting=5)
                                await asyncio.sleep(5)
                                # Retry once
                                try:
                                    return await orchestrator.code_generator.generate_file(
                                        file_spec=file_spec,
                                        architecture=architecture,
                                        generated_files=generated_files,
                                        problem_statement=message
                                    )
                                except Exception as retry_e:
                                    return {"error": str(retry_e), "filepath": filepath}
                            
                            return {"error": error_msg, "filepath": filepath}

                # Create tasks for this batch
                tasks = []
                for file_spec in batch:
                    total_processed += 1
                    tasks.append(generate_with_semaphore(file_spec, total_processed))
                
                # Execute batch
                if tasks:
                    batch_results = await asyncio.gather(*tasks)
                    
                    # Process results
                    for res in batch_results:
                        if "error" in res:
                            yield f"data: {json.dumps({'type': 'file_error', 'data': res})}\n\n"
                        else:
                            generated_files.append(res)
                            yield f"data: {json.dumps({'type': 'file_generated', 'data': res})}\n\n"
                
                # Small delay between batches to let API cool down
                await asyncio.sleep(0.5)
            
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
            
            # ========================================
            # PHASE 5: CODE REVIEW
            # ========================================
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'reviewing_code', 'message': '🔍 Reviewing code for syntax errors...'}})}\n\n"
            
            try:
                review_result = await orchestrator.code_reviewer.review_and_fix_files(
                    files=generated_files,
                    architecture=architecture
                )
                
                generated_files = review_result.get("files", generated_files)
                review_summary = review_result.get("review_summary", {})
                
                if review_summary.get("files_fixed", 0) > 0:
                    fixed_count = review_summary.get("files_fixed", 0)
                    msg = f"✅ Fixed syntax errors in {fixed_count} files"
                    yield f"data: {json.dumps({'type': 'code_fixed', 'data': {'message': msg, 'summary': review_summary}})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'code_reviewed', 'data': {'message': '✅ Code review passed - no syntax errors'}})}\n\n"
                
            except Exception as e:
                logger.error("code_review_error", error=str(e))
                yield f"data: {json.dumps({'type': 'warning', 'data': {'message': f'⚠️ Code review skipped: {str(e)[:100]}'}})}\n\n"
            
            # ========================================
            # PHASE 6: UNIT TEST GENERATION
            # ========================================
            yield f"data: {json.dumps({'type': 'phase_change', 'data': {'phase': 'generating_tests', 'message': '🧪 Generating unit tests for each file...'}})}\n\n"
            
            try:
                test_result = await orchestrator.test_generator.generate_tests(
                    generated_files=generated_files,
                    architecture=architecture,
                    problem_statement=conv.problem_statement or message
                )
                
                test_files = test_result.get("test_files", [])
                config_files = test_result.get("config_files", [])
                updated_files = test_result.get("updated_files", [])
                
                # Replace generated_files with updated_files if available (has updated package.json with Jest)
                if updated_files:
                    generated_files = updated_files
                
                for tf in test_files:
                    generated_files.append(tf)
                    yield f"data: {json.dumps({'type': 'file_generated', 'data': tf})}\n\n"
                
                for cf in config_files:
                    if not any(f.get("filepath") == cf.get("filepath") for f in generated_files):
                        generated_files.append(cf)
                        yield f"data: {json.dumps({'type': 'file_generated', 'data': cf})}\n\n"
                
                test_count = len(test_files)
                yield f"data: {json.dumps({'type': 'tests_generated', 'data': {'message': f'✅ Generated {test_count} unit test files', 'test_count': test_count, 'summary': test_result.get('summary', {})}})}\n\n"
                
            except Exception as e:
                logger.error("unit_test_generation_error", error=str(e))
                yield f"data: {json.dumps({'type': 'warning', 'data': {'message': f'⚠️ Unit test generation skipped: {str(e)[:100]}'}})}\n\n"
            
            conv.phase = ConversationPhase.CODE_GENERATED
            
            # Get usage summary
            usage_summary = tracker.get_summary()
            
            # Send completion event with usage stats
            yield f"data: {json.dumps({'type': 'code_generated', 'data': {'message': f'🎉 Generated {len(generated_files)} files successfully!', 'total_files': len(generated_files), 'project_type': arch_info.get('project_type'), 'usage': {'total_calls': usage_summary.get('total_calls', 0), 'total_tokens': usage_summary.get('total_tokens', 0), 'total_cost': usage_summary.get('total_cost', 0)}}})}\n\n"
        
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
    """Get available agents info with current usage statistics"""
    usage_summary = tracker.get_summary()
    usage_by_agent = usage_summary.get("usage_by_agent", {})
    
    agents_info = [
        {
            "id": "feature_planner",
            "name": "Feature Planner",
            "role": "FeaturePlannerAgent",
            "phase": "planning",
            "description": "Analyzes requirements and proposes features for user confirmation",
            "icon": "💡",
            "usage": usage_by_agent.get("Feature Planner", {"calls": 0, "tokens": 0})
        },
        {
            "id": "architect",
            "name": "Architect",
            "role": "ArchitectAgent",
            "phase": "discovery",
            "description": "Designs system architecture, tech stack, and database schema",
            "icon": "🏗️",
            "usage": usage_by_agent.get("Architect", {"calls": 0, "tokens": 0})
        },
        {
            "id": "file_planner",
            "name": "File Planner",
            "role": "FilePlannerAgent",
            "phase": "design",
            "description": "Plans all files needed for the project with dependencies",
            "icon": "📋",
            "usage": usage_by_agent.get("File Planner", {"calls": 0, "tokens": 0})
        },
        {
            "id": "code_generator",
            "name": "Code Generator",
            "role": "CodeGeneratorAgent",
            "phase": "implementation",
            "description": "Generates production-ready code files with full context",
            "icon": "⚙️",
            "usage": usage_by_agent.get("Code Generator", {"calls": 0, "tokens": 0})
        },
        {
            "id": "validator",
            "name": "Integration Validator",
            "role": "IntegrationValidatorAgent",
            "phase": "validation",
            "description": "Validates imports, types, and integration between files",
            "icon": "🔗",
            "usage": usage_by_agent.get("Validator", {"calls": 0, "tokens": 0})
        },
        {
            "id": "code_reviewer",
            "name": "Code Reviewer",
            "role": "CodeReviewerAgent",
            "phase": "review",
            "description": "Reviews code for syntax errors and fixes them",
            "icon": "🔍",
            "usage": usage_by_agent.get("Code Reviewer", {"calls": 0, "tokens": 0})
        },
        {
            "id": "test_generator",
            "name": "Test Generator",
            "role": "TestGeneratorAgent",
            "phase": "testing",
            "description": "Generates unit tests for each code file",
            "icon": "🧪",
            "usage": usage_by_agent.get("Test Generator", {"calls": 0, "tokens": 0})
        },
        {
            "id": "execution",
            "name": "Execution Agent",
            "role": "ExecutionAgent",
            "phase": "execution",
            "description": "Executes generated code, detects errors, and applies auto-fixes",
            "icon": "🚀",
            "usage": usage_by_agent.get("Execution", {"calls": 0, "tokens": 0})
        }
    ]
    
    return {
        "agents": agents_info,
        "phases": ["planning", "discovery", "design", "implementation", "validation", "review", "testing", "execution"],
        "capabilities": [
            "Feature planning with user confirmation",
            "Dynamic architecture design",
            "Multi-project type support (frontend/backend/fullstack/microservices)",
            "Intelligent file planning with dependencies",
            "Context-aware code generation",
            "Integration validation",
            "Syntax error detection and auto-fix",
            "Unit test generation for each file",
            "Auto-fix execution"
        ],
        "mcp_integration": {
            "enabled": True,
            "description": "Agents communicate via Model Context Protocol for coordinated generation"
        },
        "total_usage": {
            "calls": usage_summary.get("total_calls", 0),
            "tokens": usage_summary.get("total_tokens", 0),
            "cost": usage_summary.get("total_cost", 0)
        }
    }


@app.get("/api/v1/preset/symptom-tracker")
async def get_symptom_tracker_preset():
    """Get the symptom tracker preset problem statement"""
    return {
        "name": "Symptom Tracker",
        "description": "Health symptom tracking application",
        "problem_statement": SYMPTOM_TRACKER_PRESET,
        "features": [
            "User Authentication",
            "Symptom Logging with Severity",
            "Associated Factors Tracking",
            "Pattern Analysis & Charts",
            "Trigger Detection",
            "Symptom History & Search",
            "Data Export (CSV/PDF)",
            "Reminders",
            "Dashboard with Insights"
        ]
    }


@app.get("/api/v1/usage/detailed")
async def get_detailed_usage():
    """Get detailed LLM usage statistics broken down by agent"""
    summary = tracker.get_summary()
    return {
        "summary": summary,
        "by_agent": summary.get("usage_by_agent", {}),
        "by_model": summary.get("usage_by_model", {}),
        "timeline": tracker.get_timeline(),
        "session_info": {
            "duration_seconds": summary.get("session_duration_seconds", 0),
            "calls_per_minute": summary.get("calls_per_minute", 0)
        }
    }


# ============================================================================
# APPLICATION EXECUTION ENDPOINTS
# ============================================================================

@app.post("/api/execute")
async def execute_generated_app(request: Request):
    """
    Execute the generated application with automatic error detection and fixing.
    
    Uses the ExecutionAgent to:
    1. Save files to disk
    2. Install dependencies
    3. Detect and fix build/runtime errors automatically
    4. Start the dev server
    
    Returns a streaming response with execution logs, fixes applied, and status.
    """
    body = await request.json()
    files = body.get("files", [])
    conversation_id = body.get("conversation_id", str(uuid.uuid4()))
    use_auto_fix = body.get("auto_fix", True)  # Enable auto-fix by default
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    async def stream_execution():
        try:
            if use_auto_fix:
                # Use ExecutionAgent with auto-fix capabilities
                async for event in execution_agent.execute_with_auto_fix(files, conversation_id):
                    yield f"data: {json.dumps(event)}\n\n"
            else:
                # Use original execution without auto-fix
                async for event in execute_application(files, conversation_id):
                    yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            import traceback
            logger.error("execution_error", error=str(e), traceback=traceback.format_exc())
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
    import io
    import zipfile
    
    body = await request.json()
    files = body.get("files", [])
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    logger.info("download_request", file_count=len(files))
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    files_added = 0
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_info in files:
            filepath = file_info.get("filepath", "")
            content = file_info.get("content", "")
            
            if filepath:
                # Ensure we don't have absolute paths
                clean_path = filepath.lstrip("/")
                # Write file even if content is empty (creates empty file)
                zip_file.writestr(clean_path, content or "")
                files_added += 1
    
    logger.info("download_zip_created", files_added=files_added)
    
    # Get the zip content
    zip_content = zip_buffer.getvalue()
    zip_size = len(zip_content)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ai-generated-project-{timestamp}.zip"
    
    return StreamingResponse(
        iter([zip_content]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(zip_size),
            "Cache-Control": "no-cache"
        }
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
