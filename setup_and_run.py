#!/usr/bin/env python3
"""
Setup and Run Script for BeeGypt AI Code Agent

This script helps you:
1. Check and install dependencies
2. Set up environment variables
3. Run the main.py in interactive mode with best practices
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'google-generativeai',
        'openai', 
        'anthropic',
        'python-dotenv',
        'gitpython',
        'click',
        'rich',
        'pydantic',
        'pytest',
        'markdown',
        'pyautogui',
        'pytesseract',
        'Pillow',
        'watchdog'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(missing_packages: List[str]):
    """Install missing dependencies."""
    if not missing_packages:
        return True
        
    print(f"\n📥 Installing {len(missing_packages)} missing packages...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\n🔧 Checking environment configuration...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        print("📝 Creating .env file from .env.example...")
        
        example_file = Path('.env.example')
        if example_file.exists():
            with open(example_file, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
            print("✅ .env file created from .env.example")
            print("⚠️  Please edit .env file and add your API keys")
            return False
        else:
            print("❌ .env.example file not found")
            return False
    
    # Check if API key is configured
    with open(env_file, 'r') as f:
        content = f.read()
        
    if 'your_google_api_key_here' in content or 'your_openai_api_key_here' in content:
        print("⚠️  Please configure your API keys in .env file")
        return False
        
    print("✅ Environment file configured")
    return True

def get_interactive_options():
    """Get user preferences for running the agent."""
    print("\n🎯 Interactive Setup")
    print("Please provide the following information:")
    
    # Get project path
    while True:
        path = input("\n📁 Project path (where to create/edit project): ").strip()
        if path:
            path = Path(path).resolve()
            break
        print("❌ Please provide a valid path")
    
    # Get project description
    while True:
        prompt = input("\n📝 Project description or edit request: ").strip()
        if prompt:
            break
        print("❌ Please provide a description")
    
    # Get mode preference
    print("\n🔄 Choose mode:")
    print("1. Interactive (step-by-step with confirmations) - Recommended")
    print("2. Oneshot (automatic execution)")
    
    while True:
        mode_choice = input("Enter choice (1 or 2): ").strip()
        if mode_choice in ['1', '2']:
            oneshot = mode_choice == '2'
            break
        print("❌ Please enter 1 or 2")
    
    # Additional options
    print("\n⚙️  Additional options (y/n):")
    no_editor = input("Skip opening code editor after completion? (n): ").lower().startswith('y')
    no_deploy = input("Skip local deployment? (n): ").lower().startswith('y')
    show_diff = input("Show diff of changes? (y): ").lower() != 'n'
    run_verify = input("Run verification and auto-fix after completion? (y): ").lower() != 'n'
    
    return {
        'path': path,
        'prompt': prompt,
        'oneshot': oneshot,
        'no_editor': no_editor,
        'no_deploy': no_deploy,
        'show_diff': show_diff,
        'run_verify': run_verify
    }

def build_command(options: dict) -> List[str]:
    """Build the command to run main.py with the given options."""
    cmd = [sys.executable, 'main.py']
    
    # Required arguments
    cmd.extend(['--path', str(options['path'])])
    cmd.extend(['--prompt', options['prompt']])
    
    # Optional flags
    if options['oneshot']:
        cmd.append('--oneshot')
    
    if options['no_editor']:
        cmd.append('--no-editor')
        
    if options['no_deploy']:
        cmd.append('--no-deploy')
        
    if options['show_diff']:
        cmd.append('--diff')
        
    if options['run_verify']:
        cmd.append('--run-verify')
    
    return cmd

def main():
    """Main setup and run function."""
    print("🐝 BeeGypt AI Code Agent Setup & Runner")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check and install dependencies
    missing_packages = check_dependencies()
    if missing_packages:
        if not install_dependencies(missing_packages):
            return 1
    
    # Check environment configuration
    if not check_env_file():
        print("\n⚠️  Please configure your .env file and run this script again")
        return 1
    
    # Get interactive options
    options = get_interactive_options()
    
    # Build and display command
    cmd = build_command(options)
    print("\n🚀 Running command:")
    print(f"   {' '.join(cmd)}")
    
    # Confirm before running
    confirm = input("\n▶️  Proceed? (Y/n): ").strip().lower()
    if confirm and confirm != 'y' and confirm != 'yes':
        print("❌ Cancelled")
        return 0
    
    # Run the command
    print("\n" + "=" * 50)
    print("🐝 Starting BeeGypt AI Code Agent...")
    print("=" * 50)
    
    try:
        result = subprocess.run(cmd, cwd=Path.cwd())
        return result.returncode
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running command: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())