"""
Advanced Orchestrator - Manages sophisticated multi-phase workflow
Coordinates all agents across 6 phases of software development
"""
import asyncio
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, timezone
import structlog

# Import all enhanced schemas
from models.enhanced_schemas import (
    AgentRole, WorkflowPhase, EnhancedCodeGenerationResult,
    Requirements, ResearchFindings, HighLevelDesign,
    ModuleDesign, LowLevelDesign, SecurityAudit,
    DebugReport, ExecutionResult, AgentHealthStatus
)
from models.clarification_schemas import (
    ClarificationRequest, ClarificationResponse, TechStackDecision
)

# Import Phase 1 agents
from agents.phase1_discovery.requirements_analyst_agent import RequirementsAnalystAgent
from agents.phase1_discovery.requirements_analyst_interactive import InteractiveRequirementsAnalystAgent
from agents.phase1_discovery.tech_stack_decision_agent import TechStackDecisionAgent
from agents.phase1_discovery.research_agent import ResearchAgent

# Import Phase 2 agents
from agents.phase2_design.architect_agent import ArchitectAgent
from agents.phase2_design.module_designer_agent import ModuleDesignerAgent
from agents.phase2_design.component_designer_agent import ComponentDesignerAgent
from agents.phase2_design.ui_designer_agent import UIDesignerAgent
from agents.phase2_design.database_designer_agent import DatabaseDesignerAgent

# Import Phase 3 implementation agents
from agents.phase3_implementation.nextjs_coder_agent import NextJSCoderAgent
from agents.phase3_implementation.docker_generator_agent import DockerGeneratorAgent

# Import Phase 4 agents
from agents.phase4_qa.debugger_agent import DebuggerAgent
from agents.phase4_qa.security_auditor_agent import SecurityAuditorAgent
from agents.reviewer_agent import ReviewerAgent

# Import Phase 5 agents
from agents.phase5_validation.executor_agent import ExecutorAgent

# Import Phase 6 agents
from agents.phase6_monitoring.monitor_agent import MonitorAgent

from mcp.server import MCPServer
from utils.openai_client import OpenAIClient
from utils.llm_tracker import tracker

logger = structlog.get_logger()


class AdvancedOrchestrator:
    """
    Advanced orchestrator managing 6-phase workflow:

    Phase 1: Discovery & Analysis
      - Requirements Analysis
      - Research

    Phase 2: Design & Planning
      - Architecture (HLD)
      - Module Design
      - Component Design (LLD)

    Phase 3: Implementation
      - Code Generation
      - Documentation

    Phase 4: Quality Assurance
      - Testing
      - Debugging
      - Security Audit
      - Code Review

    Phase 5: Validation & Deployment
      - Execution Validation
      - Integration Testing

    Phase 6: Monitoring
      - Agent Health Monitoring
    """

    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
        self.mcp = MCPServer()

        logger.info("initializing_advanced_orchestrator")

        # Initialize all agents
        self._initialize_agents()

        # Track active requests
        self.active_requests: Dict[str, EnhancedCodeGenerationResult] = {}

        logger.info("advanced_orchestrator_initialized", total_agents=len(self._get_all_agents()))

    def _initialize_agents(self):
        """Initialize all agents"""
        # Phase 1: Discovery & Analysis
        self.requirements_analyst = RequirementsAnalystAgent(self.mcp, self.openai)
        self.interactive_requirements_analyst = InteractiveRequirementsAnalystAgent(self.mcp, self.openai)
        self.tech_stack_decision_agent = TechStackDecisionAgent(self.mcp, self.openai)
        self.researcher = ResearchAgent(self.mcp, self.openai)

        # Phase 2: Design & Planning
        self.architect = ArchitectAgent(self.mcp, self.openai)
        self.database_designer = DatabaseDesignerAgent(self.mcp, self.openai)
        self.module_designer = ModuleDesignerAgent(self.mcp, self.openai)
        self.component_designer = ComponentDesignerAgent(self.mcp, self.openai)
        self.ui_designer = UIDesignerAgent(self.mcp, self.openai)

        # Phase 3: Implementation (Next.js focused)
        self.coder = NextJSCoderAgent(self.mcp, self.openai)  # Next.js-specific coder
        # Note: Testing is now integrated into NextJSCoderAgent
        self.docker_generator = DockerGeneratorAgent(self.mcp, self.openai)

        # Phase 4: Quality Assurance
        self.debugger = DebuggerAgent(self.mcp, self.openai)
        self.security_auditor = SecurityAuditorAgent(self.mcp, self.openai)
        self.reviewer = ReviewerAgent(self.mcp, self.openai)

        # Phase 5: Validation
        self.executor = ExecutorAgent(self.mcp, self.openai)

        # Phase 6: Monitoring
        self.monitor = MonitorAgent(self.mcp, self.openai)

    def _get_all_agents(self) -> List[Any]:
        """Get list of all agents"""
        return [
            self.requirements_analyst, self.researcher,
            self.architect, self.database_designer, self.module_designer, self.component_designer, self.ui_designer,
            self.coder, self.docker_generator,
            self.debugger, self.security_auditor, self.reviewer,
            self.executor, self.monitor
        ]

    async def generate_code(self, request_data: Dict[str, Any]) -> EnhancedCodeGenerationResult:
        """
        Main workflow - orchestrate all phases

        Args:
            request_data: Contains description, language, framework, requirements

        Returns:
            Complete enhanced result
        """
        request_id = str(uuid.uuid4())

        logger.info(
            "enhanced_generation_started",
            request_id=request_id,
            language=request_data.get("language")
        )

        # Initialize result
        result = EnhancedCodeGenerationResult(
            request_id=request_id,
            status="in_progress",
            current_phase=WorkflowPhase.DISCOVERY,
            created_at=datetime.now(timezone.utc)
        )

        self.active_requests[request_id] = result
        tracker.reset()

        try:
            # ==== PHASE 1: DISCOVERY & ANALYSIS ====
            logger.info("phase_1_discovery", request_id=request_id)
            result.current_phase = WorkflowPhase.DISCOVERY

            # Step 1.1: Requirements Analysis
            req_result = await self.requirements_analyst.process_task(request_data)
            if "requirements" not in req_result:
                raise ValueError("Requirements analyst did not return 'requirements' key")
            result.requirements = Requirements(**req_result["requirements"])
            if req_result.get("activity"):
                result.agent_activities.append(req_result["activity"])

            # Step 1.2: Research
            research_result = await self.researcher.process_task({
                **request_data,
                "requirements": result.requirements.model_dump()
            })
            if "research" not in research_result:
                raise ValueError("Research agent did not return 'research' key")
            result.research = [ResearchFindings(**r) for r in research_result["research"]]
            if research_result.get("activity"):
                result.agent_activities.append(research_result["activity"])

            # ==== PHASE 2: DESIGN & PLANNING ====
            logger.info("phase_2_design", request_id=request_id)
            result.current_phase = WorkflowPhase.DESIGN

            # Step 2.1: High-Level Design (HLD)
            hld_result = await self.architect.process_task({
                **request_data,
                "requirements": result.requirements.model_dump(),
                "research": [r.model_dump() for r in result.research]
            })
            if "hld" not in hld_result:
                raise ValueError("Architect did not return 'hld' key")
            result.hld = HighLevelDesign(**hld_result["hld"])
            if hld_result.get("activity"):
                result.agent_activities.append(hld_result["activity"])

            # Step 2.1.5: Database Schema Design (Next.js specific)
            db_result = await self.database_designer.process_task({
                "requirements": result.requirements.model_dump(),
                "database_preference": request_data.get("database", "auto"),
                "description": request_data.get("description", "")
            })
            result.database_schema = db_result.get("database_schema", {})
            if db_result.get("activity"):
                result.agent_activities.append(db_result["activity"])
            
            logger.info("database_schema_designed", 
                       database_type=result.database_schema.get("database_type"),
                       entity_count=len(result.database_schema.get("entities", [])))

            # Step 2.2: Module Design
            module_result = await self.module_designer.process_task({
                **request_data,
                "hld": result.hld.model_dump(),
                "requirements": result.requirements.model_dump()
            })
            if "modules" not in module_result:
                raise ValueError("Module designer did not return 'modules' key")
            result.modules = [ModuleDesign(**m) for m in module_result["modules"]]
            if module_result.get("activity"):
                result.agent_activities.append(module_result["activity"])

            # Step 2.3: Low-Level Design (LLD)
            lld_result = await self.component_designer.process_task({
                **request_data,
                "modules": [m.model_dump() for m in result.modules],
                "requirements": result.requirements.model_dump()
            })
            if "lld" not in lld_result:
                raise ValueError("Component designer did not return 'lld' key")
            result.lld = [LowLevelDesign(**l) for l in lld_result["lld"]]
            if lld_result.get("activity"):
                result.agent_activities.append(lld_result["activity"])

            # Step 2.4: UI/UX Design
            ui_result = await self.ui_designer.process_task({
                **request_data,
                "requirements": result.requirements.model_dump(),
                "hld": result.hld.model_dump(),
                "modules": [m.model_dump() for m in result.modules]
            })
            if "ui_design" not in ui_result:
                raise ValueError("UI designer did not return 'ui_design' key")
            result.ui_design = ui_result["ui_design"]
            if ui_result.get("activity"):
                result.agent_activities.append(ui_result["activity"])

            # ==== PHASE 3: IMPLEMENTATION ====
            logger.info("phase_3_implementation", request_id=request_id)
            result.current_phase = WorkflowPhase.IMPLEMENTATION

            # Step 3.1: Code Generation (enhanced with design context)
            # Safely extract dependencies from technology_stack
            tech_stack = getattr(result.hld, 'technology_stack', {})
            dependencies = tech_stack.get("dependencies", []) if isinstance(tech_stack, dict) else []
            
            code_result = await self.coder.process_task({
                "plan": {
                    "overview": result.hld.system_overview,
                    "steps": [m.purpose for m in result.modules],
                    "file_structure": {m.module_name: m.purpose for m in result.modules},
                    "dependencies": dependencies,
                    "estimated_complexity": "medium"
                },
                "description": request_data.get("description"),
                "language": request_data.get("language", "nextjs"),
                "database_schema": result.database_schema,  # Pass database schema to coder
                "requirements": result.requirements.model_dump(),
                "hld": result.hld.model_dump(),
                "modules": [m.model_dump() for m in result.modules],
                "lld": [l.model_dump() for l in result.lld]
            })
            if "code_files" not in code_result:
                raise ValueError("Coder did not return 'code_files' key")
            result.code_files = code_result["code_files"]
            if code_result.get("activity"):
                result.agent_activities.append(code_result["activity"])

            # Step 3.2: Test Generation (integrated into NextJSCoderAgent)
            # Note: NextJSCoderAgent now includes test files in code_files
            result.test_files = []  # Tests are included in code_files

            # Step 3.3: Docker Configuration Generation (Next.js specific)
            docker_result = await self.docker_generator.process_task({
                "database_schema": result.database_schema,
                "code_files": result.code_files,
                "description": request_data.get("description", "")
            })
            docker_files = docker_result.get("docker_files", [])
            # Add Docker files to code files
            result.code_files.extend(docker_files)
            if docker_result.get("activity"):
                result.agent_activities.append(docker_result["activity"])
            
            logger.info("docker_configuration_generated", docker_file_count=len(docker_files))

            # ==== PHASE 4: QUALITY ASSURANCE ====
            logger.info("phase_4_qa", request_id=request_id)
            result.current_phase = WorkflowPhase.QUALITY_ASSURANCE

            # Step 4.1: Security Audit
            security_result = await self.security_auditor.process_task({
                "code_files": result.code_files,
                "requirements": result.requirements.model_dump(),
                "language": request_data.get("language")
            })
            if "security_audit" not in security_result:
                raise ValueError("Security auditor did not return 'security_audit' key")
            result.security_audit = SecurityAudit(**security_result["security_audit"])
            if security_result.get("activity"):
                result.agent_activities.append(security_result["activity"])

            # Step 4.2: Code Review
            review_result = await self.reviewer.process_task({
                "code_files": result.code_files,
                "test_files": result.test_files,
                "language": request_data.get("language")
            })
            # Store review in original format for compatibility
            if review_result.get("activity"):
                result.agent_activities.append(review_result["activity"])

            # ==== PHASE 5: VALIDATION ====
            logger.info("phase_5_validation", request_id=request_id)
            result.current_phase = WorkflowPhase.VALIDATION

            # Step 5.1: Execution Validation
            execution_result = await self.executor.process_task({
                "code_files": result.code_files,
                "test_files": result.test_files,
                "language": request_data.get("language")
            })
            if "execution_result" not in execution_result:
                raise ValueError("Executor did not return 'execution_result' key")
            result.execution_result = ExecutionResult(**execution_result["execution_result"])
            if execution_result.get("activity"):
                result.agent_activities.append(execution_result["activity"])

            # Step 5.2: Debugging (if issues found)
            if not result.execution_result.success or result.execution_result.errors:
                logger.info("running_debugger", request_id=request_id)
                debug_result = await self.debugger.process_task({
                    "code_files": result.code_files,
                    "execution_result": result.execution_result.model_dump(),
                    "test_results": result.execution_result.test_results
                })
                if "debug_report" not in debug_result:
                    raise ValueError("Debugger did not return 'debug_report' key")
                result.debug_report = DebugReport(**debug_result["debug_report"])
                if debug_result.get("activity"):
                    result.agent_activities.append(debug_result["activity"])

            # ==== PHASE 6: MONITORING ====
            logger.info("phase_6_monitoring", request_id=request_id)

            # Step 6.1: Monitor Agent Health
            monitor_result = await self.monitor.process_task({
                "agent_activities": result.agent_activities
            })
            if "agent_health" not in monitor_result:
                raise ValueError("Monitor did not return 'agent_health' key")
            result.agent_health = [AgentHealthStatus(**h) for h in monitor_result["agent_health"]]
            if monitor_result.get("activity"):
                result.agent_activities.append(monitor_result["activity"])

            # Get LLM usage summary
            usage_summary = tracker.get_summary()
            result.total_llm_usage = {
                "total_calls": usage_summary.get("total_calls", 0),
                "total_tokens": usage_summary.get("total_tokens", 0)
            }
            result.total_cost = usage_summary.get("total_cost", 0.0)

            # Mark as completed
            result.status = "completed"
            result.completed_at = datetime.now(timezone.utc)

            logger.info(
                "enhanced_generation_completed",
                request_id=request_id,
                phases_completed=6,
                code_files=len(result.code_files),
                total_tokens=result.total_llm_usage["total_tokens"],
                total_cost=result.total_cost
            )

            return result

        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.now(timezone.utc)
            result.errors.append(str(e))

            logger.error(
                "enhanced_generation_failed",
                request_id=request_id,
                error=str(e),
                phase=result.current_phase.value
            )

            raise
        
        finally:
            # Cleanup active request from memory
            if request_id in self.active_requests:
                del self.active_requests[request_id]
                logger.debug("cleaned_up_active_request", request_id=request_id)

    async def generate_code_interactive(self, request_data: Dict[str, Any]) -> EnhancedCodeGenerationResult:
        """
        Interactive workflow - pauses for clarifications if needed

        Args:
            request_data: Contains description, language, framework, requirements

        Returns:
            Complete enhanced result (or partial result with clarification_request)
        """
        request_id = str(uuid.uuid4())

        logger.info(
            "interactive_generation_started",
            request_id=request_id,
            language=request_data.get("language")
        )

        # Initialize result
        result = EnhancedCodeGenerationResult(
            request_id=request_id,
            status="in_progress",
            current_phase=WorkflowPhase.DISCOVERY,
            created_at=datetime.now(timezone.utc),
            original_request=request_data  # Store for resume
        )

        self.active_requests[request_id] = result
        tracker.reset()

        try:
            # ==== PHASE 1: DISCOVERY & ANALYSIS (Interactive) ====
            logger.info("phase_1_interactive_discovery", request_id=request_id)
            result.current_phase = WorkflowPhase.DISCOVERY

            # Step 1.1: Interactive Requirements Analysis
            analysis_result = await self.interactive_requirements_analyst.analyze_and_generate_questions(request_data)

            if analysis_result.get("needs_clarification"):
                # Need to pause for clarifications
                logger.info("clarifications_needed", request_id=request_id,
                          question_count=len(analysis_result["questions"]))

                clarification_request = ClarificationRequest(
                    request_id=request_id,
                    phase="discovery",
                    agent="interactive_requirements_analyst",
                    reason=f"Need clarification to better understand requirements (confidence: {analysis_result.get('confidence_score', 0.5)})",
                    questions=analysis_result["questions"],
                    can_skip=False
                )

                result.clarification_request = clarification_request.model_dump()
                result.awaiting_clarifications = True
                result.status = "awaiting_clarifications"

                # Store preliminary requirements for resume
                result.requirements = Requirements(**analysis_result["preliminary_requirements"])

                logger.info("workflow_paused_for_clarifications", request_id=request_id)
                return result

            # No clarifications needed - continue with standard requirements
            result.requirements = Requirements(**analysis_result["preliminary_requirements"])

            # Continue to tech stack decision and rest of workflow
            return await self._continue_workflow_after_clarifications(request_id, request_data, None)

        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.now(timezone.utc)
            result.errors.append(str(e))

            logger.error(
                "interactive_generation_failed",
                request_id=request_id,
                error=str(e),
                phase=result.current_phase.value
            )

            raise
        
        finally:
            # Note: Don't cleanup if status is "awaiting_clarifications" - need to resume later
            if result.status not in ["awaiting_clarifications", "awaiting_tech_stack"]:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
                    logger.debug("cleaned_up_active_request", request_id=request_id)

    async def submit_clarifications(
        self,
        request_id: str,
        clarification_response: ClarificationResponse
    ) -> EnhancedCodeGenerationResult:
        """
        Resume workflow after receiving clarifications

        Args:
            request_id: The generation request ID
            clarification_response: User's answers to clarification questions

        Returns:
            Updated result continuing the workflow
        """
        result = self.active_requests.get(request_id)
        if not result:
            raise ValueError(f"Request {request_id} not found")

        if not result.awaiting_clarifications:
            raise ValueError(f"Request {request_id} is not awaiting clarifications")

        logger.info("clarifications_received", request_id=request_id,
                   answer_count=len(clarification_response.answers))

        try:
            # Store clarification response
            result.clarification_response = clarification_response.model_dump()
            result.awaiting_clarifications = False
            result.status = "in_progress"

            # Get original request data
            request_data = result.original_request or {}

            # Finalize requirements with clarifications
            finalized_reqs = await self.interactive_requirements_analyst.finalize_requirements(
                task_data={
                    "description": request_data.get("description"),
                    "preliminary_requirements": result.requirements.model_dump() if result.requirements else {}
                },
                clarifications=clarification_response.model_dump()
            )

            result.requirements = Requirements(**finalized_reqs["requirements"])
            if finalized_reqs.get("activity"):
                result.agent_activities.append(finalized_reqs["activity"])

            # Continue workflow
            return await self._continue_workflow_after_clarifications(
                request_id, request_data, clarification_response
            )

        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.now(timezone.utc)
            result.errors.append(str(e))

            logger.error(
                "clarification_submission_failed",
                request_id=request_id,
                error=str(e)
            )

            raise
        
        finally:
            # Cleanup on completion or error
            if result.status not in ["awaiting_tech_stack"]:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
                    logger.debug("cleaned_up_active_request", request_id=request_id)

    async def _continue_workflow_after_clarifications(
        self,
        request_id: str,
        request_data: Dict[str, Any],
        clarification_response: Optional[ClarificationResponse]
    ) -> EnhancedCodeGenerationResult:
        """
        Continue workflow after clarifications (or if no clarifications needed)

        This includes: Tech Stack Decision → Research → Design → Implementation → QA → Validation → Monitoring
        """
        result = self.active_requests[request_id]

        try:
            # Step 1.2: Tech Stack Decision (based on requirements and clarifications)
            clarifications_dict = {}
            if clarification_response:
                # Convert answers to dict
                for ans in clarification_response.answers:
                    clarifications_dict[ans.question_id] = ans.answer

            tech_decision_result = await self.tech_stack_decision_agent.process_task({
                **request_data,
                "requirements": result.requirements.model_dump(),
                "clarifications": clarifications_dict,
                "user_preferences": request_data.get("user_preferences", {})
            })

            result.tech_stack_decision = tech_decision_result["tech_stack_decision"]
            if tech_decision_result.get("activity"):
                result.agent_activities.append(tech_decision_result["activity"])

            tech_decision = TechStackDecision(**result.tech_stack_decision)
            logger.info("tech_stack_decided", request_id=request_id,
                       language=tech_decision.language,
                       database=tech_decision.database,
                       architecture=tech_decision.architecture_pattern)

            # Step 1.3: Research (using tech stack decisions)
            research_result = await self.researcher.process_task({
                **request_data,
                "requirements": result.requirements.model_dump(),
                "tech_stack": result.tech_stack_decision
            })
            result.research = [ResearchFindings(**r) for r in research_result["research"]]
            if research_result.get("activity"):
                result.agent_activities.append(research_result["activity"])

            # ==== PHASE 2: DESIGN & PLANNING ====
            logger.info("phase_2_design", request_id=request_id)
            result.current_phase = WorkflowPhase.DESIGN

            # Step 2.1: High-Level Design (HLD) - using tech stack decisions
            hld_result = await self.architect.process_task({
                **request_data,
                "requirements": result.requirements.model_dump(),
                "research": [r.model_dump() for r in result.research],
                "tech_stack_decision": result.tech_stack_decision
            })
            result.hld = HighLevelDesign(**hld_result["hld"])
            if hld_result.get("activity"):
                result.agent_activities.append(hld_result["activity"])

            # Step 2.2: Module Design
            module_result = await self.module_designer.process_task({
                **request_data,
                "hld": result.hld.model_dump(),
                "requirements": result.requirements.model_dump()
            })
            result.modules = [ModuleDesign(**m) for m in module_result["modules"]]
            if module_result.get("activity"):
                result.agent_activities.append(module_result["activity"])

            # Step 2.3: Low-Level Design (LLD)
            lld_result = await self.component_designer.process_task({
                **request_data,
                "modules": [m.model_dump() for m in result.modules],
                "requirements": result.requirements.model_dump()
            })
            result.lld = [LowLevelDesign(**l) for l in lld_result["lld"]]
            if lld_result.get("activity"):
                result.agent_activities.append(lld_result["activity"])

            # Step 2.4: UI/UX Design
            ui_result = await self.ui_designer.process_task({
                **request_data,
                "requirements": result.requirements.model_dump(),
                "hld": result.hld.model_dump(),
                "modules": [m.model_dump() for m in result.modules]
            })
            result.ui_design = ui_result["ui_design"]
            if ui_result.get("activity"):
                result.agent_activities.append(ui_result["activity"])

            # ==== PHASE 3: IMPLEMENTATION ====
            logger.info("phase_3_implementation", request_id=request_id)
            result.current_phase = WorkflowPhase.IMPLEMENTATION

            # Use tech stack decision for language
            effective_language = tech_decision.language if tech_decision else request_data.get("language", "python")

            # Step 3.1: Code Generation
            # Safely extract dependencies from technology_stack
            tech_stack = getattr(result.hld, 'technology_stack', {})
            dependencies = tech_stack.get("dependencies", []) if isinstance(tech_stack, dict) else []
            
            code_result = await self.coder.process_task({
                "plan": {
                    "overview": result.hld.system_overview,
                    "steps": [m.purpose for m in result.modules],
                    "file_structure": {m.module_name: m.purpose for m in result.modules},
                    "dependencies": dependencies,
                    "estimated_complexity": "medium"
                },
                "description": request_data.get("description"),
                "language": effective_language,
                "hld": result.hld.model_dump(),
                "modules": [m.model_dump() for m in result.modules],
                "lld": [l.model_dump() for l in result.lld],
                "tech_stack_decision": result.tech_stack_decision
            })
            result.code_files = code_result["code_files"]
            if code_result.get("activity"):
                result.agent_activities.append(code_result["activity"])

            # Step 3.2: Test Generation (integrated into NextJSCoderAgent)
            # Note: NextJSCoderAgent now includes test files in code_files
            result.test_files = []  # Tests are included in code_files

            # ==== PHASE 4: QUALITY ASSURANCE ====
            logger.info("phase_4_qa", request_id=request_id)
            result.current_phase = WorkflowPhase.QUALITY_ASSURANCE

            # Step 4.1: Security Audit
            security_result = await self.security_auditor.process_task({
                "code_files": result.code_files,
                "requirements": result.requirements.model_dump(),
                "language": effective_language
            })
            result.security_audit = SecurityAudit(**security_result["security_audit"])
            if security_result.get("activity"):
                result.agent_activities.append(security_result["activity"])

            # Step 4.2: Code Review
            review_result = await self.reviewer.process_task({
                "code_files": result.code_files,
                "test_files": result.test_files,
                "language": effective_language
            })
            if review_result.get("activity"):
                result.agent_activities.append(review_result["activity"])

            # ==== PHASE 5: VALIDATION ====
            logger.info("phase_5_validation", request_id=request_id)
            result.current_phase = WorkflowPhase.VALIDATION

            # Step 5.1: Execution Validation
            execution_result = await self.executor.process_task({
                "code_files": result.code_files,
                "test_files": result.test_files,
                "language": effective_language
            })
            result.execution_result = ExecutionResult(**execution_result["execution_result"])
            if execution_result.get("activity"):
                result.agent_activities.append(execution_result["activity"])

            # Step 5.2: Debugging (if issues found)
            if not result.execution_result.success or result.execution_result.errors:
                logger.info("running_debugger", request_id=request_id)
                debug_result = await self.debugger.process_task({
                    "code_files": result.code_files,
                    "execution_result": result.execution_result.model_dump(),
                    "test_results": result.execution_result.test_results
                })
                if "debug_report" not in debug_result:
                    raise ValueError("Debugger did not return 'debug_report' key")
                result.debug_report = DebugReport(**debug_result["debug_report"])
                if debug_result.get("activity"):
                    result.agent_activities.append(debug_result["activity"])

            # ==== PHASE 6: MONITORING ====
            logger.info("phase_6_monitoring", request_id=request_id)

            # Step 6.1: Monitor Agent Health
            monitor_result = await self.monitor.process_task({
                "agent_activities": result.agent_activities
            })
            if "agent_health" not in monitor_result:
                raise ValueError("Monitor did not return 'agent_health' key")
            result.agent_health = [AgentHealthStatus(**h) for h in monitor_result["agent_health"]]
            if monitor_result.get("activity"):
                result.agent_activities.append(monitor_result["activity"])

            # Get LLM usage summary
            usage_summary = tracker.get_summary()
            result.total_llm_usage = {
                "total_calls": usage_summary.get("total_calls", 0),
                "total_tokens": usage_summary.get("total_tokens", 0)
            }
            result.total_cost = usage_summary.get("total_cost", 0.0)

            # Mark as completed
            result.status = "completed"
            result.completed_at = datetime.now(timezone.utc)

            logger.info(
                "interactive_generation_completed",
                request_id=request_id,
                phases_completed=6,
                code_files=len(result.code_files),
                total_tokens=result.total_llm_usage["total_tokens"],
                total_cost=result.total_cost
            )

            return result

        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.now(timezone.utc)
            result.errors.append(str(e))

            logger.error(
                "workflow_continuation_failed",
                request_id=request_id,
                error=str(e),
                phase=result.current_phase.value
            )

            raise
        
        finally:
            # Cleanup on completion or error (this is called from various places, so cleanup here)
            if request_id in self.active_requests:
                # Only cleanup if truly complete or failed
                if result.status in ["completed", "failed"]:
                    del self.active_requests[request_id]
                    logger.debug("cleaned_up_active_request", request_id=request_id)

    def get_request_status(self, request_id: str) -> Optional[EnhancedCodeGenerationResult]:
        """Get status of a request"""
        return self.active_requests.get(request_id)

    async def start_background_tasks(self):
        """Start background tasks"""
        asyncio.create_task(self.mcp.process_messages())
        logger.info("background_tasks_started")

    async def generate_with_streaming(self, request_data: Dict[str, Any]):
        """
        Generate code with real-time streaming of events
        Yields events as each phase progresses
        """
        request_id = str(uuid.uuid4())
        
        try:
            # Emit start event
            yield {
                'type': 'started',
                'request_id': request_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Phase 1: Discovery
            yield {'type': 'phase_started', 'phase': 'Phase 1: Discovery & Analysis'}
            
            # Requirements Analysis
            yield {'type': 'agent_started', 'agent': 'Requirements Analyst', 'activity': 'Analyzing requirements...'}
            req_result = await self.requirements_analyst.process_task(request_data)
            requirements = req_result["requirements"]
            yield {'type': 'agent_completed', 'agent': 'Requirements Analyst', 'data': {'count': len(requirements.get('functional', []))}}
            
            # Research
            yield {'type': 'agent_started', 'agent': 'Research Agent', 'activity': 'Researching best practices...'}
            research_result = await self.researcher.process_task({"requirements": requirements})
            yield {'type': 'agent_completed', 'agent': 'Research Agent'}
            
            # Tech Stack
            yield {'type': 'agent_started', 'agent': 'Tech Stack Decision', 'activity': 'Selecting technologies...'}
            tech_result = await self.tech_stack_decision_agent.process_task({**request_data, "requirements": requirements, "research": research_result["research_findings"]})
            yield {'type': 'agent_completed', 'agent': 'Tech Stack Decision', 'data': {'tech_stack': tech_result.get('tech_stack', {})}}
            
            # Phase 2: Design
            yield {'type': 'phase_started', 'phase': 'Phase 2: Design & Planning'}
            
            # Architecture
            yield {'type': 'agent_started', 'agent': 'Architect', 'activity': 'Designing system architecture...'}
            arch_result = await self.architect.process_task({**request_data, "requirements": requirements, "research": research_result["research_findings"]})
            yield {'type': 'agent_completed', 'agent': 'Architect'}
            
            # Database Schema Design
            yield {'type': 'agent_started', 'agent': 'Database Designer', 'activity': 'Designing database schema...'}
            db_result = await self.database_designer.process_task({
                "requirements": requirements,
                "database_preference": request_data.get("database", "auto"),
                "description": request_data.get("description", "")
            })
            database_schema = db_result.get("database_schema", {})
            yield {'type': 'agent_completed', 'agent': 'Database Designer', 'data': {
                'database_type': database_schema.get('database_type'),
                'entity_count': len(database_schema.get('entities', []))
            }}
            
            # Module Design
            yield {'type': 'agent_started', 'agent': 'Module Designer', 'activity': 'Planning module structure...'}
            module_result = await self.module_designer.process_task({**request_data, "requirements": requirements, "architecture": arch_result["architecture"]})
            yield {'type': 'agent_completed', 'agent': 'Module Designer'}
            
            # Component Design
            yield {'type': 'agent_started', 'agent': 'Component Designer', 'activity': 'Creating detailed designs...'}
            comp_result = await self.component_designer.process_task({**request_data, "requirements": requirements, "module_design": module_result["module_design"]})
            yield {'type': 'agent_completed', 'agent': 'Component Designer'}
            
            # UI Design
            yield {'type': 'agent_started', 'agent': 'UI Designer', 'activity': 'Designing user interface...'}
            ui_result = await self.ui_designer.process_task({**request_data, "requirements": requirements})
            yield {'type': 'agent_completed', 'agent': 'UI Designer'}
            
            # Phase 3: Implementation
            yield {'type': 'phase_started', 'phase': 'Phase 3: Implementation'}
            
            # Code Generation
            yield {'type': 'agent_started', 'agent': 'Code Generator', 'activity': 'Generating Next.js code files...'}
            code_result = await self.coder.process_task({
                **request_data,
                "requirements": requirements,
                "database_schema": database_schema,  # Pass database schema
                "architecture": arch_result.get("architecture", {}),
                "component_design": comp_result.get("component_design", {}),
                "ui_design": ui_result.get("ui_design")
            })
            
            # Stream each generated file
            for file in code_result.get("code_files", []):
                yield {
                    'type': 'file_generated',
                    'file': {
                        'filename': file.get('filename'),
                        'filepath': file.get('filepath'),
                        'language': file.get('language'),
                        'content': file.get('content')
                    }
                }
            yield {'type': 'agent_completed', 'agent': 'Code Generator', 'data': {'file_count': len(code_result.get("code_files", []))}}
            
            # Test Generation (integrated into NextJSCoderAgent)
            # Note: Tests are now included in code_files from NextJSCoderAgent
            
            # Skip separate test generation - already included
            test_result = {"test_files": []}
            
            for file in test_result.get("test_files", []):
                yield {
                    'type': 'file_generated',
                    'file': {
                        'filename': file.get('filename'),
                        'filepath': file.get('filepath'),
                        'language': file.get('language'),
                        'content': file.get('content')
                    }
                }
            yield {'type': 'agent_completed', 'agent': 'Test Generator', 'data': {'test_count': len(test_result.get("test_files", []))}}
            
            # Docker Configuration
            yield {'type': 'agent_started', 'agent': 'Docker Generator', 'activity': 'Generating Docker configuration...'}
            docker_result = await self.docker_generator.process_task({
                "database_schema": database_schema,
                "code_files": code_result.get("code_files", []),
                "description": request_data.get("description", "")
            })
            
            # Stream Docker files
            for file in docker_result.get("docker_files", []):
                yield {
                    'type': 'file_generated',
                    'file': {
                        'filename': file.get('filename'),
                        'filepath': file.get('filepath'),
                        'language': file.get('language'),
                        'content': file.get('content')
                    }
                }
            yield {'type': 'agent_completed', 'agent': 'Docker Generator', 'data': {'docker_file_count': len(docker_result.get("docker_files", []))}}
            
            # Phase 4: QA
            yield {'type': 'phase_started', 'phase': 'Phase 4: Quality Assurance'}
            
            # Security Audit
            yield {'type': 'agent_started', 'agent': 'Security Auditor', 'activity': 'Auditing security...'}
            security_result = await self.security_auditor.process_task({"code_files": code_result.get("code_files", [])})
            yield {'type': 'agent_completed', 'agent': 'Security Auditor', 'data': {'vulnerabilities': len(security_result.get("security_audit", {}).get("vulnerabilities", []))}}
            
            # Code Review
            yield {'type': 'agent_started', 'agent': 'Code Reviewer', 'activity': 'Reviewing code quality...'}
            review_result = await self.reviewer.process_task({
                "code_files": code_result.get("code_files", []),
                "requirements": requirements
            })
            yield {'type': 'agent_completed', 'agent': 'Code Reviewer', 'data': {'score': review_result.get("review", {}).get("overall_score")}}
            
            # Phase 5: Validation
            yield {'type': 'phase_started', 'phase': 'Phase 5: Validation'}
            yield {'type': 'agent_started', 'agent': 'Executor', 'activity': 'Validating execution...'}
            exec_result = await self.executor.process_task({"code_files": code_result.get("code_files", [])})
            yield {'type': 'agent_completed', 'agent': 'Executor'}
            
            # Final completion event with all data
            yield {
                'type': 'completed',
                'request_id': request_id,
                'data': {
                    'code_files': code_result.get("code_files", []),
                    'test_files': test_result.get("test_files", []),
                    'requirements': requirements,
                    'security_audit': security_result.get("security_audit"),
                    'review': review_result.get("review")
                }
            }
            
        except Exception as e:
            logger.error("streaming_generation_failed", error=str(e), request_id=request_id)
            yield {
                'type': 'error',
                'error': str(e),
                'request_id': request_id
            }
        
        finally:
            # Always log completion/termination
            logger.info("streaming_generation_ended", request_id=request_id)
