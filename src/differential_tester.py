"""
Differential Tester

Orchestrates differential testing by generating random expressions, evaluating
them with the Python oracle, compiling to C++, and comparing results across
multiple optimization levels.
"""

import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import json

from src.ast_nodes import Expr
from src.expression_generator import generate_random_expr
from src.python_interpreter import evaluate
from src.cpp_codegen import generate_cpp
from src.compiler_runner import (
    compile_cpp,
    execute_binary,
    CompilationResult,
    ExecutionResult
)


@dataclass
class TestCase:
    """
    Single differential test case.
    
    Attributes:
        seed: Random seed used to generate expression
        expr: AST expression to test
        x_value: Runtime input value for variable x
        expected: Expected result from Python oracle
    """
    seed: int
    expr: Expr
    x_value: int
    expected: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'seed': self.seed,
            'expr': repr(self.expr),
            'x_value': self.x_value,
            'expected': self.expected
        }


@dataclass
class OptimizationResult:
    """
    Result of testing one expression at one optimization level.
    
    Attributes:
        opt_level: Optimization level tested
        compiled: True if compilation succeeded
        compilation_errors: Compilation error messages if any
        executed: True if execution succeeded
        execution_errors: Execution error messages if any
        result: Actual output value, None if not obtained
        matches_oracle: True if result matches expected value
    """
    opt_level: int
    compiled: bool
    compilation_errors: str = ""
    executed: bool = False
    execution_errors: str = ""
    result: Optional[int] = None
    matches_oracle: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'opt_level': self.opt_level,
            'compiled': self.compiled,
            'compilation_errors': self.compilation_errors,
            'executed': self.executed,
            'execution_errors': self.execution_errors,
            'result': self.result,
            'matches_oracle': self.matches_oracle
        }


@dataclass
class Discrepancy:
    """
    Detected mismatch between oracle and compiled results.
    
    This represents a case requiring investigation. It may indicate:
    - A bug in our test infrastructure (oracle, codegen, etc.)
    - A compiler bug (rare)
    - Undefined behavior in generated code (should not happen)
    
    Never automatically claim this is a compiler bug without verification.
    """
    test_case: TestCase
    opt_results: Dict[int, OptimizationResult]
    cpp_source: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'test_case': self.test_case.to_dict(),
            'opt_results': {
                opt: result.to_dict() 
                for opt, result in self.opt_results.items()
            },
            'cpp_source': self.cpp_source
        }


@dataclass
class TestSummary:
    """
    Summary of differential testing campaign.
    
    Attributes:
        total_tests: Total number of test cases attempted
        successful_tests: Tests where all optimizations matched oracle
        compilation_failures: Tests where compilation failed
        execution_failures: Tests where execution failed  
        discrepancies: Tests where results didn't match
        discrepancy_list: Detailed discrepancy information
    """
    total_tests: int = 0
    successful_tests: int = 0
    compilation_failures: int = 0
    execution_failures: int = 0
    discrepancies: int = 0
    discrepancy_list: List[Discrepancy] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'total_tests': self.total_tests,
            'successful_tests': self.successful_tests,
            'compilation_failures': self.compilation_failures,
            'execution_failures': self.execution_failures,
            'discrepancies': self.discrepancies,
            'discrepancy_list': [d.to_dict() for d in self.discrepancy_list]
        }


def run_differential_test(
    num_tests: int = 100,
    seed_start: int = 0,
    opt_levels: List[int] = None,
    x_values: List[int] = None,
    max_depth: int = 4,
    max_const: int = 1000,
    var_probability: float = 0.3,
    compiler: str = "g++",
    compile_timeout: int = 30,
    execute_timeout: int = 5,
    output_dir: Optional[Path] = None,
    keep_files: bool = False
) -> TestSummary:
    """
    Run differential testing campaign.
    
    Generates random expressions, evaluates with Python oracle, compiles with
    various optimization levels, and compares results. Reports discrepancies
    without claiming they are compiler bugs.
    
    Args:
        num_tests: Number of random expressions to generate
        seed_start: Starting seed for expression generation
        opt_levels: Optimization levels to test (default: [0, 1, 2, 3])
        x_values: Runtime input values to test (default: [0, 1, 5, 100, 0xFFFFFFFF])
        max_depth: Maximum expression tree depth
        max_const: Maximum constant value in expressions
        var_probability: Probability of generating variable vs constant
        compiler: Compiler command (default: "g++")
        compile_timeout: Compilation timeout in seconds
        execute_timeout: Execution timeout in seconds
        output_dir: Directory for generated files (default: temp directory)
        keep_files: If True, keep generated files for inspection
    
    Returns:
        TestSummary with results and discrepancies
    
    Examples:
        >>> summary = run_differential_test(num_tests=10, seed_start=0)
        >>> summary.total_tests
        10
        >>> summary.successful_tests >= 0
        True
    """
    # Set defaults
    if opt_levels is None:
        opt_levels = [0, 1, 2, 3]
    
    if x_values is None:
        x_values = [0, 1, 5, 100, 0xFFFFFFFF]
    
    # Validate parameters
    if num_tests <= 0:
        raise ValueError(f"num_tests must be positive, got {num_tests}")
    
    if seed_start < 0:
        raise ValueError(f"seed_start must be non-negative, got {seed_start}")
    
    for opt in opt_levels:
        if opt not in [0, 1, 2, 3]:
            raise ValueError(f"Invalid optimization level: {opt}")
    
    # Setup output directory
    if output_dir is None:
        temp_dir = tempfile.mkdtemp()
        output_dir = Path(temp_dir)
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = TestSummary()
    
    # Generate and test expressions
    for i in range(num_tests):
        seed = seed_start + i
        
        # Generate random expression
        try:
            expr = generate_random_expr(
                seed=seed,
                max_depth=max_depth,
                max_const=max_const,
                var_probability=var_probability
            )
        except Exception as e:
            # Expression generation failed (shouldn't happen)
            summary.total_tests += 1
            summary.compilation_failures += 1
            continue
        
        # Test with each x value
        for x_value in x_values:
            summary.total_tests += 1
            
            # Create test case
            try:
                expected = evaluate(expr, x_value=x_value)
            except Exception as e:
                # Oracle evaluation failed (shouldn't happen)
                summary.execution_failures += 1
                continue
            
            test_case = TestCase(
                seed=seed,
                expr=expr,
                x_value=x_value,
                expected=expected
            )
            
            # Generate C++ source
            try:
                cpp_source = generate_cpp(expr)
            except Exception as e:
                # Code generation failed (shouldn't happen)
                summary.compilation_failures += 1
                continue
            
            # Test with each optimization level
            opt_results = {}
            has_discrepancy = False
            had_compilation_failure = False
            had_execution_failure = False
            
            for opt_level in opt_levels:
                # Compile
                binary_path = output_dir / f"test_{seed}_x{x_value}_O{opt_level}"
                
                compile_result = compile_cpp(
                    cpp_source,
                    binary_path,
                    opt_level=opt_level,
                    compiler=compiler,
                    timeout=compile_timeout
                )
                
                if not compile_result.success:
                    # Compilation failed
                    opt_results[opt_level] = OptimizationResult(
                        opt_level=opt_level,
                        compiled=False,
                        compilation_errors=compile_result.stderr,
                        executed=False
                    )
                    had_compilation_failure = True
                    continue
                
                # Execute
                exec_result = execute_binary(
                    binary_path,
                    x_value=x_value,
                    timeout=execute_timeout
                )
                
                if not exec_result.success or exec_result.output is None:
                    # Execution failed
                    opt_results[opt_level] = OptimizationResult(
                        opt_level=opt_level,
                        compiled=True,
                        executed=False,
                        execution_errors=exec_result.stderr,
                        result=exec_result.output
                    )
                    had_execution_failure = True
                    continue
                
                # Compare result
                matches = (exec_result.output == expected)
                
                opt_results[opt_level] = OptimizationResult(
                    opt_level=opt_level,
                    compiled=True,
                    executed=True,
                    result=exec_result.output,
                    matches_oracle=matches
                )
                
                if not matches:
                    has_discrepancy = True
                
                # Clean up binary unless keeping files
                if not keep_files and binary_path.exists():
                    try:
                        binary_path.unlink()
                    except:
                        pass
            
            # Categorize result
            if had_compilation_failure:
                summary.compilation_failures += 1
            elif had_execution_failure:
                summary.execution_failures += 1
            elif has_discrepancy:
                summary.discrepancies += 1
                # Record discrepancy for investigation
                discrepancy = Discrepancy(
                    test_case=test_case,
                    opt_results=opt_results,
                    cpp_source=cpp_source
                )
                summary.discrepancy_list.append(discrepancy)
            else:
                summary.successful_tests += 1
    
    return summary


def save_summary(summary: TestSummary, output_file: Path) -> None:
    """
    Save test summary to JSON file.
    
    Args:
        summary: Test summary to save
        output_file: Path to output JSON file
    """
    with open(output_file, 'w') as f:
        json.dump(summary.to_dict(), f, indent=2)


def print_summary(summary: TestSummary) -> None:
    """
    Print human-readable test summary.
    
    Args:
        summary: Test summary to print
    """
    print("=" * 70)
    print("DIFFERENTIAL TESTING SUMMARY")
    print("=" * 70)
    print(f"Total tests:             {summary.total_tests}")
    print(f"Successful:              {summary.successful_tests}")
    print(f"Compilation failures:    {summary.compilation_failures}")
    print(f"Execution failures:      {summary.execution_failures}")
    print(f"Discrepancies found:     {summary.discrepancies}")
    print("=" * 70)
    
    if summary.discrepancies > 0:
        print("\n⚠️  DISCREPANCIES DETECTED - REQUIRES INVESTIGATION")
        print("These cases need manual review to determine root cause:")
        print("- Test infrastructure bug (oracle, codegen, etc.)")
        print("- Compiler bug (rare - verify before claiming)")
        print("- Undefined behavior (should not happen in our generator)")
        print()
        
        for i, disc in enumerate(summary.discrepancy_list, 1):
            print(f"\nDiscrepancy #{i}:")
            print(f"  Seed: {disc.test_case.seed}")
            print(f"  Expression: {disc.test_case.expr}")
            print(f"  x_value: {disc.test_case.x_value}")
            print(f"  Expected (oracle): {disc.test_case.expected}")
            print(f"  Results by optimization level:")
            for opt, result in disc.opt_results.items():
                if result.compiled and result.executed:
                    match_str = "✓" if result.matches_oracle else "✗"
                    print(f"    -O{opt}: {result.result} {match_str}")
                elif result.compiled:
                    print(f"    -O{opt}: execution failed")
                else:
                    print(f"    -O{opt}: compilation failed")
    else:
        print("\n✅ No discrepancies found!")
        print("All compiled results matched the Python oracle.")
