"""
Python Oracle Interpreter

Reference implementation that evaluates AST expressions with 32-bit unsigned
integer semantics. This serves as the oracle (ground truth) for differential
testing against compiled C++ code.

Critical: Apply 32-bit masking after EVERY arithmetic operation to match
uint32_t wraparound behavior in C++.
"""

from src.ast_nodes import Expr, Const, Var, BinOp


def mask32(value: int) -> int:
    """
    Apply 32-bit unsigned mask to ensure result fits in uint32_t range.
    
    This ensures Python's arbitrary-precision integers behave like C++'s
    uint32_t with defined wraparound on overflow/underflow.
    
    Args:
        value: Python integer (can be negative or > 2^32)
    
    Returns:
        Value masked to [0, 2^32-1] range
    
    Examples:
        >>> mask32(42)
        42
        >>> mask32(0xFFFFFFFF)
        4294967295
        >>> mask32(0x100000000)  # 2^32
        0
        >>> mask32(-1)
        4294967295
    """
    return value & 0xFFFFFFFF


def evaluate(expr: Expr, x_value: int) -> int:
    """
    Evaluate an AST expression with 32-bit unsigned semantics.
    
    This function recursively evaluates the expression tree, applying 32-bit
    masking after every arithmetic operation to match C++ uint32_t behavior.
    
    Args:
        expr: AST expression to evaluate
        x_value: Value to substitute for variable 'x'
    
    Returns:
        32-bit unsigned integer result [0, 2^32-1]
    
    Raises:
        TypeError: If expr is not a valid Expr node
        ValueError: If expr contains unsupported operations
    
    Examples:
        >>> evaluate(Const(42), x_value=0)
        42
        >>> evaluate(Var('x'), x_value=100)
        100
        >>> evaluate(BinOp('+', Const(10), Const(20)), x_value=0)
        30
        >>> evaluate(BinOp('+', Const(0xFFFFFFFF), Const(1)), x_value=0)
        0
    """
    if not isinstance(expr, Expr):
        raise TypeError(f"Expected Expr node, got {type(expr).__name__}")
    
    if isinstance(expr, Const):
        # Apply mask to constant value
        return mask32(expr.value)
    
    elif isinstance(expr, Var):
        # Apply mask to variable value
        if expr.name != 'x':
            raise ValueError(f"Unsupported variable name: {expr.name}")
        return mask32(x_value)
    
    elif isinstance(expr, BinOp):
        # Recursively evaluate operands (which applies masking to them)
        left_val = evaluate(expr.left, x_value)
        right_val = evaluate(expr.right, x_value)
        
        # Perform operation and apply mask to result
        if expr.op == '+':
            result = left_val + right_val
        elif expr.op == '-':
            result = left_val - right_val
        elif expr.op == '*':
            result = left_val * right_val
        else:
            raise ValueError(f"Unsupported operator: {expr.op}")
        
        # Critical: Apply mask to operation result
        return mask32(result)
    
    else:
        raise TypeError(f"Unsupported expression type: {type(expr).__name__}")
