# 🚀 Quick Start - No-Code Interface

## One-Time Setup

```bash
# Install frontend dependencies
cd frontend
npm install
cd ..
```

## Start Application

```bash
# Terminal 1 - Backend
cd backend
python main_enhanced.py

# Terminal 2 - Frontend
cd frontend
npm start
```

## Access

Open browser: **http://localhost:3000**

## Usage

1. **Enter what you want to build** (in plain English)
2. **Select language** (Python, JavaScript, TypeScript, etc.)
3. **Click "Generate Code"**
4. **Watch AI build it in real-time!**
5. **Download all files**

## Example Request

```
Build a REST API for a todo app with:
- User authentication (JWT tokens)
- CRUD operations for tasks
- SQLite database
- Input validation
- Unit tests
```

## What You'll See

- ✅ **Real-time progress** (0-100%)
- ✅ **Live activity log** (what agents are doing)
- ✅ **Files generated** as they're created
- ✅ **VS Code-like editor** with syntax highlighting
- ✅ **File tree** to browse all files
- ✅ **Multiple tabs** to view different files

## Features

- 🎨 **Monaco Editor** - Same editor as VS Code
- 🔄 **Real-time Streaming** - Watch code being written
- 📊 **Activity Feed** - See what's happening live
- 📁 **File Explorer** - Browse generated files
- ⚡ **Fast** - See results immediately
- 💾 **Download** - Get all files with one click

## Tips

- **Be specific** in your requirements
- **Watch the activity log** to see progress
- **Explore all files** in the tree
- **Check test files** to understand usage
- **Review security findings** in activity log

## Troubleshooting

**Backend won't start?**
```bash
cd backend
pip install -r requirements.txt
python main_enhanced.py
```

**Frontend won't start?**
```bash
cd frontend
rm -rf node_modules
npm install
npm start
```

**No code appearing?**
- Check backend is running on port 8500
- Check OpenAI API key in `.env`
- Look at activity log for errors

---

**That's it!** Now start building with AI - no coding required! 🎉

