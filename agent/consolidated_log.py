"""
Consolidated log manager for the AI Code Agent.
"""
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO, List, Dict

# Configure logging
logger = logging.getLogger(__name__)

class ConsolidatedLogManager:
    """
    Manages a consolidated log file for all operations.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern to ensure only one log manager exists.
        """
        if cls._instance is None:
            cls._instance = super(ConsolidatedLogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the consolidated log manager.
        
        Args:
            log_dir: Directory to save logs (default: ./logs)
        """
        if self._initialized:
            return
            
        self.log_dir = log_dir or Path("logs")
        self.log_file: Optional[TextIO] = None
        self.log_path: Optional[Path] = None
        self.start_time = time.time()
        self.command_history: List[str] = []
        self.session_logs: Dict[str, Path] = {}
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the consolidated log file
        self._create_log_file()
        
        self._initialized = True
    
    def _create_log_file(self):
        """
        Create the consolidated log file.
        """
        # Create a timestamped log file
        timestamp = datetime.now().strftime("%Y-%m-%d")
        self.log_path = self.log_dir / f"consolidated_log_{timestamp}.md"
        
        # Check if the file already exists
        file_exists = self.log_path.exists()
        
        # Open the log file in append mode
        self.log_file = open(self.log_path, "a", encoding="utf-8")
        
        # Write header if it's a new file
        if not file_exists:
            self.log_file.write(f"# AI Code Agent Consolidated Log - {timestamp}\n\n")
            self.log_file.write("## System Information\n\n")
            self.log_file.write(f"- Python version: {sys.version.split()[0]}\n")
            self.log_file.write(f"- Operating system: {sys.platform}\n")
            self.log_file.write(f"- Log file: {self.log_path}\n\n")
        
        # Add a new session marker
        session_timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_file.write(f"## New Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        self.log_file.flush()
        
        logger.info(f"Started consolidated log at {self.log_path}")
    
    def register_session_log(self, session_name: str, log_path: Path):
        """
        Register a session log file.
        
        Args:
            session_name: Name of the session
            log_path: Path to the session log file
        """
        self.session_logs[session_name] = log_path
        self.log_file.write(f"### Session Log: {session_name}\n\n")
        self.log_file.write(f"- Log file: {log_path}\n\n")
        self.log_file.flush()
    
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
    
    def log_diff(self, diff_text: str, path: str):
        """
        Log a diff.
        
        Args:
            diff_text: Diff text
            path: Path that was diffed
        """
        if not self.log_file:
            return
            
        # Write diff to log file
        self.log_file.write(f"### Diff - {datetime.now().strftime('%H:%M:%S')}\n\n")
        self.log_file.write(f"**Path**: `{path}`\n\n")
        self.log_file.write("```diff\n")
        self.log_file.write(f"{diff_text}\n")
        self.log_file.write("```\n\n")
        self.log_file.write("---\n\n")
        self.log_file.flush()
    
    def close(self):
        """
        Close the log file.
        """
        if not self.log_file:
            return
            
        # Calculate execution time
        execution_time = time.time() - self.start_time
        
        # Write summary
        self.log_file.write("## Session Summary\n\n")
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
        
        logger.info(f"Closed consolidated log at {self.log_path}")
    
    def __del__(self):
        """
        Ensure log file is closed when object is deleted.
        """
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()
