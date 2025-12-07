"""
Application Execution Service
Saves generated code to disk and executes it in a sandboxed environment
"""

import asyncio
import os
import shutil
import signal
import subprocess
import tempfile
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import structlog

logger = structlog.get_logger()

# Track running processes
running_processes: Dict[str, subprocess.Popen] = {}
running_ports: Dict[str, int] = {}

# Base port for generated apps (will increment for each app)
BASE_PORT = 3001


def get_next_available_port() -> int:
    """Find the next available port starting from BASE_PORT"""
    import socket
    
    port = BASE_PORT
    while port < BASE_PORT + 100:  # Try up to 100 ports
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                port += 1
    
    raise RuntimeError("No available ports found")


async def save_files_to_disk(files: List[Dict[str, Any]], base_path: str) -> None:
    """Save generated files to disk"""
    for file_data in files:
        filepath = file_data.get("filepath", "")
        content = file_data.get("content", "")
        
        if not filepath or not content:
            continue
        
        # Create full path
        full_path = os.path.join(base_path, filepath)
        
        # Create directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("file_saved", filepath=filepath)


def detect_project_type(files: List[Dict[str, Any]]) -> str:
    """Detect the type of project from the files"""
    filepaths = [f.get("filepath", "") for f in files]
    
    # Check for Next.js
    if any("next.config" in fp for fp in filepaths) or any("pages/" in fp or "app/" in fp for fp in filepaths):
        return "nextjs"
    
    # Check for React (Create React App)
    if any("package.json" in fp for fp in filepaths):
        for f in files:
            if f.get("filepath") == "package.json":
                try:
                    pkg = json.loads(f.get("content", "{}"))
                    deps = pkg.get("dependencies", {})
                    if "next" in deps:
                        return "nextjs"
                    if "react-scripts" in deps:
                        return "cra"
                    if "react" in deps:
                        return "react-vite"
                except:
                    pass
    
    # Check for plain HTML
    if any(fp.endswith(".html") for fp in filepaths):
        return "static"
    
    # Check for Python
    if any(fp.endswith(".py") for fp in filepaths):
        if any("requirements.txt" in fp for fp in filepaths):
            return "python"
        if any("main.py" in fp or "app.py" in fp for fp in filepaths):
            return "python"
    
    return "unknown"


async def execute_application(
    files: List[Dict[str, Any]],
    conversation_id: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Execute the generated application
    
    This will:
    1. Save files to a temporary directory
    2. Install dependencies
    3. Start the development server
    4. Stream logs and status back
    """
    project_type = detect_project_type(files)
    port = get_next_available_port()
    
    # Create project directory
    base_dir = os.path.join(tempfile.gettempdir(), "ai-generated-apps")
    os.makedirs(base_dir, exist_ok=True)
    
    project_dir = os.path.join(base_dir, f"app_{conversation_id[:8]}_{port}")
    
    # Clean up existing directory if it exists
    if os.path.exists(project_dir):
        # Stop any running process first
        if project_dir in running_processes:
            try:
                running_processes[project_dir].terminate()
                await asyncio.sleep(1)
            except:
                pass
            del running_processes[project_dir]
        
        shutil.rmtree(project_dir)
    
    os.makedirs(project_dir, exist_ok=True)
    
    yield {
        "type": "log",
        "message": f"📁 Created project directory: {project_dir}"
    }
    
    # Save files
    yield {
        "type": "log",
        "message": f"💾 Saving {len(files)} files..."
    }
    
    await save_files_to_disk(files, project_dir)
    
    yield {
        "type": "log",
        "message": f"✅ All files saved successfully"
    }
    
    # Handle different project types
    if project_type in ["nextjs", "react-vite", "cra"]:
        async for event in execute_node_project(project_dir, project_type, port, conversation_id):
            yield event
    
    elif project_type == "python":
        async for event in execute_python_project(project_dir, port, conversation_id):
            yield event
    
    elif project_type == "static":
        async for event in serve_static_files(project_dir, port, conversation_id):
            yield event
    
    else:
        # Try to detect and run anyway
        if os.path.exists(os.path.join(project_dir, "package.json")):
            async for event in execute_node_project(project_dir, "nextjs", port, conversation_id):
                yield event
        else:
            yield {
                "type": "error",
                "message": f"Unknown project type. Could not determine how to run the application."
            }


async def execute_node_project(
    project_dir: str,
    project_type: str,
    port: int,
    conversation_id: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute a Node.js project (Next.js, React, etc.)"""
    
    yield {
        "type": "log",
        "message": f"📦 Installing dependencies (this may take a minute)..."
    }
    
    # Install dependencies
    try:
        # Optimize npm install with flags
        install_process = await asyncio.create_subprocess_exec(
            "npm", "install", "--legacy-peer-deps", "--no-audit", "--no-fund", "--prefer-offline",
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            install_process.communicate(),
            timeout=300  # 5 minute timeout
        )
        
        if install_process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error during npm install"
            yield {
                "type": "log",
                "message": f"⚠️ npm install warnings: {error_msg[:500]}"
            }
        
        yield {
            "type": "log",
            "message": "✅ Dependencies installed"
        }
        
    except asyncio.TimeoutError:
        yield {
            "type": "error",
            "message": "npm install timed out after 5 minutes"
        }
        return
    except Exception as e:
        yield {
            "type": "error",
            "message": f"Failed to install dependencies: {str(e)}"
        }
        return
    
    # Determine start command based on project type
    # Use -H 0.0.0.0 to bind to all interfaces (needed for Docker)
    if project_type == "nextjs":
        cmd = ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", str(port)]
    elif project_type == "cra":
        cmd = ["npm", "start"]
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = "0.0.0.0"
        env["BROWSER"] = "none"
    else:
        cmd = ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(port)]
    
    yield {
        "type": "log",
        "message": f"🚀 Starting development server on port {port}..."
    }
    
    # Start the dev server
    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = "0.0.0.0"
        env["HOSTNAME"] = "0.0.0.0"
        env["BROWSER"] = "none"
        
        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        running_processes[project_dir] = process
        running_ports[project_dir] = port
        
        # Wait for server to be ready (check for specific output or port)
        url = f"http://localhost:{port}"
        ready = False
        start_time = asyncio.get_event_loop().time()
        timeout = 60  # 60 second timeout
        
        while not ready and (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check if process is still running
            if process.poll() is not None:
                output = process.stdout.read().decode() if process.stdout else ""
                yield {
                    "type": "error",
                    "message": f"Process exited unexpectedly: {output[:500]}"
                }
                return
            
            # Try to connect to the server
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.settimeout(1)
                    s.connect(('localhost', port))
                    ready = True
                except:
                    await asyncio.sleep(1)
        
        if ready:
            yield {
                "type": "started",
                "url": url,
                "port": port,
                "project_path": project_dir,
                "message": f"Application running at {url}"
            }
        else:
            yield {
                "type": "error",
                "message": "Server failed to start within 60 seconds"
            }
            
    except Exception as e:
        yield {
            "type": "error",
            "message": f"Failed to start server: {str(e)}"
        }


async def execute_python_project(
    project_dir: str,
    port: int,
    conversation_id: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute a Python project"""
    
    requirements_file = os.path.join(project_dir, "requirements.txt")
    
    if os.path.exists(requirements_file):
        yield {
            "type": "log",
            "message": "📦 Installing Python dependencies..."
        }
        
        try:
            install_process = await asyncio.create_subprocess_exec(
                "pip", "install", "-r", "requirements.txt",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(
                install_process.communicate(),
                timeout=120
            )
            
            yield {
                "type": "log",
                "message": "✅ Python dependencies installed"
            }
            
        except Exception as e:
            yield {
                "type": "log",
                "message": f"⚠️ Warning: {str(e)}"
            }
    
    # Find main Python file
    main_file = None
    for name in ["main.py", "app.py", "server.py", "run.py"]:
        if os.path.exists(os.path.join(project_dir, name)):
            main_file = name
            break
    
    if not main_file:
        yield {
            "type": "error",
            "message": "Could not find main Python file (main.py, app.py, server.py, or run.py)"
        }
        return
    
    yield {
        "type": "log",
        "message": f"🚀 Starting Python server on port {port}..."
    }
    
    try:
        env = os.environ.copy()
        env["PORT"] = str(port)
        
        process = subprocess.Popen(
            ["python", main_file],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        running_processes[project_dir] = process
        running_ports[project_dir] = port
        
        # Wait for server to be ready
        url = f"http://localhost:{port}"
        await asyncio.sleep(3)  # Give Python server time to start
        
        if process.poll() is None:
            yield {
                "type": "started",
                "url": url,
                "port": port,
                "project_path": project_dir,
                "message": f"Python application running at {url}"
            }
        else:
            output = process.stdout.read().decode() if process.stdout else ""
            yield {
                "type": "error",
                "message": f"Python server exited: {output[:500]}"
            }
            
    except Exception as e:
        yield {
            "type": "error",
            "message": f"Failed to start Python server: {str(e)}"
        }


async def serve_static_files(
    project_dir: str,
    port: int,
    conversation_id: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """Serve static HTML files using Python's http.server"""
    
    yield {
        "type": "log",
        "message": f"🌐 Starting static file server on port {port}..."
    }
    
    try:
        process = subprocess.Popen(
            ["python", "-m", "http.server", str(port)],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        running_processes[project_dir] = process
        running_ports[project_dir] = port
        
        await asyncio.sleep(1)
        
        url = f"http://localhost:{port}"
        
        if process.poll() is None:
            yield {
                "type": "started",
                "url": url,
                "port": port,
                "project_path": project_dir,
                "message": f"Static server running at {url}"
            }
        else:
            yield {
                "type": "error",
                "message": "Failed to start static server"
            }
            
    except Exception as e:
        yield {
            "type": "error",
            "message": f"Failed to start static server: {str(e)}"
        }


async def stop_application(project_path: str) -> bool:
    """Stop a running application"""
    if project_path in running_processes:
        process = running_processes[project_path]
        
        try:
            if os.name != 'nt':
                # Kill the entire process group on Unix
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
            
            await asyncio.sleep(1)
            
            if process.poll() is None:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
            
            del running_processes[project_path]
            if project_path in running_ports:
                del running_ports[project_path]
            
            logger.info("application_stopped", project_path=project_path)
            return True
            
        except Exception as e:
            logger.error("failed_to_stop_application", error=str(e))
            return False
    
    return False


def get_running_applications() -> List[Dict[str, Any]]:
    """Get list of all running applications"""
    apps = []
    
    for project_path, process in running_processes.items():
        if process.poll() is None:  # Still running
            port = running_ports.get(project_path)
            apps.append({
                "project_path": project_path,
                "port": port,
                "url": f"http://localhost:{port}" if port else None,
                "pid": process.pid
            })
    
    return apps


async def cleanup_all_applications() -> None:
    """Stop all running applications (for cleanup on shutdown)"""
    for project_path in list(running_processes.keys()):
        await stop_application(project_path)

