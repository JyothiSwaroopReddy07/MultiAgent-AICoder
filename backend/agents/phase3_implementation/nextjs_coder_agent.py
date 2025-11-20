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

🧠 **USE CHAIN OF THOUGHT REASONING**

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

**Step 5: Generate React Components**

Server Component (default):
```typescript
// app/dashboard/page.tsx
import { prisma } from '@/lib/db';

export default async function DashboardPage() {
  const users = await prisma.user.findMany({
    take: 10
  });
  
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <div className="grid gap-4">
        {users.map((user) => (
          <div key={user.id} className="p-4 border rounded-lg">
            <h2 className="font-semibold">{user.name}</h2>
            <p className="text-gray-600">{user.email}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Client Component (interactive):
```typescript
'use client';

import { useState } from 'react';

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      if (res.ok) {
        // Handle success
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full px-4 py-2 border rounded-lg"
        placeholder="Email"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full px-4 py-2 border rounded-lg"
        placeholder="Password"
      />
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Loading...' : 'Login'}
      </button>
    </form>
  );
}
```

**Step 6: Generate Configuration Files**

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

