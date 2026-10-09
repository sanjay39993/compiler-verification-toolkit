"""
Unit tests for C++ Code Generator

Tests the translation of AST expressions into valid C++17 code with uint32_t
semantics, proper parenthesization, and complete program structure.
"""

import pytest
import re
from src.ast_nodes import Const, Var, BinOp
from src.cpp_codegen import expr_to_cpp, generate_cpp


class TestExprToCppConst:
    """Tests for converting Const nodes to C++"""
    
    def test_const_simple(self):
        """Test converting simple constant"""
        assert expr_to_cpp(Const(42)) == "42u"
    
    def test_const_zero(self):
        """Test converting zero constant"""
        assert expr_to_cpp(Const(0)) == "0u"
    
    def test_const_large(self):
        """Test converting large constant"""
        assert expr_to_cpp(Const(0xFFFFFFFF)) == "4294967295u"
    
    def test_const_normalized(self):
        """Test that large constants are normalized to 32-bit"""
        # Constant larger than 2^32 should wrap
        cpp = expr_to_cpp(Const(0x100000000))  # 2^32
        assert cpp == "0u"
        
        cpp2 = expr_to_cpp(Const(0x100000005))  # 2^32 + 5
        assert cpp2 == "5u"
    
    def test_const_negative(self):
        """Test that negative constants are normalized to unsigned"""
        # -1 should become 0xFFFFFFFF
        cpp = expr_to_cpp(Const(-1))
        assert cpp == "4294967295u"
        
        # -100 should wrap around
        cpp2 = expr_to_cpp(Const(-100))
        expected = str(0xFFFFFFFF - 99) + "u"
        assert cpp2 == expected
    
    def test_const_has_u_suffix(self):
        """Test that all constants have 'u' suffix"""
        assert expr_to_cpp(Const(1)).endswith('u')
        assert expr_to_cpp(Const(100)).endswith('u')
        assert expr_to_cpp(Const(0xFFFFFFFF)).endswith('u')


class TestExprToCppVar:
    """Tests for converting Var nodes to C++"""
    
    def test_var_x(self):
        """Test converting variable x"""
        assert expr_to_cpp(Var('x')) == "x"
    
    def test_var_no_suffix(self):
        """Test that variable has no 'u' suffix"""
        cpp = expr_to_cpp(Var('x'))
        assert cpp == "x"
        assert not cpp.endswith('u')


class TestExprToCppBinOp:
    """Tests for converting BinOp nodes to C++"""
    
    def test_binop_add(self):
        """Test converting addition"""
        expr = BinOp('+', Const(10), Const(20))
        assert expr_to_cpp(expr) == "(10u + 20u)"
    
    def test_binop_sub(self):
        """Test converting subtraction"""
        expr = BinOp('-', Const(20), Const(10))
        assert expr_to_cpp(expr) == "(20u - 10u)"
    
    def test_binop_mul(self):
        """Test converting multiplication"""
        expr = BinOp('*', Const(3), Const(4))
        assert expr_to_cpp(expr) == "(3u * 4u)"
    
    def test_binop_var_const(self):
        """Test converting operation with variable and constant"""
        expr = BinOp('+', Var('x'), Const(5))
        assert expr_to_cpp(expr) == "(x + 5u)"
    
    def test_binop_const_var(self):
        """Test converting operation with constant and variable"""
        expr = BinOp('*', Const(2), Var('x'))
        assert expr_to_cpp(expr) == "(2u * x)"
    
    def test_binop_parentheses(self):
        """Test that binary operations are parenthesized"""
        expr = BinOp('+', Const(1), Const(2))
        cpp = expr_to_cpp(expr)
        assert cpp.startswith('(')
        assert cpp.endswith(')')


class TestExprToCppNested:
    """Tests for converting nested expressions to C++"""
    
    def test_nested_add_mul(self):
        """Test nested (2 + 3) * 4"""
        inner = BinOp('+', Const(2), Const(3))
        outer = BinOp('*', inner, Const(4))
        assert expr_to_cpp(outer) == "((2u + 3u) * 4u)"
    
    def test_nested_mul_add(self):
        """Test nested (x * 2) + 100"""
        inner = BinOp('*', Var('x'), Const(2))
        outer = BinOp('+', inner, Const(100))
        assert expr_to_cpp(outer) == "((x * 2u) + 100u)"
    
    def test_deeply_nested(self):
        """Test deeply nested ((x + 1) * 2) - 3"""
        level1 = BinOp('+', Var('x'), Const(1))
        level2 = BinOp('*', level1, Const(2))
        level3 = BinOp('-', level2, Const(3))
        assert expr_to_cpp(level3) == "(((x + 1u) * 2u) - 3u)"
    
    def test_complex_expression(self):
        """Test complex (x * 2) + ((100 - x) * 3)"""
        left = BinOp('*', Var('x'), Const(2))
        right_inner = BinOp('-', Const(100), Var('x'))
        right = BinOp('*', right_inner, Const(3))
        expr = BinOp('+', left, right)
        expected = "((x * 2u) + ((100u - x) * 3u))"
        assert expr_to_cpp(expr) == expected
    
    def test_nested_preserves_structure(self):
        """Test that nested structure is preserved in C++"""
        # (a + b) + c should be different from a + (b + c)
        expr1 = BinOp('+', BinOp('+', Const(1), Const(2)), Const(3))
        expr2 = BinOp('+', Const(1), BinOp('+', Const(2), Const(3)))
        
        cpp1 = expr_to_cpp(expr1)
        cpp2 = expr_to_cpp(expr2)
        
        assert cpp1 == "((1u + 2u) + 3u)"
        assert cpp2 == "(1u + (2u + 3u))"
        assert cpp1 != cpp2


class TestExprToCppEdgeCases:
    """Tests for edge cases in expression conversion"""
    
    def test_max_uint32(self):
        """Test maximum uint32 value"""
        expr = BinOp('+', Const(0xFFFFFFFF), Const(0))
        cpp = expr_to_cpp(expr)
        assert "4294967295u" in cpp
    
    def test_same_node_reused(self):
        """Test same node reused (x + x)"""
        x_node = Var('x')
        expr = BinOp('+', x_node, x_node)
        assert expr_to_cpp(expr) == "(x + x)"
    
    def test_all_operators(self):
        """Test all three operators appear correctly"""
        expr_add = BinOp('+', Const(1), Const(2))
        expr_sub = BinOp('-', Const(3), Const(4))
        expr_mul = BinOp('*', Const(5), Const(6))
        
        assert '+' in expr_to_cpp(expr_add)
        assert '-' in expr_to_cpp(expr_sub)
        assert '*' in expr_to_cpp(expr_mul)


class TestExprToCppErrors:
    """Tests for error handling in expression conversion"""
    
    def test_invalid_expr_type(self):
        """Test that non-Expr types raise TypeError"""
        with pytest.raises(TypeError, match="Expected Expr node"):
            expr_to_cpp(42)
        
        with pytest.raises(TypeError, match="Expected Expr node"):
            expr_to_cpp("not an expr")
        
        with pytest.raises(TypeError, match="Expected Expr node"):
            expr_to_cpp(None)


class TestGenerateCpp:
    """Tests for complete C++ program generation"""
    
    def test_generate_const(self):
        """Test generating program for constant"""
        prog = generate_cpp(Const(42))
        
        # Check structure
        assert "#include <iostream>" in prog
        assert "#include <cstdint>" in prog
        assert "int main()" in prog
        assert "uint32_t x;" in prog
        assert "std::cin >> x;" in prog
        assert "uint32_t result = 42u;" in prog
        assert "std::cout << result << std::endl;" in prog
        assert "return 0;" in prog
    
    def test_generate_var(self):
        """Test generating program for variable"""
        prog = generate_cpp(Var('x'))
        assert "uint32_t result = x;" in prog
    
    def test_generate_binop(self):
        """Test generating program for binary operation"""
        expr = BinOp('+', Const(10), Const(20))
        prog = generate_cpp(expr)
        assert "uint32_t result = (10u + 20u);" in prog
    
    def test_generate_nested(self):
        """Test generating program for nested expression"""
        inner = BinOp('+', Const(2), Const(3))
        outer = BinOp('*', inner, Const(4))
        prog = generate_cpp(outer)
        assert "uint32_t result = ((2u + 3u) * 4u);" in prog
    
    def test_includes_order(self):
        """Test that includes appear at the top"""
        prog = generate_cpp(Const(1))
        lines = prog.strip().split('\n')
        assert lines[0] == "#include <iostream>"
        assert lines[1] == "#include <cstdint>"
    
    def test_has_main_function(self):
        """Test that program has main function"""
        prog = generate_cpp(Const(1))
        assert "int main()" in prog
        assert "{" in prog
        assert "}" in prog
    
    def test_uses_uint32_t(self):
        """Test that program uses uint32_t not int"""
        prog = generate_cpp(Const(1))
        assert "uint32_t x;" in prog
        assert "uint32_t result" in prog
        # Should not have plain 'int' (except in 'int main()')
        prog_without_main = prog.replace("int main()", "")
        prog_without_uint = prog_without_main.replace("uint32_t", "")
        # Any remaining 'int' would be suspicious
        assert "int " not in prog_without_uint
    
    def test_input_output_structure(self):
        """Test that program reads input and writes output"""
        prog = generate_cpp(Const(1))
        # Input comes before computation
        assert prog.index("std::cin") < prog.index("uint32_t result")
        # Computation comes before output
        assert prog.index("uint32_t result") < prog.index("std::cout")
    
    def test_program_compiles_structure(self):
        """Test that generated program has valid C++ structure"""
        prog = generate_cpp(BinOp('+', Var('x'), Const(5)))
        
        # Count braces
        assert prog.count('{') == prog.count('}')
        
        # Check main function structure
        assert "int main() {" in prog
        
        # Check statements have semicolons
        assert "uint32_t x;" in prog
        assert "std::cin >> x;" in prog
        assert prog.count("uint32_t result = ") == 1
        assert "std::cout << result << std::endl;" in prog
        assert "return 0;" in prog


class TestGenerateCppEdgeCases:
    """Tests for edge cases in program generation"""
    
    def test_generate_large_constant(self):
        """Test generating program with large constant"""
        prog = generate_cpp(Const(0xFFFFFFFF))
        assert "4294967295u" in prog
    
    def test_generate_negative_constant(self):
        """Test generating program with negative constant (normalized)"""
        prog = generate_cpp(Const(-1))
        assert "4294967295u" in prog
    
    def test_generate_overflow_constant(self):
        """Test generating program with overflow constant"""
        prog = generate_cpp(Const(0x100000001))
        assert "1u" in prog
    
    def test_generate_complex_expression(self):
        """Test generating program with complex nested expression"""
        # ((x + 1) * 2) - 3
        expr = BinOp('-', BinOp('*', BinOp('+', Var('x'), Const(1)), Const(2)), Const(3))
        prog = generate_cpp(expr)
        assert "uint32_t result = (((x + 1u) * 2u) - 3u);" in prog


class TestGenerateCppErrors:
    """Tests for error handling in program generation"""
    
    def test_generate_invalid_expr_type(self):
        """Test that non-Expr types raise TypeError"""
        with pytest.raises(TypeError, match="Expected Expr node"):
            generate_cpp(42)
        
        with pytest.raises(TypeError, match="Expected Expr node"):
            generate_cpp("not an expr")
    
    def test_generate_invalid_input_var(self):
        """Test that non-'x' input variable names are rejected"""
        with pytest.raises(ValueError, match="Only input variable 'x' is supported"):
            generate_cpp(Const(1), input_var='y')


class TestGeneratedCodeValidity:
    """Tests to verify generated code would be valid C++"""
    
    def test_no_double_operators(self):
        """Test that generated code doesn't have operator issues like '+ +' or '- -'"""
        expr = BinOp('+', Const(5), Const(10))
        cpp = expr_to_cpp(expr)
        assert '+ +' not in cpp
        assert '- -' not in cpp
        assert '* *' not in cpp
    
    def test_constants_are_numeric(self):
        """Test that generated constants are valid numbers"""
        expr = Const(42)
        cpp = expr_to_cpp(expr)
        # Remove 'u' suffix and verify it's a number
        num_str = cpp.rstrip('u')
        assert num_str.isdigit()
    
    def test_balanced_parentheses(self):
        """Test that parentheses are balanced"""
        expr = BinOp('*', BinOp('+', Const(2), Const(3)), Const(4))
        cpp = expr_to_cpp(expr)
        assert cpp.count('(') == cpp.count(')')
    
    def test_no_syntax_errors_simple(self):
        """Test simple expressions don't have obvious syntax errors"""
        exprs = [
            Const(42),
            Var('x'),
            BinOp('+', Const(1), Const(2)),
            BinOp('-', Var('x'), Const(5)),
            BinOp('*', Const(3), Var('x'))
        ]
        
        for expr in exprs:
            cpp = expr_to_cpp(expr)
            # Should not have double operators
            assert '++' not in cpp or 'x++' in cpp  # x++ would be valid but we don't generate it
            assert '--' not in cpp or 'x--' in cpp  # x-- would be valid but we don't generate it
            # Should have balanced parens
            assert cpp.count('(') == cpp.count(')')
