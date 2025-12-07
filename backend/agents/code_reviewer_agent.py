"""
Code Reviewer Agent - Validates generated code for syntax errors and fixes them
Part of the Multi-Agent System with MCP Integration
"""
from typing import Dict, Any, List, Optional, Tuple
import json
import re
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class CodeReviewerAgent(BaseAgent):
    """
    Code Reviewer Agent that validates generated code for syntax errors.
    
    This agent:
    1. Checks each generated file for common syntax errors
    2. Validates bracket/brace matching
    3. Checks for incomplete code patterns
    4. Requests regeneration of files with errors
    
    Role in Multi-Agent System:
    - Receives generated code from CodeGeneratorAgent
    - Validates syntax before passing to TestGeneratorAgent
    - Reports and fixes errors found
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.CODE_GENERATOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.agent_name = "CodeReviewerAgent"

    def get_system_prompt(self) -> str:
        return """You are a Senior Code Reviewer. Fix the syntax errors in the provided code.

## YOUR TASK
The code has syntax errors. Fix ALL errors and return the COMPLETE corrected file.

## COMMON ISSUES TO FIX
1. Unclosed braces, brackets, or parentheses
2. Return statements outside of functions
3. Missing function declarations
4. Malformed strings (unclosed quotes, wrong concatenation)
5. Missing imports
6. Duplicate code blocks
7. Incomplete JSX elements

## RULES
1. Return the COMPLETE fixed file
2. NO COMMENTS in the code
3. Ensure all functions are properly closed
4. Ensure all JSX is valid
5. Keep the original functionality intact

Return ONLY the corrected code. No explanations, no markdown code blocks.
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process code review task"""
        files = task_data.get("files", [])
        architecture = task_data.get("architecture", {})
        
        return await self.review_and_fix_files(files, architecture)

    async def review_and_fix_files(
        self,
        files: List[Dict[str, Any]],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Review all files and fix any with syntax errors"""
        activity = await self.start_activity("Reviewing code for syntax errors")
        
        fixed_files = []
        errors_found = 0
        files_fixed = 0
        
        try:
            for file in files:
                filepath = file.get("filepath", "")
                content = file.get("content", "")
                language = file.get("language", "")
                
                if not self._should_validate(filepath, language):
                    fixed_files.append(file)
                    continue
                
                errors = self._check_syntax_errors(content, filepath)
                
                if errors:
                    errors_found += len(errors)
                    logger.warning(
                        "syntax_errors_found",
                        filepath=filepath,
                        error_count=len(errors),
                        errors=errors[:3]
                    )
                    
                    fixed_content = await self._fix_file(file, errors, architecture)
                    
                    if fixed_content and fixed_content != content:
                        file["content"] = fixed_content
                        files_fixed += 1
                        logger.info("file_fixed", filepath=filepath)
                
                fixed_files.append(file)
            
            await self.complete_activity("completed")
            
            logger.info(
                "code_review_completed",
                total_files=len(files),
                errors_found=errors_found,
                files_fixed=files_fixed
            )
            
            return {
                "files": fixed_files,
                "review_summary": {
                    "total_files": len(files),
                    "errors_found": errors_found,
                    "files_fixed": files_fixed
                }
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("code_review_failed", error=str(e))
            return {"files": files, "review_summary": {"error": str(e)}}

    def _should_validate(self, filepath: str, language: str) -> bool:
        """Check if file should be validated"""
        skip_extensions = [".json", ".md", ".css", ".sql", ".yaml", ".yml", ".env", ".gitignore", ".dockerignore"]
        skip_files = ["package.json", "tsconfig.json", "tailwind.config", "postcss.config", "next.config", "jest.config", "jest.setup"]
        
        filepath_lower = filepath.lower()
        
        for ext in skip_extensions:
            if filepath_lower.endswith(ext):
                return False
        
        for skip in skip_files:
            if skip in filepath_lower:
                return False
        
        return language in ["typescript", "javascript"] or filepath.endswith((".ts", ".tsx", ".js", ".jsx"))

    def _check_syntax_errors(self, content: str, filepath: str) -> List[str]:
        """Check for common syntax errors"""
        errors = []
        
        if not content or not content.strip():
            return ["Empty file"]
        
        brace_errors = self._check_bracket_balance(content)
        if brace_errors:
            errors.extend(brace_errors)
        
        if filepath.endswith((".tsx", ".jsx")):
            jsx_errors = self._check_jsx_errors(content)
            if jsx_errors:
                errors.extend(jsx_errors)
        
        string_errors = self._check_string_errors(content)
        if string_errors:
            errors.extend(string_errors)
        
        structure_errors = self._check_structure_errors(content, filepath)
        if structure_errors:
            errors.extend(structure_errors)
        
        return errors

    def _check_bracket_balance(self, content: str) -> List[str]:
        """Check if brackets/braces are balanced"""
        errors = []
        
        content_no_strings = self._remove_strings_and_comments(content)
        
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        
        for i, char in enumerate(content_no_strings):
            if char in '([{':
                stack.append((char, i))
            elif char in ')]}':
                if not stack:
                    errors.append(f"Unmatched closing '{char}' at position {i}")
                elif stack[-1][0] != pairs[char]:
                    errors.append(f"Mismatched bracket: expected closing for '{stack[-1][0]}', got '{char}'")
                else:
                    stack.pop()
        
        if stack:
            for bracket, pos in stack:
                errors.append(f"Unclosed '{bracket}' at position {pos}")
        
        return errors

    def _check_jsx_errors(self, content: str) -> List[str]:
        """Check for JSX-specific errors"""
        errors = []
        
        if "return (" in content or "return(" in content:
            return_blocks = re.findall(r'return\s*\([^)]*$', content, re.MULTILINE)
            if return_blocks:
                for block in return_blocks:
                    if block.count('(') > block.count(')'):
                        pass
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'^\s*<[a-zA-Z]', line) and i > 0:
                prev_lines = '\n'.join(lines[max(0, i-5):i])
                if 'return' not in prev_lines and 'const' not in prev_lines and '=' not in prev_lines:
                    if not any(c in prev_lines for c in ['(', '{', '[']):
                        errors.append(f"JSX element at line {i+1} may be outside a function")
        
        return errors

    def _check_string_errors(self, content: str) -> List[str]:
        """Check for string-related errors"""
        errors = []
        
        bad_patterns = [
            (r"'[^']*'[^']*'[^']*'", "Possible malformed string concatenation"),
            (r'method:\s*[\'"][A-Z]+[\'"],\s*[A-Z]+[\'"]', "Malformed method string (e.g., 'DELETE',PUT')"),
            (r'`[^`]*\$\{[^}]*$', "Unclosed template literal"),
        ]
        
        for pattern, message in bad_patterns:
            if re.search(pattern, content):
                errors.append(message)
        
        return errors

    def _check_structure_errors(self, content: str, filepath: str) -> List[str]:
        """Check for structural errors"""
        errors = []
        
        if filepath.endswith(("page.tsx", "page.ts")):
            export_match = re.search(r'export\s+default\s+function\s+(\w+)', content)
            if not export_match:
                if 'export default' not in content:
                    errors.append("Missing default export for page component")
        
        if filepath.endswith("route.ts"):
            has_handler = any(f"export async function {method}" in content or f"export function {method}" in content 
                           for method in ["GET", "POST", "PUT", "DELETE", "PATCH"])
            if not has_handler:
                errors.append("API route missing HTTP method handler (GET, POST, etc.)")
        
        return_count = content.count("return (")
        if return_count > 1:
            lines = content.split('\n')
            return_lines = [i for i, line in enumerate(lines) if 'return (' in line]
            if len(return_lines) > 1:
                for i in range(len(return_lines) - 1):
                    between = '\n'.join(lines[return_lines[i]:return_lines[i+1]])
                    if between.count('{') != between.count('}'):
                        errors.append(f"Possible duplicate return statement or unclosed function")
        
        return errors

    def _remove_strings_and_comments(self, content: str) -> str:
        """Remove strings and comments for bracket checking"""
        result = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
        result = re.sub(r'"(?:[^"\\]|\\.)*"', '""', result)
        result = re.sub(r"'(?:[^'\\]|\\.)*'", "''", result)
        result = re.sub(r'`(?:[^`\\]|\\.)*`', '``', result)
        return result

    async def _fix_file(
        self,
        file: Dict[str, Any],
        errors: List[str],
        architecture: Dict[str, Any]
    ) -> Optional[str]:
        """Use LLM to fix a file with syntax errors"""
        
        filepath = file.get("filepath", "")
        content = file.get("content", "")
        purpose = file.get("purpose", "")
        
        error_list = "\n".join(f"- {e}" for e in errors[:5])
        
        prompt = f"""Fix the syntax errors in this file:

## File: {filepath}
## Purpose: {purpose}

## Errors Found:
{error_list}

## Current Code:
```
{content}
```

## Instructions:
1. Fix ALL syntax errors
2. Ensure all brackets/braces are balanced
3. Ensure all functions are properly defined and closed
4. Fix any malformed strings
5. Keep the original functionality
6. Return the COMPLETE fixed file
7. NO COMMENTS

Return ONLY the corrected code, no explanations."""

        try:
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=6000
            )
            
            fixed_content = self._clean_response(response)
            
            remaining_errors = self._check_syntax_errors(fixed_content, filepath)
            if len(remaining_errors) < len(errors):
                return fixed_content
            
            return fixed_content
            
        except Exception as e:
            logger.error("fix_file_failed", filepath=filepath, error=str(e))
            return None

    def _clean_response(self, response: str) -> str:
        """Clean LLM response"""
        content = response.strip()
        
        if content.startswith("```typescript"):
            content = content[13:]
        elif content.startswith("```tsx"):
            content = content[6:]
        elif content.startswith("```javascript"):
            content = content[13:]
        elif content.startswith("```jsx"):
            content = content[6:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        return content.strip()

