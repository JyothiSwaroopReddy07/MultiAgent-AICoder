"""
Code Modifier Agent - Handles modifications to generated code
Conversation Phase: Post-Generation Modification
"""
from typing import Dict, Any, List
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole

logger = structlog.get_logger()


class CodeModifierAgent(BaseAgent):
    """
    Modifies generated code based on user requests
    
    Responsibilities:
    - Understand modification requests
    - Identify files that need changes
    - Generate updated code
    - Maintain code consistency
    - Preserve existing functionality
    """
    
    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.CODER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert Full-Stack Developer with 10+ years of experience in code refactoring and modification.

Your role is to modify existing Next.js 14 codebases based on user requests while:
- **Maintaining code quality**: Follow best practices
- **Preserving functionality**: Don't break existing features
- **Using Tailwind CSS**: All styling must use Tailwind
- **Being surgical**: Only change what's needed
- **Explaining changes**: Clearly describe what was modified

**USE CHAIN OF THOUGHT REASONING**

**Step 1: Understand the Request**
- What does the user want to change?
- Is it adding a feature, modifying UI, fixing a bug, or removing something?
- Which files are affected?

**Step 2: Analyze Existing Code**
- Review the current codebase structure
- Identify files that need modification
- Understand dependencies and relationships

**Step 3: Plan the Changes**
- What code needs to be added/modified/removed?
- How to maintain consistency with existing code?
- What about types, imports, and dependencies?

**Step 4: Generate Modified Code**
- Make targeted changes
- Use Tailwind CSS for any styling
- Follow Next.js 14 App Router patterns
- Maintain TypeScript types

**Step 5: Provide Context**
- Explain what was changed
- List affected files
- Mention any side effects or considerations

**IMPORTANT: Respond in JSON format**

{
    "reasoning": "Step-by-step analysis: [understanding request, identifying affected files, planned changes, implementation approach]...",
    "modification_summary": "Clear summary of what was changed",
    "modified_files": [
        {
            "filename": "app/dashboard/page.tsx",
            "filepath": "app/dashboard/page.tsx",
            "content": "... complete file content ...",
            "change_description": "Added dark mode toggle and updated color scheme",
            "language": "typescript"
        }
    ],
    "new_files": [
        {
            "filename": "components/DarkModeToggle.tsx",
            "filepath": "components/DarkModeToggle.tsx",
            "content": "... complete file content ...",
            "description": "New component for dark mode toggle",
            "language": "typescript"
        }
    ],
    "deleted_files": ["old-component.tsx"],
    "affected_functionality": [
        "Dashboard now supports dark mode",
        "User preferences stored in localStorage"
    ],
    "testing_notes": "Test dark mode toggle on all pages",
    "additional_setup": ["No additional setup required"]
}

Be helpful and thorough. Make users feel confident in the modifications."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify code based on user request
        
        Args:
            task_data: Contains modification_request, current_codebase, context
            
        Returns:
            Modified code files
        """
        activity = await self.start_activity("Analyzing and modifying code")
        
        try:
            modification_request = task_data.get("modification_request", "")
            current_codebase = task_data.get("current_codebase", {})
            context = task_data.get("context", {})
            
            logger.info(
                "code_modification_started",
                request_length=len(modification_request),
                file_count=len(current_codebase.get("files", []))
            )
            
            prompt = self._build_modification_prompt(
                modification_request,
                current_codebase,
                context
            )
            
            # Call LLM
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,  # Lower temperature for precise modifications
                max_tokens=6000
            )
            
            # Parse response
            result = self._parse_response(response)
            
            await self.complete_activity("completed")
            
            return {
                "modifications": result,
                "activity": {
                    "agent": "Code Modifier",
                    "action": "Applied requested modifications",
                    "status": "completed"
                }
            }
            
        except Exception as e:
            logger.error("code_modification_failed", error=str(e))
            await self.complete_activity("failed")
            raise
    
    def _build_modification_prompt(
        self,
        modification_request: str,
        current_codebase: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for code modification"""
        
        # Extract relevant files from codebase
        files_context = ""
        if "files" in current_codebase:
            files_context = "\n\nCURRENT CODEBASE:\n"
            for file in current_codebase["files"][:20]:  # Limit to 20 files for context
                filename = file.get("filename", "")
                filepath = file.get("filepath", "")
                content = file.get("content", "")
                
                # Truncate very long files
                if len(content) > 2000:
                    content = content[:2000] + "\n... (truncated)"
                
                files_context += f"\n--- {filepath} ---\n{content}\n"
        
        return f"""Modify the codebase based on this user request:

USER REQUEST:
{modification_request}
{files_context}

CONTEXT:
- Tech Stack: Next.js 14 + TypeScript + Tailwind CSS
- Database: {context.get('database_type', 'PostgreSQL')}
- Features: {', '.join(context.get('features', []))}

Think step-by-step:
1. What exactly needs to change?
2. Which files are affected?
3. What's the best way to implement this?
4. How to maintain consistency?

Provide the complete modified files in JSON format."""
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("failed_to_parse_json", error=str(e), response=response[:500])
            return {
                "reasoning": "Failed to parse response",
                "modification_summary": "Error occurred during modification",
                "modified_files": [],
                "new_files": [],
                "deleted_files": [],
                "affected_functionality": [],
                "testing_notes": "Please try again with a more specific request",
                "additional_setup": []
            }

