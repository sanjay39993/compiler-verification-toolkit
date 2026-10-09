"""
Random Expression Generator

Generates random AST expressions with configurable constraints for differential
testing. Uses fixed seeds for reproducibility.
"""

import random
from typing import List
from src.ast_nodes import Expr, Const, Var, BinOp


# Supported operators
OPERATORS: List[str] = ['+', '-', '*']


def generate_random_expr(
    seed: int,
    max_depth: int = 4,
    max_const: int = 1000,
    var_probability: float = 0.3
) -> Expr:
    """
    Generate a random AST expression with fixed seed for reproducibility.
    
    The generator creates bounded random expressions suitable for differential
    testing. All parameters are validated, and the same seed always produces
    the same expression.
    
    Depth semantics:
    - depth 0: Only leaf nodes (Const or Var)
    - depth > 0: May generate BinOp with children at depth-1
    - No path in the tree exceeds max_depth
    
    Args:
        seed: Random seed for reproducibility (must be non-negative)
        max_depth: Maximum tree depth (0 = leaves only, must be >= 0)
        max_const: Maximum constant value, constants in [0, max_const] (must be > 0)
        var_probability: Probability of Var vs Const at leaves, in [0.0, 1.0]
    
    Returns:
        Random Expr (Const, Var, or BinOp tree)
    
    Raises:
        ValueError: If parameters are out of valid range
        TypeError: If parameters have wrong type
    
    Examples:
        >>> expr1 = generate_random_expr(seed=42, max_depth=2)
        >>> expr2 = generate_random_expr(seed=42, max_depth=2)
        >>> expr1 == expr2  # Same seed produces same expression
        True
        >>> expr3 = generate_random_expr(seed=43, max_depth=2)
        >>> expr1 == expr3  # Different seed produces different expression
        False
    """
    # Validate parameters
    if not isinstance(seed, int):
        raise TypeError(f"seed must be int, got {type(seed).__name__}")
    if seed < 0:
        raise ValueError(f"seed must be non-negative, got {seed}")
    
    if not isinstance(max_depth, int):
        raise TypeError(f"max_depth must be int, got {type(max_depth).__name__}")
    if max_depth < 0:
        raise ValueError(f"max_depth must be >= 0, got {max_depth}")
    
    if not isinstance(max_const, int):
        raise TypeError(f"max_const must be int, got {type(max_const).__name__}")
    if max_const <= 0:
        raise ValueError(f"max_const must be > 0, got {max_const}")
    
    if not isinstance(var_probability, (int, float)):
        raise TypeError(f"var_probability must be float, got {type(var_probability).__name__}")
    if not (0.0 <= var_probability <= 1.0):
        raise ValueError(f"var_probability must be in [0.0, 1.0], got {var_probability}")
    
    # Create local random generator (doesn't affect global state)
    rng = random.Random(seed)
    
    def _generate(current_depth: int) -> Expr:
        """
        Recursively generate expression at given depth.
        
        Args:
            current_depth: Remaining depth (0 = leaf only)
        
        Returns:
            Generated expression
        """
        # At depth 0, must generate leaf
        if current_depth == 0:
            return _generate_leaf(rng, max_const, var_probability)
        
        # At depth > 0, can generate leaf or BinOp
        # Use 50% probability to generate BinOp (could be parameterized)
        if rng.random() < 0.5:
            # Generate BinOp with children at depth-1
            op = rng.choice(OPERATORS)
            left = _generate(current_depth - 1)
            right = _generate(current_depth - 1)
            return BinOp(op, left, right)
        else:
            # Generate leaf
            return _generate_leaf(rng, max_const, var_probability)
    
    return _generate(max_depth)


def _generate_leaf(
    rng: random.Random,
    max_const: int,
    var_probability: float
) -> Expr:
    """
    Generate a leaf node (Const or Var).
    
    Args:
        rng: Random number generator
        max_const: Maximum constant value
        var_probability: Probability of generating Var
    
    Returns:
        Const or Var node
    """
    # Decide whether to generate Var or Const
    if rng.random() < var_probability:
        return Var('x')
    else:
        # Generate constant in range [0, max_const]
        value = rng.randint(0, max_const)
        return Const(value)
