"""Real-time terminal logging system for the AI Code Agent.

This module provides real-time terminal logging with:
- File creation/editing events with visual indicators (++, --)
- Color-coded syntax highlighting for code changes
- Live updates as modifications occur
"""

import logging
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass
from queue import Queue, Empty

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.text import Text
    from rich.live import Live
    from rich.table import Table
    from rich.columns import Columns
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not available. Terminal logging will use basic formatting.")

# Configure logging
logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of events that can be logged."""
    FILE_CREATED = "created"
    FILE_MODIFIED = "modified"
    FILE_DELETED = "deleted"
    DIRECTORY_CREATED = "dir_created"
    COMMAND_EXECUTED = "command"
    API_CALL = "api_call"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"

@dataclass
class LogEvent:
    """Represents a single log event."""
    event_type: EventType
    message: str
    file_path: Optional[Path] = None
    code_content: Optional[str] = None
    language: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class TerminalLogger:
    """Real-time terminal logger with visual indicators and syntax highlighting."""
    
    def __init__(self, 
                 max_events: int = 100,
                 enable_live_updates: bool = True,
                 enable_syntax_highlighting: bool = True,
                 log_file: Optional[Path] = None):
        """
        Initialize the terminal logger.
        
        Args:
            max_events: Maximum number of events to keep in memory
            enable_live_updates: Whether to enable live terminal updates
            enable_syntax_highlighting: Whether to enable syntax highlighting
            log_file: Optional file to also write logs to
        """
        self.max_events = max_events
        self.enable_live_updates = enable_live_updates
        self.enable_syntax_highlighting = enable_syntax_highlighting and RICH_AVAILABLE
        self.log_file = log_file
        
        # Event storage
        self.events: List[LogEvent] = []
        self.event_queue: Queue = Queue()
        
        # Rich console setup
        if RICH_AVAILABLE:
            self.console = Console()
            self.live_display = None
        else:
            self.console = None
            
        # Threading for live updates
        self._stop_event = threading.Event()
        self._update_thread = None
        
        # Visual indicators
        self.indicators = {
            EventType.FILE_CREATED: "[bold green]++[/bold green]",
            EventType.FILE_MODIFIED: "[bold yellow]~~[/bold yellow]",
            EventType.FILE_DELETED: "[bold red]--[/bold red]",
            EventType.DIRECTORY_CREATED: "[bold blue]📁[/bold blue]",
            EventType.COMMAND_EXECUTED: "[bold cyan]⚡[/bold cyan]",
            EventType.API_CALL: "[bold magenta]🌐[/bold magenta]",
            EventType.ERROR: "[bold red]❌[/bold red]",
            EventType.INFO: "[bold blue]ℹ️[/bold blue]",
            EventType.WARNING: "[bold yellow]⚠️[/bold yellow]",
            EventType.SUCCESS: "[bold green]✅[/bold green]",
        }
        
        # Color schemes for different file types
        self.language_colors = {
            'python': 'bright_blue',
            'javascript': 'bright_yellow',
            'typescript': 'blue',
            'html': 'bright_red',
            'css': 'bright_magenta',
            'json': 'bright_green',
            'yaml': 'cyan',
            'markdown': 'white',
            'bash': 'bright_black',
            'sql': 'magenta',
        }
        
        # Start live updates if enabled
        if self.enable_live_updates and RICH_AVAILABLE:
            self.start_live_updates()
            
        logger.info("Terminal logger initialized")
    
    def start_live_updates(self):
        """Start the live update thread."""
        if not RICH_AVAILABLE:
            return
            
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        logger.info("Live updates started")
    
    def stop_live_updates(self):
        """Stop the live update thread."""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=1.0)
        if self.live_display:
            self.live_display.stop()
        logger.info("Live updates stopped")
    
    def _update_loop(self):
        """Main update loop for live terminal display."""
        if not RICH_AVAILABLE:
            return
            
        with Live(self._generate_display(), refresh_per_second=4, console=self.console) as live:
            self.live_display = live
            while not self._stop_event.is_set():
                try:
                    # Process queued events
                    while True:
                        try:
                            event = self.event_queue.get_nowait()
                            self._add_event(event)
                            self.event_queue.task_done()
                        except Empty:
                            break
                    
                    # Update display
                    live.update(self._generate_display())
                    time.sleep(0.25)
                    
                except Exception as e:
                    logger.error(f"Error in update loop: {e}")
                    time.sleep(1.0)
    
    def _generate_display(self):
        """Generate the current display content."""
        if not RICH_AVAILABLE:
            return "Terminal logging active (Rich not available)"
            
        # Create main table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim", width=8)
        table.add_column("Event", width=6)
        table.add_column("Details", min_width=40)
        
        # Add recent events (last 20)
        recent_events = self.events[-20:] if self.events else []
        
        for event in recent_events:
            time_str = event.timestamp.strftime("%H:%M:%S")
            indicator = self.indicators.get(event.event_type, "[dim]•[/dim]")
            
            # Format details based on event type
            details = self._format_event_details(event)
            
            table.add_row(time_str, indicator, details)
        
        # Create header panel
        header = Panel(
            Align.center("[bold cyan]BEE EGYPT - Real-time Terminal Logger[/bold cyan]"),
            style="bright_blue"
        )
        
        # Create stats panel
        stats_text = f"Total Events: {len(self.events)} | Active: {not self._stop_event.is_set()}"
        stats = Panel(stats_text, title="Statistics", style="dim")
        
        # Combine all elements
        return Columns([header, stats, table], equal=False, expand=True)
    
    def _format_event_details(self, event: LogEvent) -> str:
        """Format event details for display."""
        if event.event_type in [EventType.FILE_CREATED, EventType.FILE_MODIFIED, EventType.FILE_DELETED]:
            if event.file_path:
                file_name = event.file_path.name
                file_ext = event.file_path.suffix.lstrip('.')
                color = self.language_colors.get(file_ext, 'white')
                return f"[{color}]{file_name}[/{color}] - {event.message}"
        
        elif event.event_type == EventType.COMMAND_EXECUTED:
            return f"[cyan]{event.message}[/cyan]"
            
        elif event.event_type == EventType.API_CALL:
            return f"[magenta]{event.message}[/magenta]"
            
        elif event.event_type == EventType.ERROR:
            return f"[red]{event.message}[/red]"
            
        elif event.event_type == EventType.SUCCESS:
            return f"[green]{event.message}[/green]"
            
        return event.message
    
    def _add_event(self, event: LogEvent):
        """Add an event to the internal storage."""
        self.events.append(event)
        
        # Maintain max events limit
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Write to log file if specified
        if self.log_file:
            self._write_to_file(event)
    
    def _write_to_file(self, event: LogEvent):
        """Write event to log file."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {event.event_type.value.upper()}: {event.message}\n")
                
                if event.code_content and event.language:
                    f.write(f"```{event.language}\n{event.code_content}\n```\n\n")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
    
    def log_file_event(self, 
                      event_type: EventType, 
                      file_path: Path, 
                      message: str = "",
                      code_content: Optional[str] = None,
                      language: Optional[str] = None):
        """Log a file-related event."""
        if not message:
            message = f"{event_type.value.title()} {file_path.name}"
            
        # Auto-detect language from file extension
        if not language and file_path:
            ext = file_path.suffix.lstrip('.')
            language = self._detect_language(ext)
        
        event = LogEvent(
            event_type=event_type,
            message=message,
            file_path=file_path,
            code_content=code_content,
            language=language
        )
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def log_command(self, command: str, output: Optional[str] = None, success: bool = True):
        """Log a command execution."""
        status = "✅" if success else "❌"
        message = f"{status} {command}"
        
        event = LogEvent(
            event_type=EventType.COMMAND_EXECUTED,
            message=message,
            metadata={'output': output, 'success': success}
        )
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def log_api_call(self, provider: str, endpoint: str, duration: Optional[float] = None):
        """Log an API call."""
        message = f"{provider} - {endpoint}"
        if duration:
            message += f" ({duration:.2f}s)"
            
        event = LogEvent(
            event_type=EventType.API_CALL,
            message=message,
            metadata={'provider': provider, 'endpoint': endpoint, 'duration': duration}
        )
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def log_info(self, message: str):
        """Log an info message."""
        event = LogEvent(event_type=EventType.INFO, message=message)
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def log_warning(self, message: str):
        """Log a warning message."""
        event = LogEvent(event_type=EventType.WARNING, message=message)
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log an error message."""
        if exception:
            message += f" - {str(exception)}"
            
        event = LogEvent(
            event_type=EventType.ERROR, 
            message=message,
            metadata={'exception': str(exception) if exception else None}
        )
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def log_success(self, message: str):
        """Log a success message."""
        event = LogEvent(event_type=EventType.SUCCESS, message=message)
        
        if self.enable_live_updates:
            self.event_queue.put(event)
        else:
            self._add_event(event)
            self._print_event(event)
    
    def _print_event(self, event: LogEvent):
        """Print event to console (fallback when live updates are disabled)."""
        if RICH_AVAILABLE and self.console:
            time_str = event.timestamp.strftime("%H:%M:%S")
            indicator = self.indicators.get(event.event_type, "•")
            details = self._format_event_details(event)
            
            self.console.print(f"[dim]{time_str}[/dim] {indicator} {details}")
        else:
            # Fallback to basic print
            time_str = event.timestamp.strftime("%H:%M:%S")
            print(f"[{time_str}] {event.event_type.value.upper()}: {event.message}")
    
    def _detect_language(self, file_extension: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'html': 'html',
            'htm': 'html',
            'css': 'css',
            'scss': 'scss',
            'sass': 'sass',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sh': 'bash',
            'bash': 'bash',
            'sql': 'sql',
            'xml': 'xml',
            'php': 'php',
            'rb': 'ruby',
            'go': 'go',
            'rs': 'rust',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'h': 'c',
            'hpp': 'cpp',
        }
        return ext_map.get(file_extension.lower())
    
    def display_code_diff(self, 
                         old_code: str, 
                         new_code: str, 
                         language: str = "python",
                         title: str = "Code Changes"):
        """Display a code diff with syntax highlighting."""
        if not RICH_AVAILABLE:
            print(f"\n=== {title} ===")
            print("OLD:")
            print(old_code)
            print("\nNEW:")
            print(new_code)
            return
        
        # Create syntax highlighted panels
        old_syntax = Syntax(old_code, language, theme="monokai", line_numbers=True)
        new_syntax = Syntax(new_code, language, theme="monokai", line_numbers=True)
        
        old_panel = Panel(old_syntax, title="[red]Before[/red]", border_style="red")
        new_panel = Panel(new_syntax, title="[green]After[/green]", border_style="green")
        
        # Display side by side
        columns = Columns([old_panel, new_panel], equal=True, expand=True)
        
        main_panel = Panel(columns, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan")
        
        self.console.print(main_panel)
    
    def get_event_summary(self) -> Dict[str, int]:
        """Get a summary of events by type."""
        summary = {}
        for event in self.events:
            event_type = event.event_type.value
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary
    
    def clear_events(self):
        """Clear all stored events."""
        self.events.clear()
        logger.info("Cleared all terminal logger events")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_live_updates()

# Global terminal logger instance
_terminal_logger: Optional[TerminalLogger] = None

def get_terminal_logger() -> TerminalLogger:
    """Get the global terminal logger instance."""
    global _terminal_logger
    if _terminal_logger is None:
        _terminal_logger = TerminalLogger()
    return _terminal_logger

def initialize_terminal_logger(**kwargs) -> TerminalLogger:
    """Initialize the global terminal logger with custom settings."""
    global _terminal_logger
    _terminal_logger = TerminalLogger(**kwargs)
    return _terminal_logger

def shutdown_terminal_logger():
    """Shutdown the global terminal logger."""
    global _terminal_logger
    if _terminal_logger:
        _terminal_logger.stop_live_updates()
        _terminal_logger = None

# Convenience functions
def log_file_created(file_path: Path, code_content: Optional[str] = None):
    """Log a file creation event."""
    get_terminal_logger().log_file_event(EventType.FILE_CREATED, file_path, code_content=code_content)

def log_file_modified(file_path: Path, code_content: Optional[str] = None):
    """Log a file modification event."""
    get_terminal_logger().log_file_event(EventType.FILE_MODIFIED, file_path, code_content=code_content)

def log_file_deleted(file_path: Path):
    """Log a file deletion event."""
    get_terminal_logger().log_file_event(EventType.FILE_DELETED, file_path)

def log_command_executed(command: str, output: Optional[str] = None, success: bool = True):
    """Log a command execution."""
    get_terminal_logger().log_command(command, output, success)

def log_api_call(provider: str, endpoint: str, duration: Optional[float] = None):
    """Log an API call."""
    get_terminal_logger().log_api_call(provider, endpoint, duration)

def log_info(message: str):
    """Log an info message."""
    get_terminal_logger().log_info(message)

def log_warning(message: str):
    """Log a warning message."""
    get_terminal_logger().log_warning(message)

def log_error(message: str, exception: Optional[Exception] = None):
    """Log an error message."""
    get_terminal_logger().log_error(message, exception)

def log_success(message: str):
    """Log a success message."""
    get_terminal_logger().log_success(message)

def display_code_diff(old_code: str, new_code: str, language: str = "python", title: str = "Code Changes"):
    """Display a code diff with syntax highlighting."""
    get_terminal_logger().display_code_diff(old_code, new_code, language, title)