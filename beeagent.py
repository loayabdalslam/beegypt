#!/usr/bin/env python3
"""
BeeAgent - A unified interface for creating or editing projects.

Usage:
    python beeagent.py --path /path/to/project --prompt "Your project description or edit request"
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import run-verify functionality
from run_verify import run_verify_fix

# Import from the AI Code Agent
from fix_project import fix_project
from oneshot import oneshot
from agent.diff_utils import get_project_diff
from agent.consolidated_log import ConsolidatedLogManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize console
console = Console()

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

def create_new_project(path: Path, prompt: str, options: Dict) -> bool:
    """
    Create a new project using oneshot.

    Args:
        path: Path where the project should be created
        prompt: Project description
        options: Additional options

    Returns:
        True if successful, False otherwise
    """
    # Initialize the consolidated log manager
    log_manager = ConsolidatedLogManager(path / "logs")
    log_manager.log_section("Create New Project", f"Project path: {path}\nPrompt: {prompt}")
    console.print(Panel(f"[bold blue]Creating new project at: {path}[/bold blue]"))
    console.print(f"Project description: [italic]{prompt}[/italic]")

    # Ensure the parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Set the output directory to the specified path
    output_dir = path

    # Extract options
    no_editor = options.get("no_editor", False)
    no_deploy = options.get("no_deploy", False)
    no_code_generators = options.get("no_code_generators", False)

    # Create the project using oneshot
    result = oneshot(
        description=prompt,
        output_dir=output_dir,
        open_editor=not no_editor,
        deploy=not no_deploy,
        no_code_generators=no_code_generators
    )

    return result

def edit_existing_project(path: Path, prompt: str, options: Dict) -> bool:
    """
    Edit an existing project using fix_project.

    Args:
        path: Path to the existing project
        prompt: Edit request description
        options: Additional options

    Returns:
        True if successful, False otherwise
    """
    # Initialize the consolidated log manager
    log_manager = ConsolidatedLogManager(path / "logs")
    log_manager.log_section("Edit Existing Project", f"Project path: {path}\nPrompt: {prompt}")
    console.print(Panel(f"[bold blue]Editing existing project at: {path}[/bold blue]"))
    console.print(f"Edit request: [italic]{prompt}[/italic]")

    # Extract options
    no_editor = options.get("no_editor", False)
    no_deploy = options.get("no_deploy", False)

    # Edit the project using fix_project
    result = fix_project(
        project_dir=path,
        problem_description=prompt,
        open_editor=not no_editor,
        deploy=not no_deploy
    )

    return result

def main():
    """Main entry point for the script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="BeeAgent - Create or edit projects with AI")
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

        if is_project:
            # Edit existing project
            console.print("[bold green]Detected existing project[/bold green]")
            result = edit_existing_project(path, args.prompt, options)
        else:
            # Create new project
            console.print("[bold green]Creating new project[/bold green]")
            result = create_new_project(path, args.prompt, options)

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

if __name__ == "__main__":
    sys.exit(main())
