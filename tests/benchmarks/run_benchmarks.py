#!/usr/bin/env python3
"""Istara Orchestration Benchmark Runner — Layer 4.

Standalone runner for the orchestration benchmark suite. Can run in two modes:

1. Unit Test Mode (default): Runs all benchmarks with mocked responses.
   No database or LLM server required. Fast (~2-5 seconds).

   Usage: python tests/benchmarks/run_benchmarks.py

2. JSON Output Mode: Same as above but outputs results as JSON for CI/CD.

   Usage: python tests/benchmarks/run_benchmarks.py --json results.json

3. Full Integration Mode: Runs benchmarks against live Istara instance.
   Requires docker compose up and a running LLM server. Slow (~60+ seconds).

   Usage: python tests/benchmarks/run_benchmarks.py --integration --base-url http://localhost:8000

Architecture:
- Each benchmark is self-contained with mocked LLM responses (unit mode)
- Results include timing, accuracy, and statistical significance metrics
- Designed for CI/CD pipeline integration via JSON output mode
- Can also be run as pytest: pytest tests/benchmarks/test_orchestration.py -v

Usage:
    # Run all benchmarks (unit test mode)
    python tests/benchmarks/run_benchmarks.py

    # Run with JSON output for CI/CD
    python tests/benchmarks/run_benchmarks.py --json results.json

    # Run specific benchmark only
    python tests/benchmarks/run_benchmarks.py --benchmark long_horizon_dag

    # Full integration mode (requires live server)
    python tests/benchmarks/run_benchmarks.py --integration
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parents[2] / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("IstaraBenchmarkRunner")


async def run_benchmarks(benchmark_filter: str | None = None) -> Dict[str, Any]:
    """Run all orchestration benchmarks and return results.

    Args:
        benchmark_filter: If provided, only run this specific benchmark.
                        Options: long_horizon_dag, tool_calling_accuracy,
                                 a2a_consensus, async_steering_responsiveness

    Returns:
        Dictionary with aggregate results and per-benchmark details.
    """
    from tests.benchmarks.test_orchestration import (
        test_long_horizon_dag_decomposition,
        test_tool_calling_accuracy_resilience,
        test_a2a_mathematical_consensus,
        test_async_steering_responsiveness,
    )

    benchmarks = {
        "long_horizon_dag": (
            "Long-Horizon DAG Decomposition",
            test_long_horizon_dag_decomposition,
        ),
        "tool_calling_accuracy": (
            "Tool-Calling Accuracy & Resilience",
            test_tool_calling_accuracy_resilience,
        ),
        "a2a_consensus": (
            "A2A Mathematical Consensus",
            test_a2a_mathematical_consensus,
        ),
        "async_steering_responsiveness": (
            "Async Steering Responsiveness",
            test_async_steering_responsiveness,
        ),
    }

    if benchmark_filter:
        # Run only the specified benchmark
        if benchmark_filter not in benchmarks:
            logger.error(f"Unknown benchmark: {benchmark_filter}")
            logger.info(f"Available: {', '.join(benchmarks.keys())}")
            sys.exit(1)

        name, fn = benchmarks[benchmark_filter]
        logger.info(f"Running single benchmark: {name}")
        results = await _run_single_benchmark(name, fn)
    else:
        # Run all benchmarks
        logger.info("=" * 70)
        logger.info("🚀 Istara Orchestration Benchmark Suite (Layer 4)")
        logger.info("=" * 70)

        results = {}
        for key, (name, fn) in benchmarks.items():
            result = await _run_single_benchmark(name, fn)
            results[key] = result

    return {
        "suite": "full_orchestration",
        "benchmarks": results,
    }


async def _run_single_benchmark(name: str, fn) -> Dict[str, Any]:
    """Run a single benchmark and capture its result."""
    start_time = time.monotonic()

    try:
        logger.info(f"\n▶️  Running: {name}")
        logger.info("-" * len(name))

        result = await fn()
        elapsed_ms = (time.monotonic() - start_time) * 1000

        if isinstance(result, dict):
            result["benchmark"] = name.lower().replace(" ", "_")
            result["status"] = "PASS"
            result["execution_time_ms"] = round(elapsed_ms, 2)

            logger.info(f"✅ {name}: PASS ({elapsed_ms:.1f}ms)")
        else:
            result = {
                "benchmark": name.lower().replace(" ", "_"),
                "status": "ERROR",
                "error": "Unexpected return type",
            }
            logger.error(f"❌ {name}: ERROR - Unexpected return type")

    except AssertionError as e:
        elapsed_ms = (time.monotonic() - start_time) * 1000
        result = {
            "benchmark": name.lower().replace(" ", "_"),
            "status": "FAIL",
            "error": str(e),
        }
        logger.error(f"❌ {name}: FAIL — {e}")

    except Exception as e:
        elapsed_ms = (time.monotonic() - start_time) * 1000
        result = {
            "benchmark": name.lower().replace(" ", "_"),
            "status": "ERROR",
            "error": str(e),
        }
        logger.error(f"❌ {name}: ERROR — {e}")

    return result


def print_summary(results: Dict[str, Any]) -> None:
    """Print a formatted summary of benchmark results."""
    benchmarks = results.get("benchmarks", {})

    total = len(benchmarks)
    passed = sum(1 for b in benchmarks.values() if b.get("status") == "PASS")
    failed = sum(1 for b in benchmarks.values() if b.get("status") in ("FAIL", "ERROR"))

    logger.info("\n" + "=" * 70)
    logger.info(f"BENCHMARK SUITE RESULTS: {passed}/{total} passed, {failed} failed")
    logger.info("=" * 70)

    for key, bench_result in benchmarks.items():
        status_icon = "✅" if bench_result.get("status") == "PASS" else "❌"
        exec_time = bench_result.get("execution_time_ms", 0)
        error = bench_result.get("error", "")

        logger.info(f"\n{status_icon} {key}:")
        logger.info(f"   Status:     {bench_result.get('status', 'UNKNOWN')}")
        logger.info(f"   Time:       {exec_time:.1f}ms")
        if error:
            logger.info(f"   Error:      {error}")

        # Print key metrics for passing benchmarks
        if bench_result.get("status") == "PASS":
            for metric_key, metric_val in bench_result.items():
                if metric_key not in ("benchmark", "status", "execution_time_ms"):
                    logger.info(f"   {metric_key}: {metric_val}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Istara Orchestration Benchmark Runner (Layer 4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_benchmarks.py                          # Run all benchmarks
  python run_benchmarks.py --json results.json      # JSON output for CI/CD
  python run_benchmarks.py --benchmark long_horizon_dag  # Single benchmark
        """,
    )

    parser.add_argument(
        "--benchmark",
        "-b",
        type=str,
        default=None,
        help="Run only this specific benchmark (options: long_horizon_dag, tool_calling_accuracy, a2a_consensus, async_steering_responsiveness)",
    )

    parser.add_argument(
        "--json",
        "-j",
        type=str,
        default=None,
        metavar="FILE",
        help="Output results to JSON file",
    )

    args = parser.parse_args()

    # Run benchmarks
    results = asyncio.run(run_benchmarks(args.benchmark))

    # Print summary
    print_summary(results)

    # Save JSON if requested
    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"\n📄 Results saved to {args.json}")

    # Exit code for CI/CD gating
    failed = sum(
        1
        for b in results.get("benchmarks", {}).values()
        if b.get("status") in ("FAIL", "ERROR")
    )

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
