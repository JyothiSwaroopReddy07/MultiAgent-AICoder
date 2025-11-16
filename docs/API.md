# API Documentation

Complete API reference for the AI Coder backend.

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### 1. Generate Code

Generate a complete software application from requirements.

**Endpoint:** `POST /generate`

**Request Body:**
```json
{
  "description": "Create a REST API for a todo list application",
  "language": "python",
  "framework": "fastapi",
  "requirements": [
    "CRUD operations",
    "SQLite database",
    "Authentication"
  ]
}
```

**Response:** `200 OK`
```json
{
  "request_id": "abc-123-def",
  "status": "completed",
  "plan": {
    "overview": "Implementation overview...",
    "steps": ["Step 1", "Step 2", ...],
    "file_structure": {
      "main.py": "Main application file",
      "models.py": "Data models"
    },
    "dependencies": ["fastapi", "sqlalchemy"],
    "estimated_complexity": "medium"
  },
  "code_files": [
    {
      "filename": "main.py",
      "filepath": "./main.py",
      "content": "# Python code here...",
      "language": "python",
      "description": "Main FastAPI application"
    }
  ],
  "test_files": [
    {
      "name": "Test main.py",
      "filepath": "./tests/test_main.py",
      "content": "# Test code here...",
      "test_type": "unit",
      "target_file": "./main.py"
    }
  ],
  "review": {
    "file": "Overall Project",
    "issues": [],
    "suggestions": ["Consider adding logging"],
    "quality_score": 8.5,
    "approved": true
  },
  "agent_activities": [
    {
      "agent": "planner",
      "action": "Creating implementation plan",
      "status": "completed",
      "start_time": "2024-01-01T10:00:00",
      "end_time": "2024-01-01T10:00:30",
      "llm_usage": {
        "model": "gpt-4",
        "prompt_tokens": 500,
        "completion_tokens": 800,
        "total_tokens": 1300,
        "cost": 0.052
      }
    }
  ],
  "total_llm_usage": {
    "total_calls": 4,
    "total_tokens": 5200
  },
  "total_cost": 0.208,
  "created_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:02:00"
}
```

---

### 2. Get Request Status

Get the status of a code generation request.

**Endpoint:** `GET /status/{request_id}`

**Parameters:**
- `request_id` (path): The unique request ID

**Response:** `200 OK`
```json
{
  "request_id": "abc-123-def",
  "status": "in_progress",
  ...
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": "Request not found"
}
```

---

### 3. Get LLM Usage Statistics

Get current LLM usage statistics.

**Endpoint:** `GET /usage`

**Response:** `200 OK`
```json
{
  "total_calls": 10,
  "total_tokens": 25000,
  "total_cost": 1.25,
  "average_tokens_per_call": 2500,
  "usage_by_model": {
    "gpt-4": {
      "calls": 6,
      "tokens": 15000,
      "cost": 0.90
    },
    "gpt-3.5-turbo": {
      "calls": 4,
      "tokens": 10000,
      "cost": 0.35
    }
  }
}
```

---

### 4. Reset Usage Statistics

Reset LLM usage statistics.

**Endpoint:** `POST /usage/reset`

**Response:** `200 OK`
```json
{
  "message": "Usage statistics reset successfully"
}
```

---

### 5. Health Check

Check if the API is running.

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "AI Coder Multi-Agent System"
}
```

---

### 6. Get Agents Information

Get information about registered agents.

**Endpoint:** `GET /agents`

**Response:** `200 OK`
```json
{
  "agents": [
    {
      "role": "planner",
      "description": "Analyzes requirements and creates implementation plans",
      "status": "active"
    },
    {
      "role": "coder",
      "description": "Generates code based on implementation plans",
      "status": "active"
    },
    {
      "role": "tester",
      "description": "Creates test cases for generated code",
      "status": "active"
    },
    {
      "role": "reviewer",
      "description": "Reviews code quality and provides feedback",
      "status": "active"
    }
  ],
  "mcp_server": {
    "status": "running",
    "host": "localhost",
    "port": 5000
  }
}
```

---

## Data Models

### CodeRequest

```typescript
{
  description: string;        // Required: Software description
  language?: string;          // Optional: Programming language (default: "python")
  framework?: string;         // Optional: Framework to use
  requirements?: string[];    // Optional: List of specific requirements
}
```

### CodeGenerationResult

See the `/generate` endpoint response for the complete structure.

### Agent Roles

- `planner` - Creates implementation plans
- `coder` - Generates code
- `tester` - Creates tests
- `reviewer` - Reviews code quality

### Status Values

- `in_progress` - Generation is ongoing
- `completed` - Generation completed successfully
- `failed` - Generation failed with errors

---

## Error Handling

All endpoints may return error responses:

**400 Bad Request**
```json
{
  "detail": "Invalid request format"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "details": {
    "message": "Error description"
  }
}
```

---

## Rate Limiting

Currently, there are no rate limits, but be mindful of:
- OpenAI API rate limits
- Token usage costs
- Server resources

---

## Interactive Documentation

Visit these URLs when the server is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

These provide interactive API testing and documentation.
