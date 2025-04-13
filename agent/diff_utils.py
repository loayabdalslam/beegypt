"""
Diff utilities for the AI Code Agent.
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_file_diff(file_path: Path, original_content: Optional[str] = None) -> Tuple[bool, str]:
    """
    Get the diff for a single file.
    
    Args:
        file_path: Path to the file
        original_content: Original content of the file (if available)
        
    Returns:
        Tuple of (has_changes, diff_text)
    """
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"
    
    try:
        if original_content is not None:
            # Create a temporary file with the original content
            temp_file = file_path.with_suffix(f"{file_path.suffix}.orig")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Get the diff
            try:
                result = subprocess.run(
                    ['diff', '-u', str(temp_file), str(file_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                diff_text = result.stdout
                
                # Clean up the temporary file
                temp_file.unlink()
                
                return bool(diff_text), diff_text
            except Exception as e:
                logger.error(f"Error getting diff: {e}")
                # Clean up the temporary file
                if temp_file.exists():
                    temp_file.unlink()
                return False, f"Error getting diff: {e}"
        else:
            # Try to use git diff if it's a git repository
            try:
                result = subprocess.run(
                    ['git', 'diff', '--', str(file_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                diff_text = result.stdout
                
                if diff_text:
                    return True, diff_text
                
                # If no diff, check if the file is untracked
                result = subprocess.run(
                    ['git', 'ls-files', '--others', '--exclude-standard', str(file_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.stdout.strip():
                    # File is untracked, show its content as a diff
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return True, f"New file: {file_path}\n\n{content}"
                
                return False, f"No changes detected for {file_path}"
            except Exception as e:
                logger.error(f"Error getting git diff: {e}")
                
                # Fallback: just show the file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return True, f"File content: {file_path}\n\n{content}"
                except Exception as e:
                    logger.error(f"Error reading file: {e}")
                    return False, f"Error reading file: {e}"
    except Exception as e:
        logger.error(f"Error in get_file_diff: {e}")
        return False, f"Error: {e}"

def get_project_diff(project_dir: Path) -> Tuple[bool, str]:
    """
    Get the diff for an entire project.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        Tuple of (has_changes, diff_text)
    """
    if not project_dir.exists() or not project_dir.is_dir():
        return False, f"Project directory does not exist: {project_dir}"
    
    try:
        # Try to use git diff if it's a git repository
        git_dir = project_dir / ".git"
        
        if git_dir.exists() and git_dir.is_dir():
            # It's a git repository
            try:
                # Get the diff for tracked files
                result = subprocess.run(
                    ['git', '-C', str(project_dir), 'diff'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                diff_text = result.stdout
                
                # Get the list of untracked files
                result_untracked = subprocess.run(
                    ['git', '-C', str(project_dir), 'ls-files', '--others', '--exclude-standard'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                untracked_files = result_untracked.stdout.strip().split('\n')
                untracked_diff = ""
                
                # Add content of untracked files to the diff
                for file in untracked_files:
                    if file:
                        file_path = project_dir / file
                        if file_path.is_file():
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                untracked_diff += f"\n\n--- /dev/null\n+++ b/{file}\n@@ -0,0 +1,{len(content.split('\\n'))} @@\n"
                                for line in content.split('\n'):
                                    untracked_diff += f"+{line}\n"
                            except Exception as e:
                                logger.error(f"Error reading untracked file {file}: {e}")
                
                # Combine tracked and untracked diffs
                combined_diff = diff_text
                if untracked_diff:
                    if combined_diff:
                        combined_diff += "\n" + untracked_diff
                    else:
                        combined_diff = untracked_diff
                
                return bool(combined_diff), combined_diff or "No changes detected"
            except Exception as e:
                logger.error(f"Error getting git diff: {e}")
                return False, f"Error getting git diff: {e}"
        else:
            # Not a git repository, list all files
            all_files = []
            for root, _, files in os.walk(project_dir):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(project_dir)
                    
                    # Skip common binary files and hidden files
                    if any(ext in file_path.suffix.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip']):
                        continue
                    
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in rel_path.parts):
                        continue
                    
                    all_files.append(rel_path)
            
            # Sort files for consistent output
            all_files.sort()
            
            # Generate a "diff" showing all files
            diff_text = f"Project directory: {project_dir}\n\n"
            diff_text += f"Found {len(all_files)} files:\n\n"
            
            for file in all_files[:20]:  # Limit to first 20 files to avoid overwhelming output
                diff_text += f"- {file}\n"
            
            if len(all_files) > 20:
                diff_text += f"\n... and {len(all_files) - 20} more files\n"
            
            return True, diff_text
    except Exception as e:
        logger.error(f"Error in get_project_diff: {e}")
        return False, f"Error: {e}"
