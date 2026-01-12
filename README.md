# AI Code Generator - Enterprise Multi-Agent Platform

An enterprise-grade AI code generation platform that uses multiple specialized agents to generate production-ready applications from natural language descriptions.

## Features

- **Dynamic Architecture Design** - AI determines optimal project structure based on requirements
- **Multi-Project Support** - Supports frontend, backend, fullstack, microservices, and more
- **Production-Ready Code** - Generates complete, working code with proper error handling
- **Context-Aware Generation** - Each file knows about types, utilities, and other files
- **Streaming Output** - Real-time file generation with progress tracking

## Agent Architecture

The platform uses 4 specialized agents working together:

| Agent | Role |
|-------|------|
| **ArchitectAgent** | Analyzes requirements, designs architecture, chooses tech stack |
| **FilePlannerAgent** | Plans all files needed based on project complexity |
| **CodeGeneratorAgent** | Generates production-ready code with full context |
| **IntegrationValidatorAgent** | Validates all files work together |

## Project Structure

```
ai-coder/
├── backend/
│   ├── agents/                 # AI Agents
│   │   ├── architect_agent.py  # Architecture design
│   │   ├── code_generator_agent.py  # Code generation
│   │   └── base_agent.py       # Base agent class
│   ├── models/                 # Data schemas
│   ├── utils/                  # Utilities (Gemini client, etc.)
│   ├── mcp/                    # Message routing
│   ├── config.py               # Configuration
│   └── main_enhanced.py        # FastAPI server
├── frontend/
│   └── src/
│       └── ChatApp.tsx         # React chat interface
├── docker-compose.yml          # Docker configuration
└── start.sh                    # Startup script
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API key

### 1. Set up environment

```bash
# Clone the repository
git clone <repo-url>
cd ai-coder

# Set your Gemini API key
export GEMINI_API_KEY='your-api-key-here'
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
python main_enhanced.py
```

The server will start at http://localhost:8000

### 3. Start the frontend (optional)

```bash
cd frontend
npm install
npm start
```

The UI will be available at http://localhost:3000

## API Usage

### Generate Code

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Build a todo app with user authentication"}'
```

### Health Check

```bash
curl http://localhost:8000/api/chat/health
```

## Example Requests

### Simple App
```
"Create a calculator app"
```
→ Generates ~15 files

### Complex Enterprise App
```
"Build an e-commerce platform with user auth, product catalog, 
shopping cart, Stripe checkout, admin dashboard, and reviews"
```
→ Generates 30-50+ files

### Backend API
```
"Build a REST API for a blog with posts, comments, and users. 
Use FastAPI and PostgreSQL."
```
→ Generates Python backend with proper structure

## Technology Stack

- **Backend**: Python, FastAPI, Gemini AI
- **Frontend**: React, TypeScript, Tailwind CSS
- **AI**: Google Gemini 2.5 Flash
- **Infrastructure**: Docker, Nginx

## Generated Output

The platform generates:

- ✅ Configuration files (package.json, tsconfig, etc.)
- ✅ Database schemas (Prisma, TypeORM, etc.)
- ✅ Type definitions
- ✅ UI components
- ✅ API routes
- ✅ Middleware
- ✅ Docker files
- ✅ Documentation

## Configuration

Edit `backend/config.py` to customize:

```python
gemini_api_key = "your-api-key"
gemini_model = "gemini-2.5-flash"
backend_port = 8000
```

## License

MIT License

---

Built with ❤️ using Google Gemini AI
