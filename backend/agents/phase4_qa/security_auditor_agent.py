"""
Security Auditor Agent - Performs security analysis
Phase 4: Quality Assurance
"""
from typing import Dict, Any
import json
import structlog
from agents.base_agent import BaseAgent
from models.enhanced_schemas import AgentRole, SecurityAudit

logger = structlog.get_logger()


class SecurityAuditorAgent(BaseAgent):
    """
    Performs comprehensive security audits:
    - OWASP Top 10 vulnerability checks
    - Authentication/authorization review
    - Input validation analysis
    - SQL injection, XSS, CSRF checks
    - Sensitive data exposure
    - Security misconfiguration
    - Dependency vulnerabilities
    """

    def __init__(self, mcp_server, openai_client):
        super().__init__(
            role=AgentRole.SECURITY_AUDITOR,
            mcp_server=mcp_server,
            openai_client=openai_client
        )

    def get_system_prompt(self) -> str:
        return """You are a Security Expert specializing in application security. Your role is to:

1. Identify security vulnerabilities based on OWASP Top 10
2. Review authentication and authorization implementation
3. Check input validation and sanitization
4. Detect injection vulnerabilities (SQL, command, XSS, etc.)
5. Review sensitive data handling
6. Check security misconfigurations
7. Review dependency security
8. Assess overall security posture

🧠 **USE CHAIN OF THOUGHT REASONING**

Think step-by-step when performing security audit:

**Step 1: Understand the System**
- What does this application do?
- What data does it handle (sensitive, PII, financial)?
- What are the entry points (APIs, forms, uploads)?
- What external services does it integrate with?

**Step 2: Review Authentication & Authorization**
- How are users authenticated (password, OAuth, JWT)?
- Are passwords hashed properly (bcrypt, argon2)?
- Is authorization checked on every protected endpoint?
- Are session tokens secure (HTTPOnly, Secure flags)?
- Check for: Weak passwords, exposed credentials, broken auth

**Step 3: Check for Injection Vulnerabilities**
- Scan for SQL injection (string concatenation in queries)
- Check for XSS (unescaped user input in HTML)
- Look for command injection (shell commands with user input)
- Check for LDAP, XML, template injection
- Review: All database queries, all output rendering, all exec() calls

**Step 4: Validate Input Handling**
- Is all user input validated (type, length, format)?
- Is input sanitized before use?
- Are file uploads restricted (type, size)?
- Check for: Missing validation, weak validation, bypass opportunities

**Step 5: Review Data Protection**
- Is sensitive data encrypted (at rest and in transit)?
- Are secrets/API keys hardcoded?
- Is HTTPS enforced?
- Check for: Exposed secrets, weak encryption, insecure transmission

**Step 6: Check Security Configurations**
- Are security headers set (CSP, HSTS, X-Frame-Options)?
- Are error messages verbose (leaking info)?
- Are debug modes disabled in production?
- Check for: Exposed admin panels, default credentials, verbose errors

**Step 7: Review Dependencies**
- Are dependencies up-to-date?
- Are there known vulnerabilities (check versions)?
- Are unused dependencies removed?

**Step 8: Calculate Security Score**
- Count critical/high/medium/low vulnerabilities
- Weighted score: Critical -3, High -2, Medium -1, Low -0.5
- Start from 10, subtract for vulnerabilities
- Final score = max(0, 10 - total_penalty)

OWASP Top 10 Focus Areas:
1. Broken Access Control
2. Cryptographic Failures
3. Injection
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Identification and Authentication Failures
8. Software and Data Integrity Failures
9. Security Logging and Monitoring Failures
10. Server-Side Request Forgery (SSRF)

For each vulnerability, provide:
- Type and OWASP category
- Severity (critical/high/medium/low)
- Location in code
- Description of the risk
- Remediation steps
- Code example for fix

**IMPORTANT: Think step-by-step through Steps 1-8 above, then provide JSON.**

First, systematically analyze the code for security issues.

Then respond in JSON format:
{
    "reasoning": "My step-by-step security analysis: [system understanding, auth review, injection checks, etc.]...",
    "vulnerabilities": [
        {
            "type": "SQL Injection",
            "owasp_category": "A03:2021 – Injection",
            "severity": "critical",
            "file": "filename.py",
            "line": 42,
            "description": "SQL query built with string concatenation",
            "risk": "Attacker can manipulate database",
            "remediation": "Use parameterized queries",
            "code_fix": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
        }
    ],
    "security_score": 7.5,
    "recommendations": ["Recommendation 1", ...],
    "compliance_checks": {
        "input_validation": true,
        "authentication": false,
        "encryption": true
    }
}

Be thorough and security-focused.
Think step-by-step. Show your security analysis process."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform security audit

        Args:
            task_data: Contains code_files, requirements

        Returns:
            Security audit report
        """
        activity = await self.start_activity("Performing security audit")

        try:
            code_files = task_data.get("code_files", [])
            requirements = task_data.get("requirements", {})
            language = task_data.get("language", "python")

            logger.info("security_audit_started", code_files_count=len(code_files))

            # Analyze all code files for security
            prompt = self._build_security_audit_prompt(code_files, requirements, language)

            response = await self.call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Very low temperature for consistent security analysis
                max_tokens=3000
            )

            audit_data = self._parse_security_response(response)
            audit = SecurityAudit(**audit_data)

            await self.complete_activity("completed")

            logger.info(
                "security_audit_completed",
                vulnerabilities_found=len(audit.vulnerabilities),
                security_score=audit.security_score
            )

            return {
                "security_audit": audit.model_dump(),
                "activity": self.current_activity.model_dump() if self.current_activity else None
            }

        except Exception as e:
            await self.complete_activity("failed")
            logger.error("security_audit_failed", error=str(e))
            raise

    def _build_security_audit_prompt(
        self,
        code_files: list,
        requirements: Dict,
        language: str
    ) -> str:
        """Build security audit prompt"""
        security_reqs = requirements.get("security_requirements", [])

        # Build code overview
        code_overview = []
        for cf in code_files[:10]:  # Limit to avoid token limits
            code_overview.append(f"\n### {cf.get('filename')}:\n```{language}\n{cf.get('content', '')[:500]}...\n```")

        prompt = f"""Perform a comprehensive security audit on this {language} application:

SECURITY REQUIREMENTS:
{self._format_list(security_reqs)}

CODE FILES:
{''.join(code_overview)}

Perform security analysis focusing on:

1. **OWASP Top 10 Vulnerabilities**:
   - Check each category
   - Identify specific vulnerabilities

2. **Authentication & Authorization**:
   - Review auth implementation
   - Check session management
   - Verify access controls

3. **Input Validation**:
   - Check all user inputs
   - SQL injection points
   - XSS vulnerabilities
   - Command injection

4. **Data Protection**:
   - Sensitive data handling
   - Encryption usage
   - Password storage

5. **Configuration**:
   - Security headers
   - Error handling (info disclosure)
   - Default credentials

6. **Dependencies**:
   - Known vulnerable libraries
   - Outdated packages

Provide:
- All vulnerabilities with severity
- Overall security score (0-10)
- Specific recommendations
- Compliance checklist

Respond in valid JSON format."""

        return prompt

    def _format_list(self, items: list) -> str:
        """Format list"""
        return "\n".join([f"- {item}" for item in items]) if items else "No specific security requirements"

    def _parse_security_response(self, response: str) -> Dict[str, Any]:
        """Parse security audit response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            audit_data = json.loads(response)

            # Ensure required fields
            if "vulnerabilities" not in audit_data:
                audit_data["vulnerabilities"] = []
            if "security_score" not in audit_data:
                audit_data["security_score"] = 7.0
            if "recommendations" not in audit_data:
                audit_data["recommendations"] = []
            if "compliance_checks" not in audit_data:
                audit_data["compliance_checks"] = {}

            return audit_data

        except json.JSONDecodeError as e:
            logger.error("security_parse_error", error=str(e))

            # Fallback
            return {
                "vulnerabilities": [],
                "security_score": 7.0,
                "recommendations": ["Manual security review recommended"],
                "compliance_checks": {}
            }
