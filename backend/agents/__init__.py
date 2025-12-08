"""
AI Code Generator - Enterprise Multi-Agent System with MCP Integration

This module contains the core agents for code generation using Model Context Protocol:

Agent Pipeline:
1. FeaturePlannerAgent: Proposes features and gets user confirmation
2. ArchitectAgent: Designs system architecture and determines project structure
3. FilePlannerAgent: Plans all files needed for the project
4. CodeGeneratorAgent: Generates production-ready code files
5. IntegrationValidatorAgent: Validates all generated files work together
6. TestGeneratorAgent: Generates comprehensive test cases
7. TestingAgent: Tests generated code and fixes errors
8. ExecutionAgent: Executes applications and auto-fixes runtime errors

Supporting Classes:
- BaseAgent: Abstract base class for all agents
- DependencyValidator: Validates all file dependencies are satisfied
- TestReportAgent: Generates test coverage reports

MCP Integration:
- Agents communicate via Model Context Protocol for coordinated generation
- Each agent tracks its own LLM usage for transparency
- Sequential pipeline with parallel file generation
"""

from agents.base_agent import BaseAgent
from agents.architect_agent import ArchitectAgent, FilePlannerAgent
from agents.code_generator_agent import CodeGeneratorAgent, IntegrationValidatorAgent
from agents.feature_planner_agent import FeaturePlannerAgent
from agents.testing_agent import TestingAgent, DependencyValidator
from agents.test_generator_agent import TestGeneratorAgent, TestReportAgent
from agents.code_reviewer_agent import CodeReviewerAgent
from agents.validation_pipeline_agent import ValidationPipelineAgent

__all__ = [
    "BaseAgent",
    "FeaturePlannerAgent",
    "ArchitectAgent",
    "FilePlannerAgent", 
    "CodeGeneratorAgent",
    "CodeReviewerAgent",
    "IntegrationValidatorAgent",
    "TestGeneratorAgent",
    "TestReportAgent",
    "TestingAgent",
    "DependencyValidator",
    "ValidationPipelineAgent"
]
