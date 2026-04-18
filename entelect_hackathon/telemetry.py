"""
telemetry.py — Human-readable race telemetry printer.
"""

from simulator import RaceResult


def print_telemetry(race_result: RaceResult):
    print(f"\n{'='*70}")
    print(f"  RACE TELEMETRY")
    print(f"{'='*70}")

    for lap in race_result.laps:
        print(f"\n--- LAP {lap.lap:3d}  (lap time: {lap.total_lap_time:8.3f}s, pit: {lap.pit_time:.1f}s) ---")
        for seg in lap.segments:
            flags = []
            if seg.crashed:
                flags.append("CRASH")
            if seg.limp_triggered:
                flags.append("LIMP!")
            if seg.blowout:
                flags.append("BLOWOUT!")
            if seg.notes:
                flags.append(seg.notes)
            flag_str = " ".join(flags)
            print(
                f"  Seg {seg.segment_id:2d} | "
                f"time={seg.time_s:8.3f}s | "
                f"v_in={seg.entry_speed:5.1f} v_out={seg.exit_speed:5.1f} peak={seg.peak_speed:5.1f} m/s | "
                f"fuel_used={seg.fuel_used_l:.4f}L | "
                f"deg+={seg.deg_added:.6f} | "
                f"{flag_str}"
            )

    print(f"\n{'='*70}")
    print(f"  TOTAL TIME : {race_result.total_time:.3f} s")
    print(f"  FUEL USED  : {race_result.fuel_used:.3f} L")
    print(f"  CRASHES    : {race_result.crashes}")
    print(f"  BLOWOUTS   : {race_result.blowouts}")
    print(f"{'='*70}\n")


def compute_score(race_result: RaceResult, time_reference: float) -> float:
    """Level 1 scoring formula."""
    return 500_000 * (time_reference / race_result.total_time) ** 3