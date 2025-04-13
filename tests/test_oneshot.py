#!/usr/bin/env python3
"""
Tests for the oneshot script.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oneshot import oneshot
from config import OUTPUT_DIR

class TestOneshot(unittest.TestCase):
    """Test cases for the oneshot script."""

    @patch('oneshot.CodeAgent')
    def test_oneshot_initialization(self, mock_code_agent):
        """Test that oneshot initializes the CodeAgent correctly."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": True}
        mock_instance.setup_project.return_value = {"success": True}
        mock_instance.tasks = []

        # Call oneshot
        result = oneshot(
            description="Test project",
            output_dir=OUTPUT_DIR / "test_oneshot",
            open_editor=False,
            deploy=False
        )

        # Assertions
        self.assertTrue(result)
        mock_code_agent.assert_called_once()
        mock_instance.process_project_description.assert_called_once_with("Test project")
        mock_instance.setup_project.assert_called_once()

    @patch('oneshot.CodeAgent')
    def test_oneshot_with_project_name(self, mock_code_agent):
        """Test that oneshot uses the provided project name."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": True}
        mock_instance.setup_project.return_value = {"success": True}
        mock_instance.tasks = []

        # Call oneshot with project name
        result = oneshot(
            description="Test project",
            output_dir=OUTPUT_DIR / "test_oneshot",
            open_editor=False,
            deploy=False,
            project_name="custom_name"
        )

        # Assertions
        self.assertTrue(result)
        self.assertEqual(mock_instance.project_name, "custom_name")

    @patch('oneshot.CodeAgent')
    def test_oneshot_with_no_code_generators(self, mock_code_agent):
        """Test that oneshot sets the NO_CODE_GENERATORS environment variable."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": True}
        mock_instance.setup_project.return_value = {"success": True}
        mock_instance.tasks = []

        # Call oneshot with no_code_generators=True
        with patch.dict(os.environ, {}, clear=True):
            result = oneshot(
                description="Test project",
                output_dir=OUTPUT_DIR / "test_oneshot",
                open_editor=False,
                deploy=False,
                no_code_generators=True
            )

            # Assertions
            self.assertTrue(result)
            self.assertEqual(os.environ.get("NO_CODE_GENERATORS"), "true")

    @patch('oneshot.CodeAgent')
    def test_oneshot_with_code_generators_allowed(self, mock_code_agent):
        """Test that oneshot doesn't set the NO_CODE_GENERATORS environment variable when allowed."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": True}
        mock_instance.setup_project.return_value = {"success": True}
        mock_instance.tasks = []

        # Call oneshot with no_code_generators=False
        with patch.dict(os.environ, {}, clear=True):
            result = oneshot(
                description="Test project",
                output_dir=OUTPUT_DIR / "test_oneshot",
                open_editor=False,
                deploy=False,
                no_code_generators=False
            )

            # Assertions
            self.assertTrue(result)
            self.assertNotEqual(os.environ.get("NO_CODE_GENERATORS"), "true")

    @patch('oneshot.CodeAgent')
    def test_oneshot_process_description_failure(self, mock_code_agent):
        """Test that oneshot handles process_project_description failure."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": False, "error": "Test error"}

        # Call oneshot
        result = oneshot(
            description="Test project",
            output_dir=OUTPUT_DIR / "test_oneshot",
            open_editor=False,
            deploy=False
        )

        # Assertions
        self.assertFalse(result)

    @patch('oneshot.CodeAgent')
    def test_oneshot_setup_project_failure(self, mock_code_agent):
        """Test that oneshot handles setup_project failure."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": True}
        mock_instance.setup_project.return_value = {"success": False, "error": "Test error"}

        # Call oneshot
        result = oneshot(
            description="Test project",
            output_dir=OUTPUT_DIR / "test_oneshot",
            open_editor=False,
            deploy=False
        )

        # Assertions
        self.assertFalse(result)

    @patch('oneshot.CodeAgent')
    def test_oneshot_task_execution(self, mock_code_agent):
        """Test that oneshot executes tasks correctly."""
        # Setup mock
        mock_instance = MagicMock()
        mock_code_agent.return_value = mock_instance
        mock_instance.process_project_description.return_value = {"success": True}
        mock_instance.setup_project.return_value = {"success": True}
        mock_instance.tasks = [
            {"task name": "Task 1", "description": "Test task 1"},
            {"task name": "Task 2", "description": "Test task 2"}
        ]
        mock_instance.execute_task.return_value = {"success": True}

        # Call oneshot
        result = oneshot(
            description="Test project",
            output_dir=OUTPUT_DIR / "test_oneshot",
            open_editor=False,
            deploy=False
        )

        # Assertions
        self.assertTrue(result)
        self.assertEqual(mock_instance.execute_task.call_count, 2)
        mock_instance.execute_task.assert_any_call(0)
        mock_instance.execute_task.assert_any_call(1)

if __name__ == '__main__':
    unittest.main()
