#!/usr/bin/env python3
"""
Run script for FreeSMS application
"""
import os
import sys
import subprocess

def main():
    """Run the FreeSMS application"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set the main script path
    main_script = os.path.join(script_dir, "src", "main.py")
    
    # Get command line arguments
    args = sys.argv[1:]
    
    # Set PYTHONPATH to include only our project
    env = os.environ.copy()
    env["PYTHONPATH"] = script_dir
    
    # Check if the first argument is 'cli' to run in CLI mode
    if len(args) > 0 and args[0] == 'cli':
        # Remove 'cli' from args and add --cli flag
        args = args[1:] + ["--cli"]
    
    # Prepare the command
    cmd = [sys.executable, main_script] + args
    
    # Run the application
    subprocess.run(cmd, env=env)

if __name__ == "__main__":
    main() 