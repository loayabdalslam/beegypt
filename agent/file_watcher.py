"""File system watcher for real-time monitoring of file changes.

This module provides file system monitoring capabilities that integrate
with the terminal logger to provide real-time updates on file operations.
"""

import logging
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: Watchdog library not available. File watching will use polling.")

from agent.terminal_logger import (
    get_terminal_logger, 
    EventType, 
    log_file_created, 
    log_file_modified, 
    log_file_deleted
)

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class FileChangeEvent:
    """Represents a file change event."""
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    file_path: Path
    timestamp: datetime
    is_directory: bool = False
    old_path: Optional[Path] = None  # For move events
    file_size: Optional[int] = None
    content_preview: Optional[str] = None

class BeeEgyptFileHandler(FileSystemEventHandler):
    """Custom file system event handler for BEE EGYPT application."""
    
    def __init__(self, 
                 file_watcher: 'FileWatcher',
                 ignored_patterns: Optional[List[str]] = None,
                 monitored_extensions: Optional[Set[str]] = None):
        """
        Initialize the file handler.
        
        Args:
            file_watcher: Parent file watcher instance
            ignored_patterns: Patterns to ignore (e.g., ['*.pyc', '__pycache__'])
            monitored_extensions: File extensions to monitor (e.g., {'.py', '.js'})
        """
        super().__init__()
        self.file_watcher = file_watcher
        self.ignored_patterns = ignored_patterns or [
            '*.pyc', '*.pyo', '*.pyd', '__pycache__', '.git', '.vscode',
            '*.log', '*.tmp', '.DS_Store', 'Thumbs.db', '*.swp', '*.swo'
        ]
        self.monitored_extensions = monitored_extensions or {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
            '.json', '.yaml', '.yml', '.md', '.txt', '.sql', '.sh', '.bat',
            '.xml', '.php', '.rb', '.go', '.rs', '.java', '.c', '.cpp', '.h'
        }
        
        # Debouncing to avoid duplicate events
        self._last_events: Dict[str, float] = {}
        self._debounce_time = 0.5  # 500ms debounce
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored."""
        # Check file extension
        if self.monitored_extensions and file_path.suffix not in self.monitored_extensions:
            return True
        
        # Check ignored patterns
        for pattern in self.ignored_patterns:
            if pattern.startswith('*.'):
                if file_path.name.endswith(pattern[1:]):
                    return True
            elif pattern in str(file_path):
                return True
        
        return False
    
    def _debounce_event(self, event_key: str) -> bool:
        """Check if event should be debounced."""
        current_time = time.time()
        last_time = self._last_events.get(event_key, 0)
        
        if current_time - last_time < self._debounce_time:
            return True  # Should be debounced
        
        self._last_events[event_key] = current_time
        return False
    
    def _get_file_content_preview(self, file_path: Path, max_lines: int = 10) -> Optional[str]:
        """Get a preview of file content."""
        try:
            if file_path.stat().st_size > 1024 * 1024:  # Skip files larger than 1MB
                return "[File too large for preview]"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append("...")
                        break
                    lines.append(line.rstrip())
                return '\n'.join(lines)
        except Exception as e:
            logger.debug(f"Could not read file content: {e}")
            return None
    
    def on_created(self, event: FileSystemEvent):
        """Handle file/directory creation events."""
        file_path = Path(event.src_path)
        
        if event.is_directory:
            # Log directory creation
            get_terminal_logger().log_file_event(
                EventType.DIRECTORY_CREATED,
                file_path,
                f"Directory created: {file_path.name}"
            )
            return
        
        if self._should_ignore(file_path):
            return
        
        event_key = f"created:{file_path}"
        if self._debounce_event(event_key):
            return
        
        # Get file content preview
        content_preview = self._get_file_content_preview(file_path)
        
        # Create file change event
        change_event = FileChangeEvent(
            event_type='created',
            file_path=file_path,
            timestamp=datetime.now(),
            is_directory=False,
            file_size=file_path.stat().st_size if file_path.exists() else None,
            content_preview=content_preview
        )
        
        # Log to terminal
        log_file_created(file_path, content_preview)
        
        # Notify file watcher
        self.file_watcher._notify_change(change_event)
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if self._should_ignore(file_path):
            return
        
        event_key = f"modified:{file_path}"
        if self._debounce_event(event_key):
            return
        
        # Get file content preview
        content_preview = self._get_file_content_preview(file_path)
        
        # Create file change event
        change_event = FileChangeEvent(
            event_type='modified',
            file_path=file_path,
            timestamp=datetime.now(),
            is_directory=False,
            file_size=file_path.stat().st_size if file_path.exists() else None,
            content_preview=content_preview
        )
        
        # Log to terminal
        log_file_modified(file_path, content_preview)
        
        # Notify file watcher
        self.file_watcher._notify_change(change_event)
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file/directory deletion events."""
        file_path = Path(event.src_path)
        
        if self._should_ignore(file_path):
            return
        
        event_key = f"deleted:{file_path}"
        if self._debounce_event(event_key):
            return
        
        # Create file change event
        change_event = FileChangeEvent(
            event_type='deleted',
            file_path=file_path,
            timestamp=datetime.now(),
            is_directory=event.is_directory
        )
        
        # Log to terminal
        log_file_deleted(file_path)
        
        # Notify file watcher
        self.file_watcher._notify_change(change_event)
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file/directory move events."""
        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)
        
        if self._should_ignore(old_path) and self._should_ignore(new_path):
            return
        
        event_key = f"moved:{old_path}:{new_path}"
        if self._debounce_event(event_key):
            return
        
        # Create file change event
        change_event = FileChangeEvent(
            event_type='moved',
            file_path=new_path,
            timestamp=datetime.now(),
            is_directory=event.is_directory,
            old_path=old_path
        )
        
        # Log as deletion and creation
        log_file_deleted(old_path)
        log_file_created(new_path)
        
        # Notify file watcher
        self.file_watcher._notify_change(change_event)

class FileWatcher:
    """File system watcher with real-time terminal logging integration."""
    
    def __init__(self, 
                 watch_paths: Optional[List[Path]] = None,
                 recursive: bool = True,
                 use_polling: bool = False):
        """
        Initialize the file watcher.
        
        Args:
            watch_paths: Paths to watch (defaults to current directory)
            recursive: Whether to watch subdirectories
            use_polling: Force use of polling instead of native file events
        """
        self.watch_paths = watch_paths or [Path.cwd()]
        self.recursive = recursive
        self.use_polling = use_polling or not WATCHDOG_AVAILABLE
        
        # Event handling
        self.change_callbacks: List[Callable[[FileChangeEvent], None]] = []
        self.recent_changes: List[FileChangeEvent] = []
        self.max_recent_changes = 100
        
        # Watchdog components
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[BeeEgyptFileHandler] = None
        
        # Polling components
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()
        self._file_states: Dict[Path, Dict[str, Any]] = {}
        
        # Status
        self.is_watching = False
        
        logger.info(f"File watcher initialized for paths: {self.watch_paths}")
    
    def add_change_callback(self, callback: Callable[[FileChangeEvent], None]):
        """Add a callback to be called when files change."""
        self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[FileChangeEvent], None]):
        """Remove a change callback."""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
    
    def _notify_change(self, change_event: FileChangeEvent):
        """Notify all callbacks of a file change."""
        # Store recent change
        self.recent_changes.append(change_event)
        if len(self.recent_changes) > self.max_recent_changes:
            self.recent_changes = self.recent_changes[-self.max_recent_changes:]
        
        # Notify callbacks
        for callback in self.change_callbacks:
            try:
                callback(change_event)
            except Exception as e:
                logger.error(f"Error in change callback: {e}")
    
    def start_watching(self):
        """Start watching for file changes."""
        if self.is_watching:
            logger.warning("File watcher is already running")
            return
        
        if self.use_polling:
            self._start_polling()
        else:
            self._start_watchdog()
        
        self.is_watching = True
        logger.info("File watcher started")
    
    def stop_watching(self):
        """Stop watching for file changes."""
        if not self.is_watching:
            return
        
        if self.use_polling:
            self._stop_polling_watcher()
        else:
            self._stop_watchdog()
        
        self.is_watching = False
        logger.info("File watcher stopped")
    
    def _start_watchdog(self):
        """Start watchdog-based file watching."""
        if not WATCHDOG_AVAILABLE:
            logger.error("Watchdog not available, falling back to polling")
            self.use_polling = True
            self._start_polling()
            return
        
        self.event_handler = BeeEgyptFileHandler(self)
        self.observer = Observer()
        
        for watch_path in self.watch_paths:
            if watch_path.exists():
                self.observer.schedule(
                    self.event_handler, 
                    str(watch_path), 
                    recursive=self.recursive
                )
                logger.info(f"Watching path: {watch_path}")
        
        self.observer.start()
    
    def _stop_watchdog(self):
        """Stop watchdog-based file watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.event_handler = None
    
    def _start_polling(self):
        """Start polling-based file watching."""
        self._stop_polling.clear()
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._polling_thread.start()
        logger.info("Started polling-based file watching")
    
    def _stop_polling_watcher(self):
        """Stop polling-based file watching."""
        self._stop_polling.set()
        if self._polling_thread:
            self._polling_thread.join(timeout=2.0)
        self._polling_thread = None
    
    def _polling_loop(self):
        """Main polling loop for file watching."""
        poll_interval = 1.0  # Check every second
        
        while not self._stop_polling.is_set():
            try:
                self._check_file_changes()
                time.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(poll_interval)
    
    def _check_file_changes(self):
        """Check for file changes using polling."""
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
            
            self._scan_directory(watch_path)
    
    def _scan_directory(self, directory: Path):
        """Scan a directory for changes."""
        try:
            if self.recursive:
                files = directory.rglob('*')
            else:
                files = directory.iterdir()
            
            current_files = set()
            
            for file_path in files:
                if file_path.is_file():
                    current_files.add(file_path)
                    self._check_file_state(file_path)
            
            # Check for deleted files
            previous_files = set(self._file_states.keys())
            deleted_files = previous_files - current_files
            
            for deleted_file in deleted_files:
                if deleted_file in self._file_states:
                    del self._file_states[deleted_file]
                    
                    change_event = FileChangeEvent(
                        event_type='deleted',
                        file_path=deleted_file,
                        timestamp=datetime.now(),
                        is_directory=False
                    )
                    
                    log_file_deleted(deleted_file)
                    self._notify_change(change_event)
                    
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
    
    def _check_file_state(self, file_path: Path):
        """Check if a file has changed."""
        try:
            stat = file_path.stat()
            current_state = {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'exists': True
            }
            
            previous_state = self._file_states.get(file_path)
            
            if previous_state is None:
                # New file
                self._file_states[file_path] = current_state
                
                content_preview = self._get_file_content_preview(file_path)
                
                change_event = FileChangeEvent(
                    event_type='created',
                    file_path=file_path,
                    timestamp=datetime.now(),
                    is_directory=False,
                    file_size=current_state['size'],
                    content_preview=content_preview
                )
                
                log_file_created(file_path, content_preview)
                self._notify_change(change_event)
                
            elif (current_state['size'] != previous_state['size'] or 
                  current_state['mtime'] != previous_state['mtime']):
                # Modified file
                self._file_states[file_path] = current_state
                
                content_preview = self._get_file_content_preview(file_path)
                
                change_event = FileChangeEvent(
                    event_type='modified',
                    file_path=file_path,
                    timestamp=datetime.now(),
                    is_directory=False,
                    file_size=current_state['size'],
                    content_preview=content_preview
                )
                
                log_file_modified(file_path, content_preview)
                self._notify_change(change_event)
                
        except Exception as e:
            logger.debug(f"Error checking file state for {file_path}: {e}")
    
    def _get_file_content_preview(self, file_path: Path, max_lines: int = 5) -> Optional[str]:
        """Get a preview of file content."""
        try:
            if file_path.stat().st_size > 1024 * 512:  # Skip files larger than 512KB
                return "[File too large for preview]"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append("...")
                        break
                    lines.append(line.rstrip())
                return '\n'.join(lines)
        except Exception:
            return None
    
    def get_recent_changes(self, limit: int = 20) -> List[FileChangeEvent]:
        """Get recent file changes."""
        return self.recent_changes[-limit:] if self.recent_changes else []
    
    def get_change_summary(self) -> Dict[str, int]:
        """Get a summary of recent changes by type."""
        summary = {}
        for change in self.recent_changes:
            event_type = change.event_type
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary
    
    def __enter__(self):
        """Context manager entry."""
        self.start_watching()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_watching()

# Global file watcher instance
_file_watcher: Optional[FileWatcher] = None

def get_file_watcher() -> FileWatcher:
    """Get the global file watcher instance."""
    global _file_watcher
    if _file_watcher is None:
        _file_watcher = FileWatcher()
    return _file_watcher

def initialize_file_watcher(**kwargs) -> FileWatcher:
    """Initialize the global file watcher with custom settings."""
    global _file_watcher
    _file_watcher = FileWatcher(**kwargs)
    return _file_watcher

def start_file_watching(watch_paths: Optional[List[Path]] = None):
    """Start file watching with optional custom paths."""
    if watch_paths:
        initialize_file_watcher(watch_paths=watch_paths)
    get_file_watcher().start_watching()

def stop_file_watching():
    """Stop file watching."""
    global _file_watcher
    if _file_watcher:
        _file_watcher.stop_watching()
        _file_watcher = None