#!/usr/bin/env python3
"""
BeeEgypt Interactive CLI

An enhanced interactive command-line interface for the BeeEgypt AI Code Agent
with ASCII art logo and streamlined project creation/editing workflow.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional
import time

def display_bee_logo():
    """Display the BeeEgypt ASCII logo with animation."""
    # ANSI color codes
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    logo = f"""
{YELLOW}{BOLD}
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║    ██████╗ ███████╗███████╗    ███████╗ ██████╗██╗   ██╗     ║
    ║    ██╔══██╗██╔════╝██╔════╝    ██╔════╝██╔════╝╚██╗ ██╔╝     ║
    ║    ██████╔╝█████╗  █████╗      █████╗  ██║  ███╗╚████╔╝      ║
    ║    ██╔══██╗██╔══╝  ██╔══╝      ██╔══╝  ██║   ██║ ╚██╔╝       ║
    ║    ██████╔╝███████╗███████╗    ███████╗╚██████╔╝  ██║        ║
    ║    ╚═════╝ ╚══════╝╚══════╝    ╚══════╝ ╚═════╝   ╚═╝        ║
    ║                                                              ║
    ║                  Buzzing with Intelligence                   ║
    ║                     By:@Loaiiabdalslam                       ║
    ╚══════════════════════════════════════════════════════════════╝
{RESET}
    """
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display logo with animation
    lines = logo.strip().split('\n')
    for line in lines:
        print(line)
        time.sleep(0.1)
    
    print(f"\n{YELLOW}{BOLD}" + "="*60 + f"{RESET}")
    print(f"{YELLOW}🚀 Welcome to Bee Egypt - Your AI-Powered Development Assistant{RESET}")
    print(f"{YELLOW}{BOLD}" + "="*60 + f"{RESET}\n")



def get_project_path():
    """Get project path from user with validation."""
    print("\n📁 PROJECT PATH SELECTION")
    print("-" * 30)
    print("Choose how to specify your project path:")
    print("1. Enter custom path")
    print("2. Use current directory")
    print("3. Browse and select (manual input)")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            while True:
                path_input = input("\n📂 Enter project path: ").strip()
                if path_input:
                    path = Path(path_input).resolve()
                    print(f"Selected path: {path}")
                    
                    # Ask for confirmation
                    if input("Confirm this path? (y/n): ").lower().startswith('y'):
                        return path
                else:
                    print("❌ Please provide a valid path")
                    
        elif choice == '2':
            path = Path.cwd()
            print(f"\nUsing current directory: {path}")
            if input("Confirm this path? (y/n): ").lower().startswith('y'):
                return path
                
        elif choice == '3':
            print("\n📋 Please manually enter the full path to your desired project directory:")
            while True:
                path_input = input("Full path: ").strip()
                if path_input:
                    path = Path(path_input).resolve()
                    print(f"Selected path: {path}")
                    if input("Confirm this path? (y/n): ").lower().startswith('y'):
                        return path
                else:
                    print("❌ Please provide a valid path")
        else:
            print("❌ Please enter 1, 2, or 3")

def get_project_mode(project_path):
    """Determine if user wants to create new project or edit existing one."""
    print("\n🎯 PROJECT MODE SELECTION")
    print("-" * 30)
    
    # Check if path exists and has project files
    path_exists = project_path.exists()
    has_files = False
    
    if path_exists:
        files = list(project_path.glob('*'))
        has_files = len(files) > 0
        
        if has_files:
            print(f"📁 Directory exists with {len(files)} items")
            print("\nDetected files/folders:")
            for item in files[:5]:  # Show first 5 items
                icon = "📁" if item.is_dir() else "📄"
                print(f"   {icon} {item.name}")
            if len(files) > 5:
                print(f"   ... and {len(files) - 5} more items")
        else:
            print("📁 Directory exists but is empty")
    else:
        print("📁 Directory does not exist (will be created)")
    
    print("\nWhat would you like to do?")
    print("1. 🆕 Create new project")
    print("2. ✏️  Edit existing project")
    
    if not path_exists or not has_files:
        print("   (Recommended: Create new project)")
    else:
        print("   (Recommended: Edit existing project)")
    
    while True:
        choice = input("\nEnter your choice (1-2): ").strip()
        if choice == '1':
            return 'create'
        elif choice == '2':
            return 'edit'
        else:
            print("❌ Please enter 1 or 2")

def get_project_prompt(mode):
    """Get project description or edit request from user."""
    print(f"\n📝 PROJECT {'DESCRIPTION' if mode == 'create' else 'EDIT REQUEST'}")
    print("-" * 30)
    
    if mode == 'create':
        print("Describe the project you want to create:")
        print("Examples:")
        print("  • 'A React todo app with dark mode'")
        print("  • 'Python Flask API for user management'")
        print("  • 'Vue.js dashboard with charts and tables'")
    else:
        print("Describe what you want to edit or add:")
        print("Examples:")
        print("  • 'Add user authentication to the app'")
        print("  • 'Fix the responsive design issues'")
        print("  • 'Add a new API endpoint for orders'")
    
    while True:
        prompt = input(f"\n✍️  Enter your {'description' if mode == 'create' else 'edit request'}: ").strip()
        if prompt:
            print(f"\n📋 You entered: {prompt}")
            if input("Confirm this prompt? (y/n): ").lower().startswith('y'):
                return prompt
        else:
            print("❌ Please provide a description")

def get_execution_options():
    """Get execution preferences from user."""
    print("\n⚙️  EXECUTION OPTIONS")
    print("-" * 30)
    
    print("Choose execution mode:")
    print("1. 🎯 Interactive (step-by-step with confirmations) - Recommended")
    print("2. 🚀 Auto-yes (automatic execution, no confirmations)")
    print("3. 🔄 Oneshot (fully automatic execution)")
    
    while True:
        mode_choice = input("\nEnter choice (1-3): ").strip()
        if mode_choice == '1':
            execution_mode = 'interactive'
            break
        elif mode_choice == '2':
            execution_mode = 'auto_yes'
            break
        elif mode_choice == '3':
            execution_mode = 'oneshot'
            break
        else:
            print("❌ Please enter 1, 2, or 3")
    
    print("\n🔧 Additional options:")
    no_editor = input("Skip opening code editor after completion? (y/N): ").lower().startswith('y')
    no_deploy = input("Skip local deployment? (y/N): ").lower().startswith('y')
    show_diff = input("Show diff of changes? (Y/n): ").lower() != 'n'
    run_verify = input("Run verification and auto-fix after completion? (Y/n): ").lower() != 'n'
    
    return {
        'execution_mode': execution_mode,
        'no_editor': no_editor,
        'no_deploy': no_deploy,
        'show_diff': show_diff,
        'run_verify': run_verify
    }

def build_command(project_path, prompt, mode, options):
    """Build the command to run main.py with the given options."""
    cmd = [sys.executable, 'main.py']
    
    # Required arguments
    cmd.extend(['--path', str(project_path)])
    cmd.extend(['--prompt', prompt])
    
    # Execution mode flags
    if options['execution_mode'] == 'oneshot':
        cmd.append('--oneshot')
    elif options['execution_mode'] == 'auto_yes':
        cmd.append('--auto-yes')
    
    # Optional flags
    if options['no_editor']:
        cmd.append('--no-editor')
        
    if options['no_deploy']:
        cmd.append('--no-deploy')
        
    if options['show_diff']:
        cmd.append('--diff')
        
    if options['run_verify']:
        cmd.append('--run-verify')
    
    return cmd

def display_summary(project_path, prompt, mode, options, cmd):
    """Display a summary of the selected options."""
    print("\n" + "="*60)
    print("📋 EXECUTION SUMMARY")
    print("="*60)
    print(f"📁 Project Path: {project_path}")
    print(f"🎯 Mode: {mode.title()}")
    print(f"📝 Prompt: {prompt}")
    print(f"⚙️  Execution: {options['execution_mode'].replace('_', ' ').title()}")
    print(f"🔧 Options: Editor={'Skip' if options['no_editor'] else 'Open'}, "
          f"Deploy={'Skip' if options['no_deploy'] else 'Run'}, "
          f"Diff={'Show' if options['show_diff'] else 'Hide'}, "
          f"Verify={'Run' if options['run_verify'] else 'Skip'}")
    print(f"\n🚀 Command: {' '.join(cmd)}")
    print("="*60)

def main():
    """Main interactive function."""
    # Display logo and welcome
    display_bee_logo()
    
    # System checks
    print("🔍 SYSTEM CHECKS")
    print("-" * 20)
    
  
    
 
    
    print("\n✅ All system checks passed!")
    input("\nPress Enter to continue...")
    
    # Interactive setup
    try:
        # Get project path
        project_path = get_project_path()
        
        # Determine mode (create/edit)
        mode = get_project_mode(project_path)
        
        # Get project prompt
        prompt = get_project_prompt(mode)
        
        # Get execution options
        options = get_execution_options()
        
        # Build command
        cmd = build_command(project_path, prompt, mode, options)
        
        # Display summary
        display_summary(project_path, prompt, mode, options, cmd)
        
        # Final confirmation
        print("\n🚀 Ready to start BeeEgypt!")
        confirm = input("Proceed with execution? (Y/n): ").strip().lower()
        if confirm and confirm != 'y' and confirm != 'yes' and confirm != '':
            print("❌ Cancelled by user")
            return 0
        
        # Clear screen and run
        os.system('cls' if os.name == 'nt' else 'clear')
        print("🐝" * 20)
        print("🚀 STARTING BEEGYPT AI CODE AGENT")
        print("🐝" * 20)
        print(f"📁 Working on: {project_path}")
        print(f"🎯 Mode: {mode.title()}")
        print("🐝" * 20 + "\n")
        
        # Run the command
        try:
            result = subprocess.run(cmd, cwd=Path.cwd())
            return result.returncode
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            return 1
        except Exception as e:
            print(f"\n❌ Error running command: {e}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())