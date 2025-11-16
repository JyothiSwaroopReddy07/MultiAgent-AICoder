# Quick Start Guide

Get started with AI Coder in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- OpenAI API key

## Installation

### 1. Clone/Download the Project

```bash
cd ai-coder
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

### 3. Quick Start (Automated)

#### On macOS/Linux:

```bash
chmod +x start.sh
./start.sh
```

#### On Windows:

```cmd
start.bat
```

The script will automatically:
- Create Python virtual environment
- Install all dependencies
- Start both backend and frontend servers

## Manual Setup

If you prefer to set up manually:

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## Using AI Coder

1. Open your browser to `http://localhost:3000`

2. Fill in the code generation form:
   - **Description**: Describe the software you want to build
   - **Language**: Choose your programming language
   - **Framework**: (Optional) Specify a framework
   - **Requirements**: (Optional) List specific requirements

3. Click "Generate Code"

4. Watch the multi-agent system work:
   - **Planner** creates an implementation plan
   - **Coder** generates the code
   - **Tester** creates test cases
   - **Reviewer** reviews the quality

5. Review and download your generated code!

## Example Usage

Try this example to get started:

**Description:**
```
Create a REST API for a simple todo list application with CRUD operations
```

**Language:** Python

**Framework:** FastAPI

**Requirements:**
```
- Create, read, update, delete todos
- Each todo has title, description, and completed status
- SQLite database
- Pydantic models for validation
```

Click "Generate Code" and watch the magic happen!

## API Documentation

Once the backend is running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Troubleshooting

### Port Already in Use

If ports 8000 or 3000 are already in use, edit `.env`:

```
BACKEND_PORT=8001
FRONTEND_PORT=3001
```

### OpenAI API Errors

Make sure your API key is valid and has credits:
- Check your key at https://platform.openai.com/api-keys
- View usage at https://platform.openai.com/usage

### Dependencies Installation Failed

Try upgrading pip:
```bash
pip install --upgrade pip
```

Or use Python 3.10+ specifically:
```bash
python3.10 -m venv venv
```

### Frontend Won't Start

Clear cache and reinstall:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

- Explore the [Architecture Documentation](../README.md#architecture)
- Review generated code examples
- Customize agent prompts in `backend/agents/`
- Adjust LLM settings in `.env`

## Support

For issues and questions:
- Check the main [README.md](../README.md)
- Review API documentation at `/docs`
- Check backend logs for errors

Happy coding! 🚀
