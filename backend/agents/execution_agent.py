"""
Execution Agent - Executes applications, detects errors, and fixes them automatically

This agent:
1. PRE-VALIDATES code using ValidationPipelineAgent (fast, deterministic fixes)
2. Executes generated applications
3. Captures runtime errors and build errors
4. Uses pattern-based fixes first, LLM only as last resort
5. Retries execution with fixed code
"""

import asyncio
import os
import re
import shutil
import signal
import subprocess
import tempfile
import json
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from datetime import datetime
import structlog

from utils.gemini_client import get_gemini_client
from agents.validation_pipeline_agent import ValidationPipelineAgent

logger = structlog.get_logger()

# Track running processes
running_processes: Dict[str, subprocess.Popen] = {}
running_ports: Dict[str, int] = {}

BASE_PORT = 3001
MAX_FIX_ATTEMPTS = 8  # Reduced - ValidationPipelineAgent handles most errors upfront
DOCKER_EXECUTION_ENABLED = True


class ExecutionAgent:
    """Agent that executes applications and fixes runtime errors"""
    
    def __init__(self):
        self.name = "execution_agent"
        self.description = "Executes applications, detects errors, and fixes them automatically"
        self.gemini_client = get_gemini_client()
        self.current_files: List[Dict[str, Any]] = []
        self.project_dir: Optional[str] = None
        self.error_history: List[str] = []
        # Initialize the validation pipeline for pre-execution validation
        self.validation_pipeline = ValidationPipelineAgent()
        logger.info("agent_initialized", name=self.name)
    
    def get_next_available_port(self) -> int:
        """Find the next available port starting from BASE_PORT"""
        import socket
        
        port = BASE_PORT
        while port < BASE_PORT + 100:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('0.0.0.0', port))
                    return port
                except socket.error:
                    port += 1
        
        raise RuntimeError("No available ports found")
    
    async def save_files_to_disk(self, files: List[Dict[str, Any]], base_path: str) -> None:
        """Save generated files to disk"""
        for file_data in files:
            filepath = file_data.get("filepath", "")
            content = file_data.get("content", "")
            
            if not filepath or not content:
                continue
            
            full_path = os.path.join(base_path, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("file_saved", filepath=filepath)
    
    def detect_project_type(self, files: List[Dict[str, Any]]) -> str:
        """Detect the type of project from the files"""
        filepaths = [f.get("filepath", "") for f in files]
        
        if any("next.config" in fp for fp in filepaths) or any("pages/" in fp or "app/" in fp for fp in filepaths):
            return "nextjs"
        
        if any("package.json" in fp for fp in filepaths):
            for f in files:
                if f.get("filepath") == "package.json":
                    try:
                        pkg = json.loads(f.get("content", "{}"))
                        deps = pkg.get("dependencies", {})
                        if "next" in deps:
                            return "nextjs"
                        if "react-scripts" in deps:
                            return "cra"
                        if "react" in deps:
                            return "react-vite"
                    except:
                        pass
        
        if any(fp.endswith(".html") for fp in filepaths):
            return "static"
        
        if any(fp.endswith(".py") for fp in filepaths):
            return "python"
        
        return "unknown"
    
    async def cleanup_directory(self, project_dir: str) -> None:
        """Safely clean up a project directory"""
        if not os.path.exists(project_dir):
            return
        
        # Stop any running process first
        if project_dir in running_processes:
            try:
                process = running_processes[project_dir]
                if os.name != 'nt':
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except:
                        process.terminate()
                else:
                    process.terminate()
                await asyncio.sleep(2)
                if process.poll() is None:
                    if os.name != 'nt':
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except:
                            process.kill()
                    else:
                        process.kill()
            except Exception as e:
                logger.warning("cleanup_process_error", error=str(e))
            finally:
                if project_dir in running_processes:
                    del running_processes[project_dir]
                if project_dir in running_ports:
                    del running_ports[project_dir]
        
        # Try multiple times to remove the directory
        for attempt in range(3):
            try:
                # First, try to remove any problematic directories
                for root, dirs, files in os.walk(project_dir, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            os.chmod(file_path, 0o777)
                            os.remove(file_path)
                        except:
                            pass
                    for name in dirs:
                        try:
                            dir_path = os.path.join(root, name)
                            os.chmod(dir_path, 0o777)
                            os.rmdir(dir_path)
                        except:
                            pass
                
                shutil.rmtree(project_dir, ignore_errors=True)
                
                if not os.path.exists(project_dir):
                    return
                    
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning("cleanup_attempt_failed", attempt=attempt, error=str(e))
                await asyncio.sleep(1)
        
        # If still exists, just move it aside
        if os.path.exists(project_dir):
            try:
                backup_dir = f"{project_dir}_old_{int(datetime.now().timestamp())}"
                shutil.move(project_dir, backup_dir)
            except:
                pass
    
    async def analyze_error(
        self, 
        error_message: str, 
        files: List[Dict[str, Any]],
        strategy: str = "standard",
        error_type: str = "general"
    ) -> Dict[str, Any]:
        """Use LLM to analyze an error and propose fixes"""
        
        # Get relevant file contents - prioritize files mentioned in error
        file_contents = ""
        error_files = self._extract_files_from_error(error_message)
        
        # First add files mentioned in the error
        for f in files:
            filepath = f.get("filepath", "")
            content = f.get("content", "")
            if any(ef in filepath for ef in error_files):
                file_contents += f"\n\n--- {filepath} ---\n{content}"
        
        # Then add remaining files up to limit
        for f in files[:15]:
            filepath = f.get("filepath", "")
            content = f.get("content", "")
            if content and f"--- {filepath} ---" not in file_contents:
                file_contents += f"\n\n--- {filepath} ---\n{content[:3000]}"
        
        system_instruction = """You are an expert debugger specializing in TypeScript, React, and Jest testing.
Your job is to fix errors by providing COMPLETE fixed file content.
NEVER delete tests or functionality - FIX the actual issue."""
        
        # Check if this is a test failure
        is_test_failure = any(x in error_message.lower() for x in [
            'test failed', 'expect(', 'received:', 'expected:', 'jest',
            'test suites:', 'tests:', 'toequal', 'tobe', 'tohave'
        ])
        
        if is_test_failure or error_type == "test":
            prompt = self._build_test_fix_prompt(error_message, file_contents)
        elif strategy == "desperate":
            prompt = f"""CRITICAL ERROR: The application failed to run after multiple attempts.
You must perform a DEEP DEBUGGING analysis to fix the root cause.

ERROR MESSAGE:
{error_message[:3000]}

RELEVANT FILES:
{file_contents[:25000]}

INSTRUCTIONS:
1. Do NOT delete or comment out failing tests. FIX the code to make them pass.
2. Check for mismatching imports/exports (e.g. default vs named exports).
3. Check for missing dependencies in package.json.
4. Check for syntax errors or typos in variable names.
5. If a component is using a property that doesn't exist, define it or fix the usage.
6. Your goal is to produce working, correct code.

Respond with JSON:
{{
    "error_type": "test_error",
    "root_cause": "Brief explanation",
    "fixes": [
        {{
            "filepath": "path/to/file.ext",
            "action": "replace",
            "old_content": "",
            "new_content": "COMPLETE fixed file content",
            "explanation": "why this fix is needed"
        }}
    ]
}}
"""
        else:
            prompt = f"""Analyze this application error and provide fixes.

ERROR MESSAGE:
{error_message[:2000]}

PREVIOUS ERRORS IN THIS SESSION:
{chr(10).join(self.error_history[-3:]) if self.error_history else 'None'}

RELEVANT FILES:
{file_contents[:20000]}

INSTRUCTIONS:
1. Identify the root cause (missing dependency, syntax error, duplicate definition, etc.)
2. Provide EXACT fixes for the files.
3. If modules are missing (e.g., 'Module not found'), check package.json and add them.
4. If duplicate definitions exist, rename or remove one.
5. If syntax errors exist, provide the corrected code.
6. YOU MUST PROVIDE A FIX. Do not return empty fixes.
7. Do NOT simply delete code to fix errors. Fix the logic.

Respond with a JSON object containing:
{{
    "error_type": "build_error" | "runtime_error" | "dependency_error" | "config_error",
    "root_cause": "Brief explanation of the root cause",
    "fixes": [
        {{
            "filepath": "path/to/file.ext",
            "action": "replace" | "create" | "delete",
            "old_content": "content to find and replace (if action is replace)",
            "new_content": "new content to insert",
            "explanation": "why this fix is needed"
        }}
    ]
}}
"""
        
        try:
            response = await self.gemini_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_instruction,
                max_tokens=8000  # Increased for full file replacements
            )
            
            content = response.get("content", "")
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                logger.info("error_analysis_complete", 
                           fixes_count=len(result.get("fixes", [])),
                           error_type=result.get("error_type"))
                return result
            
            return {"error": "Could not parse fix response", "raw": content}
            
        except Exception as e:
            logger.error("error_analysis_failed", error=str(e))
            return {"error": str(e)}
    
    def _extract_files_from_error(self, error_message: str) -> List[str]:
        """Extract file paths mentioned in error message"""
        patterns = [
            r'at\s+(?:Object\.|Module\.|)(?:\w+\s+)?\(([^:)]+)',  # at Object.fn (file.ts:1:1)
            r'(?:in|from)\s+[\'"]?([^\s\'"]+\.(?:ts|tsx|js|jsx))',  # in/from file.ts
            r'([a-zA-Z0-9_\-./]+\.(?:ts|tsx|js|jsx))(?::\d+)?',  # file.ts:123
            r'FAIL\s+([^\s]+)',  # FAIL src/file.test.ts
        ]
        
        files = set()
        for pattern in patterns:
            matches = re.findall(pattern, error_message)
            for match in matches:
                # Clean up the path
                clean = match.strip().strip("'\"")
                if clean and not clean.startswith('node_modules'):
                    files.add(clean)
        
        return list(files)
    
    def _build_test_fix_prompt(self, error_message: str, file_contents: str) -> str:
        """Build a specialized prompt for fixing test failures"""
        return f"""FIX FAILING UNIT TESTS

The tests are failing. You need to fix the SOURCE CODE (not the tests) to make them pass.

## TEST OUTPUT:
```
{error_message[:4000]}
```

## SOURCE FILES:
{file_contents[:25000]}

## ANALYSIS STEPS:
1. Look at what the test expects vs what it receives
2. Find the source file that contains the function/component being tested
3. Fix the source code to return/render what the test expects
4. If the test imports something that doesn't exist, create it in the source file

## COMMON TEST FIXES:
- "Expected X but received Y" → Fix the source function to return X
- "Cannot find module" → Create the missing file or fix the import path
- "is not a function" → Export the function from the source file
- "is not defined" → Add the missing import or define the variable

## RULES:
1. DO NOT modify or delete the test files
2. Fix the SOURCE CODE to match what tests expect
3. Return COMPLETE file content for fixes
4. Provide the full file path for each fix

Respond with JSON:
{{
    "error_type": "test_error",
    "root_cause": "Brief explanation of why tests fail",
    "fixes": [
        {{
            "filepath": "src/path/to/source.ts",
            "action": "replace",
            "old_content": "",
            "new_content": "COMPLETE FIXED FILE CONTENT HERE",
            "explanation": "Fixed X to return Y as test expects"
        }}
    ]
}}
"""
    
    async def apply_fixes(
        self, 
        fixes: List[Dict[str, Any]], 
        files: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Apply fixes to the files and return updated files list"""
        updated_files = [f.copy() for f in files]  # Deep copy
        applied_fixes = []
        
        for fix in fixes:
            filepath = fix.get("filepath", "")
            action = fix.get("action", "replace")
            new_content = fix.get("new_content", "")
            old_content = fix.get("old_content", "")
            
            if not filepath or not new_content:
                logger.warning("invalid_fix", filepath=filepath, has_content=bool(new_content))
                continue
            
            if action == "create":
                # Add new file
                updated_files.append({
                    "filepath": filepath,
                    "filename": os.path.basename(filepath),
                    "content": new_content,
                    "language": self.detect_language(filepath),
                    "description": fix.get("explanation", "Auto-generated fix")
                })
                applied_fixes.append(f"Created {filepath}")
                logger.info("fix_created_file", filepath=filepath)
                
            elif action == "delete":
                # Remove file
                updated_files = [f for f in updated_files if not self._paths_match(f.get("filepath", ""), filepath)]
                applied_fixes.append(f"Deleted {filepath}")
                
            elif action == "replace":
                # Find and update file using fuzzy matching
                matched_idx = self._find_matching_file(updated_files, filepath)
                
                if matched_idx is not None:
                    actual_filepath = updated_files[matched_idx].get("filepath", "")
                    content = updated_files[matched_idx].get("content", "")
                    
                    if old_content and old_content in content:
                        content = content.replace(old_content, new_content, 1)
                        logger.info("fix_partial_replace", filepath=actual_filepath)
                    else:
                        # Full file replacement
                        content = new_content
                        logger.info("fix_full_replace", filepath=actual_filepath, content_len=len(new_content))
                    
                    updated_files[matched_idx] = {
                        **updated_files[matched_idx], 
                        "content": content
                    }
                    applied_fixes.append(f"Updated {actual_filepath}")
                else:
                    # File not found, create it
                    logger.warning("fix_file_not_found_creating", requested=filepath)
                    updated_files.append({
                        "filepath": filepath,
                        "filename": os.path.basename(filepath),
                        "content": new_content,
                        "language": self.detect_language(filepath),
                        "description": fix.get("explanation", "Auto-generated fix")
                    })
                    applied_fixes.append(f"Created {filepath} (was missing)")
        
        logger.info("fixes_applied", total=len(applied_fixes), fixes=applied_fixes)
        return updated_files, applied_fixes
    
    def _find_matching_file(self, files: List[Dict[str, Any]], target_path: str) -> Optional[int]:
        """Find a file in the list that matches the target path (fuzzy matching)"""
        target_normalized = self._normalize_path(target_path)
        target_basename = os.path.basename(target_path)
        
        # First try exact match
        for i, f in enumerate(files):
            if self._normalize_path(f.get("filepath", "")) == target_normalized:
                return i
        
        # Then try matching by filename + partial path
        for i, f in enumerate(files):
            file_path = f.get("filepath", "")
            if file_path.endswith(target_path) or target_path.endswith(file_path):
                logger.info("fuzzy_path_match", target=target_path, matched=file_path)
                return i
        
        # Finally try just filename match (risky but better than nothing)
        for i, f in enumerate(files):
            if os.path.basename(f.get("filepath", "")) == target_basename:
                logger.warning("basename_only_match", target=target_path, matched=f.get("filepath"))
                return i
        
        return None
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for comparison"""
        # Remove leading ./ or /
        path = path.lstrip("./").lstrip("/")
        # Normalize separators
        path = path.replace("\\", "/")
        return path.lower()
    
    def _paths_match(self, path1: str, path2: str) -> bool:
        """Check if two paths refer to the same file"""
        return self._normalize_path(path1) == self._normalize_path(path2)
    
    def detect_language(self, filepath: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".json": "json",
            ".html": "html",
            ".css": "css",
            ".md": "markdown"
        }
        ext = os.path.splitext(filepath)[1].lower()
        return ext_map.get(ext, "text")
    
    def has_docker_files(self, files: List[Dict[str, Any]]) -> bool:
        """Check if Docker files are present in the generated files"""
        filepaths = [f.get("filepath", "") for f in files]
        return "docker-compose.yml" in filepaths or "Dockerfile" in filepaths
    
    async def check_docker_available(self) -> bool:
        """Check if Docker and Docker Compose are available"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode != 0:
                return False
            
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            return process.returncode == 0
        except Exception:
            return False
    
    async def run_docker_compose_up(
        self, 
        project_dir: str, 
        port: int
    ) -> Tuple[bool, str, Optional[subprocess.Popen]]:
        """Run docker-compose up and return success status, output, and process"""
        
        env = os.environ.copy()
        env["APP_PORT"] = str(port)
        
        try:
            process = subprocess.Popen(
                ["docker", "compose", "up", "--build"],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            import socket
            start_time = asyncio.get_event_loop().time()
            timeout = 180
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                if process.poll() is not None:
                    output = process.stdout.read().decode() if process.stdout else ""
                    return False, f"Process exited: {output}", None
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.settimeout(1)
                        s.connect(('0.0.0.0', port))
                        return True, "", process
                    except:
                        await asyncio.sleep(2)
            
            return False, "Docker services failed to start within 180 seconds", process
            
        except Exception as e:
            return False, str(e), None
    
    async def stop_docker_compose(self, project_dir: str) -> bool:
        """Stop docker-compose services"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "down", "-v",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=60)
            return True
        except Exception as e:
            logger.warning("docker_compose_stop_error", error=str(e))
            return False
    
    async def run_npm_install(self, project_dir: str) -> Tuple[bool, str]:
        """Run npm install and return success status and output"""
        try:
            # Optimize npm install with flags for speed and less noise
            process = await asyncio.create_subprocess_exec(
                "npm", "install", "--legacy-peer-deps", "--no-audit", "--no-fund", "--prefer-offline",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300 # Increased timeout to 5 mins for slow networks
            )
            
            output = stdout.decode() + stderr.decode()
            return process.returncode == 0, output
            
        except asyncio.TimeoutError:
            return False, "npm install timed out after 5 minutes"
        except Exception as e:
            return False, str(e)
    
    async def run_npm_build(self, project_dir: str) -> Tuple[bool, str]:
        """Run npm run build to check for build errors"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npm", "run", "build",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120
            )
            
            output = stdout.decode() + stderr.decode()
            return process.returncode == 0, output
            
        except asyncio.TimeoutError:
            return False, "npm run build timed out"
        except Exception as e:
            return False, str(e)
    
    async def start_dev_server(
        self, 
        project_dir: str, 
        project_type: str, 
        port: int
    ) -> Tuple[bool, str, Optional[subprocess.Popen]]:
        """Start the development server and return success status, output, and process"""
        
        # Determine start command based on project type
        if project_type == "nextjs":
            cmd = ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", str(port)]
        elif project_type == "cra":
            cmd = ["npm", "start"]
        else:
            cmd = ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(port)]
        
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = "0.0.0.0"
        env["HOSTNAME"] = "0.0.0.0"
        env["BROWSER"] = "none"
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Wait for server to be ready
            import socket
            start_time = asyncio.get_event_loop().time()
            timeout = 60
            output_lines = []
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Check if process is still running
                if process.poll() is not None:
                    output = process.stdout.read().decode() if process.stdout else ""
                    return False, f"Process exited: {output}", None
                
                # Try to connect to the server
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.settimeout(1)
                        s.connect(('0.0.0.0', port))
                        return True, "", process
                    except:
                        await asyncio.sleep(1)
            
            return False, "Server failed to start within 60 seconds", process
            
        except Exception as e:
            return False, str(e), None
    
    async def run_tests(self, project_dir: str) -> Tuple[bool, str]:
        """Run tests and return success status and output"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npm", "test",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "CI": "true"}  # Force CI mode for single run
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120
            )
            
            output = stdout.decode() + stderr.decode()
            return process.returncode == 0, output
            
        except asyncio.TimeoutError:
            return False, "Tests timed out after 2 minutes"
        except Exception as e:
            return False, str(e)

    async def execute_with_auto_fix(
        self,
        files: List[Dict[str, Any]],
        conversation_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute application with automatic error detection and fixing
        
        Yields events during execution including:
        - log: Progress messages
        - error: Error messages
        - fix_applied: When a fix is applied
        - started: When app starts successfully
        - files_updated: When files are modified
        """
        self.current_files = files.copy()
        self.error_history = []
        
        project_type = self.detect_project_type(files)
        port = self.get_next_available_port()
        
        has_docker = self.has_docker_files(files)
        use_docker = False
        
        if has_docker and DOCKER_EXECUTION_ENABLED:
            docker_available = await self.check_docker_available()
            if docker_available:
                use_docker = True
        
        base_dir = os.path.join(tempfile.gettempdir(), "ai-generated-apps")
        os.makedirs(base_dir, exist_ok=True)
        
        self.project_dir = os.path.join(base_dir, f"app_{conversation_id[:8]}_{port}")
        
        execution_mode = "Docker" if use_docker else "Node.js"
        yield {
            "type": "log",
            "message": f"🚀 Starting application execution with {execution_mode} (auto-fix enabled)..."
        }
        
        # Clean up existing directory
        await self.cleanup_directory(self.project_dir)
        os.makedirs(self.project_dir, exist_ok=True)
        
        yield {
            "type": "log",
            "message": f"📁 Created project directory: {self.project_dir}"
        }
        
        # ==========================================
        # PRE-VALIDATION: Run ValidationPipelineAgent first
        # This catches and fixes most errors BEFORE execution
        # Using pattern-based fixes (fast, deterministic, free)
        # ==========================================
        yield {
            "type": "log",
            "message": "🔍 Running pre-validation pipeline (pattern-based fixes)..."
        }
        
        try:
            # Save files first for TypeScript check
            await self.save_files_to_disk(self.current_files, self.project_dir)
            
            # Run the validation pipeline
            validation_result = await self.validation_pipeline.validate_and_fix(
                files=self.current_files,
                project_dir=self.project_dir,
                max_iterations=5
            )
            
            if validation_result.get("fixes_applied"):
                fixes_applied = validation_result["fixes_applied"]
                self.current_files = validation_result["files"]
                
                yield {
                    "type": "fix_applied",
                    "message": f"🔧 Pre-validation fixed {len(fixes_applied)} issue(s): {', '.join(fixes_applied[:5])}{'...' if len(fixes_applied) > 5 else ''}",
                    "fixes": fixes_applied
                }
                
                yield {
                    "type": "files_updated",
                    "files": self.current_files
                }
                
                # Save the fixed files
                await self.save_files_to_disk(self.current_files, self.project_dir)
            
            if validation_result.get("success"):
                yield {
                    "type": "log",
                    "message": "✅ Pre-validation passed - code is ready for execution"
                }
            else:
                remaining = validation_result.get("remaining_errors", [])
                if remaining:
                    yield {
                        "type": "log",
                        "message": f"⚠️ Pre-validation completed with {len(remaining)} unresolved issue(s) - will attempt to fix during execution"
                    }
                    
        except Exception as e:
            logger.warning("pre_validation_error", error=str(e))
            yield {
                "type": "log",
                "message": f"⚠️ Pre-validation had issues: {str(e)[:100]} - continuing with execution"
            }
        
        for attempt in range(MAX_FIX_ATTEMPTS):
            # Determine strategy based on attempt count
            strategy = "standard"
            if attempt > 10:
                strategy = "desperate"
                yield {
                    "type": "log",
                    "message": "🔬 Entering DEEP DEBUGGING MODE: Analyzing root causes..."
                }

            # Save files
            yield {
                "type": "log",
                "message": f"💾 Saving {len(self.current_files)} files... (Attempt {attempt + 1}/{MAX_FIX_ATTEMPTS})"
            }
            
            await self.save_files_to_disk(self.current_files, self.project_dir)
            
            yield {
                "type": "log",
                "message": "✅ Files saved successfully"
            }
            
            # ==========================================
            # DOCKER EXECUTION PATH
            # ==========================================
            if use_docker:
                yield {
                    "type": "log",
                    "message": "🐳 Starting Docker containers..."
                }
                
                success, error_output, process = await self.run_docker_compose_up(
                    self.project_dir, port
                )
                
                if success and process:
                    running_processes[self.project_dir] = process
                    running_ports[self.project_dir] = port
                    
                    url = f"http://localhost:{port}"
                    
                    yield {
                        "type": "started",
                        "url": url,
                        "port": port,
                        "project_path": self.project_dir,
                        "message": f"✅ Docker containers running! App at {url}",
                        "files": self.current_files,
                        "execution_mode": "docker"
                    }
                    return
                else:
                    self.error_history.append(f"Docker error: {error_output[:500]}")
                    
                    yield {
                        "type": "log",
                        "message": f"⚠️ Docker startup failed. Analyzing..."
                    }
                    
                    fix_result = await self.analyze_error(error_output, self.current_files, strategy=strategy)
                    
                    if "fixes" in fix_result and fix_result["fixes"]:
                        self.current_files, applied = await self.apply_fixes(
                            fix_result["fixes"], 
                            self.current_files
                        )
                        
                        yield {
                            "type": "fix_applied",
                            "message": f"🔧 Applied fixes: {', '.join(applied)}",
                            "fixes": applied,
                            "root_cause": fix_result.get("root_cause", "")
                        }
                        
                        yield {
                            "type": "files_updated",
                            "files": self.current_files
                        }
                        
                        await self.stop_docker_compose(self.project_dir)
                        continue
                    else:
                        if attempt < MAX_FIX_ATTEMPTS - 1:
                            await self.stop_docker_compose(self.project_dir)
                            continue
                
                continue
            
            # ==========================================
            # STANDARD NODE.JS EXECUTION PATH
            # ==========================================
            yield {
                "type": "log",
                "message": "📦 Installing dependencies..."
            }
            
            install_success, install_output = await self.run_npm_install(self.project_dir)
            
            if not install_success:
                self.error_history.append(f"npm install error: {install_output[:500]}")
                
                yield {
                    "type": "log",
                    "message": f"⚠️ Dependency installation issue detected. Analyzing..."
                }
                
                fix_result = await self.analyze_error(install_output, self.current_files, strategy=strategy)
                
                if "fixes" in fix_result and fix_result["fixes"]:
                    self.current_files, applied = await self.apply_fixes(
                        fix_result["fixes"], 
                        self.current_files
                    )
                    
                    yield {
                        "type": "fix_applied",
                        "message": f"🔧 Applied fixes: {', '.join(applied)}",
                        "fixes": applied
                    }
                    
                    yield {
                        "type": "files_updated",
                        "files": self.current_files
                    }
                    
                    continue
                else:
                    yield {
                        "type": "log",
                        "message": "⚠️ Could not auto-fix dependency issue, continuing anyway..."
                    }
            
            yield {
                "type": "log",
                "message": "✅ Dependencies installed"
            }
            
            # ==========================================
            # STEP 1: RUN UNIT TESTS FIRST
            # ==========================================
            yield {
                "type": "log",
                "message": "🧪 Running unit tests..."
            }
            
            test_success, test_output = await self.run_tests(self.project_dir)
            
            if not test_success:
                self.error_history.append(f"Test failure: {test_output[:1000]}")
                
                # Extract which files failed from test output
                failed_files = self._extract_files_from_error(test_output)
                
                yield {
                    "type": "log",
                    "message": f"⚠️ Unit tests failed. Analyzing {len(failed_files)} related file(s)..."
                }
                
                # First try ValidationPipelineAgent's specialized test fix
                yield {
                    "type": "log",
                    "message": "🔧 Attempting pattern-based test fixes..."
                }
                
                try:
                    pipeline_result = await self.validation_pipeline.fix_test_failures(
                        test_output,
                        self.current_files
                    )
                    
                    if pipeline_result.get("success") and pipeline_result.get("fixes_applied"):
                        self.current_files = pipeline_result["files"]
                        applied = pipeline_result["fixes_applied"]
                        
                        yield {
                            "type": "fix_applied",
                            "message": f"🔧 Pipeline fixed {len(applied)} issue(s): {', '.join(applied[:3])}",
                            "fixes": applied
                        }
                        
                        yield {
                            "type": "files_updated",
                            "files": self.current_files
                        }
                        
                        await self.save_files_to_disk(self.current_files, self.project_dir)
                        continue  # Retry tests
                except Exception as e:
                    logger.warning("pipeline_test_fix_failed", error=str(e))
                
                # Fallback to LLM analysis
                yield {
                    "type": "log",
                    "message": "🤖 Using LLM for test fix analysis..."
                }
                
                # Use specialized test error analysis
                fix_result = await self.analyze_error(
                    test_output, 
                    self.current_files, 
                    strategy=strategy,
                    error_type="test"  # Specialized test prompt
                )
                
                # If standard analysis failed to find fixes, escalate immediately
                if not ("fixes" in fix_result and fix_result["fixes"]):
                    yield {
                        "type": "log",
                        "message": "⚠️ Standard analysis yielded no fixes for tests. Escalating to Deep Debugging..."
                    }
                    fix_result = await self.analyze_error(
                        test_output, 
                        self.current_files, 
                        strategy="desperate",
                        error_type="test"
                    )

                if "fixes" in fix_result and fix_result["fixes"]:
                    # Log what we're about to fix
                    logger.info(
                        "applying_test_fixes",
                        fix_count=len(fix_result["fixes"]),
                        files=[f.get("filepath") for f in fix_result["fixes"]]
                    )
                    
                    self.current_files, applied = await self.apply_fixes(
                        fix_result["fixes"], 
                        self.current_files
                    )
                    
                    yield {
                        "type": "fix_applied",
                        "message": f"🔧 Applied {len(applied)} fix(es) for tests: {', '.join(applied[:3])}{'...' if len(applied) > 3 else ''}",
                        "fixes": applied,
                        "root_cause": fix_result.get("root_cause", "")
                    }
                    
                    yield {
                        "type": "files_updated",
                        "files": self.current_files
                    }
                    
                    await self.save_files_to_disk(self.current_files, self.project_dir)
                    continue # Retry loop
                else:
                    yield {
                        "type": "log",
                        "message": "⚠️ Could not auto-fix test failures yet, retrying execution loop...",
                        "error_history": self.error_history
                    }
                    continue
            else:
                yield {
                    "type": "log",
                    "message": "✅ All unit tests passed!"
                }
            
            # ==========================================
            # STEP 2: RUN BUILD CHECK AFTER TESTS PASS
            # ==========================================
            if project_type in ["nextjs", "react-vite"]:
                yield {
                    "type": "log",
                    "message": "🔨 Running build check..."
                }
                
                build_success, build_output = await self.run_npm_build(self.project_dir)
                
                if not build_success:
                    self.error_history.append(f"Build error: {build_output[:1000]}")
                    
                    yield {
                        "type": "log",
                        "message": "⚠️ Build error detected. Analyzing..."
                    }
                    
                    fix_result = await self.analyze_error(build_output, self.current_files, strategy=strategy)
                    
                    # If standard analysis failed to find fixes, escalate immediately
                    if not ("fixes" in fix_result and fix_result["fixes"]):
                        yield {
                            "type": "log",
                            "message": "⚠️ Standard analysis yielded no fixes. Escalating to Deep Debugging..."
                        }
                        fix_result = await self.analyze_error(build_output, self.current_files, strategy="desperate")

                    if "fixes" in fix_result and fix_result["fixes"]:
                        self.current_files, applied = await self.apply_fixes(
                            fix_result["fixes"], 
                            self.current_files
                        )
                        
                        yield {
                            "type": "fix_applied",
                            "message": f"🔧 Applied fixes: {', '.join(applied)}",
                            "fixes": applied,
                            "root_cause": fix_result.get("root_cause", "")
                        }
                        
                        yield {
                            "type": "files_updated",
                            "files": self.current_files
                        }
                        
                        await self.save_files_to_disk(self.current_files, self.project_dir)
                        
                        continue
                    else:
                        yield {
                            "type": "log",
                            "message": "⚠️ Could not auto-fix build error yet, retrying execution loop...",
                            "error_history": self.error_history
                        }
                        # Do not return, just retry the loop
                        continue
            
            # ==========================================
            # STEP 3: START SERVER
            # ==========================================
            yield {
                "type": "log",
                "message": f"🚀 Starting development server on port {port}..."
            }
            
            success, error_output, process = await self.start_dev_server(
                self.project_dir, project_type, port
            )
            
            if success and process:
                running_processes[self.project_dir] = process
                running_ports[self.project_dir] = port
                
                url = f"http://localhost:{port}"
                
                yield {
                    "type": "started",
                    "url": url,
                    "port": port,
                    "project_path": self.project_dir,
                    "message": f"✅ Application running at {url}",
                    "files": self.current_files
                }
                return
            
            else:
                self.error_history.append(f"Server error: {error_output[:500]}")
                
                if attempt < MAX_FIX_ATTEMPTS - 1:
                    yield {
                        "type": "log",
                        "message": f"⚠️ Server failed to start. Analyzing error..."
                    }
                    
                    fix_result = await self.analyze_error(error_output, self.current_files, strategy=strategy)
                    
                    if "fixes" in fix_result and fix_result["fixes"]:
                        self.current_files, applied = await self.apply_fixes(
                            fix_result["fixes"], 
                            self.current_files
                        )
                        
                        yield {
                            "type": "fix_applied",
                            "message": f"🔧 Applied fixes: {', '.join(applied)}",
                            "fixes": applied,
                            "root_cause": fix_result.get("root_cause", "")
                        }
                        
                        yield {
                            "type": "files_updated",
                            "files": self.current_files
                        }
                        
                        # Clean up for retry
                        if process:
                            try:
                                process.terminate()
                            except:
                                pass
                        
                        continue
        
        # All attempts exhausted
        yield {
            "type": "error",
            "message": f"❌ Failed to start application after {MAX_FIX_ATTEMPTS} attempts.",
            "error_history": self.error_history,
            "files": self.current_files
        }
    
    async def stop_application(self) -> bool:
        """Stop the current running application (Docker or Node.js)"""
        if not self.project_dir:
            return False
        
        stopped = False
        
        if self.has_docker_files(self.current_files):
            stopped = await self.stop_docker_compose(self.project_dir)
        
        if self.project_dir in running_processes:
            process = running_processes[self.project_dir]
            
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                await asyncio.sleep(1)
                
                if process.poll() is None:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                
                stopped = True
                
            except Exception as e:
                logger.error("failed_to_stop_application", error=str(e))
        
        if self.project_dir in running_processes:
            del running_processes[self.project_dir]
        if self.project_dir in running_ports:
            del running_ports[self.project_dir]
        
        return stopped
    
    def get_updated_files(self) -> List[Dict[str, Any]]:
        """Get the current state of files (after any fixes)"""
        return self.current_files

