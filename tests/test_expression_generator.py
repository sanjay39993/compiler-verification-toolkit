"""
Unit tests for Random Expression Generator

Tests reproducibility, depth constraints, constant bounds, operator variety,
and compatibility with the Python oracle and C++ code generator.
"""

import pytest
from src.ast_nodes import Expr, Const, Var, BinOp
from src.expression_generator import generate_random_expr
from src.python_interpreter import evaluate
from src.cpp_codegen import expr_to_cpp, generate_cpp


class TestReproducibility:
    """Tests for reproducible random generation"""
    
    def test_same_seed_same_expr(self):
        """Test that same seed produces same expression"""
        expr1 = generate_random_expr(seed=42, max_depth=3)
        expr2 = generate_random_expr(seed=42, max_depth=3)
        assert expr1 == expr2
    
    def test_different_seed_different_expr(self):
        """Test that different seeds produce different expressions"""
        expr1 = generate_random_expr(seed=42, max_depth=3)
        expr2 = generate_random_expr(seed=43, max_depth=3)
        # Very unlikely to be the same (though theoretically possible)
        assert expr1 != expr2
    
    def test_seed_reproducibility_multiple_calls(self):
        """Test reproducibility across multiple generations"""
        exprs1 = [generate_random_expr(seed=i, max_depth=2) for i in range(10)]
        exprs2 = [generate_random_expr(seed=i, max_depth=2) for i in range(10)]
        assert exprs1 == exprs2
    
    def test_same_seed_different_params(self):
        """Test that same seed with different params produces different expressions"""
        expr1 = generate_random_expr(seed=42, max_depth=2, max_const=100)
        expr2 = generate_random_expr(seed=42, max_depth=3, max_const=100)
        # Different max_depth may produce different expression
        # (Not guaranteed to be different, but likely)
    
    def test_global_random_not_affected(self):
        """Test that generator doesn't affect global random state"""
        import random
        random.seed(999)
        val1 = random.random()
        
        random.seed(999)
        _ = generate_random_expr(seed=42, max_depth=2)
        val2 = random.random()
        
        # Global random state should be the same
        assert val1 == val2


class TestDepthConstraints:
    """Tests for depth constraint enforcement"""
    
    def test_depth_zero_only_leaves(self):
        """Test that depth 0 produces only leaf nodes"""
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=0)
            # Should be either Const or Var
            assert isinstance(expr, (Const, Var))
            assert not isinstance(expr, BinOp)
    
    def test_depth_one_structure(self):
        """Test that depth 1 has at most one level of BinOp"""
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=1)
            if isinstance(expr, BinOp):
                # Children must be leaves
                assert isinstance(expr.left, (Const, Var))
                assert isinstance(expr.right, (Const, Var))
    
    def test_depth_two_structure(self):
        """Test that depth 2 has at most two levels of BinOp"""
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=2)
            if isinstance(expr, BinOp):
                # Children can be BinOp or leaves
                if isinstance(expr.left, BinOp):
                    # Grandchildren must be leaves
                    assert isinstance(expr.left.left, (Const, Var))
                    assert isinstance(expr.left.right, (Const, Var))
                if isinstance(expr.right, BinOp):
                    # Grandchildren must be leaves
                    assert isinstance(expr.right.left, (Const, Var))
                    assert isinstance(expr.right.right, (Const, Var))
    
    def test_max_depth_respected(self):
        """Test that generated trees don't exceed max_depth"""
        def tree_depth(expr: Expr) -> int:
            """Calculate actual depth of expression tree"""
            if isinstance(expr, (Const, Var)):
                return 0
            elif isinstance(expr, BinOp):
                return 1 + max(tree_depth(expr.left), tree_depth(expr.right))
            else:
                return 0
        
        for max_d in [0, 1, 2, 3, 4]:
            for seed in range(10):
                expr = generate_random_expr(seed=seed, max_depth=max_d)
                actual_depth = tree_depth(expr)
                assert actual_depth <= max_d, f"Depth {actual_depth} exceeds max {max_d}"


class TestConstantBounds:
    """Tests for constant value bounds"""
    
    def test_constants_within_range(self):
        """Test that generated constants are within [0, max_const]"""
        def extract_constants(expr: Expr) -> list:
            """Extract all constant values from expression"""
            if isinstance(expr, Const):
                return [expr.value]
            elif isinstance(expr, BinOp):
                return extract_constants(expr.left) + extract_constants(expr.right)
            else:
                return []
        
        max_c = 100
        for seed in range(50):
            expr = generate_random_expr(seed=seed, max_depth=3, max_const=max_c, var_probability=0.3)
            constants = extract_constants(expr)
            for const in constants:
                assert 0 <= const <= max_c, f"Constant {const} out of range [0, {max_c}]"
    
    def test_small_max_const(self):
        """Test with small max_const value"""
        expr = generate_random_expr(seed=42, max_depth=2, max_const=10)
        # Should generate successfully
        assert isinstance(expr, Expr)
    
    def test_large_max_const(self):
        """Test with large max_const value"""
        expr = generate_random_expr(seed=42, max_depth=2, max_const=1000000)
        # Should generate successfully
        assert isinstance(expr, Expr)
    
    def test_max_const_one(self):
        """Test with max_const=1 (only 0 and 1 allowed)"""
        def extract_constants(expr: Expr) -> list:
            if isinstance(expr, Const):
                return [expr.value]
            elif isinstance(expr, BinOp):
                return extract_constants(expr.left) + extract_constants(expr.right)
            else:
                return []
        
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=2, max_const=1, var_probability=0.0)
            constants = extract_constants(expr)
            for const in constants:
                assert const in [0, 1]


class TestOperators:
    """Tests for operator generation"""
    
    def test_generates_all_operators(self):
        """Test that all three operators are generated"""
        def extract_operators(expr: Expr) -> list:
            """Extract all operators from expression"""
            if isinstance(expr, BinOp):
                return [expr.op] + extract_operators(expr.left) + extract_operators(expr.right)
            else:
                return []
        
        # Generate many expressions and collect operators
        all_ops = set()
        for seed in range(100):
            expr = generate_random_expr(seed=seed, max_depth=3)
            ops = extract_operators(expr)
            all_ops.update(ops)
        
        # Should see all three operators
        assert '+' in all_ops
        assert '-' in all_ops
        assert '*' in all_ops
    
    def test_valid_operators_only(self):
        """Test that only valid operators are generated"""
        def extract_operators(expr: Expr) -> list:
            if isinstance(expr, BinOp):
                return [expr.op] + extract_operators(expr.left) + extract_operators(expr.right)
            else:
                return []
        
        valid_ops = {'+', '-', '*'}
        for seed in range(50):
            expr = generate_random_expr(seed=seed, max_depth=3)
            ops = extract_operators(expr)
            for op in ops:
                assert op in valid_ops


class TestVariableProbability:
    """Tests for variable generation probability"""
    
    def test_var_probability_zero(self):
        """Test that var_probability=0.0 produces no variables"""
        def has_var(expr: Expr) -> bool:
            """Check if expression contains Var"""
            if isinstance(expr, Var):
                return True
            elif isinstance(expr, BinOp):
                return has_var(expr.left) or has_var(expr.right)
            else:
                return False
        
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=3, var_probability=0.0)
            assert not has_var(expr), "Found Var with var_probability=0.0"
    
    def test_var_probability_one(self):
        """Test that var_probability=1.0 produces only variables at leaves"""
        def check_leaves(expr: Expr) -> bool:
            """Check that all leaves are Var"""
            if isinstance(expr, Const):
                return False  # Found a Const, should be Var
            elif isinstance(expr, Var):
                return True
            elif isinstance(expr, BinOp):
                return check_leaves(expr.left) and check_leaves(expr.right)
            else:
                return True
        
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=3, var_probability=1.0)
            assert check_leaves(expr), "Found Const with var_probability=1.0"
    
    def test_var_probability_mixed(self):
        """Test that 0 < var_probability < 1 produces mix of Var and Const"""
        def count_leaves(expr: Expr) -> tuple:
            """Count Var and Const leaves"""
            if isinstance(expr, Var):
                return (1, 0)  # (var_count, const_count)
            elif isinstance(expr, Const):
                return (0, 1)
            elif isinstance(expr, BinOp):
                left_var, left_const = count_leaves(expr.left)
                right_var, right_const = count_leaves(expr.right)
                return (left_var + right_var, left_const + right_const)
            else:
                return (0, 0)
        
        # With var_probability=0.5 and enough samples, should see both
        total_vars = 0
        total_consts = 0
        for seed in range(100):
            expr = generate_random_expr(seed=seed, max_depth=2, var_probability=0.5)
            var_count, const_count = count_leaves(expr)
            total_vars += var_count
            total_consts += const_count
        
        # Should have generated both types
        assert total_vars > 0, "No variables generated with var_probability=0.5"
        assert total_consts > 0, "No constants generated with var_probability=0.5"


class TestParameterValidation:
    """Tests for parameter validation"""
    
    def test_negative_seed_rejected(self):
        """Test that negative seed is rejected"""
        with pytest.raises(ValueError, match="seed must be non-negative"):
            generate_random_expr(seed=-1)
    
    def test_negative_max_depth_rejected(self):
        """Test that negative max_depth is rejected"""
        with pytest.raises(ValueError, match="max_depth must be >= 0"):
            generate_random_expr(seed=42, max_depth=-1)
    
    def test_zero_max_const_rejected(self):
        """Test that max_const=0 is rejected"""
        with pytest.raises(ValueError, match="max_const must be > 0"):
            generate_random_expr(seed=42, max_const=0)
    
    def test_negative_max_const_rejected(self):
        """Test that negative max_const is rejected"""
        with pytest.raises(ValueError, match="max_const must be > 0"):
            generate_random_expr(seed=42, max_const=-10)
    
    def test_var_probability_below_zero_rejected(self):
        """Test that var_probability < 0 is rejected"""
        with pytest.raises(ValueError, match="var_probability must be in"):
            generate_random_expr(seed=42, var_probability=-0.1)
    
    def test_var_probability_above_one_rejected(self):
        """Test that var_probability > 1 is rejected"""
        with pytest.raises(ValueError, match="var_probability must be in"):
            generate_random_expr(seed=42, var_probability=1.1)
    
    def test_invalid_seed_type(self):
        """Test that non-int seed is rejected"""
        with pytest.raises(TypeError, match="seed must be int"):
            generate_random_expr(seed="42")
        with pytest.raises(TypeError, match="seed must be int"):
            generate_random_expr(seed=3.14)
    
    def test_invalid_max_depth_type(self):
        """Test that non-int max_depth is rejected"""
        with pytest.raises(TypeError, match="max_depth must be int"):
            generate_random_expr(seed=42, max_depth="3")
        with pytest.raises(TypeError, match="max_depth must be int"):
            generate_random_expr(seed=42, max_depth=3.5)
    
    def test_invalid_max_const_type(self):
        """Test that non-int max_const is rejected"""
        with pytest.raises(TypeError, match="max_const must be int"):
            generate_random_expr(seed=42, max_const="100")
        with pytest.raises(TypeError, match="max_const must be int"):
            generate_random_expr(seed=42, max_const=100.5)
    
    def test_invalid_var_probability_type(self):
        """Test that non-numeric var_probability is rejected"""
        with pytest.raises(TypeError, match="var_probability must be float"):
            generate_random_expr(seed=42, var_probability="0.5")


class TestOracleCompatibility:
    """Tests for compatibility with Python oracle"""
    
    def test_generated_expr_evaluable(self):
        """Test that generated expressions can be evaluated"""
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=3)
            # Should evaluate without error
            result = evaluate(expr, x_value=10)
            assert isinstance(result, int)
            assert 0 <= result <= 0xFFFFFFFF
    
    def test_various_x_values(self):
        """Test evaluation with various x values"""
        expr = generate_random_expr(seed=42, max_depth=3)
        x_values = [0, 1, 10, 100, 1000, 0xFFFFFFFF]
        for x_val in x_values:
            result = evaluate(expr, x_value=x_val)
            assert isinstance(result, int)
    
    def test_complex_expressions_evaluable(self):
        """Test that complex expressions can be evaluated"""
        for seed in range(10):
            expr = generate_random_expr(seed=seed, max_depth=5, max_const=1000)
            result = evaluate(expr, x_value=50)
            assert isinstance(result, int)


class TestCppCodegenCompatibility:
    """Tests for compatibility with C++ code generator"""
    
    def test_generated_expr_convertible(self):
        """Test that generated expressions can be converted to C++"""
        for seed in range(20):
            expr = generate_random_expr(seed=seed, max_depth=3)
            # Should convert without error
            cpp_expr = expr_to_cpp(expr)
            assert isinstance(cpp_expr, str)
            assert len(cpp_expr) > 0
    
    def test_full_cpp_program_generation(self):
        """Test that full C++ programs can be generated"""
        for seed in range(10):
            expr = generate_random_expr(seed=seed, max_depth=3)
            # Should generate complete program
            cpp_program = generate_cpp(expr)
            assert isinstance(cpp_program, str)
            assert "#include <iostream>" in cpp_program
            assert "#include <cstdint>" in cpp_program
            assert "uint32_t" in cpp_program
    
    def test_complex_expressions_convertible(self):
        """Test that complex expressions convert to valid C++"""
        for seed in range(10):
            expr = generate_random_expr(seed=seed, max_depth=5, max_const=1000)
            cpp_expr = expr_to_cpp(expr)
            # Should have balanced parentheses
            assert cpp_expr.count('(') == cpp_expr.count(')')


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_max_depth_zero(self):
        """Test generation with max_depth=0"""
        expr = generate_random_expr(seed=42, max_depth=0)
        assert isinstance(expr, (Const, Var))
    
    def test_large_depth(self):
        """Test generation with large depth"""
        expr = generate_random_expr(seed=42, max_depth=10)
        assert isinstance(expr, Expr)
        # Should still be evaluable
        result = evaluate(expr, x_value=5)
        assert isinstance(result, int)
    
    def test_boundary_var_probabilities(self):
        """Test boundary values for var_probability"""
        expr0 = generate_random_expr(seed=42, max_depth=2, var_probability=0.0)
        expr1 = generate_random_expr(seed=42, max_depth=2, var_probability=1.0)
        assert isinstance(expr0, Expr)
        assert isinstance(expr1, Expr)
    
    def test_many_expressions(self):
        """Test generating many expressions without errors"""
        exprs = [generate_random_expr(seed=i, max_depth=3) for i in range(100)]
        assert len(exprs) == 100
        assert all(isinstance(e, Expr) for e in exprs)
    
    def test_consistent_across_runs(self):
        """Test that expressions are consistent across multiple runs"""
        exprs1 = [generate_random_expr(seed=i, max_depth=2) for i in range(10)]
        exprs2 = [generate_random_expr(seed=i, max_depth=2) for i in range(10)]
        exprs3 = [generate_random_expr(seed=i, max_depth=2) for i in range(10)]
        assert exprs1 == exprs2 == exprs3
