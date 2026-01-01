"""
Modification Analyzer Agent
Intelligently analyzes modification requests and determines which files to modify/add
"""

import json
from typing import Dict, Any, List, Optional
from models.schemas import AgentRole
from agents.base_agent import BaseAgent
import structlog

logger = structlog.get_logger()


class ModificationAnalyzerAgent(BaseAgent):
    """
    Intelligent agent that analyzes modification requests and determines:
    1. Which existing files need to be modified
    2. Which new files need to be created
    3. The rationale for each decision
    
    This eliminates hardcoded keywords and manual file detection logic.
    """
    
    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.MODULE_DESIGNER,  # Reusing this role for analysis
            mcp_server=mcp_server,
            openai_client=openai_client
        )
    
    def get_system_prompt(self) -> str:
        return """You are a Modification Analyzer Agent specialized in understanding code modification requests.

Your job is to analyze a user's modification request and determine:
1. Which EXISTING files need to be modified (and why)
2. Which NEW files need to be created (and why)
3. Whether this is a simple modification or requires new files

IMPORTANT PRINCIPLES:
- Be SURGICAL: Only modify what's necessary
- PRESERVE working code: Never regenerate files that don't need changes
- Be ADDITIVE: Prefer creating new files over modifying existing ones when possible
- NEVER suggest full regeneration - always be specific about which files

Respond with JSON in this exact format:
{
  "modification_type": "targeted" | "additive" | "mixed",
  "existing_files_to_modify": [
    {
      "filepath": "path/to/file.tsx",
      "reason": "Why this file needs modification",
      "changes_needed": "Brief description of changes"
    }
  ],
  "new_files_to_create": [
    {
      "filepath": "path/to/newfile.tsx",
      "purpose": "Purpose of this new file",
      "file_type": "component" | "api" | "page" | "utility" | "config"
    }
  ],
  "rationale": "Overall reasoning for this approach"
}"""
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process modification analysis request"""
        return await self.analyze_modification(
            modification_request=task_data.get("modification_request", ""),
            existing_files=task_data.get("existing_files", []),
            architecture=task_data.get("architecture", {}),
            feature_plan=task_data.get("feature_plan", None)
        )
    
    async def analyze_modification(
        self,
        modification_request: str,
        existing_files: List[Dict[str, Any]],
        architecture: Dict[str, Any],
        feature_plan: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Intelligently analyze what needs to be modified/created
        
        Args:
            modification_request: User's modification request
            existing_files: List of existing files with metadata
            architecture: Current architecture info
            feature_plan: Optional approved feature plan for context
            
        Returns:
            Analysis with specific files to modify/create
        """
        activity = await self.start_activity("Analyzing modification request")
        
        try:
            # Build file summary for context
            file_summary = self._build_file_summary(existing_files)
            tech_stack = architecture.get("tech_stack", {})
            
            prompt = self._build_analysis_prompt(
                modification_request,
                file_summary,
                tech_stack,
                feature_plan
            )
            
            logger.info("analyzing_modification",
                       request_length=len(modification_request),
                       existing_files_count=len(existing_files))
            
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Low temperature for consistent analysis
                max_tokens=2000
            )
            
            analysis = self._parse_analysis_response(response)
            
            await self.complete_activity("completed")
            
            logger.info("modification_analysis_complete",
                       modification_type=analysis.get("modification_type"),
                       files_to_modify=len(analysis.get("existing_files_to_modify", [])),
                       new_files=len(analysis.get("new_files_to_create", [])))
            
            return analysis
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("modification_analysis_failed", error=str(e))
            raise
    
    def _build_file_summary(self, existing_files: List[Dict[str, Any]]) -> str:
        """Build a concise summary of existing files"""
        if not existing_files:
            return "No existing files"
        
        # Group files by type/category
        summary_lines = []
        for file_info in existing_files[:50]:  # Limit to 50 for token efficiency
            filepath = file_info.get("filepath", "")
            purpose = file_info.get("description", file_info.get("purpose", ""))
            language = file_info.get("language", "")
            
            summary_lines.append(f"- {filepath} ({language}): {purpose[:80]}")
        
        return "\n".join(summary_lines)
    
    def _build_analysis_prompt(
        self,
        modification_request: str,
        file_summary: str,
        tech_stack: Dict[str, Any],
        feature_plan: Dict[str, Any] = None
    ) -> str:
        """Build the analysis prompt"""
        
        # Add feature plan context if available
        features_context = ""
        if feature_plan:
            core_features = feature_plan.get("core_features", [])
            if core_features:
                features_context = "\n## APPROVED FEATURES (User-Confirmed)\n"
                features_context += "The user originally requested these features:\n"
                for i, feature in enumerate(core_features, 1):
                    features_context += f"{i}. {feature.get('name')}: {feature.get('description')}\n"
                features_context += "\nUse this context to understand what's missing or what the user is referring to.\n"
        
        return f"""Analyze this modification request and determine which files to modify/create.

## MODIFICATION REQUEST
{modification_request}

## EXISTING FILES
{file_summary}
{features_context}

## TECHNOLOGY STACK
{json.dumps(tech_stack, indent=2)}

## YOUR TASK
Analyze the modification request and determine:
1. Which EXISTING files need modification (be specific)
2. Which NEW files need to be created (if any)
3. The rationale for your decisions

GUIDELINES:
- Be SURGICAL: Only modify what's absolutely necessary
- Be SPECIFIC: Name exact files, not categories
- Be ADDITIVE: Prefer new files over modifying existing ones when possible
- Consider the approved features - if user is asking for something from that list, implement it completely
- NEVER suggest regenerating everything
- If the request is vague, make reasonable assumptions based on approved features

Respond with the JSON format specified in your system prompt."""
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM analysis response"""
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            analysis = json.loads(response)
            
            # Validate required fields
            if "modification_type" not in analysis:
                analysis["modification_type"] = "mixed"
            
            if "existing_files_to_modify" not in analysis:
                analysis["existing_files_to_modify"] = []
            
            if "new_files_to_create" not in analysis:
                analysis["new_files_to_create"] = []
            
            if "rationale" not in analysis:
                analysis["rationale"] = "Analysis completed"
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error("failed_to_parse_analysis", error=str(e), response=response[:200])
            # Return safe fallback
            return {
                "modification_type": "mixed",
                "existing_files_to_modify": [],
                "new_files_to_create": [],
                "rationale": "Failed to parse analysis, will attempt smart modification"
            }

