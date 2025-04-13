#!/usr/bin/env python3
"""
Tests for the fix_project script.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fix_project import fix_project, analyze_project, identify_issues, generate_fixes, apply_fixes
from config import OUTPUT_DIR

class TestFixProject(unittest.TestCase):
    """Test cases for the fix_project script."""

    @patch('fix_project.AIClientFactory')
    @patch('fix_project.analyze_project')
    @patch('fix_project.identify_issues')
    @patch('fix_project.generate_fixes')
    @patch('fix_project.apply_fixes')
    @patch('fix_project.LocalDeployer')
    @patch('fix_project.CodeAgent')
    def test_fix_project_success(self, mock_code_agent, mock_deployer, mock_apply_fixes, 
                                mock_generate_fixes, mock_identify_issues, mock_analyze_project, 
                                mock_ai_factory):
        """Test that fix_project works correctly when all steps succeed."""
        # Setup mocks
        mock_ai_client = MagicMock()
        mock_ai_factory.create_client.return_value = mock_ai_client
        
        mock_analyze_project.return_value = {"success": True, "analysis": "Test analysis"}
        mock_identify_issues.return_value = {"success": True, "issues_text": "Test issues"}
        mock_generate_fixes.return_value = {"success": True, "fixes": {}}
        mock_apply_fixes.return_value = {"modified_files": [], "created_files": [], "errors": []}
        
        mock_deployer_instance = MagicMock()
        mock_deployer.return_value = mock_deployer_instance
        mock_deployer_instance.deploy_locally.return_value = {"success": True, "message": "Deployed"}
        
        # Call fix_project
        result = fix_project(
            project_dir=Path("test_project"),
            problem_description="Test problem",
            open_editor=False,
            deploy=True
        )
        
        # Assertions
        self.assertTrue(result)
        mock_ai_factory.create_client.assert_called_once()
        mock_analyze_project.assert_called_once()
        mock_identify_issues.assert_called_once()
        mock_generate_fixes.assert_called_once()
        mock_apply_fixes.assert_called_once()
        mock_deployer.assert_called_once()
        mock_deployer_instance.deploy_locally.assert_called_once()

    @patch('fix_project.AIClientFactory')
    @patch('fix_project.analyze_project')
    def test_fix_project_analysis_failure(self, mock_analyze_project, mock_ai_factory):
        """Test that fix_project handles analysis failure."""
        # Setup mocks
        mock_ai_client = MagicMock()
        mock_ai_factory.create_client.return_value = mock_ai_client
        
        mock_analyze_project.return_value = {"success": False, "error": "Analysis error"}
        
        # Call fix_project
        result = fix_project(
            project_dir=Path("test_project"),
            problem_description="Test problem",
            open_editor=False,
            deploy=False
        )
        
        # Assertions
        self.assertFalse(result)
        mock_ai_factory.create_client.assert_called_once()
        mock_analyze_project.assert_called_once()

    @patch('fix_project.AIClientFactory')
    @patch('fix_project.analyze_project')
    @patch('fix_project.identify_issues')
    def test_fix_project_issues_failure(self, mock_identify_issues, mock_analyze_project, mock_ai_factory):
        """Test that fix_project handles issues identification failure."""
        # Setup mocks
        mock_ai_client = MagicMock()
        mock_ai_factory.create_client.return_value = mock_ai_client
        
        mock_analyze_project.return_value = {"success": True, "analysis": "Test analysis"}
        mock_identify_issues.return_value = {"success": False, "error": "Issues error"}
        
        # Call fix_project
        result = fix_project(
            project_dir=Path("test_project"),
            problem_description="Test problem",
            open_editor=False,
            deploy=False
        )
        
        # Assertions
        self.assertFalse(result)
        mock_ai_factory.create_client.assert_called_once()
        mock_analyze_project.assert_called_once()
        mock_identify_issues.assert_called_once()

    @patch('fix_project.AIClientFactory')
    @patch('fix_project.analyze_project')
    @patch('fix_project.identify_issues')
    @patch('fix_project.generate_fixes')
    def test_fix_project_fixes_failure(self, mock_generate_fixes, mock_identify_issues, 
                                     mock_analyze_project, mock_ai_factory):
        """Test that fix_project handles fixes generation failure."""
        # Setup mocks
        mock_ai_client = MagicMock()
        mock_ai_factory.create_client.return_value = mock_ai_client
        
        mock_analyze_project.return_value = {"success": True, "analysis": "Test analysis"}
        mock_identify_issues.return_value = {"success": True, "issues_text": "Test issues"}
        mock_generate_fixes.return_value = {"success": False, "error": "Fixes error"}
        
        # Call fix_project
        result = fix_project(
            project_dir=Path("test_project"),
            problem_description="Test problem",
            open_editor=False,
            deploy=False
        )
        
        # Assertions
        self.assertFalse(result)
        mock_ai_factory.create_client.assert_called_once()
        mock_analyze_project.assert_called_once()
        mock_identify_issues.assert_called_once()
        mock_generate_fixes.assert_called_once()

    @patch('fix_project.open')
    def test_analyze_project(self, mock_open):
        """Test the analyze_project function."""
        # Setup mock
        mock_open.side_effect = lambda *args, **kwargs: MagicMock()
        mock_ai_client = MagicMock()
        mock_ai_client.generate_text.return_value = "Test analysis"
        
        # Create a test directory structure
        test_dir = Path("test_project")
        
        # Call analyze_project
        with patch('fix_project.Path.glob') as mock_glob, \
             patch('fix_project.Path.is_file') as mock_is_file, \
             patch('fix_project.Path.is_dir') as mock_is_dir, \
             patch('fix_project.Path.exists') as mock_exists:
            
            mock_glob.return_value = [Path("test_project/file1.py"), Path("test_project/file2.py")]
            mock_is_file.return_value = True
            mock_is_dir.return_value = False
            mock_exists.return_value = True
            
            result = analyze_project(test_dir, mock_ai_client)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["analysis"], "Test analysis")
        mock_ai_client.generate_text.assert_called_once()

    def test_identify_issues(self):
        """Test the identify_issues function."""
        # Setup
        mock_ai_client = MagicMock()
        mock_ai_client.generate_text.return_value = "Test issues"
        project_dir = Path("test_project")
        problem_description = "Test problem"
        project_analysis = {"analysis": "Test analysis", "project_type": "python", "technologies": ["python"]}
        
        # Call identify_issues
        result = identify_issues(project_dir, problem_description, project_analysis, mock_ai_client)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["issues_text"], "Test issues")
        mock_ai_client.generate_text.assert_called_once()

    def test_generate_fixes(self):
        """Test the generate_fixes function."""
        # Setup
        mock_ai_client = MagicMock()
        mock_ai_client.generate_text.return_value = '{"files_to_modify": [], "files_to_create": []}'
        project_dir = Path("test_project")
        problem_description = "Test problem"
        project_analysis = {"analysis": "Test analysis", "files": []}
        issues = {"issues_text": "Test issues"}
        
        # Call generate_fixes
        with patch('fix_project.open') as mock_open:
            mock_open.side_effect = lambda *args, **kwargs: MagicMock()
            result = generate_fixes(project_dir, problem_description, project_analysis, issues, mock_ai_client)
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertIn("fixes", result)
        mock_ai_client.generate_text.assert_called_once()

    def test_apply_fixes(self):
        """Test the apply_fixes function."""
        # Setup
        project_dir = Path("test_project")
        fixes = {
            "files_to_modify": [
                {
                    "file_path": "file1.py",
                    "changes": [
                        {
                            "type": "replace",
                            "old_code": "old code",
                            "new_code": "new code"
                        }
                    ]
                }
            ],
            "files_to_create": [
                {
                    "file_path": "file2.py",
                    "content": "file content"
                }
            ]
        }
        
        # Call apply_fixes
        with patch('fix_project.open') as mock_open, \
             patch('fix_project.Path.exists') as mock_exists, \
             patch('fix_project.Path.mkdir') as mock_mkdir:
            
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = "old code"
            mock_open.side_effect = [mock_file, MagicMock()]
            mock_exists.return_value = True
            
            result = apply_fixes(project_dir, fixes)
        
        # Assertions
        self.assertEqual(len(result["modified_files"]), 1)
        self.assertEqual(len(result["created_files"]), 1)
        self.assertEqual(len(result["errors"]), 0)

if __name__ == '__main__':
    unittest.main()
