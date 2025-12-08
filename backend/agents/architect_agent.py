"""
Architect Agent - Analyzes requirements and designs complete system architecture
Enterprise-grade agent that dynamically determines project structure
"""
from typing import Dict, Any, List, Optional
import json
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class ArchitectAgent(BaseAgent):
    """
    Enterprise Architect Agent that analyzes ANY problem statement and designs:
    - Project type (frontend/backend/fullstack/microservices/mobile)
    - Complete folder structure
    - All required files
    - Technology stack
    - Database schema
    - API design
    - Infrastructure requirements
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.ARCHITECT,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Software Architect. Return JSON only, no markdown.

NEW ARCHITECTURE: You must organize files into 5 FIXED BATCHES for efficient generation.

Response format:
{
  "analysis": {"problem_summary": "...", "complexity": "simple|moderate|complex", "estimated_files": 23},
  "architecture": {"project_type": "fullstack_monolith", "pattern": "MVC"},
  "tech_stack": {
    "frontend": {"framework": "Next.js 14", "language": "TypeScript", "styling": "Tailwind CSS"},
    "backend": {"framework": "Next.js API Routes", "language": "TypeScript"},
    "database": {"primary": "SQLite", "library": "better-sqlite3"}
  },
  "batches": [
    {
      "name": "Skeleton",
      "description": "Configuration and setup files",
      "priority": 1,
      "files": [
        {"filepath": "package.json", "filename": "package.json", "purpose": "Dependencies", "language": "json", "category": "config"},
        {"filepath": "tsconfig.json", "filename": "tsconfig.json", "purpose": "TypeScript config", "language": "json", "category": "config"}
      ]
    },
    {
      "name": "Pages",
      "description": "Core pages and API routes",
      "priority": 2,
      "files": [
        {"filepath": "app/page.tsx", "filename": "page.tsx", "purpose": "Home page", "language": "typescript", "category": "frontend"}
      ]
    }
  ],
  "features": [{"id": "f1", "name": "Feature", "description": "...", "priority": "high"}]
}

CRITICAL BATCHING RULES:
1. Batch 1 "Skeleton" (8 files): package.json, tsconfig.json, tailwind.config.ts, next.config.js, postcss.config.js, .env.example, app/globals.css, app/layout.tsx
2. Batch 2 "Pages" (5 files): Core pages (app/page.tsx, feature pages, app/api routes, lib/db.ts)
3. Batch 3 "Components" (5-6 files): UI components (components/ui/*.tsx, feature components)
4. Batch 4 "Schemas" (3-4 files): lib/schema.ts (SQLite schema), types/index.ts, lib/utils.ts, lib/validations.ts
5. Batch 5 "Validation" (0 files): No files, just validation check

Total: 21-23 files across all batches. Include filename for each file.

Rules: Use Next.js 14 + TypeScript + Tailwind + better-sqlite3 for web apps.
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze problem statement and design complete architecture
        
        Args:
            task_data: Contains 'problem_statement' and optional 'constraints'
            
        Returns:
            Complete architecture design
        """
        activity = await self.start_activity("Designing system architecture")
        
        try:
            problem_statement = task_data.get("problem_statement", "")
            constraints = task_data.get("constraints", {})
            
            logger.info(
                "architecture_design_started",
                problem_length=len(problem_statement)
            )
            
            prompt = self._build_architecture_prompt(problem_statement, constraints)
            
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,  # Lower for more consistent architecture
                max_tokens=8000   # Need more tokens for complex architectures
            )
            
            architecture = self._parse_architecture_response(response)
            
            await self.complete_activity("completed")
            
            logger.info(
                "architecture_design_completed",
                project_type=architecture.get("architecture", {}).get("project_type"),
                file_count=len(architecture.get("files", []))
            )
            
            return {
                "architecture": architecture,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("architecture_design_failed", error=str(e))
            raise

    def _build_architecture_prompt(
        self,
        problem_statement: str,
        constraints: Dict[str, Any]
    ) -> str:
        """Build the prompt for architecture design"""
        constraint_text = ""
        if constraints:
            constraint_text = f"""
## Constraints & Preferences
{json.dumps(constraints, indent=2)}
"""
        
        return f"""Analyze this software project requirement and design a complete system architecture.

## Problem Statement
{problem_statement}
{constraint_text}

## Your Task

1. **Deeply analyze** what this project needs
2. **Determine** the optimal project type and architecture
3. **Design** a complete folder structure
4. **List ALL files** needed for a production-ready application
5. **Define** the technology stack
6. **Design** the database schema (if applicable)
7. **Design** the API (if applicable)
8. **List** all features to implement

Be thorough and comprehensive. For complex applications, you may need 50-100+ files.
Include tests, documentation, CI/CD, Docker files, environment configs, etc.

Respond with a complete JSON architecture document as specified in your system prompt."""

    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """Parse the architecture response from LLM"""
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

            architecture = json.loads(response)

            # Validate required fields
            required_fields = ["analysis", "architecture", "tech_stack"]
            for field in required_fields:
                if field not in architecture:
                    architecture[field] = {}

            # NEW: Ensure batches is a list
            if not isinstance(architecture.get("batches"), list) or len(architecture.get("batches", [])) == 0:
                # Generate default batches based on architecture
                architecture["batches"] = self._generate_default_batches(architecture)

            # OLD: Keep files for backward compatibility (flatten batches)
            if not isinstance(architecture.get("files"), list):
                architecture["files"] = self._flatten_batches_to_files(architecture.get("batches", []))

            return architecture

        except json.JSONDecodeError as e:
            logger.error("architecture_parse_error", error=str(e), response_preview=response[:500])
            # Return minimal valid architecture with default batches
            default_arch = {
                "analysis": {
                    "problem_summary": "Architecture parsing failed - using defaults",
                    "complexity": "moderate",
                    "estimated_files": 23
                },
                "architecture": {
                    "project_type": "fullstack_monolith",
                    "pattern": "MVC"
                },
                "tech_stack": {
                    "frontend": {"framework": "Next.js 14", "language": "TypeScript", "styling": "Tailwind CSS"},
                    "backend": {"framework": "Next.js API Routes", "language": "TypeScript"},
                    "database": {"primary": "SQLite", "library": "better-sqlite3"}
                },
                "batches": [],
                "files": [],
                "parse_error": str(e)
            }
            default_arch["batches"] = self._generate_default_batches(default_arch)
            default_arch["files"] = self._flatten_batches_to_files(default_arch["batches"])
            return default_arch
    
    def _generate_default_files(self, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a comprehensive default file list based on architecture"""
        tech_stack = architecture.get("tech_stack", {})
        frontend = tech_stack.get("frontend", {})
        backend = tech_stack.get("backend", {})
        database = tech_stack.get("database", {})
        
        files = []
        priority = 1
        
        # Config files (priority 1-10)
        config_files = [
            ("package.json", "json", "Project dependencies and scripts", "config"),
            ("tsconfig.json", "json", "TypeScript configuration", "config"),
            ("tailwind.config.ts", "typescript", "Tailwind CSS configuration", "config"),
            ("next.config.js", "javascript", "Next.js configuration", "config"),
            ("postcss.config.js", "javascript", "PostCSS configuration", "config"),
            (".eslintrc.json", "json", "ESLint configuration", "config"),
            (".prettierrc", "json", "Prettier configuration", "config"),
            (".env.example", "shell", "Environment variables template", "config"),
            (".gitignore", "text", "Git ignore patterns", "config"),
        ]
        
        for filename, lang, purpose, category in config_files:
            files.append({
                "filepath": filename,
                "filename": filename,
                "purpose": purpose,
                "language": lang,
                "priority": priority,
                "dependencies": [],
                "category": category
            })
            priority += 1
        
        # SQLite schema file
        if database.get("primary") == "SQLite":
            files.append({
                "filepath": "lib/schema.ts",
                "filename": "schema.ts",
                "purpose": "Database schema definitions and table creation with better-sqlite3",
                "language": "typescript",
                "priority": priority,
                "dependencies": [],
                "category": "database"
            })
            priority += 1
        
        # App layout and globals
        app_files = [
            ("app/layout.tsx", "layout.tsx", "typescript", "Root layout with providers and metadata", "frontend"),
            ("app/globals.css", "globals.css", "css", "Global styles with Tailwind directives", "frontend"),
            ("app/page.tsx", "page.tsx", "typescript", "Home page component", "frontend"),
            ("app/loading.tsx", "loading.tsx", "typescript", "Loading state component", "frontend"),
            ("app/error.tsx", "error.tsx", "typescript", "Error boundary component", "frontend"),
            ("app/not-found.tsx", "not-found.tsx", "typescript", "404 page component", "frontend"),
        ]
        
        for filepath, filename, lang, purpose, category in app_files:
            files.append({
                "filepath": filepath,
                "filename": filename,
                "purpose": purpose,
                "language": lang,
                "priority": priority,
                "dependencies": ["package.json", "tailwind.config.ts"],
                "category": category
            })
            priority += 1
        
        # Shared types
        files.append({
            "filepath": "types/index.ts",
            "filename": "index.ts",
            "purpose": "TypeScript type definitions for the entire application",
            "language": "typescript",
            "priority": priority,
            "dependencies": [],
            "category": "shared"
        })
        priority += 1
        
        # Lib utilities
        lib_files = [
            ("lib/utils.ts", "utils.ts", "Utility functions and helpers"),
            ("lib/db.ts", "db.ts", "Database connection using better-sqlite3"),
            ("lib/auth.ts", "auth.ts", "Authentication utilities"),
            ("lib/validations.ts", "validations.ts", "Input validation schemas"),
        ]
        
        for filepath, filename, purpose in lib_files:
            files.append({
                "filepath": filepath,
                "filename": filename,
                "purpose": purpose,
                "language": "typescript",
                "priority": priority,
                "dependencies": ["types/index.ts"],
                "category": "shared"
            })
            priority += 1
        
        # Components
        component_files = [
            ("components/ui/Button.tsx", "Button.tsx", "Reusable button component"),
            ("components/ui/Input.tsx", "Input.tsx", "Form input component"),
            ("components/ui/Card.tsx", "Card.tsx", "Card container component"),
            ("components/ui/Modal.tsx", "Modal.tsx", "Modal dialog component"),
            ("components/layout/Header.tsx", "Header.tsx", "Header with navigation"),
            ("components/layout/Footer.tsx", "Footer.tsx", "Footer component"),
            ("components/layout/Sidebar.tsx", "Sidebar.tsx", "Sidebar navigation"),
        ]
        
        for filepath, filename, purpose in component_files:
            files.append({
                "filepath": filepath,
                "filename": filename,
                "purpose": purpose,
                "language": "typescript",
                "priority": priority,
                "dependencies": ["components/ui/Button.tsx"] if "Button" not in filename else [],
                "category": "frontend"
            })
            priority += 1
        
        # API routes
        api_files = [
            ("app/api/auth/[...nextauth]/route.ts", "route.ts", "NextAuth.js authentication handler"),
            ("app/api/health/route.ts", "route.ts", "Health check endpoint"),
        ]
        
        for filepath, filename, purpose in api_files:
            files.append({
                "filepath": filepath,
                "filename": filename,
                "purpose": purpose,
                "language": "typescript",
                "priority": priority,
                "dependencies": ["lib/db.ts", "lib/auth.ts"],
                "category": "backend"
            })
            priority += 1
        
        # Middleware
        files.append({
            "filepath": "middleware.ts",
            "filename": "middleware.ts",
            "purpose": "Next.js middleware for auth and routing",
            "language": "typescript",
            "priority": priority,
            "dependencies": ["lib/auth.ts"],
            "category": "backend"
        })
        priority += 1
        
        # Docker files
        docker_files = [
            ("Dockerfile", "Dockerfile", "dockerfile", "Docker containerization", "infra"),
            ("docker-compose.yml", "docker-compose.yml", "yaml", "Docker Compose for local dev", "infra"),
        ]
        
        for filepath, filename, lang, purpose, category in docker_files:
            files.append({
                "filepath": filepath,
                "filename": filename,
                "purpose": purpose,
                "language": lang,
                "priority": priority,
                "dependencies": [],
                "category": category
            })
            priority += 1
        
        # Documentation
        files.append({
            "filepath": "README.md",
            "filename": "README.md",
            "purpose": "Project documentation with setup instructions",
            "language": "markdown",
            "priority": priority,
            "dependencies": [],
            "category": "docs"
        })
        
        return files

    def _generate_default_batches(self, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate 5 fixed batches for efficient code generation.

        NEW ARCHITECTURE:
        - Batch 1: Skeleton (8 config files)
        - Batch 2: Pages (5 core pages/routes)
        - Batch 3: Components (5-6 UI components)
        - Batch 4: Schemas (3-4 types/schema files)
        - Batch 5: Validation (0 files, just check)
        """
        tech_stack = architecture.get("tech_stack", {})
        frontend = tech_stack.get("frontend", {})
        database = tech_stack.get("database", {})

        batches = []

        # ========================================
        # BATCH 1: SKELETON (8 files)
        # ========================================
        skeleton_files = [
            {
                "filepath": "package.json",
                "filename": "package.json",
                "purpose": "Project dependencies and npm scripts",
                "language": "json",
                "category": "config",
                "priority": 1
            },
            {
                "filepath": "tsconfig.json",
                "filename": "tsconfig.json",
                "purpose": "TypeScript configuration",
                "language": "json",
                "category": "config",
                "priority": 2
            },
            {
                "filepath": "tailwind.config.ts",
                "filename": "tailwind.config.ts",
                "purpose": "Tailwind CSS configuration",
                "language": "typescript",
                "category": "config",
                "priority": 3
            },
            {
                "filepath": "next.config.js",
                "filename": "next.config.js",
                "purpose": "Next.js configuration",
                "language": "javascript",
                "category": "config",
                "priority": 4
            },
            {
                "filepath": "postcss.config.js",
                "filename": "postcss.config.js",
                "purpose": "PostCSS configuration for Tailwind",
                "language": "javascript",
                "category": "config",
                "priority": 5
            },
            {
                "filepath": ".env.example",
                "filename": ".env.example",
                "purpose": "Environment variables template",
                "language": "shell",
                "category": "config",
                "priority": 6
            },
            {
                "filepath": "app/globals.css",
                "filename": "globals.css",
                "purpose": "Global styles with Tailwind directives",
                "language": "css",
                "category": "frontend",
                "priority": 7
            },
            {
                "filepath": "app/layout.tsx",
                "filename": "layout.tsx",
                "purpose": "Root layout with providers and metadata",
                "language": "typescript",
                "category": "frontend",
                "priority": 8
            }
        ]

        batches.append({
            "name": "Skeleton",
            "description": "Configuration and setup files",
            "priority": 1,
            "files": skeleton_files
        })

        # ========================================
        # BATCH 2: PAGES (5 files)
        # ========================================
        pages_files = [
            {
                "filepath": "app/page.tsx",
                "filename": "page.tsx",
                "purpose": "Home page component",
                "language": "typescript",
                "category": "frontend",
                "priority": 9
            },
            {
                "filepath": "app/dashboard/page.tsx",
                "filename": "page.tsx",
                "purpose": "Dashboard page",
                "language": "typescript",
                "category": "frontend",
                "priority": 10
            },
            {
                "filepath": "app/api/health/route.ts",
                "filename": "route.ts",
                "purpose": "Health check API endpoint",
                "language": "typescript",
                "category": "backend",
                "priority": 11
            },
            {
                "filepath": "app/api/data/route.ts",
                "filename": "route.ts",
                "purpose": "Main data API endpoint",
                "language": "typescript",
                "category": "backend",
                "priority": 12
            },
            {
                "filepath": "lib/db.ts",
                "filename": "db.ts",
                "purpose": "Database connection using better-sqlite3",
                "language": "typescript",
                "category": "shared",
                "priority": 13
            }
        ]

        batches.append({
            "name": "Pages",
            "description": "Core pages and API routes",
            "priority": 2,
            "files": pages_files
        })

        # ========================================
        # BATCH 3: COMPONENTS (6 files)
        # ========================================
        components_files = [
            {
                "filepath": "components/ui/Button.tsx",
                "filename": "Button.tsx",
                "purpose": "Reusable button component",
                "language": "typescript",
                "category": "frontend",
                "priority": 14
            },
            {
                "filepath": "components/ui/Input.tsx",
                "filename": "Input.tsx",
                "purpose": "Form input component",
                "language": "typescript",
                "category": "frontend",
                "priority": 15
            },
            {
                "filepath": "components/ui/Card.tsx",
                "filename": "Card.tsx",
                "purpose": "Card container component",
                "language": "typescript",
                "category": "frontend",
                "priority": 16
            },
            {
                "filepath": "components/layout/Header.tsx",
                "filename": "Header.tsx",
                "purpose": "Header with navigation",
                "language": "typescript",
                "category": "frontend",
                "priority": 17
            },
            {
                "filepath": "components/DataForm.tsx",
                "filename": "DataForm.tsx",
                "purpose": "Main data entry form",
                "language": "typescript",
                "category": "frontend",
                "priority": 18
            },
            {
                "filepath": "components/DataList.tsx",
                "filename": "DataList.tsx",
                "purpose": "List view for data items",
                "language": "typescript",
                "category": "frontend",
                "priority": 19
            }
        ]

        batches.append({
            "name": "Components",
            "description": "UI components",
            "priority": 3,
            "files": components_files
        })

        # ========================================
        # BATCH 4: SCHEMAS (4 files)
        # ========================================
        schemas_files = [
            {
                "filepath": "types/index.ts",
                "filename": "index.ts",
                "purpose": "TypeScript type definitions",
                "language": "typescript",
                "category": "shared",
                "priority": 20
            },
            {
                "filepath": "lib/utils.ts",
                "filename": "utils.ts",
                "purpose": "Utility functions and helpers",
                "language": "typescript",
                "category": "shared",
                "priority": 21
            },
            {
                "filepath": "lib/validations.ts",
                "filename": "validations.ts",
                "purpose": "Input validation schemas",
                "language": "typescript",
                "category": "shared",
                "priority": 22
            }
        ]

        # Add SQLite schema file
        if database.get("primary") == "SQLite":
            schemas_files.insert(0, {
                "filepath": "lib/schema.ts",
                "filename": "schema.ts",
                "purpose": "Database schema definitions and table creation with better-sqlite3",
                "language": "typescript",
                "category": "database",
                "priority": 23
            })

        batches.append({
            "name": "Schemas",
            "description": "Database schema and TypeScript types",
            "priority": 4,
            "files": schemas_files
        })

        # ========================================
        # BATCH 5: VALIDATION (0 files)
        # ========================================
        batches.append({
            "name": "Validation",
            "description": "Integration validation only",
            "priority": 5,
            "files": []
        })

        return batches

    def _flatten_batches_to_files(self, batches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flatten batches into a single list of files for backward compatibility.
        """
        files = []
        for batch in batches:
            batch_files = batch.get("files", [])
            files.extend(batch_files)
        return files


class FilePlannerAgent(BaseAgent):
    """
    File Planner Agent - Takes architecture and generates detailed file specifications
    Ensures all files are properly planned with correct dependencies
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.MODULE_DESIGNER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Senior Software Engineer specializing in project structure and code organization.

Given a system architecture, you create detailed file specifications for every file that needs to be generated.

For each file, you specify:
1. **filepath**: Complete path from project root
2. **filename**: Just the filename
3. **purpose**: What this file does
4. **language**: Programming language
5. **priority**: Generation order (1 = first, higher = later)
6. **dependencies**: Files that must be generated before this one
7. **category**: config|frontend|backend|shared|test|docs|infra
8. **content_hints**: Key things that should be in this file
9. **imports**: Expected imports/dependencies
10. **exports**: What this file exports

## File Categories

- **config**: package.json, tsconfig, eslint, prettier, env files
- **frontend**: React components, pages, layouts, styles
- **backend**: API routes, services, controllers, middleware
- **shared**: Types, interfaces, utilities, constants
- **database**: Schema, migrations, seeds
- **test**: Unit tests, integration tests, e2e tests
- **docs**: README, API docs, contributing guides
- **infra**: Docker, CI/CD, deployment configs

## CRITICAL: Required Config Files

For **Vite + React + TypeScript** projects, ALWAYS include these config files:
- package.json
- tsconfig.json (main TypeScript config)
- tsconfig.node.json (Vite/Node config - REQUIRED for Vite)
- vite.config.ts
- postcss.config.js (if using Tailwind)
- tailwind.config.js (if using Tailwind)
- index.html (Vite entry point)

For **Next.js** projects, ALWAYS include:
- package.json
- tsconfig.json
- next.config.js or next.config.mjs
- postcss.config.js (if using Tailwind)
- tailwind.config.js or tailwind.config.ts (if using Tailwind)

## IMPORTANT: Limit to 25-35 files maximum to avoid rate limits.

## Response Format

```json
{
    "total_files": 30,
    "files_by_category": {
        "config": 6,
        "frontend": 10,
        "backend": 8,
        "shared": 4,
        "docs": 2
    },
    "generation_order": [
        {"phase": 1, "description": "Config files", "files": ["package.json", "tsconfig.json"]},
        {"phase": 2, "description": "Shared types", "files": ["types/index.ts"]}
    ],
    "files": [
        {
            "filepath": "package.json",
            "filename": "package.json",
            "purpose": "Project dependencies and npm scripts",
            "language": "json",
            "priority": 1,
            "dependencies": [],
            "category": "config",
            "content_hints": [
                "Include Next.js 14 dependencies",
                "Add Tailwind CSS",
                "Include testing libraries",
                "Add TypeScript"
            ],
            "imports": [],
            "exports": []
        }
    ]
}
```

Focus on essential files only. Limit to 25-35 files maximum.
Skip test files unless specifically requested. Missing files can be added later.
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan all files needed based on architecture
        """
        activity = await self.start_activity("Planning file structure")
        
        try:
            architecture = task_data.get("architecture", {})
            problem_statement = task_data.get("problem_statement", "")
            
            prompt = f"""Based on this architecture, create a complete file plan:

## Architecture
{json.dumps(architecture, indent=2)}

## Original Problem
{problem_statement}

Create a detailed plan for EVERY file that needs to be generated.
Include all config files, source files, test files, documentation, and infrastructure files.
Order files by generation priority - config first, then shared types, then implementation.

Respond with a complete JSON file plan."""

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=8000
            )
            
            file_plan = self._parse_file_plan(response)
            
            await self.complete_activity("completed")
            
            return {
                "file_plan": file_plan,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("file_planning_failed", error=str(e))
            raise

    def _parse_file_plan(self, response: str) -> Dict[str, Any]:
        """Parse file plan response"""
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
            logger.error("file_plan_parse_error", error=str(e))
            return {"files": [], "error": str(e)}

