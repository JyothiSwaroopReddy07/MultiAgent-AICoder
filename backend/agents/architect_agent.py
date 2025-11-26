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
        return """You are a Principal Software Architect with 20+ years of experience designing enterprise systems.

Your role is to analyze ANY software requirement and produce a COMPLETE, DETAILED system architecture.

**CRITICAL: You must analyze the problem deeply and determine the optimal architecture.**

## Analysis Framework

### Step 1: Understand the Problem Domain
- What type of application is this? (Web app, API, CLI, Mobile, Desktop, etc.)
- Who are the users? (Consumers, Businesses, Developers, Internal teams)
- What is the scale? (Personal project, Startup MVP, Enterprise system)
- What are the core features?

### Step 2: Determine Project Type
Based on analysis, choose the most appropriate:
- **frontend_only**: Pure frontend (React, Vue, Angular) - no backend needed
- **backend_only**: API/service only (FastAPI, Express, Django) - no UI
- **fullstack_monolith**: Single codebase with both frontend and backend
- **fullstack_separated**: Separate frontend and backend projects
- **microservices**: Multiple independent services
- **serverless**: Cloud functions based architecture
- **mobile**: Mobile application (React Native, Flutter)
- **desktop**: Desktop application (Electron, Tauri)

### Step 3: Design Folder Structure
Create a COMPLETE folder structure with ALL necessary files. Consider:
- Source code organization
- Configuration files
- Test files
- Documentation
- CI/CD files
- Docker/deployment files
- Database migrations
- Static assets

### Step 4: Define All Required Files
List EVERY file needed for a production-ready application:
- Entry points
- Components/modules
- Services/utils
- Types/interfaces
- Config files
- Environment files
- Documentation
- Tests

### Step 5: Technology Stack
Choose appropriate technologies:
- Programming language(s)
- Frameworks
- Databases
- Caching
- Message queues
- Authentication
- Deployment platform

## Response Format

You MUST respond with valid JSON:

```json
{
    "analysis": {
        "problem_summary": "Clear summary of what needs to be built",
        "problem_type": "web_app|api|cli|mobile|desktop|library|microservices",
        "complexity": "simple|moderate|complex|enterprise",
        "estimated_files": 25,
        "estimated_development_time": "2 weeks",
        "key_challenges": ["challenge1", "challenge2"]
    },
    "architecture": {
        "project_type": "fullstack_monolith|fullstack_separated|frontend_only|backend_only|microservices",
        "pattern": "MVC|Clean Architecture|Hexagonal|Microservices|Serverless",
        "description": "Detailed architecture description"
    },
    "tech_stack": {
        "frontend": {
            "framework": "Next.js 14|React|Vue|Angular|None",
            "language": "TypeScript|JavaScript",
            "styling": "Tailwind CSS|CSS Modules|Styled Components",
            "state_management": "React Context|Redux|Zustand|None"
        },
        "backend": {
            "framework": "FastAPI|Express|Django|NestJS|None",
            "language": "Python|TypeScript|Go|Java",
            "api_style": "REST|GraphQL|gRPC"
        },
        "database": {
            "primary": "PostgreSQL|MongoDB|MySQL|SQLite|None",
            "orm": "Prisma|TypeORM|SQLAlchemy|Mongoose",
            "caching": "Redis|Memcached|None"
        },
        "infrastructure": {
            "containerization": "Docker|None",
            "orchestration": "Docker Compose|Kubernetes|None",
            "ci_cd": "GitHub Actions|GitLab CI|None"
        }
    },
    "folder_structure": {
        "root": "project-name",
        "directories": [
            {
                "path": "src",
                "purpose": "Source code",
                "subdirectories": [
                    {"path": "src/components", "purpose": "React components"},
                    {"path": "src/services", "purpose": "Business logic"}
                ]
            }
        ]
    },
    "files": [
        {
            "filepath": "package.json",
            "filename": "package.json",
            "purpose": "Project dependencies and scripts",
            "language": "json",
            "priority": 1,
            "dependencies": [],
            "category": "config"
        },
        {
            "filepath": "src/app/page.tsx",
            "filename": "page.tsx",
            "purpose": "Main page component",
            "language": "typescript",
            "priority": 2,
            "dependencies": ["package.json", "src/app/layout.tsx"],
            "category": "frontend"
        }
    ],
    "database_schema": {
        "entities": [
            {
                "name": "User",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": true},
                    {"name": "email", "type": "string", "unique": true},
                    {"name": "password", "type": "string", "hashed": true}
                ],
                "relationships": []
            }
        ]
    },
    "api_design": {
        "base_url": "/api/v1",
        "endpoints": [
            {
                "method": "GET",
                "path": "/users",
                "description": "List all users",
                "auth_required": true,
                "request_body": null,
                "response": {"type": "array", "items": "User"}
            }
        ]
    },
    "features": [
        {
            "id": "f1",
            "name": "User Authentication",
            "description": "Complete auth system with login, register, forgot password",
            "priority": "high",
            "files_involved": ["src/auth/*", "src/api/auth/*"]
        }
    ],
    "deployment": {
        "recommended_platform": "Vercel|AWS|GCP|Azure|DigitalOcean",
        "environment_variables": [
            {"name": "DATABASE_URL", "description": "Database connection string", "required": true},
            {"name": "JWT_SECRET", "description": "JWT signing secret", "required": true}
        ]
    }
}
```

## Guidelines

1. **Be Comprehensive**: Include ALL files needed for production
2. **Be Specific**: Don't use placeholders like "etc." - list everything
3. **Be Practical**: Choose technologies that work well together
4. **Be Scalable**: Design for growth but don't over-engineer
5. **Be Modern**: Use current best practices and frameworks
6. **Be Complete**: Include tests, docs, CI/CD, Docker files

For complex projects, you may need 50-100+ files. That's expected for enterprise applications.
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
                    "database": {"primary": "PostgreSQL", "orm": "Prisma"}
                },
                "files": [],
                "parse_error": str(e)
            }
            default_arch["files"] = self._generate_default_files(default_arch)
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
        
        # Prisma schema if using PostgreSQL
        if database.get("orm") == "Prisma" or database.get("primary") == "PostgreSQL":
            files.append({
                "filepath": "prisma/schema.prisma",
                "filename": "schema.prisma",
                "purpose": "Database schema with all models and relationships",
                "language": "prisma",
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
            ("lib/db.ts", "db.ts", "Database connection and Prisma client"),
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

## Response Format

```json
{
    "total_files": 45,
    "files_by_category": {
        "config": 8,
        "frontend": 15,
        "backend": 10,
        "shared": 5,
        "test": 5,
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

Be thorough - missing files will cause the project to fail!
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

