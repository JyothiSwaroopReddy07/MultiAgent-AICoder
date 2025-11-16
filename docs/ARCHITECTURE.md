# Architecture Documentation

Deep dive into the AI Coder multi-agent system architecture.

## Overview

AI Coder is a sophisticated multi-agent system that uses the Model Context Protocol (MCP) to coordinate specialized AI agents in generating complete software applications.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface (React)                │
│  - Code Request Form                                     │
│  - Agent Progress Display                                │
│  - Result Viewer                                         │
│  - Usage Statistics                                      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend Server                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │          API Routes (/api/v1/*)                  │   │
│  │  - /generate  - /status  - /usage               │   │
│  └────────────────────┬────────────────────────────┘   │
│                       ▼                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Agent Orchestrator                      │   │
│  │  Coordinates workflow across all agents          │   │
│  └────────────────────┬────────────────────────────┘   │
└───────────────────────┼──────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│         Model Context Protocol (MCP) Server              │
│  - Message routing                                       │
│  - Agent registration                                    │
│  - Communication management                              │
│  - Message history                                       │
└───────┬─────────┬─────────┬─────────┬───────────────────┘
        │         │         │         │
    ┌───▼───┐ ┌──▼───┐ ┌───▼────┐ ┌─▼────────┐
    │Planner│ │Coder │ │Tester  │ │Reviewer  │
    │Agent  │ │Agent │ │Agent   │ │Agent     │
    └───┬───┘ └──┬───┘ └───┬────┘ └─┬────────┘
        │        │         │         │
        └────────┴─────────┴─────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  OpenAI API (GPT-4)   │
        │  - Chat completions   │
        │  - Token tracking     │
        └───────────────────────┘
```

## Core Components

### 1. Frontend (React + TypeScript)

**Location:** `frontend/src/`

#### Components:
- **CodeRequestForm**: User input for software requirements
- **AgentProgress**: Real-time agent activity display
- **ResultDisplay**: Shows generated code, tests, and reviews
- **UsageStats**: LLM usage metrics and costs

#### Services:
- **API Service**: HTTP client for backend communication

#### State Management:
- React hooks for local state
- No external state management (keeps it simple)

---

### 2. Backend (Python + FastAPI)

**Location:** `backend/`

#### API Layer (`api/routes.py`)
- RESTful endpoints
- Request validation with Pydantic
- Error handling and logging

#### Configuration (`config.py`)
- Environment variable management
- Settings validation
- Centralized configuration

#### Main Application (`main.py`)
- FastAPI app initialization
- CORS middleware
- Lifecycle management
- Global exception handling

---

### 3. Model Context Protocol (MCP)

**Location:** `backend/mcp/server.py`

The MCP server is the communication backbone:

#### Key Responsibilities:
1. **Agent Registration**: Agents register on initialization
2. **Message Routing**: Routes messages between agents
3. **Message Queue**: Async message processing
4. **History Tracking**: Maintains conversation history
5. **Pub/Sub Pattern**: Agents subscribe to message types

#### Message Flow:
```
Agent A → MCP Server → Message Queue → MCP Server → Agent B
```

#### Message Types:
- `REQUEST`: Agent requests action from another agent
- `RESPONSE`: Agent responds to a request
- `NOTIFICATION`: Broadcast messages
- `ERROR`: Error notifications

---

### 4. Multi-Agent System

**Location:** `backend/agents/`

#### Base Agent (`base_agent.py`)

Abstract base class providing:
- MCP communication methods
- LLM calling with tracking
- Activity logging
- Message handling

All agents inherit from `BaseAgent`.

#### Specialized Agents

**Planner Agent** (`planner_agent.py`)
- **Role**: Analyzes requirements, creates implementation plans
- **Input**: Software description, language, framework, requirements
- **Output**: Detailed plan with steps, file structure, dependencies
- **LLM Prompt**: Structured JSON response format

**Coder Agent** (`coder_agent.py`)
- **Role**: Generates code files based on plan
- **Input**: Implementation plan, project context
- **Output**: Complete code files with documentation
- **LLM Prompt**: Production-ready code with best practices

**Tester Agent** (`tester_agent.py`)
- **Role**: Creates comprehensive test suites
- **Input**: Generated code files
- **Output**: Unit tests for each code file
- **LLM Prompt**: Test framework-specific test generation

**Reviewer Agent** (`reviewer_agent.py`)
- **Role**: Reviews code quality and provides feedback
- **Input**: Code files and tests
- **Output**: Issues, suggestions, quality score
- **LLM Prompt**: Security, performance, and style review

---

### 5. Orchestrator

**Location:** `backend/agents/orchestrator.py`

The orchestrator coordinates the multi-agent workflow:

#### Workflow Steps:
1. **Initialize**: Create request, reset trackers
2. **Plan**: Planner agent analyzes requirements
3. **Code**: Coder agent generates files
4. **Test**: Tester agent creates test cases
5. **Review**: Reviewer agent assesses quality
6. **Finalize**: Compile results, calculate metrics

#### Error Handling:
- Each step can fail independently
- Errors are captured and reported
- Partial results are preserved

---

### 6. LLM Integration

**Location:** `backend/utils/`

#### OpenAI Client (`openai_client.py`)
- Async API calls
- Automatic retry logic
- Fallback model support
- Usage tracking integration

#### LLM Tracker (`llm_tracker.py`)
- Tracks every API call
- Calculates costs per model
- Aggregates statistics
- Usage by model breakdown

#### Cost Calculation:
```python
cost = (prompt_tokens / 1000 * prompt_price) +
       (completion_tokens / 1000 * completion_price)
```

---

## Data Flow

### Complete Generation Flow:

1. **User submits request** via React UI
   ```
   POST /api/v1/generate
   {
     description: "Create a todo API",
     language: "python",
     framework: "fastapi"
   }
   ```

2. **FastAPI receives request**
   - Validates input
   - Passes to Orchestrator

3. **Orchestrator starts workflow**
   - Creates request ID
   - Resets LLM tracker
   - Initiates agent sequence

4. **Planner Agent**
   - Receives requirements
   - Calls GPT-4 for planning
   - Returns structured plan
   - Activity logged

5. **Coder Agent**
   - Receives plan
   - Generates code for each file
   - Multiple LLM calls
   - Activities logged

6. **Tester Agent**
   - Receives code files
   - Generates test for each file
   - Multiple LLM calls
   - Activities logged

7. **Reviewer Agent**
   - Receives code and tests
   - Reviews each file
   - Calculates quality score
   - Activity logged

8. **Results compiled**
   - All agent outputs combined
   - Usage statistics aggregated
   - Total cost calculated

9. **Response sent to frontend**
   - Complete results
   - Agent activities
   - Usage metrics

10. **UI displays results**
    - Plan, code, tests, review
    - Agent progress
    - Cost breakdown

---

## Design Patterns

### 1. Strategy Pattern
Each agent implements the same interface but with different strategies for their specific role.

### 2. Observer Pattern
Agents subscribe to MCP message types and react to relevant messages.

### 3. Command Pattern
Messages are commands that agents process asynchronously.

### 4. Factory Pattern
Orchestrator creates and manages agent instances.

### 5. Singleton Pattern
MCP server and LLM tracker are global singletons.

---

## Scalability Considerations

### Current Design:
- Single-threaded async Python
- In-memory message queue
- No persistent storage

### Scaling Options:

**Horizontal Scaling:**
- Add load balancer
- Multiple backend instances
- Shared message queue (Redis, RabbitMQ)
- Distributed agent pool

**Vertical Scaling:**
- Increase server resources
- Optimize LLM calls
- Cache common patterns

**Storage:**
- Add database for request history
- Store generated code
- Cache plans and patterns

---

## Security Considerations

### Current Security:

1. **API Key Protection**
   - Stored in environment variables
   - Never exposed to frontend

2. **CORS Configuration**
   - Restricted origins
   - Configurable in settings

3. **Input Validation**
   - Pydantic models
   - Type checking

### Production Security:

1. **Authentication**
   - Add user authentication
   - API key management
   - Rate limiting

2. **Code Execution**
   - Sandbox generated code
   - Security scanning
   - Malware detection

3. **Data Protection**
   - Encrypt sensitive data
   - Secure storage
   - Access logging

---

## Performance Optimization

### Current Performance:
- 4 sequential LLM calls per generation
- Average: 2-3 minutes per request
- Cost: $0.10-0.50 per generation

### Optimization Strategies:

1. **Parallel Processing**
   - Run some agents in parallel
   - Coder can generate files concurrently

2. **Caching**
   - Cache similar plans
   - Reuse test patterns
   - Store common code templates

3. **Model Selection**
   - Use GPT-3.5 for simpler tasks
   - GPT-4 only when needed
   - Custom models for specific tasks

4. **Token Optimization**
   - Optimize prompts
   - Reduce context size
   - Better structured outputs

---

## Testing Strategy

### Unit Tests
- Test individual agents
- Mock LLM responses
- Test MCP message routing

### Integration Tests
- Test agent collaboration
- End-to-end workflows
- API endpoints

### Example Test:
```python
@pytest.mark.asyncio
async def test_planner_agent():
    mock_client = MockOpenAIClient()
    mcp = MCPServer()
    agent = PlannerAgent(mcp, mock_client)

    result = await agent.process_task({
        "description": "Test app",
        "language": "python"
    })

    assert "plan" in result
    assert len(result["plan"]["steps"]) > 0
```

---

## Monitoring and Logging

### Current Logging:
- Structured logging with `structlog`
- JSON format for easy parsing
- Log levels: DEBUG, INFO, ERROR

### Metrics to Track:
- Request duration
- LLM token usage
- Agent success rates
- Error frequencies
- Cost per request

### Recommended Tools:
- **Logging**: ELK Stack, Splunk
- **Monitoring**: Prometheus, Grafana
- **APM**: New Relic, DataDog
- **Tracing**: Jaeger, Zipkin

---

## Future Enhancements

### Planned Features:

1. **Agent Memory**
   - Remember past generations
   - Learn from feedback
   - Improve over time

2. **Custom Agents**
   - User-defined agents
   - Plugin system
   - Agent marketplace

3. **Interactive Mode**
   - Chat with agents
   - Iterative refinement
   - Real-time collaboration

4. **Version Control Integration**
   - Git integration
   - Automatic commits
   - PR generation

5. **Deployment Support**
   - Generate Dockerfiles
   - Cloud deployment configs
   - CI/CD pipelines

---

## Contributing

To extend the system:

1. **Add New Agent:**
   - Inherit from `BaseAgent`
   - Implement `process_task()` and `get_system_prompt()`
   - Register with orchestrator

2. **Modify Workflow:**
   - Update `orchestrator.py`
   - Add new workflow steps
   - Update frontend for new outputs

3. **Add Features:**
   - Extend data models in `schemas.py`
   - Add API endpoints in `routes.py`
   - Update React components

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [React Documentation](https://react.dev/)
- [Model Context Protocol](https://github.com/anthropics/mcp) (conceptual)

---

For more information, see:
- [Quick Start Guide](QUICK_START.md)
- [API Documentation](API.md)
- [Usage Examples](EXAMPLES.md)
