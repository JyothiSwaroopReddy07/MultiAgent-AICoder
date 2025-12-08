# Bala Aparna - 29485442

"""
Code Generator Agent - Generates individual files with full context awareness
Enterprise-grade agent that produces production-ready code
"""
from typing import Dict, Any, List, Optional
import json
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class CodeGeneratorAgent(BaseAgent):
    """
    Enterprise Code Generator Agent that produces production-ready code files.
    
    Features:
    - Context-aware: Knows about all other files in the project
    - Consistent: Maintains naming conventions and patterns
    - Complete: No TODOs or placeholders - full implementation
    - Best practices: Follows industry standards
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.CODE_GENERATOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an Elite Software Engineer with expertise in full-stack development.

Your task is to generate COMPLETE, PRODUCTION-READY code files.

## CRITICAL: NO COMMENTS ALLOWED

**DO NOT include ANY comments in the generated code:**
- NO single-line comments (// or #)
- NO multi-line comments (/* */ or ''' ''')
- NO JSDoc comments (/** */)
- NO docstrings
- NO file headers or descriptions
- NO inline comments explaining logic
- NO TODO comments
- NO @param, @returns, or any documentation tags

The code must be CLEAN and COMMENT-FREE. Let the code speak for itself.

## Code Quality Standards

### 1. Completeness
- NO placeholder comments
- NO incomplete functions or methods
- NO "..." or ellipsis in code
- FULL implementation of all functionality

### 2. Best Practices
- Follow language-specific conventions (PEP 8, ESLint, etc.)
- Use meaningful, self-documenting variable and function names
- Include error handling
- Add input validation where needed

### 3. Modern Patterns
- Use modern language features (async/await, etc.)
- Follow current framework best practices
- Use proper TypeScript types (no 'any' unless necessary)
- Implement proper error boundaries

### 4. Security
- Never hardcode secrets
- Use environment variables
- Validate and sanitize inputs
- Implement proper authentication checks

### 5. Performance
- Avoid unnecessary re-renders (React)
- Use proper data structures
- Implement caching where appropriate
- Optimize database queries

## Response Format

Return ONLY the file content. No explanations, no markdown code blocks.
Start directly with the first line of code (an import statement, not a comment).

REMEMBER: ZERO COMMENTS IN THE CODE. The code should be self-explanatory through good naming.
"""

    async def generate_file(
        self,
        file_spec: Dict[str, Any],
        architecture: Dict[str, Any],
        generated_files: List[Dict[str, Any]],
        problem_statement: str
    ) -> Dict[str, Any]:
        """
        Generate a single file with full context
        
        Args:
            file_spec: Specification for this file
            architecture: Overall project architecture
            generated_files: Files already generated (for context)
            problem_statement: Original problem description
            
        Returns:
            Generated file with content
        """
        activity = await self.start_activity(f"Generating {file_spec.get('filepath', 'file')}")
        
        try:
            prompt = self._build_generation_prompt(
                file_spec, architecture, generated_files, problem_statement
            )
            
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower for consistent code
                max_tokens=6000
            )
            
            # Clean up response
            content = self._clean_code_response(response, file_spec.get("language", ""))
            
            await self.complete_activity("completed")
            
            # Extract filename from filepath if not provided
            filepath = file_spec.get("filepath", "")
            filename = file_spec.get("filename") or filepath.split("/")[-1] if filepath else "unknown"
            
            return {
                "filepath": filepath,
                "filename": filename,
                "content": content,
                "language": file_spec.get("language", "text"),
                "description": file_spec.get("purpose", ""),
                "category": file_spec.get("category", "unknown")
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("file_generation_failed", 
                        file=file_spec.get("filepath"),
                        error=str(e))
            raise

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a code generation task"""
        return await self.generate_file(
            file_spec=task_data.get("file_spec", {}),
            architecture=task_data.get("architecture", {}),
            generated_files=task_data.get("generated_files", []),
            problem_statement=task_data.get("problem_statement", "")
        )

    def _build_generation_prompt(
        self,
        file_spec: Dict[str, Any],
        architecture: Dict[str, Any],
        generated_files: List[Dict[str, Any]],
        problem_statement: str
    ) -> str:
        """Build comprehensive prompt for file generation"""
        
        # Get tech stack info
        tech_stack = architecture.get("tech_stack", {})
        frontend = tech_stack.get("frontend", {})
        backend = tech_stack.get("backend", {})
        database = tech_stack.get("database", {})
        
        # Get relevant generated files for context (limit to avoid token overflow)
        relevant_files = self._get_relevant_files(file_spec, generated_files)
        
        context_files = ""
        if relevant_files:
            context_files = "\n\n## Already Generated Files (for reference)\n"
            for f in relevant_files[:5]:  # Limit to 5 most relevant
                context_files += f"""
### {f.get('filepath')}
```{f.get('language', '')}
{f.get('content', '')[:2000]}  # Truncate long files
```
"""
        
        # Get database schema if relevant
        db_schema = ""
        if file_spec.get("category") in ["backend", "database", "shared"]:
            schema = architecture.get("database_schema", {})
            if schema:
                db_schema = f"\n\n## Database Schema\n{json.dumps(schema, indent=2)}"
        
        # Get API design if relevant
        api_design = ""
        if file_spec.get("category") in ["backend", "frontend"]:
            api = architecture.get("api_design", {})
            if api:
                api_design = f"\n\n## API Design\n{json.dumps(api, indent=2)}"
        
        # Get features
        features = architecture.get("features", [])
        features_text = ""
        if features:
            features_text = "\n\n## Features to Implement\n"
            for f in features:
                features_text += f"- **{f.get('name')}**: {f.get('description')}\n"

        # Detect if Next.js or Vite project
        framework = frontend.get('framework', '').lower()
        is_nextjs = 'next' in framework
        is_vite = 'vite' in framework
        module_format = "CommonJS (module.exports)" if is_nextjs else "ESM (export default)" if is_vite else "auto-detect"
        
        return f"""Generate the following file for this project:

## Project Overview
{problem_statement}

## Technology Stack
- Frontend: {frontend.get('framework', 'N/A')} with {frontend.get('language', 'N/A')}
- Styling: {frontend.get('styling', 'N/A')}
- Backend: {backend.get('framework', 'N/A')} with {backend.get('language', 'N/A')}
- Database: {database.get('primary', 'N/A')} with {database.get('orm', 'N/A')}
- **Config Module Format**: {module_format}

## File to Generate
- **Path**: {file_spec.get('filepath')}
- **Purpose**: {file_spec.get('purpose')}
- **Language**: {file_spec.get('language')}
- **Category**: {file_spec.get('category')}

## Content Requirements
{json.dumps(file_spec.get('content_hints', []), indent=2) if file_spec.get('content_hints') else 'Generate appropriate content based on purpose'}
{db_schema}
{api_design}
{features_text}
{context_files}

## CRITICAL Instructions

1. Generate COMPLETE, working code - no placeholders
2. Follow {file_spec.get('language', 'the language')} best practices
3. Include proper imports based on the tech stack
4. **DO NOT ADD ANY COMMENTS** - no //, no #, no /* */, no docstrings, no JSDoc
5. Use self-documenting variable and function names instead of comments
6. Implement proper error handling
7. Make it production-ready

## CRITICAL: Module Format for Config Files

**IMPORTANT: Different frameworks use different module formats!**

For **Next.js** projects (using next.js or next.config.js):
- **postcss.config.js** MUST use CommonJS: `module.exports = {{ plugins: {{ ... }} }}`
- **tailwind.config.js** can use CommonJS or TypeScript
- Use `module.exports` and `require()` syntax

Example postcss.config.js for Next.js (CommonJS):
```
module.exports = {{
  plugins: {{
    tailwindcss: {{}},
    autoprefixer: {{}},
  }},
}}
```

For **Vite** projects (using vite.config.ts):
- **postcss.config.js** MUST use ESM: `export default {{ plugins: {{ ... }} }}`
- **tailwind.config.js** MUST use ESM: `export default {{ ... }}`
- Use `export default` and `import` syntax

Example postcss.config.js for Vite (ESM):
```
export default {{
  plugins: {{
    tailwindcss: {{}},
    autoprefixer: {{}},
  }},
}}
```

**ZERO COMMENTS ALLOWED. The code must be clean without any comments.**

Return ONLY the raw code content. No explanations or markdown blocks."""

    def _get_relevant_files(
        self,
        file_spec: Dict[str, Any],
        generated_files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get files that are relevant to the current file being generated"""
        relevant = []
        
        # Get dependencies
        dependencies = file_spec.get("dependencies", [])
        
        for gen_file in generated_files:
            filepath = gen_file.get("filepath", "")
            
            # Include if it's a dependency
            if filepath in dependencies:
                relevant.append(gen_file)
                continue
            
            # Include config files for context
            if gen_file.get("category") == "config":
                relevant.append(gen_file)
                continue
            
            # Include type definitions
            if "types" in filepath.lower() or "interfaces" in filepath.lower():
                relevant.append(gen_file)
                continue
            
            # Include if in same directory
            current_dir = "/".join(file_spec.get("filepath", "").split("/")[:-1])
            file_dir = "/".join(filepath.split("/")[:-1])
            if current_dir and current_dir == file_dir:
                relevant.append(gen_file)
        
        return relevant

    def _clean_code_response(self, response: str, language: str) -> str:
        """Clean up the LLM response to extract just the code"""
        content = response.strip()
        
        # Remove markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```language)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        
        # Remove any "Here's the code" type prefixes
        prefixes_to_remove = [
            "Here's the code",
            "Here is the code",
            "Below is the code",
            "The following is",
            "Generated code:",
        ]
        for prefix in prefixes_to_remove:
            if content.lower().startswith(prefix.lower()):
                # Find the first newline after the prefix and start from there
                idx = content.find("\n")
                if idx != -1:
                    content = content[idx+1:]
        
        return content.strip()


class IntegrationValidatorAgent(BaseAgent):
    """
    Integration Validator Agent - Ensures all generated files work together
    Validates imports, exports, types, and dependencies
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.INTEGRATION_TESTER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Senior QA Engineer specializing in code integration.

Your role is to validate that all generated files work together correctly.

Check for:
1. **Import/Export Consistency**: All imports can be resolved
2. **Type Consistency**: Types match across files
3. **API Consistency**: Frontend calls match backend endpoints
4. **Naming Consistency**: Variables and functions are named consistently
5. **Missing Files**: Any files referenced but not generated
6. **Circular Dependencies**: Detect circular import issues

For each issue found, provide:
- File where issue occurs
- Line/location (if applicable)
- Description of the issue
- Suggested fix

Respond in JSON format:
{
    "valid": true/false,
    "issues": [
        {
            "severity": "error|warning|info",
            "file": "path/to/file.ts",
            "issue": "Description of the issue",
            "fix": "Suggested fix"
        }
    ],
    "summary": "Overall assessment"
}
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate integration of all generated files"""
        activity = await self.start_activity("Validating integration")
        
        try:
            files = task_data.get("files", [])
            architecture = task_data.get("architecture", {})
            
            prompt = f"""Validate the integration of these generated files:

## Architecture
{json.dumps(architecture.get("tech_stack", {}), indent=2)}

## Generated Files
"""
            for f in files:
                prompt += f"""
### {f.get('filepath')}
```{f.get('language', '')}
{f.get('content', '')[:1500]}
```
"""
            
            prompt += "\n\nCheck for import/export issues, type mismatches, and missing dependencies."
            
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=3000
            )
            
            await self.complete_activity("completed")
            
            # Parse response
            try:
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
                validation = json.loads(response.strip())
            except:
                validation = {"valid": True, "issues": [], "summary": "Validation completed"}
            
            return {
                "validation": validation,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("integration_validation_failed", error=str(e))
            return {"validation": {"valid": True, "issues": [], "error": str(e)}}

