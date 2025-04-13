#!/usr/bin/env python3
"""
Test script for BeeAgent.
This script demonstrates how to use BeeAgent programmatically.
"""
import argparse
import logging
from pathlib import Path

from beeagent import is_existing_project, create_new_project, edit_existing_project

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the test script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test BeeAgent functionality")
    parser.add_argument("--path", required=True, help="Path to the project directory")
    parser.add_argument("--prompt", required=True, help="Project description or edit request")
    parser.add_argument("--no-editor", action="store_true", help="Don't open the code editor after completion")
    parser.add_argument("--no-deploy", action="store_true", help="Don't deploy the project locally")
    
    args = parser.parse_args()
    
    # Convert path to Path object
    path = Path(args.path).resolve()
    
    # Collect options
    options = {
        "no_editor": args.no_editor,
        "no_deploy": args.no_deploy,
        "no_code_generators": True  # Always use direct code generation for testing
    }
    
    # Check if it's an existing project
    is_project = is_existing_project(path)
    
    print(f"Path: {path}")
    print(f"Is existing project: {is_project}")
    
    # Based on the result, either create a new project or edit an existing one
    if is_project:
        print("Editing existing project...")
        # This would normally call edit_existing_project, but we'll just print for testing
        print(f"Would edit project at {path} with prompt: {args.prompt}")
    else:
        print("Creating new project...")
        # This would normally call create_new_project, but we'll just print for testing
        print(f"Would create new project at {path} with prompt: {args.prompt}")
    
    return 0

if __name__ == "__main__":
    main()
