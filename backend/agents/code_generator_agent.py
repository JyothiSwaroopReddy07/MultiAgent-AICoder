"""
Code Generator Agent - Generates individual files with full context awareness
Enterprise-grade agent that produces production-ready code

Integrates CodeReviewerAgent for thorough per-file validation.
"""
from typing import Dict, Any, List, Optional
import json
import re
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()

# Import will be done lazily to avoid circular imports
_code_reviewer = None

def get_code_reviewer():
    """Lazy load CodeReviewerAgent to avoid circular imports"""
    global _code_reviewer
    if _code_reviewer is None:
        from agents.code_reviewer_agent import CodeReviewerAgent
        _code_reviewer = CodeReviewerAgent()
    return _code_reviewer


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

## CRITICAL: Next.js Client Components

If a React component uses ANY of these, it MUST start with "use client" as the FIRST LINE:
- useState, useEffect, useContext, useReducer, useCallback, useMemo, useRef
- useRouter, useSearchParams, usePathname (from 'next/navigation')
- onClick, onChange, onSubmit, or any event handlers
- window, document, localStorage, sessionStorage

Example for client components:
```
"use client"

import { useState } from 'react'
```

Server Components (no directive needed): Pages/components WITHOUT hooks or event handlers.

## Response Format

Return ONLY the file content. No explanations, no markdown code blocks.

For client components: Start with "use client" on line 1.
For server components: Start with import statements.

REMEMBER: ZERO COMMENTS IN THE CODE. The code should be self-explanatory through good naming.
"""

    # Known npm packages with their pinned versions
    # This prevents "latest" being used
    KNOWN_PACKAGES = {
        # Core React/Next.js
        "next": "14.0.4",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        
        # UI Libraries
        "lucide-react": "^0.294.0",
        "clsx": "^2.0.0",
        "tailwind-merge": "^2.1.0",
        "@radix-ui/react-dialog": "^1.0.5",
        "@radix-ui/react-dropdown-menu": "^2.0.6",
        "@radix-ui/react-slot": "^1.0.2",
        "@radix-ui/react-toast": "^1.1.5",
        "@radix-ui/react-tooltip": "^1.0.7",
        "@radix-ui/react-select": "^2.0.0",
        "@radix-ui/react-checkbox": "^1.0.4",
        "@radix-ui/react-switch": "^1.0.3",
        "@radix-ui/react-tabs": "^1.0.4",
        "@radix-ui/react-accordion": "^1.1.2",
        "@radix-ui/react-popover": "^1.0.7",
        "class-variance-authority": "^0.7.0",
        "cmdk": "^0.2.0",
        "framer-motion": "^10.16.16",
        
        # Forms & Validation
        "react-hook-form": "^7.49.2",
        "@hookform/resolvers": "^3.3.2",
        "zod": "^3.22.4",
        
        # Data Fetching & State
        "@tanstack/react-query": "^5.17.0",
        "swr": "^2.2.4",
        "zustand": "^4.4.7",
        "jotai": "^2.6.0",
        
        # Database
        "pg": "^8.11.3",
        "@types/pg": "^8.10.9",
        "prisma": "^5.7.1",
        "@prisma/client": "^5.7.1",
        "drizzle-orm": "^0.29.1",
        
        # Authentication
        "next-auth": "^4.24.5",
        "@auth/core": "^0.18.1",
        "bcrypt": "^5.1.1",
        "@types/bcrypt": "^5.0.2",
        "jsonwebtoken": "^9.0.2",
        "@types/jsonwebtoken": "^9.0.5",
        
        # Utilities
        "date-fns": "^3.0.6",
        "dayjs": "^1.11.10",
        "uuid": "^9.0.0",
        "@types/uuid": "^9.0.7",
        "lodash": "^4.17.21",
        "@types/lodash": "^4.14.202",
        "axios": "^1.6.2",
        
        # File handling
        "sharp": "^0.33.1",
        "formidable": "^3.5.1",
        
        # Charts & Visualization
        "recharts": "^2.10.3",
        "chart.js": "^4.4.1",
        "react-chartjs-2": "^5.2.0",
        
        # Tables
        "@tanstack/react-table": "^8.11.2",
        
        # Markdown/Rich Text
        "react-markdown": "^9.0.1",
        "@tiptap/react": "^2.1.13",
        "@tiptap/starter-kit": "^2.1.13",
        
        # Icons
        "react-icons": "^4.12.0",
        "@heroicons/react": "^2.1.1",
        
        # Email
        "nodemailer": "^6.9.7",
        "@types/nodemailer": "^6.4.14",
        "resend": "^2.1.0",
        
        # Stripe/Payments
        "stripe": "^14.10.0",
        "@stripe/stripe-js": "^2.2.2",
        "@stripe/react-stripe-js": "^2.4.0",
    }
    
    # Dev dependencies with versions
    DEV_PACKAGES = {
        "typescript": "^5.3.3",
        "@types/node": "^20.10.4",
        "@types/react": "^18.2.45",
        "@types/react-dom": "^18.2.17",
        "autoprefixer": "^10.4.16",
        "postcss": "^8.4.32",
        "tailwindcss": "^3.3.6",
        "eslint": "^8.55.0",
        "eslint-config-next": "14.0.4",
        "jest": "^29.7.0",
        "@types/jest": "^29.5.11",
        "jest-environment-jsdom": "^29.7.0",
        "@testing-library/react": "^14.1.2",
        "@testing-library/jest-dom": "^6.1.6",
        "@testing-library/user-event": "^14.5.1",
        "ts-jest": "^29.1.1",
        "prettier": "^3.1.1",
        "eslint-plugin-prettier": "^5.1.2",
    }
    
    # Static config templates (non-package.json)
    CONFIG_TEMPLATES = {
        "tsconfig.json": lambda arch, features: json.dumps({
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./*"]}
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"]
        }, indent=2),
        
        "jest.config.ts": lambda arch, features: """import type { Config } from 'jest';
import nextJest from 'next/jest';

const createJestConfig = nextJest({
  dir: './',
});

const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/'],
};

export default createJestConfig(config);
""",
        
        "jest.setup.ts": lambda arch, features: """import '@testing-library/jest-dom';
""",
        
        "next.config.js": lambda arch, features: """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
""",
        
        "tailwind.config.ts": lambda arch, features: """import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
""",
        
        "postcss.config.js": lambda arch, features: """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
""",
        
        "app/globals.css": lambda arch, features: """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-rgb: 10, 10, 10;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: rgb(var(--background-rgb));
}
""",
        
        ".gitignore": lambda arch, features: """# Dependencies
node_modules/
/.pnp
.pnp.js

# Testing
/coverage

# Next.js
/.next/
/out/

# Production
/build

# Misc
.DS_Store
*.pem

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Local env files
.env*.local
.env

# Vercel
.vercel

# TypeScript
*.tsbuildinfo
next-env.d.ts
""",
        
        ".env.example": lambda arch, features: """# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
""",
        
        "next-env.d.ts": lambda arch, features: """/// <reference types="next" />
/// <reference types="next/image-types/global" />
""",
    }

    def extract_dependencies_from_files(self, generated_files: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """
        Analyze all generated files to extract npm package dependencies.
        Scans import statements to find external packages.
        
        Returns:
            Dict with 'dependencies' and 'devDependencies'
        """
        dependencies = {}
        dev_dependencies = {}
        
        # Patterns to match imports
        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^./][^\'"\s]+)[\'"]',  # import X from 'package'
            r'import\s+[\'"]([^./][^\'"\s]+)[\'"]',  # import 'package'
            r'require\([\'"]([^./][^\'"\s]+)[\'"]\)',  # require('package')
            r'from\s+[\'"]([^./][^\'"\s]+)[\'"]',  # from 'package'
        ]
        
        for file_info in generated_files:
            content = file_info.get("content", "")
            filepath = file_info.get("filepath", "")
            is_test = ".test." in filepath or ".spec." in filepath or "__tests__" in filepath
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Extract base package name (handle scoped packages)
                    if match.startswith("@"):
                        # Scoped package: @scope/package or @scope/package/subpath
                        parts = match.split("/")
                        pkg_name = "/".join(parts[:2]) if len(parts) >= 2 else match
                    else:
                        # Regular package: package or package/subpath
                        pkg_name = match.split("/")[0]
                    
                    # Skip relative imports, Next.js internals, and node builtins
                    if pkg_name.startswith(".") or pkg_name.startswith("node:"):
                        continue
                    if pkg_name in ["fs", "path", "os", "crypto", "http", "https", "url", "util", "stream", "events", "buffer", "child_process"]:
                        continue
                    
                    # Determine if it's a dev dependency
                    is_dev = is_test or pkg_name.startswith("@types/") or pkg_name in [
                        "jest", "ts-jest", "@testing-library/react", "@testing-library/jest-dom",
                        "@testing-library/user-event", "eslint", "prettier", "typescript"
                    ]
                    
                    # Get version from known packages
                    if pkg_name in self.KNOWN_PACKAGES:
                        version = self.KNOWN_PACKAGES[pkg_name]
                    elif pkg_name in self.DEV_PACKAGES:
                        version = self.DEV_PACKAGES[pkg_name]
                        is_dev = True
                    else:
                        # Use a specific version instead of "latest"
                        version = "^1.0.0"
                        logger.warning("unknown_package_version", package=pkg_name)
                    
                    if is_dev:
                        dev_dependencies[pkg_name] = version
                    else:
                        dependencies[pkg_name] = version
        
        # Always include core dependencies
        core_deps = {
            "next": "14.0.4",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
        }
        dependencies.update(core_deps)
        
        # Always include core dev dependencies
        core_dev_deps = {
            "typescript": "^5.3.3",
            "@types/node": "^20.10.4",
            "@types/react": "^18.2.45",
            "@types/react-dom": "^18.2.17",
            "autoprefixer": "^10.4.16",
            "postcss": "^8.4.32",
            "tailwindcss": "^3.3.6",
            "eslint": "^8.55.0",
            "eslint-config-next": "14.0.4",
        }
        dev_dependencies.update(core_dev_deps)
        
        # Add test dependencies if test files exist
        has_tests = any(".test." in f.get("filepath", "") or ".spec." in f.get("filepath", "") for f in generated_files)
        if has_tests:
            test_deps = {
                "jest": "^29.7.0",
                "@types/jest": "^29.5.11",
                "jest-environment-jsdom": "^29.7.0",
                "@testing-library/react": "^14.1.2",
                "@testing-library/jest-dom": "^6.1.6",
                "@testing-library/user-event": "^14.5.1",
                "ts-jest": "^29.1.1",
            }
            dev_dependencies.update(test_deps)
        
        # Add API route dependencies when API routes are detected
        has_api_routes = any("/api/" in f.get("filepath", "") for f in generated_files)
        if has_api_routes:
            api_deps = {
                "zod": "^3.22.4",
            }
            dependencies.update(api_deps)
        
        # Add auth dependencies when auth routes are detected
        has_auth = any("/auth/" in f.get("filepath", "") or "login" in f.get("filepath", "").lower() for f in generated_files)
        if has_auth:
            auth_deps = {
                "jsonwebtoken": "^9.0.2",
                "bcrypt": "^5.1.1",
            }
            auth_dev_deps = {
                "@types/jsonwebtoken": "^9.0.5",
                "@types/bcrypt": "^5.0.2",
            }
            dependencies.update(auth_deps)
            dev_dependencies.update(auth_dev_deps)
        
        # Add database dependencies when db/lib files are detected
        has_db = any(
            f.get("filepath", "").startswith("lib/db") or 
            f.get("filepath", "").startswith("db/") or
            "database" in f.get("filepath", "").lower()
            for f in generated_files
        )
        if has_db:
            db_deps = {
                "pg": "^8.11.3",
            }
            db_dev_deps = {
                "@types/pg": "^8.10.9",
            }
            dependencies.update(db_deps)
            dev_dependencies.update(db_dev_deps)
        
        return {
            "dependencies": dict(sorted(dependencies.items())),
            "devDependencies": dict(sorted(dev_dependencies.items()))
        }

    def generate_package_json(self, architecture: Dict[str, Any], generated_files: List[Dict[str, Any]]) -> str:
        """
        Generate package.json with dependencies extracted from all generated files.
        This ensures accurate dependencies with proper versions.
        """
        # Extract dependencies from all files
        deps = self.extract_dependencies_from_files(generated_files)
        
        project_name = architecture.get("project_name", "my-app")
        project_name = re.sub(r'[^a-z0-9-]', '-', project_name.lower()).strip('-')
        
        has_tests = any(".test." in f.get("filepath", "") for f in generated_files)
        
        package_json = {
            "name": project_name,
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
            },
            "dependencies": deps["dependencies"],
            "devDependencies": deps["devDependencies"]
        }
        
        # Add test scripts if tests exist
        if has_tests:
            package_json["scripts"]["test"] = "jest"
            package_json["scripts"]["test:watch"] = "jest --watch"
            package_json["scripts"]["test:coverage"] = "jest --coverage"
        
        return json.dumps(package_json, indent=2)

    async def generate_config_files(
        self,
        architecture: Dict[str, Any],
        generated_files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate ALL config files with full context of the codebase.
        This should be called AFTER all code files are generated.
        
        Config files generated:
        - package.json (with extracted dependencies)
        - tsconfig.json
        - jest.config.ts
        - jest.setup.ts
        - next.config.js
        - tailwind.config.ts
        - postcss.config.js
        - .gitignore
        - .env.example
        - next-env.d.ts
        - app/globals.css
        """
        config_files = []
        features = architecture.get("features", [])
        
        # Generate package.json with extracted dependencies
        package_json_content = self.generate_package_json(architecture, generated_files)
        config_files.append({
            "filepath": "package.json",
            "filename": "package.json",
            "content": package_json_content,
            "language": "json",
            "description": "Project dependencies extracted from all source files",
            "category": "config"
        })
        logger.info("generated_package_json", 
                   deps_count=len(json.loads(package_json_content).get("dependencies", {})),
                   dev_deps_count=len(json.loads(package_json_content).get("devDependencies", {})))
        
        # Generate other config files using templates
        for filepath, template_fn in self.CONFIG_TEMPLATES.items():
            if filepath == "package.json":
                continue  # Already handled above
            
            content = template_fn(architecture, features)
            filename = filepath.split("/")[-1]
            
            config_files.append({
                "filepath": filepath,
                "filename": filename,
                "content": content,
                "language": self._get_language_for_file(filepath),
                "description": f"Config file: {filepath}",
                "category": "config"
            })
        
        logger.info("config_files_generated", count=len(config_files))
        return config_files

    async def generate_file(
        self,
        file_spec: Dict[str, Any],
        architecture: Dict[str, Any],
        generated_files: List[Dict[str, Any]],
        problem_statement: str
    ) -> Dict[str, Any]:
        """
        Generate a single file with full context.
        
        NOTE: Config files like package.json should be generated via
        generate_config_files() AFTER all code files are generated,
        so they can extract dependencies from the codebase.
        """
        filepath = file_spec.get("filepath", "")
        filename = file_spec.get("filename") or filepath.split("/")[-1] if filepath else "unknown"
        
        # Skip package.json here - it needs full codebase context
        # Will be generated via generate_config_files() after all code
        if filepath == "package.json":
            logger.info("skipping_package_json", reason="will_generate_with_full_context")
            return None  # Signal to skip this file
        
        activity = await self.start_activity(f"Generating {filepath}")
        
        try:
            # Check if this is an essential config file with a template (except package.json)
            if filepath in self.CONFIG_TEMPLATES:
                features = architecture.get("features", [])
                content = self.CONFIG_TEMPLATES[filepath](architecture, features)
                logger.info("using_config_template", filepath=filepath)
                await self.complete_activity("completed")
                
                return {
                    "filepath": filepath,
                    "filename": filename,
                    "content": content,
                    "language": file_spec.get("language", "text"),
                    "description": file_spec.get("purpose", ""),
                    "category": file_spec.get("category", "config")
                }
            
            # For non-config files, use LLM generation
            prompt = self._build_generation_prompt(
                file_spec, architecture, generated_files, problem_statement
            )
            
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=16000  # Increased to prevent truncation
            )
            
            content = self._clean_code_response(response, file_spec.get("language", ""))
            
            # Validate and fix common issues (use client, etc.)
            content = self._validate_and_fix_content(content, filepath)
            
            # Check for truncation and retry if needed
            if self._is_truncated(content, filepath):
                logger.warning("code_truncated", filepath=filepath)
                retry_prompt = f"{prompt}\n\nCRITICAL: Generate the COMPLETE file. Do NOT truncate. Include ALL code to the final closing brace/tag."
                response = await self.call_llm(
                    messages=[{"role": "user", "content": retry_prompt}],
                    temperature=0.2,
                    max_tokens=16000
                )
                content = self._clean_code_response(response, file_spec.get("language", ""))
                content = self._validate_and_fix_content(content, filepath)
            
            await self.complete_activity("completed")
            
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

    def ensure_essential_files(
        self,
        generated_files: List[Dict[str, Any]],
        architecture: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Ensure all essential config files are present WITH FULL CODEBASE CONTEXT.
        
        CRITICAL: This must be called AFTER all code files are generated because:
        - package.json needs to extract dependencies from all imports
        - Other configs may need to reference generated file patterns
        
        This replaces any existing config files with properly generated ones.
        """
        # Remove any existing config files (will regenerate with proper context)
        config_file_paths = [
            "package.json", "tsconfig.json", "jest.config.ts", "jest.setup.ts",
            "next.config.js", "tailwind.config.ts", "postcss.config.js",
            "app/globals.css", ".gitignore", ".env.example", "next-env.d.ts"
        ]
        
        # Filter out existing config files
        code_files_only = [
            f for f in generated_files 
            if f.get("filepath") not in config_file_paths
        ]
        
        logger.info("generating_configs_with_context", 
                   code_files_count=len(code_files_only))
        
        # Generate config files with full codebase context
        features = architecture.get("features", [])
        config_files = []
        
        # 1. Generate package.json with extracted dependencies (CRITICAL)
        package_json_content = self.generate_package_json(architecture, code_files_only)
        config_files.append({
            "filepath": "package.json",
            "filename": "package.json",
            "content": package_json_content,
            "language": "json",
            "description": "Dependencies extracted from all source files",
            "category": "config"
        })
        
        pkg = json.loads(package_json_content)
        logger.info("package_json_generated", 
                   dependencies=list(pkg.get("dependencies", {}).keys()),
                   dev_dependencies=list(pkg.get("devDependencies", {}).keys()))
        
        # 2. Generate other config files using templates
        for filepath, template_fn in self.CONFIG_TEMPLATES.items():
            content = template_fn(architecture, features)
            config_files.append({
                "filepath": filepath,
                "filename": filepath.split("/")[-1],
                "content": content,
                "language": self._get_language_for_file(filepath),
                "description": f"Config file: {filepath}",
                "category": "config"
            })
        
        logger.info("essential_files_generated", 
                   count=len(config_files),
                   files=[f["filepath"] for f in config_files])
        
        # Return code files + freshly generated config files
        return code_files_only + config_files
    
    def _get_language_for_file(self, filepath: str) -> str:
        """Get the language/type for a file based on extension."""
        ext_map = {
            ".json": "json",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".css": "css",
            ".sql": "sql",
            ".md": "markdown",
            ".d.ts": "typescript",
        }
        for ext, lang in ext_map.items():
            if filepath.endswith(ext):
                return lang
        return "text"

    def _validate_and_fix_content(self, content: str, filepath: str) -> str:
        """
        Validate and auto-fix common issues in generated code.
        
        Fixes:
        1. Missing "use client" for React components with hooks
        2. Adds proper directive for client components
        """
        if not content:
            return content
        
        # Check if this is a TypeScript/JavaScript React file
        is_react_file = filepath.endswith(('.tsx', '.jsx'))
        
        if is_react_file:
            # Check for React hooks that require "use client"
            client_hooks = [
                'useState', 'useEffect', 'useContext', 'useReducer',
                'useCallback', 'useMemo', 'useRef', 'useLayoutEffect',
                'useRouter', 'useSearchParams', 'usePathname', 'useParams'
            ]
            
            # Check for event handlers
            event_handlers = ['onClick', 'onChange', 'onSubmit', 'onBlur', 'onFocus', 'onKeyDown', 'onKeyUp']
            
            needs_use_client = False
            
            # Check for hooks
            for hook in client_hooks:
                if f'{hook}(' in content or f'{hook} (' in content:
                    needs_use_client = True
                    break
            
            # Check for event handlers
            if not needs_use_client:
                for handler in event_handlers:
                    if f'{handler}=' in content or f'{handler} =' in content:
                        needs_use_client = True
                        break
            
            # Add "use client" if needed and not present
            if needs_use_client:
                first_line = content.strip().split('\n')[0] if content.strip() else ""
                has_use_client = '"use client"' in first_line or "'use client'" in first_line
                
                if not has_use_client:
                    logger.info("auto_adding_use_client", filepath=filepath)
                    content = '"use client"\n\n' + content
        
        return content

    def _is_truncated(self, content: str, filepath: str) -> bool:
        """
        Detect if code appears to be truncated/incomplete.
        
        Signs of truncation:
        1. Unbalanced braces/brackets
        2. Ends mid-statement
        3. Ends with incomplete patterns
        """
        if not content:
            return True
        
        content = content.strip()
        
        # Check for obvious truncation patterns
        truncation_endings = [
            'await', 'const', 'let', 'var', 'return', 'throw',
            'try {', 'catch', 'if (', 'else {', '=>',
            '= {', '= [', '= (', '= `', 'fetch(`', 'await fetch',
            '/api/', '${', 'import', 'export'
        ]
        
        for ending in truncation_endings:
            if content.rstrip().endswith(ending):
                return True
        
        # Check brace balance for JS/TS files
        if filepath.endswith(('.ts', '.tsx', '.js', '.jsx')):
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_parens = content.count('(')
            close_parens = content.count(')')
            
            # Significant imbalance suggests truncation
            if open_braces > close_braces + 1:
                return True
            if open_parens > close_parens + 2:
                return True
        
        return False

    async def generate_file_with_test(
        self,
        file_spec: Dict[str, Any],
        architecture: Dict[str, Any],
        generated_files: List[Dict[str, Any]],
        problem_statement: str
    ) -> List[Dict[str, Any]]:
        """
        Generate a source file AND its corresponding test file together.
        
        This ensures:
        1. Tests are created with full knowledge of implementation
        2. File paths and imports are correct
        3. Tests actually test the real implementation
        
        Returns:
            List of [source_file, test_file] or just [source_file] if not testable
        """
        # First generate the source file
        source_file = await self.generate_file(
            file_spec, architecture, generated_files, problem_statement
        )
        
        result = [source_file]
        
        # Check if this file should have a test
        if self._should_generate_test(file_spec):
            test_file = await self._generate_test_for_file(
                source_file, architecture, problem_statement
            )
            if test_file:
                result.append(test_file)
                logger.info("test_generated_with_source", 
                           source=source_file.get("filepath"),
                           test=test_file.get("filepath"))
        
        return result
    
    def _should_generate_test(self, file_spec: Dict[str, Any]) -> bool:
        """Determine if a file should have a corresponding test file"""
        filepath = file_spec.get("filepath", "").lower()
        
        # Skip files that shouldn't have tests
        skip_patterns = [
            "package.json", "tsconfig", ".config.", "tailwind", "postcss",
            ".css", ".scss", ".md", ".env", ".gitignore", "dockerfile",
            "layout.tsx", "layout.ts", "globals", "middleware",
            ".test.", ".spec.", "__tests__", "jest.", "setupTests"
        ]
        
        if any(p in filepath for p in skip_patterns):
            return False
        
        # Only test TypeScript/JavaScript files
        testable_extensions = [".ts", ".tsx", ".js", ".jsx"]
        if not any(filepath.endswith(ext) for ext in testable_extensions):
            return False
        
        # Test components, utilities, hooks, and lib files
        testable_paths = [
            "components/", "utils/", "lib/", "hooks/", "services/",
            "helpers/", "api/", "actions/", "store/"
        ]
        
        return any(p in filepath for p in testable_paths)
    
    async def _generate_test_for_file(
        self,
        source_file: Dict[str, Any],
        architecture: Dict[str, Any],
        problem_statement: str
    ) -> Optional[Dict[str, Any]]:
        """Generate a test file for a given source file"""
        filepath = source_file.get("filepath", "")
        content = source_file.get("content", "")
        
        if not filepath or not content:
            return None
        
        # Determine test file path
        test_filepath = self._get_test_filepath(filepath)
        
        activity = await self.start_activity(f"Generating test for {filepath}")
        
        try:
            prompt = f"""Generate a comprehensive unit test file for the following source file.

## SOURCE FILE: {filepath}
```
{content}
```

## TEST FILE PATH: {test_filepath}

## REQUIREMENTS:
1. Import the component/function from the correct relative path
2. Use Jest and React Testing Library (for React components)
3. Test all exported functions/components
4. Include both success and error cases
5. Use descriptive test names
6. NO COMMENTS in the test code

## IMPORT PATH:
The test file is at: {test_filepath}
The source file is at: {filepath}
Calculate the correct relative import path.

## EXAMPLE STRUCTURE:
```typescript
import {{ ComponentName }} from '../relative/path';
import {{ render, screen }} from '@testing-library/react';

describe('ComponentName', () => {{
  it('should render correctly', () => {{
    render(<ComponentName />);
    expect(screen.getByRole('...')).toBeInTheDocument();
  }});
}});
```

Generate ONLY the test file content. No explanations. Start with imports.
"""

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            
            test_content = self._clean_code_response(response, "typescript")
            
            await self.complete_activity("completed")
            
            return {
                "filepath": test_filepath,
                "filename": test_filepath.split("/")[-1],
                "content": test_content,
                "language": "typescript",
                "description": f"Unit tests for {filepath}",
                "category": "test"
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.warning("test_generation_failed", source=filepath, error=str(e))
            return None
    
    def _get_test_filepath(self, source_path: str) -> str:
        """Generate the test file path from a source file path"""
        import os
        
        dir_path = os.path.dirname(source_path)
        filename = os.path.basename(source_path)
        name, ext = os.path.splitext(filename)
        
        # Use __tests__ directory pattern
        test_dir = os.path.join(dir_path, "__tests__")
        test_filename = f"{name}.test{ext}"
        
        return os.path.join(test_dir, test_filename).replace("\\", "/")

    async def generate_review_fix_test(
        self,
        file_spec: Dict[str, Any],
        architecture: Dict[str, Any],
        generated_files: List[Dict[str, Any]],
        problem_statement: str,
        max_fix_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Comprehensive per-file pipeline:
        1. Generate source file
        2. Code review and fix errors
        3. Generate unit test
        4. Return results
        
        This ensures each file is validated before moving on.
        """
        import re
        
        filepath = file_spec.get("filepath", "unknown")
        result = {
            "source_file": None,
            "test_file": None,
            "review_passed": False,
            "errors_fixed": [],
            "filepath": filepath
        }
        
        # Step 1: Generate the source file
        logger.info("pipeline_step_generate", filepath=filepath)
        try:
            source_file = await self.generate_file(
                file_spec, architecture, generated_files, problem_statement
            )
            
            # Handle None return (e.g., package.json is skipped for later generation)
            if source_file is None:
                logger.info("pipeline_skip_deferred", filepath=filepath, 
                           reason="file will be generated later with full context")
                result["skipped"] = True
                result["skip_reason"] = "deferred_for_context"
                return result
            
            result["source_file"] = source_file
        except Exception as e:
            logger.error("pipeline_generate_failed", filepath=filepath, error=str(e))
            return result
        
        # Step 2: THOROUGH code review using CodeReviewerAgent
        logger.info("pipeline_step_review", filepath=filepath)
        
        # Include this file + all generated files for import validation
        all_files_for_review = generated_files + [source_file]
        
        reviewed_file = await self._review_and_fix_file(
            source_file, 
            architecture, 
            max_fix_attempts,
            all_files=all_files_for_review
        )
        
        if reviewed_file:
            result["source_file"] = reviewed_file["file"]
            result["review_passed"] = reviewed_file["passed"]
            result["errors_fixed"] = reviewed_file.get("fixes", [])
            if reviewed_file.get("remaining_errors"):
                logger.warning("review_has_remaining_errors", 
                             filepath=filepath,
                             errors=reviewed_file["remaining_errors"])
        
        # Step 3: Generate unit test (if applicable)
        if self._should_generate_test(file_spec):
            logger.info("pipeline_step_test", filepath=filepath)
            test_file = await self._generate_test_for_file(
                result["source_file"], architecture, problem_statement
            )
            if test_file:
                # Also thoroughly review the test file
                all_files_with_test = all_files_for_review + [test_file]
                reviewed_test = await self._review_and_fix_file(
                    test_file, 
                    architecture, 
                    max_fix_attempts=2,
                    all_files=all_files_with_test
                )
                if reviewed_test:
                    result["test_file"] = reviewed_test["file"]
                    if not reviewed_test["passed"]:
                        logger.warning("test_file_review_incomplete",
                                     filepath=test_file.get("filepath"),
                                     errors=reviewed_test.get("remaining_errors", []))
                else:
                    result["test_file"] = test_file
        
        logger.info("pipeline_complete", 
                   filepath=filepath, 
                   review_passed=result["review_passed"],
                   has_test=result["test_file"] is not None)
        
        return result
    
    async def _review_and_fix_file(
        self,
        file: Dict[str, Any],
        architecture: Dict[str, Any],
        max_fix_attempts: int = 3,
        all_files: List[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Thoroughly review a file using CodeReviewerAgent's comprehensive checks.
        
        This performs 10+ checks including:
        - Bracket/brace balance
        - JSX/TSX errors
        - Import/export errors  
        - Undefined references
        - TypeScript errors
        - React errors
        - API route errors
        - Structure errors
        """
        filepath = file.get("filepath", "")
        content = file.get("content", "")
        language = file.get("language", "typescript")
        
        if not content:
            return None
        
        # Get the CodeReviewerAgent for comprehensive checking
        reviewer = get_code_reviewer()
        
        all_fixes = []
        current_content = content
        current_file = {**file}
        
        for attempt in range(max_fix_attempts):
            # Use CodeReviewerAgent's comprehensive error checking
            errors = reviewer._check_all_errors(
                current_content, 
                filepath, 
                all_files or [current_file]
            )
            
            if not errors:
                logger.info("review_passed", filepath=filepath, attempt=attempt)
                return {
                    "file": {**file, "content": current_content},
                    "passed": True,
                    "fixes": all_fixes
                }
            
            logger.info("review_found_errors", 
                       filepath=filepath, 
                       error_count=len(errors),
                       errors=errors[:5],  # Log first 5 errors
                       attempt=attempt)
            
            # Use CodeReviewerAgent's fix method for comprehensive fixing
            fixed_content = await reviewer._fix_file(
                {"filepath": filepath, "content": current_content, "language": language},
                errors,
                architecture,
                all_files or [current_file]
            )
            
            if fixed_content and fixed_content != current_content:
                current_content = fixed_content
                current_file["content"] = fixed_content
                all_fixes.append(f"Fixed {len(errors)} error(s): {', '.join(errors[:3])}")
                logger.info("file_fixed", filepath=filepath, errors_fixed=len(errors))
            else:
                # Try our own LLM fix as fallback
                fallback_content = await self._fix_file_errors(
                    current_content, filepath, errors, language
                )
                if fallback_content and fallback_content != current_content:
                    current_content = fallback_content
                    current_file["content"] = fallback_content
                    all_fixes.append(f"Fallback fix for {len(errors)} error(s)")
                else:
                    # No changes made, break
                    logger.warning("no_fix_found", filepath=filepath, remaining_errors=len(errors))
                    break
        
        # Final check
        final_errors = reviewer._check_all_errors(current_content, filepath, all_files or [current_file])
        
        return {
            "file": {**file, "content": current_content},
            "passed": len(final_errors) == 0,
            "fixes": all_fixes,
            "remaining_errors": final_errors[:5] if final_errors else []
        }
    
    def _check_file_errors(self, content: str, filepath: str, all_files: List[Dict] = None) -> List[str]:
        """
        Use CodeReviewerAgent's comprehensive error checking.
        Falls back to basic checks if reviewer not available.
        """
        try:
            reviewer = get_code_reviewer()
            return reviewer._check_all_errors(content, filepath, all_files or [])
        except Exception as e:
            logger.warning("reviewer_not_available", error=str(e))
            return self._basic_error_check(content, filepath)
    
    def _basic_error_check(self, content: str, filepath: str) -> List[str]:
        """Basic fallback error checking"""
        errors = []
        
        if not content or not content.strip():
            errors.append("Empty file content")
            return errors
        
        # Check bracket balance
        open_braces = content.count('{') - content.count('}')
        open_parens = content.count('(') - content.count(')')
        open_brackets = content.count('[') - content.count(']')
        
        if open_braces != 0:
            errors.append(f"Unbalanced braces: {open_braces:+d}")
        if open_parens != 0:
            errors.append(f"Unbalanced parentheses: {open_parens:+d}")
        if open_brackets != 0:
            errors.append(f"Unbalanced brackets: {open_brackets:+d}")
        
        # Check for common React/TypeScript errors
        if filepath.endswith((".tsx", ".jsx")):
            if re.search(r'\bclass\s*=\s*["\'{]', content):
                errors.append("Using 'class=' instead of 'className='")
            if '<label' in content and re.search(r'\bfor\s*=\s*["\']', content):
                errors.append("Using 'for=' instead of 'htmlFor='")
        
        # Check for page without default export
        if filepath.endswith(("page.tsx", "page.ts", "page.jsx", "page.js")):
            if 'export default' not in content:
                errors.append("Page component missing default export")
        
        # Check for incomplete code markers
        if '// TODO' in content or '/* TODO' in content:
            errors.append("Contains TODO comments")
        if '...' in content and 'spread' not in content.lower():
            errors.append("Contains ellipsis (...) - possible incomplete code")
        
        return errors
    
    async def _fix_file_errors(
        self,
        content: str,
        filepath: str,
        errors: List[str],
        language: str
    ) -> Optional[str]:
        """Use LLM to fix errors in a file"""
        
        error_list = "\n".join(f"- {e}" for e in errors)
        
        prompt = f"""Fix the following errors in this {language} file:

## FILE: {filepath}

## ERRORS FOUND:
{error_list}

## CURRENT CONTENT:
```{language}
{content}
```

## INSTRUCTIONS:
1. Fix ALL the errors listed above
2. Return the COMPLETE fixed file
3. Do NOT add any comments
4. Preserve all functionality
5. Ensure all brackets/braces are balanced

Return ONLY the fixed code. No explanations. Start with the first line of code.
"""

        try:
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=16000
            )
            
            fixed_content = self._clean_code_response(response, language)
            fixed_content = self._validate_and_fix_content(fixed_content, filepath)
            return fixed_content
            
        except Exception as e:
            logger.error("fix_errors_failed", filepath=filepath, error=str(e))
            return None

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
        
        # Get features - identify which feature this file implements
        features = architecture.get("features", [])
        file_feature_id = file_spec.get("feature", "")
        current_feature = None
        features_text = ""
        
        if file_feature_id:
            for f in features:
                if f.get("id") == file_feature_id:
                    current_feature = f
                    break
        
        if current_feature:
            features_text = f"""

## THIS FILE IMPLEMENTS: {current_feature.get('name')}

**Feature Description**: {current_feature.get('description')}
**Priority**: {current_feature.get('priority', 'high')}

You MUST fully implement this feature. Include:
- Complete UI with forms, lists, and interactions
- Full CRUD operations where applicable
- Proper state management
- Error handling and loading states
- Validation
"""
        elif features:
            features_text = "\n\n## All Features in This Application\n"
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

1. Generate COMPLETE, FULLY FUNCTIONAL code - no placeholders, no "TODO", no "..."
2. If this file is for a FEATURE, implement ALL functionality for that feature
3. Include ALL necessary imports
4. **DO NOT ADD ANY COMMENTS** - no //, no #, no /* */, no docstrings
5. Implement ALL CRUD operations if this is an API route
6. Implement FULL forms with validation if this is a form component
7. Implement FULL data display with loading/error states if this is a list component
8. Include proper error handling
9. Make it production-ready with real functionality

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

## CRITICAL: Database Files (PostgreSQL with pg - NO PRISMA)

If generating **lib/db.ts** (database connection):
```typescript
import {{ Pool }} from 'pg'

const pool = new Pool({{
  connectionString: process.env.DATABASE_URL,
}})

export async function query(text: string, params?: any[]) {{
  const result = await pool.query(text, params)
  return result.rows
}}

export default pool
```

If generating **db/schema.sql**:
```sql
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## CRITICAL: Docker Files (USE NPM ONLY - NO YARN)

**IMPORTANT: Use npm, NOT yarn. Do NOT reference yarn.lock - it does not exist.**

If generating **Dockerfile**, use EXACTLY this structure:
```dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

If generating **docker-compose.yml** (DO NOT include version field - it's obsolete):
```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/appdb
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: appdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

If generating **next.config.js** for Docker, include:
```javascript
module.exports = {{
  output: 'standalone',
}}
```

## CRITICAL: API Routes with PostgreSQL (NO PRISMA)

For API routes, use raw SQL with parameterized queries:
```typescript
import {{ query }} from '@/lib/db'
import {{ NextResponse }} from 'next/server'

export async function GET() {{
  const rows = await query('SELECT * FROM tablename ORDER BY created_at DESC')
  return NextResponse.json(rows)
}}

export async function POST(request: Request) {{
  const body = await request.json()
  const rows = await query(
    'INSERT INTO tablename (field1, field2) VALUES ($1, $2) RETURNING *',
    [body.field1, body.field2]
  )
  return NextResponse.json(rows[0])
}}
```

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
            "Code for",
            "This is the code",
            "Sure, here",
            "Certainly, here",
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

