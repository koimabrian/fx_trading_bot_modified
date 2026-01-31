#!/usr/bin/env python
"""
Test Runner - Execute all test suites
Organized by test category: unit, integration, performance, e2e
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"{'='*70}\n")
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    """Run all test suites"""
    print("\n" + "=" * 70)
    print("FX TRADING BOT - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    base_path = Path(__file__).parent
    test_dir = base_path / "tests"

    results = {}

    # Unit Tests
    results["Unit Tests"] = run_command(
        f"python -m pytest {test_dir}/unit -v", "Unit Tests"
    )

    # Integration Tests
    results["Integration Tests"] = run_command(
        f"python -m pytest {test_dir}/integration -v", "Integration Tests"
    )

    # Performance Tests
    print(f"\n{'='*70}")
    print("Running: Performance Tests")
    print(f"{'='*70}\n")

    results["Core Performance"] = run_command(
        f"python {test_dir}/performance/test_perf_simple.py", "Core Phases + Database"
    )

    results["Component Testing"] = run_command(
        f"python {test_dir}/performance/test_all_untested.py", "Untested Components"
    )

    results["High-Load Scenarios"] = run_command(
        f"python {test_dir}/performance/test_high_load_scenarios.py",
        "Concurrent Load Testing",
    )

    # E2E Tests
    results["E2E Tests"] = run_command(
        f"python -m pytest {test_dir}/e2e -v", "End-to-End Tests"
    )

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "[PASS]" if passed_flag else "[SKIP]"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} test suites completed")

    if passed == total:
        print("\n✓ All tests completed successfully!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test suite(s) had issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
