# Multi-Agent System with MCP Integration

## Overview

This is a Multi-Agent AI Code Generator that uses the Model Context Protocol (MCP) for coordinated code generation. The system generates executable code AND corresponding test cases based on user requirements.

## Demo Use Case: Symptom Tracker Application

A software application that allows users to track and monitor their symptoms over time, enabling them to identify patterns and potential triggers.

### Features:
- User Authentication
- Symptom Logging with Severity (1-10)
- Associated Factors Tracking (food, stress, sleep, weather, medications)
- Pattern Analysis with Charts
- Trigger Detection
- Symptom History & Search
- Data Export (CSV/PDF)
- Reminders
- Dashboard with Insights

## Multi-Agent Architecture

### Agent Pipeline

```
User Input → FeaturePlanner → Architect → FilePlanner → CodeGenerator → Validator → TestGenerator → Execution
                 ↓                ↓            ↓              ↓             ↓            ↓
              Features      Architecture   File Plan     Code Files    Validation   Test Files
```

### Agents

| Agent | Role | Phase | Description |
|-------|------|-------|-------------|
| **FeaturePlannerAgent** | 💡 Feature Planner | Planning | Analyzes requirements and proposes features for user confirmation |
| **ArchitectAgent** | 🏗️ Architect | Discovery | Designs system architecture, tech stack, and database schema |
| **FilePlannerAgent** | 📋 File Planner | Design | Plans all files needed with dependencies |
| **CodeGeneratorAgent** | ⚙️ Code Generator | Implementation | Generates production-ready code files |
| **IntegrationValidatorAgent** | 🔍 Validator | Validation | Validates imports, types, and integration |
| **TestGeneratorAgent** | 🧪 Test Generator | Testing | Generates unit tests for each code file |
| **ExecutionAgent** | 🚀 Execution | Execution | Executes code and auto-fixes errors |

### MCP Integration

Agents communicate via the Model Context Protocol:
- **Coordinated Generation**: Agents pass context to each other
- **File Dependencies**: Code generator knows about all generated files
- **Test Awareness**: Test generator receives generated code for analysis
- **Error Feedback**: Execution agent can trigger fixes

## LLM Usage Tracking

The system comprehensively tracks LLM usage:

### Tracked Metrics
- **Total API Calls**: Number of LLM invocations
- **Total Tokens**: Combined prompt + completion tokens
- **Estimated Cost**: Based on model pricing
- **Per-Agent Breakdown**: Usage statistics per agent

### API Endpoints
- `GET /api/v1/usage` - Get usage summary
- `GET /api/v1/usage/detailed` - Get detailed breakdown by agent
- `POST /api/v1/usage/reset` - Reset usage statistics
- `GET /api/v1/agents` - Get agent info with usage stats

## User Interface

### Input
1. **Description Input**: User enters software requirements
2. **Preset Button**: "Try: Symptom Tracker App" loads demo use case
3. **Feature Confirmation**: User reviews and approves proposed features

### Output
1. **Executable Code**: Complete application files
2. **Test Cases**: Jest/React Testing Library tests
3. **Live Preview**: Execute and preview the application
4. **Download**: Download source code as ZIP

### Tabs
- **Editor**: Monaco code editor with file tree
- **Live Preview**: Embedded iframe showing running app
- **Console**: Execution logs and error messages
- **Agents**: Agent pipeline visualization with usage stats

## Running the System

### Start Backend
```bash
cd backend
pip install -r requirements.txt
python main_enhanced.py
```

### Start Frontend
```bash
cd frontend
npm install
npm start
```

### Using Docker
```bash
docker-compose up
```

## API Endpoints

### Chat
- `POST /api/chat/message` - Send message (streaming SSE response)
- `GET /api/chat/health` - Health check

### Generation
- `POST /api/v1/generate` - Direct generation (non-streaming)
- `GET /api/v1/preset/symptom-tracker` - Get symptom tracker preset

### Execution
- `POST /api/execute` - Execute generated application
- `POST /api/execute/stop` - Stop running application
- `GET /api/execute/running` - List running applications

### Download
- `POST /api/download` - Download project as ZIP

## Generated Files

### Application Code
- Configuration files (package.json, tsconfig.json, etc.)
- Database schema (SQL files, connection pool)
- API routes (Next.js API routes)
- React components (Pages, Forms, Lists, Cards)
- Custom hooks (Data fetching, CRUD operations)
- Utilities (helpers, validators)
- Docker files (Dockerfile, docker-compose.yml)

### Test Files
- **Unit Tests**: One test file per source file (utilities, hooks, components, API routes)
- **Test Config**: Jest configuration (jest.config.js, jest.setup.js)
- **Test Location**: All tests in `__tests__/` directory mirroring source structure

## Technology Stack

### Backend
- Python 3.11+
- FastAPI
- Gemini AI (LLM)
- Structlog (Logging)

### Frontend
- React 18
- TypeScript
- Monaco Editor
- Tailwind CSS

### Generated Projects
- Next.js 14
- TypeScript
- PostgreSQL (pg package)
- Tailwind CSS
- Jest + React Testing Library

