# BeeAgent

BeeAgent is a unified interface for creating or editing projects using AI. It can automatically detect whether a path contains an existing project or needs a new one to be created.

## New Features

- **Optimized Project Setup Workflow**: Enhanced 5-step project creation process that prioritizes package files and prevents duplicates
- **Smart Package Management**: Creates package files (package.json, requirements.txt, etc.) first without immediate installation
- **Intelligent .gitignore Generation**: Automatically generates technology-specific .gitignore files before any other project files
- **Duplicate Structure Prevention**: Built-in cleanup system that detects and removes nested/duplicate project structures
- **Final Step Dependency Installation**: Dependencies are installed only as the final step after all project structure is complete
- **Step-by-Step Mode**: The updated `main.py` script now provides a step-by-step approach with user confirmation at each stage
- **No Package Initializers**: All projects are created by generating every single line of code directly, without using package initializers like `npm init`, `npx create-react-app`, etc.
- **Animated Terminal Interface**: Includes a visually appealing terminal animation when starting the agent
- **Oneshot Mode Option**: Includes a `--oneshot` flag for running without step-by-step confirmation

## Features

- **Automatic Mode Detection**: Automatically determines whether to create a new project or edit an existing one
- **Optimized Project Creation**: Creates new projects with a refined 5-step workflow that prevents common issues
- **Project Editing**: Edits existing projects using the fix_project functionality
- **Smart Structure Management**: Automatically detects and cleans up duplicate/nested project structures
- **Technology-Aware Setup**: Generates appropriate package files and .gitignore based on detected technologies
- **Flexible Options**: Provides various command-line options for customization
- **Step-by-Step Execution**: Provides confirmation prompts at each stage of the process
- **Manual Code Generation**: Creates all project files manually without using code generators or initializers
- **Visual Feedback**: Includes terminal animations and progress indicators

## Usage

BeeAgent is run via the `main.py` script. It has two primary modes:

1.  **Step-by-Step Mode (Default)**: An interactive mode that guides you through project creation or editing, asking for confirmation at each major step.
2.  **Oneshot Mode (`--oneshot`)**: A non-interactive mode that runs the entire process automatically, which is useful for scripting.

### Step-by-Step Mode (Default)

```bash
python main.py --path /path/to/project --prompt "Your project description or edit request"
```

### Oneshot Mode

```bash
python main.py --path /path/to/project --prompt "Your project description or edit request" --oneshot
```

## Command-Line Options

- `--path`: Path to the project directory (required).
- `--prompt`: Project description or edit request (required).
- `--oneshot`: Run in oneshot mode (no step-by-step confirmation).
- `--no-editor`: Don't open the code editor after completion.
- `--no-deploy`: Don't deploy the project locally.
- `--no-code-generators`: Don't use code generators (for new projects).
- `--force-create`: Force create a new project even if the directory exists.
- `--force-edit`: Force edit mode even if the directory doesn't look like a project.
- `--diff`: Show diff of changes after operation completes.
- `--run-verify`: Run, verify, and fix the project after completion.
- `--max-cycles`: Maximum number of run-verify cycles.
- `--no-animation`: Skip the initial startup animation.

## Examples

### Create a New Web Application (Interactive)

```bash
python main.py --path ./my-web-app --prompt "Create a responsive portfolio website with a projects section, about me page, and contact form"
```

### Create a New Web Application (Automatic)

```bash
python main.py --path ./my-web-app --prompt "Create a responsive portfolio website with a projects section, about me page, and contact form" --oneshot
```

### Add Features to an Existing Project

```bash
python main.py --path ./my-web-app --prompt "Add a blog section with pagination and categories"
```

### Fix Issues in an Existing Project

```bash
python main.py --path ./my-web-app --prompt "Fix the mobile navigation menu that doesn't close when clicking outside"
```

## How It Works

BeeAgent determines whether a path contains an existing project by checking for common project files and directories such as:

- Web projects: package.json, node_modules, src, etc.
- Python projects: requirements.txt, setup.py, venv, etc.
- Java/Kotlin projects: pom.xml, build.gradle, etc.
- .NET projects: *.csproj, *.sln, etc.
- General project files: .git, README.md, LICENSE, etc.

Based on this detection, it either:
1. Creates a new project using the optimized 5-step workflow (in step-by-step mode), or
2. Edits an existing project.

### New Project Creation Workflow (5 Steps)

1. **Package Files Creation**: Creates package.json, requirements.txt, etc. without installing dependencies.
2. **Gitignore Generation**: Creates technology-specific .gitignore file before any other project files.
3. **Git Repository Initialization**: Sets up version control.
4. **Project Structure Creation**: Generates all project files and directories with duplicate cleanup.
5. **Dependency Installation**: Installs all dependencies as the final step.

This workflow prevents common issues like nested project structures, duplicate package files, and installation conflicts.

You can override the automatic detection using the `--force-create` or `--force-edit` flags.
