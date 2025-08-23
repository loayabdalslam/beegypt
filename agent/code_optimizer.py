"""Code optimization module for analyzing and improving AI-generated code.

This module provides functionality to analyze AI-generated code output,
extract optimized versions, and present comparisons between original
and optimized code for better development decisions.
"""

import logging
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not available. Code optimization display will be limited.")

from models.ai_client_factory import AIClientFactory
from config import (
    SELECTED_PROVIDER, 
    GEMINI_MODEL,
    DEFAULT_TEMPERATURE,
    MAX_OUTPUT_TOKENS
)

# Configure logging
logger = logging.getLogger(__name__)

class OptimizationType(Enum):
    """Types of code optimizations."""
    PERFORMANCE = "performance"
    READABILITY = "readability"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    BEST_PRACTICES = "best_practices"
    MEMORY_USAGE = "memory_usage"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"

class CodeLanguage(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    SHELL = "shell"
    UNKNOWN = "unknown"

@dataclass
class OptimizationSuggestion:
    """Represents a single optimization suggestion."""
    type: OptimizationType
    title: str
    description: str
    original_code: str
    optimized_code: str
    explanation: str
    impact_level: str  # "low", "medium", "high"
    line_numbers: Optional[List[int]] = None
    estimated_improvement: Optional[str] = None
    tags: Optional[List[str]] = None

@dataclass
class CodeAnalysisResult:
    """Results of code analysis and optimization."""
    original_code: str
    language: CodeLanguage
    suggestions: List[OptimizationSuggestion]
    overall_score: float  # 0-100 scale
    complexity_score: float
    maintainability_score: float
    performance_score: float
    security_score: float
    timestamp: datetime
    analysis_duration: float
    file_path: Optional[Path] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['language'] = self.language.value
        result['timestamp'] = self.timestamp.isoformat()
        result['file_path'] = str(self.file_path) if self.file_path else None
        
        # Convert suggestions
        result['suggestions'] = [
            {
                **asdict(suggestion),
                'type': suggestion.type.value
            }
            for suggestion in self.suggestions
        ]
        
        return result

class CodeOptimizer:
    """Main code optimization engine."""
    
    def __init__(self, 
                 ai_provider: Optional[str] = None,
                 model_name: Optional[str] = None,
                 temperature: float = 0.1):
        """
        Initialize the code optimizer.
        
        Args:
            ai_provider: AI provider to use for optimization analysis
            model_name: Specific model to use
            temperature: Temperature for AI generation (lower = more focused)
        """
        self.ai_provider = ai_provider or SELECTED_PROVIDER
        self.model_name = model_name or GEMINI_MODEL
        self.temperature = temperature
        
        # Initialize AI client
        try:
            self.ai_client = AIClientFactory.create_client(
                provider=self.ai_provider,
                model=self.model_name
            )
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            self.ai_client = None
        
        # Console for rich output
        self.console = Console() if RICH_AVAILABLE else None
        
        # Language detection patterns
        self.language_patterns = {
            CodeLanguage.PYTHON: [r'\.py$', r'def\s+\w+', r'import\s+\w+', r'from\s+\w+\s+import'],
            CodeLanguage.JAVASCRIPT: [r'\.js$', r'function\s+\w+', r'const\s+\w+', r'let\s+\w+', r'var\s+\w+'],
            CodeLanguage.TYPESCRIPT: [r'\.ts$', r'interface\s+\w+', r'type\s+\w+', r':\s*\w+'],
            CodeLanguage.JAVA: [r'\.java$', r'public\s+class', r'private\s+\w+', r'public\s+static\s+void\s+main'],
            CodeLanguage.CSHARP: [r'\.cs$', r'public\s+class', r'using\s+System', r'namespace\s+\w+'],
            CodeLanguage.CPP: [r'\.(cpp|cc|cxx)$', r'#include\s*<', r'std::', r'int\s+main'],
            CodeLanguage.GO: [r'\.go$', r'package\s+\w+', r'func\s+\w+', r'import\s+"'],
            CodeLanguage.RUST: [r'\.rs$', r'fn\s+\w+', r'let\s+\w+', r'use\s+\w+'],
            CodeLanguage.PHP: [r'\.php$', r'<\?php', r'function\s+\w+', r'\$\w+'],
            CodeLanguage.RUBY: [r'\.rb$', r'def\s+\w+', r'class\s+\w+', r'require\s+'],
            CodeLanguage.HTML: [r'\.html?$', r'<html', r'<div', r'<script'],
            CodeLanguage.CSS: [r'\.css$', r'\{[^}]*\}', r'@media', r'#\w+'],
            CodeLanguage.SQL: [r'\.sql$', r'SELECT\s+', r'FROM\s+', r'WHERE\s+'],
            CodeLanguage.SHELL: [r'\.(sh|bash)$', r'#!/bin/', r'echo\s+', r'if\s*\[']
        }
    
    def detect_language(self, code: str, file_path: Optional[Path] = None) -> CodeLanguage:
        """Detect the programming language of the code."""
        if file_path:
            file_ext = file_path.suffix.lower()
            for lang, patterns in self.language_patterns.items():
                if any(re.search(pattern, file_ext, re.IGNORECASE) for pattern in patterns):
                    return lang
        
        # Analyze code content
        for lang, patterns in self.language_patterns.items():
            matches = sum(1 for pattern in patterns[1:] if re.search(pattern, code, re.IGNORECASE | re.MULTILINE))
            if matches >= 2:  # Require at least 2 pattern matches
                return lang
        
        return CodeLanguage.UNKNOWN
    
    def analyze_code(self, 
                    code: str, 
                    file_path: Optional[Path] = None,
                    optimization_types: Optional[List[OptimizationType]] = None) -> CodeAnalysisResult:
        """Analyze code and generate optimization suggestions."""
        start_time = datetime.now()
        
        # Detect language
        language = self.detect_language(code, file_path)
        
        # Default optimization types
        if optimization_types is None:
            optimization_types = [
                OptimizationType.PERFORMANCE,
                OptimizationType.READABILITY,
                OptimizationType.MAINTAINABILITY,
                OptimizationType.BEST_PRACTICES
            ]
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(code, language, optimization_types)
        
        # Calculate scores
        scores = self._calculate_scores(code, language, suggestions)
        
        # Calculate analysis duration
        duration = (datetime.now() - start_time).total_seconds()
        
        return CodeAnalysisResult(
            original_code=code,
            language=language,
            suggestions=suggestions,
            overall_score=scores['overall'],
            complexity_score=scores['complexity'],
            maintainability_score=scores['maintainability'],
            performance_score=scores['performance'],
            security_score=scores['security'],
            timestamp=start_time,
            analysis_duration=duration,
            file_path=file_path
        )
    
    def _generate_suggestions(self, 
                            code: str, 
                            language: CodeLanguage, 
                            optimization_types: List[OptimizationType]) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions using AI analysis."""
        if not self.ai_client:
            logger.warning("AI client not available, returning basic suggestions")
            return self._generate_basic_suggestions(code, language)
        
        suggestions = []
        
        for opt_type in optimization_types:
            try:
                suggestion = self._generate_suggestion_for_type(code, language, opt_type)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"Error generating {opt_type.value} suggestion: {e}")
        
        return suggestions
    
    def _generate_suggestion_for_type(self, 
                                    code: str, 
                                    language: CodeLanguage, 
                                    opt_type: OptimizationType) -> Optional[OptimizationSuggestion]:
        """Generate a specific type of optimization suggestion."""
        prompt = self._create_optimization_prompt(code, language, opt_type)
        
        try:
            response = self.ai_client.generate_text(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=MAX_OUTPUT_TOKENS // 2
            )
            
            if response.get('success') and response.get('content'):
                return self._parse_optimization_response(response['content'], opt_type)
        except Exception as e:
            logger.error(f"AI generation failed for {opt_type.value}: {e}")
        
        return None
    
    def _create_optimization_prompt(self, 
                                  code: str, 
                                  language: CodeLanguage, 
                                  opt_type: OptimizationType) -> str:
        """Create a prompt for AI optimization analysis."""
        base_prompt = f"""
Analyze the following {language.value} code and provide {opt_type.value} optimization suggestions.

Code to analyze:
```{language.value}
{code}
```

Please provide your response in the following JSON format:
{{
    "title": "Brief title of the optimization",
    "description": "Detailed description of the issue",
    "optimized_code": "The improved version of the code",
    "explanation": "Explanation of why this optimization is beneficial",
    "impact_level": "low|medium|high",
    "estimated_improvement": "Brief description of expected improvement",
    "tags": ["tag1", "tag2"]
}}

Focus specifically on {opt_type.value} improvements. If no significant improvements are possible, return null.
"""
        
        return base_prompt
    
    def _parse_optimization_response(self, 
                                   response: str, 
                                   opt_type: OptimizationType) -> Optional[OptimizationSuggestion]:
        """Parse AI response into OptimizationSuggestion."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            if not data or data == "null":
                return None
            
            return OptimizationSuggestion(
                type=opt_type,
                title=data.get('title', f'{opt_type.value.title()} Optimization'),
                description=data.get('description', ''),
                original_code='',  # Will be filled by caller
                optimized_code=data.get('optimized_code', ''),
                explanation=data.get('explanation', ''),
                impact_level=data.get('impact_level', 'medium'),
                estimated_improvement=data.get('estimated_improvement'),
                tags=data.get('tags', [])
            )
        except Exception as e:
            logger.error(f"Failed to parse optimization response: {e}")
            return None
    
    def _generate_basic_suggestions(self, 
                                  code: str, 
                                  language: CodeLanguage) -> List[OptimizationSuggestion]:
        """Generate basic optimization suggestions without AI."""
        suggestions = []
        
        # Basic Python suggestions
        if language == CodeLanguage.PYTHON:
            if 'print(' in code:
                suggestions.append(OptimizationSuggestion(
                    type=OptimizationType.BEST_PRACTICES,
                    title="Replace print statements with logging",
                    description="Using logging instead of print provides better control over output",
                    original_code=code,
                    optimized_code=code.replace('print(', 'logger.info('),
                    explanation="Logging allows for different levels and can be easily disabled in production",
                    impact_level="medium"
                ))
            
            if re.search(r'for\s+\w+\s+in\s+range\(len\(', code):
                suggestions.append(OptimizationSuggestion(
                    type=OptimizationType.READABILITY,
                    title="Use enumerate instead of range(len())",
                    description="enumerate() is more Pythonic and readable",
                    original_code=code,
                    optimized_code=re.sub(r'for\s+(\w+)\s+in\s+range\(len\((\w+)\)\):', 
                                         r'for \1, item in enumerate(\2):', code),
                    explanation="enumerate() provides both index and value, making code more readable",
                    impact_level="low"
                ))
        
        return suggestions
    
    def _calculate_scores(self, 
                        code: str, 
                        language: CodeLanguage, 
                        suggestions: List[OptimizationSuggestion]) -> Dict[str, float]:
        """Calculate various quality scores for the code."""
        # Basic scoring algorithm
        base_score = 70.0
        
        # Deduct points based on suggestions
        deductions = {
            'high': 15.0,
            'medium': 8.0,
            'low': 3.0
        }
        
        total_deduction = sum(deductions.get(s.impact_level, 5.0) for s in suggestions)
        overall_score = max(0.0, min(100.0, base_score - total_deduction))
        
        # Calculate component scores
        complexity_score = self._calculate_complexity_score(code, language)
        maintainability_score = max(0.0, 80.0 - len([s for s in suggestions if s.type == OptimizationType.MAINTAINABILITY]) * 10)
        performance_score = max(0.0, 85.0 - len([s for s in suggestions if s.type == OptimizationType.PERFORMANCE]) * 12)
        security_score = max(0.0, 90.0 - len([s for s in suggestions if s.type == OptimizationType.SECURITY]) * 20)
        
        return {
            'overall': overall_score,
            'complexity': complexity_score,
            'maintainability': maintainability_score,
            'performance': performance_score,
            'security': security_score
        }
    
    def _calculate_complexity_score(self, code: str, language: CodeLanguage) -> float:
        """Calculate code complexity score."""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Basic complexity indicators
        complexity_indicators = [
            r'if\s+',
            r'for\s+',
            r'while\s+',
            r'try\s*:',
            r'except\s*:',
            r'def\s+\w+',
            r'class\s+\w+'
        ]
        
        complexity_count = sum(
            len(re.findall(pattern, code, re.IGNORECASE))
            for pattern in complexity_indicators
        )
        
        # Calculate score (lower complexity = higher score)
        if len(non_empty_lines) == 0:
            return 100.0
        
        complexity_ratio = complexity_count / len(non_empty_lines)
        score = max(0.0, 100.0 - (complexity_ratio * 200))
        
        return min(100.0, score)
    
    def display_analysis_results(self, result: CodeAnalysisResult) -> None:
        """Display analysis results in a formatted way."""
        if not self.console:
            self._display_text_results(result)
            return
        
        # Create main panel
        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold blue]Code Analysis Results[/bold blue]\n"
            f"Language: [green]{result.language.value.title()}[/green]\n"
            f"Analysis Duration: [yellow]{result.analysis_duration:.2f}s[/yellow]",
            title="📊 BEE EGYPT Code Optimizer"
        ))
        
        # Display scores
        self._display_scores(result)
        
        # Display suggestions
        if result.suggestions:
            self.console.print("\n[bold yellow]🔧 Optimization Suggestions[/bold yellow]")
            for i, suggestion in enumerate(result.suggestions, 1):
                self._display_suggestion(suggestion, i)
        else:
            self.console.print("\n[green]✅ No optimization suggestions - code looks good![/green]")
    
    def _display_scores(self, result: CodeAnalysisResult) -> None:
        """Display quality scores."""
        table = Table(title="Quality Scores")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="magenta")
        table.add_column("Status", style="green")
        
        scores = [
            ("Overall", result.overall_score),
            ("Complexity", result.complexity_score),
            ("Maintainability", result.maintainability_score),
            ("Performance", result.performance_score),
            ("Security", result.security_score)
        ]
        
        for metric, score in scores:
            status = "🟢 Excellent" if score >= 80 else "🟡 Good" if score >= 60 else "🔴 Needs Work"
            table.add_row(metric, f"{score:.1f}/100", status)
        
        self.console.print(table)
    
    def _display_suggestion(self, suggestion: OptimizationSuggestion, index: int) -> None:
        """Display a single optimization suggestion."""
        impact_color = {
            "high": "red",
            "medium": "yellow",
            "low": "green"
        }.get(suggestion.impact_level, "white")
        
        # Create suggestion panel
        content = f"[bold]{suggestion.title}[/bold]\n\n"
        content += f"[dim]{suggestion.description}[/dim]\n\n"
        
        if suggestion.explanation:
            content += f"💡 [italic]{suggestion.explanation}[/italic]\n\n"
        
        if suggestion.estimated_improvement:
            content += f"📈 Expected improvement: {suggestion.estimated_improvement}\n\n"
        
        if suggestion.tags:
            content += f"🏷️  Tags: {', '.join(suggestion.tags)}"
        
        panel = Panel(
            content,
            title=f"[{impact_color}]#{index} - {suggestion.type.value.title()} ({suggestion.impact_level.title()} Impact)[/{impact_color}]",
            border_style=impact_color
        )
        
        self.console.print(panel)
        
        # Display code comparison if available
        if suggestion.optimized_code and suggestion.optimized_code.strip():
            self._display_code_comparison(suggestion.original_code, suggestion.optimized_code)
    
    def _display_code_comparison(self, original: str, optimized: str) -> None:
        """Display side-by-side code comparison."""
        if not original.strip():
            # Only show optimized code
            syntax = Syntax(optimized, "python", theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, title="[green]Optimized Code[/green]"))
            return
        
        # Create side-by-side comparison
        original_syntax = Syntax(original, "python", theme="monokai", line_numbers=True)
        optimized_syntax = Syntax(optimized, "python", theme="monokai", line_numbers=True)
        
        columns = Columns([
            Panel(original_syntax, title="[red]Original[/red]"),
            Panel(optimized_syntax, title="[green]Optimized[/green]")
        ])
        
        self.console.print(columns)
        self.console.print("")
    
    def _display_text_results(self, result: CodeAnalysisResult) -> None:
        """Display results in plain text format."""
        print("\n" + "=" * 60)
        print("CODE ANALYSIS RESULTS")
        print("=" * 60)
        print(f"Language: {result.language.value.title()}")
        print(f"Analysis Duration: {result.analysis_duration:.2f}s")
        print(f"Overall Score: {result.overall_score:.1f}/100")
        print("\nSuggestions:")
        
        if not result.suggestions:
            print("  No optimization suggestions - code looks good!")
        else:
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"\n{i}. {suggestion.title} ({suggestion.impact_level.upper()} impact)")
                print(f"   {suggestion.description}")
                if suggestion.explanation:
                    print(f"   Explanation: {suggestion.explanation}")
    
    def save_analysis_results(self, result: CodeAnalysisResult, output_path: Path) -> bool:
        """Save analysis results to a JSON file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Analysis results saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save analysis results: {e}")
            return False
    
    def optimize_file(self, file_path: Path, output_dir: Optional[Path] = None) -> Optional[CodeAnalysisResult]:
        """Optimize a single code file."""
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Analyze code
            result = self.analyze_code(code, file_path)
            
            # Save results if output directory specified
            if output_dir:
                output_file = output_dir / f"{file_path.stem}_analysis.json"
                self.save_analysis_results(result, output_file)
            
            return result
        except Exception as e:
            logger.error(f"Failed to optimize file {file_path}: {e}")
            return None
    
    def optimize_directory(self, 
                          directory: Path, 
                          output_dir: Optional[Path] = None,
                          file_patterns: Optional[List[str]] = None) -> List[CodeAnalysisResult]:
        """Optimize all code files in a directory."""
        if file_patterns is None:
            file_patterns = ['*.py', '*.js', '*.ts', '*.java', '*.cpp', '*.c', '*.go', '*.rs']
        
        results = []
        
        for pattern in file_patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    result = self.optimize_file(file_path, output_dir)
                    if result:
                        results.append(result)
        
        return results

# Global optimizer instance
_code_optimizer: Optional[CodeOptimizer] = None

def get_code_optimizer() -> CodeOptimizer:
    """Get the global code optimizer instance."""
    global _code_optimizer
    if _code_optimizer is None:
        _code_optimizer = CodeOptimizer()
    return _code_optimizer

def initialize_code_optimizer(**kwargs) -> CodeOptimizer:
    """Initialize the global code optimizer with custom settings."""
    global _code_optimizer
    _code_optimizer = CodeOptimizer(**kwargs)
    return _code_optimizer

def optimize_code_string(code: str, 
                        language: Optional[str] = None,
                        display_results: bool = True) -> CodeAnalysisResult:
    """Optimize a code string and optionally display results."""
    optimizer = get_code_optimizer()
    
    # Convert language string to enum if provided
    lang_enum = CodeLanguage.UNKNOWN
    if language:
        try:
            lang_enum = CodeLanguage(language.lower())
        except ValueError:
            pass
    
    # Analyze code
    result = optimizer.analyze_code(code)
    
    # Override detected language if specified
    if language:
        result.language = lang_enum
    
    # Display results if requested
    if display_results:
        optimizer.display_analysis_results(result)
    
    return result

def optimize_file_path(file_path: Union[str, Path], 
                      display_results: bool = True,
                      save_results: bool = False) -> Optional[CodeAnalysisResult]:
    """Optimize a file and optionally display/save results."""
    optimizer = get_code_optimizer()
    path = Path(file_path)
    
    result = optimizer.optimize_file(path)
    
    if result:
        if display_results:
            optimizer.display_analysis_results(result)
        
        if save_results:
            output_path = path.parent / f"{path.stem}_analysis.json"
            optimizer.save_analysis_results(result, output_path)
    
    return result