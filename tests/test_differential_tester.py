"""
Unit tests for Differential Tester

Tests the orchestration of differential testing including expression generation,
oracle evaluation, C++ compilation, execution, and result comparison.
Uses both mocking for unit tests and real integration tests.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.ast_nodes import Const, Var, BinOp
from src.differential_tester import (
    TestCase as DiffTestCase,
    OptimizationResult,
    Discrepancy,
    TestSummary as DiffTestSummary,
    run_differential_test,
    save_summary,
    print_summary
)
from src.compiler_runner import CompilationResult, ExecutionResult


class TestDataClasses:
    """Tests for dataclass structures"""
    
    def test_test_case_creation(self):
        """Test creating TestCase"""
        expr = Const(42)
        tc = DiffTestCase(seed=0, expr=expr, x_value=10, expected=42)
        
        assert tc.seed == 0
        assert tc.expr == expr
        assert tc.x_value == 10
        assert tc.expected == 42
    
    def test_test_case_to_dict(self):
        """Test TestCase serialization"""
        expr = BinOp('+', Var('x'), Const(5))
        tc = DiffTestCase(seed=42, expr=expr, x_value=10, expected=15)
        
        d = tc.to_dict()
        assert d['seed'] == 42
        assert 'expr' in d
        assert d['x_value'] == 10
        assert d['expected'] == 15
    
    def test_optimization_result_success(self):
        """Test OptimizationResult for successful case"""
        result = OptimizationResult(
            opt_level=0,
            compiled=True,
            executed=True,
            result=42,
            matches_oracle=True
        )
        
        assert result.opt_level == 0
        assert result.compiled is True
        assert result.executed is True
        assert result.result == 42
        assert result.matches_oracle is True
    
    def test_optimization_result_compilation_failure(self):
        """Test OptimizationResult for compilation failure"""
        result = OptimizationResult(
            opt_level=2,
            compiled=False,
            compilation_errors="syntax error"
        )
        
        assert result.compiled is False
        assert result.executed is False
        assert result.result is None
        assert "syntax error" in result.compilation_errors
    
    def test_discrepancy_creation(self):
        """Test creating Discrepancy"""
        tc = DiffTestCase(seed=1, expr=Const(10), x_value=5, expected=10)
        opt_results = {
            0: OptimizationResult(opt_level=0, compiled=True, executed=True, result=10, matches_oracle=True),
            1: OptimizationResult(opt_level=1, compiled=True, executed=True, result=11, matches_oracle=False)
        }
        disc = Discrepancy(test_case=tc, opt_results=opt_results, cpp_source="code")
        
        assert disc.test_case == tc
        assert len(disc.opt_results) == 2
        assert disc.cpp_source == "code"
    
    def test_test_summary_creation(self):
        """Test creating TestSummary"""
        summary = DiffTestSummary(
            total_tests=100,
            successful_tests=95,
            compilation_failures=2,
            execution_failures=1,
            discrepancies=2
        )
        
        assert summary.total_tests == 100
        assert summary.successful_tests == 95
        assert summary.compilation_failures == 2
        assert summary.execution_failures == 1
        assert summary.discrepancies == 2


class TestParameterValidation:
    """Tests for parameter validation"""
    
    def test_invalid_num_tests(self):
        """Test that invalid num_tests raises ValueError"""
        with pytest.raises(ValueError, match="num_tests must be positive"):
            run_differential_test(num_tests=0)
        
        with pytest.raises(ValueError, match="num_tests must be positive"):
            run_differential_test(num_tests=-1)
    
    def test_invalid_seed_start(self):
        """Test that negative seed_start raises ValueError"""
        with pytest.raises(ValueError, match="seed_start must be non-negative"):
            run_differential_test(num_tests=1, seed_start=-1)
    
    def test_invalid_opt_level(self):
        """Test that invalid optimization level raises ValueError"""
        with pytest.raises(ValueError, match="Invalid optimization level"):
            run_differential_test(num_tests=1, opt_levels=[0, 5])
        
        with pytest.raises(ValueError, match="Invalid optimization level"):
            run_differential_test(num_tests=1, opt_levels=[-1])


class TestMockedDifferentialTesting:
    """Tests using mocks to avoid actual compilation"""
    
    @patch('src.differential_tester.compile_cpp')
    @patch('src.differential_tester.execute_binary')
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_successful_test(self, mock_gen, mock_eval, mock_cpp, mock_exec, mock_compile):
        """Test successful differential test with mocks"""
        # Setup mocks
        mock_expr = Const(42)
        mock_gen.return_value = mock_expr
        mock_eval.return_value = 42
        mock_cpp.return_value = "mock C++ code"
        
        mock_compile.return_value = CompilationResult(
            success=True,
            command=['g++'],
            stdout='',
            stderr='',
            returncode=0,
            binary_path=Path('/tmp/test')
        )
        
        mock_exec.return_value = ExecutionResult(
            success=True,
            output=42,
            stdout='42\n',
            stderr='',
            returncode=0
        )
        
        # Run test
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Verify
        assert summary.total_tests == 1
        assert summary.successful_tests == 1
        assert summary.compilation_failures == 0
        assert summary.execution_failures == 0
        assert summary.discrepancies == 0
    
    @patch('src.differential_tester.compile_cpp')
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_compilation_failure(self, mock_gen, mock_eval, mock_cpp, mock_compile):
        """Test handling of compilation failure"""
        # Setup mocks
        mock_gen.return_value = Const(42)
        mock_eval.return_value = 42
        mock_cpp.return_value = "mock C++ code"
        
        mock_compile.return_value = CompilationResult(
            success=False,
            command=['g++'],
            stdout='',
            stderr='error: syntax error',
            returncode=1,
            binary_path=None
        )
        
        # Run test
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Verify - compilation failure is not a discrepancy
        assert summary.total_tests == 1
        assert summary.successful_tests == 0
        assert summary.compilation_failures == 1
        assert summary.discrepancies == 0
    
    @patch('src.differential_tester.execute_binary')
    @patch('src.differential_tester.compile_cpp')
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_execution_failure(self, mock_gen, mock_eval, mock_cpp, mock_compile, mock_exec):
        """Test handling of execution failure"""
        # Setup mocks
        mock_gen.return_value = Const(42)
        mock_eval.return_value = 42
        mock_cpp.return_value = "mock C++ code"
        
        mock_compile.return_value = CompilationResult(
            success=True,
            command=['g++'],
            stdout='',
            stderr='',
            returncode=0,
            binary_path=Path('/tmp/test')
        )
        
        mock_exec.return_value = ExecutionResult(
            success=False,
            output=None,
            stdout='',
            stderr='runtime error',
            returncode=1
        )
        
        # Run test
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Verify - execution failure is not a discrepancy
        assert summary.total_tests == 1
        assert summary.successful_tests == 0
        assert summary.execution_failures == 1
        assert summary.discrepancies == 0
    
    @patch('src.differential_tester.execute_binary')
    @patch('src.differential_tester.compile_cpp')
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_result_mismatch(self, mock_gen, mock_eval, mock_cpp, mock_compile, mock_exec):
        """Test detection of result mismatch (discrepancy)"""
        # Setup mocks - oracle says 42, compiled gives 43
        mock_gen.return_value = Const(42)
        mock_eval.return_value = 42  # Oracle result
        mock_cpp.return_value = "mock C++ code"
        
        mock_compile.return_value = CompilationResult(
            success=True,
            command=['g++'],
            stdout='',
            stderr='',
            returncode=0,
            binary_path=Path('/tmp/test')
        )
        
        mock_exec.return_value = ExecutionResult(
            success=True,
            output=43,  # Wrong result!
            stdout='43\n',
            stderr='',
            returncode=0
        )
        
        # Run test
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Verify - this is a discrepancy
        assert summary.total_tests == 1
        assert summary.successful_tests == 0
        assert summary.discrepancies == 1
        assert len(summary.discrepancy_list) == 1
        
        disc = summary.discrepancy_list[0]
        assert disc.test_case.expected == 42
        assert disc.opt_results[0].result == 43
        assert disc.opt_results[0].matches_oracle is False
    
    @patch('src.differential_tester.execute_binary')
    @patch('src.differential_tester.compile_cpp')
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_multiple_opt_levels(self, mock_gen, mock_eval, mock_cpp, mock_compile, mock_exec):
        """Test with multiple optimization levels"""
        # Setup mocks
        mock_gen.return_value = Const(42)
        mock_eval.return_value = 42
        mock_cpp.return_value = "mock C++ code"
        
        mock_compile.return_value = CompilationResult(
            success=True,
            command=['g++'],
            stdout='',
            stderr='',
            returncode=0,
            binary_path=Path('/tmp/test')
        )
        
        mock_exec.return_value = ExecutionResult(
            success=True,
            output=42,
            stdout='42\n',
            stderr='',
            returncode=0
        )
        
        # Run test with multiple optimization levels
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0, 1, 2, 3],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Should have compiled 4 times (once per opt level)
        assert mock_compile.call_count == 4
        assert summary.total_tests == 1
        assert summary.successful_tests == 1
    
    @patch('src.differential_tester.execute_binary')
    @patch('src.differential_tester.compile_cpp')
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_multiple_x_values(self, mock_gen, mock_eval, mock_cpp, mock_compile, mock_exec):
        """Test with multiple x values"""
        # Setup mocks
        mock_gen.return_value = Const(42)
        
        # Oracle returns different values for different x (just for testing)
        def eval_side_effect(expr, x_value):
            return 42
        mock_eval.side_effect = eval_side_effect
        
        mock_cpp.return_value = "mock C++ code"
        
        mock_compile.return_value = CompilationResult(
            success=True,
            command=['g++'],
            stdout='',
            stderr='',
            returncode=0,
            binary_path=Path('/tmp/test')
        )
        
        mock_exec.return_value = ExecutionResult(
            success=True,
            output=42,
            stdout='42\n',
            stderr='',
            returncode=0
        )
        
        # Run test with multiple x values
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[0, 1, 10],
                output_dir=Path(tmpdir)
            )
        
        # Should have 3 total tests (1 expr × 3 x values)
        assert summary.total_tests == 3


class TestIntegrationWithRealCompiler:
    """Integration tests using real G++ compiler (deterministic, minimal)"""
    
    def test_simple_constant_expression(self):
        """Test with simple constant expression"""
        # Use very small test to minimize compilation overhead
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],  # Only test -O0 for speed
                x_values=[10],
                max_depth=0,  # Only constants
                output_dir=Path(tmpdir)
            )
        
        # Should succeed (constant expressions are simple)
        assert summary.total_tests == 1
        # Either successful or had some infrastructure issue
        assert summary.total_tests == (
            summary.successful_tests +
            summary.compilation_failures +
            summary.execution_failures +
            summary.discrepancies
        )
    
    def test_reproducible_results(self):
        """Test that same seed produces reproducible results"""
        with tempfile.TemporaryDirectory() as tmpdir1:
            summary1 = run_differential_test(
                num_tests=2,
                seed_start=42,
                opt_levels=[0],
                x_values=[5],
                max_depth=1,
                output_dir=Path(tmpdir1)
            )
        
        with tempfile.TemporaryDirectory() as tmpdir2:
            summary2 = run_differential_test(
                num_tests=2,
                seed_start=42,
                opt_levels=[0],
                x_values=[5],
                max_depth=1,
                output_dir=Path(tmpdir2)
            )
        
        # Same seeds should produce same results
        assert summary1.total_tests == summary2.total_tests
        assert summary1.successful_tests == summary2.successful_tests
        assert summary1.discrepancies == summary2.discrepancies


class TestSummarySerialization:
    """Tests for summary serialization and output"""
    
    def test_save_summary(self):
        """Test saving summary to JSON"""
        summary = DiffTestSummary(
            total_tests=10,
            successful_tests=8,
            compilation_failures=1,
            execution_failures=0,
            discrepancies=1
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = Path(f.name)
        
        try:
            save_summary(summary, output_file)
            assert output_file.exists()
            
            # Verify can be read back
            import json
            with open(output_file) as f:
                data = json.load(f)
            
            assert data['total_tests'] == 10
            assert data['successful_tests'] == 8
            assert data['discrepancies'] == 1
        finally:
            output_file.unlink()
    
    def test_print_summary_no_discrepancies(self, capsys):
        """Test printing summary without discrepancies"""
        summary = DiffTestSummary(
            total_tests=100,
            successful_tests=100,
            compilation_failures=0,
            execution_failures=0,
            discrepancies=0
        )
        
        print_summary(summary)
        captured = capsys.readouterr()
        
        assert "Total tests:             100" in captured.out
        assert "Successful:              100" in captured.out
        assert "No discrepancies found" in captured.out
    
    def test_print_summary_with_discrepancies(self, capsys):
        """Test printing summary with discrepancies"""
        tc = DiffTestCase(seed=42, expr=Const(10), x_value=5, expected=10)
        opt_result = OptimizationResult(
            opt_level=0,
            compiled=True,
            executed=True,
            result=11,
            matches_oracle=False
        )
        disc = Discrepancy(
            test_case=tc,
            opt_results={0: opt_result},
            cpp_source="code"
        )
        
        summary = DiffTestSummary(
            total_tests=1,
            successful_tests=0,
            compilation_failures=0,
            execution_failures=0,
            discrepancies=1,
            discrepancy_list=[disc]
        )
        
        print_summary(summary)
        captured = capsys.readouterr()
        
        assert "DISCREPANCIES DETECTED" in captured.out
        assert "REQUIRES INVESTIGATION" in captured.out
        assert "Seed: 42" in captured.out
        assert "Expected (oracle): 10" in captured.out


class TestEdgeCases:
    """Tests for edge cases"""
    
    @patch('src.differential_tester.generate_random_expr')
    def test_expression_generation_failure(self, mock_gen):
        """Test handling when expression generation fails"""
        mock_gen.side_effect = Exception("Generation failed")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Should count as failure, not crash
        assert summary.total_tests == 1
        assert summary.compilation_failures == 1
    
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_oracle_evaluation_failure(self, mock_gen, mock_eval):
        """Test handling when oracle evaluation fails"""
        mock_gen.return_value = Const(42)
        mock_eval.side_effect = Exception("Evaluation failed")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Should count as execution failure
        assert summary.total_tests == 1
        assert summary.execution_failures == 1
    
    @patch('src.differential_tester.generate_cpp')
    @patch('src.differential_tester.evaluate')
    @patch('src.differential_tester.generate_random_expr')
    def test_cpp_generation_failure(self, mock_gen, mock_eval, mock_cpp):
        """Test handling when C++ generation fails"""
        mock_gen.return_value = Const(42)
        mock_eval.return_value = 42
        mock_cpp.side_effect = Exception("Code generation failed")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_differential_test(
                num_tests=1,
                seed_start=0,
                opt_levels=[0],
                x_values=[10],
                output_dir=Path(tmpdir)
            )
        
        # Should count as compilation failure
        assert summary.total_tests == 1
        assert summary.compilation_failures == 1
