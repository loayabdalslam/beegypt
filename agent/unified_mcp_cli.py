#!/usr/bin/env python3
"""
Unified MCP CLI Interface

Command-line interface for the unified Context7 and ShadCN MCP integration.
Provides interactive project generation, modification, and component management.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich.columns import Columns
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from .unified_mcp_integration import (
    UnifiedMCPIntegration, ProjectRequirements, IntegrationType, 
    CodeGenerationStrategy, initialize_unified_mcp_integration,
    get_unified_mcp_integration, generate_project_with_mcp,
    modify_project_with_mcp
)

logger = logging.getLogger(__name__)

class UnifiedMCPCLI:
    """Command-line interface for unified MCP integration"""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.integration: Optional[UnifiedMCPIntegration] = None
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with given arguments"""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)
        
        # Set up logging
        log_level = logging.DEBUG if parsed_args.verbose else logging.INFO
        logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
        
        try:
            # Initialize integration
            project_path = Path(parsed_args.project_path).resolve()
            self.integration = initialize_unified_mcp_integration(project_path)
            
            # Execute command
            return parsed_args.func(parsed_args)
            
        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            else:
                print("\nOperation cancelled by user")
            return 1
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error: {str(e)}[/red]")
            else:
                print(f"Error: {str(e)}")
            if parsed_args.verbose:
                raise
            return 1
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description="Unified MCP Integration CLI - Generate and modify projects with Context7 and ShadCN",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate a new React project
  python -m agent.unified_mcp_cli generate --project-type react --features routing,authentication
  
  # Add components to existing project
  python -m agent.unified_mcp_cli modify --add-components button,card,form
  
  # Interactive project generation
  python -m agent.unified_mcp_cli interactive
  
  # Analyze existing project
  python -m agent.unified_mcp_cli analyze
"""
        )
        
        parser.add_argument(
            "--project-path",
            type=str,
            default=".",
            help="Path to the project directory (default: current directory)"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Generate command
        generate_parser = subparsers.add_parser(
            "generate",
            help="Generate a new project"
        )
        generate_parser.add_argument(
            "--project-type",
            choices=["react", "nextjs", "vue", "angular"],
            required=True,
            help="Type of project to generate"
        )
        generate_parser.add_argument(
            "--features",
            type=str,
            help="Comma-separated list of features (routing,authentication,state-management,etc.)"
        )
        generate_parser.add_argument(
            "--components",
            type=str,
            help="Comma-separated list of UI components to include"
        )
        generate_parser.add_argument(
            "--styling",
            choices=["tailwind", "styled-components", "emotion", "css-modules"],
            default="tailwind",
            help="Styling approach (default: tailwind)"
        )
        generate_parser.add_argument(
            "--state-management",
            choices=["zustand", "redux", "recoil", "context"],
            help="State management library"
        )
        generate_parser.add_argument(
            "--strategy",
            choices=["minimal", "comprehensive", "best_practices", "performance_optimized"],
            default="comprehensive",
            help="Code generation strategy (default: comprehensive)"
        )
        generate_parser.add_argument(
            "--output-dir",
            type=str,
            help="Output directory for generated project"
        )
        generate_parser.set_defaults(func=self._handle_generate)
        
        # Modify command
        modify_parser = subparsers.add_parser(
            "modify",
            help="Modify an existing project"
        )
        modify_parser.add_argument(
            "--add-components",
            type=str,
            help="Comma-separated list of components to add"
        )
        modify_parser.add_argument(
            "--add-features",
            type=str,
            help="Comma-separated list of features to add"
        )
        modify_parser.add_argument(
            "--integration-type",
            choices=["component_addition", "feature_enhancement", "library_migration"],
            default="feature_enhancement",
            help="Type of modification (default: feature_enhancement)"
        )
        modify_parser.set_defaults(func=self._handle_modify)
        
        # Analyze command
        analyze_parser = subparsers.add_parser(
            "analyze",
            help="Analyze existing project structure"
        )
        analyze_parser.add_argument(
            "--format",
            choices=["table", "json", "tree"],
            default="table",
            help="Output format (default: table)"
        )
        analyze_parser.set_defaults(func=self._handle_analyze)
        
        # Interactive command
        interactive_parser = subparsers.add_parser(
            "interactive",
            help="Interactive project generation and modification"
        )
        interactive_parser.set_defaults(func=self._handle_interactive)
        
        # Status command
        status_parser = subparsers.add_parser(
            "status",
            help="Show integration status and health"
        )
        status_parser.set_defaults(func=self._handle_status)
        
        # Components command
        components_parser = subparsers.add_parser(
            "components",
            help="Manage ShadCN components"
        )
        components_subparsers = components_parser.add_subparsers(dest="components_action")
        
        list_comp_parser = components_subparsers.add_parser("list", help="List available components")
        list_comp_parser.set_defaults(func=self._handle_list_components)
        
        info_comp_parser = components_subparsers.add_parser("info", help="Get component information")
        info_comp_parser.add_argument("component_name", help="Name of the component")
        info_comp_parser.set_defaults(func=self._handle_component_info)
        
        # Libraries command
        libraries_parser = subparsers.add_parser(
            "libraries",
            help="Manage Context7 libraries"
        )
        libraries_subparsers = libraries_parser.add_subparsers(dest="libraries_action")
        
        search_lib_parser = libraries_subparsers.add_parser("search", help="Search for libraries")
        search_lib_parser.add_argument("query", help="Search query")
        search_lib_parser.set_defaults(func=self._handle_search_libraries)
        
        docs_lib_parser = libraries_subparsers.add_parser("docs", help="Get library documentation")
        docs_lib_parser.add_argument("library_name", help="Name of the library")
        docs_lib_parser.add_argument("--topic", help="Specific topic to focus on")
        docs_lib_parser.set_defaults(func=self._handle_library_docs)
        
        return parser
    
    def _handle_generate(self, args) -> int:
        """Handle project generation"""
        try:
            if self.console:
                self.console.print("[bold blue]🚀 Generating new project...[/bold blue]\n")
            
            # Parse requirements
            requirements = self._parse_requirements_from_args(args)
            strategy = CodeGenerationStrategy(args.strategy)
            
            # Generate project
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) if self.console else self._dummy_progress() as progress:
                task = progress.add_task("Generating project files...", total=None)
                result = self.integration.generate_new_project(requirements, strategy)
                progress.update(task, completed=True)
            
            if result and result.success:
                self._display_generation_result(result, args.output_dir)
                return 0
            else:
                if self.console:
                    self.console.print("[red]❌ Project generation failed[/red]")
                else:
                    print("❌ Project generation failed")
                return 1
                
        except Exception as e:
            logger.error(f"Error generating project: {str(e)}")
            return 1
    
    def _handle_modify(self, args) -> int:
        """Handle project modification"""
        try:
            if self.console:
                self.console.print("[bold blue]🔧 Modifying existing project...[/bold blue]\n")
            
            # Parse requirements
            requirements = self._parse_modification_requirements(args)
            integration_type = IntegrationType(args.integration_type)
            
            # Modify project
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) if self.console else self._dummy_progress() as progress:
                task = progress.add_task("Modifying project...", total=None)
                result = self.integration.modify_existing_project(requirements, integration_type)
                progress.update(task, completed=True)
            
            if result and result.success:
                self._display_modification_result(result)
                return 0
            else:
                if self.console:
                    self.console.print("[red]❌ Project modification failed[/red]")
                else:
                    print("❌ Project modification failed")
                return 1
                
        except Exception as e:
            logger.error(f"Error modifying project: {str(e)}")
            return 1
    
    def _handle_analyze(self, args) -> int:
        """Handle project analysis"""
        try:
            if self.console:
                self.console.print("[bold blue]🔍 Analyzing project structure...[/bold blue]\n")
            
            analysis = self.integration.analyze_project_structure()
            
            if args.format == "json":
                print(json.dumps(analysis, indent=2))
            elif args.format == "tree":
                self._display_analysis_tree(analysis)
            else:
                self._display_analysis_table(analysis)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error analyzing project: {str(e)}")
            return 1
    
    def _handle_interactive(self, args) -> int:
        """Handle interactive mode"""
        try:
            if not RICH_AVAILABLE:
                print("Interactive mode requires the 'rich' library. Please install it with: pip install rich")
                return 1
            
            self.console.print("[bold blue]🎯 Interactive Project Generator[/bold blue]\n")
            
            # Check if project exists
            project_path = Path(args.project_path)
            has_existing_project = (project_path / "package.json").exists()
            
            if has_existing_project:
                action = Prompt.ask(
                    "Existing project detected. What would you like to do?",
                    choices=["modify", "analyze", "new"],
                    default="modify"
                )
            else:
                action = "new"
            
            if action == "new":
                return self._interactive_generate()
            elif action == "modify":
                return self._interactive_modify()
            elif action == "analyze":
                return self._handle_analyze(args)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error in interactive mode: {str(e)}")
            return 1
    
    def _handle_status(self, args) -> int:
        """Handle status command"""
        try:
            status = self.integration.get_status_report()
            
            if self.console:
                self._display_status_report(status)
            else:
                print(json.dumps(status, indent=2))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return 1
    
    def _handle_list_components(self, args) -> int:
        """Handle list components command"""
        try:
            # This would use the ShadCN MCP server
            components = [
                "accordion", "alert", "alert-dialog", "aspect-ratio", "avatar",
                "badge", "breadcrumb", "button", "calendar", "card", "carousel",
                "chart", "checkbox", "collapsible", "combobox", "command",
                "context-menu", "data-table", "date-picker", "dialog",
                "drawer", "dropdown-menu", "form", "hover-card", "input",
                "input-otp", "label", "menubar", "navigation-menu",
                "pagination", "popover", "progress", "radio-group",
                "resizable", "scroll-area", "select", "separator", "sheet",
                "skeleton", "slider", "sonner", "switch", "table", "tabs",
                "textarea", "toast", "toggle", "toggle-group", "tooltip"
            ]
            
            if self.console:
                table = Table(title="Available ShadCN Components")
                table.add_column("Component", style="cyan")
                table.add_column("Category", style="yellow")
                
                for i, comp in enumerate(components):
                    category = "Form" if comp in ["input", "textarea", "select", "checkbox", "radio-group"] else "UI"
                    table.add_row(comp, category)
                
                self.console.print(table)
            else:
                print("Available ShadCN Components:")
                for comp in components:
                    print(f"  - {comp}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error listing components: {str(e)}")
            return 1
    
    def _handle_component_info(self, args) -> int:
        """Handle component info command"""
        try:
            component_name = args.component_name
            
            # This would use the ShadCN MCP server to get component info
            if self.console:
                self.console.print(f"[bold]Component: {component_name}[/bold]\n")
                self.console.print("This would show detailed component information from ShadCN MCP server.")
            else:
                print(f"Component: {component_name}")
                print("This would show detailed component information from ShadCN MCP server.")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting component info: {str(e)}")
            return 1
    
    def _handle_search_libraries(self, args) -> int:
        """Handle search libraries command"""
        try:
            query = args.query
            
            # This would use the Context7 MCP server
            if self.console:
                self.console.print(f"[bold]Searching for: {query}[/bold]\n")
                self.console.print("This would show library search results from Context7 MCP server.")
            else:
                print(f"Searching for: {query}")
                print("This would show library search results from Context7 MCP server.")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error searching libraries: {str(e)}")
            return 1
    
    def _handle_library_docs(self, args) -> int:
        """Handle library docs command"""
        try:
            library_name = args.library_name
            topic = args.topic
            
            # This would use the Context7 MCP server
            if self.console:
                self.console.print(f"[bold]Documentation for: {library_name}[/bold]")
                if topic:
                    self.console.print(f"[bold]Topic: {topic}[/bold]")
                self.console.print("\nThis would show library documentation from Context7 MCP server.")
            else:
                print(f"Documentation for: {library_name}")
                if topic:
                    print(f"Topic: {topic}")
                print("This would show library documentation from Context7 MCP server.")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting library docs: {str(e)}")
            return 1
    
    def _parse_requirements_from_args(self, args) -> ProjectRequirements:
        """Parse project requirements from command line arguments"""
        features = args.features.split(",") if args.features else []
        components = args.components.split(",") if args.components else []
        libraries = []  # Would be populated based on project type and features
        
        return ProjectRequirements(
            project_type=args.project_type,
            features=features,
            ui_components=components,
            libraries=libraries,
            styling_approach=args.styling,
            state_management=args.state_management,
            routing="routing" in features,
            authentication="authentication" in features
        )
    
    def _parse_modification_requirements(self, args) -> ProjectRequirements:
        """Parse modification requirements from command line arguments"""
        features = args.add_features.split(",") if args.add_features else []
        components = args.add_components.split(",") if args.add_components else []
        
        return ProjectRequirements(
            project_type="react",  # Default, would be detected from project
            features=features,
            ui_components=components,
            libraries=[]
        )
    
    def _interactive_generate(self) -> int:
        """Interactive project generation"""
        try:
            # Project type
            project_type = Prompt.ask(
                "What type of project would you like to create?",
                choices=["react", "nextjs", "vue", "angular"],
                default="react"
            )
            
            # Features
            self.console.print("\n[bold]Select features to include:[/bold]")
            available_features = ["routing", "authentication", "state-management", "testing", "api-integration"]
            selected_features = []
            
            for feature in available_features:
                if Confirm.ask(f"Include {feature}?", default=False):
                    selected_features.append(feature)
            
            # State management
            state_management = None
            if "state-management" in selected_features:
                state_management = Prompt.ask(
                    "Which state management library?",
                    choices=["zustand", "redux", "recoil", "context"],
                    default="zustand"
                )
            
            # Styling
            styling = Prompt.ask(
                "Which styling approach?",
                choices=["tailwind", "styled-components", "emotion", "css-modules"],
                default="tailwind"
            )
            
            # Components
            self.console.print("\n[bold]Select UI components to include:[/bold]")
            available_components = ["button", "card", "form", "table", "dialog", "navigation"]
            selected_components = []
            
            for component in available_components:
                if Confirm.ask(f"Include {component}?", default=True):
                    selected_components.append(component)
            
            # Strategy
            strategy = Prompt.ask(
                "Code generation strategy?",
                choices=["minimal", "comprehensive", "best_practices", "performance_optimized"],
                default="comprehensive"
            )
            
            # Create requirements
            requirements = ProjectRequirements(
                project_type=project_type,
                features=selected_features,
                ui_components=selected_components,
                libraries=[],
                styling_approach=styling,
                state_management=state_management,
                routing="routing" in selected_features,
                authentication="authentication" in selected_features
            )
            
            # Generate project
            self.console.print("\n[bold blue]🚀 Generating your project...[/bold blue]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Generating project files...", total=None)
                result = self.integration.generate_new_project(requirements, CodeGenerationStrategy(strategy))
                progress.update(task, completed=True)
            
            if result and result.success:
                self._display_generation_result(result)
                return 0
            else:
                self.console.print("[red]❌ Project generation failed[/red]")
                return 1
                
        except Exception as e:
            logger.error(f"Error in interactive generation: {str(e)}")
            return 1
    
    def _interactive_modify(self) -> int:
        """Interactive project modification"""
        try:
            # Analyze current project
            analysis = self.integration.analyze_project_structure()
            
            self.console.print(f"[bold]Current project type: {analysis['project_type']}[/bold]\n")
            
            # Modification type
            modification_type = Prompt.ask(
                "What would you like to do?",
                choices=["add-components", "add-features", "migrate-libraries"],
                default="add-components"
            )
            
            requirements = ProjectRequirements(
                project_type=analysis['project_type'],
                features=[],
                ui_components=[],
                libraries=[]
            )
            
            if modification_type == "add-components":
                # Component selection
                available_components = ["button", "card", "form", "table", "dialog", "navigation", "chart"]
                selected_components = []
                
                self.console.print("[bold]Select components to add:[/bold]")
                for component in available_components:
                    if Confirm.ask(f"Add {component}?", default=False):
                        selected_components.append(component)
                
                requirements.ui_components = selected_components
                integration_type = IntegrationType.COMPONENT_ADDITION
                
            elif modification_type == "add-features":
                # Feature selection
                available_features = ["routing", "authentication", "state-management", "testing"]
                selected_features = []
                
                self.console.print("[bold]Select features to add:[/bold]")
                for feature in available_features:
                    if Confirm.ask(f"Add {feature}?", default=False):
                        selected_features.append(feature)
                
                requirements.features = selected_features
                integration_type = IntegrationType.FEATURE_ENHANCEMENT
                
            else:  # migrate-libraries
                self.console.print("[yellow]Library migration is not fully implemented yet.[/yellow]")
                return 0
            
            # Modify project
            self.console.print("\n[bold blue]🔧 Modifying your project...[/bold blue]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Modifying project...", total=None)
                result = self.integration.modify_existing_project(requirements, integration_type)
                progress.update(task, completed=True)
            
            if result and result.success:
                self._display_modification_result(result)
                return 0
            else:
                self.console.print("[red]❌ Project modification failed[/red]")
                return 1
                
        except Exception as e:
            logger.error(f"Error in interactive modification: {str(e)}")
            return 1
    
    def _display_generation_result(self, result, output_dir: Optional[str] = None):
        """Display project generation result"""
        if self.console:
            self.console.print("[bold green]✅ Project generated successfully![/bold green]\n")
            self.integration.display_integration_result(result)
            
            if output_dir:
                self.console.print(f"\n[bold]Output directory: {output_dir}[/bold]")
        else:
            print("✅ Project generated successfully!")
            print(f"Generated {len(result.generated_files)} files")
    
    def _display_modification_result(self, result):
        """Display project modification result"""
        if self.console:
            self.console.print("[bold green]✅ Project modified successfully![/bold green]\n")
            self.integration.display_integration_result(result)
        else:
            print("✅ Project modified successfully!")
            print(f"Modified {len(result.generated_files)} files")
    
    def _display_analysis_table(self, analysis: Dict[str, Any]):
        """Display project analysis as table"""
        if self.console:
            table = Table(title="Project Analysis")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            for key, value in analysis.items():
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value) if value else "None"
                else:
                    value_str = str(value) if value else "None"
                table.add_row(key.replace("_", " ").title(), value_str)
            
            self.console.print(table)
        else:
            print("Project Analysis:")
            for key, value in analysis.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
    
    def _display_analysis_tree(self, analysis: Dict[str, Any]):
        """Display project analysis as tree"""
        if self.console:
            tree = Tree("[bold blue]Project Analysis[/bold blue]")
            
            for key, value in analysis.items():
                branch = tree.add(f"[cyan]{key.replace('_', ' ').title()}[/cyan]")
                if isinstance(value, list):
                    for item in value:
                        branch.add(f"[green]{item}[/green]")
                else:
                    branch.add(f"[green]{value}[/green]")
            
            self.console.print(tree)
        else:
            self._display_analysis_table(analysis)
    
    def _display_status_report(self, status: Dict[str, Any]):
        """Display status report"""
        if self.console:
            # Unified integration status
            unified_panel = Panel(
                f"""Project Path: {status['unified_integration']['project_path']}
Cache Size: {status['unified_integration']['generation_cache_size']}
Rich Available: {status['unified_integration']['rich_available']}
Status: {status['unified_integration']['integration_status']}""",
                title="[bold blue]Unified Integration Status[/bold blue]",
                expand=False
            )
            self.console.print(unified_panel)
            
            # Context7 status
            if 'context7_integration' in status:
                context7_panel = Panel(
                    json.dumps(status['context7_integration'], indent=2),
                    title="[bold yellow]Context7 Integration[/bold yellow]",
                    expand=False
                )
                self.console.print(context7_panel)
            
            # ShadCN status
            if 'shadcn_integration' in status:
                shadcn_panel = Panel(
                    json.dumps(status['shadcn_integration'], indent=2),
                    title="[bold green]ShadCN Integration[/bold green]",
                    expand=False
                )
                self.console.print(shadcn_panel)
        else:
            print("Status Report:")
            print(json.dumps(status, indent=2))
    
    def _dummy_progress(self):
        """Dummy progress context manager for when rich is not available"""
        class DummyProgress:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def add_task(self, description, total=None):
                print(f"Starting: {description}")
                return "dummy_task"
            def update(self, task_id, completed=None):
                if completed:
                    print("Completed!")
        
        return DummyProgress()

def main():
    """Main entry point"""
    cli = UnifiedMCPCLI()
    return cli.run()

if __name__ == "__main__":
    sys.exit(main())