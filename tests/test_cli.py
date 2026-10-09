"""
Unit tests for Command-Line Interface

Tests argument parsing, validation, and integration with differential_tester.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from src.cli import parse_args, main
from src.differential_tester import TestSummary as DiffTestSummary


class TestArgumentParsing:
    """Tests for command-line argument parsing"""
    
    def test_default_arguments(self):
        """Test default argument values"""
        with patch('sys.argv', ['cli.py']):
            args = parse_args()
            
            assert args.num_tests == 100
            assert args.seed == 0
            assert args.opt_levels == [0, 1, 2, 3]
            assert args.max_depth == 4
            assert args.max_const == 1000
            assert args.var_probability == 0.3
            assert args.compiler == 'g++'
            assert args.output_dir is None
            assert args.keep_files is False
    
    def test_custom_num_tests(self):
        """Test custom number of tests"""
        with patch('sys.argv', ['cli.py', '--num-tests', '50']):
            args = parse_args()
            assert args.num_tests == 50
    
    def test_custom_seed(self):
        """Test custom seed"""
        with patch('sys.argv', ['cli.py', '--seed', '42']):
            args = parse_args()
            assert args.seed == 42
    
    def test_custom_opt_levels(self):
        """Test custom optimization levels"""
        with patch('sys.argv', ['cli.py', '--opt-levels', '0', '2']):
            args = parse_args()
            assert args.opt_levels == [0, 2]
    
    def test_custom_x_values(self):
        """Test custom x values including hex"""
        with patch('sys.argv', ['cli.py', '--x-values', '10', '0xFF', '0xFFFFFFFF']):
            args = parse_args()
            assert args.x_values == [10, 0xFF, 0xFFFFFFFF]
    
    def test_custom_output_dir(self):
        """Test custom output directory"""
        with patch('sys.argv', ['cli.py', '--output-dir', './test_output']):
            args = parse_args()
            assert args.output_dir == Path('./test_output')
    
    def test_keep_files_flag(self):
        """Test keep-files flag"""
        with patch('sys.argv', ['cli.py', '--keep-files']):
            args = parse_args()
            assert args.keep_files is True
    
    def test_save_summary(self):
        """Test save-summary option"""
        with patch('sys.argv', ['cli.py', '--save-summary', 'results.json']):
            args = parse_args()
            assert args.save_summary == Path('results.json')


class TestArgumentValidation:
    """Tests for argument validation in main()"""
    
    @patch('src.cli.run_differential_test')
    def test_negative_num_tests(self, mock_run):
        """Test that negative num_tests causes error"""
        with patch('sys.argv', ['cli.py', '--num-tests', '-1']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
    
    @patch('src.cli.run_differential_test')
    def test_negative_seed(self, mock_run):
        """Test that negative seed causes error"""
        with patch('sys.argv', ['cli.py', '--seed', '-1']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
    
    @patch('src.cli.run_differential_test')
    def test_negative_max_depth(self, mock_run):
        """Test that negative max_depth causes error"""
        with patch('sys.argv', ['cli.py', '--max-depth', '-1']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
    
    @patch('src.cli.run_differential_test')
    def test_zero_max_const(self, mock_run):
        """Test that zero max_const causes error"""
        with patch('sys.argv', ['cli.py', '--max-const', '0']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
    
    @patch('src.cli.run_differential_test')
    def test_invalid_var_probability(self, mock_run):
        """Test that invalid var_probability causes error"""
        with patch('sys.argv', ['cli.py', '--var-probability', '1.5']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestMainExecution:
    """Tests for main() execution with mocked differential testing"""
    
    @patch('src.cli.run_differential_test')
    def test_successful_run(self, mock_run):
        """Test successful test run"""
        # Mock successful summary
        mock_run.return_value = DiffTestSummary(
            total_tests=10,
            successful_tests=10,
            compilation_failures=0,
            execution_failures=0,
            discrepancies=0
        )
        
        with patch('sys.argv', ['cli.py', '--num-tests', '10', '--seed', '0']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 0 for success
            assert exc_info.value.code == 0
    
    @patch('src.cli.run_differential_test')
    def test_run_with_discrepancies(self, mock_run):
        """Test run that finds discrepancies"""
        # Mock summary with discrepancies
        mock_run.return_value = DiffTestSummary(
            total_tests=10,
            successful_tests=8,
            compilation_failures=0,
            execution_failures=0,
            discrepancies=2
        )
        
        with patch('sys.argv', ['cli.py', '--num-tests', '10']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 1 for discrepancies
            assert exc_info.value.code == 1
    
    @patch('src.cli.run_differential_test')
    def test_run_with_compilation_failures(self, mock_run):
        """Test run with compilation failures"""
        # Mock summary with compilation failures
        mock_run.return_value = DiffTestSummary(
            total_tests=10,
            successful_tests=7,
            compilation_failures=3,
            execution_failures=0,
            discrepancies=0
        )
        
        with patch('sys.argv', ['cli.py', '--num-tests', '10']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 1 for infrastructure failures
            assert exc_info.value.code == 1
    
    @patch('src.cli.save_summary')
    @patch('src.cli.run_differential_test')
    def test_save_summary_called(self, mock_run, mock_save):
        """Test that save_summary is called when requested"""
        mock_run.return_value = DiffTestSummary(
            total_tests=5,
            successful_tests=5,
            compilation_failures=0,
            execution_failures=0,
            discrepancies=0
        )
        
        with patch('sys.argv', ['cli.py', '--num-tests', '5', '--save-summary', 'test.json']):
            with pytest.raises(SystemExit):
                main()
            
            # Verify save_summary was called
            mock_save.assert_called_once()
            assert mock_save.call_args[0][1] == Path('test.json')
    
    @patch('src.cli.run_differential_test')
    def test_keyboard_interrupt(self, mock_run):
        """Test handling of keyboard interrupt"""
        mock_run.side_effect = KeyboardInterrupt()
        
        with patch('sys.argv', ['cli.py', '--num-tests', '10']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 130 for keyboard interrupt
            assert exc_info.value.code == 130
    
    @patch('src.cli.run_differential_test')
    def test_exception_handling(self, mock_run):
        """Test handling of unexpected exceptions"""
        mock_run.side_effect = Exception("Test error")
        
        with patch('sys.argv', ['cli.py', '--num-tests', '10']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 1 for errors
            assert exc_info.value.code == 1


class TestIntegration:
    """Integration tests with minimal real execution"""
    
    def test_help_message(self):
        """Test that --help works"""
        with patch('sys.argv', ['cli.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                parse_args()
            # Help should exit with 0
            assert exc_info.value.code == 0
