"""Example regression suite runner.

Discovers all example build.py files under examples/ and runs each one.
Reports success/failure for each example.

Run:
    PYTHONPATH=. .venv/bin/python examples/run_all.py
"""

import subprocess
import sys
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXAMPLES_DIR.parent


def discover_examples():
    """Find all build.py files under examples/."""
    build_files = sorted(EXAMPLES_DIR.glob("*/*/build.py"))
    # Exclude any build.py in __pycache__
    return [
        f for f in build_files
        if "__pycache__" not in str(f.relative_to(EXAMPLES_DIR))
    ]


def run_example(build_path, python_exe):
    """Run a single example build.py and return (success, output)."""
    try:
        result = subprocess.run(
            [python_exe, str(build_path)],
            cwd=str(PROJECT_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (60s)"
    except Exception as e:
        return False, str(e)


def main():
    python_exe = sys.executable
    examples = discover_examples()

    if not examples:
        print("No examples found!")
        sys.exit(1)

    print(f"Found {len(examples)} examples")
    print(f"Python: {python_exe}")
    print(f"Project root: {PROJECT_ROOT}")
    print("-" * 60)

    passed = 0
    failed = 0
    results = []

    for build_path in examples:
        rel_path = build_path.relative_to(EXAMPLES_DIR)
        success, output = run_example(build_path, python_exe)

        if success:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        results.append((rel_path, status, output))
        print(f"  {status}  {rel_path}")
        if not success:
            # Show first 3 lines of error
            for line in output.split("\n")[:3]:
                print(f"        {line}")

    print("-" * 60)
    print(f"Total: {len(examples)}  Passed: {passed}  Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
