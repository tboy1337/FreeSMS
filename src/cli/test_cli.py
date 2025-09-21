#!/usr/bin/env python3
"""
Test script for CLI functionality
"""
import os
import sys
import subprocess
from datetime import datetime, timedelta

def main():
    """Run CLI test commands"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Commands to test
    commands = [
        ["python", "run.py", "cli", "--help"],
        ["python", "run.py", "cli", "services", "list"],
        ["python", "run.py", "cli", "services", "test"],
        ["python", "run.py", "cli", "contacts", "list"],
        ["python", "run.py", "cli", "contacts", "template", "contacts_template.csv"],
        ["python", "run.py", "cli", "contacts", "export", "contacts_export.csv"],
        ["python", "run.py", "cli", "templates", "list"],
        ["python", "run.py", "cli", "history", "list", "--limit", "5"],
        ["python", "run.py", "cli", "schedule", "list"],
        # Schedule a message for tomorrow
        ["python", "run.py", "cli", "schedule", "add", "+12345678901", 
         "This is a test scheduled message", 
         (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')],
        # List scheduled messages after adding
        ["python", "run.py", "cli", "schedule", "list"],
        # Test recurring schedule
        ["python", "run.py", "cli", "schedule", "add", "+12345678901", 
         "This is a recurring test message", 
         (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
         "--recurring", "daily"],
        # Export message history to CSV
        ["python", "run.py", "cli", "history", "export", "message_history.csv", "--limit", "100"],
        # Import contacts (will use the template created earlier)
        ["python", "run.py", "cli", "contacts", "import", "contacts_template.csv"],
    ]
    
    # Run each command
    for cmd in commands:
        print(f"\n{'='*50}")
        print(f"Running: {' '.join(cmd)}")
        print(f"{'='*50}")
        try:
            result = subprocess.run(cmd, cwd=script_dir, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"ERROR: {result.stderr}")
        except Exception as e:
            print(f"Error running command: {e}")

if __name__ == "__main__":
    main() 