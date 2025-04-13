# BeeAgent

BeeAgent is a unified interface for creating or editing projects using AI. It can automatically detect whether a path contains an existing project or needs a new one to be created.

## New Features

- **Step-by-Step Mode**: The updated `main.py` script now provides a step-by-step approach with user confirmation at each stage
- **No Package Initializers**: All projects are created by generating every single line of code directly, without using package initializers like `npm init`, `npx create-react-app`, etc.
- **Animated Terminal Interface**: Includes a visually appealing terminal animation when starting the agent
- **Oneshot Mode Option**: Includes a `--oneshot` flag for running without step-by-step confirmation

## Features

- **Automatic Mode Detection**: Automatically determines whether to create a new project or edit an existing one
- **Project Creation**: Creates new projects using the oneshot functionality
- **Project Editing**: Edits existing projects using the fix_project functionality
- **Flexible Options**: Provides various command-line options for customization
- **Step-by-Step Execution**: Provides confirmation prompts at each stage of the process
- **Manual Code Generation**: Creates all project files manually without using code generators or initializers
- **Visual Feedback**: Includes terminal animations and progress indicators

## Usage

### Using BeeAgent (Original)

```bash
python beeagent.py --path /path/to/project --prompt "Your project description or edit request"
```

### Using Step-by-Step Mode (New)

```bash
python main.py --path /path/to/project --prompt "Your project description or edit request"
```

### Creating a New Project

```bash
python beeagent.py --path ./my-new-project --prompt "Create a React todo list application with local storage"
```

### Editing an Existing Project

```bash
python beeagent.py --path ./my-existing-project --prompt "Add dark mode support to the application"
```

## Command-Line Options

### Common Options (Both Scripts)

- `--path`: Path to the project directory (required)
- `--prompt`: Project description or edit request (required)
- `--no-editor`: Don't open the code editor after completion
- `--no-deploy`: Don't deploy the project locally
- `--no-code-generators`: Don't use code generators (for new projects)
- `--force-create`: Force create a new project even if the directory exists
- `--force-edit`: Force edit mode even if the directory doesn't look like a project
- `--diff`: Show diff of changes after operation completes
- `--run-verify`: Run, verify, and fix the project after completion
- `--max-cycles`: Maximum number of run-verify cycles

### Additional Options for main.py

- `--oneshot`: Run in oneshot mode (no step-by-step confirmation)
- `--no-animation`: Skip the initial animation

## Examples

### Create a New Web Application

```bash
python beeagent.py --path ./my-web-app --prompt "Create a responsive portfolio website with a projects section, about me page, and contact form"
```

### Add Features to an Existing Project

```bash
python beeagent.py --path ./my-web-app --prompt "Add a blog section with pagination and categories"
```

### Fix Issues in an Existing Project

```bash
python beeagent.py --path ./my-web-app --prompt "Fix the mobile navigation menu that doesn't close when clicking outside"
```

### Create a Project Without Using Code Generators

```bash
python beeagent.py --path ./my-react-app --prompt "Create a React weather app" --no-code-generators
```

### Create a Project with Step-by-Step Confirmation

```bash
python main.py --path ./my-react-app --prompt "Create a React weather app"
```

### Create a Project in Oneshot Mode (No Step-by-Step)

```bash
python main.py --path ./my-react-app --prompt "Create a React weather app" --oneshot
```

### Create a Project Without Animation

```bash
python main.py --path ./my-react-app --prompt "Create a React weather app" --no-animation
```

## How It Works

BeeAgent determines whether a path contains an existing project by checking for common project files and directories such as:

- Web projects: package.json, node_modules, src, etc.
- Python projects: requirements.txt, setup.py, venv, etc.
- Java/Kotlin projects: pom.xml, build.gradle, etc.
- .NET projects: *.csproj, *.sln, etc.
- General project files: .git, README.md, LICENSE, etc.

Based on this detection, it either:
1. Creates a new project using the oneshot functionality, or
2. Edits an existing project using the fix_project functionality

You can override the automatic detection using the `--force-create` or `--force-edit` flags.

## Differences Between beeagent.py and main.py

### beeagent.py
- Original implementation
- Runs in oneshot mode by default
- May use package initializers in some cases

### main.py
- Updated implementation
- Runs in step-by-step mode by default with user confirmation at each stage
- Never uses package initializers (creates all files manually)
- Includes terminal animations and visual feedback
- Provides more detailed logging
- Supports all the same features as beeagent.py plus additional options

## How to Choose

- Use `beeagent.py` for quick, automated project creation and editing
- Use `main.py` when you want more control over the process and want to see/confirm each step
- Use `main.py --oneshot` when you want the benefits of the updated implementation but still want it to run automatically
