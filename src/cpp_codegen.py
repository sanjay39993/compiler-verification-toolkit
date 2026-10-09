"""
C++ Code Generator

Translates AST expressions into valid C++17 programs using uint32_t for
32-bit unsigned integer semantics. Generated programs read a runtime input
variable x, evaluate the expression, and output the result.
"""

from src.ast_nodes import Expr, Const, Var, BinOp
from src.python_interpreter import mask32


def expr_to_cpp(expr: Expr) -> str:
    """
    Convert an AST expression to a C++ expression string.
    
    Uses uint32_t semantics with proper parenthesization and unsigned literals.
    Constants are normalized to 32-bit range before emission to ensure they
    match the Python oracle's semantics.
    
    Args:
        expr: AST expression node to convert
    
    Returns:
        C++ expression string
    
    Raises:
        TypeError: If expr is not a valid Expr node
        ValueError: If expr contains unsupported operations
    
    Examples:
        >>> expr_to_cpp(Const(42))
        '42u'
        >>> expr_to_cpp(Var('x'))
        'x'
        >>> expr_to_cpp(BinOp('+', Const(10), Const(20)))
        '(10u + 20u)'
    """
    if not isinstance(expr, Expr):
        raise TypeError(f"Expected Expr node, got {type(expr).__name__}")
    
    if isinstance(expr, Const):
        # Normalize constant to 32-bit range to match oracle semantics
        # This handles negative and oversized constants correctly
        normalized_value = mask32(expr.value)
        return f"{normalized_value}u"
    
    elif isinstance(expr, Var):
        if expr.name != 'x':
            raise ValueError(f"Unsupported variable name: {expr.name}")
        return "x"
    
    elif isinstance(expr, BinOp):
        # Recursively convert operands
        left_cpp = expr_to_cpp(expr.left)
        right_cpp = expr_to_cpp(expr.right)
        
        # Map operator (all three are the same in C++)
        if expr.op not in ('+', '-', '*'):
            raise ValueError(f"Unsupported operator: {expr.op}")
        
        # Parenthesize to preserve AST evaluation order
        return f"({left_cpp} {expr.op} {right_cpp})"
    
    else:
        raise TypeError(f"Unsupported expression type: {type(expr).__name__}")


def generate_cpp(expr: Expr, input_var: str = 'x') -> str:
    """
    Generate a complete C++17 program from an AST expression.
    
    The generated program:
    1. Includes necessary headers (<iostream>, <cstdint>)
    2. Declares main() function
    3. Reads uint32_t input variable from stdin
    4. Evaluates the expression using uint32_t arithmetic
    5. Prints the result to stdout
    6. Returns 0
    
    Args:
        expr: AST expression to evaluate
        input_var: Name of the input variable (default: 'x')
    
    Returns:
        Complete C++17 program as a string
    
    Raises:
        TypeError: If expr is not a valid Expr node
        ValueError: If expr contains unsupported operations or variables
    
    Examples:
        >>> prog = generate_cpp(Const(42))
        >>> 'uint32_t result = 42u;' in prog
        True
        >>> '#include <cstdint>' in prog
        True
    """
    if not isinstance(expr, Expr):
        raise TypeError(f"Expected Expr node, got {type(expr).__name__}")
    
    if input_var != 'x':
        raise ValueError(f"Only input variable 'x' is supported, got '{input_var}'")
    
    # Convert expression to C++
    cpp_expr = expr_to_cpp(expr)
    
    # Generate complete program
    program = f"""#include <iostream>
#include <cstdint>

int main() {{
    uint32_t x;
    std::cin >> x;
    uint32_t result = {cpp_expr};
    std::cout << result << std::endl;
    return 0;
}}
"""
    
    return program
