"""
Docker Generator Agent - Creates Docker and docker-compose configuration
Phase 3: Implementation
"""
from typing import Dict, Any
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole

logger = structlog.get_logger()


class DockerGeneratorAgent(BaseAgent):
    """
    Generates Docker configuration files including:
    - Dockerfile for Next.js application
    - docker-compose.yml for all services
    - .dockerignore for optimization
    - Environment configuration
    - Multi-stage builds for production
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.CODER,  # Reuse role
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert DevOps Engineer specializing in Docker containerization for Next.js applications.

Your role is to create production-ready Docker configurations that are:
- Optimized for Next.js 14 with App Router
- Multi-stage builds for smaller images
- Properly configured for development and production
- Include all necessary services (app, database, etc.)
- Follow Docker best practices

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step:

**Step 1: Analyze Application Requirements**
- What services are needed? (Next.js app, database, Redis, etc.)
- What is the database type? (PostgreSQL, MongoDB)
- What dependencies exist?
- What ports need to be exposed?
- What environment variables are required?

**Step 2: Design Dockerfile**
- Use multi-stage build (deps, builder, runner)
- Base image: node:18-alpine (lightweight)
- Install only production dependencies in final stage
- Optimize layer caching
- Set up proper user permissions
- Configure Next.js for production

**Step 3: Design docker-compose.yml**
- Define all services (app, database, etc.)
- Set up networking between services
- Configure volumes for data persistence
- Set environment variables
- Configure health checks
- Set restart policies

**Step 4: Additional Configuration**
- Create .dockerignore for build optimization
- Create .env.example for environment variables
- Add docker-compose.dev.yml for development
- Include helpful scripts (build, run, stop)

Guidelines:
- Use Alpine Linux for smaller images
- Leverage Docker layer caching
- Run as non-root user
- Use health checks
- Set resource limits
- Include restart policies
- Use named volumes for data persistence
- Separate development and production configs

**IMPORTANT: Show your reasoning, then provide the JSON with complete file contents.**

Respond in JSON format:
{
    "reasoning": "Step-by-step analysis...",
    "docker_files": [
        {
            "filename": "Dockerfile",
            "filepath": "Dockerfile",
            "content": "# Multi-stage Dockerfile content...",
            "description": "Production-optimized Next.js Dockerfile",
            "language": "dockerfile"
        },
        {
            "filename": "docker-compose.yml",
            "filepath": "docker-compose.yml",
            "content": "version: '3.8'\\nservices:...",
            "description": "Docker Compose configuration",
            "language": "yaml"
        },
        {
            "filename": ".dockerignore",
            "filepath": ".dockerignore",
            "content": "node_modules\\n.next\\n...",
            "description": "Docker ignore patterns",
            "language": "text"
        },
        {
            "filename": ".env.example",
            "filepath": ".env.example",
            "content": "DATABASE_URL=...",
            "description": "Environment variables template",
            "language": "shell"
        },
        {
            "filename": "docker-compose.dev.yml",
            "filepath": "docker-compose.dev.yml",
            "content": "version: '3.8'...",
            "description": "Development Docker Compose",
            "language": "yaml"
        }
    ],
    "services": {
        "app": {
            "name": "nextjs-app",
            "image": "app:latest",
            "ports": ["3000:3000"],
            "environment": ["NODE_ENV=production"],
            "depends_on": ["database"]
        },
        "database": {
            "name": "postgres" | "mongodb",
            "image": "postgres:15-alpine" | "mongo:7-alpine",
            "ports": ["5432:5432"] | ["27017:27017"],
            "volumes": ["db_data:/var/lib/postgresql/data"],
            "environment": {"POSTGRES_DB": "myapp"}
        }
    },
    "deployment_instructions": {
        "development": "docker-compose -f docker-compose.dev.yml up",
        "production": "docker-compose up -d",
        "build": "docker-compose build",
        "stop": "docker-compose down",
        "logs": "docker-compose logs -f"
    },
    "dockerfile_features": [
        "Multi-stage build for optimization",
        "Layer caching for faster builds",
        "Non-root user for security",
        "Production dependencies only",
        "Next.js standalone output"
    ]
}

Be comprehensive and production-ready."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Docker configuration files

        Args:
            task_data: Contains 'database_schema', 'code_files', 'description'

        Returns:
            Docker configuration files
        """
        activity = await self.start_activity("Generating Docker configuration")

        try:
            database_schema = task_data.get("database_schema", {})
            description = task_data.get("description", "")
            code_files = task_data.get("code_files", [])

            logger.info("docker_generation_started", database_type=database_schema.get("database_type"))

            # Build Docker generation prompt
            prompt = self._build_docker_prompt(database_schema, description, code_files)

            # Call LLM
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Low temperature for consistent configs
                max_tokens=4000
            )

            # Parse response
            docker_config = self._parse_docker_response(response)

            await self.complete_activity("completed")

            logger.info(
                "docker_generation_completed",
                file_count=len(docker_config.get("docker_files", []))
            )

            return {
                "docker_files": docker_config.get("docker_files", []),
                "services": docker_config.get("services", {}),
                "deployment_instructions": docker_config.get("deployment_instructions", {}),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("docker_generation_failed", error=str(e))
            raise

    def _build_docker_prompt(
        self,
        database_schema: dict,
        description: str,
        code_files: list
    ) -> str:
        """Build the Docker generation prompt"""
        
        database_type = database_schema.get("database_type", "postgresql")
        entities = database_schema.get("entities", [])
        
        prompt = f"""Generate complete Docker configuration for a Next.js 14 application:

**Application Description:**
{description}

**Database:**
- Type: {database_type}
- Entities: {len(entities)} models

**Requirements:**
1. **Dockerfile** - Multi-stage build for Next.js 14
   - Stage 1: Install dependencies
   - Stage 2: Build application
   - Stage 3: Production runtime (minimal)
   - Use node:18-alpine
   - Run as non-root user
   - Optimize for Next.js standalone output

2. **docker-compose.yml** - Production configuration
   - Next.js app service
   - {database_type.capitalize()} database service
   - Proper networking
   - Health checks
   - Restart policies
   - Named volumes for data persistence
   - Environment variables

3. **docker-compose.dev.yml** - Development configuration
   - Hot reload enabled
   - Volume mounts for code
   - Development database
   - Easier debugging

4. **.dockerignore** - Optimize build
   - Exclude node_modules, .next, .git
   - Exclude test files
   - Exclude documentation

5. **.env.example** - Environment template
   - All required variables
   - Example values
   - Comments explaining each

**Docker Best Practices:**
- Use Alpine images for smaller size
- Leverage layer caching
- Multi-stage builds
- Health checks for all services
- Named volumes (not anonymous)
- Proper restart policies
- Resource limits
- Security (non-root user)

Generate complete, production-ready Docker configuration files."""

        return prompt

    def _parse_docker_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into Docker configuration"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            docker_data = json.loads(response)

            # Ensure required fields
            if "docker_files" not in docker_data:
                docker_data["docker_files"] = []
            if "services" not in docker_data:
                docker_data["services"] = {}
            if "deployment_instructions" not in docker_data:
                docker_data["deployment_instructions"] = {}

            return docker_data

        except json.JSONDecodeError as e:
            logger.error("docker_parse_error", error=str(e))
            
            # Fallback minimal Docker config
            return {
                "docker_files": [
                    {
                        "filename": "Dockerfile",
                        "filepath": "Dockerfile",
                        "content": self._get_default_dockerfile(),
                        "description": "Next.js Dockerfile",
                        "language": "dockerfile"
                    },
                    {
                        "filename": "docker-compose.yml",
                        "filepath": "docker-compose.yml",
                        "content": self._get_default_compose(),
                        "description": "Docker Compose configuration",
                        "language": "yaml"
                    }
                ],
                "services": {},
                "deployment_instructions": {
                    "development": "docker-compose up",
                    "production": "docker-compose up -d"
                }
            }

    def _get_default_dockerfile(self) -> str:
        """Get default Dockerfile content"""
        return """FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT 3000
CMD ["node", "server.js"]
"""

    def _get_default_compose(self) -> str:
        """Get default docker-compose content"""
        return """version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
"""

