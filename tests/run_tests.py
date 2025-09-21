#!/usr/bin/env python3
"""
Test runner for FreeSMS application
"""
import os
import sys
import unittest
import coverage

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def run_tests_with_coverage():
    """Run all tests with coverage reporting"""
    # Start coverage measurement
    cov = coverage.Coverage(
        source=['src'],
        omit=[
            '*/tests/*',
            '*/gui/*',  # Omit GUI modules for now
            '*/__pycache__/*',
            '*/__init__.py'
        ]
    )
    cov.start()
    
    # Discover and run tests
    loader = unittest.TestLoader()
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(tests_dir)
    
    # Run the tests
    print("\n========== Running Tests ==========\n")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Stop coverage measurement
    cov.stop()
    cov.save()
    
    # Report coverage results
    print("\n========== Coverage Report ==========\n")
    cov.report()
    
    # Save HTML report if requested
    if '--html' in sys.argv:
        html_dir = os.path.join(tests_dir, 'coverage_html')
        print(f"\nGenerating HTML coverage report in {html_dir}")
        cov.html_report(directory=html_dir)
    
    return len(result.failures) + len(result.errors)

def run_specific_test(test_path):
    """Run a specific test file or test case"""
    if not os.path.exists(test_path):
        print(f"Error: Test file {test_path} not found")
        return 1
    
    # Run the specific test
    print(f"\n========== Running Test: {test_path} ==========\n")
    return os.system(f"{sys.executable} {test_path}")

def main():
    """Main entry point for test runner"""
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        # Run a specific test
        return run_specific_test(sys.argv[1])
    else:
        # Run all tests with coverage
        return run_tests_with_coverage()

if __name__ == "__main__":
    sys.exit(main()) 