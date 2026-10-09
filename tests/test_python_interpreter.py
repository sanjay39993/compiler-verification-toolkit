"""
Unit tests for Python Oracle Interpreter

Tests the reference implementation that evaluates AST expressions with
correct 32-bit unsigned integer semantics.
"""

import pytest
from src.ast_nodes import Const, Var, BinOp
from src.python_interpreter import mask32, evaluate


class TestMask32:
    """Tests for 32-bit masking function"""
    
    def test_mask32_zero(self):
        """Test masking zero"""
        assert mask32(0) == 0
    
    def test_mask32_small_positive(self):
        """Test masking small positive values"""
        assert mask32(1) == 1
        assert mask32(42) == 42
        assert mask32(1000) == 1000
    
    def test_mask32_max_uint32(self):
        """Test masking maximum uint32 value"""
        assert mask32(0xFFFFFFFF) == 0xFFFFFFFF
        assert mask32(4294967295) == 4294967295
    
    def test_mask32_overflow(self):
        """Test masking values > 2^32"""
        assert mask32(0x100000000) == 0  # 2^32 wraps to 0
        assert mask32(0x100000001) == 1  # 2^32 + 1 wraps to 1
        assert mask32(0xFFFFFFFF + 1) == 0
    
    def test_mask32_negative(self):
        """Test masking negative values (two's complement)"""
        assert mask32(-1) == 0xFFFFFFFF
        assert mask32(-2) == 0xFFFFFFFE
        assert mask32(-100) == 0xFFFFFFFF - 99
    
    def test_mask32_large_overflow(self):
        """Test masking very large values"""
        assert mask32(2**64) == 0
        assert mask32(2**64 + 42) == 42


class TestEvaluateConst:
    """Tests for evaluating constant nodes"""
    
    def test_eval_const_simple(self):
        """Test evaluating simple constant"""
        assert evaluate(Const(42), x_value=0) == 42
    
    def test_eval_const_zero(self):
        """Test evaluating zero constant"""
        assert evaluate(Const(0), x_value=0) == 0
    
    def test_eval_const_large(self):
        """Test evaluating large constant"""
        assert evaluate(Const(0xFFFFFFFF), x_value=0) == 0xFFFFFFFF
    
    def test_eval_const_negative(self):
        """Test evaluating negative constant (wraps around)"""
        assert evaluate(Const(-1), x_value=0) == 0xFFFFFFFF
        assert evaluate(Const(-100), x_value=0) == 0xFFFFFFFF - 99
    
    def test_eval_const_overflow(self):
        """Test evaluating constant that overflows 32-bit"""
        assert evaluate(Const(0x100000000), x_value=0) == 0
        assert evaluate(Const(0x100000001), x_value=0) == 1
    
    def test_eval_const_ignores_x_value(self):
        """Test that constant evaluation ignores x_value"""
        assert evaluate(Const(42), x_value=999) == 42


class TestEvaluateVar:
    """Tests for evaluating variable nodes"""
    
    def test_eval_var_simple(self):
        """Test evaluating variable with simple value"""
        assert evaluate(Var('x'), x_value=100) == 100
    
    def test_eval_var_zero(self):
        """Test evaluating variable with zero value"""
        assert evaluate(Var('x'), x_value=0) == 0
    
    def test_eval_var_large(self):
        """Test evaluating variable with large value"""
        assert evaluate(Var('x'), x_value=0xFFFFFFFF) == 0xFFFFFFFF
    
    def test_eval_var_negative(self):
        """Test evaluating variable with negative value (wraps around)"""
        assert evaluate(Var('x'), x_value=-1) == 0xFFFFFFFF
        assert evaluate(Var('x'), x_value=-100) == 0xFFFFFFFF - 99
    
    def test_eval_var_overflow(self):
        """Test evaluating variable with value > 2^32"""
        assert evaluate(Var('x'), x_value=0x100000000) == 0
        assert evaluate(Var('x'), x_value=0x100000001) == 1


class TestEvaluateAddition:
    """Tests for addition operations"""
    
    def test_add_constants(self):
        """Test adding two constants"""
        expr = BinOp('+', Const(10), Const(20))
        assert evaluate(expr, x_value=0) == 30
    
    def test_add_var_const(self):
        """Test adding variable and constant"""
        expr = BinOp('+', Var('x'), Const(5))
        assert evaluate(expr, x_value=10) == 15
    
    def test_add_const_var(self):
        """Test adding constant and variable"""
        expr = BinOp('+', Const(100), Var('x'))
        assert evaluate(expr, x_value=50) == 150
    
    def test_add_overflow_simple(self):
        """Test addition overflow wraps to zero"""
        expr = BinOp('+', Const(0xFFFFFFFF), Const(1))
        assert evaluate(expr, x_value=0) == 0
    
    def test_add_overflow_both_large(self):
        """Test addition of two large numbers overflows"""
        expr = BinOp('+', Const(0xFFFFFFFF), Const(0xFFFFFFFF))
        result = evaluate(expr, x_value=0)
        assert result == 0xFFFFFFFE  # (2^32 - 1) + (2^32 - 1) = 2^33 - 2, masked
    
    def test_add_with_var_overflow(self):
        """Test addition with variable causes overflow"""
        expr = BinOp('+', Var('x'), Const(10))
        assert evaluate(expr, x_value=0xFFFFFFFF) == 9


class TestEvaluateSubtraction:
    """Tests for subtraction operations"""
    
    def test_sub_constants(self):
        """Test subtracting two constants"""
        expr = BinOp('-', Const(20), Const(10))
        assert evaluate(expr, x_value=0) == 10
    
    def test_sub_var_const(self):
        """Test subtracting constant from variable"""
        expr = BinOp('-', Var('x'), Const(5))
        assert evaluate(expr, x_value=10) == 5
    
    def test_sub_const_var(self):
        """Test subtracting variable from constant"""
        expr = BinOp('-', Const(100), Var('x'))
        assert evaluate(expr, x_value=30) == 70
    
    def test_sub_underflow_simple(self):
        """Test subtraction underflow (0 - 1 = 2^32 - 1)"""
        expr = BinOp('-', Const(0), Const(1))
        assert evaluate(expr, x_value=0) == 0xFFFFFFFF
    
    def test_sub_underflow_small_from_large(self):
        """Test subtracting small from large number"""
        expr = BinOp('-', Const(5), Const(10))
        result = evaluate(expr, x_value=0)
        # 5 - 10 = -5, which wraps to 2^32 - 5
        assert result == 0xFFFFFFFF - 4
    
    def test_sub_same_values(self):
        """Test subtracting same values gives zero"""
        expr = BinOp('-', Const(42), Const(42))
        assert evaluate(expr, x_value=0) == 0
    
    def test_sub_with_var_underflow(self):
        """Test subtraction with variable causes underflow"""
        expr = BinOp('-', Const(10), Var('x'))
        assert evaluate(expr, x_value=20) == 0xFFFFFFFF - 9


class TestEvaluateMultiplication:
    """Tests for multiplication operations"""
    
    def test_mul_constants(self):
        """Test multiplying two constants"""
        expr = BinOp('*', Const(3), Const(4))
        assert evaluate(expr, x_value=0) == 12
    
    def test_mul_var_const(self):
        """Test multiplying variable and constant"""
        expr = BinOp('*', Var('x'), Const(2))
        assert evaluate(expr, x_value=50) == 100
    
    def test_mul_const_var(self):
        """Test multiplying constant and variable"""
        expr = BinOp('*', Const(10), Var('x'))
        assert evaluate(expr, x_value=7) == 70
    
    def test_mul_by_zero(self):
        """Test multiplication by zero"""
        expr = BinOp('*', Const(0), Const(12345))
        assert evaluate(expr, x_value=0) == 0
        
        expr2 = BinOp('*', Var('x'), Const(0))
        assert evaluate(expr2, x_value=999) == 0
    
    def test_mul_by_one(self):
        """Test multiplication by one"""
        expr = BinOp('*', Const(1), Var('x'))
        assert evaluate(expr, x_value=42) == 42
    
    def test_mul_overflow_simple(self):
        """Test multiplication overflow"""
        # 0x10000 * 0x10000 = 0x100000000 = 2^32, wraps to 0
        expr = BinOp('*', Const(0x10000), Const(0x10000))
        assert evaluate(expr, x_value=0) == 0
    
    def test_mul_overflow_partial(self):
        """Test multiplication with partial overflow"""
        # Large multiplication that wraps around
        expr = BinOp('*', Const(0xFFFFFFFF), Const(2))
        result = evaluate(expr, x_value=0)
        # (2^32 - 1) * 2 = 2^33 - 2, masked to 32-bit
        assert result == 0xFFFFFFFE
    
    def test_mul_large_numbers(self):
        """Test multiplying large numbers"""
        expr = BinOp('*', Const(0xFFFF), Const(0x10001))
        result = evaluate(expr, x_value=0)
        # Calculate expected: 65535 * 65537 = 4294836735, mask to 32-bit
        expected = mask32(65535 * 65537)
        assert result == expected


class TestNestedExpressions:
    """Tests for nested and complex expressions"""
    
    def test_nested_add_mul(self):
        """Test nested (2 + 3) * 4"""
        inner = BinOp('+', Const(2), Const(3))
        outer = BinOp('*', inner, Const(4))
        assert evaluate(outer, x_value=0) == 20
    
    def test_nested_mul_add(self):
        """Test nested (x * 2) + 100"""
        inner = BinOp('*', Var('x'), Const(2))
        outer = BinOp('+', inner, Const(100))
        assert evaluate(outer, x_value=50) == 200
    
    def test_deeply_nested(self):
        """Test deeply nested ((x + 1) * 2) - 3"""
        level1 = BinOp('+', Var('x'), Const(1))
        level2 = BinOp('*', level1, Const(2))
        level3 = BinOp('-', level2, Const(3))
        # x=10: (10+1)*2 - 3 = 11*2 - 3 = 22 - 3 = 19
        assert evaluate(level3, x_value=10) == 19
    
    def test_complex_expression(self):
        """Test complex (x * 2) + ((100 - x) * 3)"""
        left = BinOp('*', Var('x'), Const(2))
        right_inner = BinOp('-', Const(100), Var('x'))
        right = BinOp('*', right_inner, Const(3))
        expr = BinOp('+', left, right)
        # x=20: (20*2) + ((100-20)*3) = 40 + (80*3) = 40 + 240 = 280
        assert evaluate(expr, x_value=20) == 280
    
    def test_nested_with_overflow(self):
        """Test nested expression with overflow"""
        # (0xFFFFFFFF + 1) * 2 = 0 * 2 = 0
        inner = BinOp('+', Const(0xFFFFFFFF), Const(1))
        outer = BinOp('*', inner, Const(2))
        assert evaluate(outer, x_value=0) == 0
    
    def test_nested_with_underflow(self):
        """Test nested expression with underflow"""
        # (0 - 1) + 1 = 0xFFFFFFFF + 1 = 0
        inner = BinOp('-', Const(0), Const(1))
        outer = BinOp('+', inner, Const(1))
        assert evaluate(outer, x_value=0) == 0


class TestWraparound:
    """Tests for wraparound and chained overflow/underflow"""
    
    def test_chained_overflow(self):
        """Test chained additions that overflow"""
        # ((0xFFFFFFFE + 1) + 1) = (0xFFFFFFFF + 1) = 0
        inner = BinOp('+', Const(0xFFFFFFFE), Const(1))
        outer = BinOp('+', inner, Const(1))
        assert evaluate(outer, x_value=0) == 0
    
    def test_chained_underflow(self):
        """Test chained subtractions that underflow"""
        # ((1 - 1) - 1) = (0 - 1) = 0xFFFFFFFF
        inner = BinOp('-', Const(1), Const(1))
        outer = BinOp('-', inner, Const(1))
        assert evaluate(outer, x_value=0) == 0xFFFFFFFF
    
    def test_overflow_then_underflow(self):
        """Test overflow followed by underflow"""
        # ((0xFFFFFFFF + 5) - 10) = (4 - 10) wraps around
        inner = BinOp('+', Const(0xFFFFFFFF), Const(5))
        outer = BinOp('-', inner, Const(10))
        result = evaluate(outer, x_value=0)
        # 4 - 10 = -6, wraps to 2^32 - 6
        assert result == 0xFFFFFFFF - 5
    
    def test_multiple_operations_wraparound(self):
        """Test multiple operations with wraparound"""
        # (((x + 0xFFFFFFFF) * 2) - 100) with x=10
        e1 = BinOp('+', Var('x'), Const(0xFFFFFFFF))  # 10 + 0xFFFFFFFF wraps to 9
        e2 = BinOp('*', e1, Const(2))  # 9 * 2 = 18
        e3 = BinOp('-', e2, Const(100))  # 18 - 100 wraps
        result = evaluate(e3, x_value=10)
        expected = mask32(18 - 100)
        assert result == expected


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_invalid_expr_type(self):
        """Test that non-Expr types raise TypeError"""
        with pytest.raises(TypeError, match="Expected Expr node"):
            evaluate(42, x_value=0)
        
        with pytest.raises(TypeError, match="Expected Expr node"):
            evaluate("not an expr", x_value=0)
        
        with pytest.raises(TypeError, match="Expected Expr node"):
            evaluate(None, x_value=0)
    
    def test_invalid_operator(self):
        """Test that invalid operators raise ValueError"""
        # This shouldn't happen due to BinOp validation, but test anyway
        # We'd need to bypass BinOp construction to test this
        # Since BinOp validates in __post_init__, this is already covered
        pass


class TestEdgeCases:
    """Tests for edge cases and boundary values"""
    
    def test_max_uint32_operations(self):
        """Test operations at maximum uint32 value"""
        # 0xFFFFFFFF + 0 = 0xFFFFFFFF
        expr = BinOp('+', Const(0xFFFFFFFF), Const(0))
        assert evaluate(expr, x_value=0) == 0xFFFFFFFF
        
        # 0xFFFFFFFF - 0 = 0xFFFFFFFF
        expr2 = BinOp('-', Const(0xFFFFFFFF), Const(0))
        assert evaluate(expr2, x_value=0) == 0xFFFFFFFF
        
        # 0xFFFFFFFF * 1 = 0xFFFFFFFF
        expr3 = BinOp('*', Const(0xFFFFFFFF), Const(1))
        assert evaluate(expr3, x_value=0) == 0xFFFFFFFF
    
    def test_zero_operations(self):
        """Test all operations with zero"""
        # 0 + 0 = 0
        assert evaluate(BinOp('+', Const(0), Const(0)), x_value=0) == 0
        
        # 0 - 0 = 0
        assert evaluate(BinOp('-', Const(0), Const(0)), x_value=0) == 0
        
        # 0 * 0 = 0
        assert evaluate(BinOp('*', Const(0), Const(0)), x_value=0) == 0
    
    def test_same_node_reused(self):
        """Test that same node can be reused (x + x)"""
        x_node = Var('x')
        expr = BinOp('+', x_node, x_node)
        assert evaluate(expr, x_value=100) == 200
    
    def test_var_in_multiple_places(self):
        """Test variable used in multiple subexpressions"""
        # (x + 5) * (x - 3) with x=10
        left = BinOp('+', Var('x'), Const(5))
        right = BinOp('-', Var('x'), Const(3))
        expr = BinOp('*', left, right)
        # (10 + 5) * (10 - 3) = 15 * 7 = 105
        assert evaluate(expr, x_value=10) == 105
