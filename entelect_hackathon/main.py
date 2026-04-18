import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from level_loader import load_level
from strategy_generator import generate_level1_strategy
from simulator import simulate_race
from telemetry import print_telemetry, compute_score


def main():
    parser = argparse.ArgumentParser(description="Entelect Grand Prix — Level 1 Strategy Generator")
    parser.add_argument("level_path", help="Path to the level JSON file")
    parser.add_argument("--output", default="submission.txt", help="Output file for submission JSON")
    parser.add_argument("--telemetry", action="store_true", help="Print lap-by-lap telemetry")
    parser.add_argument("--score-only", action="store_true", help="Print score and exit")
    args = parser.parse_args()

    # ── Load level ────────────────────────────────────────────────────────────
    print(f"Loading level: {args.level_path}", file=sys.stderr)
    level = load_level(args.level_path)
    print(f"  Race: {level.race.name}, {level.race.laps} laps", file=sys.stderr)
    print(f"  Track: {len(level.segments)} segments", file=sys.stderr)

    # ── Generate strategy ─────────────────────────────────────────────────────
    print("Generating Level 1 strategy...", file=sys.stderr)
    strategy = generate_level1_strategy(level)
    tyre_compound = level.get_compound_for_id(strategy["initial_tyre_id"])
    print(f"  Starting tyre: ID={strategy['initial_tyre_id']} ({tyre_compound})", file=sys.stderr)

    # ── Simulate race ─────────────────────────────────────────────────────────
    print("Simulating race...", file=sys.stderr)
    result = simulate_race(strategy, level)

    score = compute_score(result, level.race.time_reference)
    print(f"\n  Total time : {result.total_time:.3f} s", file=sys.stderr)
    print(f"  Fuel used  : {result.fuel_used:.3f} L", file=sys.stderr)
    print(f"  Crashes    : {result.crashes}", file=sys.stderr)
    print(f"  Blowouts   : {result.blowouts}", file=sys.stderr)
    print(f"  Score      : {score:.0f}", file=sys.stderr)

    if args.telemetry:
        print_telemetry(result)

    if args.score_only:
        print(f"{score:.0f}")
        return

    # ── Write submission JSON ─────────────────────────────────────────────────
    submission_json = json.dumps(strategy, indent=2)
    output_path = args.output
    with open(output_path, "w") as f:
        f.write(submission_json)
    print(f"\nSubmission written to: {output_path}", file=sys.stderr)

    # Also print to stdout for piping
    print(submission_json)


if __name__ == "__main__":
    main()