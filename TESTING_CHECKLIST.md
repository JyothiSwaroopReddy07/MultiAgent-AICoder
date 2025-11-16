# ✅ Testing Checklist

Use this checklist to verify everything works correctly.

---

## 🔧 Setup Checklist

- [ ] **Frontend dependencies installed**
  ```bash
  cd frontend
  npm install  # Should show "added 5 packages"
  ```

- [ ] **Backend dependencies OK**
  ```bash
  cd backend
  pip list | grep -E "fastapi|openai|structlog"
  ```

- [ ] **OpenAI API key set**
  ```bash
  cat .env | grep OPENAI_API_KEY
  # Should show your API key
  ```

---

## 🚀 Startup Checklist

### Terminal 1 - Backend

- [ ] **Start backend**
  ```bash
  cd backend
  python main_enhanced.py
  ```

- [ ] **Verify backend started**
  - [ ] See "AI Coder Enhanced Multi-Agent System v2.0" banner
  - [ ] See "Application startup complete"
  - [ ] See "Uvicorn running on http://0.0.0.0:8500"
  - [ ] No errors in output

### Terminal 2 - Frontend

- [ ] **Start frontend**
  ```bash
  cd frontend
  npm start
  ```

- [ ] **Verify frontend started**
  - [ ] See "webpack compiled successfully"
  - [ ] Browser opens automatically to http://localhost:3000
  - [ ] No compilation errors

---

## 🎨 UI Checklist

### Initial Load

- [ ] **Page loads successfully**
- [ ] **Header shows:**
  - [ ] Title: "AI Coder - No Code Required"
  - [ ] Subtitle: "Describe what you want..."
- [ ] **Left sidebar shows:**
  - [ ] Large text area for description
  - [ ] Language dropdown
  - [ ] "Generate Code" button (blue gradient)
- [ ] **Right panel shows:**
  - [ ] "ACTIVITY LOG" header
  - [ ] "No activity yet..." message
- [ ] **Center area is empty** (no files yet)

### Visual Check

- [ ] **Dark theme** (gray/black background)
- [ ] **Icons visible** (Terminal icon, Activity icon)
- [ ] **No console errors** (Press F12, check Console tab)
- [ ] **Responsive layout** (try resizing browser)

---

## 🧪 Functional Testing

### Test 1: Simple Generation

- [ ] **Enter description:**
  ```
  Build a simple calculator API with add, subtract,
  multiply, divide operations using FastAPI
  ```

- [ ] **Select language:** Python

- [ ] **Click "Generate Code"**

- [ ] **Verify progress bar appears:**
  - [ ] Shows 0-100% progress
  - [ ] Updates as phases progress
  - [ ] Shows current phase text
  - [ ] Shows current agent text
  - [ ] Cancel button visible

- [ ] **Verify activity log updates:**
  - [ ] "🚀 Starting code generation..."
  - [ ] "📋 Phase 1: Discovery & Analysis"
  - [ ] "🤖 Requirements Analyst: Analyzing..."
  - [ ] Events appear in real-time
  - [ ] Auto-scrolls to bottom

- [ ] **Wait for Phase 3 (Implementation)**

- [ ] **Verify files appear:**
  - [ ] File tree appears on left
  - [ ] Files shown with icons
  - [ ] Folders expandable
  - [ ] First file opens automatically

- [ ] **Verify Monaco Editor:**
  - [ ] Code appears in center
  - [ ] Syntax highlighting (colored)
  - [ ] Line numbers on left
  - [ ] File tab at top
  - [ ] Status bar at bottom

- [ ] **Verify completion:**
  - [ ] Progress reaches 100%
  - [ ] "🎉 Code generation completed!" in log
  - [ ] "Download All" button enabled
  - [ ] No errors in activity log

### Test 2: File Navigation

- [ ] **Click different files in tree:**
  - [ ] File opens in editor
  - [ ] Content changes
  - [ ] Syntax highlighting matches file type
  - [ ] Tab added at top

- [ ] **Open multiple files:**
  - [ ] Multiple tabs appear
  - [ ] Switch between tabs works
  - [ ] Close tab with X button works
  - [ ] Selected tab highlighted

- [ ] **Expand/collapse folders:**
  - [ ] Folder icon changes
  - [ ] Children show/hide
  - [ ] Badge shows file count

### Test 3: Download

- [ ] **Click "Download All" button**
- [ ] **Verify downloads:**
  - [ ] Multiple files downloaded
  - [ ] File names correct
  - [ ] File contents match editor
  - [ ] Can open files locally

### Test 4: Cancel

- [ ] **Start new generation**
- [ ] **Click "Cancel" during generation**
- [ ] **Verify:**
  - [ ] Generation stops
  - [ ] "⚠️ Generation cancelled" in log
  - [ ] Progress stops updating
  - [ ] UI remains responsive

---

## 🎯 Activity Log Checklist

Verify different event types appear correctly:

- [ ] **Phase events (blue):**
  - [ ] "📋 Phase 1: Discovery & Analysis"
  - [ ] "📋 Phase 2: Design & Planning"
  - [ ] "📋 Phase 3: Implementation"

- [ ] **Agent events (purple):**
  - [ ] "🤖 Requirements Analyst: Analyzing..."
  - [ ] "🤖 Code Generator: Generating..."
  - [ ] Shows activity description

- [ ] **File events (green):**
  - [ ] "📄 Generated main.py"
  - [ ] "📄 Generated config.py"
  - [ ] One event per file

- [ ] **Success events (green):**
  - [ ] "✓ Requirements Analyst completed"
  - [ ] "✓ Code Generator completed"
  - [ ] Shows completion data

- [ ] **Completion event:**
  - [ ] "🎉 Code generation completed!"
  - [ ] Final event in log

---

## 🔍 Monaco Editor Checklist

- [ ] **Syntax highlighting works:**
  - [ ] Python: imports, keywords colored
  - [ ] JavaScript: function, const colored
  - [ ] Comments are gray/green
  - [ ] Strings are colored

- [ ] **Line numbers:**
  - [ ] Visible on left
  - [ ] Aligned with code
  - [ ] Gray color

- [ ] **Minimap:**
  - [ ] Visible on right side
  - [ ] Shows code overview
  - [ ] Clickable for navigation

- [ ] **Status bar:**
  - [ ] Shows line count
  - [ ] Shows file size
  - [ ] Shows language

- [ ] **Scrolling:**
  - [ ] Vertical scroll works
  - [ ] Horizontal scroll works (if needed)
  - [ ] Smooth scrolling

---

## 🌐 Browser Compatibility

Test in different browsers:

- [ ] **Chrome:** Everything works
- [ ] **Firefox:** Everything works
- [ ] **Safari:** Everything works
- [ ] **Edge:** Everything works

---

## 📱 Responsive Design

Test at different screen sizes:

- [ ] **Desktop (1920x1080):**
  - [ ] 3-column layout
  - [ ] All panels visible
  - [ ] Comfortable spacing

- [ ] **Laptop (1366x768):**
  - [ ] Layout adjusts
  - [ ] Still usable
  - [ ] Scrollbars if needed

- [ ] **Tablet landscape (1024x768):**
  - [ ] Layout responsive
  - [ ] Still functional
  - [ ] May need scrolling

---

## 🚨 Error Handling

### Test Error Cases:

- [ ] **Backend not running:**
  - [ ] Try generating code
  - [ ] Error appears in activity log
  - [ ] User-friendly error message

- [ ] **Invalid API key:**
  - [ ] Backend shows error
  - [ ] Frontend shows error
  - [ ] Clear error message

- [ ] **Network error:**
  - [ ] Disconnect network mid-generation
  - [ ] Error caught gracefully
  - [ ] UI remains responsive

---

## ⚡ Performance Checklist

- [ ] **Initial load:**
  - [ ] Page loads in < 3 seconds
  - [ ] No lag in UI
  - [ ] Smooth animations

- [ ] **During generation:**
  - [ ] UI remains responsive
  - [ ] Activity log updates smoothly
  - [ ] No freezing
  - [ ] Can cancel anytime

- [ ] **File navigation:**
  - [ ] Switching files is instant
  - [ ] Monaco loads quickly
  - [ ] No lag when opening files

- [ ] **Large files:**
  - [ ] Files with 500+ lines load OK
  - [ ] Scrolling is smooth
  - [ ] Syntax highlighting works

---

## 🔄 Multiple Generations

- [ ] **Generate code once:** Works ✓
- [ ] **Generate again (same session):**
  - [ ] Previous files cleared
  - [ ] New generation starts fresh
  - [ ] Activity log resets
  - [ ] Progress resets to 0%
- [ ] **Generate third time:** Still works ✓

---

## 🎓 Example Test Cases

### Test Case 1: Todo API
```
Build a REST API for a todo list with:
- User authentication (JWT tokens)
- CRUD operations for todos
- SQLite database
- Input validation
```

Expected:
- [ ] 8-12 files generated
- [ ] main.py, models.py, auth.py, database.py
- [ ] routes/ folder with endpoints
- [ ] tests/ folder with test files
- [ ] requirements.txt

### Test Case 2: Calculator API
```
Build a simple calculator API with add, subtract,
multiply, divide operations using FastAPI
```

Expected:
- [ ] 4-6 files generated
- [ ] main.py with operations
- [ ] test files
- [ ] Completes in < 3 minutes

### Test Case 3: Blog API
```
Build a blog API with posts, comments, user auth,
categories, tags, and search functionality
```

Expected:
- [ ] 15+ files generated
- [ ] Multiple route files
- [ ] Comprehensive tests
- [ ] Completes in 6-8 minutes

---

## ✅ Final Verification

- [ ] **All features working:**
  - [ ] Real-time streaming ✓
  - [ ] Monaco Editor ✓
  - [ ] File tree ✓
  - [ ] Activity log ✓
  - [ ] Progress bar ✓
  - [ ] Multi-tabs ✓
  - [ ] Download ✓

- [ ] **No errors in:**
  - [ ] Browser console (F12)
  - [ ] Backend logs
  - [ ] Terminal output

- [ ] **User experience:**
  - [ ] Intuitive UI
  - [ ] Clear feedback
  - [ ] Smooth experience
  - [ ] Professional look

---

## 🎉 Success Criteria

✅ **Minimum Requirements:**
- Can generate code successfully
- Real-time updates visible
- Monaco Editor shows code
- Can download files

✅ **Ideal State:**
- All features work perfectly
- No errors or warnings
- Smooth, professional UX
- Fast and responsive

---

## 📞 If Something Doesn't Work

1. **Check browser console** (F12 → Console)
2. **Check backend logs** (Terminal 1 output)
3. **Verify ports:**
   - Backend: http://localhost:8500
   - Frontend: http://localhost:3000
4. **Restart services:**
   - Ctrl+C both terminals
   - Start backend first
   - Then start frontend
5. **Clear browser cache:** Ctrl+Shift+Delete
6. **Reinstall dependencies:**
   ```bash
   cd frontend
   rm -rf node_modules
   npm install
   ```

---

## 📊 Test Report Template

```
Date: ___________
Tester: ___________

Setup: ✅ / ❌
Startup: ✅ / ❌
UI Load: ✅ / ❌
Simple Generation: ✅ / ❌
File Navigation: ✅ / ❌
Monaco Editor: ✅ / ❌
Activity Log: ✅ / ❌
Download: ✅ / ❌

Issues Found:
1. _______________________
2. _______________________

Overall: PASS / FAIL
```

---

**Happy Testing!** 🧪✅

If everything passes, you're ready to share this with users! 🎉

