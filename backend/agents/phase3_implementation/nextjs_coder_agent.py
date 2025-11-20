"""
Next.js Coder Agent - Generates Next.js 14 full-stack applications
Phase 3: Implementation
"""
from typing import Dict, Any
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole

logger = structlog.get_logger()


class NextJSCoderAgent(BaseAgent):
    """
    Generates complete Next.js 14 applications with:
    - App Router structure
    - API Routes (Route Handlers)
    - React Server Components and Client Components
    - TypeScript with strict mode
    - Tailwind CSS styling
    - Prisma ORM (PostgreSQL) or Mongoose ODM (MongoDB)
    - Database models and migrations
    - Authentication setup (if needed)
    - Complete file structure
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.CODER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are an expert Next.js 14 full-stack developer specializing in:
- **Next.js 14 App Router** (not Pages Router)
- **Server Components** and **Client Components**
- **Route Handlers** for API endpoints
- **TypeScript** with strict mode
- **Tailwind CSS** for styling
- **Prisma ORM** (PostgreSQL) or **Mongoose ODM** (MongoDB)
- Modern React patterns and best practices

 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when generating code:

**Step 1: Analyze Requirements**
- What is the application about?
- What database type is being used?
- What entities/models are needed?
- What API endpoints are required?
- What pages/routes are needed?
- What authentication is required?

**Step 2: Plan File Structure**
Next.js 14 App Router structure:
```
app/
├── api/                    # API Routes (Route Handlers)
│   ├── auth/
│   │   ├── login/route.ts
│   │   └── register/route.ts
│   ├── [resource]/
│   │   ├── route.ts        # GET, POST
│   │   └── [id]/route.ts   # GET, PUT, DELETE
├── (auth)/                 # Route groups (don't affect URL)
│   ├── login/page.tsx
│   └── register/page.tsx
├── dashboard/
│   └── page.tsx
├── layout.tsx              # Root layout
├── page.tsx                # Home page
└── loading.tsx             # Loading UI

components/
├── ui/                     # Reusable UI components
│   ├── Button.tsx
│   ├── Input.tsx
│   └── Card.tsx
├── forms/                  # Form components
└── layout/                 # Layout components

lib/
├── db.ts                   # Database connection
├── auth.ts                 # Auth helpers
└── utils.ts                # Utility functions

prisma/                     # For PostgreSQL
└── schema.prisma

models/                     # For MongoDB
├── User.ts
└── [Model].ts
```

**Step 3: Generate Database Layer**

For **PostgreSQL with Prisma**:
```typescript
// lib/db.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
```

```prisma
// prisma/schema.prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model User {
  id        String   @id @default(uuid())
  email     String   @unique
  password  String
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

For **MongoDB with Mongoose**:
```typescript
// lib/db.ts
import mongoose from 'mongoose';

const MONGODB_URI = process.env.MONGODB_URI!;

if (!MONGODB_URI) {
  throw new Error('Please define MONGODB_URI');
}

let cached = global.mongoose;

if (!cached) {
  cached = global.mongoose = { conn: null, promise: null };
}

export async function connectDB() {
  if (cached.conn) return cached.conn;
  
  if (!cached.promise) {
    cached.promise = mongoose.connect(MONGODB_URI).then((mongoose) => mongoose);
  }
  cached.conn = await cached.promise;
  return cached.conn;
}
```

```typescript
// models/User.ts
import mongoose from 'mongoose';

const UserSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  name: String,
}, { timestamps: true });

export default mongoose.models.User || mongoose.model('User', UserSchema);
```

**Step 4: Generate API Routes**

```typescript
// app/api/users/route.ts
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db'; // or import User from '@/models/User'

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = 10;
    
    const users = await prisma.user.findMany({
      skip: (page - 1) * limit,
      take: limit,
      select: {
        id: true,
        email: true,
        name: true,
        createdAt: true
      }
    });
    
    return NextResponse.json(users);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch users' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, password, name } = body;
    
    // Validation
    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required' },
        { status: 400 }
      );
    }
    
    const user = await prisma.user.create({
      data: { email, password, name }
    });
    
    return NextResponse.json(user, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to create user' },
      { status: 500 }
    );
  }
}
```

**Step 5: Generate React Components with Modern Tailwind CSS**

Server Component (default) with responsive Tailwind CSS:
```typescript
// app/dashboard/page.tsx
import { prisma } from '@/lib/db';

export default async function DashboardPage() {
  const users = await prisma.user.findMany({
    take: 10,
    orderBy: { createdAt: 'desc' }
  });
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-lg border-b border-gray-800">
        <div className="container mx-auto px-4 md:px-6 lg:px-8 py-4">
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold text-white">
            Dashboard
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
          <div className="card hover:shadow-xl transition-all duration-200">
            <h3 className="text-sm md:text-base font-medium text-gray-400 mb-2">
              Total Users
            </h3>
            <p className="text-2xl md:text-3xl font-bold text-white">
              {users.length}
            </p>
          </div>
        </div>

        {/* Users Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {users.map((user) => (
            <div 
              key={user.id} 
              className="card hover:bg-gray-800 hover:border-gray-600 hover:shadow-xl transition-all duration-200 group"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h2 className="text-lg md:text-xl font-semibold text-white mb-1 group-hover:text-blue-400 transition-colors">
                    {user.name}
                  </h2>
                  <p className="text-sm text-gray-400">{user.email}</p>
                </div>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-600/20 text-green-400 border border-green-500/30">
                  Active
                </span>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors">
                  View
                </button>
                <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors">
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {users.length === 0 && (
          <div className="card text-center py-12">
            <p className="text-gray-400 text-lg">No users found</p>
            <button className="mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all hover:scale-105">
              Add User
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
```

Client Component (interactive) with modern responsive Tailwind CSS:
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        router.push('/dashboard');
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (error) {
      setError('An error occurred. Please try again.');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 px-4">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="card animate-in">
          <div className="text-center mb-8">
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
              Welcome Back
            </h1>
            <p className="text-gray-400 text-sm md:text-base">
              Sign in to your account
            </p>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-4 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-200 text-sm animate-in">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
                required
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center text-gray-400 hover:text-white cursor-pointer">
                <input 
                  type="checkbox" 
                  className="mr-2 rounded border-gray-600 bg-gray-700 focus:ring-2 focus:ring-blue-500"
                />
                Remember me
              </label>
              <a href="#" className="text-blue-400 hover:text-blue-300 transition-colors">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Signing in...</span>
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-gray-400">
            Don't have an account?{' '}
            <a href="/register" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Sign up
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Step 6: Apply Modern Tailwind CSS Styling**

**CRITICAL: ALL frontend components MUST use Tailwind CSS for styling**

Use modern, responsive Tailwind CSS patterns:

1. **Responsive Design** - Always use responsive breakpoints:
```typescript
// Mobile-first responsive design
<div className="w-full md:w-1/2 lg:w-1/3 xl:w-1/4">
  <h1 className="text-xl md:text-2xl lg:text-3xl">
  <button className="px-4 py-2 md:px-6 md:py-3">
```

2. **Modern Component Styling**:
```typescript
// Button with modern styling
<button className="btn-primary w-full md:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 active:scale-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100">

// Card with glass morphism
<div className="bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200">

// Input field
<input className="w-full px-4 py-3 bg-gray-700 text-white border border-gray-600 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-colors disabled:opacity-50" />

// Badge
<span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-600/20 text-blue-400 border border-blue-500/30">
```

3. **Layout Patterns**:
```typescript
// Container with max-width
<div className="container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl">

// Grid layout (responsive)
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">

// Flexbox layout
<div className="flex flex-col md:flex-row items-start md:items-center gap-4">

// Sticky header
<header className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-lg border-b border-gray-800">
```

4. **Color Schemes** - Use consistent color palette:
- Primary: blue-600, blue-700
- Success: green-600, green-700
- Danger: red-600, red-700
- Warning: yellow-600, yellow-700
- Background: gray-900, gray-800, gray-700
- Text: white, gray-300, gray-400, gray-500

5. **Animations & Transitions**:
```typescript
// Hover effects
<button className="transition-all duration-200 hover:scale-105 active:scale-100">

// Loading spinner
<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white">

// Fade in
<div className="animate-in fade-in duration-300">
```

6. **Tailwind Config File**:
```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
export default config
```

7. **Global Styles with Tailwind**:
```css
// app/globals.css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-900 text-gray-100;
  }
  
  /* Custom scrollbar */
  ::-webkit-scrollbar {
    @apply w-2 h-2;
  }
  
  ::-webkit-scrollbar-track {
    @apply bg-gray-800;
  }
  
  ::-webkit-scrollbar-thumb {
    @apply bg-gray-600 rounded-full hover:bg-gray-500;
  }
}

@layer components {
  .btn-primary {
    @apply px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 active:scale-100 disabled:opacity-50 disabled:cursor-not-allowed;
  }
  
  .card {
    @apply bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-xl p-6 shadow-lg;
  }
  
  .input {
    @apply w-full px-4 py-3 bg-gray-700 text-white border border-gray-600 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-colors;
  }
}
```

**Step 7: Generate Configuration Files**

```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // For Docker
  experimental: {
    serverActions: true
  }
};

module.exports = nextConfig;
```

```json
// package.json
{
  "name": "nextjs-app",
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.0.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@prisma/client": "^5.7.0", // or "mongoose": "^8.0.3"
    "typescript": "^5.3.3",
    "tailwindcss": "^3.3.6"
  },
  "devDependencies": {
    "@types/node": "^20.10.5",
    "@types/react": "^18.2.45",
    "prisma": "^5.7.0"
  }
}
```

**Important Next.js 14 Concepts:**
1. **Server Components by default** - faster, smaller bundle
2. **Client Components** - use 'use client' directive for interactivity
3. **Route Handlers** - replace API routes from Pages Router
4. **Loading and Error UI** - loading.tsx, error.tsx
5. **Layouts** - shared UI across routes
6. **Parallel Routes** - @folder syntax
7. **Intercepting Routes** - (..) syntax

**Best Practices:**
- Use Server Components when possible
- Client Components only for interactivity
- Colocate components with routes
- Use TypeScript for type safety
- Implement proper error handling
- Add loading states
- Use environment variables
- Implement proper validation

**IMPORTANT: Provide complete, working code files in JSON format**

Respond with:
{
    "reasoning": "Step-by-step analysis...",
    "code_files": [
        {
            "filename": "app/layout.tsx",
            "filepath": "app/layout.tsx",
            "content": "...",
            "description": "Root layout",
            "language": "typescript"
        },
        ...
    ],
    "file_structure": {
        "app/": ["layout.tsx", "page.tsx", ...],
        "components/": [...],
        "lib/": [...],
        "prisma/": [...] // or "models/": [...]
    },
    "setup_instructions": [
        "npm install",
        "npx prisma generate", // if PostgreSQL
        "npm run dev"
    ]
}

Generate production-ready Next.js 14 code following best practices."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Next.js 14 code files

        Args:
            task_data: Contains database_schema, requirements, description, etc.

        Returns:
            Generated code files
        """
        activity = await self.start_activity("Generating Next.js code")

        try:
            description = task_data.get("description", "")
            requirements = task_data.get("requirements", {})
            database_schema = task_data.get("database_schema", {})
            hld = task_data.get("hld", {})
            modules = task_data.get("modules", [])

            logger.info(
                "nextjs_code_generation_started",
                database_type=database_schema.get("database_type"),
                entity_count=len(database_schema.get("entities", []))
            )

            # Build comprehensive code generation prompt
            prompt = self._build_nextjs_prompt(
                description, requirements, database_schema, hld, modules
            )

            # Call LLM with higher token limit for more code
            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower for consistent code structure
                max_tokens=4000
            )

            # Parse response
            code_data = self._parse_code_response(response)

            await self.complete_activity("completed")

            logger.info(
                "nextjs_code_generation_completed",
                file_count=len(code_data.get("code_files", []))
            )

            return {
                "code_files": code_data.get("code_files", []),
                "file_structure": code_data.get("file_structure", {}),
                "setup_instructions": code_data.get("setup_instructions", []),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("nextjs_code_generation_failed", error=str(e))
            raise

    def _build_nextjs_prompt(
        self,
        description: str,
        requirements: dict,
        database_schema: dict,
        hld: dict,
        modules: list
    ) -> str:
        """Build comprehensive Next.js code generation prompt"""
        
        database_type = database_schema.get("database_type", "postgresql")
        entities = database_schema.get("entities", [])
        prisma_schema = database_schema.get("prisma_schema", "")
        mongoose_schema = database_schema.get("mongoose_schema", "")
        
        functional_reqs = requirements.get("functional", [])
        
        prompt = f"""Generate a complete Next.js 14 full-stack application:

**Application Description:**
{description}

**Database:**
- Type: {database_type}
- ORM/ODM: {"Prisma" if database_type == "postgresql" else "Mongoose"}
- Entities: {len(entities)} models

**Entities/Models:**
{self._format_entities(entities)}

**Functional Requirements:**
{self._format_list(functional_reqs)}

**Your Task:**
Generate a complete, production-ready Next.js 14 application with:

1. **App Router Structure**
   - app/layout.tsx (root layout)
   - app/page.tsx (home page)
   - app/api/[resource]/route.ts (API routes for each entity)
   - app/[pages]/page.tsx (all necessary pages)

2. **Database Layer**
   {"- lib/db.ts (Prisma client)" if database_type == "postgresql" else "- lib/db.ts (MongoDB connection)"}
   {"- prisma/schema.prisma (complete schema)" if database_type == "postgresql" else "- models/[Entity].ts (Mongoose models for each entity)"}

3. **API Routes (Route Handlers)**
   - Full CRUD for each entity
   - Proper error handling
   - Input validation
   - Status codes

4. **React Components**
   - Server Components (for data fetching)
   - Client Components (for interactivity)
   - Tailwind CSS styling
   - Reusable UI components

5. **Configuration Files**
   - next.config.js
   - tailwind.config.ts
   - tsconfig.json
   - package.json

6. **Type Safety**
   - TypeScript throughout
   - Proper types and interfaces

Generate at least 15-25 files covering:
- Complete app directory structure
- All API routes
- All pages
- Reusable components
- Database setup
- Configuration

Make it production-ready, well-structured, and following Next.js 14 best practices."""

        return prompt

    def _format_entities(self, entities: list) -> str:
        """Format entities for prompt"""
        if not entities:
            return "No specific entities defined"
        
        result = []
        for entity in entities:
            fields = ", ".join([f['name'] for f in entity.get('fields', [])])
            result.append(f"- {entity.get('name')}: {fields}")
        return "\n".join(result)

    def _format_list(self, items: list) -> str:
        """Format list for prompt"""
        if not items:
            return "None specified"
        return "\n".join([f"- {item}" for item in items])

    def _parse_code_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into code files"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            code_data = json.loads(response)

            # Ensure required fields
            if "code_files" not in code_data:
                code_data["code_files"] = []
            if "file_structure" not in code_data:
                code_data["file_structure"] = {}
            if "setup_instructions" not in code_data:
                code_data["setup_instructions"] = []

            return code_data

        except json.JSONDecodeError as e:
            logger.error("code_parse_error", error=str(e))
            
            # Fallback minimal structure
            return {
                "code_files": [
                    {
                        "filename": "README.md",
                        "filepath": "README.md",
                        "content": "# Next.js Application\n\nGenerated application structure.",
                        "description": "Project README",
                        "language": "markdown"
                    }
                ],
                "file_structure": {},
                "setup_instructions": ["npm install", "npm run dev"]
            }

