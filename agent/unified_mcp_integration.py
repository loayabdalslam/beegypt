#!/usr/bin/env python3
"""
Unified MCP Integration Module

Combines Context7 and ShadCN MCP services to provide:
- Intelligent code generation with documentation context
- UI component integration with best practices
- Project scaffolding with proper library usage
- Code modification suggestions for existing projects
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from .context7_integration import (
    Context7Integration, LibraryInfo, DocumentationResult, CodeSuggestion,
    initialize_context7_integration, get_context7_integration
)
from .shadcn_integration import (
    ShadcnIntegration, ComponentInfo, ProjectType,
    initialize_shadcn_integration, get_shadcn_integration
)

logger = logging.getLogger(__name__)

class IntegrationType(Enum):
    """Types of integration scenarios"""
    NEW_PROJECT = "new_project"
    EXISTING_PROJECT = "existing_project"
    COMPONENT_ADDITION = "component_addition"
    LIBRARY_MIGRATION = "library_migration"
    FEATURE_ENHANCEMENT = "feature_enhancement"

class CodeGenerationStrategy(Enum):
    """Strategies for code generation"""
    MINIMAL = "minimal"  # Basic implementation
    COMPREHENSIVE = "comprehensive"  # Full-featured implementation
    BEST_PRACTICES = "best_practices"  # Following all best practices
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # Optimized for performance

@dataclass
class ProjectRequirements:
    """Requirements for project generation or modification"""
    project_type: str
    features: List[str]
    ui_components: List[str]
    libraries: List[str]
    styling_approach: str = "tailwind"
    state_management: Optional[str] = None
    routing: bool = False
    authentication: bool = False
    database: Optional[str] = None
    testing: bool = False
    deployment_target: Optional[str] = None

@dataclass
class GeneratedCode:
    """Generated code with metadata"""
    file_path: str
    content: str
    language: str
    description: str
    dependencies: List[str]
    imports: List[str]
    exports: List[str]
    component_usage: List[str] = field(default_factory=list)
    best_practices_applied: List[str] = field(default_factory=list)
    performance_notes: List[str] = field(default_factory=list)

@dataclass
class IntegrationResult:
    """Result of unified MCP integration"""
    success: bool
    generated_files: List[GeneratedCode]
    component_suggestions: List[ComponentInfo]
    library_recommendations: List[LibraryInfo]
    setup_instructions: List[str]
    best_practices: List[str]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class UnifiedMCPIntegration:
    """Unified integration of Context7 and ShadCN MCP services"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.console = Console() if RICH_AVAILABLE else None
        
        # Initialize individual integrations
        self.context7 = initialize_context7_integration(project_path)
        self.shadcn = initialize_shadcn_integration(project_path)
        
        # Cache for generated content
        self.generation_cache: Dict[str, IntegrationResult] = {}
        
        logger.info(f"Unified MCP integration initialized for project: {project_path}")
    
    def analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze existing project structure to determine integration approach"""
        analysis = {
            "project_type": "unknown",
            "existing_libraries": [],
            "ui_framework": None,
            "has_components": False,
            "package_manager": None,
            "build_tool": None,
            "styling_approach": None,
            "state_management": None,
            "routing_library": None
        }
        
        try:
            # Check for package.json
            package_json = self.project_path / "package.json"
            if package_json.exists():
                with open(package_json, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                analysis["existing_libraries"] = list(dependencies.keys())
                analysis["package_manager"] = "npm"  # Could detect yarn/pnpm too
                
                # Detect project type and frameworks
                if "next" in dependencies:
                    analysis["project_type"] = "nextjs"
                    analysis["ui_framework"] = "react"
                elif "react" in dependencies:
                    analysis["project_type"] = "react"
                    analysis["ui_framework"] = "react"
                elif "vue" in dependencies:
                    analysis["project_type"] = "vue"
                    analysis["ui_framework"] = "vue"
                elif "@angular/core" in dependencies:
                    analysis["project_type"] = "angular"
                    analysis["ui_framework"] = "angular"
                
                # Detect styling approach
                if "tailwindcss" in dependencies:
                    analysis["styling_approach"] = "tailwind"
                elif "styled-components" in dependencies:
                    analysis["styling_approach"] = "styled-components"
                elif "@emotion/react" in dependencies:
                    analysis["styling_approach"] = "emotion"
                
                # Detect state management
                if "redux" in dependencies or "@reduxjs/toolkit" in dependencies:
                    analysis["state_management"] = "redux"
                elif "zustand" in dependencies:
                    analysis["state_management"] = "zustand"
                elif "recoil" in dependencies:
                    analysis["state_management"] = "recoil"
                
                # Detect routing
                if "react-router-dom" in dependencies:
                    analysis["routing_library"] = "react-router"
                elif "@reach/router" in dependencies:
                    analysis["routing_library"] = "reach-router"
            
            # Check for components directory
            components_dir = self.project_path / "components"
            src_components_dir = self.project_path / "src" / "components"
            if components_dir.exists() or src_components_dir.exists():
                analysis["has_components"] = True
            
            # Check for build tools
            if (self.project_path / "vite.config.js").exists() or (self.project_path / "vite.config.ts").exists():
                analysis["build_tool"] = "vite"
            elif (self.project_path / "webpack.config.js").exists():
                analysis["build_tool"] = "webpack"
            elif (self.project_path / "next.config.js").exists():
                analysis["build_tool"] = "next"
            
            logger.info(f"Project analysis completed: {analysis['project_type']} project detected")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing project structure: {str(e)}")
            return analysis
    
    def generate_new_project(self, requirements: ProjectRequirements, strategy: CodeGenerationStrategy = CodeGenerationStrategy.COMPREHENSIVE) -> IntegrationResult:
        """Generate a complete new project with Context7 and ShadCN integration"""
        try:
            logger.info(f"Generating new {requirements.project_type} project with {strategy.value} strategy")
            
            result = IntegrationResult(
                success=True,
                generated_files=[],
                component_suggestions=[],
                library_recommendations=[],
                setup_instructions=[],
                best_practices=[]
            )
            
            # Get library recommendations from Context7
            library_suggestions = self.context7.suggest_libraries_for_project(
                requirements.project_type, requirements.features
            )
            result.library_recommendations = library_suggestions
            
            # Get component suggestions from ShadCN
            for feature in requirements.features:
                components = self.shadcn.suggest_components_for_feature(feature)
                for comp_name in components:
                    comp_info = ComponentInfo(
                        name=comp_name,
                        description=f"Component for {feature}",
                        category="ui",
                        dependencies=[],
                        usage_example=""
                    )
                    result.component_suggestions.append(comp_info)
            
            # Generate project structure files
            generated_files = self._generate_project_files(requirements, strategy, library_suggestions)
            result.generated_files = generated_files
            
            # Generate setup instructions
            result.setup_instructions = self._generate_setup_instructions(requirements, library_suggestions)
            
            # Generate best practices
            result.best_practices = self._generate_best_practices(requirements, strategy)
            
            logger.info(f"Successfully generated new project with {len(generated_files)} files")
            return result
            
        except Exception as e:
            logger.error(f"Error generating new project: {str(e)}")
            return IntegrationResult(
                success=False,
                generated_files=[],
                component_suggestions=[],
                library_recommendations=[],
                setup_instructions=[],
                best_practices=[],
                errors=[str(e)]
            )
    
    def modify_existing_project(self, requirements: ProjectRequirements, integration_type: IntegrationType = IntegrationType.FEATURE_ENHANCEMENT) -> IntegrationResult:
        """Modify an existing project with new features or components"""
        try:
            logger.info(f"Modifying existing project for {integration_type.value}")
            
            # Analyze current project
            project_analysis = self.analyze_project_structure()
            
            result = IntegrationResult(
                success=True,
                generated_files=[],
                component_suggestions=[],
                library_recommendations=[],
                setup_instructions=[],
                best_practices=[]
            )
            
            # Generate modifications based on integration type
            if integration_type == IntegrationType.COMPONENT_ADDITION:
                result = self._add_components_to_project(requirements, project_analysis)
            elif integration_type == IntegrationType.FEATURE_ENHANCEMENT:
                result = self._enhance_project_features(requirements, project_analysis)
            elif integration_type == IntegrationType.LIBRARY_MIGRATION:
                result = self._migrate_project_libraries(requirements, project_analysis)
            
            logger.info(f"Successfully modified project with {len(result.generated_files)} changes")
            return result
            
        except Exception as e:
            logger.error(f"Error modifying existing project: {str(e)}")
            return IntegrationResult(
                success=False,
                generated_files=[],
                component_suggestions=[],
                library_recommendations=[],
                setup_instructions=[],
                best_practices=[],
                errors=[str(e)]
            )
    
    def _generate_project_files(self, requirements: ProjectRequirements, strategy: CodeGenerationStrategy, libraries: List[LibraryInfo]) -> List[GeneratedCode]:
        """Generate project files based on requirements"""
        files = []
        
        try:
            # Generate package.json
            package_json = self._generate_package_json(requirements, libraries)
            files.append(package_json)
            
            # Generate main application file
            if requirements.project_type.lower() in ["react", "nextjs"]:
                app_file = self._generate_react_app(requirements, strategy)
                files.append(app_file)
                
                # Generate components
                for component in requirements.ui_components:
                    comp_file = self._generate_component_file(component, requirements, strategy)
                    if comp_file:
                        files.append(comp_file)
            
            # Generate configuration files
            config_files = self._generate_config_files(requirements)
            files.extend(config_files)
            
            # Generate README
            readme = self._generate_readme(requirements, libraries)
            files.append(readme)
            
            return files
            
        except Exception as e:
            logger.error(f"Error generating project files: {str(e)}")
            return []
    
    def _generate_package_json(self, requirements: ProjectRequirements, libraries: List[LibraryInfo]) -> GeneratedCode:
        """Generate package.json with proper dependencies"""
        dependencies = {}
        dev_dependencies = {}
        
        # Add base dependencies based on project type
        if requirements.project_type.lower() == "react":
            dependencies["react"] = "^18.2.0"
            dependencies["react-dom"] = "^18.2.0"
            dev_dependencies["@types/react"] = "^18.2.0"
            dev_dependencies["@types/react-dom"] = "^18.2.0"
        elif requirements.project_type.lower() == "nextjs":
            dependencies["next"] = "^14.0.0"
            dependencies["react"] = "^18.2.0"
            dependencies["react-dom"] = "^18.2.0"
        
        # Add styling dependencies
        if requirements.styling_approach == "tailwind":
            dependencies["tailwindcss"] = "^3.4.0"
            dev_dependencies["autoprefixer"] = "^10.4.0"
            dev_dependencies["postcss"] = "^8.4.0"
        
        # Add ShadCN UI dependencies
        dependencies["@radix-ui/react-slot"] = "^1.0.2"
        dependencies["class-variance-authority"] = "^0.7.0"
        dependencies["clsx"] = "^2.0.0"
        dependencies["tailwind-merge"] = "^2.0.0"
        
        # Add feature-specific dependencies
        if "routing" in requirements.features:
            if requirements.project_type.lower() == "react":
                dependencies["react-router-dom"] = "^6.8.0"
        
        if requirements.state_management:
            if requirements.state_management == "zustand":
                dependencies["zustand"] = "^4.4.0"
            elif requirements.state_management == "redux":
                dependencies["@reduxjs/toolkit"] = "^1.9.0"
                dependencies["react-redux"] = "^8.1.0"
        
        package_content = {
            "name": "generated-project",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev" if requirements.project_type.lower() == "nextjs" else "vite",
                "build": "next build" if requirements.project_type.lower() == "nextjs" else "vite build",
                "start": "next start" if requirements.project_type.lower() == "nextjs" else "vite preview",
                "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
            },
            "dependencies": dependencies,
            "devDependencies": dev_dependencies
        }
        
        return GeneratedCode(
            file_path="package.json",
            content=json.dumps(package_content, indent=2),
            language="json",
            description="Package configuration with dependencies",
            dependencies=list(dependencies.keys()),
            imports=[],
            exports=[]
        )
    
    def _generate_react_app(self, requirements: ProjectRequirements, strategy: CodeGenerationStrategy) -> GeneratedCode:
        """Generate main React application file"""
        imports = [
            "import React from 'react';",
            "import './App.css';"
        ]
        
        # Add routing imports if needed
        if "routing" in requirements.features:
            imports.extend([
                "import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';",
                "import { Home } from './components/Home';",
                "import { About } from './components/About';"
            ])
        
        # Add state management imports
        if requirements.state_management == "zustand":
            imports.append("import { useStore } from './store/useStore';")
        
        # Generate component imports
        for component in requirements.ui_components:
            component_name = component.replace("-", "").title()
            imports.append(f"import {{ {component_name} }} from './components/{component_name}';")
        
        # Generate app component
        app_content = []
        
        if "routing" in requirements.features:
            app_content = [
                "function App() {",
                "  return (",
                "    <Router>",
                "      <div className='min-h-screen bg-background'>",
                "        <Routes>",
                "          <Route path='/' element={<Home />} />",
                "          <Route path='/about' element={<About />} />",
                "        </Routes>",
                "      </div>",
                "    </Router>",
                "  );",
                "}"
            ]
        else:
            app_content = [
                "function App() {",
                "  return (",
                "    <div className='min-h-screen bg-background p-8'>",
                "      <div className='max-w-4xl mx-auto'>",
                "        <h1 className='text-4xl font-bold mb-8'>Welcome to Your App</h1>"
            ]
            
            # Add components to the app
            for component in requirements.ui_components:
                component_name = component.replace("-", "").title()
                app_content.append(f"        <{component_name} />")
            
            app_content.extend([
                "      </div>",
                "    </div>",
                "  );",
                "}"
            ])
        
        app_content.append("\nexport default App;")
        
        full_content = "\n".join(imports) + "\n\n" + "\n".join(app_content)
        
        return GeneratedCode(
            file_path="src/App.tsx" if requirements.project_type.lower() == "react" else "app/page.tsx",
            content=full_content,
            language="typescript",
            description="Main application component",
            dependencies=["react"],
            imports=imports,
            exports=["App"],
            component_usage=requirements.ui_components,
            best_practices_applied=[
                "TypeScript for type safety",
                "Tailwind CSS for styling",
                "Component composition",
                "Responsive design patterns"
            ]
        )
    
    def _generate_component_file(self, component_name: str, requirements: ProjectRequirements, strategy: CodeGenerationStrategy) -> Optional[GeneratedCode]:
        """Generate a component file with ShadCN integration"""
        try:
            # Get component info from ShadCN
            # This would normally use the MCP server
            
            component_title = component_name.replace("-", "").title()
            
            # Generate basic component structure
            imports = [
                "import React from 'react';",
                "import { cn } from '@/lib/utils';"
            ]
            
            # Add ShadCN component imports based on component type
            if "button" in component_name.lower():
                imports.append("import { Button } from '@/components/ui/button';")
            elif "card" in component_name.lower():
                imports.extend([
                    "import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';"
                ])
            elif "form" in component_name.lower():
                imports.extend([
                    "import { Button } from '@/components/ui/button';",
                    "import { Input } from '@/components/ui/input';",
                    "import { Label } from '@/components/ui/label';"
                ])
            
            # Generate component interface
            interface_content = [
                f"interface {component_title}Props {{",
                "  className?: string;",
                "}"
            ]
            
            # Generate component implementation
            component_content = [
                f"export function {component_title}({{ className, ...props }}: {component_title}Props) {{",
                "  return (",
                f"    <div className={{cn('p-4', className)}} {{...props}}>",
                f"      <h2 className='text-2xl font-semibold mb-4'>{component_title}</h2>"
            ]
            
            # Add component-specific content
            if "button" in component_name.lower():
                component_content.extend([
                    "      <Button variant='default' size='default'>",
                    "        Click me",
                    "      </Button>"
                ])
            elif "card" in component_name.lower():
                component_content.extend([
                    "      <Card>",
                    "        <CardHeader>",
                    "          <CardTitle>Card Title</CardTitle>",
                    "          <CardDescription>Card description goes here.</CardDescription>",
                    "        </CardHeader>",
                    "        <CardContent>",
                    "          <p>Card content goes here.</p>",
                    "        </CardContent>",
                    "      </Card>"
                ])
            elif "form" in component_name.lower():
                component_content.extend([
                    "      <form className='space-y-4'>",
                    "        <div>",
                    "          <Label htmlFor='email'>Email</Label>",
                    "          <Input id='email' type='email' placeholder='Enter your email' />",
                    "        </div>",
                    "        <Button type='submit'>Submit</Button>",
                    "      </form>"
                ])
            else:
                component_content.append(f"      <p>This is the {component_title} component.</p>")
            
            component_content.extend([
                "    </div>",
                "  );",
                "}"
            ])
            
            full_content = "\n".join(imports) + "\n\n" + "\n".join(interface_content) + "\n\n" + "\n".join(component_content)
            
            return GeneratedCode(
                file_path=f"src/components/{component_title}.tsx",
                content=full_content,
                language="typescript",
                description=f"{component_title} component with ShadCN UI integration",
                dependencies=["react", "@radix-ui/react-slot"],
                imports=imports,
                exports=[component_title],
                component_usage=[component_name],
                best_practices_applied=[
                    "TypeScript interfaces for props",
                    "ShadCN UI components",
                    "Tailwind CSS classes",
                    "Accessible component structure",
                    "Proper prop spreading"
                ]
            )
            
        except Exception as e:
            logger.error(f"Error generating component {component_name}: {str(e)}")
            return None
    
    def _generate_config_files(self, requirements: ProjectRequirements) -> List[GeneratedCode]:
        """Generate configuration files"""
        config_files = []
        
        # Generate Tailwind config
        if requirements.styling_approach == "tailwind":
            tailwind_config = GeneratedCode(
                file_path="tailwind.config.js",
                content="""/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}""",
                language="javascript",
                description="Tailwind CSS configuration with ShadCN theme",
                dependencies=["tailwindcss"],
                imports=[],
                exports=[]
            )
            config_files.append(tailwind_config)
        
        # Generate TypeScript config
        tsconfig = GeneratedCode(
            file_path="tsconfig.json",
            content="""{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}""",
            language="json",
            description="TypeScript configuration with path mapping",
            dependencies=[],
            imports=[],
            exports=[]
        )
        config_files.append(tsconfig)
        
        return config_files
    
    def _generate_readme(self, requirements: ProjectRequirements, libraries: List[LibraryInfo]) -> GeneratedCode:
        """Generate comprehensive README"""
        readme_content = f"""# Generated {requirements.project_type.title()} Project

This project was generated using the BEE EGYPT AI Code Agent with Context7 and ShadCN integration.

## Features

{chr(10).join(f"- {feature.title()}" for feature in requirements.features)}

## UI Components

{chr(10).join(f"- {component.title()}" for component in requirements.ui_components)}

## Libraries Used

{chr(10).join(f"- **{lib.name}**: {lib.description}" for lib in libraries)}

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

## Project Structure

```
src/
├── components/          # React components
├── lib/                # Utility functions
├── styles/             # CSS styles
└── App.tsx             # Main application
```

## ShadCN UI Integration

This project uses ShadCN UI components for consistent and accessible design. Components are located in `src/components/ui/`.

## Best Practices Applied

- TypeScript for type safety
- Tailwind CSS for styling
- Component composition patterns
- Accessible component structure
- Responsive design
- Performance optimizations

## Development

### Adding New Components

```bash
npx shadcn-ui@latest add [component-name]
```

### Code Style

This project follows React and TypeScript best practices:
- Use functional components with hooks
- Implement proper TypeScript interfaces
- Follow naming conventions
- Use Tailwind CSS classes consistently

## Deployment

Build the project for production:

```bash
npm run build
```

The build artifacts will be stored in the `dist/` directory.

## Generated by BEE EGYPT

This project was automatically generated using advanced AI code generation with:
- Context7 MCP for documentation and best practices
- ShadCN MCP for UI component integration
- Intelligent project structure analysis
- Performance and accessibility optimizations
"""
        
        return GeneratedCode(
            file_path="README.md",
            content=readme_content,
            language="markdown",
            description="Comprehensive project documentation",
            dependencies=[],
            imports=[],
            exports=[]
        )
    
    def _generate_setup_instructions(self, requirements: ProjectRequirements, libraries: List[LibraryInfo]) -> List[str]:
        """Generate setup instructions"""
        instructions = [
            "1. Install Node.js (version 18 or higher)",
            "2. Run 'npm install' to install dependencies",
            "3. Run 'npm run dev' to start the development server"
        ]
        
        if requirements.styling_approach == "tailwind":
            instructions.append("4. Tailwind CSS is pre-configured with ShadCN theme")
        
        if "routing" in requirements.features:
            instructions.append("5. React Router is configured for client-side routing")
        
        if requirements.state_management:
            instructions.append(f"6. {requirements.state_management.title()} is set up for state management")
        
        instructions.extend([
            "7. ShadCN UI components are available in src/components/ui/",
            "8. Add new ShadCN components with: npx shadcn-ui@latest add [component]",
            "9. Customize theme in tailwind.config.js",
            "10. Build for production with: npm run build"
        ])
        
        return instructions
    
    def _generate_best_practices(self, requirements: ProjectRequirements, strategy: CodeGenerationStrategy) -> List[str]:
        """Generate best practices recommendations"""
        practices = [
            "Use TypeScript for type safety and better developer experience",
            "Implement proper error boundaries for React components",
            "Use React.memo() for performance optimization when needed",
            "Follow the single responsibility principle for components",
            "Use custom hooks to extract and reuse stateful logic",
            "Implement proper loading and error states",
            "Use semantic HTML elements for accessibility",
            "Optimize images and assets for web performance",
            "Implement proper SEO meta tags",
            "Use environment variables for configuration"
        ]
        
        if strategy == CodeGenerationStrategy.PERFORMANCE_OPTIMIZED:
            practices.extend([
                "Implement code splitting with React.lazy()",
                "Use React.Suspense for loading states",
                "Optimize bundle size with tree shaking",
                "Implement virtual scrolling for large lists",
                "Use Web Workers for heavy computations"
            ])
        
        if requirements.styling_approach == "tailwind":
            practices.extend([
                "Use Tailwind's utility classes consistently",
                "Create custom components for repeated patterns",
                "Use Tailwind's responsive design utilities",
                "Leverage Tailwind's dark mode support"
            ])
        
        return practices
    
    def _add_components_to_project(self, requirements: ProjectRequirements, analysis: Dict[str, Any]) -> IntegrationResult:
        """Add new components to existing project"""
        result = IntegrationResult(
            success=True,
            generated_files=[],
            component_suggestions=[],
            library_recommendations=[],
            setup_instructions=[],
            best_practices=[]
        )
        
        # Generate new component files
        for component in requirements.ui_components:
            comp_file = self._generate_component_file(component, requirements, CodeGenerationStrategy.BEST_PRACTICES)
            if comp_file:
                result.generated_files.append(comp_file)
        
        # Update existing files if needed
        if analysis["project_type"] == "react" and (self.project_path / "src" / "App.tsx").exists():
            # Generate updated App.tsx with new components
            updated_app = self._update_app_with_components(requirements.ui_components, analysis)
            if updated_app:
                result.generated_files.append(updated_app)
        
        result.setup_instructions = [
            "1. Add the generated components to your project",
            "2. Import and use the components in your application",
            "3. Install any missing ShadCN components: npx shadcn-ui@latest add [component]",
            "4. Update your imports and component usage as needed"
        ]
        
        return result
    
    def _enhance_project_features(self, requirements: ProjectRequirements, analysis: Dict[str, Any]) -> IntegrationResult:
        """Enhance existing project with new features"""
        result = IntegrationResult(
            success=True,
            generated_files=[],
            component_suggestions=[],
            library_recommendations=[],
            setup_instructions=[],
            best_practices=[]
        )
        
        # Add routing if requested and not present
        if "routing" in requirements.features and not analysis["routing_library"]:
            routing_files = self._add_routing_to_project(analysis)
            result.generated_files.extend(routing_files)
        
        # Add state management if requested and not present
        if requirements.state_management and not analysis["state_management"]:
            state_files = self._add_state_management(requirements.state_management)
            result.generated_files.extend(state_files)
        
        # Add authentication if requested
        if requirements.authentication:
            auth_files = self._add_authentication_system()
            result.generated_files.extend(auth_files)
        
        return result
    
    def _migrate_project_libraries(self, requirements: ProjectRequirements, analysis: Dict[str, Any]) -> IntegrationResult:
        """Migrate project to use different libraries"""
        result = IntegrationResult(
            success=True,
            generated_files=[],
            component_suggestions=[],
            library_recommendations=[],
            setup_instructions=[],
            best_practices=[],
            warnings=["Library migration requires careful testing of all functionality"]
        )
        
        # This would implement migration logic
        # For now, we'll provide guidance
        result.setup_instructions = [
            "1. Review current library usage in your codebase",
            "2. Install new libraries: npm install [new-libraries]",
            "3. Update imports and component usage",
            "4. Test all functionality thoroughly",
            "5. Remove old dependencies: npm uninstall [old-libraries]"
        ]
        
        return result
    
    def _update_app_with_components(self, components: List[str], analysis: Dict[str, Any]) -> Optional[GeneratedCode]:
        """Update App.tsx to include new components"""
        try:
            # Read existing App.tsx
            app_path = self.project_path / "src" / "App.tsx"
            if not app_path.exists():
                return None
            
            with open(app_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Add imports for new components
            new_imports = []
            for component in components:
                component_name = component.replace("-", "").title()
                import_line = f"import {{ {component_name} }} from './components/{component_name}';"
                if import_line not in existing_content:
                    new_imports.append(import_line)
            
            # Insert new imports after existing imports
            lines = existing_content.split('\n')
            import_end_index = 0
            for i, line in enumerate(lines):
                if line.startswith('import '):
                    import_end_index = i + 1
            
            # Insert new imports
            for import_line in reversed(new_imports):
                lines.insert(import_end_index, import_line)
            
            # Add components to JSX (simple approach - add before closing div)
            for i in range(len(lines) - 1, -1, -1):
                if '</div>' in lines[i] and 'return' not in lines[i]:
                    for component in reversed(components):
                        component_name = component.replace("-", "").title()
                        lines.insert(i, f"        <{component_name} />")
                    break
            
            updated_content = '\n'.join(lines)
            
            return GeneratedCode(
                file_path="src/App.tsx",
                content=updated_content,
                language="typescript",
                description="Updated App component with new components",
                dependencies=["react"],
                imports=new_imports,
                exports=["App"],
                component_usage=components
            )
            
        except Exception as e:
            logger.error(f"Error updating App.tsx: {str(e)}")
            return None
    
    def _add_routing_to_project(self, analysis: Dict[str, Any]) -> List[GeneratedCode]:
        """Add routing system to project"""
        files = []
        
        # Generate route components
        home_component = GeneratedCode(
            file_path="src/components/Home.tsx",
            content="""import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function Home() {
  return (
    <div className='container mx-auto py-8'>
      <Card>
        <CardHeader>
          <CardTitle>Welcome Home</CardTitle>
          <CardDescription>This is the home page of your application.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className='mb-4'>Get started by editing this component.</p>
          <Button>Get Started</Button>
        </CardContent>
      </Card>
    </div>
  );
}""",
            language="typescript",
            description="Home page component",
            dependencies=["react"],
            imports=["import React from 'react';"],
            exports=["Home"]
        )
        files.append(home_component)
        
        about_component = GeneratedCode(
            file_path="src/components/About.tsx",
            content="""import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function About() {
  return (
    <div className='container mx-auto py-8'>
      <Card>
        <CardHeader>
          <CardTitle>About Us</CardTitle>
          <CardDescription>Learn more about this application.</CardDescription>
        </CardHeader>
        <CardContent>
          <p>This application was generated using BEE EGYPT AI Code Agent.</p>
        </CardContent>
      </Card>
    </div>
  );
}""",
            language="typescript",
            description="About page component",
            dependencies=["react"],
            imports=["import React from 'react';"],
            exports=["About"]
        )
        files.append(about_component)
        
        return files
    
    def _add_state_management(self, state_type: str) -> List[GeneratedCode]:
        """Add state management system"""
        files = []
        
        if state_type == "zustand":
            store_file = GeneratedCode(
                file_path="src/store/useStore.ts",
                content="""import { create } from 'zustand';

interface AppState {
  count: number;
  increment: () => void;
  decrement: () => void;
  reset: () => void;
}

export const useStore = create<AppState>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
  reset: () => set({ count: 0 }),
}));""",
                language="typescript",
                description="Zustand store for state management",
                dependencies=["zustand"],
                imports=["import { create } from 'zustand';"],
                exports=["useStore"]
            )
            files.append(store_file)
        
        return files
    
    def _add_authentication_system(self) -> List[GeneratedCode]:
        """Add authentication system"""
        files = []
        
        # Generate auth context
        auth_context = GeneratedCode(
            file_path="src/contexts/AuthContext.tsx",
            content="""import React, { createContext, useContext, useState, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Implement your login logic here
      const mockUser = { id: '1', email, name: 'User' };
      setUser(mockUser);
    } catch (error) {
      console.error('Login failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}""",
            language="typescript",
            description="Authentication context and provider",
            dependencies=["react"],
            imports=["import React, { createContext, useContext, useState, ReactNode } from 'react';"],
            exports=["AuthProvider", "useAuth"]
        )
        files.append(auth_context)
        
        return files
    
    def display_integration_result(self, result: IntegrationResult) -> None:
        """Display integration result in a formatted way"""
        if self.console:
            # Display success/failure status
            status_color = "green" if result.success else "red"
            status_text = "✅ Success" if result.success else "❌ Failed"
            self.console.print(f"[{status_color}]{status_text}[/{status_color}]\n")
            
            # Display generated files
            if result.generated_files:
                files_table = Table(title="Generated Files")
                files_table.add_column("File Path", style="cyan")
                files_table.add_column("Language", style="yellow")
                files_table.add_column("Description", style="green")
                
                for file in result.generated_files:
                    files_table.add_row(file.file_path, file.language, file.description)
                
                self.console.print(files_table)
                self.console.print()
            
            # Display component suggestions
            if result.component_suggestions:
                comp_table = Table(title="Component Suggestions")
                comp_table.add_column("Component", style="cyan")
                comp_table.add_column("Description", style="green")
                
                for comp in result.component_suggestions:
                    comp_table.add_row(comp.name, comp.description)
                
                self.console.print(comp_table)
                self.console.print()
            
            # Display library recommendations
            if result.library_recommendations:
                lib_table = Table(title="Library Recommendations")
                lib_table.add_column("Library", style="cyan")
                lib_table.add_column("Description", style="green")
                lib_table.add_column("Trust Score", style="yellow")
                
                for lib in result.library_recommendations:
                    lib_table.add_row(lib.name, lib.description, f"{lib.trust_score}/10")
                
                self.console.print(lib_table)
                self.console.print()
            
            # Display setup instructions
            if result.setup_instructions:
                instructions_panel = Panel(
                    "\n".join(result.setup_instructions),
                    title="Setup Instructions",
                    expand=False
                )
                self.console.print(instructions_panel)
                self.console.print()
            
            # Display warnings and errors
            if result.warnings:
                warnings_panel = Panel(
                    "\n".join(f"⚠️  {warning}" for warning in result.warnings),
                    title="Warnings",
                    border_style="yellow",
                    expand=False
                )
                self.console.print(warnings_panel)
            
            if result.errors:
                errors_panel = Panel(
                    "\n".join(f"❌ {error}" for error in result.errors),
                    title="Errors",
                    border_style="red",
                    expand=False
                )
                self.console.print(errors_panel)
        
        else:
            # Plain text output
            print(f"Integration {'Success' if result.success else 'Failed'}")
            
            if result.generated_files:
                print("\nGenerated Files:")
                for file in result.generated_files:
                    print(f"  - {file.file_path} ({file.language}): {file.description}")
            
            if result.setup_instructions:
                print("\nSetup Instructions:")
                for instruction in result.setup_instructions:
                    print(f"  {instruction}")
            
            if result.warnings:
                print("\nWarnings:")
                for warning in result.warnings:
                    print(f"  ⚠️  {warning}")
            
            if result.errors:
                print("\nErrors:")
                for error in result.errors:
                    print(f"  ❌ {error}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        context7_status = self.context7.get_status_report() if self.context7 else {}
        shadcn_status = self.shadcn.get_status_report() if self.shadcn else {}
        
        return {
            "unified_integration": {
                "project_path": str(self.project_path),
                "generation_cache_size": len(self.generation_cache),
                "rich_available": RICH_AVAILABLE,
                "integration_status": "active"
            },
            "context7_integration": context7_status,
            "shadcn_integration": shadcn_status
        }

# Global instance management
_unified_integration: Optional[UnifiedMCPIntegration] = None

def initialize_unified_mcp_integration(project_path: Path) -> UnifiedMCPIntegration:
    """Initialize the global unified MCP integration instance"""
    global _unified_integration
    _unified_integration = UnifiedMCPIntegration(project_path)
    logger.info("Unified MCP integration initialized globally")
    return _unified_integration

def get_unified_mcp_integration() -> Optional[UnifiedMCPIntegration]:
    """Get the global unified MCP integration instance"""
    return _unified_integration

def generate_project_with_mcp(requirements: ProjectRequirements, strategy: CodeGenerationStrategy = CodeGenerationStrategy.COMPREHENSIVE) -> Optional[IntegrationResult]:
    """Convenience function to generate project using global instance"""
    integration = get_unified_mcp_integration()
    if integration:
        return integration.generate_new_project(requirements, strategy)
    return None

def modify_project_with_mcp(requirements: ProjectRequirements, integration_type: IntegrationType = IntegrationType.FEATURE_ENHANCEMENT) -> Optional[IntegrationResult]:
    """Convenience function to modify project using global instance"""
    integration = get_unified_mcp_integration()
    if integration:
        return integration.modify_existing_project(requirements, integration_type)
    return None