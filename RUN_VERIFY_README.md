# Run-Verify-Fix Functionality

The Run-Verify-Fix functionality allows you to automatically run your project, take screenshots, analyze them for errors, and apply fixes. This creates a continuous improvement loop based on visual feedback.

## Features

- **Automatic Project Running**: Detects the appropriate command to run your project based on its type
- **Screenshot Capture**: Takes screenshots of your running application
- **Error Detection**: Analyzes screenshots for error messages and UI issues
- **Fix Suggestions**: Generates fix suggestions based on detected errors
- **Continuous Improvement**: Runs multiple cycles of run-verify-fix to ensure the project works correctly

## Usage

### Using with BeeAgent

```bash
python beeagent.py --path ./your-project --prompt "Your prompt" --run-verify
```

### Using Standalone

```bash
python run_verify.py --project-dir ./your-project
```

## Command-Line Options

### BeeAgent Options

- `--run-verify`: Enable the run-verify-fix functionality
- `--max-cycles`: Maximum number of run-verify cycles (default: 3)

### Standalone Options

- `--project-dir`: Path to the project directory (required)
- `--command`: Command to run the project (if not provided, will be detected)
- `--max-cycles`: Maximum number of cycles to run (default: 3)
- `--monitor-duration`: Duration to monitor in seconds (default: 60)
- `--monitor-interval`: Interval between screenshots in seconds (default: 5)
- `--no-screenshots`: Disable screenshots

## How It Works

1. **Project Detection**: The system detects the type of project (web, Python, Node.js, etc.) and determines the appropriate command to run it.

2. **Run Project**: The project is run using the detected command or a user-provided command.

3. **Screenshot Capture**: Screenshots are taken at regular intervals to monitor the running application.

4. **Error Detection**: Screenshots are analyzed using OCR to detect error messages and UI issues.

5. **Fix Generation**: If errors are detected, the system uses multimodal AI to analyze the errors and generate fix suggestions.

6. **Fix Application**: The system attempts to apply the fixes to the project code.

7. **Verification**: The project is run again to verify that the fixes resolved the issues.

8. **Cycle Repetition**: Steps 2-7 are repeated until no errors are detected or the maximum number of cycles is reached.

## Supported Project Types

- **Web Projects**: HTML/CSS/JavaScript projects
- **Node.js Projects**: React, Angular, Vue, Next.js, etc.
- **Python Projects**: Flask, Django, FastAPI, etc.
- **Java Projects**: Spring Boot, etc.

## Requirements

- Python 3.7+
- Tesseract OCR (for screenshot analysis)
- Dependencies listed in requirements.txt

## Examples

### Running a React Project

```bash
python run_verify.py --project-dir ./my-react-app
```

### Running a Python Flask Project

```bash
python run_verify.py --project-dir ./my-flask-app --command "python app.py"
```

### Running with BeeAgent

```bash
python beeagent.py --path ./my-project --prompt "Fix the navigation menu" --run-verify --max-cycles 5
```
