#!/bin/bash
# Examples of using BeeAgent (now with main.py)

# Create a new React todo app using oneshot mode
echo "Example 1: Creating a new React todo app"
python main.py --path ./output/todo-app --prompt "Create a React todo list application with local storage" --oneshot --no-editor

# Edit an existing project using oneshot mode
echo "Example 2: Adding features to the todo app"
python main.py --path ./output/todo-app --prompt "Add dark mode support and categories to the todo app" --oneshot --no-editor

# Create a Python web application using oneshot mode
echo "Example 3: Creating a Python Flask web application"
python main.py --path ./output/flask-app --prompt "Create a Flask web application with user authentication and a blog" --oneshot --no-editor --no-code-generators

# Force create a new project in an existing directory using oneshot mode
echo "Example 4: Force creating a new project"
python main.py --path ./output/new-project --prompt "Create a simple HTML/CSS/JS landing page" --force-create --oneshot --no-editor
