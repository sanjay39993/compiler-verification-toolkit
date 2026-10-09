"""
Command-Line Interface for Differential Testing

Provides a simple CLI for running differential testing campaigns.
Reuses the run_differential_test() function from differential_tester.py.
"""

import argparse
import sys
from pathlib import Path

from src.differential_tester import run_differential_test, print_summary, save_summary


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Run differential testing for compiler verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Quick test with 10 expressions
  python -m src.cli --num-tests 10 --seed 0
  
  # Test specific optimization levels
  python -m src.cli --num-tests 50 --opt-levels 0 2 3
  
  # Full test campaign with saved results
  python -m src.cli --num-tests 100 --output-dir ./results --save-summary results.json
        '''
    )
    
    parser.add_argument(
        '--num-tests',
        type=int,
        default=100,
        help='Number of random expressions to generate (default: 100)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=0,
        help='Starting seed for reproducible generation (default: 0)'
    )
    
    parser.add_argument(
        '--opt-levels',
        type=int,
        nargs='+',
        default=[0, 1, 2, 3],
        choices=[0, 1, 2, 3],
        help='Optimization levels to test (default: 0 1 2 3)'
    )
    
    parser.add_argument(
        '--x-values',
        type=lambda x: int(x, 0),  # Accept hex like 0xFFFFFFFF
        nargs='+',
        default=[0, 1, 5, 100, 0xFFFFFFFF],
        help='Runtime input values to test (default: 0 1 5 100 0xFFFFFFFF)'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=4,
        help='Maximum expression tree depth (default: 4)'
    )
    
    parser.add_argument(
        '--max-const',
        type=int,
        default=1000,
        help='Maximum constant value in expressions (default: 1000)'
    )
    
    parser.add_argument(
        '--var-probability',
        type=float,
        default=0.3,
        help='Probability of generating variables vs constants (default: 0.3)'
    )
    
    parser.add_argument(
        '--compiler',
        type=str,
        default='g++',
        help='Compiler command (default: g++)'
    )
    
    parser.add_argument(
        '--compile-timeout',
        type=int,
        default=30,
        help='Compilation timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--execute-timeout',
        type=int,
        default=5,
        help='Execution timeout in seconds (default: 5)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Directory for generated files (default: temp directory)'
    )
    
    parser.add_argument(
        '--keep-files',
        action='store_true',
        help='Keep generated C++ files and binaries'
    )
    
    parser.add_argument(
        '--save-summary',
        type=Path,
        default=None,
        help='Save JSON summary to file'
    )
    
    return parser.parse_args()


def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Validate arguments
    if args.num_tests <= 0:
        print("Error: --num-tests must be positive", file=sys.stderr)
        sys.exit(1)
    
    if args.seed < 0:
        print("Error: --seed must be non-negative", file=sys.stderr)
        sys.exit(1)
    
    if args.max_depth < 0:
        print("Error: --max-depth must be non-negative", file=sys.stderr)
        sys.exit(1)
    
    if args.max_const <= 0:
        print("Error: --max-const must be positive", file=sys.stderr)
        sys.exit(1)
    
    if not (0.0 <= args.var_probability <= 1.0):
        print("Error: --var-probability must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)
    
    # Print configuration
    print("=" * 70)
    print("DIFFERENTIAL TESTING CONFIGURATION")
    print("=" * 70)
    print(f"Test expressions:     {args.num_tests}")
    print(f"Starting seed:        {args.seed}")
    print(f"Optimization levels:  {args.opt_levels}")
    print(f"X values:             {[hex(x) if x > 1000 else x for x in args.x_values]}")
    print(f"Max depth:            {args.max_depth}")
    print(f"Max constant:         {args.max_const}")
    print(f"Variable probability: {args.var_probability}")
    print(f"Compiler:             {args.compiler}")
    print(f"Output directory:     {args.output_dir or '(temporary)'}")
    print("=" * 70)
    print()
    
    # Calculate total tests
    total = args.num_tests * len(args.x_values)
    print(f"Running {total} tests ({args.num_tests} expressions × {len(args.x_values)} x-values)...")
    print("This may take a while depending on test count and optimization levels.")
    print()
    
    # Run differential testing
    try:
        summary = run_differential_test(
            num_tests=args.num_tests,
            seed_start=args.seed,
            opt_levels=args.opt_levels,
            x_values=args.x_values,
            max_depth=args.max_depth,
            max_const=args.max_const,
            var_probability=args.var_probability,
            compiler=args.compiler,
            compile_timeout=args.compile_timeout,
            execute_timeout=args.execute_timeout,
            output_dir=args.output_dir,
            keep_files=args.keep_files
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError during testing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Print results
    print()
    print_summary(summary)
    
    # Save summary if requested
    if args.save_summary:
        try:
            save_summary(summary, args.save_summary)
            print()
            print(f"Summary saved to: {args.save_summary}")
        except Exception as e:
            print(f"\n\nWarning: Could not save summary: {e}", file=sys.stderr)
    
    # Exit with appropriate code
    if summary.discrepancies > 0:
        print("\n⚠️  Discrepancies detected - manual investigation required")
        sys.exit(1)
    elif summary.compilation_failures > 0 or summary.execution_failures > 0:
        print("\n⚠️  Infrastructure failures detected - review test setup")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
