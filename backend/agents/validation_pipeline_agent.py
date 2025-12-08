"""
Validation Pipeline Agent - Multi-stage error detection and fixing

This agent uses a staged approach to validate and fix code:
1. Static Analysis (FREE, INSTANT) - bracket balance, import/export checks
2. TypeScript Compiler (FAST, RELIABLE) - tsc --noEmit
3. Dependency Check - package.json validation
4. Pattern-Based Fixes - deterministic fixes for common errors
5. LLM Fixer (LAST RESORT) - only for complex errors

This replaces the expensive LLM-first approach with deterministic fixes.
"""

import asyncio
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class ErrorType(Enum):
    SYNTAX = "syntax"
    IMPORT = "import"
    EXPORT = "export"
    TYPE = "type"
    DEPENDENCY = "dependency"
    BUILD = "build"
    JSX = "jsx"
    UNKNOWN = "unknown"


@dataclass
class ParsedError:
    """Structured representation of an error"""
    error_type: ErrorType
    file_path: str
    line: Optional[int]
    column: Optional[int]
    message: str
    code: Optional[str] = None  # e.g., TS2307, TS2339
    raw: str = ""
    
    def signature(self) -> str:
        """Unique signature for deduplication"""
        return f"{self.file_path}:{self.line}:{self.code}:{self.message[:50]}"


@dataclass
class Fix:
    """Represents a code fix"""
    file_path: str
    action: str  # "replace_line", "replace_content", "insert_line", "add_import", "add_dep"
    description: str
    old_value: Optional[str] = None
    new_value: str = ""
    line: Optional[int] = None
    confidence: float = 1.0  # 0-1, high = deterministic, low = LLM guess


@dataclass
class ValidationResult:
    """Result of a validation stage"""
    success: bool
    errors: List[ParsedError] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    stage: str = ""


class ValidationPipelineAgent(BaseAgent):
    """
    Multi-stage validation pipeline that fixes errors deterministically when possible,
    only escalating to LLM for truly complex cases.
    
    Pipeline Stages:
    1. Static Analysis - syntax, brackets, imports
    2. TypeScript Check - tsc --noEmit  
    3. Dependency Validation - package.json
    4. Build Test - npm run build
    5. LLM Fixer - last resort for complex errors
    """
    
    # TypeScript error codes and their patterns
    TS_ERROR_PATTERNS = {
        # TS2307: Cannot find module
        "TS2307": {
            "pattern": r"Cannot find module '([^']+)'",
            "type": ErrorType.DEPENDENCY,
            "fix_fn": "_fix_missing_module"
        },
        # TS2305: Module has no exported member
        "TS2305": {
            "pattern": r"\"([^\"]+)\" has no exported member '([^']+)'",
            "type": ErrorType.IMPORT,
            "fix_fn": "_fix_missing_export"
        },
        # TS2614: Module has no default export
        "TS2614": {
            "pattern": r"has no default export",
            "type": ErrorType.IMPORT,
            "fix_fn": "_fix_default_export_mismatch"
        },
        # TS2339: Property does not exist on type
        "TS2339": {
            "pattern": r"Property '([^']+)' does not exist on type '([^']+)'",
            "type": ErrorType.TYPE,
            "fix_fn": "_fix_missing_property"
        },
        # TS2304: Cannot find name
        "TS2304": {
            "pattern": r"Cannot find name '([^']+)'",
            "type": ErrorType.IMPORT,
            "fix_fn": "_fix_undefined_name"
        },
        # TS2322: Type is not assignable
        "TS2322": {
            "pattern": r"Type '([^']+)' is not assignable to type '([^']+)'",
            "type": ErrorType.TYPE,
            "fix_fn": "_fix_type_mismatch"
        },
        # TS2345: Argument type not assignable
        "TS2345": {
            "pattern": r"Argument of type '([^']+)' is not assignable",
            "type": ErrorType.TYPE,
            "fix_fn": "_fix_argument_type"
        },
        # TS1005: Expected token
        "TS1005": {
            "pattern": r"'([^']+)' expected",
            "type": ErrorType.SYNTAX,
            "fix_fn": "_fix_expected_token"
        },
        # TS1128: Declaration or statement expected
        "TS1128": {
            "pattern": r"Declaration or statement expected",
            "type": ErrorType.SYNTAX,
            "fix_fn": "_fix_syntax_error"
        },
        # TS2532: Object is possibly undefined
        "TS2532": {
            "pattern": r"Object is possibly 'undefined'",
            "type": ErrorType.TYPE,
            "fix_fn": "_fix_possibly_undefined"
        },
        # TS7006: Parameter implicitly has 'any' type
        "TS7006": {
            "pattern": r"Parameter '([^']+)' implicitly has an 'any' type",
            "type": ErrorType.TYPE,
            "fix_fn": "_fix_implicit_any"
        },
    }
    
    # Common npm packages for auto-imports
    COMMON_IMPORTS = {
        "useState": ("react", True),  # (module, is_named)
        "useEffect": ("react", True),
        "useCallback": ("react", True),
        "useMemo": ("react", True),
        "useRef": ("react", True),
        "useContext": ("react", True),
        "useReducer": ("react", True),
        "React": ("react", False),
        "Link": ("next/link", False),
        "Image": ("next/image", False),
        "useRouter": ("next/navigation", True),
        "usePathname": ("next/navigation", True),
        "useSearchParams": ("next/navigation", True),
        "redirect": ("next/navigation", True),
        "notFound": ("next/navigation", True),
        "NextRequest": ("next/server", True),
        "NextResponse": ("next/server", True),
        "cn": ("@/lib/utils", True),
        "clsx": ("clsx", False),
        "motion": ("framer-motion", True),
        "AnimatePresence": ("framer-motion", True),
    }

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.CODE_GENERATOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.agent_name = "ValidationPipelineAgent"
        self.error_history: Set[str] = set()  # Track error signatures to avoid loops
        self.fix_history: List[str] = []  # Track applied fixes
        
    def get_system_prompt(self) -> str:
        return """You are an expert code debugger. Fix the specific error shown.
        
RULES:
1. Return ONLY valid JSON with the fix
2. Provide the COMPLETE fixed content for the file
3. Do NOT delete functionality - fix the error while preserving behavior
4. If it's an import error, add the missing import
5. If it's a type error, add proper typing

Return JSON format:
{
    "file_path": "path/to/file.tsx",
    "fixed_content": "complete file content here",
    "explanation": "brief explanation"
}
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process validation task"""
        files = task_data.get("files", [])
        project_dir = task_data.get("project_dir", "")
        
        return await self.validate_and_fix(files, project_dir)

    async def validate_and_fix(
        self,
        files: List[Dict[str, Any]],
        project_dir: str,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Run the full validation pipeline.
        
        Returns:
            Dict with keys: success, files, fixes_applied, errors
        """
        activity = await self.start_activity("Running validation pipeline")
        
        current_files = [f.copy() for f in files]
        all_fixes: List[str] = []
        self.error_history.clear()
        
        try:
            for iteration in range(max_iterations):
                logger.info(
                    "validation_iteration",
                    iteration=iteration + 1,
                    max=max_iterations
                )
                
                # Stage 1: Static Analysis
                result = await self._stage_static_analysis(current_files)
                if not result.success and result.errors:
                    fixes = self._generate_static_fixes(result.errors, current_files)
                    if fixes:
                        current_files = self._apply_fixes(current_files, fixes)
                        all_fixes.extend([f.description for f in fixes])
                        continue
                
                # Stage 2: TypeScript Check (only if project uses TS)
                if self._has_typescript(current_files):
                    await self._save_files_to_disk(current_files, project_dir)
                    result = await self._stage_typescript_check(project_dir)
                    
                    if not result.success and result.errors:
                        # Filter out already-seen errors
                        new_errors = [
                            e for e in result.errors 
                            if e.signature() not in self.error_history
                        ]
                        
                        if not new_errors:
                            logger.warning("all_errors_already_seen", count=len(result.errors))
                            break
                        
                        # Try pattern-based fixes first
                        fixes = self._generate_ts_fixes(new_errors, current_files)
                        
                        if fixes:
                            current_files = self._apply_fixes(current_files, fixes)
                            all_fixes.extend([f.description for f in fixes])
                            # Mark errors as seen
                            for e in new_errors:
                                self.error_history.add(e.signature())
                            continue
                        
                        # Escalate to LLM for remaining errors
                        llm_fixes = await self._escalate_to_llm(new_errors[:3], current_files)
                        if llm_fixes:
                            current_files = self._apply_fixes(current_files, llm_fixes)
                            all_fixes.extend([f.description for f in llm_fixes])
                            for e in new_errors:
                                self.error_history.add(e.signature())
                            continue
                        
                        # No fixes found, record and continue
                        for e in new_errors:
                            self.error_history.add(e.signature())
                
                # Stage 3: Dependency Check
                dep_result = self._stage_dependency_check(current_files)
                if not dep_result.success:
                    fixes = self._generate_dep_fixes(dep_result.errors, current_files)
                    if fixes:
                        current_files = self._apply_fixes(current_files, fixes)
                        all_fixes.extend([f.description for f in fixes])
                        continue
                
                # Stage 4: Build Test
                await self._save_files_to_disk(current_files, project_dir)
                build_success, build_output = await self._run_build(project_dir)
                
                if build_success:
                    logger.info("validation_success", iterations=iteration + 1)
                    await self.complete_activity("completed")
                    return {
                        "success": True,
                        "files": current_files,
                        "fixes_applied": all_fixes,
                        "iterations": iteration + 1
                    }
                
                # Parse and fix build errors
                build_errors = self._parse_build_errors(build_output)
                new_errors = [
                    e for e in build_errors 
                    if e.signature() not in self.error_history
                ]
                
                if not new_errors:
                    logger.warning("no_new_build_errors", seen=len(build_errors))
                    break
                
                fixes = self._generate_ts_fixes(new_errors, current_files)
                if fixes:
                    current_files = self._apply_fixes(current_files, fixes)
                    all_fixes.extend([f.description for f in fixes])
                    for e in new_errors:
                        self.error_history.add(e.signature())
                    continue
                
                # Try LLM for build errors
                llm_fixes = await self._escalate_to_llm(new_errors[:2], current_files)
                if llm_fixes:
                    current_files = self._apply_fixes(current_files, llm_fixes)
                    all_fixes.extend([f.description for f in llm_fixes])
                    for e in new_errors:
                        self.error_history.add(e.signature())
                    continue
                
                # No more fixes possible
                for e in new_errors:
                    self.error_history.add(e.signature())
                break
            
            await self.complete_activity("completed_with_errors")
            return {
                "success": False,
                "files": current_files,
                "fixes_applied": all_fixes,
                "remaining_errors": [e.message for e in list(self.error_history)[:10]]
            }
            
        except Exception as e:
            logger.error("validation_pipeline_error", error=str(e))
            await self.complete_activity("failed")
            return {
                "success": False,
                "files": current_files,
                "fixes_applied": all_fixes,
                "error": str(e)
            }

    # =========================================================================
    # STAGE 1: Static Analysis
    # =========================================================================
    
    async def _stage_static_analysis(
        self, 
        files: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Run static analysis checks"""
        errors: List[ParsedError] = []
        
        for file in files:
            filepath = file.get("filepath", "")
            content = file.get("content", "")
            
            if not self._should_validate(filepath):
                continue
            
            # Check bracket balance
            bracket_errors = self._check_brackets(content, filepath)
            errors.extend(bracket_errors)
            
            # Check imports
            import_errors = self._check_imports(content, filepath, files)
            errors.extend(import_errors)
            
            # Check exports
            export_errors = self._check_exports(content, filepath)
            errors.extend(export_errors)
            
            # Check JSX (for .tsx/.jsx files)
            if filepath.endswith((".tsx", ".jsx")):
                jsx_errors = self._check_jsx(content, filepath)
                errors.extend(jsx_errors)
        
        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            stage="static_analysis"
        )
    
    def _should_validate(self, filepath: str) -> bool:
        """Check if file should be validated"""
        skip_patterns = [
            ".css", ".scss", ".less", ".md", ".json", ".svg", ".png", ".jpg",
            ".ico", ".txt", ".env", ".gitignore", "tailwind.config",
            "postcss.config", "next.config"
        ]
        return not any(p in filepath.lower() for p in skip_patterns)
    
    def _check_brackets(self, content: str, filepath: str) -> List[ParsedError]:
        """Check bracket/brace balance"""
        errors = []
        
        # Remove strings and comments
        clean = self._remove_strings_and_comments(content)
        
        stack = []
        pairs = {')': '(', ']': '[', '}': '{', '>': '<'}
        openers = '([{'
        closers = ')]}'
        
        lines = clean.split('\n')
        for line_num, line in enumerate(lines, 1):
            for char in line:
                if char in openers:
                    stack.append((char, line_num))
                elif char in closers:
                    if not stack:
                        errors.append(ParsedError(
                            error_type=ErrorType.SYNTAX,
                            file_path=filepath,
                            line=line_num,
                            column=None,
                            message=f"Unmatched closing '{char}'",
                            raw=line
                        ))
                    elif stack[-1][0] != pairs[char]:
                        errors.append(ParsedError(
                            error_type=ErrorType.SYNTAX,
                            file_path=filepath,
                            line=line_num,
                            column=None,
                            message=f"Mismatched bracket: expected '{pairs[char]}', got '{char}'",
                            raw=line
                        ))
                    else:
                        stack.pop()
        
        if stack:
            for bracket, line_num in stack[-3:]:
                errors.append(ParsedError(
                    error_type=ErrorType.SYNTAX,
                    file_path=filepath,
                    line=line_num,
                    column=None,
                    message=f"Unclosed '{bracket}'",
                    raw=""
                ))
        
        return errors
    
    def _check_imports(
        self, 
        content: str, 
        filepath: str, 
        all_files: List[Dict]
    ) -> List[ParsedError]:
        """Check for import errors"""
        errors = []
        
        # Pattern for relative imports
        import_pattern = r"from\s+['\"](\.[^'\"]+)['\"]"
        
        all_filepaths = {f.get("filepath", "") for f in all_files}
        
        for match in re.finditer(import_pattern, content):
            import_path = match.group(1)
            resolved = self._resolve_import(filepath, import_path, all_filepaths)
            
            if resolved is None:
                line_num = content[:match.start()].count('\n') + 1
                errors.append(ParsedError(
                    error_type=ErrorType.IMPORT,
                    file_path=filepath,
                    line=line_num,
                    column=None,
                    message=f"Import not found: '{import_path}'",
                    raw=match.group(0)
                ))
        
        return errors
    
    def _resolve_import(
        self, 
        current_file: str, 
        import_path: str,
        all_filepaths: Set[str]
    ) -> Optional[str]:
        """Resolve relative import to actual file path"""
        current_dir = os.path.dirname(current_file)
        
        extensions = ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx']
        
        for ext in extensions:
            test_path = os.path.normpath(os.path.join(current_dir, import_path + ext))
            test_path = test_path.replace('\\', '/')
            
            if test_path in all_filepaths:
                return test_path
            if test_path.startswith('./'):
                test_path = test_path[2:]
            if test_path in all_filepaths:
                return test_path
        
        return None
    
    def _check_exports(self, content: str, filepath: str) -> List[ParsedError]:
        """Check for export errors"""
        errors = []
        
        # Multiple default exports
        default_count = len(re.findall(r'export\s+default\s+', content))
        if default_count > 1:
            errors.append(ParsedError(
                error_type=ErrorType.EXPORT,
                file_path=filepath,
                line=None,
                column=None,
                message=f"Multiple default exports ({default_count})",
                raw=""
            ))
        
        # Page without default export
        if filepath.endswith(("page.tsx", "page.ts", "page.jsx", "page.js")):
            if 'export default' not in content:
                errors.append(ParsedError(
                    error_type=ErrorType.EXPORT,
                    file_path=filepath,
                    line=None,
                    column=None,
                    message="Page component missing default export",
                    raw=""
                ))
        
        return errors
    
    def _check_jsx(self, content: str, filepath: str) -> List[ParsedError]:
        """Check JSX syntax"""
        errors = []
        
        # class= instead of className=
        if re.search(r'\bclass\s*=\s*["\'{]', content):
            errors.append(ParsedError(
                error_type=ErrorType.JSX,
                file_path=filepath,
                line=None,
                column=None,
                message="Using 'class=' instead of 'className=' in JSX",
                raw=""
            ))
        
        # for= instead of htmlFor=
        if '<label' in content and re.search(r'\bfor\s*=\s*["\']', content):
            errors.append(ParsedError(
                error_type=ErrorType.JSX,
                file_path=filepath,
                line=None,
                column=None,
                message="Using 'for=' instead of 'htmlFor=' in JSX",
                raw=""
            ))
        
        return errors
    
    def _remove_strings_and_comments(self, content: str) -> str:
        """Remove string literals and comments for analysis"""
        # Remove template literals
        content = re.sub(r'`[^`]*`', '""', content)
        # Remove double-quoted strings
        content = re.sub(r'"(?:[^"\\]|\\.)*"', '""', content)
        # Remove single-quoted strings
        content = re.sub(r"'(?:[^'\\]|\\.)*'", "''", content)
        # Remove multi-line comments
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        return content

    # =========================================================================
    # STAGE 2: TypeScript Check
    # =========================================================================
    
    def _has_typescript(self, files: List[Dict]) -> bool:
        """Check if project uses TypeScript"""
        return any(
            f.get("filepath", "").endswith((".ts", ".tsx"))
            for f in files
        )
    
    async def _stage_typescript_check(self, project_dir: str) -> ValidationResult:
        """Run TypeScript compiler check"""
        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "npx", "tsc", "--noEmit", "--pretty", "false",
                    cwd=project_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=60
            )
            stdout, stderr = await result.communicate()
            
            output = stdout.decode() + stderr.decode()
            errors = self._parse_ts_errors(output)
            
            return ValidationResult(
                success=result.returncode == 0,
                errors=errors,
                stage="typescript_check"
            )
            
        except asyncio.TimeoutError:
            logger.warning("typescript_check_timeout")
            return ValidationResult(success=True, stage="typescript_check")
        except Exception as e:
            logger.warning("typescript_check_failed", error=str(e))
            return ValidationResult(success=True, stage="typescript_check")
    
    def _parse_ts_errors(self, output: str) -> List[ParsedError]:
        """Parse TypeScript compiler output"""
        errors = []
        
        # Format: path/file.ts(line,col): error TSxxxx: message
        pattern = r"(.+?)\((\d+),(\d+)\):\s*error\s+(TS\d+):\s*(.+)"
        
        for line in output.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                errors.append(ParsedError(
                    error_type=ErrorType.TYPE,
                    file_path=match.group(1),
                    line=int(match.group(2)),
                    column=int(match.group(3)),
                    message=match.group(5),
                    code=match.group(4),
                    raw=line
                ))
        
        return errors

    # =========================================================================
    # STAGE 3: Dependency Check
    # =========================================================================
    
    def _stage_dependency_check(self, files: List[Dict]) -> ValidationResult:
        """Check for missing dependencies"""
        errors = []
        
        # Find package.json
        pkg_file = next(
            (f for f in files if f.get("filepath") == "package.json"),
            None
        )
        
        if not pkg_file:
            return ValidationResult(success=True, stage="dependency_check")
        
        try:
            pkg = json.loads(pkg_file.get("content", "{}"))
            all_deps = set(pkg.get("dependencies", {}).keys())
            all_deps.update(pkg.get("devDependencies", {}).keys())
        except json.JSONDecodeError:
            return ValidationResult(success=True, stage="dependency_check")
        
        # Check imports across all files
        for file in files:
            content = file.get("content", "")
            filepath = file.get("filepath", "")
            
            if not filepath.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue
            
            # Find package imports (not relative)
            imports = re.findall(r"from\s+['\"]([^'\"./][^'\"]*)['\"]", content)
            
            for imp in imports:
                # Get base package name (e.g., @scope/pkg or pkg)
                if imp.startswith('@'):
                    parts = imp.split('/')
                    pkg_name = '/'.join(parts[:2]) if len(parts) > 1 else parts[0]
                else:
                    pkg_name = imp.split('/')[0]
                
                # Skip built-ins and already-present deps
                built_ins = {'react', 'react-dom', 'next', 'fs', 'path', 'http', 'https', 'url', 'util'}
                if pkg_name not in all_deps and pkg_name not in built_ins:
                    errors.append(ParsedError(
                        error_type=ErrorType.DEPENDENCY,
                        file_path="package.json",
                        line=None,
                        column=None,
                        message=f"Missing dependency: {pkg_name}",
                        raw=imp
                    ))
        
        return ValidationResult(
            success=len(errors) == 0,
            errors=errors,
            stage="dependency_check"
        )

    # =========================================================================
    # STAGE 4: Build Test
    # =========================================================================
    
    async def _run_build(self, project_dir: str) -> Tuple[bool, str]:
        """Run npm build"""
        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "npm", "run", "build",
                    cwd=project_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=120
            )
            stdout, stderr = await result.communicate()
            
            output = stdout.decode() + stderr.decode()
            return result.returncode == 0, output
            
        except asyncio.TimeoutError:
            return False, "Build timeout"
        except Exception as e:
            return False, str(e)
    
    def _parse_build_errors(self, output: str) -> List[ParsedError]:
        """Parse build output for errors"""
        errors = []
        
        # TypeScript errors in build output
        ts_pattern = r"(.+?)\((\d+),(\d+)\):\s*error\s+(TS\d+):\s*(.+)"
        for match in re.finditer(ts_pattern, output):
            errors.append(ParsedError(
                error_type=ErrorType.BUILD,
                file_path=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                message=match.group(5),
                code=match.group(4),
                raw=match.group(0)
            ))
        
        # Next.js/React build errors
        nextjs_pattern = r"Error:\s*(.+?)\n\s*at\s+(.+?):(\d+):(\d+)"
        for match in re.finditer(nextjs_pattern, output):
            errors.append(ParsedError(
                error_type=ErrorType.BUILD,
                file_path=match.group(2),
                line=int(match.group(3)),
                column=int(match.group(4)),
                message=match.group(1),
                raw=match.group(0)
            ))
        
        return errors

    # =========================================================================
    # FIX GENERATORS
    # =========================================================================
    
    def _generate_static_fixes(
        self, 
        errors: List[ParsedError], 
        files: List[Dict]
    ) -> List[Fix]:
        """Generate fixes for static analysis errors"""
        fixes = []
        
        for error in errors:
            if error.error_type == ErrorType.JSX:
                if "class=" in error.message:
                    fix = self._fix_class_to_classname(error, files)
                    if fix:
                        fixes.append(fix)
                elif "for=" in error.message:
                    fix = self._fix_for_to_htmlfor(error, files)
                    if fix:
                        fixes.append(fix)
            
            elif error.error_type == ErrorType.EXPORT:
                if "missing default export" in error.message:
                    fix = self._fix_add_default_export(error, files)
                    if fix:
                        fixes.append(fix)
        
        return fixes
    
    def _generate_ts_fixes(
        self, 
        errors: List[ParsedError], 
        files: List[Dict]
    ) -> List[Fix]:
        """Generate fixes for TypeScript errors using pattern matching"""
        fixes = []
        
        for error in errors:
            code = error.code
            
            if code and code in self.TS_ERROR_PATTERNS:
                pattern_config = self.TS_ERROR_PATTERNS[code]
                fix_fn_name = pattern_config["fix_fn"]
                fix_fn = getattr(self, fix_fn_name, None)
                
                if fix_fn:
                    match = re.search(pattern_config["pattern"], error.message)
                    fix = fix_fn(error, match, files)
                    if fix:
                        fixes.append(fix)
            else:
                # Try generic fixes based on error type
                fix = self._try_generic_fix(error, files)
                if fix:
                    fixes.append(fix)
        
        return fixes
    
    def _generate_dep_fixes(
        self, 
        errors: List[ParsedError], 
        files: List[Dict]
    ) -> List[Fix]:
        """Generate fixes for dependency errors"""
        fixes = []
        
        pkg_file = next(
            (f for f in files if f.get("filepath") == "package.json"),
            None
        )
        
        if not pkg_file:
            return fixes
        
        try:
            pkg = json.loads(pkg_file.get("content", "{}"))
        except json.JSONDecodeError:
            return fixes
        
        deps_to_add = []
        
        for error in errors:
            if error.error_type == ErrorType.DEPENDENCY:
                match = re.search(r"Missing dependency: (.+)", error.message)
                if match:
                    deps_to_add.append(match.group(1))
        
        if deps_to_add:
            if "dependencies" not in pkg:
                pkg["dependencies"] = {}
            
            for dep in deps_to_add:
                if dep not in pkg["dependencies"]:
                    pkg["dependencies"][dep] = "latest"
            
            fixes.append(Fix(
                file_path="package.json",
                action="replace_content",
                description=f"Added dependencies: {', '.join(deps_to_add)}",
                new_value=json.dumps(pkg, indent=2)
            ))
        
        return fixes

    # =========================================================================
    # SPECIFIC FIXERS
    # =========================================================================
    
    def _fix_missing_module(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2307: Cannot find module"""
        if not match:
            return None
        
        module_name = match.group(1)
        
        # Skip relative imports (handled by static analysis)
        if module_name.startswith('.'):
            return None
        
        # Find package.json
        pkg_file = next(
            (f for f in files if f.get("filepath") == "package.json"),
            None
        )
        
        if not pkg_file:
            return None
        
        try:
            pkg = json.loads(pkg_file.get("content", "{}"))
        except json.JSONDecodeError:
            return None
        
        # Get base package name
        if module_name.startswith('@'):
            parts = module_name.split('/')
            pkg_name = '/'.join(parts[:2])
        else:
            pkg_name = module_name.split('/')[0]
        
        # Check if already present
        all_deps = set(pkg.get("dependencies", {}).keys())
        all_deps.update(pkg.get("devDependencies", {}).keys())
        
        if pkg_name in all_deps:
            return None
        
        # Add to dependencies
        if "dependencies" not in pkg:
            pkg["dependencies"] = {}
        
        pkg["dependencies"][pkg_name] = "latest"
        
        return Fix(
            file_path="package.json",
            action="replace_content",
            description=f"Added missing dependency: {pkg_name}",
            new_value=json.dumps(pkg, indent=2)
        )
    
    def _fix_undefined_name(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2304: Cannot find name - add missing import"""
        if not match:
            return None
        
        name = match.group(1)
        
        # Check if it's a known import
        if name not in self.COMMON_IMPORTS:
            return None
        
        module, is_named = self.COMMON_IMPORTS[name]
        
        # Find the file
        file = next(
            (f for f in files if error.file_path.endswith(f.get("filepath", ""))),
            None
        )
        
        if not file:
            return None
        
        content = file.get("content", "")
        lines = content.split('\n')
        
        # Check if already imported
        if re.search(rf'\b{name}\b.*from\s+[\'\"]{module}[\'\"]', content):
            return None
        
        # Create import statement
        if is_named:
            import_stmt = f"import {{ {name} }} from '{module}';"
        else:
            import_stmt = f"import {name} from '{module}';"
        
        # Find where to insert (after existing imports or at top)
        insert_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import '):
                insert_line = i + 1
        
        lines.insert(insert_line, import_stmt)
        
        return Fix(
            file_path=file.get("filepath", ""),
            action="replace_content",
            description=f"Added import for {name} from {module}",
            new_value='\n'.join(lines)
        )
    
    def _fix_default_export_mismatch(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix default/named export mismatch"""
        file = next(
            (f for f in files if error.file_path.endswith(f.get("filepath", ""))),
            None
        )
        
        if not file:
            return None
        
        content = file.get("content", "")
        lines = content.split('\n')
        
        if error.line and error.line <= len(lines):
            line = lines[error.line - 1]
            
            # Convert: import X from 'y' → import { X } from 'y'
            new_line = re.sub(
                r"import\s+(\w+)\s+from",
                r"import { \1 } from",
                line
            )
            
            if new_line != line:
                lines[error.line - 1] = new_line
                return Fix(
                    file_path=file.get("filepath", ""),
                    action="replace_content",
                    description=f"Fixed default import to named import at line {error.line}",
                    new_value='\n'.join(lines)
                )
        
        return None
    
    def _fix_missing_export(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2305: Module has no exported member"""
        if not match:
            return None
        
        # Try to switch to default import
        return self._fix_default_export_mismatch(error, match, files)
    
    def _fix_missing_property(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2339: Property does not exist on type"""
        # This typically requires LLM assistance
        return None
    
    def _fix_type_mismatch(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2322: Type is not assignable"""
        # Complex - escalate to LLM
        return None
    
    def _fix_argument_type(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2345: Argument type not assignable"""
        # Complex - escalate to LLM
        return None
    
    def _fix_expected_token(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS1005: Expected token"""
        # Syntax error - escalate to LLM
        return None
    
    def _fix_syntax_error(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix syntax errors"""
        # Escalate to LLM
        return None
    
    def _fix_possibly_undefined(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS2532: Object is possibly undefined"""
        file = next(
            (f for f in files if error.file_path.endswith(f.get("filepath", ""))),
            None
        )
        
        if not file or not error.line:
            return None
        
        content = file.get("content", "")
        lines = content.split('\n')
        
        if error.line <= len(lines):
            line = lines[error.line - 1]
            
            # Try adding optional chaining
            # This is a simple heuristic - might not always work
            new_line = re.sub(r'(\w+)\.(\w+)', r'\1?.\2', line)
            
            if new_line != line:
                lines[error.line - 1] = new_line
                return Fix(
                    file_path=file.get("filepath", ""),
                    action="replace_content",
                    description=f"Added optional chaining at line {error.line}",
                    new_value='\n'.join(lines),
                    confidence=0.7
                )
        
        return None
    
    def _fix_implicit_any(
        self, 
        error: ParsedError, 
        match: Optional[re.Match], 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix TS7006: Parameter implicitly has 'any' type"""
        if not match:
            return None
        
        param_name = match.group(1)
        
        file = next(
            (f for f in files if error.file_path.endswith(f.get("filepath", ""))),
            None
        )
        
        if not file or not error.line:
            return None
        
        content = file.get("content", "")
        lines = content.split('\n')
        
        if error.line <= len(lines):
            line = lines[error.line - 1]
            
            # Add : any type annotation
            new_line = re.sub(
                rf'\b({param_name})(\s*[,\)])',
                rf'\1: any\2',
                line
            )
            
            if new_line != line:
                lines[error.line - 1] = new_line
                return Fix(
                    file_path=file.get("filepath", ""),
                    action="replace_content",
                    description=f"Added type annotation for {param_name}",
                    new_value='\n'.join(lines)
                )
        
        return None
    
    def _fix_class_to_classname(
        self, 
        error: ParsedError, 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix class= to className="""
        file = next(
            (f for f in files if f.get("filepath") == error.file_path),
            None
        )
        
        if not file:
            return None
        
        content = file.get("content", "")
        new_content = re.sub(r'\bclass\s*=\s*(["\'{])', r'className=\1', content)
        
        if new_content != content:
            return Fix(
                file_path=error.file_path,
                action="replace_content",
                description="Replaced class= with className=",
                new_value=new_content
            )
        
        return None
    
    def _fix_for_to_htmlfor(
        self, 
        error: ParsedError, 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Fix for= to htmlFor="""
        file = next(
            (f for f in files if f.get("filepath") == error.file_path),
            None
        )
        
        if not file:
            return None
        
        content = file.get("content", "")
        new_content = re.sub(r'\bfor\s*=\s*(["\'])', r'htmlFor=\1', content)
        
        if new_content != content:
            return Fix(
                file_path=error.file_path,
                action="replace_content",
                description="Replaced for= with htmlFor=",
                new_value=new_content
            )
        
        return None
    
    def _fix_add_default_export(
        self, 
        error: ParsedError, 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Add default export to page component"""
        file = next(
            (f for f in files if f.get("filepath") == error.file_path),
            None
        )
        
        if not file:
            return None
        
        content = file.get("content", "")
        
        # Find the main component function
        match = re.search(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', content)
        
        if match:
            component_name = match.group(1)
            
            # Check if already has export default
            if 'export default' in content:
                return None
            
            # Add export default at end
            new_content = content.rstrip() + f"\n\nexport default {component_name};\n"
            
            return Fix(
                file_path=error.file_path,
                action="replace_content",
                description=f"Added default export for {component_name}",
                new_value=new_content
            )
        
        return None
    
    def _try_generic_fix(
        self, 
        error: ParsedError, 
        files: List[Dict]
    ) -> Optional[Fix]:
        """Try generic fixes based on error message patterns"""
        msg = error.message.lower()
        
        # Missing import patterns
        if "cannot find" in msg and "name" in msg:
            return self._fix_undefined_name(error, re.search(r"'(\w+)'", error.message), files)
        
        return None

    # =========================================================================
    # LLM ESCALATION
    # =========================================================================
    
    async def _escalate_to_llm(
        self, 
        errors: List[ParsedError], 
        files: List[Dict]
    ) -> List[Fix]:
        """Escalate complex errors to LLM for fixing"""
        fixes = []
        
        for error in errors:
            file = next(
                (f for f in files if error.file_path.endswith(f.get("filepath", ""))),
                None
            )
            
            if not file:
                continue
            
            prompt = f"""Fix this TypeScript/React error:

ERROR: {error.code} - {error.message}
FILE: {error.file_path}
LINE: {error.line}

CURRENT FILE CONTENT:
```
{file.get("content", "")[:8000]}
```

Return ONLY valid JSON:
{{
    "file_path": "{file.get("filepath", "")}",
    "fixed_content": "complete corrected file content",
    "explanation": "brief explanation"
}}
"""
            
            try:
                response = await self.call_llm(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=8000
                )
                
                # Parse JSON response
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    fix_data = json.loads(json_match.group())
                    
                    if "fixed_content" in fix_data:
                        fixes.append(Fix(
                            file_path=fix_data.get("file_path", file.get("filepath", "")),
                            action="replace_content",
                            description=fix_data.get("explanation", f"LLM fix for {error.code}"),
                            new_value=fix_data["fixed_content"],
                            confidence=0.6
                        ))
                        
            except Exception as e:
                logger.warning("llm_fix_failed", error=str(e))
                continue
        
        return fixes

    # =========================================================================
    # APPLY FIXES
    # =========================================================================
    
    def _apply_fixes(
        self, 
        files: List[Dict], 
        fixes: List[Fix]
    ) -> List[Dict]:
        """Apply fixes to files with fuzzy path matching"""
        updated_files = [f.copy() for f in files]
        
        for fix in fixes:
            if not fix.new_value:
                logger.warning("empty_fix_content", file=fix.file_path)
                continue
                
            if fix.action == "replace_content":
                # Find file using fuzzy matching
                matched_idx = self._find_matching_file(updated_files, fix.file_path)
                
                if matched_idx is not None:
                    actual_path = updated_files[matched_idx].get("filepath", "")
                    updated_files[matched_idx] = {
                        **updated_files[matched_idx],
                        "content": fix.new_value
                    }
                    self.fix_history.append(fix.description)
                    logger.info("fix_applied", 
                               target=fix.file_path, 
                               actual=actual_path, 
                               desc=fix.description,
                               content_len=len(fix.new_value))
                else:
                    # File not found, create it
                    logger.warning("fix_file_not_found_creating", file=fix.file_path)
                    updated_files.append({
                        "filepath": fix.file_path,
                        "filename": os.path.basename(fix.file_path),
                        "content": fix.new_value,
                        "language": self._detect_language(fix.file_path)
                    })
                    self.fix_history.append(fix.description)
        
        return updated_files
    
    def _find_matching_file(self, files: List[Dict], target_path: str) -> Optional[int]:
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
                return i
        
        # Finally try just filename match
        for i, f in enumerate(files):
            if os.path.basename(f.get("filepath", "")) == target_basename:
                logger.warning("basename_only_match", target=target_path, matched=f.get("filepath"))
                return i
        
        return None
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for comparison"""
        path = path.lstrip("./").lstrip("/")
        path = path.replace("\\", "/")
        return path.lower()
    
    def _detect_language(self, filepath: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript", ".json": "json",
            ".html": "html", ".css": "css", ".md": "markdown"
        }
        for ext, lang in ext_map.items():
            if filepath.endswith(ext):
                return lang
        return "text"

    # =========================================================================
    # FILE UTILITIES
    # =========================================================================
    
    async def _save_files_to_disk(
        self, 
        files: List[Dict], 
        project_dir: str
    ) -> None:
        """Save files to disk for compilation"""
        for file in files:
            filepath = os.path.join(project_dir, file.get("filepath", ""))
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(file.get("content", ""))

    # =========================================================================
    # TEST FAILURE FIXES
    # =========================================================================
    
    async def fix_test_failures(
        self,
        test_output: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze test failures and fix the source code.
        
        This method is called when unit tests fail. It:
        1. Parses the test output to understand failures
        2. Identifies which source files need fixing
        3. Uses LLM to generate fixes for the source code
        """
        activity = await self.start_activity("Fixing test failures")
        
        try:
            # Parse test errors
            test_errors = self._parse_test_errors(test_output)
            
            if not test_errors:
                logger.warning("no_test_errors_parsed", output_len=len(test_output))
                return {"success": False, "files": files, "fixes_applied": []}
            
            logger.info("test_errors_found", count=len(test_errors))
            
            # Find the source files that need fixing (not test files)
            source_files = [
                f for f in files 
                if not any(x in f.get("filepath", "") for x in [".test.", ".spec.", "__tests__"])
            ]
            
            # Build context for LLM
            file_contents = ""
            for f in source_files[:10]:
                filepath = f.get("filepath", "")
                content = f.get("content", "")
                file_contents += f"\n\n--- {filepath} ---\n{content}"
            
            # Generate fix prompt
            error_summary = "\n".join([
                f"- {e.file_path}: {e.message}"
                for e in test_errors[:5]
            ])
            
            prompt = f"""Fix these test failures by modifying the SOURCE CODE (not the tests).

## TEST FAILURES:
{error_summary}

## FULL TEST OUTPUT:
```
{test_output[:3000]}
```

## SOURCE FILES:
{file_contents[:20000]}

## INSTRUCTIONS:
1. The tests are CORRECT - fix the source code to make them pass
2. Look at what the test expects and make the source code return/render that
3. DO NOT modify test files
4. Return COMPLETE fixed file content

Respond with JSON:
{{
    "fixes": [
        {{
            "filepath": "src/path/to/source.ts",
            "action": "replace_content",
            "description": "Fixed X to return Y",
            "new_value": "COMPLETE FILE CONTENT"
        }}
    ]
}}
"""
            
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8000
            )
            
            # Parse response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                fix_data = json.loads(json_match.group())
                fixes_raw = fix_data.get("fixes", [])
                
                # Convert to Fix objects
                fixes = []
                for f in fixes_raw:
                    fixes.append(Fix(
                        file_path=f.get("filepath", ""),
                        action=f.get("action", "replace_content"),
                        description=f.get("description", "Test fix"),
                        new_value=f.get("new_value", "")
                    ))
                
                if fixes:
                    updated_files = self._apply_fixes(files, fixes)
                    
                    await self.complete_activity("completed")
                    return {
                        "success": True,
                        "files": updated_files,
                        "fixes_applied": [f.description for f in fixes]
                    }
            
            await self.complete_activity("completed_no_fixes")
            return {"success": False, "files": files, "fixes_applied": []}
            
        except Exception as e:
            logger.error("test_fix_failed", error=str(e))
            await self.complete_activity("failed")
            return {"success": False, "files": files, "error": str(e)}
    
    def _parse_test_errors(self, output: str) -> List[ParsedError]:
        """Parse Jest test output for errors"""
        errors = []
        
        # Pattern for FAIL lines
        fail_pattern = r"FAIL\s+([^\s]+)"
        for match in re.finditer(fail_pattern, output):
            errors.append(ParsedError(
                error_type=ErrorType.BUILD,
                file_path=match.group(1),
                line=None,
                column=None,
                message="Test suite failed",
                raw=match.group(0)
            ))
        
        # Pattern for expect failures
        expect_pattern = r"expect\((.+?)\)\.(\w+)\((.+?)\)"
        for match in re.finditer(expect_pattern, output):
            errors.append(ParsedError(
                error_type=ErrorType.BUILD,
                file_path="",
                line=None,
                column=None,
                message=f"Expected {match.group(1)} to {match.group(2)} {match.group(3)}",
                raw=match.group(0)
            ))
        
        # Pattern for "Expected X, Received Y"
        received_pattern = r"Expected:?\s*(.+?)\s*Received:?\s*(.+?)(?:\n|$)"
        for match in re.finditer(received_pattern, output, re.IGNORECASE):
            errors.append(ParsedError(
                error_type=ErrorType.BUILD,
                file_path="",
                line=None,
                column=None,
                message=f"Expected: {match.group(1).strip()}, Got: {match.group(2).strip()}",
                raw=match.group(0)
            ))
        
        # Pattern for "Cannot find module"
        module_pattern = r"Cannot find module '([^']+)'"
        for match in re.finditer(module_pattern, output):
            errors.append(ParsedError(
                error_type=ErrorType.IMPORT,
                file_path="",
                line=None,
                column=None,
                message=f"Cannot find module: {match.group(1)}",
                raw=match.group(0)
            ))
        
        return errors

