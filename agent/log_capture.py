"""
Log capture module for the AI Code Agent.
Captures logs and saves them to a Markdown file.
"""
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO, List

# Configure logging
logger = logging.getLogger(__name__)

class MarkdownLogCapture:
    """
    Captures logs and saves them to a Markdown file.
    """
    
    def __init__(self, log_dir: Path, prefix: str = "log"):
        """
        Initialize the log capture.
        
        Args:
            log_dir: Directory to save logs
            prefix: Prefix for log files
        """
        self.log_dir = log_dir
        self.prefix = prefix
        self.log_file: Optional[TextIO] = None
        self.log_path: Optional[Path] = None
        self.start_time = time.time()
        self.command_history: List[str] = []
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def start_capture(self):
        """
        Start capturing logs.
        """
        # Create a timestamped log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_path = self.log_dir / f"{self.prefix}_{timestamp}.md"
        
        # Open the log file
        self.log_file = open(self.log_path, "w", encoding="utf-8")
        
        # Write header
        self.log_file.write(f"# AI Code Agent Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        self.log_file.write("## System Information\n\n")
        self.log_file.write(f"- Python version: {sys.version.split()[0]}\n")
        self.log_file.write(f"- Operating system: {sys.platform}\n")
        self.log_file.write(f"- Log file: {self.log_path}\n\n")
        self.log_file.write("## Execution Log\n\n")
        self.log_file.flush()
        
        logger.info(f"Started log capture to {self.log_path}")
        
    def log_command(self, command: str, description: str = ""):
        """
        Log a command execution.
        
        Args:
            command: Command that was executed
            description: Description of the command
        """
        if not self.log_file:
            return
            
        self.command_history.append(command)
        
        # Write command to log file
        self.log_file.write(f"### Command Execution - {datetime.now().strftime('%H:%M:%S')}\n\n")
        if description:
            self.log_file.write(f"**Description**: {description}\n\n")
        self.log_file.write("```bash\n")
        self.log_file.write(f"{command}\n")
        self.log_file.write("```\n\n")
        self.log_file.flush()
        
    def log_output(self, output: str, success: bool = True):
        """
        Log command output.
        
        Args:
            output: Command output
            success: Whether the command was successful
        """
        if not self.log_file:
            return
            
        # Write output to log file
        status = "✅ Success" if success else "❌ Failure"
        self.log_file.write(f"**Result**: {status}\n\n")
        
        if output:
            self.log_file.write("**Output**:\n\n")
            self.log_file.write("```\n")
            self.log_file.write(f"{output}\n")
            self.log_file.write("```\n\n")
        else:
            self.log_file.write("**No output**\n\n")
            
        self.log_file.write("---\n\n")
        self.log_file.flush()
        
    def log_file_operation(self, operation: str, file_path: str, content_preview: str = ""):
        """
        Log a file operation.
        
        Args:
            operation: Operation performed (create, modify, delete)
            file_path: Path to the file
            content_preview: Preview of the file content
        """
        if not self.log_file:
            return
            
        # Write file operation to log file
        self.log_file.write(f"### File Operation - {datetime.now().strftime('%H:%M:%S')}\n\n")
        self.log_file.write(f"**Operation**: {operation}\n")
        self.log_file.write(f"**File**: `{file_path}`\n\n")
        
        if content_preview:
            self.log_file.write("**Content Preview**:\n\n")
            self.log_file.write("```\n")
            # Limit preview to 20 lines
            preview_lines = content_preview.split("\n")[:20]
            self.log_file.write("\n".join(preview_lines))
            if len(preview_lines) < len(content_preview.split("\n")):
                self.log_file.write("\n... (truncated)")
            self.log_file.write("\n```\n\n")
            
        self.log_file.write("---\n\n")
        self.log_file.flush()
        
    def log_error(self, error_message: str, context: str = ""):
        """
        Log an error.
        
        Args:
            error_message: Error message
            context: Context in which the error occurred
        """
        if not self.log_file:
            return
            
        # Write error to log file
        self.log_file.write(f"### Error - {datetime.now().strftime('%H:%M:%S')}\n\n")
        if context:
            self.log_file.write(f"**Context**: {context}\n\n")
        self.log_file.write("```\n")
        self.log_file.write(f"{error_message}\n")
        self.log_file.write("```\n\n")
        self.log_file.write("---\n\n")
        self.log_file.flush()
        
    def log_section(self, section_name: str, content: str = ""):
        """
        Log a new section.
        
        Args:
            section_name: Name of the section
            content: Content for the section
        """
        if not self.log_file:
            return
            
        # Write section to log file
        self.log_file.write(f"## {section_name} - {datetime.now().strftime('%H:%M:%S')}\n\n")
        if content:
            self.log_file.write(f"{content}\n\n")
        self.log_file.flush()
        
    def log_message(self, message: str):
        """
        Log a simple message.
        
        Args:
            message: Message to log
        """
        if not self.log_file:
            return
            
        # Write message to log file
        self.log_file.write(f"{message}\n\n")
        self.log_file.flush()
        
    def stop_capture(self):
        """
        Stop capturing logs and close the log file.
        """
        if not self.log_file:
            return
            
        # Calculate execution time
        execution_time = time.time() - self.start_time
        
        # Write summary
        self.log_file.write("## Summary\n\n")
        self.log_file.write(f"- Execution time: {execution_time:.2f} seconds\n")
        self.log_file.write(f"- Commands executed: {len(self.command_history)}\n")
        
        # Write command history
        if self.command_history:
            self.log_file.write("\n### Command History\n\n")
            for i, cmd in enumerate(self.command_history, 1):
                self.log_file.write(f"{i}. `{cmd}`\n")
                
        # Close the log file
        self.log_file.close()
        self.log_file = None
        
        logger.info(f"Stopped log capture to {self.log_path}")
        
    def __del__(self):
        """
        Ensure log file is closed when object is deleted.
        """
        if self.log_file:
            self.log_file.close()
