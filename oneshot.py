#!/usr/bin/env python3
"""
One-shot script for end-to-end project generation and deployment.
This script will:
1. Generate a project from a description
2. Set up the project structure
3. Implement all tasks
4. Review and fix code issues
5. Open the project in a code editor
6. Deploy the project locally
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from main import CodeAgent
from config import OUTPUT_DIR, ENABLE_SCREENSHOTS, OPERATION_MAX_RETRIES, OPERATION_RETRY_DELAY, OPERATION_BACKOFF_FACTOR
from agent.log_capture import MarkdownLogCapture
from agent.consolidated_log import ConsolidatedLogManager
from agent.retry_mechanism import RetryManager
from agent.screenshot_utils import ScreenshotManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("oneshot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize console for rich output
console = Console()

def oneshot(description: str, output_dir: Optional[Path] = None, open_editor: bool = True, deploy: bool = True,
           project_name: Optional[str] = None, no_code_generators: bool = True, enable_screenshots: bool = ENABLE_SCREENSHOTS) -> bool:
    """
    Run the entire project generation and deployment process in one shot.

    Args:
        description: Project description
        output_dir: Output directory for the project
        open_editor: Whether to open the project in a code editor
        deploy: Whether to deploy the project locally
        project_name: Optional project name to use (if not provided, will be derived from description)
        no_code_generators: Whether to disable code generators completely (default: True)
        enable_screenshots: Whether to enable screenshot capture and analysis

    Returns:
        True if successful, False otherwise
    """
    console.print(Panel("[bold blue]AI Code Agent - One-Shot Mode[/bold blue]"))
    console.print("This will generate, implement, review, fix, and deploy a project in one go.")
    console.print("")

    # Initialize log capture for the oneshot process
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    log_capture = MarkdownLogCapture(log_dir, "oneshot_log")
    log_capture.start_capture()
    log_capture.log_section("Oneshot Mode", f"Project description: {description}")

    # Initialize the consolidated log manager
    consolidated_log = ConsolidatedLogManager(log_dir)
    consolidated_log.log_section("Oneshot Mode", f"Project description: {description}")

    # Initialize the retry manager
    retry_manager = RetryManager(
        max_retries=OPERATION_MAX_RETRIES,
        initial_delay=OPERATION_RETRY_DELAY,
        backoff_factor=OPERATION_BACKOFF_FACTOR
    )

    # Initialize the screenshot manager if enabled
    screenshot_manager = None
    if enable_screenshots:
        screenshot_manager = ScreenshotManager()
        consolidated_log.log_message("Screenshot capture and analysis enabled.")

    try:
        # Initialize the agent
        agent = CodeAgent(output_dir)

        # Set environment variables to control code generation behavior
        import os
        if no_code_generators:
            os.environ["NO_CODE_GENERATORS"] = "true"
            console.print("[yellow]Code generators are disabled. All code will be generated directly.[/yellow]")

        # If project_name is provided, set it directly to avoid creating a new folder
        if project_name:
            agent.project_name = project_name
            console.print(f"[yellow]Using provided project name: {project_name}[/yellow]")

        # Step 1: Process the project description
        console.print("[bold yellow]Step 1: Processing project description...[/bold yellow]")
        log_capture.log_section("Step 1: Processing Project Description")
        consolidated_log.log_section("Step 1: Processing Project Description", "Starting to process the project description and extract key information.")
        result = agent.process_project_description(description)

        if not result["success"]:
            console.print(f"[bold red]Error processing project description:[/bold red] {result.get('error', 'Unknown error')}")
            consolidated_log.log_error(f"Error processing project description: {result.get('error', 'Unknown error')}")
            return False

        # Log the successful completion of step 1
        consolidated_log.log_message("✅ Successfully processed project description.")
        consolidated_log.log_message(f"Project name: {agent.project_name}")
        if hasattr(agent, 'project_plan') and agent.project_plan:
            consolidated_log.log_message(f"Project plan summary: {agent.project_plan.get('overview', 'No overview available')}")

        # Step 2: Set up the project structure
        console.print("\n[bold yellow]Step 2: Setting up project structure...[/bold yellow]")
        log_capture.log_section("Step 2: Setting Up Project Structure")
        consolidated_log.log_section("Step 2: Setting Up Project Structure", "Creating the initial project structure and directories.")
        setup_result = agent.setup_project()

        if not setup_result["success"]:
            console.print(f"[bold red]Error setting up project:[/bold red] {setup_result.get('error', 'Unknown error')}")
            consolidated_log.log_error(f"Error setting up project: {setup_result.get('error', 'Unknown error')}")
            return False

        # Log the successful completion of step 2
        consolidated_log.log_message("✅ Successfully set up project structure.")
        if hasattr(agent, 'project_dir') and agent.project_dir:
            consolidated_log.log_message(f"Project directory: {agent.project_dir}")

        # Step 3: Execute all tasks
        console.print("\n[bold yellow]Step 3: Implementing all tasks...[/bold yellow]")
        log_capture.log_section("Step 3: Implementing All Tasks")
        consolidated_log.log_section("Step 3: Implementing All Tasks", f"Implementing {len(agent.tasks)} tasks to build the project.")

        # Print a note about direct code generation
        console.print("\n[bold cyan]Note about code generation:[/bold cyan]")
        if no_code_generators:
            console.print("[bold green]Code generators are disabled.[/bold green] The agent will generate all code directly.")
            console.print("This means it will create all necessary files manually instead of using tools like 'create-react-app'.")
            console.print("All configuration files (package.json, etc.) will be created with appropriate content.")
            console.print("Only necessary package installation commands will be used.")
            console.print("[bold yellow]This ensures only ONE project is created in the output directory.[/bold yellow]\n")
        else:
            console.print("The agent may use code generators but will modify commands to create in the current directory.")
            console.print("For example, 'npx create-react-app my-app' will be changed to 'npx create-react-app .'")
            console.print("This ensures only ONE project is created in the output directory.\n")

        # Add a warning about nested projects
        console.print("[bold cyan]Note about nested projects:[/bold cyan]")
        console.print("[yellow]The agent will detect and prevent nested project creation.[/yellow]")
        console.print("If a file or directory path would create a nested project, it will be modified.")
        console.print("For example, 'my-app/src/App.js' would become 'src/App.js' if we're already in the 'my-app' directory.\n")

        for i, task in enumerate(agent.tasks):
            task_name = task.get('task name', task.get('name', f'Task {i+1}'))
            console.print(f"\nImplementing task {i+1}/{len(agent.tasks)}: [bold]{task_name}[/bold]")
            log_capture.log_section(f"Task {i+1}/{len(agent.tasks)}: {task_name}",
                                   f"Description: {task.get('description', 'No description')}")
            consolidated_log.log_section(f"Task {i+1}/{len(agent.tasks)}: {task_name}",
                                   f"Description: {task.get('description', 'No description')}")

            # Check if this is likely a project initialization task
            is_init_task = any(keyword in task_name.lower() for keyword in [
                "init", "create", "setup", "scaffold", "generate", "bootstrap"
            ])

            if is_init_task:
                console.print("[yellow]This appears to be a project initialization task.[/yellow]")
                if no_code_generators:
                    console.print("[bold green]Code generators are disabled.[/bold green] The agent will generate all files directly.")
                    console.print("[yellow]This ensures only ONE project is created in the output directory.[/yellow]")
                else:
                    console.print("[yellow]The agent will modify any code generator commands to create in the current directory.[/yellow]")
                    console.print("[yellow]This ensures only ONE project is created in the output directory.[/yellow]")
                console.print("[yellow]Please be patient while the agent generates the code...[/yellow]")

            # Execute the task with retry mechanism
            success, task_result, attempts = retry_manager.with_retry(agent.execute_task, i)

            # Log retry attempts if more than one
            if attempts > 1:
                console.print(f"[yellow]Task required {attempts} attempts to complete[/yellow]")
                consolidated_log.log_message(f"Task required {attempts} attempts to complete")

            # Take a screenshot after task execution if enabled
            if enable_screenshots:
                screenshot_name = f"task_{i+1}_of_{len(agent.tasks)}"
                screenshot_result = screenshot_manager.capture_screenshot(screenshot_name)
                if screenshot_result[0]:  # If screenshot was successful
                    screenshot_path = screenshot_result[1]
                    analysis_result = screenshot_manager.analyze_screenshot(screenshot_path)
                    if analysis_result["success"] and analysis_result["has_errors"]:
                        consolidated_log.log_message(f"⚠️ Errors detected in screenshot after task {i+1}")
                        for error in analysis_result["errors"]:
                            consolidated_log.log_message(f"Error: {error['pattern']} - {error['line']}")

            if not task_result["success"]:
                error_msg = f"Error executing task {i+1}: {task_result.get('error', 'Unknown error')}"
                console.print(f"[bold red]{error_msg}[/bold red]")
                log_capture.log_error(task_result.get('error', 'Unknown error'),
                                    context=f"Task {i+1}: {task_name}")
                consolidated_log.log_error(f"Error executing task {i+1}/{len(agent.tasks)}: {task_name}",
                                        f"Error: {task_result.get('error', 'Unknown error')}")
                # Continue with the next task even if this one failed
            else:
                log_capture.log_message(f"Task {i+1} executed successfully")
                consolidated_log.log_message(f"✅ Successfully completed task {i+1}/{len(agent.tasks)}: {task_name}")
                if 'output' in task_result:
                    consolidated_log.log_message(f"Task output summary: {task_result['output'][:200]}..." if len(task_result.get('output', '')) > 200 else f"Task output: {task_result.get('output', 'No output')}")

        # Step 4: Deploy locally to install packages (if requested)
        if deploy:
            console.print("\n[bold yellow]Step 4: Installing packages...[/bold yellow]")
            console.print("[yellow]Installing packages before code review to ensure all dependencies are available.[/yellow]")
            log_capture.log_section("Step 4: Installing Packages",
                                 "Installing packages before code review to ensure all dependencies are available.")
            consolidated_log.log_section("Step 4: Installing Packages",
                                 "Installing packages before code review to ensure all dependencies are available.")
            # Deploy the project with retry mechanism
            success, deploy_result, attempts = retry_manager.with_retry(agent.deploy_locally)

            # Log retry attempts if more than one
            if attempts > 1:
                console.print(f"[yellow]Deployment required {attempts} attempts to complete[/yellow]")
                consolidated_log.log_message(f"Deployment required {attempts} attempts to complete")

            # Take a screenshot after deployment if enabled
            if enable_screenshots:
                screenshot_result = screenshot_manager.capture_screenshot("after_deployment")
                if screenshot_result[0]:  # If screenshot was successful
                    screenshot_path = screenshot_result[1]
                    consolidated_log.log_message(f"Deployment screenshot saved to: {screenshot_path}")

                    # Analyze the screenshot for errors
                    analysis_result = screenshot_manager.analyze_screenshot(screenshot_path)
                    if analysis_result["success"] and analysis_result["has_errors"]:
                        consolidated_log.log_message("⚠️ Errors detected in deployment screenshot")
                        for error in analysis_result["errors"]:
                            consolidated_log.log_message(f"Error: {error['pattern']} - {error['line']}")

            if not deploy_result["success"]:
                console.print(f"[bold red]Error installing packages:[/bold red] {deploy_result.get('error', 'Unknown error')}")
                consolidated_log.log_error(f"Error installing packages: {deploy_result.get('error', 'Unknown error')}")
                # Continue even if package installation failed
            else:
                console.print("\n[bold green]Package installation successful![/bold green]")
                consolidated_log.log_message("✅ Successfully installed packages.")
                if "start_command" in deploy_result:
                    console.print(f"To start the application, run: [bold yellow]{deploy_result['start_command']}[/bold yellow]")

        # Step 5: Review code
        console.print("\n[bold yellow]Step 5: Reviewing code...[/bold yellow]")
        log_capture.log_section("Step 5: Reviewing Code")
        consolidated_log.log_section("Step 5: Reviewing Code", "Analyzing code quality and identifying potential issues.")
        # Review code with retry mechanism
        success, review_result, attempts = retry_manager.with_retry(agent.review_code, auto_fix=False)

        # Log retry attempts if more than one
        if attempts > 1:
            console.print(f"[yellow]Code review required {attempts} attempts to complete[/yellow]")
            consolidated_log.log_message(f"Code review required {attempts} attempts to complete")

        # Take a screenshot after code review if enabled
        if enable_screenshots:
            screenshot_result = screenshot_manager.capture_screenshot("after_code_review")
            if screenshot_result[0]:  # If screenshot was successful
                screenshot_path = screenshot_result[1]
                consolidated_log.log_message(f"Code review screenshot saved to: {screenshot_path}")

        if not review_result["success"]:
            console.print(f"[bold red]Error reviewing code:[/bold red] {review_result.get('error', 'Unknown error')}")
            consolidated_log.log_error(f"Error reviewing code: {review_result.get('error', 'Unknown error')}")
            # Continue even if review failed
        else:
            consolidated_log.log_message("✅ Successfully reviewed code.")
            if "report" in review_result:
                consolidated_log.log_message("Review summary: " + review_result["report"][:200] + "..." if len(review_result.get("report", "")) > 200 else "Review summary: " + review_result.get("report", "No report available"))

        # Step 6: Fix code issues
        console.print("\n[bold yellow]Step 6: Fixing code issues...[/bold yellow]")
        log_capture.log_section("Step 6: Fixing Code Issues")
        consolidated_log.log_section("Step 6: Fixing Code Issues", "Automatically fixing identified code issues.")
        # Fix code issues with retry mechanism
        success, fix_result, attempts = retry_manager.with_retry(agent.review_code, auto_fix=True)

        # Log retry attempts if more than one
        if attempts > 1:
            console.print(f"[yellow]Code fixing required {attempts} attempts to complete[/yellow]")
            consolidated_log.log_message(f"Code fixing required {attempts} attempts to complete")

        # Take a screenshot after code fixing if enabled
        if enable_screenshots:
            screenshot_result = screenshot_manager.capture_screenshot("after_code_fixing")
            if screenshot_result[0]:  # If screenshot was successful
                screenshot_path = screenshot_result[1]
                consolidated_log.log_message(f"Code fixing screenshot saved to: {screenshot_path}")

        if not fix_result["success"]:
            console.print(f"[bold red]Error fixing code:[/bold red] {fix_result.get('error', 'Unknown error')}")
            consolidated_log.log_error(f"Error fixing code: {fix_result.get('error', 'Unknown error')}")
            # Continue even if fixing failed
        else:
            consolidated_log.log_message("✅ Successfully fixed code issues.")
            if "report" in fix_result:
                consolidated_log.log_message("Fix summary: " + fix_result["report"][:200] + "..." if len(fix_result.get("report", "")) > 200 else "Fix summary: " + fix_result.get("report", "No report available"))

        # Step 7: Deploy locally again if needed (if requested)
        if deploy:
            console.print("\n[bold yellow]Step 7: Finalizing deployment...[/bold yellow]")
            console.print("[yellow]Running deployment again to ensure all changes are properly applied.[/yellow]")
            log_capture.log_section("Step 7: Finalizing Deployment",
                                 "Running deployment again to ensure all changes are properly applied.")
            consolidated_log.log_section("Step 7: Finalizing Deployment",
                                 "Running deployment again to ensure all changes are properly applied.")
            # Deploy the project with retry mechanism
            success, deploy_result, attempts = retry_manager.with_retry(agent.deploy_locally)

            # Log retry attempts if more than one
            if attempts > 1:
                console.print(f"[yellow]Final deployment required {attempts} attempts to complete[/yellow]")
                consolidated_log.log_message(f"Final deployment required {attempts} attempts to complete")

            # Take a screenshot after final deployment if enabled
            if enable_screenshots:
                screenshot_result = screenshot_manager.capture_screenshot("after_final_deployment")
                if screenshot_result[0]:  # If screenshot was successful
                    screenshot_path = screenshot_result[1]
                    consolidated_log.log_message(f"Final deployment screenshot saved to: {screenshot_path}")

                    # Monitor for a short period to catch any startup errors
                    console.print("[yellow]Monitoring application startup for errors...[/yellow]")
                    error_reports = screenshot_manager.monitor_for_errors(interval=2, duration=10)
                    if error_reports:
                        console.print(f"[bold red]Detected {len(error_reports)} potential issues during startup[/bold red]")
                        consolidated_log.log_message(f"⚠️ Detected {len(error_reports)} potential issues during startup")

            if not deploy_result["success"]:
                console.print(f"[bold red]Error deploying project:[/bold red] {deploy_result.get('error', 'Unknown error')}")
                consolidated_log.log_error(f"Error deploying project: {deploy_result.get('error', 'Unknown error')}")
                # Continue even if deployment failed
            else:
                console.print("\n[bold green]Deployment successful![/bold green]")
                consolidated_log.log_message("✅ Successfully finalized deployment.")
                if "start_command" in deploy_result:
                    console.print(f"To start the application, run: [bold yellow]{deploy_result['start_command']}[/bold yellow]")
                    consolidated_log.log_message(f"Start command: {deploy_result['start_command']}")
                if "url" in deploy_result and deploy_result["url"]:
                    console.print(f"Application will be available at: [bold blue]{deploy_result['url']}[/bold blue]")
                    consolidated_log.log_message(f"Application URL: {deploy_result['url']}")

        # Step 8: Open in code editor (if requested)
        if open_editor:
            console.print("\n[bold yellow]Step 8: Opening project in code editor...[/bold yellow]")
            log_capture.log_section("Step 8: Opening Project in Code Editor")
            consolidated_log.log_section("Step 8: Opening Project in Code Editor", "Opening the project in the default code editor.")
            agent.open_in_editor()
            consolidated_log.log_message("✅ Opened project in code editor.")

        # Final summary
        console.print("\n[bold green]Project generation complete![/bold green]")
        console.print(f"Project name: [bold]{agent.project_name}[/bold]")
        console.print(f"Project directory: [bold]{agent.project_dir}[/bold]")

        # Log final summary
        log_capture.log_section("Project Generation Complete",
                             f"Project name: {agent.project_name}\n" +
                             f"Project directory: {agent.project_dir}")
        consolidated_log.log_section("Project Generation Complete",
                             f"Project name: {agent.project_name}\n" +
                             f"Project directory: {agent.project_dir}")

        # Stop log capture
        log_capture.stop_capture()
        console.print(f"\n[bold blue]Log saved to:[/bold blue] {log_capture.log_path}")
        console.print(f"\n[bold blue]Consolidated log saved to:[/bold blue] {consolidated_log.log_path}")

        return True
    except Exception as e:
        logger.error(f"Error in oneshot mode: {e}")
        console.print(f"[bold red]Error in oneshot mode:[/bold red] {str(e)}")

        # Log the error
        log_capture.log_error(str(e), context="Oneshot mode")
        log_capture.stop_capture()
        console.print(f"\n[bold blue]Log saved to:[/bold blue] {log_capture.log_path}")

        # Log to consolidated log
        if 'consolidated_log' in locals() and consolidated_log:
            consolidated_log.log_error(f"Unhandled exception in oneshot mode: {e}")
            console.print(f"\n[bold blue]Consolidated log saved to:[/bold blue] {consolidated_log.log_path}")

        return False

def main():
    """Main entry point for the one-shot script."""
    parser = argparse.ArgumentParser(description="Generate and deploy a project in one shot.")
    parser.add_argument("description", help="Project description")
    parser.add_argument("--output", "-o", help="Output directory for the project")
    parser.add_argument("--no-editor", action="store_true", help="Don't open the project in a code editor")
    parser.add_argument("--no-deploy", action="store_true", help="Don't deploy the project locally")
    parser.add_argument("--name", "-n", help="Project name (to avoid creating a new folder)")
    parser.add_argument("--allow-code-generators", action="store_true",
                      help="Allow the use of code generators like create-react-app (not recommended)")

    args = parser.parse_args()

    # Set output directory
    # Always use the output directory by default
    if args.output:
        # If a specific output directory is provided, use it
        output_dir = Path(args.output)
    else:
        # Otherwise, use the default output directory
        output_dir = OUTPUT_DIR

    # Run the oneshot function
    success = oneshot(
        description=args.description,
        output_dir=output_dir,
        open_editor=not args.no_editor,
        deploy=not args.no_deploy,
        project_name=args.name,
        no_code_generators=not args.allow_code_generators
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
