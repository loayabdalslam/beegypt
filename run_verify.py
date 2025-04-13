#!/usr/bin/env python3
"""
Run, verify, and fix a project.
This script will:
1. Run the project
2. Take screenshots and analyze them
3. Fix any issues detected
4. Verify the fixes
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from agent.project_runner import ProjectRunner
from config import ENABLE_SCREENSHOTS, SCREENSHOT_MONITOR_DURATION, SCREENSHOT_INTERVAL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("run_verify.log")
    ]
)
logger = logging.getLogger(__name__)

# Initialize console
console = Console()

def run_verify_fix(project_dir: Path, command: Optional[str] = None, max_cycles: int = 3,
                  monitor_duration: int = SCREENSHOT_MONITOR_DURATION,
                  monitor_interval: float = SCREENSHOT_INTERVAL) -> bool:
    """
    Run, verify, and fix a project.
    
    Args:
        project_dir: Path to the project directory
        command: Command to run the project (if None, will be detected)
        max_cycles: Maximum number of cycles to run
        monitor_duration: Duration to monitor in seconds
        monitor_interval: Interval between screenshots in seconds
        
    Returns:
        True if successful, False otherwise
    """
    console.print(Panel(f"[bold blue]Run, Verify, and Fix: {project_dir}[/bold blue]"))
    
    # Initialize the project runner
    runner = ProjectRunner(project_dir)
    
    # Run the verify-fix cycle
    result = runner.run_verify_fix_cycle(max_cycles=max_cycles)
    
    # Print summary
    if result["success"]:
        console.print(f"[bold green]Success![/bold green] Completed {result['total_cycles']} cycles.")
        return True
    else:
        console.print(f"[bold red]Failed![/bold red] Completed {result['total_cycles']} cycles with {result['failed_cycles']} failures.")
        return False

def main():
    """Main entry point for the script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run, verify, and fix a project")
    parser.add_argument("--project-dir", required=True, help="Path to the project directory")
    parser.add_argument("--command", help="Command to run the project (if not provided, will be detected)")
    parser.add_argument("--max-cycles", type=int, default=3, help="Maximum number of cycles to run")
    parser.add_argument("--monitor-duration", type=int, default=SCREENSHOT_MONITOR_DURATION, 
                        help="Duration to monitor in seconds")
    parser.add_argument("--monitor-interval", type=float, default=SCREENSHOT_INTERVAL,
                        help="Interval between screenshots in seconds")
    parser.add_argument("--no-screenshots", action="store_true", help="Disable screenshots")
    
    args = parser.parse_args()
    
    # Convert path to Path object
    project_dir = Path(args.project_dir).resolve()
    
    # Check if the directory exists
    if not project_dir.exists() or not project_dir.is_dir():
        console.print(f"[bold red]Error:[/bold red] Project directory not found: {project_dir}")
        return 1
        
    # Override screenshot settings if requested
    if args.no_screenshots:
        global ENABLE_SCREENSHOTS
        ENABLE_SCREENSHOTS = False
        
    try:
        # Run the verify-fix cycle
        success = run_verify_fix(
            project_dir=project_dir,
            command=args.command,
            max_cycles=args.max_cycles,
            monitor_duration=args.monitor_duration,
            monitor_interval=args.monitor_interval
        )
        
        return 0 if success else 1
        
    except Exception as e:
        logger.exception("Unhandled exception")
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
