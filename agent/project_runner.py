"""
Project runner for the AI Code Agent.
Runs projects, takes screenshots, analyzes them, and makes fixes.
"""
import logging
import os
import subprocess
import time
import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from rich.console import Console
from rich.panel import Panel

from agent.screenshot_utils import ScreenshotManager
from agent.retry_mechanism import RetryManager
from agent.consolidated_log import ConsolidatedLogManager
from models.ai_client_factory import AIClientFactory
from config import (
    ENABLE_SCREENSHOTS, OPERATION_MAX_RETRIES, OPERATION_RETRY_DELAY,
    OPERATION_BACKOFF_FACTOR, SCREENSHOT_INTERVAL, SCREENSHOT_MONITOR_DURATION
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize console
console = Console()

class ProjectRunner:
    """
    Runs projects, takes screenshots, analyzes them, and makes fixes.
    """
    
    def __init__(self, project_dir: Union[str, Path], log_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the project runner.
        
        Args:
            project_dir: Path to the project directory
            log_dir: Directory to save logs (default: project_dir/logs)
        """
        self.project_dir = Path(project_dir)
        self.log_dir = Path(log_dir) if log_dir else self.project_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize utilities
        self.screenshot_manager = ScreenshotManager()
        self.retry_manager = RetryManager(
            max_retries=OPERATION_MAX_RETRIES,
            initial_delay=OPERATION_RETRY_DELAY,
            backoff_factor=OPERATION_BACKOFF_FACTOR
        )
        self.consolidated_log = ConsolidatedLogManager(self.log_dir)
        
        # Initialize multimodal AI client
        self.ai_client = AIClientFactory.create_multimodal_client()
        
        # Process tracking
        self.current_process = None
        self.process_info = {}
        
    def detect_project_type(self) -> str:
        """
        Detect the type of project.
        
        Returns:
            Project type (web, python, node, etc.)
        """
        # Check for package.json (Node.js project)
        if (self.project_dir / "package.json").exists():
            return "node"
            
        # Check for requirements.txt or setup.py (Python project)
        if (self.project_dir / "requirements.txt").exists() or (self.project_dir / "setup.py").exists():
            return "python"
            
        # Check for pom.xml or build.gradle (Java project)
        if (self.project_dir / "pom.xml").exists() or (self.project_dir / "build.gradle").exists():
            return "java"
            
        # Check for index.html (Web project)
        if (self.project_dir / "index.html").exists() or list(self.project_dir.glob("**/index.html")):
            return "web"
            
        # Default to unknown
        return "unknown"
        
    def get_run_command(self, project_type: Optional[str] = None) -> str:
        """
        Get the command to run the project.
        
        Args:
            project_type: Type of project (if None, will be detected)
            
        Returns:
            Command to run the project
        """
        if project_type is None:
            project_type = self.detect_project_type()
            
        # Check for npm scripts in package.json
        if project_type == "node":
            package_json_path = self.project_dir / "package.json"
            if package_json_path.exists():
                try:
                    import json
                    with open(package_json_path, 'r') as f:
                        package_data = json.load(f)
                        
                    # Check for start script
                    if "scripts" in package_data and "start" in package_data["scripts"]:
                        return "npm start"
                    elif "scripts" in package_data and "dev" in package_data["scripts"]:
                        return "npm run dev"
                except Exception as e:
                    logger.error(f"Error parsing package.json: {e}")
                    
            # Check for specific frameworks
            if (self.project_dir / "angular.json").exists():
                return "ng serve"
            elif (self.project_dir / "next.config.js").exists():
                return "npx next dev"
            elif (self.project_dir / "vite.config.js").exists() or (self.project_dir / "vite.config.ts").exists():
                return "npx vite"
                
            # Default npm command
            return "npm start"
            
        # Python projects
        elif project_type == "python":
            # Check for Flask app
            for file in self.project_dir.glob("**/*.py"):
                with open(file, 'r') as f:
                    content = f.read()
                    if "Flask(__name__)" in content:
                        return f"python {file.relative_to(self.project_dir)}"
                        
            # Check for Django project
            if (self.project_dir / "manage.py").exists():
                return "python manage.py runserver"
                
            # Check for FastAPI
            for file in self.project_dir.glob("**/*.py"):
                with open(file, 'r') as f:
                    content = f.read()
                    if "FastAPI(" in content:
                        return f"uvicorn {file.stem}:app --reload"
                        
            # Default to main.py or app.py
            if (self.project_dir / "main.py").exists():
                return "python main.py"
            elif (self.project_dir / "app.py").exists():
                return "python app.py"
                
        # Web projects
        elif project_type == "web":
            # Check for index.html
            index_html = list(self.project_dir.glob("**/index.html"))
            if index_html:
                # Use a simple HTTP server
                return f"python -m http.server 8000 -d {self.project_dir}"
                
        # Default command
        return ""
        
    def run_project(self, command: Optional[str] = None) -> Dict:
        """
        Run the project.
        
        Args:
            command: Command to run the project (if None, will be detected)
            
        Returns:
            Dictionary with run results
        """
        if command is None:
            command = self.get_run_command()
            
        if not command:
            return {
                "success": False,
                "error": "Could not determine how to run the project"
            }
            
        console.print(f"[bold yellow]Running project with command:[/bold yellow] {command}")
        self.consolidated_log.log_section("Run Project", f"Running project with command: {command}")
        
        try:
            # Kill any existing process
            self.stop_project()
            
            # Start the process
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.current_process = process
            self.process_info = {
                "command": command,
                "pid": process.pid,
                "start_time": time.time()
            }
            
            # Wait a bit for the process to start
            time.sleep(3)
            
            # Check if the process is still running
            if process.poll() is not None:
                # Process has already terminated
                stdout, stderr = process.communicate()
                return {
                    "success": False,
                    "error": f"Process terminated with exit code {process.returncode}",
                    "stdout": stdout,
                    "stderr": stderr
                }
                
            # Take a screenshot
            if ENABLE_SCREENSHOTS:
                screenshot_result = self.screenshot_manager.capture_screenshot("project_running")
                if screenshot_result[0]:
                    self.consolidated_log.log_message(f"Screenshot saved to: {screenshot_result[1]}")
                    
            return {
                "success": True,
                "process": process,
                "command": command,
                "pid": process.pid
            }
            
        except Exception as e:
            logger.error(f"Error running project: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def stop_project(self) -> Dict:
        """
        Stop the running project.
        
        Returns:
            Dictionary with stop results
        """
        if self.current_process is None:
            return {
                "success": True,
                "message": "No process to stop"
            }
            
        try:
            # Try to terminate gracefully
            if self.current_process.poll() is None:
                # On Windows, we need to use taskkill to kill the process tree
                if os.name == 'nt':
                    subprocess.run(f"taskkill /F /T /PID {self.current_process.pid}", shell=True)
                else:
                    # On Unix, we can use process groups
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                    
                # Wait a bit for the process to terminate
                time.sleep(1)
                
                # Force kill if still running
                if self.current_process.poll() is None:
                    self.current_process.kill()
                    
            # Get any remaining output
            stdout, stderr = self.current_process.communicate()
            
            result = {
                "success": True,
                "exit_code": self.current_process.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
            
            # Reset process tracking
            self.current_process = None
            self.process_info = {}
            
            return result
            
        except Exception as e:
            logger.error(f"Error stopping project: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def monitor_project(self, duration: int = SCREENSHOT_MONITOR_DURATION, interval: float = SCREENSHOT_INTERVAL) -> Dict:
        """
        Monitor the running project.
        
        Args:
            duration: Duration to monitor in seconds
            interval: Interval between screenshots in seconds
            
        Returns:
            Dictionary with monitoring results
        """
        if self.current_process is None or self.current_process.poll() is not None:
            return {
                "success": False,
                "error": "No running process to monitor"
            }
            
        console.print(f"[bold yellow]Monitoring project for {duration} seconds...[/bold yellow]")
        self.consolidated_log.log_section("Monitor Project", f"Monitoring project for {duration} seconds with {interval} second intervals")
        
        start_time = time.time()
        end_time = start_time + duration
        screenshots = []
        error_reports = []
        
        try:
            while time.time() < end_time and self.current_process.poll() is None:
                # Take a screenshot
                screenshot_result = self.screenshot_manager.capture_screenshot(f"monitor_{int(time.time())}")
                if screenshot_result[0]:
                    screenshot_path = screenshot_result[1]
                    screenshots.append(screenshot_path)
                    
                    # Analyze the screenshot
                    analysis_result = self.screenshot_manager.analyze_screenshot(screenshot_path)
                    if analysis_result["success"] and analysis_result["has_errors"]:
                        error_reports.append(analysis_result)
                        console.print(f"[bold red]Errors detected in screenshot:[/bold red] {screenshot_path}")
                        for error in analysis_result["errors"]:
                            console.print(f"[red]- {error['pattern']}: {error['line']}[/red]")
                            
                # Wait for the next interval
                time.sleep(interval)
                
            # Check if the process is still running
            is_running = self.current_process.poll() is None
            
            return {
                "success": True,
                "is_running": is_running,
                "duration": time.time() - start_time,
                "screenshots": screenshots,
                "error_reports": error_reports,
                "has_errors": len(error_reports) > 0
            }
            
        except Exception as e:
            logger.error(f"Error monitoring project: {e}")
            return {
                "success": False,
                "error": str(e),
                "screenshots": screenshots,
                "error_reports": error_reports
            }
            
    def analyze_and_fix(self, error_reports: List[Dict], code_context: Optional[Dict] = None) -> Dict:
        """
        Analyze errors and suggest fixes.
        
        Args:
            error_reports: List of error reports from screenshot analysis
            code_context: Optional code context to help with fixes
            
        Returns:
            Dictionary with analysis and fix results
        """
        if not error_reports:
            return {
                "success": True,
                "message": "No errors to analyze"
            }
            
        console.print(f"[bold yellow]Analyzing {len(error_reports)} error reports...[/bold yellow]")
        self.consolidated_log.log_section("Analyze and Fix", f"Analyzing {len(error_reports)} error reports")
        
        try:
            # Collect all errors
            all_errors = []
            for report in error_reports:
                if "errors" in report:
                    all_errors.extend(report["errors"])
                    
            # Group errors by pattern
            error_groups = {}
            for error in all_errors:
                pattern = error["pattern"]
                if pattern not in error_groups:
                    error_groups[pattern] = []
                error_groups[pattern].append(error)
                
            # Analyze each error group
            analyses = []
            for pattern, errors in error_groups.items():
                # Use the first screenshot that contains this error
                for report in error_reports:
                    if "errors" in report and any(e["pattern"] == pattern for e in report["errors"]):
                        screenshot_path = report["screenshot_path"]
                        break
                else:
                    screenshot_path = None
                    
                if screenshot_path:
                    # Get code context if available
                    context_str = ""
                    if code_context:
                        context_str = f"\\n\\nRelevant code:\\n```\\n{code_context.get('code', '')}\\n```"
                        
                    # Analyze the error
                    prompt = f"Analyze this error: {pattern}\\n\\nError context:\\n{errors[0]['context']}{context_str}"
                    analysis = self.ai_client.analyze_image(screenshot_path, prompt)
                    
                    if analysis["success"]:
                        analyses.append({
                            "pattern": pattern,
                            "errors": errors,
                            "screenshot_path": screenshot_path,
                            "analysis": analysis["analysis"]
                        })
                        
            # Generate fix suggestions
            if analyses:
                fixes = []
                for analysis in analyses:
                    # Extract fix suggestions from the analysis
                    fix_lines = []
                    in_fix_section = False
                    for line in analysis["analysis"].split("\\n"):
                        if "suggested fix" in line.lower() or "solution" in line.lower() or "code fix" in line.lower():
                            in_fix_section = True
                            fix_lines.append(line)
                        elif in_fix_section:
                            fix_lines.append(line)
                            
                    fixes.append({
                        "pattern": analysis["pattern"],
                        "analysis": analysis["analysis"],
                        "fix_suggestion": "\\n".join(fix_lines)
                    })
                    
                return {
                    "success": True,
                    "analyses": analyses,
                    "fixes": fixes
                }
            else:
                return {
                    "success": False,
                    "error": "Could not analyze errors",
                    "error_reports": error_reports
                }
                
        except Exception as e:
            logger.error(f"Error analyzing and fixing: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def apply_fixes(self, fixes: List[Dict]) -> Dict:
        """
        Apply fixes to the project.
        
        Args:
            fixes: List of fix suggestions
            
        Returns:
            Dictionary with apply results
        """
        if not fixes:
            return {
                "success": True,
                "message": "No fixes to apply"
            }
            
        console.print(f"[bold yellow]Applying {len(fixes)} fixes...[/bold yellow]")
        self.consolidated_log.log_section("Apply Fixes", f"Applying {len(fixes)} fixes")
        
        try:
            # TODO: Implement actual code modification based on fix suggestions
            # This would require parsing the fix suggestions and modifying the code
            # For now, we'll just return the fix suggestions
            
            return {
                "success": True,
                "message": "Fix suggestions generated (manual application required)",
                "fixes": fixes
            }
            
        except Exception as e:
            logger.error(f"Error applying fixes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def run_verify_fix_cycle(self, max_cycles: int = 3) -> Dict:
        """
        Run a cycle of: run project, verify, fix issues, repeat.
        
        Args:
            max_cycles: Maximum number of cycles to run
            
        Returns:
            Dictionary with cycle results
        """
        console.print(Panel(f"[bold blue]Starting Run-Verify-Fix Cycle (max {max_cycles} cycles)[/bold blue]"))
        self.consolidated_log.log_section("Run-Verify-Fix Cycle", f"Starting cycle with max {max_cycles} cycles")
        
        cycle_results = []
        
        for cycle in range(1, max_cycles + 1):
            console.print(f"[bold yellow]Cycle {cycle}/{max_cycles}[/bold yellow]")
            self.consolidated_log.log_section(f"Cycle {cycle}/{max_cycles}", f"Starting cycle {cycle}")
            
            # Step 1: Run the project
            run_result = self.run_project()
            if not run_result["success"]:
                cycle_results.append({
                    "cycle": cycle,
                    "status": "failed",
                    "stage": "run",
                    "error": run_result.get("error", "Unknown error")
                })
                console.print(f"[bold red]Failed to run project:[/bold red] {run_result.get('error', 'Unknown error')}")
                break
                
            # Step 2: Monitor and verify
            monitor_result = self.monitor_project()
            if not monitor_result["success"]:
                cycle_results.append({
                    "cycle": cycle,
                    "status": "failed",
                    "stage": "monitor",
                    "error": monitor_result.get("error", "Unknown error")
                })
                console.print(f"[bold red]Failed to monitor project:[/bold red] {monitor_result.get('error', 'Unknown error')}")
                break
                
            # Check if there are errors
            if not monitor_result.get("has_errors", False):
                cycle_results.append({
                    "cycle": cycle,
                    "status": "success",
                    "stage": "verify",
                    "message": "No errors detected"
                })
                console.print("[bold green]No errors detected. Project is running successfully![/bold green]")
                break
                
            # Step 3: Analyze and fix
            error_reports = monitor_result.get("error_reports", [])
            analyze_result = self.analyze_and_fix(error_reports)
            
            if not analyze_result["success"]:
                cycle_results.append({
                    "cycle": cycle,
                    "status": "failed",
                    "stage": "analyze",
                    "error": analyze_result.get("error", "Unknown error")
                })
                console.print(f"[bold red]Failed to analyze errors:[/bold red] {analyze_result.get('error', 'Unknown error')}")
                break
                
            # Step 4: Apply fixes
            fixes = analyze_result.get("fixes", [])
            apply_result = self.apply_fixes(fixes)
            
            if not apply_result["success"]:
                cycle_results.append({
                    "cycle": cycle,
                    "status": "failed",
                    "stage": "apply",
                    "error": apply_result.get("error", "Unknown error")
                })
                console.print(f"[bold red]Failed to apply fixes:[/bold red] {apply_result.get('error', 'Unknown error')}")
                break
                
            # Record cycle results
            cycle_results.append({
                "cycle": cycle,
                "status": "in_progress",
                "stage": "complete",
                "fixes_applied": len(fixes)
            })
            
            # Stop the project before the next cycle
            self.stop_project()
            
            # Wait a bit before the next cycle
            time.sleep(2)
            
        # Stop the project at the end
        self.stop_project()
        
        # Summarize results
        successful_cycles = [r for r in cycle_results if r["status"] == "success"]
        failed_cycles = [r for r in cycle_results if r["status"] == "failed"]
        
        if successful_cycles:
            console.print("[bold green]Project verification successful![/bold green]")
            self.consolidated_log.log_message("✅ Project verification successful!")
        else:
            console.print("[bold red]Project verification failed![/bold red]")
            self.consolidated_log.log_message("❌ Project verification failed!")
            
        return {
            "success": len(successful_cycles) > 0,
            "cycles": cycle_results,
            "successful_cycles": len(successful_cycles),
            "failed_cycles": len(failed_cycles),
            "total_cycles": len(cycle_results)
        }
