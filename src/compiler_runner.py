"""
Compiler Runner

Compiles and executes C++ programs generated from AST expressions.
Handles compilation with various optimization levels, captures output,
and parses results safely.
"""

import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CompilationResult:
    """
    Result of a C++ compilation attempt.
    
    Attributes:
        success: True if compilation succeeded (return code 0)
        command: List of command arguments used
        stdout: Standard output from compiler
        stderr: Standard error from compiler (warnings, errors)
        returncode: Process return code
        binary_path: Path to output binary if successful, None otherwise
    """
    success: bool
    command: List[str]
    stdout: str
    stderr: str
    returncode: int
    binary_path: Optional[Path] = None


@dataclass
class ExecutionResult:
    """
    Result of executing a compiled binary.
    
    Attributes:
        success: True if execution succeeded (return code 0) and output parsed
        output: Parsed integer result, None if parsing failed
        stdout: Raw standard output from program
        stderr: Standard error from program
        returncode: Process return code
    """
    success: bool
    output: Optional[int]
    stdout: str
    stderr: str
    returncode: int


def compile_cpp(
    source_code: str,
    output_binary: Path,
    opt_level: int = 0,
    compiler: str = "g++",
    timeout: int = 30
) -> CompilationResult:
    """
    Compile C++ source code using G++ with specified optimization level.
    
    Uses subprocess.run() with shell=False for security. Captures all output
    and handles errors gracefully. Creates parent directories if needed.
    
    Args:
        source_code: C++17 source code as string
        output_binary: Path where compiled binary should be written
        opt_level: Optimization level (0, 1, 2, or 3)
        compiler: Compiler command (default: "g++")
        timeout: Compilation timeout in seconds (default: 30)
    
    Returns:
        CompilationResult with success status and captured output
    
    Raises:
        ValueError: If opt_level is not in [0, 1, 2, 3]
        TypeError: If parameters have wrong types
    
    Examples:
        >>> result = compile_cpp("int main() { return 0; }", Path("test"), opt_level=0)
        >>> result.success
        True
    """
    # Validate parameters
    if not isinstance(source_code, str):
        raise TypeError(f"source_code must be str, got {type(source_code).__name__}")
    
    if not isinstance(output_binary, Path):
        raise TypeError(f"output_binary must be Path, got {type(output_binary).__name__}")
    
    if not isinstance(opt_level, int):
        raise TypeError(f"opt_level must be int, got {type(opt_level).__name__}")
    
    if opt_level not in [0, 1, 2, 3]:
        raise ValueError(f"opt_level must be 0, 1, 2, or 3, got {opt_level}")
    
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError(f"timeout must be positive int, got {timeout}")
    
    # Create parent directory if it doesn't exist
    output_binary.parent.mkdir(parents=True, exist_ok=True)
    
    # Build compiler command
    # Use -x c++ to read from stdin, -o for output
    command = [
        compiler,
        "-std=c++17",
        f"-O{opt_level}",
        "-Wall",
        "-Wextra",
        "-o", str(output_binary),
        "-x", "c++",
        "-"  # Read from stdin
    ]
    
    try:
        # Run compiler with source code as input
        result = subprocess.run(
            command,
            input=source_code,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False  # Security: never use shell=True
        )
        
        success = (result.returncode == 0)
        binary_path = output_binary if success else None
        
        return CompilationResult(
            success=success,
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            binary_path=binary_path
        )
    
    except subprocess.TimeoutExpired:
        # Compilation took too long
        return CompilationResult(
            success=False,
            command=command,
            stdout="",
            stderr=f"Compilation timeout after {timeout} seconds",
            returncode=-1,
            binary_path=None
        )
    
    except FileNotFoundError:
        # Compiler not found
        return CompilationResult(
            success=False,
            command=command,
            stdout="",
            stderr=f"Compiler '{compiler}' not found",
            returncode=-1,
            binary_path=None
        )
    
    except Exception as e:
        # Other unexpected errors
        return CompilationResult(
            success=False,
            command=command,
            stdout="",
            stderr=f"Unexpected error: {str(e)}",
            returncode=-1,
            binary_path=None
        )


def execute_binary(
    binary_path: Path,
    x_value: int,
    timeout: int = 5
) -> ExecutionResult:
    """
    Execute a compiled binary with input value and parse output.
    
    Runs the binary with x_value as stdin input, captures output, and
    attempts to parse the result as an integer. Handles errors gracefully.
    
    Args:
        binary_path: Path to compiled binary
        x_value: Input value to provide as stdin (for variable x)
        timeout: Execution timeout in seconds (default: 5)
    
    Returns:
        ExecutionResult with success status and parsed output
    
    Raises:
        TypeError: If parameters have wrong types
        ValueError: If timeout is not positive
        FileNotFoundError: If binary doesn't exist
    
    Examples:
        >>> # Assuming binary prints input + 5
        >>> result = execute_binary(Path("./add5"), x_value=10)
        >>> result.output
        15
    """
    # Validate parameters
    if not isinstance(binary_path, Path):
        raise TypeError(f"binary_path must be Path, got {type(binary_path).__name__}")
    
    if not isinstance(x_value, int):
        raise TypeError(f"x_value must be int, got {type(x_value).__name__}")
    
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError(f"timeout must be positive int, got {timeout}")
    
    # Check binary exists
    if not binary_path.exists():
        raise FileNotFoundError(f"Binary not found: {binary_path}")
    
    # Prepare input (x_value as string with newline)
    input_str = f"{x_value}\n"
    
    try:
        # Run binary
        result = subprocess.run(
            [str(binary_path)],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False  # Security: never use shell=True
        )
        
        # Try to parse output
        output_value = None
        if result.returncode == 0:
            try:
                # Strip whitespace and parse as integer
                output_str = result.stdout.strip()
                output_value = int(output_str)
                success = True
            except ValueError:
                # Output isn't a valid integer
                success = False
        else:
            success = False
        
        return ExecutionResult(
            success=success,
            output=output_value,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode
        )
    
    except subprocess.TimeoutExpired:
        # Execution took too long
        return ExecutionResult(
            success=False,
            output=None,
            stdout="",
            stderr=f"Execution timeout after {timeout} seconds",
            returncode=-1
        )
    
    except Exception as e:
        # Other unexpected errors
        return ExecutionResult(
            success=False,
            output=None,
            stdout="",
            stderr=f"Unexpected error: {str(e)}",
            returncode=-1
        )


def create_output_directory(base_dir: Path = None) -> Path:
    """
    Create output directory for generated files.
    
    Args:
        base_dir: Base directory (default: current working directory)
    
    Returns:
        Path to output directory
    """
    if base_dir is None:
        base_dir = Path.cwd()
    
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return output_dir
