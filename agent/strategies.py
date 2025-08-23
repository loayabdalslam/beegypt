from abc import ABC, abstractmethod
from typing import Dict, Optional

from rich.console import Console

from .unified_mcp_integration import get_unified_mcp_integration

console = Console()

class BaseProjectStrategy(ABC):
    """Abstract base class for a project creation strategy."""

    @abstractmethod
    def get_project_type_name(self) -> str:
        """Returns the human-readable name of the project type."""
        pass

    @abstractmethod
    def get_package_structure(self, project_description: Dict) -> Dict:
        """Returns the structure for package files like package.json."""
        pass

    @abstractmethod
    def generate_gitignore_content(self, technologies: list) -> str:
        """Generates the content for the .gitignore file."""
        pass

    @abstractmethod
    def enhance_with_mcp(self) -> None:
        """Performs optional enhancements using MCP integrations like ShadCN or Context7."""
        pass


class ReactViteExpressStrategy(BaseProjectStrategy):
    """Strategy for creating a React (Vite) + Express project."""

    def get_project_type_name(self) -> str:
        return "React (Vite) + Express"

    def get_package_structure(self, project_description: Dict) -> Dict:
        """Returns a basic structure for a React/Express package.json."""
        return {
            "project_name": project_description.get("project_name", "my-react-express-app"),
            "description": project_description.get("description", "A React and Express application"),
            "scripts": {
                "dev:backend": "node backend/index.js",
                "dev:frontend": "vite",
                "dev": "npm-run-all --parallel dev:*"
            },
            "dependencies": {
                "express": "^4.18.2"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.0.0",
                "npm-run-all": "^4.1.5",
                "vite": "^4.3.9",
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            }
        }

    def generate_gitignore_content(self, technologies: list) -> str:
        """Generates a .gitignore for Node.js projects."""
        return """
# Dependencies
/node_modules
# Build artifacts
/dist
/build
# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*
# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
# IDEs and editors
.idea/
.vscode/
*.swp
*.swo
*~
"""

    def enhance_with_mcp(self) -> None:
        """Enhance the project using unified MCP integration for Context7 and ShadCN"""
        try:
            console.print("\n[bold blue]🚀 Enhancing project with MCP integration...[/bold blue]")
            unified_integration = get_unified_mcp_integration()
            if not unified_integration:
                console.print("  [yellow]Warning: Unified MCP integration not available[/yellow]")
                return

            analysis = unified_integration.analyze_project_structure()
            project_type = analysis.get('project_type', 'unknown')
            console.print(f"  [dim]Detected project type: {project_type}[/dim]")

            # Get and display recommendations
            recommendations = unified_integration.get_integration_recommendations()
            if recommendations:
                console.print("  [dim]💡 Integration recommendations:[/dim]")
                for rec in recommendations[:3]:
                    console.print(f"    - {rec}")

            console.print("  [green]✅ MCP integration enhancement check completed[/green]")

        except Exception as e:
            console.print(f"  [yellow]Warning: Could not enhance project with MCP integration: {str(e)}[/yellow]")


class DefaultStrategy(BaseProjectStrategy):
    """A fallback strategy that performs no special operations."""

    def get_project_type_name(self) -> str:
        return "Generic Project"

    def get_package_structure(self, project_description: Dict) -> Dict:
        return {
            "project_name": project_description.get("project_name", "generic-project"),
            "description": project_description.get("description", "A generic project"),
        }

    def generate_gitignore_content(self, technologies: list) -> str:
        return "# Add project-specific files to ignore\n"

    def enhance_with_mcp(self) -> None:
        # Does nothing by design
        pass


class StrategyFactory:
    """Factory for creating project strategy instances."""

    _strategies = {
        "react": ReactViteExpressStrategy,
        # Add other strategies here, e.g., "python_flask": PythonFlaskStrategy
    }

    @staticmethod
    def get_strategy(project_type: str) -> BaseProjectStrategy:
        """
        Returns a strategy instance for the given project type.
        Falls back to a default if the specific type is not found.
        """
        # Simple detection logic, can be improved
        if 'react' in project_type.lower() or 'vite' in project_type.lower():
            strategy_class = StrategyFactory._strategies.get("react")
        # Add more rules here, e.g., for 'python', 'flask', 'vue', etc.
        else:
            strategy_class = None

        return strategy_class() if strategy_class else DefaultStrategy()
