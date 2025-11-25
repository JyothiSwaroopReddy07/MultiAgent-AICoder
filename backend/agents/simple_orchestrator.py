"""
Simple Orchestrator - Fast code generation with minimal agents
Only essential agents for rapid Next.js full-stack development
"""
from typing import Dict, Any, AsyncGenerator
import structlog
from datetime import datetime, timezone
import uuid

from agents.phase1_discovery.requirements_analyst_agent import RequirementsAnalystAgent
from agents.phase1_discovery.tech_stack_decision_agent import TechStackDecisionAgent
from agents.phase2_design.database_designer_agent import DatabaseDesignerAgent
from agents.phase3_implementation.nextjs_coder_agent import NextJSCoderAgent
from agents.phase3_implementation.docker_generator_agent import DockerGeneratorAgent
from mcp.server import MCPServer
from utils.openai_client import OpenAIClient

logger = structlog.get_logger()


class SimpleOrchestrator:
    """
    Simplified orchestrator with only 5 essential agents:
    1. Requirements Analyst - Understand what to build
    2. Tech Stack Decision - Choose technologies
    3. Database Designer - Design schema
    4. Code Generator - Generate all Next.js code
    5. Docker Generator - Create deployment files
    """
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai = openai_client
        self.mcp = MCPServer()
        
        logger.info("initializing_simple_orchestrator")
        
        # Initialize only essential agents
        self.requirements_analyst = RequirementsAnalystAgent(self.mcp, self.openai)
        self.tech_stack_agent = TechStackDecisionAgent(self.mcp, self.openai)
        self.database_designer = DatabaseDesignerAgent(self.mcp, self.openai)
        self.coder = NextJSCoderAgent(self.mcp, self.openai)
        self.docker_generator = DockerGeneratorAgent(self.mcp, self.openai)
        
        logger.info("simple_orchestrator_initialized", agents=5)
    
    async def generate_with_streaming(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate code with streaming - simplified 3-phase workflow:
        Phase 1: Analysis (Requirements + Tech Stack)
        Phase 2: Design (Database Schema)
        Phase 3: Implementation (Code + Docker)
        """
        request_id = str(uuid.uuid4())
        
        try:
            yield {
                'type': 'started',
                'request_id': request_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # ============================================================
            # PHASE 1: ANALYSIS (Fast requirements + tech stack)
            # ============================================================
            yield {'type': 'phase_started', 'phase': '📋 Phase 1: Analysis'}
            
            # Step 1: Quick requirements analysis
            yield {'type': 'agent_started', 'agent': 'Requirements Analyst', 'activity': 'Analyzing requirements...'}
            req_result = await self.requirements_analyst.process_task(request_data)
            requirements = req_result["requirements"]
            yield {'type': 'agent_completed', 'agent': 'Requirements Analyst'}
            
            # Step 2: Tech stack decision
            yield {'type': 'agent_started', 'agent': 'Tech Stack', 'activity': 'Selecting technologies...'}
            tech_result = await self.tech_stack_agent.process_task({
                **request_data,
                "requirements": requirements
            })
            tech_stack = tech_result.get('tech_stack', {})
            yield {'type': 'agent_completed', 'agent': 'Tech Stack'}
            
            # ============================================================
            # PHASE 2: DESIGN (Database only)
            # ============================================================
            yield {'type': 'phase_started', 'phase': '🎨 Phase 2: Database Design'}
            
            yield {'type': 'agent_started', 'agent': 'Database Designer', 'activity': 'Designing database schema...'}
            db_result = await self.database_designer.process_task({
                "requirements": requirements,
                "database_preference": request_data.get("database", "auto"),
                "description": request_data.get("description", "")
            })
            database_schema = db_result.get("database_schema", {})
            yield {'type': 'agent_completed', 'agent': 'Database Designer'}
            
            # ============================================================
            # PHASE 3: IMPLEMENTATION (All code at once)
            # ============================================================
            yield {'type': 'phase_started', 'phase': '⚡ Phase 3: Code Generation'}
            
            # Step 1: Generate all Next.js code
            yield {'type': 'agent_started', 'agent': 'Code Generator', 'activity': 'Generating Next.js application...'}
            code_result = await self.coder.process_task({
                **request_data,
                "requirements": requirements,
                "tech_stack": tech_stack,
                "database_schema": database_schema
            })
            
            # Stream each generated file
            code_files = code_result.get("code_files", [])
            for file in code_files:
                yield {
                    'type': 'file_generated',
                    'file': {
                        'filename': file.get('filename'),
                        'filepath': file.get('filepath'),
                        'language': file.get('language'),
                        'content': file.get('content')
                    }
                }
            
            yield {'type': 'agent_completed', 'agent': 'Code Generator', 'data': {'file_count': len(code_files)}}
            
            # Step 2: Generate Docker configuration
            yield {'type': 'agent_started', 'agent': 'Docker Generator', 'activity': 'Creating deployment files...'}
            docker_result = await self.docker_generator.process_task({
                "database_schema": database_schema,
                "code_files": code_files,
                "description": request_data.get("description", "")
            })
            
            # Stream Docker files
            for file in docker_result.get("docker_files", []):
                yield {
                    'type': 'file_generated',
                    'file': {
                        'filename': file.get('filename'),
                        'filepath': file.get('filepath'),
                        'language': file.get('language'),
                        'content': file.get('content')
                    }
                }
            
            yield {'type': 'agent_completed', 'agent': 'Docker Generator'}
            
            # ============================================================
            # COMPLETION
            # ============================================================
            all_files = code_files + docker_result.get("docker_files", [])
            
            yield {
                'type': 'completed',
                'data': {
                    'code_files': all_files,
                    'file_structure': self._build_file_structure(all_files),
                    'setup_instructions': self._generate_setup_instructions(database_schema),
                    'total_files': len(all_files)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "code_generation_completed",
                request_id=request_id,
                total_files=len(all_files)
            )
            
        except Exception as e:
            logger.error("code_generation_failed", error=str(e), request_id=request_id)
            yield {
                'type': 'error',
                'error': str(e),
                'request_id': request_id
            }
    
    def _build_file_structure(self, files: list) -> Dict[str, list]:
        """Build file structure tree"""
        structure = {}
        for file in files:
            filepath = file.get('filepath', '')
            parts = filepath.split('/')
            if len(parts) > 1:
                folder = '/'.join(parts[:-1])
                if folder not in structure:
                    structure[folder] = []
                structure[folder].append(parts[-1])
        return structure
    
    def _generate_setup_instructions(self, database_schema: Dict[str, Any]) -> list:
        """Generate setup instructions"""
        db_type = database_schema.get('database_type', 'postgresql')
        
        instructions = [
            "# Setup Instructions",
            "",
            "## 1. Install Dependencies",
            "```bash",
            "npm install",
            "```",
            "",
            "## 2. Configure Environment",
            "Create a `.env.local` file:",
            "```",
            "DATABASE_URL=your_database_url",
            "NEXTAUTH_SECRET=your_secret_key",
            "NEXTAUTH_URL=http://localhost:3000",
            "```",
            "",
            "## 3. Setup Database",
        ]
        
        if db_type == 'postgresql':
            instructions.extend([
                "```bash",
                "# Run migrations",
                "npx prisma migrate dev",
                "```"
            ])
        elif db_type == 'mongodb':
            instructions.extend([
                "```bash",
                "# No migrations needed for MongoDB",
                "# Just ensure your MongoDB instance is running",
                "```"
            ])
        
        instructions.extend([
            "",
            "## 4. Run Development Server",
            "```bash",
            "npm run dev",
            "```",
            "",
            "## 5. Build for Production",
            "```bash",
            "npm run build",
            "npm start",
            "```",
            "",
            "## 6. Deploy with Docker",
            "```bash",
            "docker-compose up -d",
            "```"
        ])
        
        return instructions

