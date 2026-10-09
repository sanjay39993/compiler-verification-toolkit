# AST-Based Compiler Verification & Differential Testing Toolkit

An educational toolkit demonstrating compiler verification concepts through differential testing of C++ code generation. This project compares a Python reference implementation (oracle) against compiled C++ code across multiple optimization levels to detect discrepancies.

## 🎯 Project Objective

This toolkit is designed for learning and demonstrating:
- **Differential testing** as a verification technique
- **AST-based code generation** and transformation
- **Reference implementation patterns** (Python oracle vs. C++ compiled)
- **Compiler optimization testing** across `-O0`, `-O1`, `-O2`, `-O3`
- **Reproducible test case generation** using fixed random seeds

**Important**: This is an educational project. Any detected discrepancies require thorough investigation to determine if they result from test infrastructure bugs, implementation errors, or (rarely) actual compiler issues. We never automatically claim compiler bugs without independent verification.

## 🏗️ Architecture

The toolkit consists of six main modules:

### 1. AST Nodes (`src/ast_nodes.py`)
Defines immutable abstract syntax tree nodes:
- `Const(value)` - Integer constants
- `Var('x')` - Runtime variable
- `BinOp(op, left, right)` - Binary operations (`+`, `-`, `*`)

All nodes are immutable dataclasses using `@dataclass(frozen=True)`.

### 2. Python Oracle (`src/python_interpreter.py`)
Reference implementation that evaluates AST expressions:
- Applies **32-bit unsigned semantics** via `mask32(value & 0xFFFFFFFF)`
- Masks after **every** arithmetic operation to match C++ `uint32_t` behavior
- Handles overflow (wraps to 0) and underflow (wraps to 0xFFFFFFFF)

**Critical**: The oracle is the ground truth. It independently implements wraparound semantics without relying on C++ behavior.

### 3. C++ Code Generator (`src/cpp_codegen.py`)
Translates AST expressions to C++17 programs:
- Uses `uint32_t` exclusively for defined wraparound behavior
- Generates complete programs with input/output
- Normalizes constants to 32-bit range before emission
- Parenthesizes operations to preserve AST structure

### 4. Expression Generator (`src/expression_generator.py`)
Creates random bounded expressions:
- **Reproducible**: Same seed always produces same expression
- **Configurable depth**: Control expression complexity
- **Bounded constants**: Range `[0, max_const]`
- **Variable probability**: Control `Var` vs `Const` ratio
- Uses local random state (doesn't affect global `random` module)

### 5. Compiler Runner (`src/compiler_runner.py`)
Handles C++ compilation and execution:
- Compiles with G++ using `subprocess.run(shell=False)` for security
- Supports optimization levels: `-O0`, `-O1`, `-O2`, `-O3`
- Captures stdout, stderr, and return codes
- Distinguishes compilation failures from execution failures
- Timeout handling for both compilation and execution

### 6. Differential Tester (`src/differential_tester.py`)
Orchestrates end-to-end testing:
- Generates random expressions with fixed seeds
- Evaluates with Python oracle
- Compiles C++ code at multiple optimization levels
- Compares results and categorizes outcomes:
  - **Successful**: All results match oracle
  - **Compilation failure**: C++ didn't compile (infrastructure issue)
  - **Execution failure**: Binary crashed or timed out
  - **Discrepancy**: Results don't match (requires investigation)

## 🔢 32-Bit Unsigned Arithmetic

The toolkit implements unsigned 32-bit integer semantics matching C++'s `uint32_t`:

- **Range**: `[0, 4294967295]` (0 to 2³²-1)
- **Overflow**: `0xFFFFFFFF + 1 = 0`
- **Underflow**: `0 - 1 = 0xFFFFFFFF`
- **Wraparound**: All arithmetic wraps modulo 2³²

**Python oracle**:
```python
def mask32(value):
    return value & 0xFFFFFFFF

result = mask32(mask32(a) + mask32(b))  # Mask after every operation
```

**C++ implementation**:
```cpp
uint32_t result = a + b;  // Wraparound is defined for unsigned types
```

## 🧪 Optimization Level Testing

The toolkit tests across four optimization levels:

| Level | Description | Purpose |
|-------|-------------|---------|
| `-O0` | No optimization | Baseline correctness verification |
| `-O1` | Basic optimization | Light optimization testing |
| `-O2` | Moderate optimization | Common production optimization |
| `-O3` | Aggressive optimization | Maximum optimization testing |

A well-functioning compiler should produce identical results across all optimization levels for our expressions, which avoid undefined behavior.

## 📦 Installation & Prerequisites

### Requirements
- **Python**: 3.10+ (developed with 3.12.3)
- **G++**: 13+ with C++17 support (any modern GCC)
- **pytest**: 8.0+ (for running tests)
- **OS**: Linux, macOS, or WSL 2 on Windows

### Setup
```bash
# Clone or navigate to project directory
cd compiler-verification-toolkit

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install pytest

# Verify installation
python --version
g++ --version
pytest --version
```

## 🧪 Running Tests

### Run Full Test Suite
```bash
# All tests (203 tests, may take 1-2 minutes due to C++ compilation)
python -m pytest tests/ -v

# Quick test (no real compilation)
python -m pytest tests/ -v -k "not Integration"

# Specific module tests
python -m pytest tests/test_ast_nodes.py -v
python -m pytest tests/test_python_interpreter.py -v
python -m pytest tests/test_cpp_codegen.py -v
```

### Test Count by Stage
- Stage 1 (AST Nodes): 38 tests
- Stage 2 (Python Interpreter): 54 tests
- Stage 3 (C++ Code Generator): 42 tests
- Stage 4 (Expression Generator): 39 tests
- Stage 5 (Compiler Runner): 30 tests
- Stage 6 (Differential Tester): 23 tests

**Total: 226 tests**

## 🚀 Running Differential Tests

### Quick Example (Python API)
```python
from pathlib import Path
from src.differential_tester import run_differential_test, print_summary

# Run small test campaign
summary = run_differential_test(
    num_tests=10,           # Generate 10 random expressions
    seed_start=0,           # Start from seed 0
    opt_levels=[0, 2],      # Test -O0 and -O2
    x_values=[0, 5, 100],   # Test with 3 input values
    max_depth=3,            # Expression depth
    output_dir=Path("./output")
)

# Display results
print_summary(summary)
```

### Command-Line Interface
```bash
# Small test (30 total: 10 expressions × 3 x-values)
python -m src.cli --num-tests 10 --seed 0

# Medium test with specific optimization levels
python -m src.cli --num-tests 50 --seed 42 --opt-levels 0 2 3

# Larger campaign (save results)
python -m src.cli --num-tests 100 --seed 0 --output-dir ./results

# Full options
python -m src.cli \
    --num-tests 100 \
    --seed 42 \
    --opt-levels 0 1 2 3 \
    --x-values 0 1 10 100 4294967295 \
    --max-depth 4 \
    --max-const 1000 \
    --output-dir ./output \
    --keep-files
```

### CLI Options
- `--num-tests N`: Number of random expressions to generate (default: 100)
- `--seed N`: Starting seed for reproducibility (default: 0)
- `--opt-levels L1 L2 ...`: Optimization levels to test (default: 0 1 2 3)
- `--x-values V1 V2 ...`: Runtime input values (default: 0 1 5 100 0xFFFFFFFF)
- `--max-depth D`: Maximum expression depth (default: 4)
- `--max-const C`: Maximum constant value (default: 1000)
- `--output-dir PATH`: Directory for generated files (default: temp)
- `--keep-files`: Keep generated C++ files and binaries
- `--save-summary PATH`: Save JSON summary to file

## 📊 Interpreting Results

### Successful Test
```
Total tests:             100
Successful:              100
Compilation failures:    0
Execution failures:      0
Discrepancies found:     0

✅ No discrepancies found!
All compiled results matched the Python oracle.
```

### Compilation Failure
**Not a compiler bug** - Indicates an issue with our C++ code generation:
```
Compilation failures:    5
```
**Action**: Review generated C++ code for syntax errors or invalid constructs.

### Execution Failure
**Not a result mismatch** - Binary crashed or timed out:
```
Execution failures:      3
```
**Action**: Check for infinite loops, segfaults, or timeout issues.

### Discrepancy Detected
**Requires investigation**:
```
Discrepancies found:     1

⚠️  DISCREPANCIES DETECTED - REQUIRES INVESTIGATION
Discrepancy #1:
  Seed: 42
  Expression: BinOp('+', Var('x'), Const(5))
  x_value: 10
  Expected (oracle): 15
  Results by optimization level:
    -O0: 15 ✓
    -O1: 15 ✓
    -O2: 16 ✗
    -O3: 16 ✗
```

**Investigation steps**:
1. **Verify reproducibility**: Run again with same seed and x_value
2. **Check oracle**: Manually calculate expected result
3. **Inspect C++ code**: Review generated source for errors
4. **Test manually**: Compile and run C++ by hand
5. **Compare optimizations**: Does `-O0` match oracle?
6. **Check for undefined behavior**: Our generator shouldn't produce any
7. **Only then**: Consider if this might be a compiler issue

**Never claim a compiler bug without thorough verification!**

## 🔍 Reproducibility

All test cases are fully reproducible:
```python
# Same seed produces same expression
expr1 = generate_random_expr(seed=42, max_depth=3)
expr2 = generate_random_expr(seed=42, max_depth=3)
assert expr1 == expr2  # Always true

# Discrepancies can be reproduced
summary = run_differential_test(num_tests=1, seed_start=42)
# If discrepancy found, re-run with same seed to reproduce
```

Saved information for each discrepancy:
- Random seed used
- Expression AST
- Input value `x`
- Expected result (oracle)
- Actual results per optimization level
- Generated C++ source code

## 📁 Project Structure

```
compiler-verification-toolkit/
├── src/
│   ├── __init__.py
│   ├── ast_nodes.py              # AST definitions
│   ├── python_interpreter.py     # Python oracle
│   ├── cpp_codegen.py            # C++ code generator
│   ├── expression_generator.py   # Random expression generator
│   ├── compiler_runner.py        # G++ compilation & execution
│   ├── differential_tester.py    # Main testing orchestrator
│   └── cli.py                    # Command-line interface
│
├── tests/
│   ├── __init__.py
│   ├── test_ast_nodes.py
│   ├── test_python_interpreter.py
│   ├── test_cpp_codegen.py
│   ├── test_expression_generator.py
│   ├── test_compiler_runner.py
│   └── test_differential_tester.py
│
├── output/                       # Generated files (created automatically)
│   ├── generated/                # C++ source files
│   ├── compiled/                 # Compiled binaries
│   └── logs/                     # Test summaries
│
├── README.md                     # This file
├── .venv/                        # Python virtual environment
└── .vscode/                      # VS Code settings
```

## 🎓 Demonstrating in an Internship Interview

### Quick Demo Script (5 minutes)

1. **Introduction** (30 seconds):
   ```
   "I built a compiler verification toolkit that uses differential testing
   to compare a Python reference implementation against compiled C++ code
   across multiple optimization levels."
   ```

2. **Show the concept** (1 minute):
   ```python
   # Simple example
   from src.ast_nodes import *
   from src.python_interpreter import evaluate
   from src.cpp_codegen import generate_cpp
   
   # Create expression: x + 5
   expr = BinOp('+', Var('x'), Const(5))
   
   # Python oracle
   result = evaluate(expr, x_value=10)  # Returns 15
   
   # Generate C++
   cpp_code = generate_cpp(expr)
   print(cpp_code)
   ```

3. **Run live test** (2 minutes):
   ```bash
   # Quick differential test
   python -m src.cli --num-tests 10 --seed 0
   ```

4. **Explain architecture** (1 minute):
   - Show modular design (6 stages)
   - Explain oracle vs. compiled comparison
   - Mention 32-bit unsigned semantics
   - Highlight reproducibility

5. **Discuss technical decisions** (30 seconds):
   - Why immutable ASTs
   - Why mask after every operation
   - Why test multiple optimization levels
   - How we avoid false positives

### Key Points to Emphasize

✅ **Engineering practices**:
- Test-driven development (226 tests)
- Modular architecture (clear separation of concerns)
- Type hints and documentation
- Error handling and validation

✅ **Computer science concepts**:
- Abstract syntax trees
- Interpreter design
- Code generation
- Compiler optimization
- Differential testing methodology

✅ **Problem-solving approach**:
- Started with simple immutable AST nodes
- Built oracle with correct semantics first
- Added code generation with proper type handling
- Integrated everything into differential tester
- Never claims bugs without verification

✅ **Production-ready practices**:
- Comprehensive test coverage
- Clear documentation
- CLI for easy use
- Reproducible results
- Conservative bug reporting

### Example Interview Questions You Can Answer

**Q**: "How do you ensure the Python oracle is correct?"
- Extensive unit tests with known values
- Test overflow/underflow explicitly
- Compare with manual calculations
- Test against hand-written C++ programs

**Q**: "What happens if you find a discrepancy?"
- Check reproducibility first
- Verify oracle is correct
- Inspect generated C++ code
- Test manually with different compilers
- Only claim compiler bug after exhaustive verification

**Q**: "Why use differential testing instead of formal methods?"
- Complementary approach
- Easier to implement
- Finds real-world issues
- Scales to complex code
- Practical for education

**Q**: "How would you extend this project?"
- Add more operators (division, modulo, bitwise)
- Support signed integers
- Add floating-point testing
- Test multiple compilers (GCC, Clang, MSVC)
- Implement automatic test-case reduction

## 🚧 Limitations & Future Work

### Current Limitations
- Only supports `+`, `-`, `*` operators
- Single variable `x` only
- No division (avoids divide-by-zero complexity)
- No shift operators (avoids undefined behavior)
- No pointer arithmetic

### Potential Extensions
- **More operators**: Division with zero checks, modulo, bitwise operations
- **Multiple variables**: Support `x`, `y`, `z`
- **Control flow**: If-then-else expressions
- **Type system**: Add support for different integer types
- **Multi-compiler testing**: Test GCC, Clang, MSVC simultaneously
- **Automatic reduction**: Minimize failing test cases
- **Coverage-guided generation**: Generate expressions targeting specific code patterns

## 📚 References

- **Differential Testing**: McKeeman, W.M. (1998). "Differential Testing for Software"
- **Compiler Testing**: Yang et al. (2011). "Finding and Understanding Bugs in C Compilers"
- **EMI Testing**: Le et al. (2014). "Compiler Validation via Equivalence Modulo Inputs"
- **C++ Standard**: ISO/IEC 14882:2017 (C++17) - Unsigned arithmetic semantics

## 📄 License

Educational project for learning compiler verification concepts.

## 👤 Author

Developed as a learning project demonstrating:
- Software engineering practices
- Compiler verification techniques  
- Differential testing methodology
- Test-driven development
- Modular architecture design
