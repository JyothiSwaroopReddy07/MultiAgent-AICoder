"""
Testing Agent - Runs generated application, catches errors, and fixes them
"""
from typing import Dict, Any, List, Optional
import json
import re
import structlog
import asyncio
import subprocess
import os
import tempfile

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class TestingAgent(BaseAgent):
    """
    Testing Agent that validates generated code and fixes errors.
    
    This agent:
    1. Saves generated code to a temporary directory
    2. Installs dependencies
    3. Attempts to build/run the application
    4. Captures any errors
    5. Analyzes errors and proposes fixes
    6. Applies fixes and re-tests
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.CODE_GENERATOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.max_fix_attempts = 3
        self.project_dir = None

    def get_system_prompt(self) -> str:
        return """You are an Expert Debugging Engineer specializing in fixing build and runtime errors.

Your task is to analyze error messages and provide exact fixes for the generated code.

## Error Analysis Process

1. **Identify the Error Type**:
   - Module not found: Missing import or file
   - Syntax error: Code syntax issue
   - Type error: TypeScript/type mismatch
   - Runtime error: Logic or execution issue

2. **Determine the Root Cause**:
   - Is a file missing that needs to be created?
   - Is an import path incorrect?
   - Is there a typo or syntax issue?
   - Is a dependency missing from package.json?

3. **Provide the Fix**:
   - Specify exactly which file needs to be modified or created
   - Provide the complete corrected code
   - Explain what was wrong and why the fix works

## Response Format

```json
{
    "error_analysis": {
        "error_type": "module_not_found|syntax|type|runtime|dependency",
        "error_message": "The actual error message",
        "affected_file": "path/to/file.tsx",
        "root_cause": "Explanation of what's wrong"
    },
    "fixes": [
        {
            "action": "create|modify|delete",
            "filepath": "path/to/file.tsx",
            "content": "Complete file content if create/modify",
            "explanation": "Why this fix is needed"
        }
    ],
    "additional_dependencies": ["package-name"],
    "confidence": "high|medium|low"
}
```

IMPORTANT: 
- When creating missing files, provide COMPLETE working code
- Do NOT add any comments to the generated code
- Ensure all imports are correct
- Follow the project's existing patterns
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a testing task.
        
        Args:
            task_data: Contains 'files', 'architecture', 'problem_statement'
            
        Returns:
            Test and fix result
        """
        files = task_data.get("files", [])
        architecture = task_data.get("architecture", {})
        problem_statement = task_data.get("problem_statement", "")
        
        return await self.test_and_fix(files, architecture, problem_statement)

    async def test_and_fix(
        self,
        generated_files: List[Dict[str, Any]],
        architecture: Dict[str, Any],
        problem_statement: str
    ) -> Dict[str, Any]:
        """
        Test the generated code and fix any errors
        """
        activity = await self.start_activity("Testing generated application")
        
        all_fixes = []
        current_files = {f.get("filepath"): f for f in generated_files}
        
        try:
            for attempt in range(self.max_fix_attempts):
                logger.info(f"test_attempt", attempt=attempt + 1)
                
                test_result = await self._run_build_test(list(current_files.values()))
                
                if test_result["success"]:
                    logger.info("build_test_passed")
                    await self.complete_activity("completed")
                    return {
                        "success": True,
                        "files": list(current_files.values()),
                        "fixes_applied": all_fixes,
                        "attempts": attempt + 1,
                        "activity": self.current_activity.model_dump() if self.current_activity else None
                    }
                
                fixes = await self._analyze_and_fix_error(
                    test_result["error"],
                    current_files,
                    architecture,
                    problem_statement
                )
                
                if not fixes.get("fixes"):
                    logger.warning("no_fixes_generated", error=test_result["error"])
                    break
                
                for fix in fixes.get("fixes", []):
                    all_fixes.append(fix)
                    
                    if fix["action"] == "create" or fix["action"] == "modify":
                        filepath = fix["filepath"]
                        content = fix.get("content", "")
                        
                        if filepath in current_files:
                            current_files[filepath]["content"] = content
                        else:
                            current_files[filepath] = {
                                "filepath": filepath,
                                "filename": os.path.basename(filepath),
                                "content": content,
                                "language": self._detect_language(filepath),
                                "category": self._detect_category(filepath)
                            }
                    
                    elif fix["action"] == "delete" and fix["filepath"] in current_files:
                        del current_files[fix["filepath"]]
            
            await self.complete_activity("completed")
            return {
                "success": False,
                "files": list(current_files.values()),
                "fixes_applied": all_fixes,
                "attempts": self.max_fix_attempts,
                "last_error": test_result.get("error", "Unknown error"),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("testing_failed", error=str(e))
            return {
                "success": False,
                "files": list(current_files.values()),
                "fixes_applied": all_fixes,
                "error": str(e),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

    async def _run_build_test(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run build test on the generated files"""
        try:
            base_dir = tempfile.mkdtemp(prefix="test-build-")
            self.project_dir = base_dir
            
            for file_info in files:
                filepath = os.path.join(base_dir, file_info.get("filepath", ""))
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                content = file_info.get("content", "")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            
            package_json_path = os.path.join(base_dir, "package.json")
            if not os.path.exists(package_json_path):
                return {"success": False, "error": "No package.json found"}
            
            with open(package_json_path, "r") as f:
                package_data = json.load(f)
            
            is_nextjs = "next" in package_data.get("dependencies", {}) or "next" in package_data.get("devDependencies", {})
            is_vite = "vite" in package_data.get("devDependencies", {})
            
            install_result = subprocess.run(
                ["npm", "install", "--legacy-peer-deps"],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if install_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"npm install failed: {install_result.stderr}"
                }
            
            if is_nextjs:
                build_result = subprocess.run(
                    ["npx", "next", "build"],
                    cwd=base_dir,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env={**os.environ, "SKIP_ENV_VALIDATION": "true"}
                )
            elif is_vite:
                build_result = subprocess.run(
                    ["npx", "vite", "build"],
                    cwd=base_dir,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
            else:
                build_result = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=base_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            if build_result.returncode != 0:
                error_output = build_result.stderr or build_result.stdout
                return {
                    "success": False,
                    "error": error_output
                }
            
            return {"success": True}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Build timeout exceeded"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _analyze_and_fix_error(
        self,
        error: str,
        current_files: Dict[str, Dict[str, Any]],
        architecture: Dict[str, Any],
        problem_statement: str
    ) -> Dict[str, Any]:
        """Analyze error and generate fixes"""
        
        file_list = "\n".join([f"- {fp}" for fp in current_files.keys()])
        
        prompt = f"""Analyze this build error and provide fixes:

## Error Message
```
{error[:3000]}
```

## Current Project Files
{file_list}

## Architecture
{json.dumps(architecture, indent=2)[:2000]}

## Problem Statement
{problem_statement[:500]}

## Instructions
1. Identify what's causing the error
2. Determine if files need to be created, modified, or if imports need fixing
3. Provide complete, working code for any fixes
4. Do NOT include any comments in the code

Respond with a JSON fix plan."""

        response = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=6000
        )
        
        return self._parse_fix_response(response)

    def _parse_fix_response(self, response: str) -> Dict[str, Any]:
        """Parse fix response from LLM"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error("fix_parse_error", error=str(e))
            return {"fixes": [], "error": str(e)}

    def _detect_language(self, filepath: str) -> str:
        """Detect language from filepath"""
        ext_map = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".json": "json",
            ".css": "css",
            ".scss": "scss",
            ".md": "markdown",
            ".py": "python",
            ".prisma": "prisma"
        }
        ext = os.path.splitext(filepath)[1].lower()
        return ext_map.get(ext, "text")

    def _detect_category(self, filepath: str) -> str:
        """Detect category from filepath"""
        filepath_lower = filepath.lower()
        
        if "test" in filepath_lower or "spec" in filepath_lower:
            return "test"
        elif "component" in filepath_lower:
            return "frontend"
        elif "api" in filepath_lower or "route" in filepath_lower:
            return "backend"
        elif "lib" in filepath_lower or "util" in filepath_lower:
            return "shared"
        elif filepath.endswith(".json") or filepath.endswith("config"):
            return "config"
        else:
            return "frontend"


class DependencyValidator:
    """Validates that all file dependencies are satisfied"""
    
    @staticmethod
    def find_missing_dependencies(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find imports that reference non-existent files"""
        file_paths = {f.get("filepath", "") for f in files}
        missing = []
        
        import_patterns = [
            r"from ['\"](@/[^'\"]+)['\"]",
            r"from ['\"](\./[^'\"]+)['\"]",
            r"from ['\"](\.\./[^'\"]+)['\"]",
            r"import ['\"](@/[^'\"]+)['\"]",
            r"import ['\"](\./[^'\"]+)['\"]",
        ]
        
        for file_info in files:
            content = file_info.get("content", "")
            current_path = file_info.get("filepath", "")
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    resolved = DependencyValidator._resolve_import(match, current_path)
                    
                    possible_paths = [
                        resolved,
                        resolved + ".ts",
                        resolved + ".tsx",
                        resolved + ".js",
                        resolved + ".jsx",
                        resolved + "/index.ts",
                        resolved + "/index.tsx",
                    ]
                    
                    if not any(p in file_paths for p in possible_paths):
                        missing.append({
                            "import_path": match,
                            "resolved_path": resolved,
                            "importing_file": current_path,
                            "possible_paths": possible_paths
                        })
        
        return missing

    @staticmethod
    def _resolve_import(import_path: str, current_file: str) -> str:
        """Resolve an import path to an actual file path"""
        if import_path.startswith("@/"):
            return import_path[2:]
        
        if import_path.startswith("./") or import_path.startswith("../"):
            current_dir = os.path.dirname(current_file)
            return os.path.normpath(os.path.join(current_dir, import_path))
        
        return import_path

