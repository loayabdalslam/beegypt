#!/usr/bin/env python3
"""
AI Code Agent - Step-by-step project creation and editing.

This agent can handle software engineering tasks with a step-by-step approach,
allowing user confirmation at each stage and avoiding package initializers.
"""
import logging
import json
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Union

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm
from rich.live import Live
from rich.text import Text
from rich.style import Style

from models.ai_client_factory import AIClientFactory
from agent.planner import Planner
from agent.executor import Executor
from agent.git_manager import GitManager
from agent.code_reviewer import CodeReviewer
from agent.utils import parse_project_description, format_command_output, save_json
from agent.logger import MarkdownLogger
from agent.code_editor import open_code_editor
from agent.deployer import LocalDeployer
from agent.log_capture import MarkdownLogCapture
from agent.consolidated_log import ConsolidatedLogManager
from agent.package_handler import PackageHandler
from agent.strategies import StrategyFactory
from agent.terminal_logger import get_terminal_logger, initialize_terminal_logger
from agent.file_watcher import get_file_watcher, start_file_watching, stop_file_watching
from agent.code_optimizer import get_code_optimizer, initialize_code_optimizer, optimize_file_path
from agent.shadcn_integration import get_shadcn_integration, initialize_shadcn_integration, perform_shadcn_health_check
from agent.context7_integration import get_context7_integration, initialize_context7_integration
from agent.unified_mcp_integration import (
    get_unified_mcp_integration, initialize_unified_mcp_integration,
    generate_project_with_mcp, modify_project_with_mcp
)
from config import OUTPUT_DIR

# Import other modules
from run_verify import run_verify_fix
from agent.diff_utils import get_project_diff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize console for rich output
console = Console()

# Global variable for auto-yes mode
auto_yes_mode = False

def auto_confirm(message: str, default: bool = True) -> bool:
    """
    Auto-confirmation function that respects auto_yes_mode.
    """
    if auto_yes_mode:
        console.print(f"[dim]{message} [auto-yes][/dim]")
        return True
    return Confirm.ask(message, default=default)

class CodeAgent:
    """
    AI-powered code agent that can handle software engineering tasks.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the code agent."""
        # Initialize components
        self.ai_client = AIClientFactory.create_client()
        self.planner = Planner(self.ai_client)
        self.executor = None  # Will be initialized after project directory is created
        self.code_reviewer = CodeReviewer(self.ai_client)
        self.git_manager = None  # Will be initialized in the project directory

        # Project state
        self.project_description = None
        self.project_plan = None
        self.tasks = []
        self.current_task = None
        self.project_name = None
        self.project_dir = None

        # Set output directory
        # Always use the output directory by default
        if output_dir:
            # If a specific output directory is provided, use it
            self.output_dir = output_dir
        else:
            # Otherwise, use the default output directory
            self.output_dir = OUTPUT_DIR

        # Initialize logger (will be properly set up once we have a project name and directory)
        self.logger = None
        self.strategy = None
        
        # Track installation status to prevent nested loops
        self.dependencies_installed = False

    def process_project_description(self, description: str) -> Dict:
        """
        Process a project description and generate a plan.

        Args:
            description: Project description

        Returns:
            Dictionary with processing results
        """
        console.print(Panel("[bold blue]Processing Project Description[/bold blue]"))

        self.project_description = parse_project_description(description)

        # Determine and set the project strategy
        project_type_str = self.project_description.get("technologies", [""])[0]
        self.strategy = StrategyFactory.get_strategy(project_type_str)

        self.project_name = self._generate_project_name(description)

        self._setup_project_directory()
        self._initialize_logging_and_execution()
        self._display_project_info()

        if not self._generate_and_log_plan(description):
            return {"success": False, "error": "Failed to generate project plan"}

        self._save_project_state()
        self.logger.save()

        return {
            "success": True,
            "project_name": self.project_description["project_name"],
            "plan": self.project_plan,
            "tasks": self.tasks
        }

    def _generate_project_name(self, description: str) -> str:
        """Generates and cleans a project name from the description."""
        console.print("\n[bold yellow]Generating AI project name...[/bold yellow]")
        name_prompt = f"""
        Generate a creative, memorable, and relevant project name for the following project description:

        {description}

        The name should be short (1-3 words), catchy, and reflect the purpose or main features of the project.
        Return ONLY the name without any explanation or additional text.
        """
        try:
            ai_project_name = self.ai_client.generate_text(name_prompt).strip()
            import re
            clean_name = re.sub(r'[^\w\s-]', '', ai_project_name).strip()
            clean_name = re.sub(r'[\s]+', '-', clean_name).lower()
            return clean_name if clean_name else self.project_description['project_name']
        except Exception as e:
            logger.warning(f"Error generating AI project name: {e}")
            return self.project_description['project_name']

    def _setup_project_directory(self) -> None:
        """Creates the project directory and changes the CWD."""
        self.project_dir = self.output_dir / self.project_name

        current_dir = Path(os.getcwd())
        if current_dir.name == self.project_name and str(self.output_dir) in str(current_dir):
            logger.warning(f"Already in a directory named {self.project_name}, using current directory")
            self.project_dir = current_dir
        else:
            self.project_dir.mkdir(exist_ok=True, parents=True)
            os.chdir(self.project_dir)
            logger.info(f"Changed working directory to: {self.project_dir}")

    def _initialize_logging_and_execution(self) -> None:
        """Initializes the logger, log capture, and executor."""
        self.executor = Executor(self.ai_client, working_dir=self.project_dir)
        logger.info(f"Initialized executor with working directory: {self.project_dir}")

        self.logger = MarkdownLogger(self.project_dir, self.project_name)
        self.logger.start_section("Project Initialization")
        self.logger.log_text(f"Project Name: {self.project_name}")
        self.logger.log_text(f"Project Directory: {self.project_dir}")

        log_dir = self.project_dir / "logs"
        self.log_capture = MarkdownLogCapture(log_dir, "agent_log")
        self.log_capture.start_capture()
        self.log_capture.log_section("Project Initialization", f"Project: {self.project_name}\nDirectory: {self.project_dir}")

    def _display_project_info(self) -> None:
        """Displays project name, directory, technologies, and features."""
        console.print(f"Project Name: [bold]{self.project_name}[/bold]")
        console.print(f"Project Directory: [bold]{self.project_dir}[/bold]")

        if self.project_description.get("technologies"):
            console.print("Technologies:")
            tech_list = []
            for tech in self.project_description["technologies"]:
                console.print(f"  - {tech}")
                tech_list.append(tech)
            self.logger.log_text("**Technologies:**")
            self.logger.log_text("\n".join([f"- {tech}" for tech in tech_list]))

        if self.project_description.get("features"):
            console.print("Features:")
            feature_list = []
            for feature in self.project_description["features"]:
                console.print(f"  - {feature}")
                feature_list.append(feature)
            self.logger.log_text("**Features:**")
            self.logger.log_text("\n".join([f"- {feature}" for feature in feature_list]))

    def _generate_and_log_plan(self, description: str) -> bool:
        """Generates, displays, and logs the project plan and tasks."""
        console.print("\n[bold yellow]Generating project plan and tasks...[/bold yellow]")
        combined_result = self.planner.generate_plan_and_tasks(description)

        if "error" in combined_result:
            console.print(f"[bold red]Error generating project plan:[/bold red] {combined_result['error']}")
            return False

        self.project_plan = {
            "raw_plan": combined_result.get("raw_plan", ""),
            "structured_plan": combined_result.get("structured_plan", {})
        }

        console.print("\n[bold green]Project Plan Generated:[/bold green]")
        console.print(Markdown(self.project_plan["raw_plan"]))
        self.logger.start_section("Project Plan")
        self.logger.log_plan(self.project_plan)

        self.tasks = combined_result.get("tasks", [])
        if not self.tasks:
            console.print("\n[bold yellow]Extracting development tasks from plan...[/bold yellow]")
            try:
                self.tasks = self.planner.generate_tasks(self.project_plan)
                if not self.tasks:
                    console.print("[bold red]Error generating tasks: No tasks were returned[/bold red]")
                    return False
            except Exception as e:
                console.print(f"[bold red]Error generating tasks: {str(e)}[/bold red]")
                return False

        console.print(f"\n[bold green]Generated {len(self.tasks)} tasks[/bold green]")
        for i, task in enumerate(self.tasks):
            console.print(f"{i+1}. [bold]{task.get('task name', task.get('name', f'Task {i+1}'))}[/bold]")
            if "description" in task:
                console.print(f"   {task['description']}")

        self.logger.start_section("Development Tasks")
        self.logger.log_tasks(self.tasks)
        return True

    def setup_project(self) -> Dict:
        """
        Set up the project structure based on the plan.
        Prioritizes package files and .gitignore creation first, then directories.

        Returns:
            Dictionary with setup results
        """
        if not self.project_plan:
            return {"success": False, "error": "No project plan available"}

        console.print(Panel("[bold blue]Setting Up Project Structure[/bold blue]"))
        self.logger.start_section("Project Setup")

        package_results = self._setup_package_files_and_gitignore()
        self._setup_git_repository()
        
        try:
            setup_result = self._setup_directory_structure()
            self._commit_initial_structure()
            self._install_project_dependencies(package_results.get("created_files", []))

            self.logger.save()
            console.print("\n[bold green]✅ Project structure ready! All code generation will be handled by the planned tasks.[/bold green]")

            return {
                "success": True,
                "directories_created": len(setup_result.get("created_directories", [])),
                "files_created": len(package_results.get("created_files", [])),
                "errors": setup_result.get("errors", []) + package_results.get("errors", [])
            }
        except Exception as e:
            logger.error(f"Error setting up project structure: {e}")
            console.print(f"[bold red]Error setting up project structure:[/bold red] {str(e)}")
            return {"success": False, "error": str(e)}

    def _setup_package_files_and_gitignore(self) -> Dict:
        """Creates package files and .gitignore using the selected strategy."""
        console.print("\n[bold yellow]Step 1: Creating package files and .gitignore...[/bold yellow]")
        package_handler = PackageHandler(self.project_dir)

        if self.strategy:
            package_structure = self.strategy.get_package_structure(self.project_description)
            gitignore_content = self.strategy.generate_gitignore_content(
                self.project_description.get("technologies", [])
            )
        else:
            # Fallback to old behavior if no strategy is found
            package_structure = {
                "project_name": self.project_description.get("project_name", "my-project"),
                "description": self.project_description.get("description", ""),
                "project_type": self.project_plan.get("project_type", ""),
                "technologies": self.project_plan.get("technologies", []),
                "directories": [], "files": []
            }
            gitignore_content = self._generate_gitignore_fallback(package_structure)

        package_results = package_handler.ensure_package_files(package_structure)
        
        gitignore_path = self.project_dir / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, "w", encoding='utf-8') as f:
                f.write(gitignore_content)
            package_results.setdefault("created_files", []).append(str(gitignore_path))
            console.print(f"  - Created .gitignore")
        
        if package_results.get("created_files"):
            console.print("\n[bold green]Created package and gitignore files:[/bold green]")
            self.logger.start_subsection("Created Package Files")
            for file_path in package_results["created_files"]:
                console.print(f"  - {Path(file_path).name}")
                self.logger.log_text(f"- {Path(file_path).name}")
        return package_results

    def _setup_git_repository(self) -> None:
        """Initializes the Git repository."""
        console.print("\n[bold yellow]Step 2: Initializing Git repository...[/bold yellow]")
        self.git_manager = GitManager(self.project_dir)
        git_init_result = self.git_manager.init_repo()
        if git_init_result["success"]:
            console.print(f"[bold green]{git_init_result['message']}[/bold green]")
            self.logger.log_text(f"✅ {git_init_result['message']}")
        else:
            console.print(f"[bold yellow]Note:[/bold yellow] {git_init_result['message']}")
            self.logger.log_text(f"⚠️ {git_init_result['message']}")

    def _setup_directory_structure(self) -> Dict:
        """Creates the directory structure for the project."""
        console.print("\n[bold yellow]Step 3: Creating directory structure...[/bold yellow]")
        self._clean_duplicate_structures()

        structure_prompt = f"""
        Based on the following project plan, generate ONLY a directory structure without any file content.
        Do not generate any code files - only create the folder structure.
        {self.project_plan.get('raw_plan', '')}
        Provide your response in JSON format: {{"directories": ["path/to/dir1", ...], "files": []}}
        IMPORTANT: Leave the "files" array empty.
        """
        structure_text = self.ai_client.generate_text(structure_prompt)

        json_start = structure_text.find('{')
        json_end = structure_text.rfind('}') + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in the directory structure response")

        structure = json.loads(structure_text[json_start:json_end])
        self.executor = Executor(self.ai_client, self.project_dir)
        initialize_code_optimizer()
        initialize_unified_mcp_integration(self.project_dir)
        setup_result = self.executor.setup_project_structure(structure)

        if setup_result.get("created_directories"):
            console.print("\n[bold green]Created directories:[/bold green]")
            self.logger.start_subsection("Created Directories")
            for directory in setup_result["created_directories"]:
                console.print(f"  - {directory}")
                self.logger.log_text(f"- {directory}")

        if setup_result.get("errors"):
            console.print("\n[bold red]Errors creating directories:[/bold red]")
            self.logger.start_subsection("Errors")
            for error in setup_result["errors"]:
                console.print(f"  - {error}")
                self.logger.log_text(f"- ❌ {error}")

        return setup_result

    def _commit_initial_structure(self) -> None:
        """Commits the initial project structure to Git."""
        console.print("\n[bold yellow]Committing initial project structure...[/bold yellow]")
        commit_result = self.git_manager.commit("Initial project structure")
        if commit_result["success"]:
            console.print(f"[bold green]{commit_result['message']}[/bold green]")
            self.logger.log_text(f"✅ {commit_result['message']}")
        else:
            console.print(f"[bold red]Error committing changes:[/bold red] {commit_result.get('error', 'Unknown error')}")
            self.logger.log_text(f"❌ Error committing changes: {commit_result.get('error', 'Unknown error')}")

        state_file = self.project_dir / "project_state.json"
        self._save_project_state(state_file)

    def _install_project_dependencies(self, created_files: List[str]) -> None:
        """Installs project dependencies as the final step."""
        console.print("\n[bold yellow]Step 4: Installing dependencies (final step)...[/bold yellow]")
        package_files = [f for f in created_files if Path(f).name in ["package.json", "requirements.txt", "Gemfile", "Cargo.toml"]]
        if package_files:
            self._install_dependencies(package_files)
        else:
            console.print("  - No package files found to install")

    def _clean_duplicate_structures(self) -> None:
        """
        Clean up duplicate/nested project structures and files.
        """
        console.print("  - Checking for duplicate/nested structures...")
        
        duplicates_found = False
        
        # Check for nested projects with same name
        project_name = self.project_dir.name
        nested_project_path = self.project_dir / project_name
        
        if nested_project_path.exists() and nested_project_path.is_dir():
            console.print(f"    [yellow]Found nested project directory: {nested_project_path}[/yellow]")
            # Move contents up one level
            for item in nested_project_path.iterdir():
                target = self.project_dir / item.name
                if not target.exists():
                    item.rename(target)
                    console.print(f"    - Moved {item.name} up one level")
                else:
                    console.print(f"    [yellow]Skipped {item.name} (already exists)[/yellow]")
            
            # Remove empty nested directory
            try:
                nested_project_path.rmdir()
                console.print(f"    - Removed empty nested directory: {project_name}")
                duplicates_found = True
            except OSError:
                console.print(f"    [yellow]Could not remove {project_name} (not empty)[/yellow]")
        
        # Check for duplicate package files
        package_files = ["package.json", "requirements.txt", "Gemfile", "Cargo.toml"]
        for package_file in package_files:
            main_file = self.project_dir / package_file
            if main_file.exists():
                # Look for duplicates in subdirectories
                for subdir in self.project_dir.rglob("*/"):
                    if subdir.is_dir() and subdir != self.project_dir:
                        duplicate_file = subdir / package_file
                        if duplicate_file.exists():
                            console.print(f"    [yellow]Found duplicate {package_file} in {subdir.relative_to(self.project_dir)}[/yellow]")
                            duplicate_file.unlink()
                            console.print(f"    - Removed duplicate {package_file}")
                            duplicates_found = True
        
        # Check for duplicate directories with similar names
        dirs_to_check = list(self.project_dir.iterdir())
        for i, dir1 in enumerate(dirs_to_check):
            if not dir1.is_dir():
                continue
            for dir2 in dirs_to_check[i+1:]:
                if not dir2.is_dir():
                    continue
                # Check if directories have very similar names (case insensitive)
                if dir1.name.lower() == dir2.name.lower() and dir1.name != dir2.name:
                    console.print(f"    [yellow]Found similar directories: {dir1.name} and {dir2.name}[/yellow]")
                    # Keep the one with more standard naming (lowercase, no spaces)
                    if dir1.name.islower() and not dir2.name.islower():
                        console.print(f"    - Removing {dir2.name} (keeping {dir1.name})")
                        import shutil
                        shutil.rmtree(dir2)
                        duplicates_found = True
                    elif dir2.name.islower() and not dir1.name.islower():
                        console.print(f"    - Removing {dir1.name} (keeping {dir2.name})")
                        import shutil
                        shutil.rmtree(dir1)
                        duplicates_found = True
        
        if not duplicates_found:
            console.print("    - No duplicates found")
        else:
            console.print("    [green]✓ Cleaned up duplicate structures[/green]")

    def _install_dependencies(self, created_files: list) -> None:
        """
        Install dependencies based on created package files.
        """
        import subprocess
        
        for file_path in created_files:
            file_name = Path(file_path).name
            
            if file_name == "package.json":
                console.print("  - Installing npm dependencies...")
                try:
                    result = subprocess.run(
                        ["npm", "install"],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        console.print("    [bold green]✓ npm install completed[/bold green]")
                    else:
                        console.print(f"    [bold yellow]⚠ npm install warning: {result.stderr}[/bold yellow]")
                except Exception as e:
                    console.print(f"    [bold red]✗ npm install failed: {e}[/bold red]")
            
            elif file_name == "requirements.txt":
                console.print("  - Installing pip dependencies...")
                try:
                    result = subprocess.run(
                        ["pip", "install", "-r", "requirements.txt"],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        console.print("    [bold green]✓ pip install completed[/bold green]")
                    else:
                        console.print(f"    [bold yellow]⚠ pip install warning: {result.stderr}[/bold yellow]")
                except Exception as e:
                    console.print(f"    [bold red]✗ pip install failed: {e}[/bold red]")
            
            elif file_name == "Gemfile":
                console.print("  - Installing bundle dependencies...")
                try:
                    result = subprocess.run(
                        ["bundle", "install"],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        console.print("    [bold green]✓ bundle install completed[/bold green]")
                    else:
                        console.print(f"    [bold yellow]⚠ bundle install warning: {result.stderr}[/bold yellow]")
                except Exception as e:
                    console.print(f"    [bold red]✗ bundle install failed: {e}[/bold red]")
            
            elif file_name == "Cargo.toml":
                console.print("  - Installing cargo dependencies...")
                try:
                    result = subprocess.run(
                        ["cargo", "build"],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        console.print("    [bold green]✓ cargo build completed[/bold green]")
                    else:
                        console.print(f"    [bold yellow]⚠ cargo build warning: {result.stderr}[/bold yellow]")
                except Exception as e:
                    console.print(f"    [bold red]✗ cargo build failed: {e}[/bold red]")

    def _optimize_created_files(self, created_files: List[str]) -> None:
        """
        Optimize created code files using the code optimizer.
        
        Args:
            created_files: List of file paths that were created
        """
        if not created_files:
            return
            
        console.print("\n[bold cyan]Optimizing created files...[/bold cyan]")
        
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs', '.go', '.rs', '.php', '.rb'}
        
        for file_path_str in created_files:
            try:
                file_path = Path(file_path_str)
                
                # Only optimize code files
                if file_path.suffix.lower() in code_extensions and file_path.exists():
                    console.print(f"  Analyzing: {file_path.name}")
                    
                    # Use the code optimizer to analyze and potentially optimize the file
                    optimizer = get_code_optimizer()
                    if optimizer:
                        result = optimizer.analyze_file(str(file_path))
                        
                        if result and result.suggestions:
                            console.print(f"    Found {len(result.suggestions)} optimization suggestions")
                            
                            # Log optimization results
                            self.logger.log_text(f"Code optimization for {file_path.name}:")
                            for suggestion in result.suggestions[:3]:  # Show top 3 suggestions
                                self.logger.log_text(f"  - {suggestion.type.value}: {suggestion.description}")
                        else:
                            console.print(f"    No optimization suggestions found")
                            
            except Exception as e:
                console.print(f"  [yellow]Warning: Could not optimize {file_path_str}: {str(e)}[/yellow]")
                logger.warning(f"Code optimization failed for {file_path_str}: {e}")

    def execute_task(self, task_index: int) -> Dict:
        """
        Execute a specific task from the task list.

        Args:
            task_index: Index of the task to execute

        Returns:
            Dictionary with execution results
        """
        if not self.tasks or not (0 <= task_index < len(self.tasks)):
            return {"success": False, "error": "Invalid task index"}

        self.current_task = self.tasks[task_index]
        task_name = self.current_task.get('task name', f'Task {task_index+1}')
        task_description = self.current_task.get('description', 'No description')

        self._log_task_start(task_index, task_name, task_description)

        if not self.project_dir or not self.project_dir.exists():
            console.print("[bold red]Error: Project directory not found[/bold red]")
            return {"success": False, "error": "Project directory not found"}

        self._ensure_git_initialized()
        branch_name = self._setup_task_branch(task_name)

        try:
            execution_plan = self._generate_execution_plan(self.current_task)
            self._execute_commands(execution_plan.get("commands", []))
            self._implement_code_changes(execution_plan.get("code_changes", []))
            self._commit_task_changes(task_name)
            self._ensure_readme_exists()

            return {
                "success": True, "task_index": task_index, "branch": branch_name,
                "commands_executed": len(execution_plan.get("commands", [])),
                "code_changes": len(execution_plan.get("code_changes", []))
            }
        except Exception as e:
            logger.error(f"Error executing task {task_name}: {e}")
            console.print(f"[bold red]Error executing task {task_name}:[/bold red] {str(e)}")
            return {"success": False, "error": str(e)}

    def _log_task_start(self, task_index, task_name, task_description):
        """Logs the start of a task."""
        self.logger.start_section(f"Task {task_index+1}: {task_name}")
        self.logger.log_text(f"Description: {task_description}")
        self.log_capture.log_section(f"Task {task_index+1}: {task_name}", f"Description: {task_description}")
        console.print(Panel(f"[bold blue]Executing Task: {task_name}[/bold blue]"))
        console.print(f"Description: {task_description}")

    def _ensure_git_initialized(self):
        """Initializes Git if it hasn't been already."""
        if not self.git_manager:
            console.print("[bold yellow]Initializing Git repository in project directory...[/bold yellow]")
            self.git_manager = GitManager(self.project_dir)
            git_init_result = self.git_manager.init_repo()
            if git_init_result["success"]:
                console.print(f"[bold green]{git_init_result['message']}[/bold green]")
            else:
                console.print(f"[bold yellow]Note:[/bold yellow] {git_init_result['message']}")

    def _setup_task_branch(self, task_name: str) -> str:
        """Creates and checks out a new branch for the task."""
        branch_name = f"feature/{task_name.lower().replace(' ', '-')}"
        console.print(f"\n[bold yellow]Creating branch: {branch_name}[/bold yellow]")
        branch_result = self.git_manager.create_branch(branch_name)
        if branch_result["success"]:
            console.print(f"[bold green]{branch_result['message']}[/bold green]")
        else:
            console.print(f"[bold red]Error creating branch:[/bold red] {branch_result.get('error', 'Unknown error')}")
        return branch_name

    def _generate_execution_plan(self, task: Dict) -> Dict:
        """Generates the execution plan (commands and code changes) for a task."""
        execution_prompt = f"""
        I need to implement the following task in a software project:
        Task: {task.get('task name', 'Unnamed Task')}
        Description: {task.get('description', 'No description')}
        Project context: {self.project_plan.get('raw_plan', '')}
        Project name: {self.project_name}
        IMPORTANT GUIDELINES:
        - Generate all required configuration files and code manually.
        - Do not use external code generators like 'create-react-app'.
        - Provide your response as a single JSON object.
        {{
            "commands": [{{"command": "...", "description": "..."}}],
            "code_changes": [{{"file_path": "...", "description": "..."}}]
        }}
        """
        console.print("\n[bold yellow]Generating implementation plan...[/bold yellow]")
        execution_text = self.ai_client.generate_text(execution_prompt)
        json_start = execution_text.find('{')
        json_end = execution_text.rfind('}') + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in the implementation plan response")
        return json.loads(execution_text[json_start:json_end])

    def _execute_commands(self, commands: List[Dict]):
        """Executes a list of shell commands."""
        if not commands:
            return
        console.print("\n[bold green]Executing commands:[/bold green]")
        for cmd_info in commands:
            command = cmd_info.get("command", "")
            description = cmd_info.get("description", "No description")
            console.print(f"\n[bold cyan]Command:[/bold cyan] {command}")
            console.print(f"[italic]{description}[/italic]")
            self.log_capture.log_command(command, description=description)

            is_package_install = any(cmd in command for cmd in ["npm install", "yarn add", "pip install"])
            result = self.executor.execute_command(command, capture_output=not is_package_install)
            console.print(Markdown(format_command_output(result)))

    def _implement_code_changes(self, code_changes: List[Dict]):
        """Implements a list of code changes by generating files."""
        if not code_changes:
            return
        console.print("\n[bold green]Implementing code changes:[/bold green]")
        for change in code_changes:
            file_path = change.get("file_path", "")
            description = change.get("description", "No description")
            console.print(f"\n[bold cyan]📄 Creating file:[/bold cyan] {file_path}")
            console.print(f"[italic]📝 {description}[/italic]")

            language = Path(file_path).suffix[1:] if '.' in Path(file_path).name else None
            result = self.executor.generate_file(file_path, description, language)

            if result["success"]:
                console.print(f"[dim]📊 File created: {result.get('file_size', 0)} characters[/dim]")
                self.log_capture.log_file_operation("create", result['file_path'], result['content_preview'])
            else:
                error_msg = result.get('error', 'Unknown error')
                console.print(f"[bold red]❌ Error generating file:[/bold red] {error_msg}")
                self.log_capture.log_error(error_msg, context=f"File generation: {file_path}")

    def _commit_task_changes(self, task_name: str):
        """Commits the changes for the current task."""
        console.print("\n[bold yellow]Committing changes...[/bold yellow]")
        commit_message = f"Implement task: {task_name}"
        commit_result = self.git_manager.commit(commit_message)
        if commit_result["success"]:
            console.print(f"[bold green]{commit_result['message']}[/bold green]")
        else:
            console.print(f"[bold red]Error committing changes:[/bold red] {commit_result.get('error', 'Unknown error')}")

        state_file = self.project_dir / "project_state.json"
        self._save_project_state(state_file)

    def _ensure_readme_exists(self):
        """Creates a README.md file if one doesn't exist."""
        readme_path = self.project_dir / "README.md"
        if not readme_path.exists():
            console.print("\n[bold yellow]Creating README.md...[/bold yellow]")
            readme_content = f"# {self.project_name.replace('-', ' ').title()}\n\nThis project was generated by AI Code Agent."
            try:
                with open(readme_path, 'w') as f:
                    f.write(readme_content)
                console.print(f"[bold green]Created README.md[/bold green]")
                self.git_manager.add_files([str(readme_path)])
                self.git_manager.commit("Add README.md")
            except Exception as e:
                console.print(f"[bold red]Error creating README:[/bold red] {str(e)}")

    def review_code(self, auto_fix: bool = False) -> Dict:
        """
        Review the code in the current project.

        Args:
            auto_fix: Whether to automatically fix issues

        Returns:
            Dictionary with review results
        """
        if auto_fix:
            console.print(Panel("[bold blue]Reviewing and Fixing Code[/bold blue]"))
        else:
            console.print(Panel("[bold blue]Reviewing Code[/bold blue]"))

        # Use the project directory if available, otherwise current directory
        review_dir = self.project_dir if self.project_dir and self.project_dir.exists() else Path.cwd()

        console.print(f"Reviewing code in: {review_dir}")

        # Review the code
        # Use the review_project method which excludes node_modules, packages, and virtual environments
        review_result = self.code_reviewer.review_project(review_dir, auto_fix=auto_fix)

        # Extract the actual review results from the project review
        if review_result["success"] and "review_results" in review_result:
            review_result = review_result["review_results"]

        if not review_result["success"]:
            console.print(f"[bold red]Error reviewing code:[/bold red] {review_result.get('error', 'Unknown error')}")
            return review_result

        # Generate a report
        report = self.code_reviewer.generate_review_report(review_result)

        # Display the report
        console.print("\n[bold green]Code Review Report:[/bold green]")
        console.print(Markdown(report))

        # Save the report
        report_path = review_dir / "code_review_report.md"
        try:
            with open(report_path, 'w') as f:
                f.write(report)
            console.print(f"[bold green]Saved review report to:[/bold green] {report_path}")

            # Commit the review report if we have a git repository
            if self.git_manager:
                try:
                    self.git_manager.add_files([report_path])
                    self.git_manager.commit("Add code review report")
                    console.print("[bold green]Committed code review report[/bold green]")
                except Exception as git_error:
                    logger.error(f"Error committing review report: {git_error}")
        except Exception as e:
            logger.error(f"Error saving review report: {e}")
            console.print(f"[bold red]Error saving review report:[/bold red] {str(e)}")

        return review_result

    def open_in_editor(self) -> bool:
        """
        Open the project in a code editor.

        Returns:
            True if successful, False otherwise
        """
        if not self.project_dir or not self.project_dir.exists():
            console.print("[bold red]Error: Project directory not found[/bold red]")
            return False

        console.print(f"\n[bold yellow]Opening project in code editor: {self.project_dir}[/bold yellow]")

        # Log the action
        if self.logger:
            self.logger.log_text(f"Opening project in code editor: {self.project_dir}")

        # Open the code editor
        result = open_code_editor(self.project_dir)

        if result:
            console.print("[bold green]Successfully opened project in code editor[/bold green]")
            if self.logger:
                self.logger.log_text("✅ Successfully opened project in code editor")
        else:
            console.print("[bold red]Failed to open project in code editor[/bold red]")
            if self.logger:
                self.logger.log_text("❌ Failed to open project in code editor")

        return result

    def deploy_locally(self) -> Dict:
        """
        Deploy the project locally.

        Returns:
            Dictionary with deployment results
        """
        if not self.project_dir or not self.project_dir.exists():
            console.print("[bold red]Error: Project directory not found[/bold red]")
            return {"success": False, "error": "Project directory not found"}

        console.print(f"\n[bold yellow]Deploying project locally: {self.project_dir}[/bold yellow]")

        # Log the action
        if self.logger:
            self.logger.start_section("Local Deployment")
            self.logger.log_text(f"Deploying project locally: {self.project_dir}")

        try:
            # Create a deployer
            deployer = LocalDeployer(self.project_dir)

            # Detect project type
            project_type = deployer.detect_project_type()
            console.print(f"Detected project type: [bold]{project_type}[/bold]")

            if self.logger:
                self.logger.log_text(f"Detected project type: {project_type}")

            # Check if dependencies are already installed
            if self.dependencies_installed:
                console.print("[yellow]Dependencies already installed, skipping installation...[/yellow]")
                if self.logger:
                    self.logger.log_text("Dependencies already installed, skipping installation")
                return {"success": True, "message": "Project already deployed", "skipped_installation": True}

            # Deploy the project
            result = deployer.deploy_locally()
            
            # Mark dependencies as installed if deployment was successful
            if result["success"]:
                self.dependencies_installed = True

            if result["success"]:
                console.print(f"[bold green]{result['message']}[/bold green]")
                if "url" in result and result["url"]:
                    console.print(f"URL: [bold blue]{result['url']}[/bold blue]")
                if "start_command" in result:
                    console.print(f"Start command: [bold yellow]{result['start_command']}[/bold yellow]")
                if "process_id" in result:
                    console.print(f"Process ID: [bold]{result['process_id']}[/bold]")

                if self.logger:
                    self.logger.log_text(f"✅ {result['message']}")
                    if "url" in result and result["url"]:
                        self.logger.log_text(f"URL: {result['url']}")
                    if "start_command" in result:
                        self.logger.log_text(f"Start command: {result['start_command']}")
                    if "process_id" in result:
                        self.logger.log_text(f"Process ID: {result['process_id']}")
            else:
                console.print(f"[bold red]{result['message']}[/bold red]")
                if self.logger:
                    self.logger.log_text(f"❌ {result['message']}")

            return result
        except Exception as e:
            error_msg = f"Error deploying project: {str(e)}"
            console.print(f"[bold red]{error_msg}[/bold red]")
            if self.logger:
                self.logger.log_text(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def _save_project_state(self, file_path: Optional[Path] = None) -> bool:
        """
        Save the current project state to a file.

        Args:
            file_path: Path to save the state file (default: project_state.json in current directory)

        Returns:
            True if successful, False otherwise
        """
        state = {
            "project_description": self.project_description,
            "project_plan": self.project_plan,
            "tasks": self.tasks,
            "current_task": self.current_task,
            "project_name": self.project_name,
            "project_dir": str(self.project_dir) if self.project_dir else None
        }

        # Use provided path or default
        save_path = file_path or Path("project_state.json")

        return save_json(state, save_path)

def is_existing_project(path: Path) -> bool:
    """
    Check if the path contains an existing project.

    Args:
        path: Path to check

    Returns:
        True if it's an existing project, False otherwise
    """
    # Check if the directory exists
    if not path.exists():
        return False

    # Check if it's a directory
    if not path.is_dir():
        return False

    # Check for common project files/directories
    project_indicators = [
        # Web projects
        "package.json",
        "node_modules",
        "public",
        "src",
        "index.html",
        "webpack.config.js",
        "tsconfig.json",
        "angular.json",
        "next.config.js",
        "vite.config.js",

        # Python projects
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "venv",
        ".venv",
        "Pipfile",

        # Java/Kotlin projects
        "pom.xml",
        "build.gradle",
        "gradlew",
        "src/main",

        # .NET projects
        "*.csproj",
        "*.sln",

        # General project files
        ".git",
        "README.md",
        "LICENSE",
        ".gitignore"
    ]

    # Check for the presence of any project indicator
    for indicator in project_indicators:
        if "*" in indicator:
            # Handle wildcard patterns
            pattern = indicator.replace("*", "")
            # If any matching files exist, return True
            if next(path.glob(f"*{pattern}"), None):
                return True
        else:
            if (path / indicator).exists():
                return True

    # If no indicators are found, check if the directory is not empty
    # An empty directory is likely not a project
    has_files = any(path.iterdir())

    return has_files

def create_new_project_step_by_step(path: Path, prompt: str, options: Dict) -> bool:
    """
    Create a new project step by step, with user confirmation at each stage.

    Args:
        path: Path where the project should be created
        prompt: Project description
        options: Additional options

    Returns:
        True if successful, False otherwise
    """
    # Initialize the consolidated log manager
    log_manager = ConsolidatedLogManager(path / "logs")
    log_manager.log_section("Create New Project (Step-by-Step)", f"Project path: {path}\nPrompt: {prompt}")
    console.print(Panel(f"[bold blue]Creating new project at: {path}[/bold blue]"))
    console.print(f"Project description: [italic]{prompt}[/italic]")

    # Ensure the parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize the agent with the specified path
    agent = CodeAgent(path)

    # Extract options
    no_editor = options.get("no_editor", False)
    no_deploy = options.get("no_deploy", False)
    no_code_generators = options.get("no_code_generators", True)  # Default to True to avoid code generators

    # Step 1: Process project description
    console.print("\n[bold yellow]Step 1: Processing project description...[/bold yellow]")
    if not auto_confirm("Continue with processing project description?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    result = agent.process_project_description(prompt)
    if not result["success"]:
        console.print(f"[bold red]Error processing project description:[/bold red] {result.get('error', 'Unknown error')}")
        return False

    # Step 2: Set up project structure
    console.print("\n[bold yellow]Step 2: Setting up project structure...[/bold yellow]")
    if not auto_confirm("Continue with setting up project structure?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    setup_result = agent.setup_project()
    if not setup_result["success"]:
        console.print(f"[bold red]Error setting up project:[/bold red] {setup_result.get('error', 'Unknown error')}")
        return False

    # Step 3: Enhance with MCP
    console.print("\n[bold yellow]Step 3: Enhancing project with MCPs...[/bold yellow]")
    if not auto_confirm("Continue with MCP enhancement?"):
        console.print("[bold yellow]Skipping MCP enhancement.[/bold yellow]")
    elif agent.strategy:
        agent.strategy.enhance_with_mcp()

    # Step 4: Execute tasks
    for i in range(len(agent.tasks)):
        task = agent.tasks[i]
        task_name = task.get('task name', task.get('name', f'Task {i+1}'))
        console.print(f"\n[bold yellow]Step 4.{i+1}: Executing task: {task_name}[/bold yellow]")

        if not auto_confirm(f"Continue with executing task: {task_name}?"):
            console.print("[bold yellow]Skipping this task.[/bold yellow]")
            continue

        task_result = agent.execute_task(i)
        if not task_result["success"]:
            console.print(f"[bold red]Error executing task {i+1}:[/bold red] {task_result.get('error', 'Unknown error')}")
            if not auto_confirm("Continue with the next task?"):
                console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
                return False

    # Step 5: Review code
    console.print("\n[bold yellow]Step 5: Reviewing code...[/bold yellow]")
    if not auto_confirm("Continue with code review?"):
        console.print("[bold yellow]Skipping code review.[/bold yellow]")
    else:
        review_result = agent.review_code(auto_fix=False)
        if not review_result["success"]:
            console.print(f"[bold red]Error reviewing code:[/bold red] {review_result.get('error', 'Unknown error')}")

    # Step 6: Fix code issues
    console.print("\n[bold yellow]Step 6: Fixing code issues...[/bold yellow]")
    if not auto_confirm("Continue with fixing code issues?"):
        console.print("[bold yellow]Skipping code fixes.[/bold yellow]")
    else:
        fix_result = agent.review_code(auto_fix=True)
        if not fix_result["success"]:
            console.print(f"[bold red]Error fixing code:[/bold red] {fix_result.get('error', 'Unknown error')}")

    # Step 7: Open in editor
    if not no_editor:
        console.print("\n[bold yellow]Step 7: Opening in code editor...[/bold yellow]")
        if not auto_confirm("Open project in code editor?"):
            console.print("[bold yellow]Skipping opening in editor.[/bold yellow]")
        else:
            agent.open_in_editor()

    # Step 8: Deploy locally
    if not no_deploy:
        console.print("\n[bold yellow]Step 8: Deploying locally...[/bold yellow]")
        if not auto_confirm("Deploy project locally?"):
            console.print("[bold yellow]Skipping local deployment.[/bold yellow]")
        else:
            agent.deploy_locally()

    console.print("\n[bold green]Project creation completed![/bold green]")
    return True

def edit_existing_project_step_by_step(path: Path, prompt: str, options: Dict) -> bool:
    """
    Edit an existing project step by step, with user confirmation at each stage.

    Args:
        path: Path to the existing project
        prompt: Edit request description
        options: Additional options

    Returns:
        True if successful, False otherwise
    """
    # Initialize the consolidated log manager
    log_manager = ConsolidatedLogManager(path / "logs")
    log_manager.log_section("Edit Existing Project (Step-by-Step)", f"Project path: {path}\nPrompt: {prompt}")
    console.print(Panel(f"[bold blue]Editing existing project at: {path}[/bold blue]"))
    console.print(f"Edit request: [italic]{prompt}[/italic]")

    # Extract options
    no_editor = options.get("no_editor", False)
    no_deploy = options.get("no_deploy", False)

    # Step 1: Analyze project
    console.print("\n[bold yellow]Step 1: Analyzing project...[/bold yellow]")
    if not auto_confirm("Continue with analyzing project?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    # Step 2: Generate fixes
    console.print("\n[bold yellow]Step 2: Generating fixes...[/bold yellow]")
    if not auto_confirm("Continue with generating fixes?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    # Step 3: Apply fixes
    console.print("\n[bold yellow]Step 3: Applying fixes...[/bold yellow]")
    if not auto_confirm("Continue with applying fixes?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    # Import fix_project here to avoid circular imports
    from fix_project import fix_project

    # Use the fix_project function with step-by-step confirmation
    result = fix_project(
        project_dir=path,
        problem_description=prompt,
        open_editor=not no_editor,
        deploy=not no_deploy
    )

    if result:
        console.print("\n[bold green]Project editing completed![/bold green]")
    else:
        console.print("\n[bold red]Project editing failed![/bold red]")

    return result

def display_bee_animation():
    """
    Display an animated ASCII art of a bee with pyramids.
    """
    # Clear the terminal
    os.system('cls' if os.name == 'nt' else 'clear')

    # Define the frames of the animation with a bee and pyramids
    frames = [
        # Frame 1
        r"""
          ▗▄▄▖ ▗▄▄▄▖    ▗▄▄▄▖ ▗▄▄▖▗▖  ▗▖▗▄▄▖ ▗▄▄▄▖
▐▌ ▐▌▐▌   ▐▌        ▐▌   
▐▛▀▚▖▐▛▀▀▘▐▛▀▀▘      
▐▙▄▞▘▐▙▄▄▖▐▙▄▄▖     ▐▙▄▄▖▝▚▄▞▘  ▐▌  ▐▌     █  
        """,
        # Frame 2
        r"""
    ▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖     ▗▄▄▄▖ ▗▄▄▖▗▖  ▗▖▗▄▄▖ ▗▄▄▄▖
▐▌ ▐▌▐▌   ▐▌        ▐▌   ▐▌    ▝▚▞▘ ▐▌ ▐▌  █  
▐▛▀▚▖▐▛▀▀▘▐▛▀▀▘     ▐▛▀▀▘▐▌▝▜▌  ▐▌  ▐▛▀▘   █  
        """
    ]

    # Create a Rich console for colored output
    animation_console = Console()

    # Display the animation
    animation_console.print("[bold yellow]BeeAgent - AI-powered project creation and editing[/bold yellow]")
    animation_console.print("[bold blue]Initializing...[/bold blue]")

    # Display the animation frames
    for _ in range(3):  # Run the animation for 3 cycles
        for frame in frames:
            # Clear the terminal for smooth animation
            os.system('cls' if os.name == 'nt' else 'clear')

            # Print the header again
            animation_console.print("[bold yellow]BeeAgent - AI-powered project creation and editing[/bold yellow]")
            animation_console.print("[bold blue]Initializing...[/bold blue]")

            # Create a styled text with yellow color for the bee and pyramids
            styled_frame = Text(frame)
            styled_frame.stylize("yellow")

            # Print the frame
            animation_console.print(styled_frame)

            # Control animation speed
            time.sleep(0.3)

    # Clear the terminal one last time
    os.system('cls' if os.name == 'nt' else 'clear')

    # Display welcome message
    animation_console.print(Panel("[bold yellow]Welcome to BeeAgent - AI-powered project creation and editing[/bold yellow]"))
    animation_console.print("[bold blue]Let's build something amazing together![/bold blue]\n")

    # Display a final bee with pyramids
    final_art = r"""         
▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖     ▗▄▄▄▖ ▗▄▄▖▗▖  ▗▖
▐▌ ▐▌▐▌   ▐▌        ▐▌   ▐▌    ▝▚▞▘ 
▐▛▀▚▖▐▛▀▀▘▐▛▀▀▘     ▐▛▀▀▘▐▌▝▜▌  ▐▌  
▐▙▄▞▘▐▙▄▄▖▐▙▄▄▖     ▐▙▄▄▖▝▚▄▞▘  ▐▌  

@By: Loaii abdalslam
    """

    styled_final = Text(final_art)
    styled_final.stylize("yellow")
    animation_console.print(styled_final)

def main():
    """
    Main entry point for the script.
    """
    global auto_yes_mode
    
    # Initialize terminal logger and file watcher
    # initialize_terminal_logger()  # Disabled to prevent blocking live display
    
    # Display the bee animation
    display_bee_animation()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="AI Code Agent - Step-by-step project creation and editing")
    parser.add_argument("--path", required=True, help="Path to the project directory")
    parser.add_argument("--prompt", required=True, help="Project description or edit request")
    parser.add_argument("--no-editor", action="store_true", help="Don't open the code editor after completion")
    parser.add_argument("--no-deploy", action="store_true", help="Don't deploy the project locally")
    parser.add_argument("--no-code-generators", action="store_true", help="Don't use code generators (for new projects)")
    parser.add_argument("--force-create", action="store_true", help="Force create a new project even if the directory exists")
    parser.add_argument("--force-edit", action="store_true", help="Force edit mode even if the directory doesn't look like a project")
    parser.add_argument("--diff", action="store_true", help="Show diff of changes after operation completes")
    parser.add_argument("--run-verify", action="store_true", help="Run, verify, and fix the project after completion")
    parser.add_argument("--max-cycles", type=int, default=3, help="Maximum number of run-verify cycles")
    parser.add_argument("--oneshot", action="store_true", help="Run in oneshot mode (no step-by-step confirmation)")
    parser.add_argument("--auto-yes", action="store_true", help="Automatically answer 'yes' to all prompts")
    parser.add_argument("--no-animation", action="store_true", help="Skip the initial animation")

    args = parser.parse_args()
    
    # Set auto_yes_mode based on argument
    auto_yes_mode = args.auto_yes

    # Convert path to Path object
    path = Path(args.path).resolve()

    # Collect options
    options = {
        "no_editor": args.no_editor,
        "no_deploy": args.no_deploy,
        "no_code_generators": args.no_code_generators,
        "show_diff": args.diff,
        "run_verify": args.run_verify,
        "max_cycles": args.max_cycles
    }

    try:
        # Start file watching for the project directory
        # console.print(f"[dim]Starting file watcher for {path}...[/dim]")
        # start_file_watching([path])  # Disabled to prevent terminal logger initialization
        
        # Skip animation if requested
        if not args.no_animation:
            # Display a simple loading animation for project analysis
            with console.status(f"[bold yellow]Analyzing project at {path}...[/bold yellow]", spinner="dots") as status:
                time.sleep(2)

        # Determine if it's an existing project
        if args.force_create:
            # Force create mode
            console.print("[yellow]Forcing create mode as requested[/yellow]")
            is_project = False
        elif args.force_edit:
            # Force edit mode
            console.print("[yellow]Forcing edit mode as requested[/yellow]")
            is_project = True
        else:
            # Auto-detect
            is_project = is_existing_project(path)

        # If oneshot mode is enabled, use the original oneshot or fix_project functions
        if args.oneshot:
            if is_project:
                # Edit existing project
                console.print("[bold green]Detected existing project - using oneshot edit mode[/bold green]")
                # Import fix_project here to avoid circular imports
                from fix_project import fix_project
                result = fix_project(
                    project_dir=path,
                    problem_description=args.prompt,
                    open_editor=not args.no_editor,
                    deploy=not args.no_deploy
                )
            else:
                # Create new project
                console.print("[bold green]Creating new project - using oneshot mode[/bold green]")
                # Import oneshot here to avoid circular imports
                from oneshot import oneshot
                result = oneshot(
                    description=args.prompt,
                    output_dir=path,
                    open_editor=not args.no_editor,
                    deploy=not args.no_deploy,
                    no_code_generators=args.no_code_generators
                )
        else:
            # Use step-by-step mode
            if is_project:
                # Edit existing project
                console.print("[bold green]Detected existing project[/bold green]")
                result = edit_existing_project_step_by_step(path, args.prompt, options)
            else:
                # Create new project
                console.print("[bold green]Creating new project[/bold green]")
                result = create_new_project_step_by_step(path, args.prompt, options)

        if result:
            console.print("[bold green]Operation completed successfully![/bold green]")

            # Show diff if requested
            if options.get("show_diff", False):
                console.print("\n[bold yellow]Generating diff of changes...[/bold yellow]")
                has_changes, diff_text = get_project_diff(path)

                if has_changes:
                    console.print("\n[bold green]Changes detected:[/bold green]")
                    console.print(Markdown(f"```diff\n{diff_text}\n```"))

                    # Log the diff to the consolidated log
                    log_manager = ConsolidatedLogManager(path / "logs")
                    log_manager.log_diff(diff_text, str(path))
                else:
                    console.print("\n[yellow]No changes detected[/yellow]")

            # Run, verify, and fix the project if requested
            if options.get("run_verify", False):
                console.print("\n[bold yellow]Running, verifying, and fixing the project...[/bold yellow]")
                run_verify_result = run_verify_fix(
                    project_dir=path,
                    max_cycles=options.get("max_cycles", 3)
                )

                if run_verify_result:
                    console.print("\n[bold green]Run-verify process completed successfully![/bold green]")
                else:
                    console.print("\n[bold yellow]Run-verify process completed with issues.[/bold yellow]")

            return 0
        else:
            console.print("[bold red]Operation failed![/bold red]")
            return 1

    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        logger.exception("Unhandled exception")
        return 1
    finally:
        # Clean up file watcher
        # try:
        #     console.print("[dim]Stopping file watcher...[/dim]")
        #     stop_file_watching()
        # except Exception as cleanup_error:
        #     logger.error(f"Error stopping file watcher: {cleanup_error}")
        pass

# Add __del__ method to CodeAgent class
def __del__(self):
    """
    Clean up resources when the agent is deleted.
    """
    # Stop log capture
    if hasattr(self, 'log_capture'):
        self.log_capture.stop_capture()

# Add the __del__ method to the CodeAgent class
CodeAgent.__del__ = __del__

# Modify the execute_command method in Executor class to avoid using code generators
original_execute_command = Executor.execute_command

def patched_execute_command(self, command: str, capture_output: bool = True, timeout: int = 600) -> Dict:
    """
    Execute a shell command with enhanced handling of code generators.
    This patched version ensures we never use npm init, npx, or other initializers.
    """
    # Check if this is a code generator or initializer command
    is_initializer = any(cmd in command for cmd in [
        "npm init",
        "npx create-",
        "yarn create",
        "create-react-app",
        "django-admin startproject",
        "rails new",
        "vue create",
        "ng new",
        "cargo init",
        "mvn archetype:generate"
    ])

    if is_initializer:
        logger.warning(f"Initializer command blocked: {command}")
        logger.warning("Initializer commands are disabled. Command will not be executed.")
        print(f"\n[WARNING] Initializer command blocked: {command}")
        print("Initializer commands are disabled. The command will not be executed.")
        print("The agent will generate all files directly instead.\n")

        # Return a simulated result without executing the command
        return {
            "command": command,
            "success": False,
            "return_code": 1,
            "stdout": "",
            "stderr": "Initializer commands are disabled. Please generate files directly.",
            "error": "Initializers are disabled"
        }

    # Call the original method for non-initializer commands
    return original_execute_command(self, command, capture_output, timeout)

# Apply the patch
Executor.execute_command = patched_execute_command

if __name__ == "__main__":
    sys.exit(main())
