"""
Command execution module for the AI Code Agent.
"""
import logging
import subprocess
import os
from typing import Dict, List, Optional, Union
from pathlib import Path

from models.gemini_client import GeminiClient
from agent.utils import extract_code_from_markdown
from agent.package_handler import PackageHandler
from agent.log_capture import MarkdownLogCapture

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Executor:
    """
    Responsible for executing commands and generating code.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None, working_dir: Optional[Path] = None):
        """
        Initialize the executor.

        Args:
            gemini_client: GeminiClient instance for AI capabilities
            working_dir: Working directory for command execution
        """
        self.gemini_client = gemini_client or GeminiClient()
        self.working_dir = working_dir or Path.cwd()
        self.command_history = []

        # Initialize log capture
        log_dir = self.working_dir / "logs"
        self.log_capture = MarkdownLogCapture(log_dir, "execution_log")
        self.log_capture.start_capture()

    def execute_command(self, command: str, capture_output: bool = True, timeout: int = 600) -> Dict:
        """
        Execute a shell command.

        Args:
            command: Command to execute
            capture_output: Whether to capture and return command output
            timeout: Timeout in seconds (default: 10 minutes)

        Returns:
            Dictionary with command execution results
        """
        logger.info(f"Executing command: {command}")
        self.command_history.append(command)

        # Log the command to the markdown log
        self.log_capture.log_command(command)

        # Check if this is a known project creation command that should be avoided
        is_code_generator = any(cmd in command for cmd in [
            "create-react-app",
            "npx create-",
            "yarn create",
            "django-admin startproject",
            "rails new",
            "vue create",
            "ng new"
        ])

        # Check if code generators are disabled via environment variable
        import os
        no_code_generators = os.environ.get("NO_CODE_GENERATORS", "").lower() == "true"

        # Handle code generators based on settings
        if is_code_generator:
            if no_code_generators:
                logger.warning(f"Code generator command blocked: {command}")
                logger.warning("Code generators are disabled. Command will not be executed.")
                print(f"\n[WARNING] Code generator command blocked: {command}")
                print("Code generators are disabled. The command will not be executed.")
                print("The agent should generate all files directly instead.\n")

                # Return a simulated result without executing the command
                return {
                    "command": command,
                    "success": False,
                    "return_code": 1,
                    "stdout": "",
                    "stderr": "Code generator commands are disabled. Please generate files directly.",
                    "error": "Code generators are disabled"
                }
            else:
                logger.warning(f"Code generator command detected: {command}")
                logger.warning("Code generators should be avoided in favor of direct file creation.")
                print(f"\n[WARNING] Code generator command detected: {command}")
                print("This type of command should be avoided in favor of direct file creation.")
                print("The agent will proceed, but consider modifying your approach to use direct file creation instead.\n")

        # Check if this is a known project creation command
        is_project_creation = is_code_generator or any(cmd in command for cmd in [
            "npm init -y",
            "cargo init",
            "mvn archetype:generate"
        ])

        # Modify project creation commands to avoid nested projects
        if is_code_generator and not no_code_generators:
            # Extract the project name from the command
            project_name = self._extract_project_name_from_command(command)

            if project_name:
                # Check if the command would create a nested project
                if Path(project_name).exists() and Path(project_name).is_dir():
                    logger.warning(f"Detected potential nested project creation: {command}")

                    # Modify the command to create in the current directory
                    if "create-react-app" in command or "npx create-" in command:
                        # For React and other npx creators, use the dot notation
                        command = command.replace(project_name, ".")
                        logger.info(f"Modified command to: {command}")
                    elif "django-admin startproject" in command:
                        # For Django, add the current directory parameter
                        command = f"{command} ."
                        logger.info(f"Modified command to: {command}")
                    elif "rails new" in command or "vue create" in command or "ng new" in command:
                        # For Rails, Vue, and Angular, use the dot notation
                        command = command.replace(project_name, ".")
                        logger.info(f"Modified command to: {command}")

        # Check if this is a known long-running command
        is_long_running = is_project_creation or any(cmd in command for cmd in [
            "npm install",
            "yarn install",
            "pip install",
            "mvn install",
            "gradle build",
            "cargo build"
        ])

        # Handle project creation commands specially
        if is_project_creation:
            # Extract the project name from the command
            project_name = self._extract_project_name_from_command(command)

            # Check if we're already in a directory with that name
            current_dir_name = Path(self.working_dir).name

            if project_name and project_name != current_dir_name:
                logger.info(f"Project creation command detected. Project name: {project_name}")
                logger.info(f"Current directory: {current_dir_name}")

                # If we're not in a directory with the project name, we have two options:
                # 1. Change the command to create in the current directory
                # 2. Change our working directory to the parent and let the command create a new directory

                # Option 1: Modify the command to create in the current directory
                if "create-react-app" in command or "npx create-" in command:
                    # For React apps, we can use '.' to create in the current directory
                    modified_command = command.replace(project_name, ".")
                    logger.info(f"Modified command to create in current directory: {modified_command}")
                    command = modified_command
                    print(f"\nModified command to create in current directory: {command}")

        if is_long_running:
            logger.info(f"Detected long-running command: {command}")
            logger.info("This may take several minutes. Please be patient...")
            print(f"\nExecuting long-running command: {command}")
            print("This may take several minutes. Please be patient...\n")

        try:
            # For long-running commands, show output in real-time
            if is_long_running and not capture_output:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self.working_dir,
                    text=True
                )
                process.wait(timeout=timeout)

                result = {
                    "command": command,
                    "return_code": process.returncode,
                    "success": process.returncode == 0,
                    "long_running": True
                }

                return result

            # For normal commands or when capturing output
            process = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )

            result = {
                "command": command,
                "return_code": process.returncode,
                "success": process.returncode == 0
            }

            if capture_output:
                result["stdout"] = process.stdout
                result["stderr"] = process.stderr

                # Log the command output
                output = process.stdout + ("\n" + process.stderr if process.stderr else "")
                self.log_capture.log_output(output, success=process.returncode == 0)

            return result
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout} seconds: {command}")
            error_msg = f"Command timed out after {timeout} seconds"

            # Log the timeout error
            self.log_capture.log_error(error_msg, context=f"Command: {command}")

            return {
                "command": command,
                "error": error_msg,
                "success": False,
                "timed_out": True
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            error_msg = str(e)

            # Log the execution error
            self.log_capture.log_error(error_msg, context=f"Command: {command}")

            return {
                "command": command,
                "error": error_msg,
                "success": False
            }

    def generate_file(self, file_path: Union[str, Path], content_description: str, language: Optional[str] = None) -> Dict:
        """
        Generate a file with AI-generated content.

        Args:
            file_path: Path to the file to create
            content_description: Description of the file content to generate
            language: Programming language for the file

        Returns:
            Dictionary with file generation results
        """
        # Convert to Path object
        file_path = Path(file_path)

        # Ensure the file path is relative to the working directory
        if file_path.is_absolute():
            # If it's an absolute path, make sure it's within the working directory
            try:
                file_path = file_path.relative_to(self.working_dir)
            except ValueError:
                # If it's not within the working directory, use just the filename
                logger.warning(f"File path {file_path} is outside working directory {self.working_dir}")
                file_path = Path(file_path.name)

        # Check if the file path contains a project name that would create a nested project
        # For example, if file_path is 'my-app/src/App.js' and we're already in a project directory
        parts = file_path.parts
        if len(parts) > 1:
            potential_project_name = parts[0]
            # Check if this looks like a project name (common directories like src, public, etc.)
            common_project_dirs = ['src', 'public', 'app', 'components', 'pages', 'styles', 'assets', 'images']

            # If the first part is a common project directory and we're already in a project directory
            # then we're probably in the right place
            if potential_project_name.lower() in common_project_dirs:
                # This is fine, keep the path as is
                pass
            # If the first part is not a common directory and contains a dash (like 'my-app')
            # it might be a nested project
            elif '-' in potential_project_name or potential_project_name == self.working_dir.name:
                # Check if this would create a nested project with the same name as the working directory
                if potential_project_name == self.working_dir.name:
                    # Remove the project name from the path to avoid nesting
                    logger.warning(f"Detected potential nested project in path: {file_path}")
                    logger.warning(f"Removing project name from path to avoid nesting")
                    file_path = Path(*parts[1:])
                    if not file_path.parts:  # If we removed everything, use the filename only
                        file_path = Path(parts[-1])

        # Construct the full path within the working directory
        full_path = self.working_dir / file_path

        # Determine language from file extension if not provided
        if not language:
            extension = file_path.suffix.lower()
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".jsx": "javascript",
                ".ts": "typescript",
                ".tsx": "typescript",
                ".html": "html",
                ".css": "css",
                ".scss": "css",
                ".json": "json",
                ".java": "java",
                ".c": "c",
                ".cpp": "c++",
                ".go": "go",
                ".rs": "rust",
                ".rb": "ruby",
                ".php": "php",
                ".sh": "bash",
                ".md": "markdown"
            }
            language = language_map.get(extension, "text")

        logger.info(f"Generating {language} file: {full_path}")

        try:
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate content
            content = self.gemini_client.generate_code(content_description, language)

            # Extract code from markdown if needed
            clean_content = extract_code_from_markdown(content)

            # Write to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)

            # Log the file creation
            content_preview = content[:200] + ("..." if len(content) > 200 else "")
            self.log_capture.log_file_operation("create", str(full_path), content_preview)

            return {
                "file_path": str(full_path),
                "relative_path": str(file_path),
                "language": language,
                "success": True,
                "content_preview": content_preview
            }
        except Exception as e:
            logger.error(f"Error generating file {full_path}: {e}")
            error_msg = str(e)

            # Log the file generation error
            self.log_capture.log_error(error_msg, context=f"File: {full_path}")

            return {
                "file_path": str(full_path),
                "relative_path": str(file_path),
                "error": error_msg,
                "success": False
            }

    def setup_project_structure(self, structure: Dict) -> Dict:
        """
        Set up a project directory structure.

        Args:
            structure: Dictionary describing the project structure

        Returns:
            Dictionary with setup results
        """
        results = {
            "created_directories": [],
            "created_files": [],
            "errors": []
        }

        try:
            # Create directories
            for directory in structure.get("directories", []):
                # Convert to Path object
                dir_path = Path(directory)

                # Ensure the directory path is relative to the working directory
                if dir_path.is_absolute():
                    try:
                        dir_path = dir_path.relative_to(self.working_dir)
                    except ValueError:
                        # If it's not within the working directory, use just the directory name
                        logger.warning(f"Directory path {dir_path} is outside working directory {self.working_dir}")
                        dir_path = Path(dir_path.name)

                # Check if the directory path would create a nested project
                parts = dir_path.parts
                if len(parts) > 0:
                    potential_project_name = parts[0]
                    # Check if this looks like a project name (not a common directory)
                    common_project_dirs = ['src', 'public', 'app', 'components', 'pages', 'styles', 'assets', 'images']

                    # If the first part is not a common directory and contains a dash (like 'my-app')
                    # or is the same as the working directory name, it might be a nested project
                    if (potential_project_name not in common_project_dirs and
                        ('-' in potential_project_name or potential_project_name == self.working_dir.name)):
                        # Check if this would create a nested project with the same name as the working directory
                        if potential_project_name == self.working_dir.name:
                            # Remove the project name from the path to avoid nesting
                            logger.warning(f"Detected potential nested project in directory path: {dir_path}")
                            logger.warning(f"Removing project name from path to avoid nesting")
                            if len(parts) > 1:
                                dir_path = Path(*parts[1:])
                            else:
                                # If we removed everything, use a default directory
                                dir_path = Path('src')

                # Construct the full path within the working directory
                full_dir_path = self.working_dir / dir_path

                try:
                    full_dir_path.mkdir(parents=True, exist_ok=True)
                    results["created_directories"].append(str(full_dir_path))
                    logger.info(f"Created directory: {full_dir_path}")
                except Exception as e:
                    results["errors"].append(f"Error creating directory {full_dir_path}: {str(e)}")

            # Create files
            for file_info in structure.get("files", []):
                try:
                    # Get the file path from the file info
                    file_path = file_info["path"]

                    # Generate the file using our improved generate_file method
                    # which will handle path normalization
                    file_result = self.generate_file(
                        file_path,  # Just pass the path, generate_file will handle normalization
                        file_info["description"],
                        file_info.get("language")
                    )

                    if file_result["success"]:
                        results["created_files"].append(file_result["file_path"])
                    else:
                        results["errors"].append(f"Error creating file {file_info['path']}: {file_result.get('error')}")
                except Exception as e:
                    results["errors"].append(f"Error processing file {file_info['path']}: {str(e)}")

            # Ensure package files are created based on project type
            package_handler = PackageHandler(self.working_dir)
            package_results = package_handler.ensure_package_files(structure)

            # Add package files to results
            results["created_files"].extend(package_results.get("created_files", []))
            results["errors"].extend(package_results.get("errors", []))

            return results
        except Exception as e:
            logger.error(f"Error setting up project structure: {e}")
            results["errors"].append(f"General error: {str(e)}")
            return results

    def _extract_project_name_from_command(self, command: str) -> Optional[str]:
        """
        Extract the project name from a project creation command.

        Args:
            command: The command string

        Returns:
            The project name or None if it couldn't be extracted
        """
        # For create-react-app and similar commands
        if "create-react-app" in command or "npx create-" in command:
            parts = command.split()
            # The last part is usually the project name
            for part in reversed(parts):
                # Skip options (starting with -)
                if not part.startswith("-") and part != "create-react-app" and "npx" not in part and "create-" not in part:
                    # Check if this is a valid project name (not a path with slashes)
                    if "/" not in part and "\\" not in part and part != ".":
                        return part

        # For django-admin startproject
        if "django-admin startproject" in command:
            parts = command.split()
            try:
                idx = parts.index("startproject")
                if idx + 1 < len(parts):
                    project_name = parts[idx + 1]
                    # Check if this is a valid project name (not a path with slashes)
                    if "/" not in project_name and "\\" not in project_name and project_name != ".":
                        return project_name
            except ValueError:
                pass

        # For cargo init
        if "cargo init" in command:
            parts = command.split()
            # Check if there's a name after 'init'
            try:
                idx = parts.index("init")
                if idx + 1 < len(parts) and not parts[idx + 1].startswith("--"):
                    project_name = parts[idx + 1]
                    # Check if this is a valid project name (not a path with slashes)
                    if "/" not in project_name and "\\" not in project_name and project_name != ".":
                        return project_name
            except ValueError:
                pass

        return None

    def get_command_history(self) -> List[str]:
        """
        Get the history of executed commands.

        Returns:
            List of executed commands
        """
        return self.command_history

    def __del__(self):
        """
        Clean up resources when the executor is deleted.
        """
        # Stop log capture
        if hasattr(self, 'log_capture'):
            self.log_capture.stop_capture()

    def get_environment_info(self) -> Dict:
        """
        Get information about the execution environment.

        Returns:
            Dictionary with environment information
        """
        import sys
        return {
            "working_dir": str(self.working_dir),
            "python_version": sys.version,
            "os_name": os.name,
            "platform": sys.platform,
            "environment_variables": dict(os.environ)
        }
