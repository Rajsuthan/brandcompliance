#!/usr/bin/env python3
"""
Script to run the benchmark.

This script reads the benchmark Excel file, runs the benchmark on each test case,
and saves the results to a JSON file.
"""

import os
import sys
import json
import asyncio
import argparse
from app.core.benchmark.excel_reader import read_and_analyze_benchmark, update_excel_with_results
from app.core.benchmark.benchmark_runner import run_benchmark

async def main(args):
    """Main function to run the benchmark."""
    print(f"Running benchmark with Excel file: {args.excel}")
    if args.mapping:
        print(f"Using asset mapping file: {args.mapping}")
    if args.asset_dir:
        print(f"Using asset directory: {args.asset_dir}")
    print(f"Saving results to: {args.output}")
    print(f"Using model: {args.model}")
    if args.test_id:
        print(f"Running only test case: {args.test_id}")

    try:
        # Read the benchmark Excel file
        results = read_and_analyze_benchmark(
            args.excel,
            asset_dir=args.asset_dir,
            mapping_file=args.mapping
        )

        # Filter test cases if test_id is provided
        test_cases = results["valid_test_cases"]
        if args.test_id:
            test_cases = [tc for tc in test_cases if tc["test_id"] == args.test_id]
            if not test_cases:
                print(f"No test case found with ID: {args.test_id}")
                return

        # Run the benchmark
        benchmark_results = await run_benchmark(
            test_cases,
            model=args.model,
            api_key=args.api_key,
            max_concurrent=args.concurrent,
            output_file=args.output,
            evaluate=not args.no_evaluate,
            use_gemini_evaluator=not args.default_evaluator
        )

        # Print summary
        completed = sum(1 for tc in benchmark_results if tc.get("status") == "completed")
        failed = sum(1 for tc in benchmark_results if tc.get("status") == "failed")
        skipped = sum(1 for tc in benchmark_results if tc.get("status") == "skipped")

        print("\n=== Benchmark Summary ===")
        print(f"Total test cases: {len(benchmark_results)}")
        print(f"Completed: {completed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")

        # Print average processing time for completed test cases
        if completed > 0:
            avg_time = sum(tc.get("processing_time", 0) for tc in benchmark_results if tc.get("status") == "completed") / completed
            print(f"Average processing time: {avg_time:.2f} seconds")

        # Print evaluation summary if available
        evaluated = sum(1 for tc in benchmark_results if "evaluation" in tc)
        if evaluated > 0:
            avg_score = sum(tc.get("evaluation", {}).get("score", 0) for tc in benchmark_results if "evaluation" in tc) / evaluated
            print("\n=== Evaluation Summary ===")
            print(f"Evaluated test cases: {evaluated}")
            print(f"Average score: {avg_score:.2f}/100")

            # Print score distribution
            score_ranges = {
                "Excellent (90-100)": sum(1 for tc in benchmark_results if tc.get("evaluation", {}).get("score", 0) >= 90),
                "Good (70-89)": sum(1 for tc in benchmark_results if 70 <= tc.get("evaluation", {}).get("score", 0) < 90),
                "Fair (50-69)": sum(1 for tc in benchmark_results if 50 <= tc.get("evaluation", {}).get("score", 0) < 70),
                "Poor (0-49)": sum(1 for tc in benchmark_results if tc.get("evaluation", {}).get("score", 0) < 50)
            }

            for range_name, count in score_ranges.items():
                print(f"{range_name}: {count}")

            # Print top and bottom performing test cases
            if evaluated >= 3:
                top_cases = sorted(
                    [tc for tc in benchmark_results if "evaluation" in tc],
                    key=lambda tc: tc.get("evaluation", {}).get("score", 0),
                    reverse=True
                )[:3]

                bottom_cases = sorted(
                    [tc for tc in benchmark_results if "evaluation" in tc],
                    key=lambda tc: tc.get("evaluation", {}).get("score", 0)
                )[:3]

                print("\nTop performing test cases:")
                for tc in top_cases:
                    print(f"  {tc.get('test_id')}: {tc.get('evaluation', {}).get('score', 0)}/100")

                print("\nBottom performing test cases:")
                for tc in bottom_cases:
                    print(f"  {tc.get('test_id')}: {tc.get('evaluation', {}).get('score', 0)}/100")

        print(f"\nResults saved to {args.output}")

        # Update the Excel file with the benchmark results
        if not args.no_excel_update:
            try:
                print(f"Updating Excel file: {args.excel}")
                update_excel_with_results(args.excel, benchmark_results)
                print(f"Excel file updated successfully")
            except Exception as excel_error:
                print(f"Warning: Failed to update Excel file: {str(excel_error)}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the benchmark on test cases from an Excel file.")

    parser.add_argument("--excel", default="benchmark/benchark_excel.xlsx",
                        help="Path to the benchmark Excel file")

    parser.add_argument("--mapping", default="benchmark/asset_mapping.json",
                        help="Path to the asset mapping file")

    parser.add_argument("--asset-dir", default=None,
                        help="Base directory for asset paths")

    parser.add_argument("--output", default="benchmark_results.json",
                        help="Path to save the results")

    parser.add_argument("--model", default="anthropic/claude-3.7-sonnet",
                        help="Model to use for compliance checking")

    parser.add_argument("--api-key",
                        default="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",
                        help="API key for the LLM service (default: hardcoded OpenRouter API key)")

    parser.add_argument("--concurrent", type=int, default=1,
                        help="Maximum number of concurrent test cases to run")

    parser.add_argument("--test-id", default=None,
                        help="Run only a specific test case by ID")

    parser.add_argument("--no-evaluate", action="store_true",
                        help="Skip evaluation of results")

    parser.add_argument("--default-evaluator", action="store_true",
                        help="Use the default evaluator instead of the Gemini evaluator")

    parser.add_argument("--no-excel-update", action="store_true",
                        help="Skip updating the Excel file with benchmark results")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
