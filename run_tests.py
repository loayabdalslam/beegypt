#!/usr/bin/env python3
"""
Test runner for the AI Code Agent.
"""
import unittest
import sys
import os
from pathlib import Path

# Add the tests directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tests'))

# Create the tests directory if it doesn't exist
Path('tests').mkdir(exist_ok=True)

# Discover and run all tests
loader = unittest.TestLoader()
start_dir = 'tests'
suite = loader.discover(start_dir)

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Exit with non-zero code if tests failed
sys.exit(not result.wasSuccessful())
