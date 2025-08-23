#!/usr/bin/env python3
"""
Shadcn-UI CLI Interface

Command-line interface for shadcn-ui integration, providing:
- Health checks and status reporting
- Component management and suggestions
- Project setup assistance
- Interactive component browser
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from .shadcn_integration import (
    get_shadcn_integration,
    initialize_shadcn_integration,
    perform_shadcn_health_check,
    ComponentStatus,
    ProjectType
)

class ShadcnCLI:
    """Command-line interface for shadcn-ui integration"""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.integration = None
    
    def run(self, args: List[str] = None) -> int:
        """Run the CLI with given arguments"""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)
        
        # Initialize integration
        project_path = Path(parsed_args.project_path) if parsed_args.project_path else Path.cwd()
        self.integration = initialize_shadcn_integration(project_path)
        
        try:
            return parsed_args.func(parsed_args)
        except AttributeError:
            parser.print_help()
            return 1
        except Exception as e:
            if self.console:
                self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
            else:
                print(f"Error: {str(e)}")
            return 1
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description="shadcn-ui Integration CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            "--project-path",
            type=str,
            help="Path to the project directory (default: current directory)"
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Health check command
        health_parser = subparsers.add_parser(
            "health",
            help="Perform comprehensive health check"
        )
        health_parser.set_defaults(func=self._cmd_health_check)
        
        # Status command
        status_parser = subparsers.add_parser(
            "status",
            help="Show current status and configuration"
        )
        status_parser.set_defaults(func=self._cmd_status)
        
        # List components command
        list_parser = subparsers.add_parser(
            "list",
            help="List available and installed components"
        )
        list_parser.add_argument(
            "--installed-only",
            action="store_true",
            help="Show only installed components"
        )
        list_parser.add_argument(
            "--available-only",
            action="store_true",
            help="Show only available components"
        )
        list_parser.set_defaults(func=self._cmd_list_components)
        
        # Component info command
        info_parser = subparsers.add_parser(
            "info",
            help="Get detailed information about a component"
        )
        info_parser.add_argument(
            "component",
            help="Component name to get information about"
        )
        info_parser.set_defaults(func=self._cmd_component_info)
        
        # Suggest components command
        suggest_parser = subparsers.add_parser(
            "suggest",
            help="Suggest components for a feature or use case"
        )
        suggest_parser.add_argument(
            "description",
            help="Description of the feature or use case"
        )
        suggest_parser.set_defaults(func=self._cmd_suggest_components)
        
        # Usage guide command
        guide_parser = subparsers.add_parser(
            "guide",
            help="Generate usage guide for a component"
        )
        guide_parser.add_argument(
            "component",
            help="Component name to generate guide for"
        )
        guide_parser.set_defaults(func=self._cmd_usage_guide)
        
        # Interactive browser command
        browse_parser = subparsers.add_parser(
            "browse",
            help="Interactive component browser"
        )
        browse_parser.set_defaults(func=self._cmd_browse_components)
        
        return parser
    
    def _cmd_health_check(self, args) -> int:
        """Perform health check command"""
        if self.console:
            self.console.print("[bold blue]Running shadcn-ui Health Check...[/bold blue]")
        
        result = self.integration.perform_health_check()
        
        if not self.console:
            # Fallback for no rich
            print(f"Health Status: {'Healthy' if result.is_healthy else 'Issues Found'}")
            if result.issues:
                print("Issues:")
                for issue in result.issues:
                    print(f"  - {issue}")
            if result.recommendations:
                print("Recommendations:")
                for rec in result.recommendations:
                    print(f"  - {rec}")
        
        return 0 if result.is_healthy else 1
    
    def _cmd_status(self, args) -> int:
        """Show status command"""
        status_report = self.integration.get_status_report()
        
        if self.console:
            # Create status table
            table = Table(title="shadcn-ui Status Report")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            health = status_report["health_check"]
            table.add_row("Health Status", "✅ Healthy" if health["is_healthy"] else "❌ Issues")
            table.add_row("Project Type", health["project_type"] or "Unknown")
            table.add_row("Components Installed", str(health["components_installed"]))
            table.add_row("Components Available", str(health["components_available"]))
            table.add_row("Issues Count", str(health["issues_count"]))
            
            self.console.print(table)
        else:
            # Fallback for no rich
            health = status_report["health_check"]
            print(f"Health Status: {'Healthy' if health['is_healthy'] else 'Issues'}")
            print(f"Project Type: {health['project_type'] or 'Unknown'}")
            print(f"Components Installed: {health['components_installed']}")
            print(f"Components Available: {health['components_available']}")
        
        return 0
    
    def _cmd_list_components(self, args) -> int:
        """List components command"""
        result = self.integration.perform_health_check()
        
        if args.installed_only:
            components = result.components_installed
            title = "Installed Components"
        elif args.available_only:
            components = [c for c in result.components_available if c not in result.components_installed]
            title = "Available Components"
        else:
            components = result.components_available
            title = "All Components"
        
        if self.console:
            if not components:
                self.console.print(f"[yellow]No components found for '{title.lower()}'[/yellow]")
                return 0
            
            # Create components table
            table = Table(title=title)
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            
            for component in sorted(components):
                status = "✅ Installed" if component in result.components_installed else "📦 Available"
                table.add_row(component, status)
            
            self.console.print(table)
        else:
            # Fallback for no rich
            print(f"{title}:")
            for component in sorted(components):
                status = "[Installed]" if component in result.components_installed else "[Available]"
                print(f"  {component} {status}")
        
        return 0
    
    def _cmd_component_info(self, args) -> int:
        """Component info command"""
        component_info = self.integration.get_component_info(args.component)
        
        if not component_info:
            if self.console:
                self.console.print(f"[red]Component '{args.component}' not found[/red]")
            else:
                print(f"Component '{args.component}' not found")
            return 1
        
        if self.console:
            # Create info panel
            info_content = []
            info_content.append(f"Name: [cyan]{component_info.name}[/cyan]")
            info_content.append(f"Status: [green]{component_info.status.value}[/green]")
            info_content.append(f"Description: {component_info.description}")
            
            if component_info.dependencies:
                info_content.append(f"Dependencies: {', '.join(component_info.dependencies)}")
            
            self.console.print(Panel("\n".join(info_content), title=f"Component: {args.component}"))
        else:
            # Fallback for no rich
            print(f"Component: {component_info.name}")
            print(f"Status: {component_info.status.value}")
            print(f"Description: {component_info.description}")
        
        return 0
    
    def _cmd_suggest_components(self, args) -> int:
        """Suggest components command"""
        suggestions = self.integration.suggest_components_for_feature(args.description)
        
        if not suggestions:
            if self.console:
                self.console.print(f"[yellow]No component suggestions found for '{args.description}'[/yellow]")
            else:
                print(f"No component suggestions found for '{args.description}'")
            return 0
        
        if self.console:
            self.console.print(f"\n[bold blue]Component suggestions for '{args.description}':[/bold blue]")
            for i, component in enumerate(suggestions, 1):
                self.console.print(f"  {i}. [cyan]{component}[/cyan]")
        else:
            print(f"Component suggestions for '{args.description}':")
            for i, component in enumerate(suggestions, 1):
                print(f"  {i}. {component}")
        
        return 0
    
    def _cmd_usage_guide(self, args) -> int:
        """Usage guide command"""
        guide = self.integration.generate_component_usage_guide(args.component)
        
        if self.console:
            self.console.print(Markdown(guide))
        else:
            print(guide)
        
        return 0
    
    def _cmd_browse_components(self, args) -> int:
        """Interactive component browser"""
        if not self.console:
            print("Interactive browsing requires the 'rich' library")
            return 1
        
        result = self.integration.perform_health_check()
        components = sorted(result.components_available)
        
        while True:
            self.console.print("\n[bold blue]shadcn-ui Component Browser[/bold blue]")
            self.console.print("Available commands:")
            self.console.print("  [cyan]list[/cyan] - List all components")
            self.console.print("  [cyan]info <component>[/cyan] - Get component information")
            self.console.print("  [cyan]guide <component>[/cyan] - Show usage guide")
            self.console.print("  [cyan]suggest <description>[/cyan] - Get component suggestions")
            self.console.print("  [cyan]quit[/cyan] - Exit browser")
            
            command = Prompt.ask("\nEnter command").strip().split()
            
            if not command:
                continue
            
            cmd = command[0].lower()
            
            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "list":
                self._show_component_list(components, result.components_installed)
            elif cmd == "info" and len(command) > 1:
                self._show_component_info(command[1])
            elif cmd == "guide" and len(command) > 1:
                self._show_usage_guide(command[1])
            elif cmd == "suggest" and len(command) > 1:
                description = " ".join(command[1:])
                self._show_suggestions(description)
            else:
                self.console.print("[red]Invalid command or missing arguments[/red]")
        
        return 0
    
    def _show_component_list(self, components: List[str], installed: List[str]) -> None:
        """Show component list in browser"""
        table = Table(title="Available Components")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        
        for component in components:
            status = "✅ Installed" if component in installed else "📦 Available"
            table.add_row(component, status)
        
        self.console.print(table)
    
    def _show_component_info(self, component_name: str) -> None:
        """Show component info in browser"""
        component_info = self.integration.get_component_info(component_name)
        
        if not component_info:
            self.console.print(f"[red]Component '{component_name}' not found[/red]")
            return
        
        info_content = []
        info_content.append(f"Name: [cyan]{component_info.name}[/cyan]")
        info_content.append(f"Status: [green]{component_info.status.value}[/green]")
        info_content.append(f"Description: {component_info.description}")
        
        self.console.print(Panel("\n".join(info_content), title=f"Component: {component_name}"))
    
    def _show_usage_guide(self, component_name: str) -> None:
        """Show usage guide in browser"""
        guide = self.integration.generate_component_usage_guide(component_name)
        self.console.print(Markdown(guide))
    
    def _show_suggestions(self, description: str) -> None:
        """Show component suggestions in browser"""
        suggestions = self.integration.suggest_components_for_feature(description)
        
        if not suggestions:
            self.console.print(f"[yellow]No suggestions found for '{description}'[/yellow]")
            return
        
        self.console.print(f"\n[bold blue]Suggestions for '{description}':[/bold blue]")
        for i, component in enumerate(suggestions, 1):
            self.console.print(f"  {i}. [cyan]{component}[/cyan]")

def main(args: List[str] = None) -> int:
    """Main entry point for CLI"""
    cli = ShadcnCLI()
    return cli.run(args)

if __name__ == "__main__":
    sys.exit(main())