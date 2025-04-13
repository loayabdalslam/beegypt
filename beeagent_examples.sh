#!/bin/bash
# Examples of using BeeAgent

# Create a new React todo app
echo "Example 1: Creating a new React todo app"
python beeagent.py --path ./output/todo-app --prompt "Create a React todo list application with local storage" --no-editor

# Edit an existing project (assuming the todo app was created)
echo "Example 2: Adding features to the todo app"
python beeagent.py --path ./output/todo-app --prompt "Add dark mode support and categories to the todo app" --no-editor

# Create a Python web application
echo "Example 3: Creating a Python Flask web application"
python beeagent.py --path ./output/flask-app --prompt "Create a Flask web application with user authentication and a blog" --no-editor --no-code-generators

# Force create a new project in an existing directory
echo "Example 4: Force creating a new project"
python beeagent.py --path ./output/new-project --prompt "Create a simple HTML/CSS/JS landing page" --force-create --no-editor
