#!/usr/bin/env python3
"""
Shadcn-UI Integration Module

This module provides integration with shadcn-ui components, including:
- Automatic health checks and status reporting
- Component management and installation
- UI generation with shadcn components
- Project setup with shadcn-ui
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

logger = logging.getLogger(__name__)

class ComponentStatus(Enum):
    """Status of shadcn-ui components"""
    AVAILABLE = "available"
    INSTALLED = "installed"
    OUTDATED = "outdated"
    ERROR = "error"
    UNKNOWN = "unknown"

class ProjectType(Enum):
    """Supported project types for shadcn-ui"""
    NEXT_JS = "next.js"
    VITE_REACT = "vite-react"
    REMIX = "remix"
    ASTRO = "astro"
    LARAVEL = "laravel"
    GATSBY = "gatsby"

@dataclass
class ComponentInfo:
    """Information about a shadcn-ui component"""
    name: str
    status: ComponentStatus
    description: str = ""
    dependencies: List[str] = None
    source_code: str = ""
    demo_code: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class HealthCheckResult:
    """Result of shadcn-ui health check"""
    is_healthy: bool
    project_type: Optional[ProjectType]
    components_installed: List[str]
    components_available: List[str]
    issues: List[str]
    recommendations: List[str]
    config_status: Dict[str, Any]

class ShadcnIntegration:
    """Main class for shadcn-ui integration"""
    
    def __init__(self, project_path: Optional[Path] = None, mcp_client=None):
        """
        Initialize shadcn-ui integration.
        
        Args:
            project_path: Path to the project directory
            mcp_client: MCP client for shadcn-ui server communication
        """
        self.project_path = project_path or Path.cwd()
        self.mcp_client = mcp_client
        self.console = Console() if RICH_AVAILABLE else None
        self.components_cache: Dict[str, ComponentInfo] = {}
        self.last_health_check: Optional[HealthCheckResult] = None
        
        # Available components from shadcn-ui
        self.available_components = [
            "accordion", "alert", "alert-dialog", "aspect-ratio", "avatar", "badge",
            "breadcrumb", "button", "calendar", "card", "carousel", "chart",
            "checkbox", "collapsible", "command", "context-menu", "dialog",
            "drawer", "dropdown-menu", "form", "hover-card", "input", "input-otp",
            "label", "menubar", "navigation-menu", "pagination", "popover",
            "progress", "radio-group", "resizable", "scroll-area", "select",
            "separator", "sheet", "sidebar", "skeleton", "slider", "sonner",
            "switch", "table", "tabs", "textarea", "toggle", "toggle-group", "tooltip"
        ]
    
    def perform_health_check(self) -> HealthCheckResult:
        """
        Perform comprehensive health check of shadcn-ui integration.
        
        Returns:
            HealthCheckResult with detailed status information
        """
        if self.console:
            self.console.print("\n[bold blue]Performing shadcn-ui Health Check...[/bold blue]")
        
        issues = []
        recommendations = []
        config_status = {}
        components_installed = []
        
        # Check project type
        project_type = self._detect_project_type()
        if not project_type:
            issues.append("Could not detect supported project type (Next.js, Vite, etc.)")
            recommendations.append("Initialize a supported framework project first")
        
        # Check for package.json
        package_json_path = self.project_path / "package.json"
        if not package_json_path.exists():
            issues.append("package.json not found")
            recommendations.append("Run 'npm init' to create package.json")
        else:
            config_status["package_json"] = "found"
            
            # Check for shadcn-ui dependencies
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    
                dependencies = package_data.get('dependencies', {})
                dev_dependencies = package_data.get('devDependencies', {})
                all_deps = {**dependencies, **dev_dependencies}
                
                # Check for common shadcn-ui dependencies
                required_deps = ['react', '@radix-ui/react-slot', 'class-variance-authority', 'clsx', 'tailwind-merge']
                missing_deps = [dep for dep in required_deps if dep not in all_deps]
                
                if missing_deps:
                    issues.append(f"Missing required dependencies: {', '.join(missing_deps)}")
                    recommendations.append("Install missing dependencies with npm/yarn")
                else:
                    config_status["dependencies"] = "complete"
                    
            except Exception as e:
                issues.append(f"Error reading package.json: {str(e)}")
        
        # Check for components.json (shadcn-ui config)
        components_json_path = self.project_path / "components.json"
        if not components_json_path.exists():
            issues.append("components.json not found")
            recommendations.append("Run 'npx shadcn-ui@latest init' to initialize shadcn-ui")
        else:
            config_status["components_json"] = "found"
            
            # Check installed components
            components_installed = self._get_installed_components()
        
        # Check for Tailwind CSS
        tailwind_config_path = self.project_path / "tailwind.config.js"
        if not tailwind_config_path.exists():
            tailwind_config_path = self.project_path / "tailwind.config.ts"
        
        if not tailwind_config_path.exists():
            issues.append("Tailwind CSS configuration not found")
            recommendations.append("Install and configure Tailwind CSS")
        else:
            config_status["tailwind"] = "configured"
        
        # Determine overall health
        is_healthy = len(issues) == 0
        
        result = HealthCheckResult(
            is_healthy=is_healthy,
            project_type=project_type,
            components_installed=components_installed,
            components_available=self.available_components,
            issues=issues,
            recommendations=recommendations,
            config_status=config_status
        )
        
        self.last_health_check = result
        self._display_health_check_results(result)
        
        return result
    
    def _detect_project_type(self) -> Optional[ProjectType]:
        """Detect the type of project (Next.js, Vite, etc.)"""
        package_json_path = self.project_path / "package.json"
        
        if not package_json_path.exists():
            return None
        
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            dependencies = package_data.get('dependencies', {})
            dev_dependencies = package_data.get('devDependencies', {})
            all_deps = {**dependencies, **dev_dependencies}
            
            # Check for framework-specific dependencies
            if 'next' in all_deps:
                return ProjectType.NEXT_JS
            elif 'vite' in all_deps and 'react' in all_deps:
                return ProjectType.VITE_REACT
            elif '@remix-run/react' in all_deps:
                return ProjectType.REMIX
            elif 'astro' in all_deps:
                return ProjectType.ASTRO
            elif 'laravel-mix' in all_deps or 'laravel-vite-plugin' in all_deps:
                return ProjectType.LARAVEL
            elif 'gatsby' in all_deps:
                return ProjectType.GATSBY
                
        except Exception as e:
            logger.warning(f"Error detecting project type: {e}")
        
        return None
    
    def _get_installed_components(self) -> List[str]:
        """Get list of installed shadcn-ui components"""
        components_dir = self.project_path / "components" / "ui"
        if not components_dir.exists():
            return []
        
        installed = []
        for component_file in components_dir.glob("*.tsx"):
            component_name = component_file.stem
            if component_name in self.available_components:
                installed.append(component_name)
        
        return installed
    
    def _display_health_check_results(self, result: HealthCheckResult) -> None:
        """Display health check results using rich formatting"""
        if not self.console:
            return
        
        # Create status panel
        status_text = "[bold green]✅ Healthy[/bold green]" if result.is_healthy else "[bold red]❌ Issues Found[/bold red]"
        
        panel_content = []
        panel_content.append(f"Status: {status_text}")
        
        if result.project_type:
            panel_content.append(f"Project Type: [cyan]{result.project_type.value}[/cyan]")
        
        panel_content.append(f"Components Installed: [yellow]{len(result.components_installed)}[/yellow]")
        panel_content.append(f"Components Available: [blue]{len(result.components_available)}[/blue]")
        
        self.console.print(Panel("\n".join(panel_content), title="[bold]shadcn-ui Health Check[/bold]"))
        
        # Display issues if any
        if result.issues:
            self.console.print("\n[bold red]Issues Found:[/bold red]")
            for issue in result.issues:
                self.console.print(f"  • {issue}")
        
        # Display recommendations
        if result.recommendations:
            self.console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in result.recommendations:
                self.console.print(f"  • {rec}")
        
        # Display installed components
        if result.components_installed:
            self.console.print("\n[bold green]Installed Components:[/bold green]")
            for component in result.components_installed:
                self.console.print(f"  • {component}")
    
    def get_component_info(self, component_name: str) -> Optional[ComponentInfo]:
        """Get detailed information about a specific component"""
        if component_name not in self.available_components:
            return None
        
        # Check cache first
        if component_name in self.components_cache:
            return self.components_cache[component_name]
        
        # Determine status
        installed_components = self._get_installed_components()
        status = ComponentStatus.INSTALLED if component_name in installed_components else ComponentStatus.AVAILABLE
        
        # Create component info
        component_info = ComponentInfo(
            name=component_name,
            status=status,
            description=f"shadcn-ui {component_name} component"
        )
        
        # Cache the result
        self.components_cache[component_name] = component_info
        
        return component_info
    
    def generate_component_usage_guide(self, component_name: str) -> str:
        """Generate usage guide for a specific component"""
        if component_name not in self.available_components:
            return f"Component '{component_name}' not found in shadcn-ui library."
        
        guide = f"""# {component_name.title()} Component Usage Guide

## Installation
```bash
npx shadcn-ui@latest add {component_name}
```

## Basic Usage
```tsx
import {{ {component_name.title().replace('-', '')} }} from "@/components/ui/{component_name}"

export default function Example() {{
  return (
    <{component_name.title().replace('-', '')}>
      {{/* Your content here */}}
    </{component_name.title().replace('-', '')}>
  )
}}
```

## Notes
- Make sure you have initialized shadcn-ui in your project
- This component requires Tailwind CSS to be configured
- Check the official documentation for advanced usage patterns
"""
        
        return guide
    
    def suggest_components_for_feature(self, feature_description: str) -> List[str]:
        """Suggest relevant shadcn-ui components for a given feature"""
        feature_lower = feature_description.lower()
        suggestions = []
        
        # Component mapping based on common use cases
        component_mappings = {
            'form': ['form', 'input', 'button', 'label', 'textarea', 'select', 'checkbox', 'radio-group'],
            'navigation': ['navigation-menu', 'breadcrumb', 'menubar', 'sidebar'],
            'data': ['table', 'pagination', 'chart'],
            'feedback': ['alert', 'progress', 'skeleton', 'sonner'],
            'overlay': ['dialog', 'sheet', 'popover', 'tooltip', 'hover-card'],
            'layout': ['card', 'separator', 'aspect-ratio', 'resizable', 'scroll-area'],
            'input': ['input', 'textarea', 'select', 'checkbox', 'radio-group', 'switch', 'slider'],
            'display': ['avatar', 'badge', 'calendar', 'carousel'],
            'interaction': ['button', 'toggle', 'toggle-group', 'collapsible', 'accordion']
        }
        
        for category, components in component_mappings.items():
            if category in feature_lower:
                suggestions.extend(components)
        
        # Remove duplicates and filter available components
        suggestions = list(set(suggestions))
        suggestions = [comp for comp in suggestions if comp in self.available_components]
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        if not self.last_health_check:
            self.perform_health_check()
        
        return {
            "timestamp": str(Path().cwd()),
            "health_check": {
                "is_healthy": self.last_health_check.is_healthy,
                "project_type": self.last_health_check.project_type.value if self.last_health_check.project_type else None,
                "components_installed": len(self.last_health_check.components_installed),
                "components_available": len(self.last_health_check.components_available),
                "issues_count": len(self.last_health_check.issues)
            },
            "components": {
                "installed": self.last_health_check.components_installed,
                "available": self.available_components
            },
            "recommendations": self.last_health_check.recommendations
        }

# Global instance
_shadcn_integration: Optional[ShadcnIntegration] = None

def get_shadcn_integration(project_path: Optional[Path] = None, mcp_client=None) -> ShadcnIntegration:
    """Get or create global shadcn integration instance"""
    global _shadcn_integration
    if _shadcn_integration is None:
        _shadcn_integration = ShadcnIntegration(project_path, mcp_client)
    return _shadcn_integration

def initialize_shadcn_integration(project_path: Optional[Path] = None, mcp_client=None) -> ShadcnIntegration:
    """Initialize shadcn integration"""
    global _shadcn_integration
    _shadcn_integration = ShadcnIntegration(project_path, mcp_client)
    return _shadcn_integration

def perform_shadcn_health_check(project_path: Optional[Path] = None) -> HealthCheckResult:
    """Perform shadcn-ui health check"""
    integration = get_shadcn_integration(project_path)
    return integration.perform_health_check()