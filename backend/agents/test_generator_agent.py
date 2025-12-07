"""
Test Generator Agent - Generates unit tests for each generated code file
Part of the Multi-Agent System with MCP Integration
"""
from typing import Dict, Any, List, Optional
import json
import os
import structlog

from agents.base_agent import BaseAgent
from models.schemas import AgentRole

logger = structlog.get_logger()


class TestGeneratorAgent(BaseAgent):
    """
    Test Generator Agent that creates unit tests for each generated code file.
    
    This agent:
    1. Analyzes each generated code file
    2. Generates a corresponding unit test file
    3. Uses Jest for testing
    
    Role in Multi-Agent System:
    - Receives generated code from CodeGeneratorAgent
    - Creates one test file per source file
    - Reports test count metrics
    """

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.INTEGRATION_TESTER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.agent_name = "TestGeneratorAgent"

    def get_system_prompt(self) -> str:
        return """You are a Unit Test Engineer. Generate unit tests for the provided code file.

## RULES
1. Generate ONLY unit tests - test functions/components in isolation
2. Mock all external dependencies (API calls, database, imports from other files)
3. Use Jest for testing
4. Use React Testing Library for React components
5. NO COMMENTS in the test code
6. Test the main functionality of the file
7. Include tests for success cases and error cases

## TEST STRUCTURE

For utility/hook files:
```typescript
import { functionName } from './filename'

describe('functionName', () => {
  it('should do something', () => {
    const result = functionName(input)
    expect(result).toBe(expected)
  })
})
```

For React components:
```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import ComponentName from './ComponentName'

describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />)
    expect(screen.getByText('...')).toBeInTheDocument()
  })
})
```

For API routes:
```typescript
import { GET, POST } from './route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/db', () => ({
  query: jest.fn()
}))

describe('API Route', () => {
  it('should return data', async () => {
    const response = await GET()
    expect(response.status).toBe(200)
  })
})
```

## RESPONSE FORMAT

Return ONLY the test file content as plain code. No JSON, no markdown code blocks.
Start directly with import statements.
"""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a test generation task."""
        files = task_data.get("files", [])
        architecture = task_data.get("architecture", {})
        problem_statement = task_data.get("problem_statement", "")
        
        return await self.generate_tests(files, architecture, problem_statement)

    async def generate_tests(
        self,
        generated_files: List[Dict[str, Any]],
        architecture: Dict[str, Any],
        problem_statement: str
    ) -> Dict[str, Any]:
        """Generate unit tests for each testable file"""
        activity = await self.start_activity("Generating unit tests")
        
        try:
            testable_files = self._get_testable_files(generated_files)
            
            logger.info(
                "unit_test_generation_started",
                agent=self.agent_name,
                testable_files=len(testable_files)
            )
            
            test_files = []
            
            for source_file in testable_files:
                try:
                    test_file = await self._generate_unit_test(source_file)
                    if test_file:
                        test_files.append(test_file)
                except Exception as e:
                    logger.warning(
                        "unit_test_generation_failed",
                        file=source_file.get("filepath"),
                        error=str(e)
                    )
                    continue
            
            config_files = self._generate_test_config()
            package_updates = self.get_package_json_updates()
            
            # Update package.json in generated_files if it exists
            updated_files = self._update_package_json(generated_files, package_updates)
            
            await self.complete_activity("completed")
            
            logger.info(
                "unit_test_generation_completed",
                agent=self.agent_name,
                test_files_generated=len(test_files)
            )
            
            return {
                "test_files": test_files,
                "config_files": config_files,
                "updated_files": updated_files,
                "package_updates": package_updates,
                "summary": {
                    "total_test_files": len(test_files),
                    "source_files_tested": len(testable_files),
                    "test_type": "unit"
                },
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("unit_test_generation_failed", agent=self.agent_name, error=str(e))
            raise
    
    def _update_package_json(
        self,
        files: List[Dict[str, Any]],
        updates: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update package.json with Jest dependencies and test script"""
        import json
        
        updated_files = []
        
        for f in files:
            if f.get("filepath") == "package.json":
                try:
                    content = f.get("content", "{}")
                    pkg = json.loads(content)
                    
                    # Update scripts
                    if "scripts" not in pkg:
                        pkg["scripts"] = {}
                    pkg["scripts"]["test"] = updates["scripts"]["test"]
                    pkg["scripts"]["test:watch"] = updates["scripts"]["test:watch"]
                    pkg["scripts"]["test:coverage"] = updates["scripts"]["test:coverage"]
                    
                    # Update devDependencies
                    if "devDependencies" not in pkg:
                        pkg["devDependencies"] = {}
                    for dep, version in updates["devDependencies"].items():
                        if dep not in pkg["devDependencies"]:
                            pkg["devDependencies"][dep] = version
                    
                    updated_file = {
                        **f,
                        "content": json.dumps(pkg, indent=2)
                    }
                    updated_files.append(updated_file)
                    
                    logger.info("package_json_updated_with_jest", 
                              scripts=list(updates["scripts"].keys()),
                              deps=list(updates["devDependencies"].keys()))
                except json.JSONDecodeError as e:
                    logger.warning("package_json_parse_error", error=str(e))
                    updated_files.append(f)
            else:
                updated_files.append(f)
        
        return updated_files
            
        except Exception as e:
            await self.complete_activity("failed")
            logger.error("unit_test_generation_failed", agent=self.agent_name, error=str(e))
            raise

    def _get_testable_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get files that should have unit tests"""
        testable = []
        
        skip_patterns = [
            "package.json", "tsconfig", ".css", ".md", ".sql",
            "tailwind", "postcss", "next.config", ".env", ".gitignore",
            "dockerfile", "docker-compose", ".dockerignore", "layout.tsx",
            "globals.css", "jest.config", "jest.setup", ".test.", ".spec."
        ]
        
        for f in files:
            filepath = f.get("filepath", "").lower()
            
            if any(pattern in filepath for pattern in skip_patterns):
                continue
            
            if filepath.endswith(".ts") or filepath.endswith(".tsx"):
                if f.get("content", "").strip():
                    testable.append(f)
        
        return testable

    async def _generate_unit_test(self, source_file: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a unit test for a single source file"""
        filepath = source_file.get("filepath", "")
        filename = source_file.get("filename", "")
        content = source_file.get("content", "")
        
        if not content.strip():
            return None
        
        test_filepath = self._get_test_filepath(filepath)
        test_filename = os.path.basename(test_filepath)
        
        prompt = f"""Generate unit tests for this file:

## File: {filepath}

```typescript
{content[:3000]}
```

## Instructions
1. Create unit tests that test the main exports
2. Mock ALL external imports (database, other components, API calls)
3. Test both success and error scenarios
4. Use Jest and React Testing Library
5. NO COMMENTS in the code

Generate the complete test file. Return ONLY the code, no markdown."""

        response = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        
        test_content = self._clean_response(response)
        
        if not test_content.strip():
            return None
        
        return {
            "filepath": test_filepath,
            "filename": test_filename,
            "content": test_content,
            "language": "typescript",
            "category": "test",
            "test_type": "unit",
            "tests_for": filepath
        }

    def _get_test_filepath(self, source_path: str) -> str:
        """Convert source path to test path"""
        dir_name = os.path.dirname(source_path)
        base_name = os.path.basename(source_path)
        
        name, ext = os.path.splitext(base_name)
        test_name = f"{name}.test{ext}"
        
        if dir_name:
            return f"__tests__/{dir_name}/{test_name}"
        return f"__tests__/{test_name}"

    def _clean_response(self, response: str) -> str:
        """Clean LLM response to get pure code"""
        content = response.strip()
        
        if content.startswith("```typescript"):
            content = content[13:]
        elif content.startswith("```tsx"):
            content = content[6:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        return content.strip()

    def _generate_test_config(self) -> List[Dict[str, Any]]:
        """Generate Jest configuration files"""
        
        jest_config = {
            "filepath": "jest.config.js",
            "filename": "jest.config.js",
            "content": """const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/.next/'],
  testMatch: ['**/__tests__/**/*.test.[jt]s?(x)'],
}

module.exports = createJestConfig(customJestConfig)
""",
            "language": "javascript",
            "category": "config"
        }
        
        jest_setup = {
            "filepath": "jest.setup.js",
            "filename": "jest.setup.js",
            "content": """import '@testing-library/jest-dom'

global.fetch = jest.fn()

jest.mock('@/lib/db', () => ({
  query: jest.fn(),
  default: { query: jest.fn() }
}))

beforeEach(() => {
  jest.clearAllMocks()
})
""",
            "language": "javascript",
            "category": "config"
        }
        
        return [jest_config, jest_setup]
    
    def get_package_json_updates(self) -> Dict[str, Any]:
        """Return the necessary package.json updates for Jest testing"""
        return {
            "scripts": {
                "test": "jest",
                "test:watch": "jest --watch",
                "test:coverage": "jest --coverage"
            },
            "devDependencies": {
                "jest": "^29.7.0",
                "jest-environment-jsdom": "^29.7.0",
                "@testing-library/react": "^14.1.0",
                "@testing-library/jest-dom": "^6.1.0",
                "@types/jest": "^29.5.0"
            }
        }


class TestReportAgent(BaseAgent):
    """Simple test report generator"""

    def __init__(self, mcp_server=None, openai_client=None):
        super().__init__(
            role=AgentRole.INTEGRATION_TESTER,
            mcp_server=mcp_server,
            openai_client=openai_client
        )
        self.agent_name = "TestReportAgent"

    def get_system_prompt(self) -> str:
        return """You are a Test Report Generator."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        test_files = task_data.get("test_files", [])
        return self.generate_report(test_files)

    def generate_report(self, test_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "total_test_files": len(test_files),
            "files_tested": [f.get("tests_for", f.get("filepath")) for f in test_files]
        }
