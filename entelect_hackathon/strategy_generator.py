import math
import json
from level_loader import Level, Segment
from utils import (
    accel_distance, accel_time, brake_exit_speed,
    max_corner_speed, compute_tyre_friction, BASE_FRICTION,
)

GRAVITY   = 9.8
FLOAT_EPS = 1e-6


# ── Tyre selection ─────────────────────────────────────────────────────────────

def best_tyre_id_for_dry(level: Level) -> int:
    """Return the tyre ID with the highest effective dry friction."""
    best_id, best_f = None, -1.0
    for ts in level.tyre_sets:
        tyre_id  = ts.ids[0]
        compound = ts.compound
        props    = level.tyre_properties[compound]
        friction = BASE_FRICTION[compound] * props.friction["dry"]
        if friction > best_f:
            best_f, best_id = friction, tyre_id
    return best_id


def _tyre_friction_static(level: Level, tyre_id: int) -> float:
    """Tyre friction in dry weather with zero degradation (Level 1 static)."""
    base = level.get_base_friction(tyre_id)
    mult = level.get_friction_mult(tyre_id, "dry")
    return base * mult


def _corner_max_speed(level: Level, seg: Segment, tyre_id: int) -> float:
    friction = _tyre_friction_static(level, tyre_id)
    return max_corner_speed(friction, seg.radius_m, level.car.crawl_speed)


# ── Optimal straight parameters ────────────────────────────────────────────────

def _compute_straight_params(
    level: Level,
    seg: Segment,
    entry_speed: float,
    required_exit_speed: float,
) -> tuple[float, float, float]:
    """
    Given an entry speed and a required exit speed for a straight, compute:
      - optimal target speed (maximum achievable peak speed)
      - brake_start_m_before_next (metres before end of straight to begin braking)
      - actual exit speed (after braking)

    Uses:
      dist_accel = (v_target² - v_entry²) / (2·a)
      dist_brake = (v_target² - v_exit²)  / (2·b)
      dist_accel + dist_brake ≤ L

    Solving for max v_target:
      v_target² ≤ (L + v_entry²/(2a) + v_exit²/(2b)) / (1/(2a) + 1/(2b))
    """
    accel_eff = level.car.accel   # dry weather → multiplier = 1
    brake_eff = level.car.brake
    max_speed = level.car.max_speed
    crawl     = level.car.crawl_speed
    L         = seg.length_m

    # Maximum target speed given distance constraints
    numer       = L + entry_speed**2 / (2*accel_eff) + required_exit_speed**2 / (2*brake_eff)
    denom       = 1/(2*accel_eff) + 1/(2*brake_eff)
    v_peak_max  = math.sqrt(max(0.0, numer / denom))
    target      = min(v_peak_max, max_speed)

    # Actual acceleration distance using real entry speed
    if entry_speed >= target:
        # No acceleration possible (entry already at or above target)
        dist_accel = 0.0
        cruise_spd = entry_speed
    else:
        dist_accel = accel_distance(entry_speed, target, accel_eff)
        cruise_spd = target

    remaining   = L - dist_accel
    if remaining < 0:
        # Shouldn't happen given the formula above, but guard
        remaining   = 0.0
        cruise_spd  = math.sqrt(entry_speed**2 + 2*accel_eff*L)
        cruise_spd  = min(cruise_spd, max_speed)

    # Braking distance from cruise_spd to required_exit_speed
    dist_brake  = (cruise_spd**2 - required_exit_speed**2) / (2*brake_eff)
    dist_brake  = max(0.0, min(dist_brake, remaining))

    # Actual exit speed after braking over dist_brake
    v_exit_sq   = cruise_spd**2 - 2*brake_eff*dist_brake
    v_exit      = max(crawl, math.sqrt(max(0.0, v_exit_sq)))

    return target, dist_brake, v_exit


# ── Single-lap forward pass ────────────────────────────────────────────────────

def _compute_lap_strategy(level: Level, tyre_id: int, entry_speed_lap: float) -> list:
    """
    Walk the track forward, tracking actual speeds and computing optimal
    target speeds + brake distances for each segment.
    Returns a list of strategy segment dicts.
    """
    segments = level.segments
    strat_segs = []

    # Pre-compute static max corner speeds
    corner_max = {}
    for seg in segments:
        if seg.type == "corner":
            corner_max[seg.id] = _corner_max_speed(level, seg, tyre_id)

    current_speed = entry_speed_lap

    for i, seg in enumerate(segments):
        if seg.type == "corner":
            # Car enters corner at current_speed; clamp to max safe speed
            safe_entry   = min(current_speed, corner_max[seg.id])
            current_speed = safe_entry  # constant through corner
            strat_segs.append({"id": seg.id, "type": "corner"})

        else:  # straight
            # Find required exit speed = max safe entry of next corner (if any)
            req_exit = level.car.crawl_speed  # default: last segment of lap
            for j in range(i+1, len(segments)):
                if segments[j].type == "corner":
                    req_exit = corner_max[segments[j].id]
                    break

            target, brake_dist, v_exit = _compute_straight_params(
                level, seg, current_speed, req_exit
            )

            strat_segs.append({
                "id"                        : seg.id,
                "type"                      : "straight",
                "target_m/s"                : round(target, 4),
                "brake_start_m_before_next" : round(brake_dist, 4),
            })
            current_speed = v_exit

    return strat_segs, current_speed   # return exit speed so we can chain laps


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_level1_strategy(level: Level) -> dict:
    """
    Generate the optimal Level 1 strategy.

    Because tyre degradation is irrelevant in Level 1, every lap uses the
    same tyre parameters. We do one forward-pass to get the steady-state
    lap strategy, then replicate it for all laps.
    """
    tyre_id = best_tyre_id_for_dry(level)

    # Lap 1 starts from rest (0 m/s).
    # From lap 2 onward the car re-enters at the exit speed of the last corner
    # of the previous lap. We do two passes:
    #  pass 1: from v=0 → get exit speed of last lap segment
    #  pass 2: from that exit speed → stable steady-state lap (use for all laps)

    strat_pass1, exit_speed_1 = _compute_lap_strategy(level, tyre_id, 0.0)
    strat_steady, _           = _compute_lap_strategy(level, tyre_id, exit_speed_1)

    laps = []
    for lap_num in range(1, level.race.laps + 1):
        segs = strat_pass1 if lap_num == 1 else strat_steady
        laps.append({
            "lap"      : lap_num,
            "segments" : [dict(s) for s in segs],
            "pit"      : {"enter": False},
        })

    return {
        "initial_tyre_id": tyre_id,
        "laps"           : laps,
    }