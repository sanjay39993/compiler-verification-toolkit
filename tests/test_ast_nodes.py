"""
Unit tests for AST node definitions

Tests construction, immutability, equality, validation, and representation
of Const, Var, and BinOp nodes.
"""

import pytest
from src.ast_nodes import Expr, Const, Var, BinOp


class TestConst:
    """Tests for Const node"""
    
    def test_create_const(self):
        """Test creating a constant node"""
        c = Const(42)
        assert c.value == 42
        assert isinstance(c, Expr)
    
    def test_create_const_zero(self):
        """Test creating a constant with value 0"""
        c = Const(0)
        assert c.value == 0
    
    def test_create_const_negative(self):
        """Test creating a constant with negative value"""
        c = Const(-100)
        assert c.value == -100
    
    def test_create_const_large(self):
        """Test creating a constant with large value"""
        c = Const(0xFFFFFFFF)
        assert c.value == 0xFFFFFFFF
    
    def test_const_repr(self):
        """Test Const has readable representation"""
        c = Const(42)
        assert repr(c) == "Const(42)"
        assert str(c) == "Const(42)"
    
    def test_const_equality(self):
        """Test two Const nodes with same value are equal"""
        c1 = Const(42)
        c2 = Const(42)
        assert c1 == c2
        assert c1 is not c2  # Different objects
    
    def test_const_inequality(self):
        """Test two Const nodes with different values are not equal"""
        c1 = Const(42)
        c2 = Const(43)
        assert c1 != c2
    
    def test_const_immutable(self):
        """Test Const node is immutable"""
        c = Const(42)
        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            c.value = 100
    
    def test_const_invalid_type(self):
        """Test Const rejects non-integer values"""
        with pytest.raises(TypeError, match="Const value must be int"):
            Const("42")
        with pytest.raises(TypeError, match="Const value must be int"):
            Const(3.14)
        with pytest.raises(TypeError, match="Const value must be int"):
            Const(None)


class TestVar:
    """Tests for Var node"""
    
    def test_create_var(self):
        """Test creating a variable node"""
        v = Var('x')
        assert v.name == 'x'
        assert isinstance(v, Expr)
    
    def test_var_repr(self):
        """Test Var has readable representation"""
        v = Var('x')
        assert repr(v) == "Var('x')"
        assert str(v) == "Var('x')"
    
    def test_var_equality(self):
        """Test two Var nodes with same name are equal"""
        v1 = Var('x')
        v2 = Var('x')
        assert v1 == v2
        assert v1 is not v2  # Different objects
    
    def test_var_immutable(self):
        """Test Var node is immutable"""
        v = Var('x')
        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            v.name = 'y'
    
    def test_var_invalid_name(self):
        """Test Var rejects names other than 'x'"""
        with pytest.raises(ValueError, match="Var name must be 'x'"):
            Var('y')
        with pytest.raises(ValueError, match="Var name must be 'x'"):
            Var('a')
        with pytest.raises(ValueError, match="Var name must be 'x'"):
            Var('X')  # Case sensitive
        with pytest.raises(ValueError, match="Var name must be 'x'"):
            Var('')
    
    def test_var_invalid_type(self):
        """Test Var rejects non-string names"""
        with pytest.raises(TypeError, match="Var name must be str"):
            Var(42)
        with pytest.raises(TypeError, match="Var name must be str"):
            Var(None)


class TestBinOp:
    """Tests for BinOp node"""
    
    def test_create_binop_add(self):
        """Test creating addition operation"""
        left = Const(10)
        right = Const(20)
        op = BinOp('+', left, right)
        assert op.op == '+'
        assert op.left == left
        assert op.right == right
        assert isinstance(op, Expr)
    
    def test_create_binop_sub(self):
        """Test creating subtraction operation"""
        left = Const(20)
        right = Const(10)
        op = BinOp('-', left, right)
        assert op.op == '-'
        assert op.left == left
        assert op.right == right
    
    def test_create_binop_mul(self):
        """Test creating multiplication operation"""
        left = Const(3)
        right = Const(4)
        op = BinOp('*', left, right)
        assert op.op == '*'
        assert op.left == left
        assert op.right == right
    
    def test_binop_with_var(self):
        """Test BinOp with variable operand"""
        op = BinOp('+', Var('x'), Const(5))
        assert op.left == Var('x')
        assert op.right == Const(5)
    
    def test_binop_repr(self):
        """Test BinOp has readable representation"""
        op = BinOp('+', Const(1), Const(2))
        assert repr(op) == "BinOp('+', Const(1), Const(2))"
        assert str(op) == "BinOp('+', Const(1), Const(2))"
    
    def test_binop_equality(self):
        """Test two BinOp nodes with same structure are equal"""
        op1 = BinOp('+', Const(1), Const(2))
        op2 = BinOp('+', Const(1), Const(2))
        assert op1 == op2
        assert op1 is not op2  # Different objects
    
    def test_binop_inequality_operator(self):
        """Test BinOp nodes with different operators are not equal"""
        op1 = BinOp('+', Const(1), Const(2))
        op2 = BinOp('-', Const(1), Const(2))
        assert op1 != op2
    
    def test_binop_inequality_operands(self):
        """Test BinOp nodes with different operands are not equal"""
        op1 = BinOp('+', Const(1), Const(2))
        op2 = BinOp('+', Const(1), Const(3))
        assert op1 != op2
    
    def test_binop_immutable(self):
        """Test BinOp node is immutable"""
        op = BinOp('+', Const(1), Const(2))
        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            op.op = '-'
        with pytest.raises(Exception):
            op.left = Const(5)
        with pytest.raises(Exception):
            op.right = Const(10)
    
    def test_binop_invalid_operator(self):
        """Test BinOp rejects invalid operators"""
        with pytest.raises(ValueError, match="BinOp operator must be"):
            BinOp('/', Const(1), Const(2))
        with pytest.raises(ValueError, match="BinOp operator must be"):
            BinOp('%', Const(1), Const(2))
        with pytest.raises(ValueError, match="BinOp operator must be"):
            BinOp('&', Const(1), Const(2))
        with pytest.raises(ValueError, match="BinOp operator must be"):
            BinOp('**', Const(1), Const(2))
        with pytest.raises(ValueError, match="BinOp operator must be"):
            BinOp('add', Const(1), Const(2))
    
    def test_binop_invalid_operator_type(self):
        """Test BinOp rejects non-string operators"""
        with pytest.raises(TypeError, match="BinOp operator must be str"):
            BinOp(1, Const(1), Const(2))
        with pytest.raises(TypeError, match="BinOp operator must be str"):
            BinOp(None, Const(1), Const(2))
    
    def test_binop_invalid_left_operand(self):
        """Test BinOp rejects invalid left operand"""
        with pytest.raises(TypeError, match="BinOp left operand must be Expr"):
            BinOp('+', 42, Const(2))
        with pytest.raises(TypeError, match="BinOp left operand must be Expr"):
            BinOp('+', "x", Const(2))
        with pytest.raises(TypeError, match="BinOp left operand must be Expr"):
            BinOp('+', None, Const(2))
    
    def test_binop_invalid_right_operand(self):
        """Test BinOp rejects invalid right operand"""
        with pytest.raises(TypeError, match="BinOp right operand must be Expr"):
            BinOp('+', Const(1), 42)
        with pytest.raises(TypeError, match="BinOp right operand must be Expr"):
            BinOp('+', Const(1), "2")
        with pytest.raises(TypeError, match="BinOp right operand must be Expr"):
            BinOp('+', Const(1), None)


class TestNestedExpressions:
    """Tests for nested and complex expressions"""
    
    def test_nested_binop(self):
        """Test creating nested binary operations"""
        # (2 + 3) * 4
        inner = BinOp('+', Const(2), Const(3))
        outer = BinOp('*', inner, Const(4))
        
        assert outer.op == '*'
        assert outer.left == inner
        assert outer.right == Const(4)
        assert outer.left.op == '+'
        assert outer.left.left == Const(2)
        assert outer.left.right == Const(3)
    
    def test_deeply_nested(self):
        """Test deeply nested expressions"""
        # ((x + 1) * 2) - 3
        level1 = BinOp('+', Var('x'), Const(1))
        level2 = BinOp('*', level1, Const(2))
        level3 = BinOp('-', level2, Const(3))
        
        assert level3.op == '-'
        assert level3.left.op == '*'
        assert level3.left.left.op == '+'
        assert level3.left.left.left == Var('x')
    
    def test_nested_repr(self):
        """Test nested expression has readable representation"""
        # (2 + 3) * 4
        inner = BinOp('+', Const(2), Const(3))
        outer = BinOp('*', inner, Const(4))
        expected = "BinOp('*', BinOp('+', Const(2), Const(3)), Const(4))"
        assert repr(outer) == expected
    
    def test_nested_equality(self):
        """Test nested expressions with same structure are equal"""
        # (x + 5) * (x - 3)
        expr1 = BinOp('*', 
                     BinOp('+', Var('x'), Const(5)),
                     BinOp('-', Var('x'), Const(3)))
        expr2 = BinOp('*', 
                     BinOp('+', Var('x'), Const(5)),
                     BinOp('-', Var('x'), Const(3)))
        assert expr1 == expr2
    
    def test_nested_immutability(self):
        """Test nested expressions are fully immutable"""
        inner = BinOp('+', Const(2), Const(3))
        outer = BinOp('*', inner, Const(4))
        
        # Cannot modify outer
        with pytest.raises(Exception):
            outer.left = Const(10)
        
        # Cannot modify inner through outer
        with pytest.raises(Exception):
            outer.left.left = Const(10)
    
    def test_complex_expression(self):
        """Test complex realistic expression"""
        # (x * 2) + ((100 - x) * 3)
        left_side = BinOp('*', Var('x'), Const(2))
        right_inner = BinOp('-', Const(100), Var('x'))
        right_side = BinOp('*', right_inner, Const(3))
        full_expr = BinOp('+', left_side, right_side)
        
        # Verify structure
        assert full_expr.op == '+'
        assert full_expr.left.op == '*'
        assert full_expr.left.left == Var('x')
        assert full_expr.right.op == '*'
        assert full_expr.right.left.op == '-'
        
        # Verify it's all immutable
        assert isinstance(full_expr, Expr)
        with pytest.raises(Exception):
            full_expr.op = '-'


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_same_node_reused(self):
        """Test that the same node can be reused in multiple places"""
        const_x = Var('x')
        # x + x
        expr = BinOp('+', const_x, const_x)
        assert expr.left is expr.right  # Same object reference
        assert expr.left == expr.right  # Equal
    
    def test_mixed_operators(self):
        """Test expression with all three operators"""
        # (x + 5) - (x * 2)
        left = BinOp('+', Var('x'), Const(5))
        right = BinOp('*', Var('x'), Const(2))
        expr = BinOp('-', left, right)
        
        assert expr.op == '-'
        assert expr.left.op == '+'
        assert expr.right.op == '*'
    
    def test_large_constants(self):
        """Test with very large constant values"""
        c1 = Const(0xFFFFFFFF)
        c2 = Const(2**31 - 1)
        expr = BinOp('+', c1, c2)
        
        assert expr.left.value == 0xFFFFFFFF
        assert expr.right.value == 2147483647
    
    def test_expression_hashable(self):
        """Test that expressions can be used in sets and as dict keys (due to frozen=True)"""
        e1 = Const(42)
        e2 = Const(42)
        e3 = Var('x')
        
        expr_set = {e1, e2, e3}
        # e1 and e2 are equal, so set should have 2 elements
        assert len(expr_set) == 2
        
        # Can use as dict key
        expr_dict = {e1: "const", e3: "var"}
        assert expr_dict[e2] == "const"  # e2 equals e1
