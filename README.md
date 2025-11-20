# AI Next.js Full-Stack Generator 

An intelligent multi-agent system that generates complete, production-ready **Next.js 14 full-stack applications** from natural language descriptions. Features **15 specialized agents** working across **6 phases** with automatic **database design** and **Docker deployment**.

**Fixed Tech Stack:**
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend:** Next.js API Routes (REST)
- **Database:** PostgreSQL/MongoDB (auto-selected)
- **ORM/ODM:** Prisma (PostgreSQL) or Mongoose (MongoDB)
- **Deployment:** Docker + docker-compose
- **Testing:** Jest + React Testing Library

## Key Features

### Next.js Full-Stack Specialization 
- **No Language Choice** - Always generates Next.js 14 with TypeScript
- **Auto Database Design** - PostgreSQL or MongoDB selected based on use case
- **ORM/ODM Included** - Complete Prisma or Mongoose schemas generated
- **Docker Ready** - Multi-stage Dockerfile + docker-compose generated
- **Complete Project** - 30-40 production-ready files in one generation

### Core Capabilities
- **15 Specialized AI Agents** - Each expert in their domain
- **Chain of Thought Prompting** - Systematic reasoning for better outputs
- **Real-Time Streaming** - Watch code being generated live
- **Complete SDLC Coverage** - From requirements to deployment
- **Modern Stack** - Next.js 14 App Router, Server Components
- **Security Auditing** - OWASP Top 10 vulnerability scanning
- **LLM Usage Tracking** - Monitor API calls and costs

---

## Architecture

### The 15 Agents

#### **Phase 1: Discovery & Analysis** 
1. **Requirements Analyst** - Extracts functional/non-functional requirements, business rules, user stories
2. **Interactive Requirements Analyst** - Asks clarifying questions when confidence is low
3. **Research Agent** - Finds best practices for Next.js, database design, security considerations
4. **Tech Stack Decision Agent** - Confirms Next.js stack and selects database type

#### **Phase 2: Design & Planning** 
5. **Architect** - Creates High-Level Design (HLD) for Next.js architecture
6. **Database Designer** **NEW** - Designs complete database schema (PostgreSQL/MongoDB)
7. **Module Designer** - Plans Next.js module structure (App Router organization)
8. **Component Designer** - Creates Low-Level Design (LLD) for React components
9. **UI Designer** - Designs complete UI/UX with Tailwind CSS components

#### **Phase 3: Implementation** 
10. **Next.js Coder** **NEW** - Generates complete Next.js 14 application (30-40 files)
11. **Test Generator** - Creates Jest + React Testing Library tests
12. **Docker Generator** **NEW** - Generates Dockerfile, docker-compose, and deployment config

#### **Phase 4: Quality Assurance** 
13. **Security Auditor** - OWASP Top 10 vulnerability analysis with fixes
14. **Code Reviewer** - Reviews code quality, provides scores and approval

#### **Phase 5: Validation** 
15. **Executor** - Validates code execution and test results

#### **Phase 6: Monitoring** 
16. **Monitor** - Tracks agent health, success rates, response times

### Workflow

```

 User: "Build a blog platform with posts, comments, and likes" 
 Database: Auto-select (Recommended) 

 
 
 Phase 1: Discovery & Analysis 
 Requirements Analysis 
 Next.js Best Practices Research 
 Database Type Selection 
 
 
 
 Phase 2: Design & Planning 
 Next.js Architecture (HLD) 
 DATABASE SCHEMA DESIGN 
 - PostgreSQL selected 
 - User, Post, Comment, Like 
 - Prisma schema generated 
 - Relationships & indexes 
 App Router Module Structure 
 React Component Design (LLD) 
 Tailwind UI/UX Design 
 
 
 
 Phase 3: Implementation 
 NEXT.JS CODE GENERATION 
 - app/ directory (App Router) 
 - API Routes for all entities 
 - Server & Client Components 
 - Prisma integration 
 - TypeScript + Tailwind 
 Output: 25-35 files 
 Test Generation (Jest + RTL) 
 DOCKER CONFIGURATION 
 - Multi-stage Dockerfile 
 - docker-compose.yml 
 - .env.example 
 
 
 
 Phase 4: Quality Assurance 
 Security Audit (OWASP Top 10) 
 Code Review 
 
 
 
 Phase 5: Validation 
 Execution Check 
 
 
 
 Complete Next.js Project 
 30-40 Production-Ready Files 
 Next.js 14 App (Frontend + API) 
 Database Schema + Migrations 
 Docker Deployment Ready 
 Comprehensive Tests 
 Configuration Files 
 README with Instructions 
 
 Deploy: docker-compose up -d 
 
```

---

## Quick Start

### Prerequisites

- **Option 1: Docker (Recommended for Production)**
 - Docker 20.10+
 - Docker Compose 2.0+
 - 4GB+ RAM available

- **Option 2: Local Development**
 - Python 3.10+
 - Node.js 18+
 - Redis (optional, for distributed workers)

- **Required**
 - OpenAI API Key

### Installation

#### Docker Installation (Recommended)

1. **Clone the repository**
 ```bash
 cd ai-coder
 ```

2. **Set up environment variables**
 ```bash
 cp .env.example .env
 # Edit .env and add your OPENAI_API_KEY
 ```

3. **Install dependencies**
 ```bash
 # Backend
 cd backend
 pip install -r requirements.txt
 
 # Frontend
 cd ../frontend
 npm install
 ```

### Running the Application

#### Docker (Recommended)

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down

# Restart services
make restart
```

#### Local Development

```bash
# Using startup scripts
./start.sh # macOS/Linux
start.bat # Windows

# Or manually
cd backend && python main_enhanced.py
cd frontend && npm start
```

### Access Points

- **Frontend UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health/enhanced
- **Nginx Gateway**: http://localhost:80 (Docker only)
- **Redis Commander**: http://localhost:8081 (Docker with monitoring)

---

## Usage

### Web UI (Recommended)

1. **Open Browser:** http://localhost:3000
2. **Enter Description:**
 ```
 Build a blog platform with posts, comments, likes,
 user authentication, and markdown editor
 ```
3. **Select Database:** Auto-select (or choose PostgreSQL/MongoDB)
4. **Click "Generate Next.js App"**
5. **Watch Real-Time Generation** - See files being created live!
6. **Download All Files**

### API Request (Alternative)

```bash
curl -X POST "http://localhost:8500/api/v2/generate/stream" \
 -H "Content-Type: application/json" \
 -d '{
 "description": "Build a task management app with projects, tasks, and team collaboration",
 "database": "auto",
 "requirements": [
 "User authentication",
 "Project management",
 "Task assignment",
 "Real-time updates",
 "File attachments"
 ]
 }'
```

### Example 2: Interactive Mode (with Clarifications)

```bash
# Step 1: Start interactive generation
curl -X POST "http://localhost:8000/api/v2/generate/enhanced/interactive" \
 -H "Content-Type: application/json" \
 -d '{
 "description": "Build a social media platform",
 "language": "python"
 }'

# Response: System may ask clarifying questions
# {
# "status": "awaiting_clarifications",
# "clarification_request": {
# "questions": [
# {
# "question_id": "q1",
# "question": "How many concurrent users do you expect?",
# "question_type": "multiple_choice",
# "options": ["< 1,000", "1,000-10,000", "10,000-100,000", "> 100,000"]
# }
# ]
# }
# }

# Step 2: Submit answers
curl -X POST "http://localhost:8000/api/v2/generate/enhanced/{request_id}/clarifications" \
 -H "Content-Type: application/json" \
 -d '{
 "answers": [
 {"question_id": "q1", "answer": "10,000-100,000"}
 ]
 }'
```

### What You Get

For a **Blog Platform** request, you receive:

** Phase 1: Discovery**
- 15+ functional requirements
- 8+ non-functional requirements
- Next.js best practices research
- Database type selection (PostgreSQL/MongoDB)

** Phase 2: Design**
- Next.js App Router architecture
- **Complete Database Schema** ( New):
 - Entity models (User, Post, Comment, Like)
 - Relationships and foreign keys
 - Indexes for performance
 - Prisma schema or Mongoose models
- Component structure (Server & Client)
- Tailwind UI component library

** Phase 3: Implementation**
- **Next.js Application (25-35 files)**:
 ```
 app/
 api/ # API Routes
 auth/
 login/route.ts
 register/route.ts
 posts/
 route.ts # GET, POST
 [id]/route.ts # GET, PUT, DELETE
 comments/route.ts
 dashboard/page.tsx # Server Component
 posts/
 [id]/page.tsx
 layout.tsx # Root layout
 page.tsx # Home page

 components/
 ui/ # Reusable components
 Button.tsx
 Card.tsx
 forms/
 PostForm.tsx # Client Component

 lib/
 db.ts # Prisma/Mongoose setup

 prisma/ # For PostgreSQL
 schema.prisma # Complete schema

 models/ # For MongoDB
 User.ts
 Post.ts
 ```

- **Test Files (8-12 files)**:
 - API route tests (Jest)
 - Component tests (React Testing Library)
 - Integration tests

- **Docker Configuration (5 files)** ( New):
 - `Dockerfile` - Multi-stage build
 - `docker-compose.yml` - All services
 - `docker-compose.dev.yml` - Development
 - `.dockerignore` - Build optimization
 - `.env.example` - Environment template

- **Configuration Files**:
 - `package.json` - All dependencies
 - `next.config.js` - Next.js config
 - `tailwind.config.ts` - Tailwind setup
 - `tsconfig.json` - TypeScript config
 - `jest.config.js` - Test configuration

** Phase 4: Quality Assurance**
- Security audit report (OWASP Top 10)
- Code quality review with scores

** Phase 5: Validation**
- Execution validation results

** Total Output**
- **30-40 production-ready files**
- **Complete full-stack application**
- **Database schema + migrations**
- **Docker deployment ready**
- **Comprehensive test suite**

---

## Metrics

### Performance

| Metric | Value |
|--------|-------|
| **Total Time** | 6-10 minutes |
| **Token Usage** | ~40,000-50,000 tokens |
| **Cost (GPT-4)** | ~$0.60-1.00 per generation |
| **Agents Used** | 16 specialized agents |
| **Code Files** | 25-35 Next.js files |
| **Test Files** | 8-12 comprehensive tests |
| **Docker Files** | 5 deployment files |
| **Total Output** | **30-40 production-ready files** |

### Cost Breakdown

- Discovery & Analysis: ~$0.15
- Design & Planning (+ Database): ~$0.35
- Implementation (+ Docker): ~$0.30
- Quality Assurance: ~$0.12
- Validation: ~$0.04
- Monitoring: ~$0.02

### Quality Metrics

- Average Security Score: **8.0/10**
- Average Code Quality Score: **8.5/10**
- Average Test Coverage: **80%+**
- Agent Success Rate: **95%+**
- **Ready to Deploy**: **docker-compose up -d**

---

## Interactive Clarification Workflow

The system intelligently asks questions when it needs more information:

### How It Works

1. **Confidence Analysis**: System analyzes your description
2. **Question Generation**: If confidence < 0.7, generates targeted questions
3. **User Input**: You provide specific answers
4. **Informed Decisions**: Tech stack chosen based on YOUR requirements

### Question Categories

- **Scalability**: Expected users, load, growth
- **Availability**: Uptime requirements, downtime tolerance
- **Security**: Data sensitivity, compliance needs
- **Tech Stack**: Technology preferences
- **Constraints**: Budget, timeline, team size

### Benefits

 No assumptions about scale or requirements 
 Tech stack based on actual needs 
 Budget-aware architecture 
 Transparent decision-making with justifications 
 Right-sized solutions (no over-engineering)

---

## API Endpoints

### Enhanced Workflow (13 Agents)

```bash
# Generate code with full workflow
POST /api/v2/generate/enhanced

# Interactive mode with clarifications
POST /api/v2/generate/enhanced/interactive

# Check generation status
GET /api/v2/generate/enhanced/status/{request_id}

# Get clarification questions
GET /api/v2/generate/enhanced/{request_id}/clarifications

# Submit clarification answers
POST /api/v2/generate/enhanced/{request_id}/clarifications

# Get workflow phases
GET /api/v2/workflow/phases

# Get agent information
GET /api/v2/agents/enhanced

# Health check
GET /health/enhanced
```

### Basic Workflow (4 Agents - Original)

```bash
# Generate code with basic workflow
POST /api/v1/generate

# Check status
GET /api/v1/status/{request_id}
```

---

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
OPENAI_MODEL=gpt-4 # or gpt-3.5-turbo
TEMPERATURE=0.7 # 0.0-1.0
MAX_TOKENS=4000 # Per request
BACKEND_PORT=8000
FRONTEND_PORT=3000
DEBUG=true
LOG_LEVEL=INFO
```

### Agent Configuration

Each agent uses chain-of-thought prompting with customizable:
- Temperature (0.2-0.7 depending on task)
- Max tokens (2000-4000)
- System prompts (editable in agent files)

---

## Chain of Thought Prompting

All agents use systematic reasoning:

### Example: Requirements Analyst

```
Step 1: Read and Parse
- What is the user trying to build?
- What domain is this (e-commerce, social, SaaS)?

Step 2: Extract Functional Requirements
- What features/capabilities must the system have?
- What user actions need support?

Step 3: Identify Non-Functional Requirements
- Performance: Response times, throughput?
- Scalability: User load, data volume?
- Security: Data sensitivity, compliance?

... [continues systematically]

Result: Comprehensive, well-reasoned requirements
```

### Benefits

- **Better Quality**: More thorough analysis
- **Transparency**: See the reasoning process
- **Consistency**: Reliable decision-making
- **Easier Debugging**: Understand why decisions were made

---

## Project Structure

### Generator Codebase:
```
ai-coder/
 backend/
 agents/ # All 16 agents
 phase1_discovery/ # Requirements, Research, Tech Decision
 phase2_design/ # Architect, Database, Module, Component, UI
 database_designer_agent.py NEW
 ...
 phase3_implementation/ # Next.js Code, Tests, Docker
 nextjs_coder_agent.py NEW
 docker_generator_agent.py NEW
 phase4_qa/ # Security, Code Review
 phase5_validation/ # Executor
 phase6_monitoring/ # Monitor
 advanced_orchestrator.py # Coordinates all agents
 api/
 streaming_routes.py # Real-time streaming API
 enhanced_routes.py # Enhanced API routes
 models/
 enhanced_schemas.py # All schemas
 utils/
 llm_tracker.py # Token/cost tracking
 openai_client.py # OpenAI integration
 main_enhanced.py # Main server
 requirements.txt
 frontend/ # VS Code-like UI
 src/
 App.tsx # Main component (Monaco Editor)
 components/ # React components
 services/ # API services
 docs/ # Documentation
 README.md # This file
```

### Generated Next.js Project Structure:
```
my-generated-app/ # Your generated application
 app/ # Next.js App Router
 api/ # API Routes (Backend)
 auth/
 login/route.ts
 register/route.ts
 [resource]/
 route.ts # GET, POST
 [id]/route.ts # GET, PUT, DELETE
 (auth)/ # Route groups
 login/page.tsx
 register/page.tsx
 dashboard/
 page.tsx # Server Component
 layout.tsx # Root layout
 page.tsx # Home page

 components/ # React Components
 ui/ # Reusable UI (Tailwind)
 Button.tsx
 Input.tsx
 Card.tsx
 forms/ # Form components
 LoginForm.tsx # Client Component

 lib/ # Utilities
 db.ts # Database connection
 utils.ts # Helper functions

 prisma/ # PostgreSQL (if selected)
 schema.prisma # Complete schema

 models/ # MongoDB (if selected)
 User.ts # Mongoose models
 [Entity].ts

 __tests__/ # Tests
 api/ # API tests
 components/ # Component tests
 integration/ # Integration tests

 Dockerfile # Production Docker image
 docker-compose.yml # All services
 docker-compose.dev.yml # Development
 .dockerignore # Build optimization
 .env.example # Environment template

 package.json # Dependencies
 next.config.js # Next.js configuration
 tailwind.config.ts # Tailwind CSS
 tsconfig.json # TypeScript
 jest.config.js # Testing

 README.md # Setup instructions
```

---

## UI Designer Features

The UI Designer agent creates complete interface designs:

### Outputs

1. **Design System Selection**
 - Material-UI, Tailwind, Bootstrap, Chakra UI
 - Justification for choice

2. **Visual Design**
 - Color palette (primary, secondary, semantic)
 - Typography system
 - Spacing and layout

3. **Component Architecture**
 - Atomic design principles
 - Component props and state
 - Reusable component library

4. **Page/Screen Designs**
 - All pages needed
 - Layout for each page
 - Data requirements
 - User interactions

5. **Responsive Design**
 - Mobile-first approach
 - Breakpoint strategy
 - Touch-friendly design

6. **Accessibility**
 - WCAG 2.1 AA compliance
 - ARIA labels
 - Keyboard navigation
 - Color contrast

7. **User Flows**
 - Key user journeys
 - Interactive states
 - Error handling

---

## Security Features

### OWASP Top 10 Coverage

The Security Auditor checks for:

1. **Broken Access Control**
2. **Cryptographic Failures**
3. **Injection** (SQL, XSS, Command)
4. **Insecure Design**
5. **Security Misconfiguration**
6. **Vulnerable Components**
7. **Authentication Failures**
8. **Data Integrity Failures**
9. **Security Logging Failures**
10. **Server-Side Request Forgery**

### Audit Output

- Vulnerability list with severity
- Specific code locations
- Remediation steps
- Code fix examples
- Security score (0-10)

---

## Docker & Microservices

### Architecture

The application is fully dockerized with microservices architecture:

- **Nginx Gateway** - Load balancer and API gateway
- **Backend API** (Scalable) - FastAPI service handling requests
- **Agent Workers** (Scalable) - Celery workers processing agent tasks
- **Frontend** - React app served by Nginx
- **Redis** - Message queue and cache

### Scaling

```bash
# Scale agent workers (parallel processing)
make scale-workers N=10

# Scale backend API (handle more requests)
make scale-api N=5

# Check status
make status

# View health
make health
```

### Production Deployment

```bash
# Deploy with production configuration
make prod-up

# Deploy with zero-downtime rolling updates
make deploy

# Uses:
# - Multiple replicas for high availability
# - Resource limits and health checks
# - Optimized for production workloads
```

### Monitoring

```bash
# Start with monitoring tools
make monitor-up

# View logs
make logs-api # Backend API logs
make logs-worker # Agent worker logs
make logs-nginx # Nginx gateway logs

# Redis monitoring
open http://localhost:8081
```

See **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** for complete Docker documentation.

### Kubernetes with HPA (Production)

For true microservices with independent scaling per agent phase:

```bash
# Build all images
./build-images.sh your-registry.com/ai-coder

# Deploy to Kubernetes
./deploy-k8s.sh

# Each phase scales independently!
# Phase 1: 2-20 pods (Discovery)
# Phase 2: 3-25 pods (Design)
# Phase 3: 4-30 pods (Implementation - most intensive)
# Phase 4: 3-20 pods (QA)
# Phase 5: 2-15 pods (Validation)
# Phase 6: 1-5 pods (Monitoring)
```

**Benefits:**
- Each agent phase is a separate microservice
- Independent Horizontal Pod Autoscaling (HPA) per phase
- Scales based on CPU, memory, and queue length
- Resource limits per service
- Production-grade orchestration

See **[kubernetes/KUBERNETES_DEPLOYMENT.md](kubernetes/KUBERNETES_DEPLOYMENT.md)** for complete Kubernetes guide including:
- Microservices architecture
- HPA configuration per phase
- Monitoring and observability
- Production deployment
- Troubleshooting

---

## Use Cases

### Perfect For

 **Next.js Full-Stack Apps** - Complete frontend + backend 
 **MVPs & Prototypes** - Production-ready in minutes 
 **SaaS Applications** - Multi-tenant ready 
 **E-commerce Stores** - Products, cart, checkout 
 **Blogs & CMS** - Content management systems 
 **Social Platforms** - Posts, comments, likes 
 **Project Management** - Tasks, teams, workflows 
 **CRM Systems** - Contacts, deals, pipelines 
 **Admin Dashboards** - Data visualization 
 **Learning Projects** - See Next.js best practices 

### Example Projects You Can Generate

**1. Blog Platform**
```
"Build a blog with posts, comments, categories, tags,
markdown editor, and user authentication"
```
Output: 35+ files, PostgreSQL, Docker ready

**2. E-commerce Store**
```
"Create an online store with products, shopping cart,
checkout, orders, and payment integration structure"
```
Output: 40+ files, PostgreSQL with Prisma, complete checkout flow

**3. Task Management**
```
"Build a project management tool with teams, projects,
tasks, file attachments, and real-time updates"
```
Output: 38+ files, MongoDB with Mongoose, real-time ready

**4. Social Media Platform**
```
"Create a social network with posts, comments, likes,
followers, messaging, and notifications"
```
Output: 42+ files, PostgreSQL, WebSocket structure included

**5. CRM System**
```
"Build a CRM with contacts, companies, deals, activities,
and email integration"
```
Output: 36+ files, PostgreSQL, business logic included

### Not Ideal For

 Non-Next.js applications (Python, Java, etc.) 
 Mobile-first apps (but generates responsive web) 
 Microservices architecture (generates monolithic Next.js) 
 Real-time execution validation (no sandbox) 

---

## Extending the System

### Add a Custom Agent

1. **Create Agent File**
 ```python
 # backend/agents/phase_X/my_agent.py
 from agents.base_agent import BaseAgent
 from models.enhanced_schemas import AgentRole
 
 class MyCustomAgent(BaseAgent):
 def __init__(self, mcp_server, openai_client):
 super().__init__(
 role=AgentRole.MY_AGENT,
 mcp_server=mcp_server,
 openai_client=openai_client
 )
 
 def get_system_prompt(self) -> str:
 return """You are an expert at...
 
 **USE CHAIN OF THOUGHT REASONING**
 
 Think step-by-step:
 
 **Step 1: Understand Context**
 - What information do I have?
 - What is the goal?
 
 **Step 2: Plan Approach**
 - How should I solve this?
 - What steps are needed?
 
 ... [more steps]
 
 Then provide output in JSON format.
 """
 
 async def process_task(self, task_data):
 # Your logic here
 pass
 ```

2. **Register in Orchestrator**
 ```python
 # backend/agents/advanced_orchestrator.py
 self.my_agent = MyCustomAgent(mcp_server, openai_client)
 ```

3. **Add to Workflow**
 ```python
 # In orchestrator's generate method
 my_result = await self.my_agent.process_task(task_data)
 ```

### Customize Existing Agents

Edit the `get_system_prompt()` method in any agent file to customize behavior for your specific domain or requirements.

---

## Monitoring & Health

### Agent Health Metrics

The Monitor agent tracks:
- Success rates per agent
-  Average response times
- Error frequencies
- Activity patterns
- Overall system health

### Access Health Data

```bash
GET /api/v2/agents/enhanced
```

### Health Status Categories

- **Healthy**: Success rate >= 90%, response time < 30s
- **Degraded**: Success rate 70-90% or slow response
- **Critical**: Success rate < 70% or not responding

---

## Best Practices

1. **Review Generated Code**: Always review before deployment
2. **Address Security Findings**: Fix vulnerabilities identified
3. **Run Tests**: Execute generated tests to validate
4. **Customize Prompts**: Adjust agents for your domain
5. **Monitor Costs**: Track usage with built-in tracker
6. **Use Interactive Mode**: For complex or unclear requirements
7. **Start with Enhanced**: Use full workflow for production
8. **Iterate**: Use feedback to improve results

---

## Comparison: Generic vs Next.js Specialized

| Feature | Generic Multi-Language | Next.js Full-Stack Generator |
|---------|----------------------|------------------------------|
| **Languages** | 6+ (Python, JS, Java, Go, Rust, etc.) | **1** (Next.js + TypeScript only) |
| **Frontend** | Varies | **Next.js 14 App Router** |
| **Backend** | Separate servers | **Next.js API Routes** (same app) |
| **Database** | Not included | **Auto-designed** (PostgreSQL/MongoDB) |
| **ORM/ODM** | Not included | **Prisma or Mongoose** (generated) |
| **Migrations** | Manual | **Auto-generated** |
| **Docker** | Not included | **Complete setup** (multi-service) |
| **Deployment** | Manual configuration | **docker-compose up -d** |
| **Type Safety** | Depends on language | **TypeScript throughout** |
| **Styling** | Varies | **Tailwind CSS** |
| **Testing** | Basic | **Jest + RTL + API tests** |
| **Agents** | 13 | **16** (+Database, NextJS, Docker) |
| **Output Files** | 8-12 | **30-40 production-ready** |
| **Setup Time** | Hours | **5 minutes** |
| **Cost** | ~$0.40-0.70 | ~$0.60-1.00 |
| **Time** | 6-8 min | 6-10 min |
| **Production Ready** | Partial | **Fully ready** |

### Key Advantages of Next.js Specialization

 **No Choice Paralysis** - One battle-tested stack 
 **Complete Solution** - Database + Docker included 
 **Faster Deployment** - One command: `docker-compose up` 
 **Modern Stack** - Latest Next.js 14 with App Router 
 **Type Safe** - TypeScript everywhere 
 **Performance** - Server Components, optimized builds 
 **Best Practices** - Industry-standard architecture 
 **Scalable** - Proper database design with indexes

---

## Complete Documentation

### Main Documentation
- **[README.md](README.md)** (this file) - Complete feature overview and getting started
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete microservices architecture deep-dive
- **[MICROSERVICES_SUMMARY.md](MICROSERVICES_SUMMARY.md)** - Quick microservices overview

### Deployment Guides
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Complete Docker deployment guide
- **[kubernetes/KUBERNETES_DEPLOYMENT.md](kubernetes/KUBERNETES_DEPLOYMENT.md)** - Kubernetes with HPA guide
- **[kubernetes/QUICK_START.md](kubernetes/QUICK_START.md)** - Kubernetes 5-minute quick start

### Key Directories
- **backend/agents/** - All agent implementations with chain of thought prompting
- **backend/agents/workers/** - Phase-specific Celery workers for microservices
- **kubernetes/** - Complete Kubernetes manifests with HPA configurations

---

## Deploying Generated Applications

### Quick Deploy with Docker (Recommended)

```bash
# Extract generated files
unzip my-nextjs-app.zip
cd my-nextjs-app

# Configure environment
cp .env.example .env
# Edit .env with your values

# Deploy with Docker (includes database)
docker-compose up -d

# View logs
docker-compose logs -f

# Your app is now running on http://localhost:3000
```

### Local Development

```bash
# Install dependencies
npm install

# Set up database (PostgreSQL)
npx prisma generate
npx prisma migrate dev

# Or set up database (MongoDB)
# Just configure MONGODB_URI in .env

# Run development server
npm run dev

# Open http://localhost:3000
```

### Production Deployment

#### Vercel (Easiest)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy (includes database via Vercel Postgres)
vercel --prod
```

#### Docker Production
```bash
# Build production image
docker-compose -f docker-compose.yml build

# Run in production mode
docker-compose up -d

# Access at your domain
```

#### Traditional Server
```bash
# Build for production
npm run build

# Start production server
npm start

# Use PM2 for process management
pm2 start npm --name "my-app" -- start
```

### Environment Variables

Generated `.env.example`:
```env
# Database (PostgreSQL)
DATABASE_URL="postgresql://user:password@localhost:5432/mydb"

# Or Database (MongoDB)
MONGODB_URI="mongodb://localhost:27017/mydb"

# Next.js
NEXT_PUBLIC_API_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-here"
NEXTAUTH_URL="http://localhost:3000"

# Optional
UPLOADTHING_SECRET="your-upload-secret"
STRIPE_SECRET_KEY="your-stripe-key"
```

---

##  Contributing

Contributions are welcome! Areas for improvement:

- [ ] Web search integration for Research Agent
- [ ] Real code execution in sandbox
- [ ] Database Designer agent
- [ ] Deployment automation agent
- [ ] Performance Analyzer agent
- [ ] CI/CD pipeline generation
- [ ] Multi-language UI support
- [ ] Custom workflow builder
- [ ] Agent fine-tuning
- [ ] Code refactoring agent

---

## Troubleshooting

### Generator Issues

**Issue: OpenAI API errors**
- Check API key in `.env`
- Verify API quota/billing
- Check network connection

**Issue: Port already in use**
- Change `BACKEND_PORT` in `.env` (backend)
- Kill process using port 3000 (frontend) or 8500 (backend)
```bash
lsof -ti:3000 | xargs kill -9 # macOS/Linux
```

**Issue: Frontend not showing tech stack**
- Clear browser cache (Ctrl+Shift+Delete)
- Restart frontend: `npm start`
- Check console for errors (F12)

**Issue: Generation timing out**
- This is normal for complex apps (can take 10 minutes)
- Watch activity log for progress
- Don't refresh the page
- Check backend logs if it fails

**Issue: High costs**
- Each generation costs ~$0.60-1.00 with GPT-4
- Use GPT-3.5-turbo for testing (change in backend config)
- Monitor usage in OpenAI dashboard

### Generated App Issues

**Issue: Docker build fails**
- Check Docker is running
- Verify `.env` file exists
- Check database connection string
- View logs: `docker-compose logs`

**Issue: Prisma errors**
```bash
# Regenerate Prisma client
npx prisma generate

# Reset database
npx prisma migrate reset

# Create new migration
npx prisma migrate dev
```

**Issue: MongoDB connection errors**
- Verify MONGODB_URI in `.env`
- Check MongoDB is running (Docker or local)
- Check network connectivity

**Issue: Next.js build errors**
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build
```

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- OpenAI for GPT-4 API
- FastAPI framework
- React ecosystem
- Model Context Protocol
- All contributors and users

---

## Support

- **Documentation**: Check `/docs` API endpoint
- **Issues**: Create GitHub issue
- **Discussions**: GitHub Discussions
- **Email**: [Your contact]

---

## Quick Start Summary

```bash
# 1. Start Generator
cd backend && python main_enhanced.py # Terminal 1
cd frontend && npm start # Terminal 2

# 2. Generate App
Open http://localhost:3000
Enter: "Build a blog platform with posts and comments"
Click "Generate Next.js App"
Watch real-time generation!

# 3. Deploy Generated App
cd my-generated-app
docker-compose up -d
# Done! App running on http://localhost:3000
```

---

## What Makes This Special

Unlike traditional no-code tools that limit you to templates:

 **Complete Freedom** - Describe any app, get custom solution 
 **Real Code** - Not drag-and-drop, actual Next.js TypeScript 
 **Production Ready** - Not prototypes, deployable applications 
 **Full Stack** - Frontend, backend, database, Docker - all included 
 **Modern Stack** - Latest Next.js 14, not outdated tech 
 **Transparent** - Watch AI build it, see every file being created 
 **Deployable** - One command: `docker-compose up -d` 
 **Editable** - Get the source code, customize as needed 

---

**AI Next.js Full-Stack Generator v2.0** - From idea to deployed application in minutes! 

Generate complete Next.js applications with just a description!

Built with using AI + Next.js + Docker

*"Why write code when AI can generate production-ready applications?"*
