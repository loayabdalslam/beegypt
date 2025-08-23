#!/usr/bin/env python3
"""Command-line interface for the BEE EGYPT Code Optimizer.

This module provides a CLI for analyzing and optimizing code files
with various options for customization and output formatting.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from code_optimizer import (
    CodeOptimizer,
    OptimizationType,
    CodeLanguage,
    optimize_code_string,
    optimize_file_path
)

class OptimizerCLI:
    """Command-line interface for code optimization."""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.optimizer = CodeOptimizer()
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="BEE EGYPT Code Optimizer - Analyze and optimize your code",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s file.py                    # Analyze a single file
  %(prog)s src/ --recursive           # Analyze all files in directory
  %(prog)s file.py --save-results     # Save analysis to JSON
  %(prog)s file.py --types performance readability  # Focus on specific optimizations
  %(prog)s --stdin --language python  # Analyze code from stdin
  %(prog)s file.py --output-dir ./reports  # Save results to specific directory

Supported Languages:
  Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, PHP, Ruby, HTML, CSS, SQL, Shell

Optimization Types:
  performance, readability, maintainability, security, best_practices, memory_usage, error_handling, documentation
            """
        )
        
        # Input options
        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument(
            'files',
            nargs='*',
            help='Code files or directories to analyze'
        )
        input_group.add_argument(
            '--stdin',
            action='store_true',
            help='Read code from standard input'
        )
        
        # Analysis options
        parser.add_argument(
            '--language', '-l',
            choices=[lang.value for lang in CodeLanguage if lang != CodeLanguage.UNKNOWN],
            help='Specify the programming language (auto-detected if not provided)'
        )
        
        parser.add_argument(
            '--types', '-t',
            nargs='+',
            choices=[opt.value for opt in OptimizationType],
            default=['performance', 'readability', 'maintainability', 'best_practices'],
            help='Types of optimizations to focus on (default: performance, readability, maintainability, best_practices)'
        )
        
        parser.add_argument(
            '--recursive', '-r',
            action='store_true',
            help='Recursively analyze files in directories'
        )
        
        parser.add_argument(
            '--patterns',
            nargs='+',
            default=['*.py', '*.js', '*.ts', '*.java', '*.cpp', '*.c', '*.go', '*.rs'],
            help='File patterns to match when analyzing directories (default: common code file extensions)'
        )
        
        # Output options
        parser.add_argument(
            '--output-dir', '-o',
            type=Path,
            help='Directory to save analysis results (JSON format)'
        )
        
        parser.add_argument(
            '--save-results', '-s',
            action='store_true',
            help='Save analysis results to JSON files'
        )
        
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress detailed output, only show summary'
        )
        
        parser.add_argument(
            '--json-output',
            action='store_true',
            help='Output results in JSON format instead of formatted display'
        )
        
        parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        
        # AI options
        parser.add_argument(
            '--ai-provider',
            help='AI provider to use for analysis (default: from config)'
        )
        
        parser.add_argument(
            '--model',
            help='AI model to use (default: from config)'
        )
        
        parser.add_argument(
            '--temperature',
            type=float,
            default=0.1,
            help='AI temperature for analysis (default: 0.1)'
        )
        
        # Utility options
        parser.add_argument(
            '--version', '-v',
            action='version',
            version='BEE EGYPT Code Optimizer 1.0.0'
        )
        
        parser.add_argument(
            '--list-languages',
            action='store_true',
            help='List supported programming languages'
        )
        
        parser.add_argument(
            '--list-types',
            action='store_true',
            help='List available optimization types'
        )
        
        return parser
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with the given arguments."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Handle utility commands
        if parsed_args.list_languages:
            self._list_languages()
            return 0
        
        if parsed_args.list_types:
            self._list_optimization_types()
            return 0
        
        # Disable colors if requested or if rich is not available
        if parsed_args.no_color or not RICH_AVAILABLE:
            self.console = None
        
        # Initialize optimizer with custom settings
        if parsed_args.ai_provider or parsed_args.model or parsed_args.temperature != 0.1:
            self.optimizer = CodeOptimizer(
                ai_provider=parsed_args.ai_provider,
                model_name=parsed_args.model,
                temperature=parsed_args.temperature
            )
        
        # Convert optimization types
        optimization_types = [OptimizationType(t) for t in parsed_args.types]
        
        try:
            if parsed_args.stdin:
                return self._analyze_stdin(parsed_args, optimization_types)
            else:
                return self._analyze_files(parsed_args, optimization_types)
        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n[yellow]Analysis interrupted by user[/yellow]")
            else:
                print("\nAnalysis interrupted by user")
            return 1
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error: {e}[/red]")
            else:
                print(f"Error: {e}")
            return 1
    
    def _analyze_stdin(self, args, optimization_types) -> int:
        """Analyze code from standard input."""
        if not args.quiet and self.console:
            self.console.print("[dim]Reading code from stdin... (Press Ctrl+D when done)[/dim]")
        
        try:
            code = sys.stdin.read()
        except KeyboardInterrupt:
            return 1
        
        if not code.strip():
            if self.console:
                self.console.print("[red]No code provided[/red]")
            else:
                print("No code provided")
            return 1
        
        # Analyze code
        result = self.optimizer.analyze_code(
            code=code,
            optimization_types=optimization_types
        )
        
        # Override language if specified
        if args.language:
            result.language = CodeLanguage(args.language)
        
        # Output results
        if args.json_output:
            print(json.dumps(result.to_dict(), indent=2))
        elif not args.quiet:
            self.optimizer.display_analysis_results(result)
        
        # Save results if requested
        if args.save_results or args.output_dir:
            output_dir = args.output_dir or Path.cwd()
            output_file = output_dir / "stdin_analysis.json"
            self.optimizer.save_analysis_results(result, output_file)
        
        return 0
    
    def _analyze_files(self, args, optimization_types) -> int:
        """Analyze files or directories."""
        if not args.files:
            print("No files specified")
            return 1
        
        all_results = []
        total_files = 0
        
        # Collect all files to analyze
        files_to_analyze = []
        for file_arg in args.files:
            path = Path(file_arg)
            if not path.exists():
                if self.console:
                    self.console.print(f"[red]Path not found: {path}[/red]")
                else:
                    print(f"Path not found: {path}")
                continue
            
            if path.is_file():
                files_to_analyze.append(path)
            elif path.is_dir() and args.recursive:
                for pattern in args.patterns:
                    files_to_analyze.extend(path.rglob(pattern))
            elif path.is_dir():
                for pattern in args.patterns:
                    files_to_analyze.extend(path.glob(pattern))
        
        if not files_to_analyze:
            if self.console:
                self.console.print("[yellow]No files found to analyze[/yellow]")
            else:
                print("No files found to analyze")
            return 0
        
        # Analyze files with progress bar
        if self.console and not args.quiet:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Analyzing files...", total=len(files_to_analyze))
                
                for file_path in files_to_analyze:
                    progress.update(task, description=f"Analyzing {file_path.name}...")
                    result = self._analyze_single_file(file_path, args, optimization_types)
                    if result:
                        all_results.append(result)
                        total_files += 1
                    progress.advance(task)
        else:
            for file_path in files_to_analyze:
                if not args.quiet:
                    print(f"Analyzing {file_path}...")
                result = self._analyze_single_file(file_path, args, optimization_types)
                if result:
                    all_results.append(result)
                    total_files += 1
        
        # Display summary
        if not args.quiet:
            self._display_summary(all_results, total_files)
        
        # Output JSON if requested
        if args.json_output:
            output_data = {
                'summary': {
                    'total_files': total_files,
                    'average_score': sum(r.overall_score for r in all_results) / len(all_results) if all_results else 0,
                    'total_suggestions': sum(len(r.suggestions) for r in all_results)
                },
                'results': [r.to_dict() for r in all_results]
            }
            print(json.dumps(output_data, indent=2))
        
        return 0
    
    def _analyze_single_file(self, file_path: Path, args, optimization_types):
        """Analyze a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            result = self.optimizer.analyze_code(
                code=code,
                file_path=file_path,
                optimization_types=optimization_types
            )
            
            # Display individual results if not quiet
            if not args.quiet and not args.json_output:
                if self.console:
                    self.console.print(f"\n[bold blue]📁 {file_path}[/bold blue]")
                else:
                    print(f"\n{file_path}")
                self.optimizer.display_analysis_results(result)
            
            # Save results if requested
            if args.save_results or args.output_dir:
                output_dir = args.output_dir or file_path.parent
                output_file = output_dir / f"{file_path.stem}_analysis.json"
                self.optimizer.save_analysis_results(result, output_file)
            
            return result
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error analyzing {file_path}: {e}[/red]")
            else:
                print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _display_summary(self, results, total_files):
        """Display analysis summary."""
        if not results:
            return
        
        avg_score = sum(r.overall_score for r in results) / len(results)
        total_suggestions = sum(len(r.suggestions) for r in results)
        
        if self.console:
            self.console.print("\n")
            summary_panel = Panel.fit(
                f"[bold green]Analysis Complete![/bold green]\n\n"
                f"📊 Files Analyzed: [cyan]{total_files}[/cyan]\n"
                f"⭐ Average Score: [yellow]{avg_score:.1f}/100[/yellow]\n"
                f"🔧 Total Suggestions: [magenta]{total_suggestions}[/magenta]",
                title="📈 Summary"
            )
            self.console.print(summary_panel)
            
            # Show top issues
            if total_suggestions > 0:
                self._display_top_issues(results)
        else:
            print("\n" + "=" * 50)
            print("ANALYSIS SUMMARY")
            print("=" * 50)
            print(f"Files Analyzed: {total_files}")
            print(f"Average Score: {avg_score:.1f}/100")
            print(f"Total Suggestions: {total_suggestions}")
    
    def _display_top_issues(self, results):
        """Display most common optimization types."""
        issue_counts = {}
        for result in results:
            for suggestion in result.suggestions:
                issue_type = suggestion.type.value
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        if not issue_counts:
            return
        
        # Sort by frequency
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        
        table = Table(title="Most Common Issues")
        table.add_column("Issue Type", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Percentage", style="green")
        
        total_issues = sum(issue_counts.values())
        for issue_type, count in sorted_issues[:5]:  # Top 5
            percentage = (count / total_issues) * 100
            table.add_row(
                issue_type.replace('_', ' ').title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        self.console.print(table)
    
    def _list_languages(self):
        """List supported programming languages."""
        if self.console:
            table = Table(title="Supported Programming Languages")
            table.add_column("Language", style="cyan")
            table.add_column("Code", style="magenta")
            
            for lang in CodeLanguage:
                if lang != CodeLanguage.UNKNOWN:
                    table.add_row(lang.value.title(), lang.value)
            
            self.console.print(table)
        else:
            print("Supported Programming Languages:")
            for lang in CodeLanguage:
                if lang != CodeLanguage.UNKNOWN:
                    print(f"  {lang.value.title()} ({lang.value})")
    
    def _list_optimization_types(self):
        """List available optimization types."""
        if self.console:
            table = Table(title="Available Optimization Types")
            table.add_column("Type", style="cyan")
            table.add_column("Code", style="magenta")
            table.add_column("Description", style="green")
            
            descriptions = {
                OptimizationType.PERFORMANCE: "Improve execution speed and efficiency",
                OptimizationType.READABILITY: "Enhance code clarity and understanding",
                OptimizationType.MAINTAINABILITY: "Make code easier to modify and extend",
                OptimizationType.SECURITY: "Address security vulnerabilities",
                OptimizationType.BEST_PRACTICES: "Follow language-specific best practices",
                OptimizationType.MEMORY_USAGE: "Optimize memory consumption",
                OptimizationType.ERROR_HANDLING: "Improve error handling and robustness",
                OptimizationType.DOCUMENTATION: "Enhance code documentation"
            }
            
            for opt_type in OptimizationType:
                table.add_row(
                    opt_type.value.replace('_', ' ').title(),
                    opt_type.value,
                    descriptions.get(opt_type, "")
                )
            
            self.console.print(table)
        else:
            print("Available Optimization Types:")
            descriptions = {
                OptimizationType.PERFORMANCE: "Improve execution speed and efficiency",
                OptimizationType.READABILITY: "Enhance code clarity and understanding",
                OptimizationType.MAINTAINABILITY: "Make code easier to modify and extend",
                OptimizationType.SECURITY: "Address security vulnerabilities",
                OptimizationType.BEST_PRACTICES: "Follow language-specific best practices",
                OptimizationType.MEMORY_USAGE: "Optimize memory consumption",
                OptimizationType.ERROR_HANDLING: "Improve error handling and robustness",
                OptimizationType.DOCUMENTATION: "Enhance code documentation"
            }
            
            for opt_type in OptimizationType:
                desc = descriptions.get(opt_type, "")
                print(f"  {opt_type.value.replace('_', ' ').title()} ({opt_type.value})")
                if desc:
                    print(f"    {desc}")

def main():
    """Main entry point for the CLI."""
    cli = OptimizerCLI()
    return cli.run()

if __name__ == '__main__':
    sys.exit(main())