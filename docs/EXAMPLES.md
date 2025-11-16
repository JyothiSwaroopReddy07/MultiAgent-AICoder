# Usage Examples

Here are some example requests you can try with AI Coder.

## Example 1: Todo List API

**Description:**
```
Create a REST API for managing todo items with full CRUD operations.
Users should be able to create, read, update, and delete todos.
Each todo should have a title, description, and completion status.
```

**Language:** Python

**Framework:** FastAPI

**Requirements:**
- CRUD operations for todos
- SQLite database
- Pydantic models
- Input validation
- API documentation

**Expected Output:**
- `main.py` - FastAPI application
- `models.py` - Pydantic schemas
- `database.py` - Database setup
- `crud.py` - CRUD operations
- Tests for all endpoints

---

## Example 2: User Authentication System

**Description:**
```
Build a user authentication system with registration, login, and JWT token management.
Include password hashing and token refresh functionality.
```

**Language:** Python

**Framework:** FastAPI

**Requirements:**
- User registration with email validation
- Password hashing with bcrypt
- JWT token generation
- Token refresh endpoint
- Protected routes
- User profile endpoint

---

## Example 3: Blog Post Manager

**Description:**
```
Create a blog management system where users can create, edit, and publish blog posts.
Posts should support markdown content and have tags for categorization.
```

**Language:** TypeScript

**Framework:** Express

**Requirements:**
- Post CRUD operations
- Markdown support
- Tag system
- Draft/published status
- Search by tags
- Author information

---

## Example 4: File Upload Service

**Description:**
```
Implement a file upload service that accepts files, validates them,
stores them securely, and provides download URLs.
```

**Language:** Python

**Framework:** FastAPI

**Requirements:**
- Multiple file upload
- File type validation (images, PDFs)
- Size limit enforcement
- Unique filename generation
- File storage in filesystem
- Download endpoint

---

## Example 5: Data Processing Pipeline

**Description:**
```
Create a data processing pipeline that reads CSV files,
validates data, performs transformations, and exports results.
```

**Language:** Python

**Framework:** None (standalone)

**Requirements:**
- CSV file reading
- Data validation with Pydantic
- Data transformation functions
- Error handling and logging
- Export to JSON and CSV
- Unit tests for transformations

---

## Example 6: Real-time Chat Server

**Description:**
```
Build a WebSocket-based chat server with rooms and private messaging.
Users can join rooms and send messages in real-time.
```

**Language:** JavaScript

**Framework:** Socket.io

**Requirements:**
- WebSocket connection management
- Chat rooms
- Private messaging
- User presence tracking
- Message history
- Connection handling

---

## Example 7: Weather Data API Wrapper

**Description:**
```
Create an API wrapper that fetches weather data from an external API,
caches results, and provides a simplified interface.
```

**Language:** Python

**Framework:** Flask

**Requirements:**
- External API integration
- Response caching (Redis or in-memory)
- Error handling
- Rate limiting
- Data formatting
- API documentation

---

## Example 8: Task Scheduler

**Description:**
```
Implement a task scheduling system that can schedule and execute
recurring tasks at specified intervals.
```

**Language:** Python

**Framework:** None

**Requirements:**
- Task registration
- Cron-like scheduling
- Background execution
- Task status tracking
- Logging
- Error recovery

---

## Tips for Best Results

1. **Be Specific**: Provide clear, detailed descriptions
2. **List Requirements**: Break down features into specific requirements
3. **Choose Appropriate Language**: Select the language that best fits your needs
4. **Specify Frameworks**: If you have a preference, mention it
5. **Include Context**: Explain the use case or business logic

## Customizing Generated Code

After generation:
1. Review the implementation plan
2. Check the code quality score
3. Read review suggestions
4. Download and test the code
5. Iterate if needed with more specific requirements

## Advanced Usage

### Complex Applications

For larger applications, break them down:

1. Start with core functionality
2. Generate and test
3. Build additional features incrementally
4. Combine generated modules

### Best Practices

- Start simple and add complexity
- Test generated code thoroughly
- Review security suggestions
- Customize based on review feedback
- Track LLM usage costs

## Need Help?

- Check the [Quick Start Guide](QUICK_START.md)
- Review [README](../README.md) for architecture details
- Examine generated code for patterns
- Adjust requirements for better results
