"""
Code Reviewer Agent - Validates generated code for ALL errors and fixes them
Part of the Multi-Agent System with MCP Integration
"""
from typing import Dict, Any, List, Optional, Tuple, Set
import json
import re
import os
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class CodeReviewerAgent(BaseAgent):
    """
    Code Reviewer Agent that validates generated code for ALL types of errors.
    
    This agent:
    1. Checks each generated file for syntax errors
    2. Validates imports and exports
    3. Checks for undefined variables and functions
    4. Validates TypeScript/React patterns
    5. Checks for missing dependencies
    6. Fixes ALL errors found
    
    Role in Multi-Agent System:
    - Receives generated code from CodeGeneratorAgent
    - Validates and fixes ALL errors before execution
    - Ensures code is executable
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.CODE_GENERATOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.agent_name = "CodeReviewerAgent"
        self.all_exports: Dict[str, Set[str]] = {}  # Track exports from each file
        self.all_imports: Dict[str, List[Dict]] = {}  # Track imports in each file

    def get_system_prompt(self) -> str:
        return """You are a Senior Code Reviewer and Debugger. Your job is to fix ALL errors in the code.

## YOUR TASK
The code has errors that will prevent successful execution. Fix ALL of them.

## ERRORS TO FIX
1. Syntax errors (unclosed braces, brackets, parentheses)
2. Import errors (missing imports, wrong import paths, default vs named export mismatch)
3. Export errors (missing exports, duplicate exports)
4. Type errors (TypeScript type mismatches, missing types)
5. Undefined variables or functions
6. JSX/TSX errors (unclosed tags, wrong attributes)
7. React errors (missing hooks imports, wrong hook usage)
8. API route errors (missing handlers, wrong response format)
9. Logical errors that would cause runtime failures
10. Missing dependencies that should be imported

## RULES
1. Return the COMPLETE fixed file - not just the changes
2. Preserve the original functionality
3. Ensure all imports are correct (check if using default or named exports)
4. Ensure all functions and variables are defined before use
5. For TypeScript, ensure proper typing
6. For React components, ensure proper JSX syntax

Return ONLY the corrected code. No explanations, no markdown code blocks.
Start directly with the import statements or code.
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
        """Review all files and fix any with errors"""
        activity = await self.start_activity("Reviewing code for ALL errors")
        
        fixed_files = []
        total_errors_found = 0
        files_fixed = 0
        error_details = []
        
        try:
            # First pass: collect all exports to validate imports
            self._collect_exports(files)
            
            # Second pass: check and fix each file
            for file in files:
                filepath = file.get("filepath", "")
                content = file.get("content", "")
                language = file.get("language", "")
                
                if not self._should_validate(filepath, language):
                    fixed_files.append(file)
                    continue
                
                # Comprehensive error checking
                errors = self._check_all_errors(content, filepath, files)
                
                if errors:
                    total_errors_found += len(errors)
                    error_details.append({
                        "filepath": filepath,
                        "errors": errors[:5]  # Limit for logging
                    })
                    
                    logger.warning(
                        "errors_found",
                        filepath=filepath,
                        error_count=len(errors),
                        errors=errors[:3]
                    )
                    
                    # Fix the file
                    fixed_content = await self._fix_file(file, errors, architecture, files)
                    
                    if fixed_content and fixed_content != content:
                        file["content"] = fixed_content
                        files_fixed += 1
                        logger.info("file_fixed", filepath=filepath)
                        
                        # Re-check for remaining errors
                        remaining_errors = self._check_all_errors(fixed_content, filepath, files)
                        if remaining_errors:
                            logger.warning(
                                "remaining_errors",
                                filepath=filepath,
                                error_count=len(remaining_errors)
                            )
                
                fixed_files.append(file)
            
            # Third pass: fix package.json if there are missing dependencies
            fixed_files = await self._fix_package_json(fixed_files)
            
            await self.complete_activity("completed")
            
            logger.info(
                "code_review_completed",
                total_files=len(files),
                errors_found=total_errors_found,
                files_fixed=files_fixed
            )
            
            return {
                "files": fixed_files,
                "review_summary": {
                    "total_files": len(files),
                    "errors_found": total_errors_found,
                    "files_fixed": files_fixed,
                    "error_details": error_details[:10]  # Limit for response size
                }
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("code_review_failed", error=str(e))
            return {"files": files, "review_summary": {"error": str(e)}}

    def _collect_exports(self, files: List[Dict[str, Any]]) -> None:
        """Collect all exports from all files"""
        self.all_exports = {}
        
        for file in files:
            filepath = file.get("filepath", "")
            content = file.get("content", "")
            
            if not filepath.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue
            
            exports = set()
            
            # Default exports
            default_patterns = [
                r'export\s+default\s+(?:function|class|const|let|var)\s+(\w+)',
                r'export\s+default\s+(\w+)',
                r'export\s+\{\s*(\w+)\s+as\s+default\s*\}',
            ]
            for pattern in default_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    exports.add("default")
                    break
            
            # Named exports
            named_patterns = [
                r'export\s+(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)',
                r'export\s+\{\s*([^}]+)\s*\}',
                r'export\s+type\s+(\w+)',
                r'export\s+interface\s+(\w+)',
            ]
            for pattern in named_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, str):
                        # Handle "export { a, b, c }" format
                        for name in match.split(','):
                            name = name.strip().split(' as ')[0].strip()
                            if name and name != 'default':
                                exports.add(name)
            
            self.all_exports[filepath] = exports

    def _should_validate(self, filepath: str, language: str) -> bool:
        """Check if file should be validated"""
        skip_extensions = [".json", ".md", ".css", ".sql", ".yaml", ".yml", ".env", ".gitignore", ".dockerignore", ".png", ".jpg", ".svg"]
        skip_files = ["package.json", "tsconfig.json", "tailwind.config", "postcss.config", "next.config", "jest.config", "jest.setup"]
        
        filepath_lower = filepath.lower()
        
        for ext in skip_extensions:
            if filepath_lower.endswith(ext):
                return False
        
        for skip in skip_files:
            if skip in filepath_lower:
                return False
        
        # Validate TS, TSX, JS, JSX files
        return filepath.endswith((".ts", ".tsx", ".js", ".jsx"))

    def _check_all_errors(self, content: str, filepath: str, all_files: List[Dict[str, Any]]) -> List[str]:
        """Comprehensive error checking"""
        errors = []
        
        if not content or not content.strip():
            return ["Empty file"]
        
        # 1. Bracket/brace balance
        brace_errors = self._check_bracket_balance(content)
        errors.extend(brace_errors)
        
        # 2. JSX/TSX specific errors
        if filepath.endswith((".tsx", ".jsx")):
            jsx_errors = self._check_jsx_tsx_errors(content)
            errors.extend(jsx_errors)
        
        # 3. Import errors
        import_errors = self._check_import_errors(content, filepath, all_files)
        errors.extend(import_errors)
        
        # 4. Export errors
        export_errors = self._check_export_errors(content, filepath)
        errors.extend(export_errors)
        
        # 5. Undefined variables/functions
        undefined_errors = self._check_undefined_references(content, filepath)
        errors.extend(undefined_errors)
        
        # 6. String errors
        string_errors = self._check_string_errors(content)
        errors.extend(string_errors)
        
        # 7. TypeScript specific errors
        if filepath.endswith((".ts", ".tsx")):
            ts_errors = self._check_typescript_errors(content)
            errors.extend(ts_errors)
        
        # 8. React specific errors
        if filepath.endswith((".tsx", ".jsx")):
            react_errors = self._check_react_errors(content)
            errors.extend(react_errors)
        
        # 9. API route errors
        if "/api/" in filepath and filepath.endswith(("route.ts", "route.tsx")):
            api_errors = self._check_api_route_errors(content)
            errors.extend(api_errors)
        
        # 10. Structure errors
        structure_errors = self._check_structure_errors(content, filepath)
        errors.extend(structure_errors)
        
        return errors

    def _check_bracket_balance(self, content: str) -> List[str]:
        """Check if brackets/braces are balanced"""
        errors = []
        
        content_no_strings = self._remove_strings_and_comments(content)
        
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        openers = '([{'
        closers = ')]}'
        
        lines = content_no_strings.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for char in line:
                if char in openers:
                    stack.append((char, line_num))
                elif char in closers:
                    if not stack:
                        errors.append(f"Unmatched closing '{char}' at line {line_num}")
                    elif stack[-1][0] != pairs[char]:
                        errors.append(f"Mismatched bracket at line {line_num}: expected closing for '{stack[-1][0]}', got '{char}'")
                    else:
                        stack.pop()
        
        if stack:
            for bracket, line_num in stack[-3:]:  # Report last 3 unclosed
                errors.append(f"Unclosed '{bracket}' opened at line {line_num}")
        
        return errors

    def _check_jsx_tsx_errors(self, content: str) -> List[str]:
        """Check for JSX/TSX specific errors"""
        errors = []
        
        # Check for unclosed JSX tags
        self_closing_tags = {'img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr'}
        
        # Find all opening tags (excluding self-closing and HTML void elements)
        opening_pattern = r'<([A-Z][a-zA-Z0-9]*|[a-z]+)(?:\s[^>]*)?(?<!/)>'
        closing_pattern = r'</([A-Z][a-zA-Z0-9]*|[a-z]+)>'
        self_close_pattern = r'<([A-Z][a-zA-Z0-9]*|[a-z]+)(?:\s[^>]*)?\s*/>'
        
        # Remove strings and comments first
        clean_content = self._remove_strings_and_comments(content)
        
        # Count tags
        opening_tags = re.findall(opening_pattern, clean_content)
        closing_tags = re.findall(closing_pattern, clean_content)
        self_closing = re.findall(self_close_pattern, clean_content)
        
        # Filter out void elements
        opening_tags = [t for t in opening_tags if t.lower() not in self_closing_tags]
        
        # Simple check for major imbalances
        tag_counts = {}
        for tag in opening_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        for tag in closing_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) - 1
        
        for tag, count in tag_counts.items():
            if count > 0:
                errors.append(f"Unclosed JSX tag: <{tag}> (missing {count} closing tag(s))")
            elif count < 0:
                errors.append(f"Extra closing tag: </{tag}> (missing {abs(count)} opening tag(s))")
        
        # Check for invalid JSX attributes
        if 'class=' in content and 'className=' not in content:
            errors.append("Using 'class=' instead of 'className=' in JSX")
        
        if 'for=' in content and 'htmlFor=' not in content:
            if '<label' in content:
                errors.append("Using 'for=' instead of 'htmlFor=' in JSX label")
        
        # Check for JSX outside of return or variable assignment
        lines = content.split('\n')
        in_function = False
        brace_depth = 0
        
        for i, line in enumerate(lines):
            if re.search(r'(?:function|const|let|var)\s+\w+\s*[=(]', line):
                in_function = True
            brace_depth += line.count('{') - line.count('}')
            
            # Check for JSX that's not in a proper context
            if re.match(r'^\s*<[A-Z]', line) and brace_depth == 0 and not in_function:
                errors.append(f"JSX at line {i+1} appears to be outside a function or return statement")
        
        return errors

    def _check_import_errors(self, content: str, filepath: str, all_files: List[Dict[str, Any]]) -> List[str]:
        """Check for import errors"""
        errors = []
        
        # Extract all imports
        import_patterns = [
            r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]",  # import X from 'y'
            r"import\s+\{\s*([^}]+)\s*\}\s+from\s+['\"]([^'\"]+)['\"]",  # import { X } from 'y'
            r"import\s+(\w+)\s*,\s*\{\s*([^}]+)\s*\}\s+from\s+['\"]([^'\"]+)['\"]",  # import X, { Y } from 'z'
            r"import\s+['\"]([^'\"]+)['\"]",  # import 'x' (side effect)
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    import_path = groups[-1] if groups[-1] else groups[0]
                    
                    # Check relative imports
                    if import_path.startswith('.'):
                        # Resolve the path
                        resolved = self._resolve_import_path(filepath, import_path, all_files)
                        if resolved is None:
                            errors.append(f"Import not found: '{import_path}' in {filepath}")
                        else:
                            # Check if imported names exist in the target file
                            imported_names = []
                            if len(groups) >= 2 and groups[0]:
                                # Check if it's a default import
                                if '{' not in match.group():
                                    # Default import
                                    if resolved in self.all_exports:
                                        if 'default' not in self.all_exports[resolved]:
                                            errors.append(f"'{import_path}' has no default export, but imported as default")
                                else:
                                    # Named imports
                                    names = groups[0].split(',')
                                    for name in names:
                                        name = name.strip().split(' as ')[0].strip()
                                        if name and resolved in self.all_exports:
                                            if name not in self.all_exports[resolved] and name != 'default':
                                                errors.append(f"'{name}' is not exported from '{import_path}'")
        
        return errors

    def _resolve_import_path(self, current_file: str, import_path: str, all_files: List[Dict[str, Any]]) -> Optional[str]:
        """Resolve a relative import path to actual file path"""
        current_dir = os.path.dirname(current_file)
        
        # Handle different import formats
        if import_path.startswith('./'):
            relative_path = import_path[2:]
        elif import_path.startswith('../'):
            parts = current_dir.split('/')
            up_count = import_path.count('../')
            relative_path = '/'.join(parts[:-up_count]) + '/' + import_path.replace('../', '')
        else:
            relative_path = import_path
        
        # Try different extensions
        extensions = ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx', '/index.js', '/index.jsx']
        
        all_filepaths = [f.get("filepath", "") for f in all_files]
        
        for ext in extensions:
            test_path = os.path.normpath(os.path.join(current_dir, import_path + ext))
            test_path = test_path.replace('\\', '/')
            
            if test_path in all_filepaths:
                return test_path
            
            # Also try without leading ./
            if test_path.startswith('./'):
                test_path = test_path[2:]
            if test_path in all_filepaths:
                return test_path
        
        return None

    def _check_export_errors(self, content: str, filepath: str) -> List[str]:
        """Check for export errors"""
        errors = []
        
        # Check for multiple default exports
        default_export_count = len(re.findall(r'export\s+default\s+', content))
        if default_export_count > 1:
            errors.append(f"Multiple default exports found ({default_export_count})")
        
        # Check for exported items that don't exist
        export_blocks = re.findall(r'export\s+\{\s*([^}]+)\s*\}', content)
        for block in export_blocks:
            names = [n.strip().split(' as ')[0].strip() for n in block.split(',')]
            for name in names:
                if name and name != 'default':
                    # Check if the name is defined in the file
                    if not re.search(rf'\b(?:const|let|var|function|class|type|interface)\s+{name}\b', content):
                        errors.append(f"Exporting undefined: '{name}'")
        
        # Check for page/route files without exports
        if filepath.endswith(("page.tsx", "page.ts", "page.jsx", "page.js")):
            if 'export default' not in content:
                errors.append("Page component missing default export")
        
        if filepath.endswith(("route.ts", "route.tsx", "route.js", "route.jsx")):
            has_handler = any(
                re.search(rf'export\s+(?:async\s+)?function\s+{method}\b', content)
                for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            )
            if not has_handler:
                errors.append("API route missing exported HTTP handler (GET, POST, etc.)")
        
        return errors

    def _check_undefined_references(self, content: str, filepath: str) -> List[str]:
        """Check for undefined variables and functions"""
        errors = []
        
        # Common globals and built-ins that don't need to be imported
        globals_and_builtins = {
            'console', 'window', 'document', 'localStorage', 'sessionStorage',
            'fetch', 'JSON', 'Promise', 'Array', 'Object', 'String', 'Number',
            'Boolean', 'Date', 'Math', 'Error', 'Map', 'Set', 'RegExp',
            'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'undefined', 'null',
            'true', 'false', 'this', 'super', 'arguments', 'process', 'Buffer',
            'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
            'require', 'module', 'exports', '__dirname', '__filename',
            'React', 'Component', 'Fragment', 'Suspense',
            'NextResponse', 'NextRequest', 'Request', 'Response', 'Headers',
            'FormData', 'URLSearchParams', 'URL', 'Blob', 'File', 'FileReader',
            'AbortController', 'AbortSignal', 'Event', 'EventTarget', 'CustomEvent',
            'alert', 'confirm', 'prompt', 'atob', 'btoa',
        }
        
        # Extract all imports (what's available)
        imported_names = set()
        import_matches = re.findall(r"import\s+(?:(\w+)\s*,?\s*)?\{?\s*([^}]*)\}?\s*from", content)
        for match in import_matches:
            if match[0]:
                imported_names.add(match[0])
            if match[1]:
                for name in match[1].split(','):
                    name = name.strip().split(' as ')[-1].strip()
                    if name:
                        imported_names.add(name)
        
        # Also add type imports
        type_imports = re.findall(r"import\s+type\s+\{\s*([^}]+)\s*\}", content)
        for match in type_imports:
            for name in match.split(','):
                name = name.strip().split(' as ')[-1].strip()
                if name:
                    imported_names.add(name)
        
        # Extract all defined names in file
        defined_names = set()
        definition_patterns = [
            r'\b(?:const|let|var)\s+(\w+)',
            r'\bfunction\s+(\w+)',
            r'\bclass\s+(\w+)',
            r'\btype\s+(\w+)',
            r'\binterface\s+(\w+)',
            r'\benum\s+(\w+)',
            r'(?:const|let|var)\s+\{\s*([^}]+)\s*\}',  # Destructuring
        ]
        
        for pattern in definition_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        if m:
                            for name in m.split(','):
                                name = name.strip().split(':')[0].strip()
                                if name:
                                    defined_names.add(name)
                else:
                    for name in match.split(','):
                        name = name.strip().split(':')[0].strip()
                        if name:
                            defined_names.add(name)
        
        # Function parameters
        param_matches = re.findall(r'\(\s*(?:\{\s*)?([^)]+?)(?:\s*\})?\s*\)\s*(?:=>|{)', content)
        for match in param_matches:
            for param in match.split(','):
                param = param.strip().split(':')[0].split('=')[0].strip()
                if param and not param.startswith('{') and not param.startswith('['):
                    defined_names.add(param)
        
        all_available = globals_and_builtins | imported_names | defined_names
        
        # Check for potentially undefined usages (simplified check)
        # Look for identifiers that might be undefined
        potential_usages = re.findall(r'\b([A-Z][a-zA-Z0-9]+)\s*[(<]', content)
        for usage in set(potential_usages):
            if usage not in all_available and not re.search(rf'(?:const|let|var|function|class|type|interface)\s+{usage}\b', content):
                # Check if it's a component being used
                if re.search(rf'<{usage}[\s/>]', content):
                    errors.append(f"Component '{usage}' is used but not imported or defined")
        
        return errors

    def _check_string_errors(self, content: str) -> List[str]:
        """Check for string-related errors"""
        errors = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for obvious unclosed strings (simple check)
            single_quotes = line.count("'") - line.count("\\'") - line.count("\"'") - line.count("'\"")
            double_quotes = line.count('"') - line.count('\\"') - line.count("'\"") - line.count("\"'")
            
            # Skip template literals for this check
            if '`' in line:
                continue
            
            # Very basic check - if odd number of quotes, might be unclosed
            if single_quotes % 2 != 0 and '"' not in line:
                # Could be unclosed single quote string
                pass  # Too many false positives, skip
            
        # Check for template literal issues
        template_count = content.count('`')
        if template_count % 2 != 0:
            errors.append("Unclosed template literal (backtick)")
        
        return errors

    def _check_typescript_errors(self, content: str) -> List[str]:
        """Check for TypeScript specific errors"""
        errors = []
        
        # Check for 'any' type that might indicate missing types
        any_count = len(re.findall(r':\s*any\b', content))
        if any_count > 5:
            errors.append(f"Many 'any' types used ({any_count}) - consider adding proper types")
        
        # Check for type assertions that might fail
        if 'as unknown as' in content:
            errors.append("Dangerous type assertion pattern: 'as unknown as'")
        
        return errors

    def _check_react_errors(self, content: str) -> List[str]:
        """Check for React specific errors"""
        errors = []
        
        # Check for hooks used without import
        hooks = ['useState', 'useEffect', 'useContext', 'useReducer', 'useCallback', 
                 'useMemo', 'useRef', 'useLayoutEffect', 'useImperativeHandle']
        
        for hook in hooks:
            if re.search(rf'\b{hook}\s*\(', content):
                if not re.search(rf"import.*\b{hook}\b.*from\s+['\"]react['\"]", content):
                    if not re.search(rf"import\s+React\s+from\s+['\"]react['\"]", content):
                        # Check if React is imported (hooks can be accessed via React.useState)
                        if f'React.{hook}' not in content:
                            errors.append(f"Hook '{hook}' used but not imported from 'react'")
        
        # Check for key prop in lists
        if re.search(r'\.map\s*\([^)]+\)\s*=>\s*[^{]*<', content):
            # There's a map with JSX - check if key is used
            map_blocks = re.findall(r'\.map\s*\([^)]+\)\s*=>\s*(?:\{[^}]*return\s*)?(<[^>]+>)', content)
            for block in map_blocks:
                if 'key=' not in block and 'key =' not in block:
                    errors.append("JSX in .map() may be missing 'key' prop")
        
        return errors

    def _check_api_route_errors(self, content: str) -> List[str]:
        """Check for API route errors"""
        errors = []
        
        # Check for NextResponse import in Next.js API routes
        if 'NextResponse' in content:
            if not re.search(r"import.*NextResponse.*from\s+['\"]next/server['\"]", content):
                errors.append("NextResponse used but not imported from 'next/server'")
        
        # Check for proper response format
        handlers = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        for handler in handlers:
            if re.search(rf'export\s+(?:async\s+)?function\s+{handler}\b', content):
                # Check if it returns NextResponse or Response
                handler_match = re.search(rf'export\s+(?:async\s+)?function\s+{handler}[^{{]+\{{([^}}]+)\}}', content, re.DOTALL)
                if handler_match:
                    handler_body = handler_match.group(1)
                    if 'return' in handler_body:
                        if not re.search(r'return\s+(?:NextResponse|Response|new\s+Response)', handler_body):
                            if 'NextResponse.json' not in handler_body and 'Response.json' not in handler_body:
                                errors.append(f"{handler} handler may not be returning a proper Response")
        
        return errors

    def _check_structure_errors(self, content: str, filepath: str) -> List[str]:
        """Check for structural errors"""
        errors = []
        
        # Check for duplicate function definitions
        func_names = re.findall(r'(?:async\s+)?function\s+(\w+)\s*\(', content)
        seen = set()
        for name in func_names:
            if name in seen:
                errors.append(f"Duplicate function definition: '{name}'")
            seen.add(name)
        
        # Check for duplicate const/let/var in same scope (simplified)
        var_names = re.findall(r'(?:const|let|var)\s+(\w+)\s*[=:]', content)
        var_seen = {}
        for name in var_names:
            if name in var_seen:
                var_seen[name] += 1
            else:
                var_seen[name] = 1
        
        for name, count in var_seen.items():
            if count > 2:  # Allow some redefinition in different scopes
                errors.append(f"Variable '{name}' may be defined multiple times ({count})")
        
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
        architecture: Dict[str, Any],
        all_files: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Use LLM to fix a file with errors"""
        
        filepath = file.get("filepath", "")
        content = file.get("content", "")
        purpose = file.get("description", file.get("purpose", ""))
        
        error_list = "\n".join(f"- {e}" for e in errors[:10])
        
        # Get related files for context
        related_files_context = ""
        for f in all_files[:5]:
            if f.get("filepath") != filepath:
                fp = f.get("filepath", "")
                fc = f.get("content", "")[:500]
                related_files_context += f"\n\n--- {fp} (partial) ---\n{fc}"
        
        prompt = f"""Fix ALL errors in this file. Return the COMPLETE corrected file.

## File: {filepath}
## Purpose: {purpose}

## Errors Found:
{error_list}

## Current Code:
{content}

## Related Files (for import/export reference):
{related_files_context}

## Instructions:
1. Fix ALL the errors listed above
2. Ensure all imports are correct (check if module exports are default or named)
3. Ensure all brackets, braces, and parentheses are balanced
4. Ensure all JSX/TSX syntax is valid
5. Ensure all variables and functions are defined before use
6. Keep the original functionality intact
7. Return the COMPLETE fixed file

Return ONLY the corrected code. Start directly with import statements or code. No markdown, no explanations."""

        try:
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=8000
            )
            
            fixed_content = self._clean_response(response)
            
            return fixed_content
            
        except Exception as e:
            logger.error("fix_file_failed", filepath=filepath, error=str(e))
            return None

    async def _fix_package_json(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check and fix package.json for missing dependencies"""
        
        # Collect all imports from all files
        all_imports = set()
        for file in files:
            content = file.get("content", "")
            filepath = file.get("filepath", "")
            
            if not filepath.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue
            
            # Find npm package imports (not relative imports)
            import_matches = re.findall(r"import\s+.*?from\s+['\"]([^'\"./][^'\"]*)['\"]", content)
            for match in import_matches:
                # Get the package name (handle scoped packages)
                if match.startswith('@'):
                    pkg = '/'.join(match.split('/')[:2])
                else:
                    pkg = match.split('/')[0]
                all_imports.add(pkg)
        
        # Find package.json
        for i, file in enumerate(files):
            if file.get("filepath") == "package.json":
                try:
                    pkg = json.loads(file.get("content", "{}"))
                    deps = set(pkg.get("dependencies", {}).keys())
                    dev_deps = set(pkg.get("devDependencies", {}).keys())
                    all_deps = deps | dev_deps
                    
                    # Common built-in Node modules
                    builtins = {'fs', 'path', 'http', 'https', 'crypto', 'util', 'stream', 'events', 'url', 'os', 'child_process'}
                    
                    # Find missing dependencies
                    missing = all_imports - all_deps - builtins
                    
                    if missing:
                        logger.info("missing_dependencies", packages=list(missing))
                        
                        # Add missing dependencies
                        if "dependencies" not in pkg:
                            pkg["dependencies"] = {}
                        
                        for pkg_name in missing:
                            if pkg_name not in pkg["dependencies"]:
                                pkg["dependencies"][pkg_name] = "latest"
                        
                        files[i]["content"] = json.dumps(pkg, indent=2)
                        
                except json.JSONDecodeError:
                    pass
                break
        
        return files

    def _clean_response(self, response: str) -> str:
        """Clean LLM response"""
        content = response.strip()
        
        # Remove markdown code blocks
        code_block_patterns = [
            r'^```(?:typescript|tsx|javascript|jsx|ts|js)?\n',
            r'^```\n',
            r'\n```$',
            r'^```',
            r'```$',
        ]
        
        for pattern in code_block_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
        
        return content.strip()
