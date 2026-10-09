"""
AST Node Definitions

Immutable abstract syntax tree nodes for representing arithmetic expressions.
Supports constants, variables, and binary operations.
"""

from dataclasses import dataclass
from typing import Union


class Expr:
    """Base class for all AST expression nodes"""
    pass


@dataclass(frozen=True)
class Const(Expr):
    """
    Integer constant node.
    
    Example:
        Const(42) represents the constant value 42
    """
    value: int
    
    def __post_init__(self):
        if not isinstance(self.value, int):
            raise TypeError(f"Const value must be int, got {type(self.value).__name__}")
    
    def __repr__(self) -> str:
        return f"Const({self.value})"


@dataclass(frozen=True)
class Var(Expr):
    """
    Runtime variable node.
    
    Only supports the variable name 'x' as the runtime input variable.
    
    Example:
        Var('x') represents the runtime variable x
    """
    name: str
    
    def __post_init__(self):
        if not isinstance(self.name, str):
            raise TypeError(f"Var name must be str, got {type(self.name).__name__}")
        if self.name != 'x':
            raise ValueError(f"Var name must be 'x', got '{self.name}'")
    
    def __repr__(self) -> str:
        return f"Var('{self.name}')"


@dataclass(frozen=True)
class BinOp(Expr):
    """
    Binary operation node.
    
    Supports only +, -, and * operations.
    Both operands must be valid Expr nodes.
    
    Example:
        BinOp('+', Const(2), Const(3)) represents (2 + 3)
        BinOp('*', Var('x'), Const(5)) represents (x * 5)
    """
    op: str
    left: Expr
    right: Expr
    
    def __post_init__(self):
        # Validate operator
        if not isinstance(self.op, str):
            raise TypeError(f"BinOp operator must be str, got {type(self.op).__name__}")
        if self.op not in ('+', '-', '*'):
            raise ValueError(f"BinOp operator must be '+', '-', or '*', got '{self.op}'")
        
        # Validate operands
        if not isinstance(self.left, Expr):
            raise TypeError(f"BinOp left operand must be Expr, got {type(self.left).__name__}")
        if not isinstance(self.right, Expr):
            raise TypeError(f"BinOp right operand must be Expr, got {type(self.right).__name__}")
    
    def __repr__(self) -> str:
        return f"BinOp('{self.op}', {repr(self.left)}, {repr(self.right)})"
