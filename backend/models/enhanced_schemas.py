"""
Enhanced data models for the advanced multi-agent system
"""
from typing import List, Dict, Optional, Any, TYPE_CHECKING, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime, timezone

# Import unified AgentRole from base schemas
from models.schemas import AgentRole

# Conditional import to avoid circular dependency
if TYPE_CHECKING:
    from models.clarification_schemas import ClarificationRequest, ClarificationResponse, TechStackDecision


class WorkflowPhase(str, Enum):
    """Workflow phases"""
    DISCOVERY = "discovery"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    QUALITY_ASSURANCE = "quality_assurance"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"


class RequirementType(str, Enum):
    """Types of requirements"""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    TECHNICAL = "technical"
    BUSINESS = "business"
    SECURITY = "security"
    PERFORMANCE = "performance"


class Requirements(BaseModel):
    """Structured requirements analysis"""
    functional: List[str] = Field(default=[], description="Functional requirements")
    non_functional: List[str] = Field(default=[], description="Non-functional requirements")
    technical_constraints: List[str] = Field(default=[], description="Technical constraints")
    business_rules: List[str] = Field(default=[], description="Business rules")
    security_requirements: List[str] = Field(default=[], description="Security requirements")
    performance_requirements: List[str] = Field(default=[], description="Performance requirements")
    user_stories: List[str] = Field(default=[], description="User stories")
    acceptance_criteria: List[str] = Field(default=[], description="Acceptance criteria")


class ResearchFindings(BaseModel):
    """Research findings from web search"""
    topic: str = Field(..., description="Research topic")
    best_practices: List[str] = Field(default=[], description="Best practices found")
    recommended_libraries: List[str] = Field(default=[], description="Recommended libraries/frameworks")
    design_patterns: List[str] = Field(default=[], description="Relevant design patterns")
    security_considerations: List[str] = Field(default=[], description="Security considerations")
    sources: List[str] = Field(default=[], description="Source URLs")


class HighLevelDesign(BaseModel):
    """High-Level Design (HLD)"""
    system_overview: str = Field(..., description="System overview")
    architecture_pattern: str = Field(..., description="Architecture pattern (e.g., microservices, monolith)")
    major_components: List[str] = Field(..., description="Major system components")
    component_interactions: Dict[str, List[str]] = Field(..., description="How components interact")
    technology_stack: Dict[str, str] = Field(..., description="Technology choices")
    scalability_strategy: str = Field(..., description="Scalability approach")
    security_architecture: str = Field(..., description="Security design")
    deployment_architecture: str = Field(..., description="Deployment strategy")


class ModuleDesign(BaseModel):
    """Module-level design"""
    module_name: str = Field(..., description="Module name")
    purpose: str = Field(..., description="Module purpose")
    responsibilities: List[str] = Field(..., description="Module responsibilities")
    interfaces: List[str] = Field(..., description="Module interfaces/APIs")
    dependencies: List[str] = Field(..., description="Dependencies on other modules")
    data_models: List[str] = Field(..., description="Data models used")


class LowLevelDesign(BaseModel):
    """Low-Level Design (LLD) for components"""
    component_name: str = Field(..., description="Component name")
    module: str = Field(..., description="Parent module")
    classes: List[Dict[str, Any]] = Field(..., description="Class designs")
    functions: List[Dict[str, Any]] = Field(..., description="Function designs")
    algorithms: List[str] = Field(default=[], description="Key algorithms")
    data_structures: List[str] = Field(default=[], description="Data structures used")
    error_handling: str = Field(..., description="Error handling strategy")
    performance_considerations: List[str] = Field(default=[], description="Performance optimizations")


class DatabaseDesign(BaseModel):
    """Database schema design"""
    database_type: Literal["postgresql", "mongodb", "mysql", "sqlite", "other"] = Field(..., description="Database type")
    tables: List[Dict[str, Any]] = Field(..., description="Table/collection definitions")
    relationships: List[str] = Field(default=[], description="Table relationships")
    indexes: List[str] = Field(default=[], description="Index definitions")
    constraints: List[str] = Field(default=[], description="Data constraints")
    migrations: List[str] = Field(default=[], description="Migration strategy")
    
    @field_validator('database_type', mode='before')
    @classmethod
    def normalize_database_type(cls, v):
        """Normalize database_type to valid values"""
        if not v or not isinstance(v, str):
            return "other"
        
        v_lower = str(v).lower().strip()
        
        # Handle empty strings, null, none
        if not v_lower or v_lower in ["null", "none", "", "undefined"]:
            return "other"
        
        # Map variations to valid values
        if "postgres" in v_lower or "psql" in v_lower:
            return "postgresql"
        elif "mongo" in v_lower:
            return "mongodb"
        elif "mysql" in v_lower or v_lower == "mariadb":
            return "mysql"
        elif "sqlite" in v_lower:
            return "sqlite"
        elif v_lower in ["postgresql", "mongodb", "mysql", "sqlite", "other"]:
            return v_lower
        elif "sql" in v_lower and "no" not in v_lower:
            # Generic SQL database
            return "other"
        else:
            return "other"


class SecurityAudit(BaseModel):
    """Security audit results"""
    vulnerabilities: List[Dict[str, str]] = Field(default=[], description="Vulnerabilities found")
    security_score: float = Field(..., ge=0, le=10, description="Security score")
    recommendations: List[str] = Field(default=[], description="Security recommendations")
    compliance_checks: Dict[str, bool] = Field(default_factory=dict, description="Compliance status")


class PerformanceAnalysis(BaseModel):
    """Performance analysis results"""
    bottlenecks: List[str] = Field(default=[], description="Performance bottlenecks")
    optimization_suggestions: List[str] = Field(default=[], description="Optimization suggestions")
    estimated_complexity: Dict[str, str] = Field(..., description="Time/space complexity")
    scalability_assessment: str = Field(..., description="Scalability assessment")


class DebugReport(BaseModel):
    """Debug report"""
    issues_found: List[Dict[str, Any]] = Field(..., description="Issues detected")
    fixes_applied: List[Dict[str, Any]] = Field(default=[], description="Fixes applied")
    remaining_issues: List[str] = Field(default=[], description="Unresolved issues")
    debug_logs: List[str] = Field(default=[], description="Debug logs")


class ExecutionResult(BaseModel):
    """Code execution result"""
    success: bool = Field(..., description="Execution successful")
    output: str = Field(..., description="Execution output")
    errors: List[str] = Field(default=[], description="Errors encountered")
    test_results: Dict[str, Any] = Field(default={}, description="Test execution results")
    execution_time: float = Field(..., description="Execution time in seconds")


class DeploymentPlan(BaseModel):
    """Deployment configuration"""
    deployment_type: str = Field(..., description="Deployment type (container, serverless, etc)")
    infrastructure: Dict[str, Any] = Field(..., description="Infrastructure requirements")
    configuration_files: List[Dict[str, str]] = Field(..., description="Config files needed")
    environment_variables: Dict[str, str] = Field(default={}, description="Environment variables")
    ci_cd_pipeline: List[str] = Field(default=[], description="CI/CD steps")


class AgentHealthStatus(BaseModel):
    """Agent health status"""
    agent: AgentRole = Field(..., description="Agent role")
    status: str = Field(..., description="Status (healthy/degraded/failed)")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    success_rate: float = Field(..., ge=0, le=1, description="Success rate")
    error_count: int = Field(default=0, description="Error count")
    average_response_time: float = Field(..., description="Average response time in seconds")


class EnhancedCodeGenerationResult(BaseModel):
    """Enhanced result with all phases"""
    request_id: str = Field(..., description="Unique request ID")
    status: str = Field(..., description="Generation status")
    current_phase: WorkflowPhase = Field(..., description="Current workflow phase")

    # Store original request data for resume
    original_request: Optional[Dict[str, Any]] = Field(None, description="Original request data")

    # Phase outputs
    requirements: Optional[Requirements] = Field(None, description="Requirements analysis")
    research: Optional[List[ResearchFindings]] = Field(None, description="Research findings")
    hld: Optional[HighLevelDesign] = Field(None, description="High-Level Design")
    modules: Optional[List[ModuleDesign]] = Field(None, description="Module designs")
    lld: Optional[List[LowLevelDesign]] = Field(None, description="Low-Level Designs")
    database_design: Optional[DatabaseDesign] = Field(None, description="Database design")
    ui_design: Optional[Dict[str, Any]] = Field(None, description="UI/UX Design")

    # Interactive clarification fields
    clarification_request: Optional[Dict[str, Any]] = Field(None, description="Clarification questions requested")
    clarification_response: Optional[Dict[str, Any]] = Field(None, description="User's clarification answers")
    tech_stack_decision: Optional[Dict[str, Any]] = Field(None, description="Tech stack decision with justifications")
    awaiting_clarifications: bool = Field(default=False, description="Whether system is waiting for user clarifications")

    code_files: List[Dict[str, Any]] = Field(default=[], description="Generated code files")
    test_files: List[Dict[str, Any]] = Field(default=[], description="Test files")
    documentation: List[Dict[str, Any]] = Field(default=[], description="Documentation files")
    config_files: List[Dict[str, Any]] = Field(default=[], description="Configuration files")

    security_audit: Optional[SecurityAudit] = Field(None, description="Security audit")
    performance_analysis: Optional[PerformanceAnalysis] = Field(None, description="Performance analysis")
    debug_report: Optional[DebugReport] = Field(None, description="Debug report")
    execution_result: Optional[ExecutionResult] = Field(None, description="Execution result")
    deployment_plan: Optional[DeploymentPlan] = Field(None, description="Deployment plan")

    agent_activities: List[Dict[str, Any]] = Field(default=[], description="Agent activities")
    agent_health: List[AgentHealthStatus] = Field(default=[], description="Agent health status")

    total_llm_usage: Dict[str, int] = Field(default={}, description="Total LLM usage")
    total_cost: float = Field(default=0.0, description="Total cost")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(None)

    errors: List[str] = Field(default=[], description="Errors encountered")
    warnings: List[str] = Field(default=[], description="Warnings")


class PhaseConfig(BaseModel):
    """Configuration for each phase"""
    phase: WorkflowPhase = Field(..., description="Phase name")
    enabled: bool = Field(default=True, description="Whether phase is enabled")
    agents: List[AgentRole] = Field(..., description="Agents to run in this phase")
    skip_on_failure: bool = Field(default=False, description="Continue if phase fails")
    timeout_seconds: int = Field(default=300, description="Phase timeout")
