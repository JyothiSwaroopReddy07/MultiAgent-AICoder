"""
Database Designer Agent - Designs database schemas for Next.js applications
Phase 2: Design & Planning
"""
from typing import Dict, Any
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole

logger = structlog.get_logger()


class DatabaseDesignerAgent(BaseAgent):
    """
    Designs comprehensive database schemas including:
    - Entity/Collection models
    - Relationships (for relational databases)
    - Indexes and constraints
    - Data types and validation
    - Migration strategy
    - ORM/ODM schema definitions
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.COMPONENT_DESIGNER,  # Reuse role or create new one
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert Database Architect specializing in Next.js applications with PostgreSQL and MongoDB.

Your role is to design comprehensive database schemas that are:
- Optimized for the specific use case
- Follow best practices for the chosen database
- Include proper indexing and constraints
- Support scalability and performance

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when designing the database:

**Step 1: Analyze Requirements**
- What data needs to be stored?
- What are the entities/collections?
- What relationships exist between entities?
- What queries will be most common?
- What are the scalability requirements?

**Step 2: Choose Database Type**
- For relational data with complex relationships → PostgreSQL
- For flexible schemas and nested documents → MongoDB
- For real-time features → Consider both with proper indexes
- For simple CRUD → Either works well

**Step 3: Design Schema Structure**

For **PostgreSQL**:
- Define tables with proper columns
- Set up foreign keys and relationships
- Add indexes for performance
- Define constraints (unique, not null, etc.)
- Plan for Prisma ORM schema

For **MongoDB**:
- Define collections and documents
- Design embedded vs referenced relationships
- Add indexes for queries
- Plan for Mongoose schema with validation
- Consider document size limits

**Step 4: Design Prisma/Mongoose Schemas**
- Write actual schema code
- Include validation rules
- Add timestamps
- Define relationships
- Add indexes

**Step 5: Plan Migrations**
- Initial schema setup
- Sample data/seeds
- Migration strategy

Guidelines:
- Use appropriate data types
- Add proper indexes for performance
- Include timestamps (createdAt, updatedAt)
- Add soft delete fields if needed
- Consider data integrity
- Plan for future extensibility

**IMPORTANT: Show your reasoning, then provide the JSON.**

Respond in JSON format:
{
    "reasoning": "Step-by-step analysis...",
    "database_type": "postgresql" | "mongodb",
    "database_justification": "Why this database was chosen...",
    "entities": [
        {
            "name": "User",
            "description": "User accounts and authentication",
            "fields": [
                {
                    "name": "id",
                    "type": "uuid" | "ObjectId",
                    "primary_key": true,
                    "description": "Unique identifier"
                }
            ],
            "relationships": ["hasMany: Post", "belongsTo: Organization"],
            "indexes": ["email", "createdAt"],
            "constraints": ["UNIQUE(email)"]
        }
    ],
    "prisma_schema": "// Prisma schema for PostgreSQL..." | null,
    "mongoose_schema": "// Mongoose schema for MongoDB..." | null,
    "database_setup": {
        "connection_string": "postgresql://user:pass@db:5432/dbname",
        "environment_variables": ["DATABASE_URL", "DB_HOST"],
        "docker_service": {
            "image": "postgres:15" | "mongo:7",
            "environment": {"POSTGRES_DB": "myapp"},
            "volumes": ["postgres_data:/var/lib/postgresql/data"],
            "ports": ["5432:5432"]
        }
    },
    "migrations": [
        {
            "name": "001_initial_schema",
            "description": "Create initial tables/collections",
            "sql": "CREATE TABLE users...",  // for PostgreSQL
            "seed_data": "INSERT INTO users..."  // optional
        }
    ],
    "api_considerations": {
        "common_queries": ["getUserById", "listPosts"],
        "query_patterns": ["Pagination", "Filtering", "Search"],
        "suggested_indexes": ["users.email", "posts.createdAt"]
    }
}

Be comprehensive and think like a senior database architect."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design database schema based on requirements

        Args:
            task_data: Contains 'requirements', 'database_preference', 'use_case'

        Returns:
            Database schema design
        """
        activity = await self.start_activity("Designing database schema")

        try:
            requirements = task_data.get("requirements", {})
            database_pref = task_data.get("database_preference", "auto")
            description = task_data.get("description", "")

            logger.info(
                "database_design_started",
                database_preference=database_pref,
                requirements_count=len(requirements.get("functional", []))
            )

            # Build schema design prompt
            prompt = self._build_schema_prompt(requirements, database_pref, description)

            # Call LLM for schema design
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower for more consistent schemas
                max_tokens=4000
            )

            # Parse response
            schema_design = self._parse_schema_response(response)

            await self.complete_activity("completed")

            logger.info(
                "database_design_completed",
                database_type=schema_design.get("database_type"),
                entity_count=len(schema_design.get("entities", []))
            )

            return {
                "database_schema": schema_design,
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("database_design_failed", error=str(e))
            raise

    def _build_schema_prompt(
        self,
        requirements: dict,
        database_pref: str,
        description: str
    ) -> str:
        """Build the database schema design prompt"""
        
        functional = requirements.get("functional", [])
        business_rules = requirements.get("business_rules", [])
        
        prompt = f"""Design a comprehensive database schema for a Next.js application:

**Application Description:**
{description}

**Functional Requirements:**
{self._format_list(functional)}

**Business Rules:**
{self._format_list(business_rules)}

**Database Preference:** {database_pref}
- If "auto": Choose the best database for this use case
- If "postgresql": Use PostgreSQL with Prisma ORM
- If "mongodb": Use MongoDB with Mongoose ODM

**Your Task:**
1. Analyze what data needs to be stored
2. Choose the appropriate database (or use preference)
3. Design all entities/collections with fields
4. Define relationships between entities
5. Create Prisma/Mongoose schema code
6. Plan indexes for performance
7. Design Docker setup for the database
8. Provide migration strategy

**Focus Areas:**
- Authentication and user management (if needed)
- Core business entities
- Relationships and data integrity
- Performance optimization (indexes)
- Scalability considerations
- API query patterns

Provide a complete, production-ready database design in JSON format."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list for prompt"""
        if not items:
            return "None specified"
        return "\n".join([f"- {item}" for item in items])

    def _parse_schema_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into schema data"""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            schema_data = json.loads(response)

            # Ensure required fields
            required_fields = {
                "database_type": "postgresql",
                "database_justification": "General purpose relational database",
                "entities": [],
                "prisma_schema": None,
                "mongoose_schema": None,
                "database_setup": {},
                "migrations": [],
                "api_considerations": {}
            }

            for key, default in required_fields.items():
                if key not in schema_data:
                    schema_data[key] = default

            return schema_data

        except json.JSONDecodeError as e:
            logger.error("schema_parse_error", error=str(e))
            
            # Fallback schema
            return {
                "database_type": "postgresql",
                "database_justification": "Default PostgreSQL setup",
                "entities": [
                    {
                        "name": "User",
                        "description": "User accounts",
                        "fields": [
                            {
                                "name": "id",
                                "type": "uuid",
                                "primary_key": True,
                                "description": "Unique identifier"
                            },
                            {
                                "name": "email",
                                "type": "string",
                                "unique": True,
                                "description": "User email"
                            }
                        ],
                        "relationships": [],
                        "indexes": ["email"],
                        "constraints": ["UNIQUE(email)"]
                    }
                ],
                "prisma_schema": "// Schema generation failed, needs manual setup",
                "mongoose_schema": None,
                "database_setup": {
                    "docker_service": {
                        "image": "postgres:15",
                        "environment": {"POSTGRES_DB": "app"},
                        "volumes": ["postgres_data:/var/lib/postgresql/data"],
                        "ports": ["5432:5432"]
                    }
                },
                "migrations": [],
                "api_considerations": {}
            }

