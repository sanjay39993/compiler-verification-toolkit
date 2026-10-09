"""
Unit tests for Compiler Runner

Tests C++ compilation, binary execution, error handling, and output parsing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.compiler_runner import (
    CompilationResult,
    ExecutionResult,
    compile_cpp,
    execute_binary,
    create_output_directory
)


# Simple valid C++ programs for testing
SIMPLE_PROGRAM = """
#include <iostream>
#include <cstdint>

int main() {
    uint32_t x;
    std::cin >> x;
    uint32_t result = x + 5u;
    std::cout << result << std::endl;
    return 0;
}
"""

CONST_PROGRAM = """
#include <iostream>
#include <cstdint>

int main() {
    uint32_t x;
    std::cin >> x;
    uint32_t result = 42u;
    std::cout << result << std::endl;
    return 0;
}
"""

SYNTAX_ERROR_PROGRAM = """
#include <iostream>

int main() {
    missing semicolon here
    return 0;
}
"""

MULTIPLY_PROGRAM = """
#include <iostream>
#include <cstdint>

int main() {
    uint32_t x;
    std::cin >> x;
    uint32_t result = x * 2u;
    std::cout << result << std::endl;
    return 0;
}
"""


class TestCompilationResult:
    """Tests for CompilationResult dataclass"""
    
    def test_compilation_result_creation(self):
        """Test creating CompilationResult"""
        result = CompilationResult(
            success=True,
            command=["g++", "-o", "test"],
            stdout="",
            stderr="",
            returncode=0,
            binary_path=Path("test")
        )
        assert result.success is True
        assert result.returncode == 0
        assert result.binary_path == Path("test")
    
    def test_compilation_result_failure(self):
        """Test CompilationResult for failure"""
        result = CompilationResult(
            success=False,
            command=["g++", "-o", "test"],
            stdout="",
            stderr="error: syntax error",
            returncode=1,
            binary_path=None
        )
        assert result.success is False
        assert result.returncode == 1
        assert result.binary_path is None


class TestExecutionResult:
    """Tests for ExecutionResult dataclass"""
    
    def test_execution_result_success(self):
        """Test creating successful ExecutionResult"""
        result = ExecutionResult(
            success=True,
            output=42,
            stdout="42\n",
            stderr="",
            returncode=0
        )
        assert result.success is True
        assert result.output == 42
        assert result.returncode == 0
    
    def test_execution_result_failure(self):
        """Test ExecutionResult for failure"""
        result = ExecutionResult(
            success=False,
            output=None,
            stdout="",
            stderr="error",
            returncode=1
        )
        assert result.success is False
        assert result.output is None
        assert result.returncode == 1


class TestCompileCpp:
    """Tests for C++ compilation"""
    
    def test_compile_simple_program(self):
        """Test compiling a simple valid program"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_prog"
            result = compile_cpp(SIMPLE_PROGRAM, output_path, opt_level=0)
            
            assert result.success is True
            assert result.returncode == 0
            assert result.binary_path == output_path
            assert output_path.exists()
    
    def test_compile_with_optimization_levels(self):
        """Test compilation with different optimization levels"""
        with tempfile.TemporaryDirectory() as tmpdir:
            for opt_level in [0, 1, 2, 3]:
                output_path = Path(tmpdir) / f"test_O{opt_level}"
                result = compile_cpp(CONST_PROGRAM, output_path, opt_level=opt_level)
                
                assert result.success is True, f"Failed at -O{opt_level}"
                assert result.returncode == 0
                assert output_path.exists()
                assert f"-O{opt_level}" in result.command
    
    def test_compile_syntax_error(self):
        """Test compilation failure due to syntax error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_error"
            result = compile_cpp(SYNTAX_ERROR_PROGRAM, output_path, opt_level=0)
            
            assert result.success is False
            assert result.returncode != 0
            assert result.binary_path is None
            assert len(result.stderr) > 0  # Should have error message
            assert not output_path.exists()
    
    def test_compile_creates_parent_directory(self):
        """Test that compilation creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir1" / "subdir2" / "test_prog"
            result = compile_cpp(SIMPLE_PROGRAM, output_path, opt_level=0)
            
            assert result.success is True
            assert output_path.exists()
            assert output_path.parent.exists()
    
    def test_compile_command_structure(self):
        """Test that compilation command has correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test"
            result = compile_cpp(SIMPLE_PROGRAM, output_path, opt_level=2)
            
            assert "g++" in result.command
            assert "-std=c++17" in result.command
            assert "-O2" in result.command
            assert "-Wall" in result.command
            assert "-Wextra" in result.command
            assert "-" in result.command  # stdin input
    
    def test_compile_invalid_opt_level(self):
        """Test that invalid optimization level raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test"
            
            with pytest.raises(ValueError, match="opt_level must be"):
                compile_cpp(SIMPLE_PROGRAM, output_path, opt_level=4)
            
            with pytest.raises(ValueError, match="opt_level must be"):
                compile_cpp(SIMPLE_PROGRAM, output_path, opt_level=-1)
    
    def test_compile_invalid_types(self):
        """Test that invalid parameter types raise TypeError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test"
            
            # Invalid source_code type
            with pytest.raises(TypeError, match="source_code must be str"):
                compile_cpp(123, output_path)
            
            # Invalid output_binary type
            with pytest.raises(TypeError, match="output_binary must be Path"):
                compile_cpp(SIMPLE_PROGRAM, "not_a_path")
            
            # Invalid opt_level type
            with pytest.raises(TypeError, match="opt_level must be int"):
                compile_cpp(SIMPLE_PROGRAM, output_path, opt_level="0")
    
    def test_compile_missing_compiler(self):
        """Test handling of missing compiler"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test"
            result = compile_cpp(
                SIMPLE_PROGRAM,
                output_path,
                compiler="nonexistent-compiler-xyz"
            )
            
            assert result.success is False
            assert "not found" in result.stderr.lower()


class TestExecuteBinary:
    """Tests for binary execution"""
    
    def test_execute_simple_program(self):
        """Test executing a simple program"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile program
            binary_path = Path(tmpdir) / "test_prog"
            compile_result = compile_cpp(SIMPLE_PROGRAM, binary_path, opt_level=0)
            assert compile_result.success
            
            # Execute with x=10, expects 10+5=15
            exec_result = execute_binary(binary_path, x_value=10)
            
            assert exec_result.success is True
            assert exec_result.output == 15
            assert exec_result.returncode == 0
    
    def test_execute_const_program(self):
        """Test executing program that returns constant"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile program
            binary_path = Path(tmpdir) / "test_const"
            compile_result = compile_cpp(CONST_PROGRAM, binary_path, opt_level=0)
            assert compile_result.success
            
            # Execute with any x, expects 42
            exec_result = execute_binary(binary_path, x_value=100)
            
            assert exec_result.success is True
            assert exec_result.output == 42
            assert exec_result.returncode == 0
    
    def test_execute_multiply_program(self):
        """Test executing program with multiplication"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile program
            binary_path = Path(tmpdir) / "test_mul"
            compile_result = compile_cpp(MULTIPLY_PROGRAM, binary_path, opt_level=0)
            assert compile_result.success
            
            # Test various inputs
            test_cases = [(10, 20), (0, 0), (50, 100), (1, 2)]
            for x_val, expected in test_cases:
                exec_result = execute_binary(binary_path, x_value=x_val)
                assert exec_result.success is True
                assert exec_result.output == expected, f"Failed for x={x_val}"
    
    def test_execute_large_values(self):
        """Test execution with large uint32 values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile const program
            binary_path = Path(tmpdir) / "test_large"
            compile_result = compile_cpp(CONST_PROGRAM, binary_path, opt_level=0)
            assert compile_result.success
            
            # Execute with large x value (should be ignored)
            exec_result = execute_binary(binary_path, x_value=0xFFFFFFFF)
            assert exec_result.success is True
            assert exec_result.output == 42
    
    def test_execute_missing_binary(self):
        """Test that missing binary raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Binary not found"):
            execute_binary(Path("/nonexistent/binary"), x_value=10)
    
    def test_execute_invalid_types(self):
        """Test that invalid parameter types raise TypeError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "dummy"
            binary_path.touch()  # Create empty file
            
            # Invalid binary_path type
            with pytest.raises(TypeError, match="binary_path must be Path"):
                execute_binary("not_a_path", x_value=10)
            
            # Invalid x_value type
            with pytest.raises(TypeError, match="x_value must be int"):
                execute_binary(binary_path, x_value="10")
    
    def test_execute_output_parsing(self):
        """Test that output is parsed correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile simple program
            binary_path = Path(tmpdir) / "test_parse"
            compile_result = compile_cpp(SIMPLE_PROGRAM, binary_path, opt_level=0)
            assert compile_result.success
            
            # Execute and check parsing
            exec_result = execute_binary(binary_path, x_value=7)
            assert exec_result.success is True
            assert exec_result.output == 12
            assert isinstance(exec_result.output, int)
    
    def test_execute_various_inputs(self):
        """Test execution with various input values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile program
            binary_path = Path(tmpdir) / "test_inputs"
            compile_result = compile_cpp(SIMPLE_PROGRAM, binary_path, opt_level=0)
            assert compile_result.success
            
            # Test various x values
            test_values = [0, 1, 10, 100, 1000, 12345]
            for x_val in test_values:
                exec_result = execute_binary(binary_path, x_value=x_val)
                assert exec_result.success is True
                assert exec_result.output == x_val + 5


class TestIntegration:
    """Integration tests for compile and execute workflow"""
    
    def test_full_workflow(self):
        """Test complete compile and execute workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Compile
            binary_path = Path(tmpdir) / "workflow_test"
            compile_result = compile_cpp(SIMPLE_PROGRAM, binary_path, opt_level=0)
            
            assert compile_result.success is True
            assert binary_path.exists()
            
            # Execute
            exec_result = execute_binary(binary_path, x_value=20)
            
            assert exec_result.success is True
            assert exec_result.output == 25
    
    def test_workflow_with_optimizations(self):
        """Test workflow with different optimization levels produces same result"""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = []
            
            for opt_level in [0, 1, 2, 3]:
                # Compile with different optimization
                binary_path = Path(tmpdir) / f"opt{opt_level}"
                compile_result = compile_cpp(
                    MULTIPLY_PROGRAM,
                    binary_path,
                    opt_level=opt_level
                )
                assert compile_result.success is True
                
                # Execute with same input
                exec_result = execute_binary(binary_path, x_value=10)
                assert exec_result.success is True
                results.append(exec_result.output)
            
            # All optimization levels should produce same result
            assert all(r == results[0] for r in results)
            assert results[0] == 20  # 10 * 2
    
    def test_compile_failure_no_execution(self):
        """Test that compilation failure prevents execution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "failed"
            compile_result = compile_cpp(
                SYNTAX_ERROR_PROGRAM,
                binary_path,
                opt_level=0
            )
            
            assert compile_result.success is False
            assert not binary_path.exists()
            
            # Cannot execute non-existent binary
            with pytest.raises(FileNotFoundError):
                execute_binary(binary_path, x_value=10)


class TestOutputDirectory:
    """Tests for output directory management"""
    
    def test_create_output_directory(self):
        """Test creating output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            output_dir = create_output_directory(base)
            
            assert output_dir.exists()
            assert output_dir.is_dir()
            assert output_dir.name == "output"
    
    def test_create_output_directory_idempotent(self):
        """Test that creating output directory multiple times is safe"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Create multiple times
            dir1 = create_output_directory(base)
            dir2 = create_output_directory(base)
            
            assert dir1 == dir2
            assert dir1.exists()


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_empty_source_code(self):
        """Test compilation with empty source code"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "empty"
            result = compile_cpp("", binary_path, opt_level=0)
            
            # Should fail (no main function)
            assert result.success is False
    
    def test_whitespace_only_source(self):
        """Test compilation with whitespace-only source"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "whitespace"
            result = compile_cpp("   \n\n\t  ", binary_path, opt_level=0)
            
            # Should fail (no main function)
            assert result.success is False
    
    def test_multiple_compilations_same_output(self):
        """Test that compiling to same output path overwrites"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "overwrite_test"
            
            # First compilation
            result1 = compile_cpp(CONST_PROGRAM, binary_path, opt_level=0)
            assert result1.success is True
            exec1 = execute_binary(binary_path, x_value=10)
            assert exec1.output == 42
            
            # Second compilation (different program)
            result2 = compile_cpp(SIMPLE_PROGRAM, binary_path, opt_level=0)
            assert result2.success is True
            exec2 = execute_binary(binary_path, x_value=10)
            assert exec2.output == 15  # Different result
    
    def test_compile_timeout_invalid(self):
        """Test that invalid timeout raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "test"
            
            with pytest.raises(ValueError, match="timeout must be positive"):
                compile_cpp(SIMPLE_PROGRAM, binary_path, timeout=0)
            
            with pytest.raises(ValueError, match="timeout must be positive"):
                compile_cpp(SIMPLE_PROGRAM, binary_path, timeout=-1)
    
    def test_execute_timeout_invalid(self):
        """Test that invalid execution timeout raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            binary_path = Path(tmpdir) / "dummy"
            binary_path.touch()
            
            with pytest.raises(ValueError, match="timeout must be positive"):
                execute_binary(binary_path, x_value=10, timeout=0)
