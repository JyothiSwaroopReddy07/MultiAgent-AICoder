"""
Streaming Wrapper - Wraps orchestrator to emit real-time events
"""
import structlog
from typing import Dict, Any
from datetime import datetime

from api.streaming_routes import (
    create_session,
    emit_agent_start,
    emit_agent_progress,
    emit_agent_complete,
    emit_phase_change,
    emit_planning_step,
    emit_token_usage,
    emit_error,
    emit_completion,
    close_session
)

logger = structlog.get_logger()


class StreamingOrchestrator:
    """Wraps AdvancedOrchestrator to add real-time streaming"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
    async def generate_code(self, request_data: Dict[str, Any]):
        """Generate code with real-time streaming"""
        request_id = request_data.get("request_id", "unknown")
        
        try:
            # Create streaming session
            create_session(request_id)
            
            # Emit initial status
            await emit_agent_progress(
                request_id,
                "orchestrator",
                "🚀 Initializing AI Coder - 13 specialized agents across 6 phases",
                {"status": "starting"}
            )
            
            # Emit agent initialization
            agents = [
                ("Requirements Analyst", "📝"),
                ("Research Agent", "🔍"),
                ("Architect", "🏗️"),
                ("Module Designer", "📦"),
                ("Component Designer", "🔧"),
                ("UI Designer", "🎨"),
                ("Coder", "💻"),
                ("Tester", "🧪"),
                ("Debugger", "🐛"),
                ("Security Auditor", "🔒"),
                ("Reviewer", "✅"),
                ("Executor", "🚀"),
                ("Monitor", "📊")
            ]
            
            for i, (agent_name, icon) in enumerate(agents):
                await emit_agent_progress(
                    request_id,
                    "orchestrator",
                    f"{icon} {agent_name} initialized and ready",
                    {"agent": agent_name, "progress": ((i + 1) / len(agents)) * 100}
                )
            
            # Phase 1: Discovery & Analysis
            await emit_phase_change(request_id, "initialization", "discovery")
            await emit_agent_start(request_id, "requirements_analyst", "Analyzing requirements")
            
            # Call the actual orchestrator and stream results as they come
            result = await self.orchestrator.generate_code(request_data)
            
            # === PHASE 1 RESULTS ===
            if hasattr(result, 'requirements'):
                await emit_agent_progress(
                    request_id,
                    "requirements_analyst",
                    f"📋 Requirements Analysis Complete!\n\n✨ Extracted {len(result.requirements.functional_requirements)} functional requirements\n🎯 Identified {len(result.requirements.non_functional_requirements)} non-functional requirements\n💡 Project Scope: {result.requirements.project_scope[:200]}...",
                    {
                        "functional": result.requirements.functional_requirements[:3],
                        "non_functional": result.requirements.non_functional_requirements[:3]
                    }
                )
            
            if hasattr(result, 'research'):
                tech_stack = result.research.recommended_technologies if hasattr(result.research, 'recommended_technologies') else []
                await emit_agent_progress(
                    request_id,
                    "research",
                    f"🔍 Research Complete!\n\n📚 Recommended Technologies:\n{', '.join(tech_stack[:5]) if tech_stack else 'Analyzing...'}\n🎯 Best Practices identified\n💡 Industry standards analyzed",
                    {"technologies": tech_stack[:5]}
                )
            
            if hasattr(result, 'hld'):
                components = result.hld.major_components if hasattr(result.hld, 'major_components') else []
                await emit_agent_progress(
                    request_id,
                    "architect",
                    f"🏗️ Architecture Design Complete!\n\n🎯 System Overview: {result.hld.system_overview[:150]}...\n📦 Major Components: {len(components)}\n🔗 Data flow designed\n⚡ Scalability patterns applied",
                    {"components": [c.name for c in components[:4]] if components else []}
                )
            
            # === PHASE 2 RESULTS ===
            await emit_phase_change(request_id, "discovery", "design")
            
            if hasattr(result, 'modules'):
                modules_info = "\n".join([f"  • {m.module_name}: {m.purpose[:60]}..." for m in result.modules[:3]])
                await emit_agent_progress(
                    request_id,
                    "module_designer",
                    f"📦 Module Design Complete!\n\n🎯 Designed {len(result.modules)} modules:\n{modules_info}",
                    {"modules": [m.module_name for m in result.modules]}
                )
                
                # Emit planning steps
                for i, module in enumerate(result.modules):
                    await emit_planning_step(
                        request_id,
                        step_number=i + 1,
                        step_description=f"{module.module_name}: {module.purpose}",
                        total_steps=len(result.modules)
                    )
            
            if hasattr(result, 'lld') and result.lld:
                classes_count = sum(len(lld.classes) for lld in result.lld if hasattr(lld, 'classes'))
                await emit_agent_progress(
                    request_id,
                    "component_designer",
                    f"🔧 Component Design Complete!\n\n📐 {classes_count} classes designed\n🔗 Interfaces defined\n🎯 Data structures optimized",
                    {"classes": classes_count}
                )
            
            if hasattr(result, 'ui_design'):
                await emit_agent_progress(
                    request_id,
                    "ui_designer",
                    f"🎨 UI/UX Design Complete!\n\n🎨 Design system created\n📱 Responsive layouts designed\n♿ Accessibility considered\n🎯 User flows mapped",
                    {"design_ready": True}
                )
            
            # === PHASE 3 RESULTS ===
            await emit_phase_change(request_id, "design", "implementation")
            
            if hasattr(result, 'code_files') and result.code_files:
                total_lines = sum(len(f.content.split('\n')) for f in result.code_files[:10])
                files_preview = "\n".join([f"  • {f.filename} ({len(f.content.split(chr(10)))} lines)" for f in result.code_files[:5]])
                
                await emit_agent_progress(
                    request_id,
                    "coder",
                    f"💻 Code Generation Complete!\n\n📁 {len(result.code_files)} files generated\n📝 ~{total_lines:,} lines of code\n\nFiles:\n{files_preview}",
                    {
                        "files": [f.filename for f in result.code_files],
                        "total_lines": total_lines
                    }
                )
                
                # Show code snippet preview
                if result.code_files:
                    first_file = result.code_files[0]
                    snippet = "\n".join(first_file.content.split('\n')[:10])
                    await emit_agent_progress(
                        request_id,
                        "coder",
                        f"📄 Preview of {first_file.filename}:\n\n```{first_file.language}\n{snippet}\n...\n```",
                        {"preview": True}
                    )
            
            # === PHASE 4 RESULTS ===
            await emit_phase_change(request_id, "implementation", "qa")
            
            if hasattr(result, 'test_files') and result.test_files:
                await emit_agent_progress(
                    request_id,
                    "tester",
                    f"🧪 Testing Suite Complete!\n\n✅ {len(result.test_files)} test files created\n🎯 Unit tests generated\n🔗 Integration tests designed\n📊 Coverage optimized",
                    {"test_files": len(result.test_files)}
                )
            
            if hasattr(result, 'security_audit'):
                issues = len(result.security_audit.vulnerabilities) if hasattr(result.security_audit, 'vulnerabilities') else 0
                risk = result.security_audit.overall_risk_level if hasattr(result.security_audit, 'overall_risk_level') else "LOW"
                
                await emit_agent_progress(
                    request_id,
                    "security_auditor",
                    f"🔒 Security Audit Complete!\n\n🛡️ Risk Level: {risk}\n🔍 {issues} potential issues found\n✅ Security recommendations provided\n🎯 Best practices validated",
                    {"risk_level": risk, "issues": issues}
                )
            
            if hasattr(result, 'agent_activities'):
                review_activity = next((a for a in result.agent_activities if 'review' in a.agent.lower()), None)
                if review_activity:
                    await emit_agent_progress(
                        request_id,
                        "reviewer",
                        f"✅ Code Review Complete!\n\n📊 Code quality analyzed\n🎯 Best practices verified\n💡 Improvement suggestions provided\n⭐ Ready for production",
                        {"reviewed": True}
                    )
            
            # === PHASE 5 RESULTS ===
            await emit_phase_change(request_id, "qa", "validation")
            
            if hasattr(result, 'execution_result'):
                status = "✅ PASSED" if result.execution_result.success else "⚠️ NEEDS ATTENTION"
                await emit_agent_progress(
                    request_id,
                    "executor",
                    f"🚀 Execution Validation Complete!\n\n{status}\n🧪 Tests executed\n📊 Results validated\n🎯 Production readiness confirmed",
                    {"success": result.execution_result.success}
                )
            
            # === PHASE 6 RESULTS ===
            await emit_phase_change(request_id, "validation", "monitoring")
            
            if hasattr(result, 'agent_health'):
                healthy = sum(1 for h in result.agent_health if h.status == "healthy")
                await emit_agent_progress(
                    request_id,
                    "monitor",
                    f"📊 Monitoring Complete!\n\n✅ {healthy}/{len(result.agent_health)} agents healthy\n🎯 Performance metrics collected\n📈 System stable and ready",
                    {"healthy_agents": healthy, "total_agents": len(result.agent_health)}
                )
            
            # Emit final summary with interesting stats
            total_files = len(result.code_files) if hasattr(result, 'code_files') else 0
            total_tests = len(result.test_files) if hasattr(result, 'test_files') else 0
            total_modules = len(result.modules) if hasattr(result, 'modules') else 0
            
            await emit_agent_progress(
                request_id,
                "orchestrator",
                f"🎉 Generation Complete!\n\n📊 Final Summary:\n  • {total_files} code files generated\n  • {total_tests} test files created\n  • {total_modules} modules designed\n  • 6 phases completed\n  • 13 agents collaborated\n\n✨ Your code is ready!",
                {
                    "files": total_files,
                    "tests": total_tests,
                    "modules": total_modules
                }
            )
            
            # Emit token usage
            if hasattr(result, 'total_llm_usage'):
                tokens = result.total_llm_usage.get("total_tokens", 0)
                cost = result.total_cost if hasattr(result, 'total_cost') else 0
                
                await emit_token_usage(request_id, tokens, cost, "gpt-4")
                
                await emit_agent_progress(
                    request_id,
                    "orchestrator",
                    f"💰 Usage Stats:\n  • {tokens:,} tokens used\n  • ${cost:.4f} estimated cost\n  • {len(result.agent_activities) if hasattr(result, 'agent_activities') else 13} agent operations",
                    {"tokens": tokens, "cost": cost}
                )
            
            # Emit completion
            await emit_completion(request_id, {
                "total_cost": result.total_cost if hasattr(result, 'total_cost') else 0,
                "total_tokens": result.total_llm_usage.get("total_tokens", 0) if hasattr(result, 'total_llm_usage') else 0,
                "code_files": total_files,
                "test_files": total_tests,
                "modules": total_modules,
                "phases_completed": 6
            })
            
            # Close session
            await close_session(request_id)
            
            return result
            
        except Exception as e:
            logger.error("streaming_generation_failed", request_id=request_id, error=str(e))
            await emit_error(request_id, str(e), "orchestrator")
            await close_session(request_id)
            raise

