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
import os
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

    def process_project_description(self, description: str) -> Dict:
        """
        Process a project description and generate a plan.

        Args:
            description: Project description

        Returns:
            Dictionary with processing results
        """
        console.print(Panel("[bold blue]Processing Project Description[/bold blue]"))

        # Parse the project description
        self.project_description = parse_project_description(description)

        # Generate an AI name for the project
        console.print("\n[bold yellow]Generating AI project name...[/bold yellow]")
        name_prompt = f"""
        Generate a creative, memorable, and relevant project name for the following project description:

        {description}

        The name should be short (1-3 words), catchy, and reflect the purpose or main features of the project.
        Return ONLY the name without any explanation or additional text.
        """

        try:
            ai_project_name = self.ai_client.generate_text(name_prompt).strip()
            # Clean up the name to be filesystem-friendly
            import re
            clean_name = re.sub(r'[^\w\s-]', '', ai_project_name).strip()
            clean_name = re.sub(r'[\s]+', '-', clean_name).lower()

            if clean_name:
                self.project_name = clean_name
            else:
                self.project_name = self.project_description['project_name']
        except Exception as e:
            logger.warning(f"Error generating AI project name: {e}")
            self.project_name = self.project_description['project_name']

        # Create project directory in the output folder
        self.project_dir = self.output_dir / self.project_name

        # Check if we're already in a project directory with the same name
        # This prevents nested project creation
        import os
        current_dir = Path(os.getcwd())
        if current_dir.name == self.project_name and str(self.output_dir) in str(current_dir):
            logger.warning(f"Already in a directory named {self.project_name}, using current directory")
            self.project_dir = current_dir
        else:
            # Create the project directory
            self.project_dir.mkdir(exist_ok=True, parents=True)

            # Change the current working directory to the project directory
            # This ensures all relative paths are resolved relative to the project directory
            os.chdir(self.project_dir)
            logger.info(f"Changed working directory to: {self.project_dir}")

        # Initialize the executor with the project directory as working directory
        self.executor = Executor(self.ai_client, working_dir=self.project_dir)
        logger.info(f"Initialized executor with working directory: {self.project_dir}")

        # Initialize the logger
        self.logger = MarkdownLogger(self.project_dir, self.project_name)
        self.logger.start_section("Project Initialization")
        self.logger.log_text(f"Project Name: {self.project_name}")
        self.logger.log_text(f"Project Directory: {self.project_dir}")

        # Initialize the log capture
        log_dir = self.project_dir / "logs"
        self.log_capture = MarkdownLogCapture(log_dir, "agent_log")
        self.log_capture.start_capture()
        self.log_capture.log_section("Project Initialization", f"Project: {self.project_name}\nDirectory: {self.project_dir}")

        console.print(f"Project Name: [bold]{self.project_name}[/bold]")
        console.print(f"Project Directory: [bold]{self.project_dir}[/bold]")

        if self.project_description["technologies"]:
            console.print("Technologies:")
            tech_list = []
            for tech in self.project_description["technologies"]:
                console.print(f"  - {tech}")
                tech_list.append(tech)
            self.logger.log_text("**Technologies:**")
            self.logger.log_text("\n".join([f"- {tech}" for tech in tech_list]))

        if self.project_description["features"]:
            console.print("Features:")
            feature_list = []
            for feature in self.project_description["features"]:
                console.print(f"  - {feature}")
                feature_list.append(feature)
            self.logger.log_text("**Features:**")
            self.logger.log_text("\n".join([f"- {feature}" for feature in feature_list]))

        console.print("\n[bold yellow]Generating project plan and tasks...[/bold yellow]")

        # Generate project plan and tasks in a single call to reduce API usage
        combined_result = self.planner.generate_plan_and_tasks(description)

        if "error" in combined_result:
            console.print(f"[bold red]Error generating project plan:[/bold red] {combined_result['error']}")
            return {"success": False, "error": combined_result["error"]}

        # Extract plan from combined result
        self.project_plan = {
            "raw_plan": combined_result.get("raw_plan", ""),
            "structured_plan": combined_result.get("structured_plan", {})
        }

        # Display the plan
        console.print("\n[bold green]Project Plan Generated:[/bold green]")
        console.print(Markdown(self.project_plan["raw_plan"]))

        # Log the plan
        self.logger.start_section("Project Plan")
        self.logger.log_plan(self.project_plan)

        # Get tasks from the combined result
        self.tasks = combined_result.get("tasks", [])

        # If no tasks were generated, try to extract them from the plan
        if not self.tasks:
            console.print("\n[bold yellow]Extracting development tasks from plan...[/bold yellow]")
            try:
                self.tasks = self.planner.generate_tasks(self.project_plan)

                if not self.tasks:
                    console.print("[bold red]Error generating tasks: No tasks were returned[/bold red]")
                    return {"success": False, "error": "Failed to generate tasks: No tasks were returned"}
            except Exception as e:
                console.print(f"[bold red]Error generating tasks: {str(e)}[/bold red]")
                return {"success": False, "error": f"Failed to generate tasks: {str(e)}"}

        # Display tasks
        console.print(f"\n[bold green]Generated {len(self.tasks)} tasks[/bold green]")
        for i, task in enumerate(self.tasks):
            console.print(f"{i+1}. [bold]{task.get('task name', task.get('name', f'Task {i+1}'))}[/bold]")
            if "description" in task:
                console.print(f"   {task['description']}")

        # Log the tasks
        self.logger.start_section("Development Tasks")
        self.logger.log_tasks(self.tasks)

        # Save the project state and logger
        self._save_project_state()
        self.logger.save()

        return {
            "success": True,
            "project_name": self.project_description["project_name"],
            "plan": self.project_plan,
            "tasks": self.tasks
        }

    def setup_project(self) -> Dict:
        """
        Set up the project structure based on the plan.

        Returns:
            Dictionary with setup results
        """
        if not self.project_plan:
            return {"success": False, "error": "No project plan available"}

        console.print(Panel("[bold blue]Setting Up Project Structure[/bold blue]"))

        # Log the setup process
        self.logger.start_section("Project Setup")

        # Initialize Git repository in the project directory
        console.print("\n[bold yellow]Initializing Git repository in project directory...[/bold yellow]")
        self.git_manager = GitManager(self.project_dir)
        git_init_result = self.git_manager.init_repo()

        if git_init_result["success"]:
            console.print(f"[bold green]{git_init_result['message']}[/bold green]")
            self.logger.log_text(f"✅ {git_init_result['message']}")
        else:
            console.print(f"[bold yellow]Note:[/bold yellow] {git_init_result['message']}")
            self.logger.log_text(f"⚠️ {git_init_result['message']}")

        # Extract directory structure from the plan
        console.print("\n[bold yellow]Creating project structure...[/bold yellow]")

        # Generate a prompt to extract the directory structure
        structure_prompt = f"""
        Based on the following project plan, generate a detailed directory structure and initial files to create:

        {self.project_plan.get('raw_plan', '')}

        Provide your response in the following JSON format:
        {{
            "directories": [
                "path/to/directory1",
                "path/to/directory2",
                ...
            ],
            "files": [
                {{
                    "path": "path/to/file1",
                    "description": "Detailed description of what this file should contain",
                    "language": "programming language"
                }},
                ...
            ]
        }}

        Include only the JSON output without any additional text.
        """

        structure_text = self.ai_client.generate_text(structure_prompt)

        # Extract JSON from the response
        try:
            # Find JSON in the response
            json_start = structure_text.find('{')
            json_end = structure_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = structure_text[json_start:json_end]
                structure = json.loads(json_str)
            else:
                raise ValueError("No JSON found in the response")

            # Update executor to use project directory
            self.executor = Executor(self.ai_client, self.project_dir)

            # Set up the project structure
            setup_result = self.executor.setup_project_structure(structure)

            # Display results
            if setup_result["created_directories"]:
                console.print("\n[bold green]Created directories:[/bold green]")
                self.logger.start_subsection("Created Directories")
                for directory in setup_result["created_directories"]:
                    console.print(f"  - {directory}")
                    self.logger.log_text(f"- {directory}")

            if setup_result["created_files"]:
                console.print("\n[bold green]Created files:[/bold green]")
                self.logger.start_subsection("Created Files")
                for file_path in setup_result["created_files"]:
                    console.print(f"  - {file_path}")
                    self.logger.log_text(f"- {file_path}")

            if setup_result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                self.logger.start_subsection("Errors")
                for error in setup_result["errors"]:
                    console.print(f"  - {error}")
                    self.logger.log_text(f"- ❌ {error}")

            # Commit the initial structure
            console.print("\n[bold yellow]Committing initial project structure...[/bold yellow]")
            commit_result = self.git_manager.commit("Initial project structure")

            if commit_result["success"]:
                console.print(f"[bold green]{commit_result['message']}[/bold green]")
                self.logger.log_text(f"✅ {commit_result['message']}")
            else:
                console.print(f"[bold red]Error committing changes:[/bold red] {commit_result.get('error', 'Unknown error')}")
                self.logger.log_text(f"❌ Error committing changes: {commit_result.get('error', 'Unknown error')}")

            # Save project state to the project directory
            state_file = self.project_dir / "project_state.json"
            self._save_project_state(state_file)

            # Save the logger
            self.logger.save()

            # Open the project in a code editor
            self.open_in_editor()

            return {
                "success": True,
                "directories_created": len(setup_result["created_directories"]),
                "files_created": len(setup_result["created_files"]),
                "errors": setup_result["errors"]
            }
        except Exception as e:
            logger.error(f"Error setting up project structure: {e}")
            console.print(f"[bold red]Error setting up project structure:[/bold red] {str(e)}")
            return {"success": False, "error": str(e)}

    def execute_task(self, task_index: int) -> Dict:
        """
        Execute a specific task from the task list.

        Args:
            task_index: Index of the task to execute

        Returns:
            Dictionary with execution results
        """
        if not self.tasks:
            return {"success": False, "error": "No tasks available"}

        if task_index < 0 or task_index >= len(self.tasks):
            return {"success": False, "error": f"Invalid task index: {task_index}"}

        task = self.tasks[task_index]
        self.current_task = task

        # Get task name and description
        task_name = task.get('task name', task.get('name', f'Task {task_index+1}'))
        task_description = task.get('description', 'No description')

        # Start task execution in the logger
        self.logger.start_section(f"Task {task_index+1}: {task_name}")
        self.logger.log_text(f"Description: {task_description}")

        # Log task execution in the markdown log
        self.log_capture.log_section(f"Task {task_index+1}: {task_name}",
                                   f"Description: {task_description}")

        console.print(Panel(f"[bold blue]Executing Task: {task_name}[/bold blue]"))
        console.print(f"Description: {task_description}")

        # Make sure we're in the project directory
        if not self.project_dir or not self.project_dir.exists():
            console.print("[bold red]Error: Project directory not found[/bold red]")
            return {"success": False, "error": "Project directory not found"}

        # Make sure git is initialized
        if not self.git_manager:
            console.print("[bold yellow]Initializing Git repository in project directory...[/bold yellow]")
            self.git_manager = GitManager(self.project_dir)
            git_init_result = self.git_manager.init_repo()

            if git_init_result["success"]:
                console.print(f"[bold green]{git_init_result['message']}[/bold green]")
            else:
                console.print(f"[bold yellow]Note:[/bold yellow] {git_init_result['message']}")

        # Create a branch for the task
        task_name = task.get('task name', task.get('name', f'task-{task_index+1}'))
        branch_name = f"feature/{task_name.lower().replace(' ', '-')}"

        console.print(f"\n[bold yellow]Creating branch: {branch_name}[/bold yellow]")
        branch_result = self.git_manager.create_branch(branch_name)

        if branch_result["success"]:
            console.print(f"[bold green]{branch_result['message']}[/bold green]")
        else:
            console.print(f"[bold red]Error creating branch:[/bold red] {branch_result.get('error', 'Unknown error')}")

        # Generate a prompt to execute the task
        execution_prompt = f"""
        I need to implement the following task in a software project:

        Task: {task.get('task name', task.get('name', f'Task {task_index+1}'))}
        Description: {task.get('description', 'No description')}

        Project context:
        {self.project_plan.get('raw_plan', '')}

        Project name: {self.project_name}

        IMPORTANT GUIDELINES:
        - DO NOT use external code generators like 'create-react-app', 'npx create-next-app', etc.
        - Instead, write all necessary code files directly
        - Generate all required configuration files (package.json, webpack.config.js, etc.) manually
        - Only use commands for necessary package installations (npm install, pip install, etc.)
        - Create a complete, working project structure with all required files

        Generate a list of specific commands and code changes needed to implement this task.
        Provide your response in the following JSON format:
        {{
            "commands": [
                {{
                    "command": "command to execute",
                    "description": "what this command does"
                }},
                ...
            ],
            "code_changes": [
                {{
                    "file_path": "path/to/file",
                    "description": "detailed description of what code to write in this file"
                }},
                ...
            ]
        }}

        Include only the JSON output without any additional text.
        """

        console.print("\n[bold yellow]Generating implementation plan...[/bold yellow]")
        execution_text = self.ai_client.generate_text(execution_prompt)

        try:
            # Find JSON in the response
            json_start = execution_text.find('{')
            json_end = execution_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = execution_text[json_start:json_end]
                execution_plan = json.loads(json_str)
            else:
                raise ValueError("No JSON found in the response")

            # Execute commands
            if "commands" in execution_plan and execution_plan["commands"]:
                console.print("\n[bold green]Executing commands:[/bold green]")

                for cmd_info in execution_plan["commands"]:
                    command = cmd_info.get("command", "")
                    description = cmd_info.get("description", "No description")

                    console.print(f"\n[bold cyan]Command:[/bold cyan] {command}")
                    console.print(f"[italic]{description}[/italic]")

                    # Log the command in the markdown log
                    self.log_capture.log_command(command, description=description)

                    # Execute the command
                    # Check if this is a code generator command that should be avoided
                    is_code_generator = any(cmd in command for cmd in [
                        "create-react-app",
                        "npx create-",
                        "yarn create",
                        "django-admin startproject",
                        "rails new",
                        "vue create",
                        "ng new"
                    ])

                    # For package installation commands, don't capture output to show real-time progress
                    is_package_install = any(cmd in command for cmd in [
                        "npm install",
                        "yarn add",
                        "pip install",
                        "mvn install",
                        "gradle build",
                        "cargo build"
                    ])

                    if is_code_generator:
                        console.print("[bold red]Warning: Code generator commands should be avoided.[/bold red]")
                        console.print("[yellow]The agent should generate all code files directly instead of using external generators.[/yellow]")
                        console.print("[yellow]Proceeding with the command, but consider modifying your approach.[/yellow]\n")
                        result = self.executor.execute_command(command, capture_output=False)
                    elif is_package_install:
                        console.print("[yellow]This is a package installation command that may take several minutes.[/yellow]")
                        console.print("[yellow]Output will be displayed in real-time. Please be patient...[/yellow]\n")
                        result = self.executor.execute_command(command, capture_output=False)
                    else:
                        result = self.executor.execute_command(command)

                    # Display the result
                    console.print(Markdown(format_command_output(result)))

            # Implement code changes
            if "code_changes" in execution_plan and execution_plan["code_changes"]:
                console.print("\n[bold green]Implementing code changes:[/bold green]")

                for change in execution_plan["code_changes"]:
                    file_path = change.get("file_path", "")
                    description = change.get("description", "No description")

                    console.print(f"\n[bold cyan]File:[/bold cyan] {file_path}")
                    console.print(f"[italic]{description}[/italic]")

                    # Determine the language from the file extension
                    language = None
                    if "." in file_path:
                        extension = file_path.split(".")[-1]
                        language_map = {
                            "py": "python",
                            "js": "javascript",
                            "ts": "typescript",
                            "html": "html",
                            "css": "css",
                            "java": "java",
                            "c": "c",
                            "cpp": "c++",
                            "go": "go",
                            "rs": "rust",
                            "rb": "ruby",
                            "php": "php",
                            "sh": "bash",
                            "md": "markdown"
                        }
                        language = language_map.get(extension.lower())

                    # Generate the file
                    result = self.executor.generate_file(file_path, description, language)

                    if result["success"]:
                        console.print(f"[bold green]Generated file:[/bold green] {result['file_path']}")
                        console.print(f"Preview: {result['content_preview']}")

                        # Log the file generation in the markdown log
                        self.log_capture.log_file_operation("create", result['file_path'], result['content_preview'])
                    else:
                        console.print(f"[bold red]Error generating file:[/bold red] {result.get('error', 'Unknown error')}")

                        # Log the file generation error in the markdown log
                        self.log_capture.log_error(result.get('error', 'Unknown error'),
                                                 context=f"File generation: {file_path}")

            # Commit the changes
            console.print("\n[bold yellow]Committing changes...[/bold yellow]")
            commit_message = f"Implement {task.get('task name', task.get('name', f'Task {task_index+1}'))}"
            commit_result = self.git_manager.commit(commit_message)

            if commit_result["success"]:
                console.print(f"[bold green]{commit_result['message']}[/bold green]")
            else:
                console.print(f"[bold red]Error committing changes:[/bold red] {commit_result.get('error', 'Unknown error')}")

            # Save project state to the project directory
            state_file = self.project_dir / "project_state.json"
            self._save_project_state(state_file)

            # Add a README if it doesn't exist
            readme_path = self.project_dir / "README.md"
            if not readme_path.exists():
                console.print("\n[bold yellow]Creating README.md...[/bold yellow]")
                readme_content = f"""# {self.project_name.replace('-', ' ').title()}

This project was generated by AI Code Agent.

## Project Description

{self.project_description.get('raw_description', 'No description available.')}

## Project Structure

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

                try:
                    with open(readme_path, 'w') as f:
                        f.write(readme_content)
                    console.print(f"[bold green]Created README.md[/bold green]")

                    # Commit the README
                    self.git_manager.add_files([readme_path])
                    self.git_manager.commit("Add README.md")
                except Exception as e:
                    console.print(f"[bold red]Error creating README:[/bold red] {str(e)}")

            return {
                "success": True,
                "task_index": task_index,
                "branch": branch_name,
                "commands_executed": len(execution_plan.get("commands", [])),
                "code_changes": len(execution_plan.get("code_changes", []))
            }
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            console.print(f"[bold red]Error executing task:[/bold red] {str(e)}")
            return {"success": False, "error": str(e)}

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

            # Deploy the project
            result = deployer.deploy_locally()

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
    if not Confirm.ask("Continue with processing project description?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    result = agent.process_project_description(prompt)
    if not result["success"]:
        console.print(f"[bold red]Error processing project description:[/bold red] {result.get('error', 'Unknown error')}")
        return False

    # Step 2: Set up project structure
    console.print("\n[bold yellow]Step 2: Setting up project structure...[/bold yellow]")
    if not Confirm.ask("Continue with setting up project structure?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    setup_result = agent.setup_project()
    if not setup_result["success"]:
        console.print(f"[bold red]Error setting up project:[/bold red] {setup_result.get('error', 'Unknown error')}")
        return False

    # Step 3: Execute tasks
    for i in range(len(agent.tasks)):
        task = agent.tasks[i]
        task_name = task.get('task name', task.get('name', f'Task {i+1}'))
        console.print(f"\n[bold yellow]Step 3.{i+1}: Executing task: {task_name}[/bold yellow]")

        if not Confirm.ask(f"Continue with executing task: {task_name}?"):
            console.print("[bold yellow]Skipping this task.[/bold yellow]")
            continue

        task_result = agent.execute_task(i)
        if not task_result["success"]:
            console.print(f"[bold red]Error executing task {i+1}:[/bold red] {task_result.get('error', 'Unknown error')}")
            if not Confirm.ask("Continue with the next task?"):
                console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
                return False

    # Step 4: Review code
    console.print("\n[bold yellow]Step 4: Reviewing code...[/bold yellow]")
    if not Confirm.ask("Continue with code review?"):
        console.print("[bold yellow]Skipping code review.[/bold yellow]")
    else:
        review_result = agent.review_code(auto_fix=False)
        if not review_result["success"]:
            console.print(f"[bold red]Error reviewing code:[/bold red] {review_result.get('error', 'Unknown error')}")

    # Step 5: Fix code issues
    console.print("\n[bold yellow]Step 5: Fixing code issues...[/bold yellow]")
    if not Confirm.ask("Continue with fixing code issues?"):
        console.print("[bold yellow]Skipping code fixes.[/bold yellow]")
    else:
        fix_result = agent.review_code(auto_fix=True)
        if not fix_result["success"]:
            console.print(f"[bold red]Error fixing code:[/bold red] {fix_result.get('error', 'Unknown error')}")

    # Step 6: Open in editor
    if not no_editor:
        console.print("\n[bold yellow]Step 6: Opening in code editor...[/bold yellow]")
        if not Confirm.ask("Open project in code editor?"):
            console.print("[bold yellow]Skipping opening in editor.[/bold yellow]")
        else:
            agent.open_in_editor()

    # Step 7: Deploy locally
    if not no_deploy:
        console.print("\n[bold yellow]Step 7: Deploying locally...[/bold yellow]")
        if not Confirm.ask("Deploy project locally?"):
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
    if not Confirm.ask("Continue with analyzing project?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    # Step 2: Generate fixes
    console.print("\n[bold yellow]Step 2: Generating fixes...[/bold yellow]")
    if not Confirm.ask("Continue with generating fixes?"):
        console.print("[bold yellow]Operation cancelled by user.[/bold yellow]")
        return False

    # Step 3: Apply fixes
    console.print("\n[bold yellow]Step 3: Applying fixes...[/bold yellow]")
    if not Confirm.ask("Continue with applying fixes?"):
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
▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖     ▗▄▄▄▖ ▗▄▄▖▗▖  ▗▖▗▄▄▖ ▗▄▄▄▖
▐▌ ▐▌▐▌   ▐▌        ▐▌   ▐▌    ▝▚▞▘ ▐▌ ▐▌  █  
▐▛▀▚▖▐▛▀▀▘▐▛▀▀▘     ▐▛▀▀▘▐▌▝▜▌  ▐▌  ▐▛▀▘   █  
▐▙▄▞▘▐▙▄▄▖▐▙▄▄▖     ▐▙▄▄▖▝▚▄▞▘  ▐▌  ▐▌     █  
    """

    styled_final = Text(final_art)
    styled_final.stylize("green")
    animation_console.print(styled_final)

def main():
    """
    Main entry point for the script.
    """
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
    parser.add_argument("--no-animation", action="store_true", help="Skip the initial animation")

    args = parser.parse_args()

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
