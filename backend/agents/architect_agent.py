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

## YOUR TASK
Analyze the problem statement and design a COMPLETE architecture with implementation files for ALL features.

## CRITICAL RULES

1. Extract ALL features from the problem statement
2. For EACH feature, generate these files:
   - Page: app/[feature-slug]/page.tsx
   - Form component: components/[feature-slug]/[Feature]Form.tsx
   - List component: components/[feature-slug]/[Feature]List.tsx
   - API route: app/api/[feature-slug]/route.ts
   - Hook: hooks/use[Feature].ts

3. Create database models for ALL entities mentioned
4. Generate as many files as needed for a complete implementation (typically 30-100)
5. Use kebab-case for folders, PascalCase for components

## RESPONSE FORMAT

{
  "analysis": {
    "problem_summary": "Brief summary of what the app does",
    "complexity": "simple|moderate|complex",
    "estimated_files": 25
  },
  "architecture": {
    "project_type": "fullstack_monolith",
    "pattern": "MVC"
  },
  "tech_stack": {
    "frontend": {"framework": "Next.js 14", "language": "TypeScript", "styling": "Tailwind CSS"},
    "backend": {"framework": "Next.js API Routes", "language": "TypeScript"},
    "database": {"primary": "PostgreSQL", "client": "pg"}
  },
  "database_schema": {
    "tables": [
      {"name": "table_name", "columns": ["id SERIAL PRIMARY KEY", "field1 VARCHAR(255)", "created_at TIMESTAMP DEFAULT NOW()"]}
    ]
  },
  "features": [
    {"id": "f1", "name": "Feature Name", "description": "What this feature does", "priority": "high"}
  ],
  "files": [
    {"filepath": "path/to/file.ext", "filename": "file.ext", "purpose": "What this file does", "language": "typescript", "category": "frontend|backend|config|database|shared", "feature": "f1"}
  ]
}

## FILE CATEGORIES
- config: package.json, tsconfig.json, tailwind.config.ts, next.config.js, postcss.config.js
- database: lib/db.ts (pg Pool connection), db/schema.sql (SQL schema), db/seed.sql (optional seed data)
- shared: types/index.ts, lib/utils.ts
- frontend: app/*/page.tsx, components/*/*.tsx, hooks/*.ts
- backend: app/api/*/route.ts

## DATABASE APPROACH (IMPORTANT)
Use PostgreSQL with 'pg' package (node-postgres) - NO PRISMA:
- lib/db.ts: Create a Pool connection using 'pg' package
- db/schema.sql: SQL file with CREATE TABLE statements
- API routes use raw SQL queries with parameterized queries for security

## DOCKER FILES (REQUIRED)
ALWAYS include these Docker files for easy deployment:
1. **Dockerfile**: Multi-stage build for Next.js
2. **docker-compose.yml**: Services for app (port 3000) and PostgreSQL db (port 5432)
3. **.dockerignore**: Exclude node_modules, .next, .git, etc.

IMPORTANT: Analyze the ACTUAL problem statement and generate files specific to THAT application. Do NOT use generic placeholder names.
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
        confirmed_features = constraints.get("confirmed_features", [])
        
        if confirmed_features:
            constraint_text = "\n\n## CONFIRMED FEATURES (You MUST implement these):\n"
            for f in confirmed_features:
                constraint_text += f"- **{f.get('name')}**: {f.get('description')}\n"
        
        return f"""Design a complete architecture for this application:

## Problem Statement
{problem_statement}
{constraint_text}

## YOUR TASK

1. **Analyze** the problem statement carefully
2. **Identify ALL features** that need to be built
3. **Design database models** for all data entities
4. **Generate implementation files** for EACH feature:
   - A page file: app/[feature-slug]/page.tsx
   - Form component: components/[feature-slug]/[Feature]Form.tsx
   - List component: components/[feature-slug]/[Feature]List.tsx
   - Card component: components/[feature-slug]/[Feature]Card.tsx
   - API routes: app/api/[feature-slug]/route.ts and app/api/[feature-slug]/[id]/route.ts
   - React hook: hooks/use[Feature].ts

5. **Include essential config files**: package.json, tsconfig.json, tailwind.config.ts, next.config.js, postcss.config.js, db/schema.sql, lib/db.ts
6. **Include shared files**: types/index.ts, lib/db.ts, lib/utils.ts
7. **Include layout**: app/layout.tsx, app/page.tsx (dashboard), components/layout/Navigation.tsx

## RULES
- Generate as many files as needed for a complete implementation (typically 30-100)
- Use descriptive names based on the ACTUAL features in the problem statement
- Every feature needs: page + form + list + API + hook
- Include the "feature" field in each file to link it to a feature ID
- Do NOT use generic placeholder names - use names from the actual problem

Respond with JSON only, following the format in your system prompt."""

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
            
            # Ensure files is a list
            if not isinstance(architecture.get("files"), list) or len(architecture.get("files", [])) == 0:
                # Generate default files based on architecture
                architecture["files"] = self._generate_default_files(architecture)
            
            return architecture
            
        except json.JSONDecodeError as e:
            logger.error("architecture_parse_error", error=str(e), response_preview=response[:500])
            # Return minimal valid architecture with default files
            default_arch = {
                "analysis": {
                    "problem_summary": "Architecture parsing failed - using defaults",
                    "complexity": "moderate"
                },
                "architecture": {
                    "project_type": "fullstack_monolith",
                    "pattern": "MVC"
                },
                "tech_stack": {
                    "frontend": {"framework": "Next.js 14", "language": "TypeScript"},
                    "backend": {"framework": "Next.js API Routes", "language": "TypeScript"},
                    "database": {"primary": "PostgreSQL", "client": "pg"}
                },
                "files": [],
                "parse_error": str(e)
            }
            default_arch["files"] = self._generate_default_files(default_arch)
            return default_arch
    
    def _generate_default_files(self, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a comprehensive file list based on architecture AND features.
        This is a FALLBACK when the LLM doesn't return a proper file list.
        It dynamically generates files based on whatever features are in the architecture.
        """
        tech_stack = architecture.get("tech_stack", {})
        database = tech_stack.get("database", {})
        features = architecture.get("features", [])
        db_schema = architecture.get("database_schema", {})
        
        files = []
        priority = 1
        
        # ========================================
        # CONFIG FILES (Always needed)
        # ========================================
        config_files = [
            ("package.json", "json", "Project dependencies and scripts"),
            ("tsconfig.json", "json", "TypeScript configuration"),
            ("tailwind.config.ts", "typescript", "Tailwind CSS configuration"),
            ("next.config.js", "javascript", "Next.js configuration"),
            ("postcss.config.js", "javascript", "PostCSS configuration"),
            (".env.example", "shell", "Environment variables template"),
            (".gitignore", "text", "Git ignore patterns"),
        ]
        
        for filename, lang, purpose in config_files:
            files.append({
                "filepath": filename,
                "filename": filename,
                "purpose": purpose,
                "language": lang,
                "priority": priority,
                "category": "config"
            })
            priority += 1
        
        # ========================================
        # DATABASE SCHEMA (PostgreSQL with pg)
        # ========================================
        if database.get("primary") == "PostgreSQL":
            tables = db_schema.get("tables", db_schema.get("models", []))
            tables_desc = ", ".join([t.get("name", "") for t in tables]) if tables else "Application tables"
            
            content_hints = []
            for t in tables:
                columns = t.get("columns", t.get("fields", []))
                content_hints.append(f"CREATE TABLE {t.get('name')}: {', '.join(columns)}")
            
            files.append({
                "filepath": "db/schema.sql",
                "filename": "schema.sql",
                "purpose": f"SQL schema with tables: {tables_desc}",
                "language": "sql",
                "priority": priority,
                "category": "database",
                "content_hints": content_hints if content_hints else [
                    "CREATE TABLE statements",
                    "Use SERIAL for auto-increment IDs",
                    "Include created_at and updated_at timestamps",
                    "Add appropriate indexes"
                ]
            })
            priority += 1
            
            files.append({
                "filepath": "db/init.sql",
                "filename": "init.sql",
                "purpose": "Database initialization script (creates tables)",
                "language": "sql",
                "priority": priority,
                "category": "database",
                "content_hints": [
                    "Include schema.sql content",
                    "Add any seed data if needed"
                ]
            })
            priority += 1
        
        # ========================================
        # APP LAYOUT AND BASE PAGES
        # ========================================
        files.append({
            "filepath": "app/layout.tsx",
            "filename": "layout.tsx",
            "purpose": "Root layout with providers and navigation",
            "language": "typescript",
            "priority": priority,
            "category": "frontend"
        })
        priority += 1
        
        files.append({
            "filepath": "app/globals.css",
            "filename": "globals.css",
            "purpose": "Global styles with Tailwind directives",
            "language": "css",
            "priority": priority,
            "category": "frontend"
        })
        priority += 1
        
        # Dashboard/Home page with links to all features
        feature_links = [f.get("name", "Feature") for f in features]
        files.append({
            "filepath": "app/page.tsx",
            "filename": "page.tsx",
            "purpose": "Dashboard/Home page with overview and navigation",
            "language": "typescript",
            "priority": priority,
            "category": "frontend",
            "content_hints": [f"Link to {name}" for name in feature_links] if feature_links else ["Main landing page"]
        })
        priority += 1
        
        # ========================================
        # SHARED FILES
        # ========================================
        # Types - include interfaces for all features
        type_hints = [f"Interface for {f.get('name', 'Feature')}" for f in features]
        files.append({
            "filepath": "types/index.ts",
            "filename": "index.ts",
            "purpose": "TypeScript interfaces for all data models",
            "language": "typescript",
            "priority": priority,
            "category": "shared",
            "content_hints": type_hints if type_hints else ["Define types based on data models"]
        })
        priority += 1
        
        files.append({
            "filepath": "lib/db.ts",
            "filename": "db.ts",
            "purpose": "PostgreSQL connection pool using pg package",
            "language": "typescript",
            "priority": priority,
            "category": "shared",
            "content_hints": [
                "Import Pool from 'pg'",
                "Create pool with DATABASE_URL from env",
                "Export query helper function",
                "Export pool for direct access"
            ]
        })
        priority += 1
        
        files.append({
            "filepath": "lib/utils.ts",
            "filename": "utils.ts",
            "purpose": "Utility functions (cn, formatDate, etc.)",
            "language": "typescript",
            "priority": priority,
            "category": "shared"
        })
        priority += 1
        
        # ========================================
        # UI COMPONENTS (Reusable)
        # ========================================
        ui_components = [
            ("Button.tsx", "Reusable button with variants"),
            ("Input.tsx", "Form input with validation"),
            ("Card.tsx", "Card container component"),
            ("Modal.tsx", "Modal dialog component"),
        ]
        
        for filename, purpose in ui_components:
            files.append({
                "filepath": f"components/ui/{filename}",
                "filename": filename,
                "purpose": purpose,
                "language": "typescript",
                "priority": priority,
                "category": "frontend"
            })
            priority += 1
        
        # Navigation with links to all features
        files.append({
            "filepath": "components/layout/Navigation.tsx",
            "filename": "Navigation.tsx",
            "purpose": "Main navigation component",
            "language": "typescript",
            "priority": priority,
            "category": "frontend",
            "content_hints": [f"Navigation link to {f.get('name', 'Feature')}" for f in features]
        })
        priority += 1
        
        # ========================================
        # FEATURE-SPECIFIC FILES (Dynamic)
        # ========================================
        for feature in features:
            feature_id = feature.get("id", f"f{priority}")
            feature_name = feature.get("name", "Feature")
            feature_desc = feature.get("description", "")
            
            # Convert to URL-friendly slug (kebab-case)
            feature_slug = self._to_slug(feature_name)
            
            # Convert to PascalCase for component names
            feature_pascal = self._to_pascal_case(feature_name)
            
            # Skip if we couldn't generate valid names
            if not feature_slug or not feature_pascal:
                continue
            
            # 1. Feature Page
            files.append({
                "filepath": f"app/{feature_slug}/page.tsx",
                "filename": "page.tsx",
                "purpose": f"{feature_name} page - {feature_desc}" if feature_desc else f"Main page for {feature_name}",
                "language": "typescript",
                "priority": priority,
                "category": "frontend",
                "feature": feature_id,
                "content_hints": [
                    f"Display {feature_pascal}List component",
                    f"Include {feature_pascal}Form for adding new items",
                    "Handle loading and error states"
                ]
            })
            priority += 1
            
            # 2. Form Component
            files.append({
                "filepath": f"components/{feature_slug}/{feature_pascal}Form.tsx",
                "filename": f"{feature_pascal}Form.tsx",
                "purpose": f"Form to create/edit {feature_name}",
                "language": "typescript",
                "priority": priority,
                "category": "frontend",
                "feature": feature_id,
                "content_hints": [
                    "Form with all required fields",
                    "Input validation",
                    "Submit to API endpoint",
                    "Success/error feedback"
                ]
            })
            priority += 1
            
            # 3. List Component
            files.append({
                "filepath": f"components/{feature_slug}/{feature_pascal}List.tsx",
                "filename": f"{feature_pascal}List.tsx",
                "purpose": f"Display list of {feature_name} items",
                "language": "typescript",
                "priority": priority,
                "category": "frontend",
                "feature": feature_id,
                "content_hints": [
                    "Fetch data using the hook",
                    "Map items to Card components",
                    "Empty state handling",
                    "Loading skeleton"
                ]
            })
            priority += 1
            
            # 4. Card Component
            files.append({
                "filepath": f"components/{feature_slug}/{feature_pascal}Card.tsx",
                "filename": f"{feature_pascal}Card.tsx",
                "purpose": f"Display single {feature_name} item",
                "language": "typescript",
                "priority": priority,
                "category": "frontend",
                "feature": feature_id,
                "content_hints": [
                    "Display item details",
                    "Edit and delete actions",
                    "Styled with Tailwind"
                ]
            })
            priority += 1
            
            # 5. API Route (collection)
            files.append({
                "filepath": f"app/api/{feature_slug}/route.ts",
                "filename": "route.ts",
                "purpose": f"API: GET all {feature_name}, POST new {feature_name}",
                "language": "typescript",
                "priority": priority,
                "category": "backend",
                "feature": feature_id,
                "content_hints": [
                    "GET: Fetch all items from database",
                    "POST: Create new item with validation",
                    "Error handling with proper status codes"
                ]
            })
            priority += 1
            
            # 6. API Route (single item)
            files.append({
                "filepath": f"app/api/{feature_slug}/[id]/route.ts",
                "filename": "route.ts",
                "purpose": f"API: GET/PUT/DELETE single {feature_name}",
                "language": "typescript",
                "priority": priority,
                "category": "backend",
                "feature": feature_id,
                "content_hints": [
                    "GET: Fetch single item by ID",
                    "PUT: Update item",
                    "DELETE: Remove item",
                    "404 handling for missing items"
                ]
            })
            priority += 1
            
            # 7. React Hook
            files.append({
                "filepath": f"hooks/use{feature_pascal}.ts",
                "filename": f"use{feature_pascal}.ts",
                "purpose": f"React hook for {feature_name} CRUD operations",
                "language": "typescript",
                "priority": priority,
                "category": "frontend",
                "feature": feature_id,
                "content_hints": [
                    "Fetch items with loading/error states",
                    "Create, update, delete mutations",
                    "Optimistic updates",
                    "Use SWR or React Query pattern"
                ]
            })
            priority += 1
        
        # ========================================
        # DOCKER FILES (For containerized deployment)
        # ========================================
        
        # Get app name for docker-compose service naming
        app_name = architecture.get("analysis", {}).get("problem_summary", "app")[:20].lower()
        app_slug = self._to_slug(app_name) or "app"
        
        # Dockerfile for Next.js app
        files.append({
            "filepath": "Dockerfile",
            "filename": "Dockerfile",
            "purpose": "Docker container for the Next.js application",
            "language": "dockerfile",
            "priority": priority,
            "category": "infra",
            "content_hints": [
                "Multi-stage build for smaller image",
                "Use Node 18 alpine as base",
                "COPY package.json package-lock.json* (NO yarn.lock)",
                "Install dependencies with npm install --legacy-peer-deps (NOT yarn)",
                "Build Next.js app with npm run build",
                "Run with node server.js on port 3000",
                "NO Prisma - uses pg package directly",
                "DO NOT use yarn - use npm only"
            ]
        })
        priority += 1
        
        # Docker Compose for full stack
        db_name = database.get("primary", "PostgreSQL").lower()
        files.append({
            "filepath": "docker-compose.yml",
            "filename": "docker-compose.yml",
            "purpose": "Docker Compose for running app with database",
            "language": "yaml",
            "priority": priority,
            "category": "infra",
            "content_hints": [
                "DO NOT include version field (it's obsolete)",
                f"Service: app (Next.js on port 3000)",
                f"Service: db ({db_name} on port 5432)",
                "Volume for database persistence",
                "Environment variables for DATABASE_URL",
                "Depends_on with condition: service_healthy",
                "Health checks for db service",
                "restart: unless-stopped for both services"
            ]
        })
        priority += 1
        
        # .dockerignore
        files.append({
            "filepath": ".dockerignore",
            "filename": ".dockerignore",
            "purpose": "Files to exclude from Docker build context",
            "language": "text",
            "priority": priority,
            "category": "infra",
            "content_hints": [
                "node_modules",
                ".next",
                ".git",
                "*.log",
                ".env.local"
            ]
        })
        priority += 1
        
        # ========================================
        # README
        # ========================================
        files.append({
            "filepath": "README.md",
            "filename": "README.md",
            "purpose": "Project documentation with Docker setup instructions",
            "language": "markdown",
            "priority": priority,
            "category": "docs",
            "content_hints": [
                "Project description",
                "Docker setup instructions (docker-compose up)",
                "Environment variables setup",
                "Database migration commands",
                "Development vs Production modes"
            ]
        })
        
        return files
    
    def _to_slug(self, name: str) -> str:
        """Convert a name to URL-friendly slug (kebab-case)"""
        if not name:
            return ""
        # Replace spaces and underscores with hyphens
        slug = name.lower().replace(" ", "-").replace("_", "-")
        # Remove any character that's not alphanumeric or hyphen
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        # Remove multiple consecutive hyphens
        while '--' in slug:
            slug = slug.replace('--', '-')
        # Remove leading/trailing hyphens
        return slug.strip('-')
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert a name to PascalCase"""
        if not name:
            return ""
        # Split by spaces, hyphens, and underscores
        words = name.replace('-', ' ').replace('_', ' ').split()
        # Capitalize each word and join
        pascal = ''.join(word.capitalize() for word in words)
        # Remove non-alphanumeric characters
        return ''.join(c for c in pascal if c.isalnum())


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

## IMPORTANT: Plan ALL files needed for a complete implementation.

## Response Format

```json
{
    "total_files": 45,
    "files_by_category": {
        "config": 6,
        "frontend": 20,
        "backend": 15,
        "shared": 4
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

Plan for a complete, production-ready application. Include all necessary files.
Ensure all features in the architecture are fully covered with implementation files.
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

