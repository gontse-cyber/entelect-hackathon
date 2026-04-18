import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from utils import (
    accel_time, accel_distance, brake_exit_speed,
    fuel_used, max_corner_speed, compute_tyre_friction,
    deg_straight, deg_braking, deg_corner,
    get_weather, BASE_FRICTION,
)
from level_loader import Level, WeatherCondition


#Data structures

@dataclass
class CarState:
    speed: float              
    fuel: float               
    tyre_id: int              
    tyre_compound: str        # 'Soft', 'Medium', …
    tyre_degradation: float   # accumulated degradation on active set
    race_time: float          # elapsed race time in seconds
    in_limp: bool             
    in_crawl: bool            # True if just crashed a corner
    lap: int
    blowout_count: int = 0
    crash_count: int = 0

    def copy(self):
        return deepcopy(self)


@dataclass
class SegmentResult:
    segment_id: int
    time_s: float
    fuel_used_l: float
    deg_added: float
    entry_speed: float
    exit_speed: float
    peak_speed: float
    crashed: bool
    limp_triggered: bool
    blowout: bool
    notes: str = ""


@dataclass
class LapResult:
    lap: int
    segments: List[SegmentResult]
    pit_time: float
    total_lap_time: float     # segment times only (pit is separate)


@dataclass
class RaceResult:
    total_time: float
    fuel_used: float
    laps: List[LapResult]
    tyre_history: List[Dict]
    crashes: int
    blowouts: int


#Weather helpers 

def _get_active_weather(state: CarState, level: Level) -> WeatherCondition:
    """Return the WeatherCondition active at the current race time."""
    return get_weather(state.race_time, level.weather_conditions)


def _weather_condition_name(weather: WeatherCondition) -> str:
    return weather.condition


# Straight simulation

def simulate_straight(seg, state: CarState, strat_seg: dict, weather: WeatherCondition, level: Level):
    """
    Simulate all three phases of a straight segment.
    Returns (SegmentResult, new_state).
    """
    new_state = state.copy()
    entry_speed = state.speed
    straight_length = seg.length_m

    #Limp mode: skip all physics 
    if state.in_limp:
        t = straight_length / level.car.limp_speed
        fuel = fuel_used(level.car.limp_speed, level.car.limp_speed, straight_length)
        new_state.fuel = max(0.0, new_state.fuel - fuel)
        new_state.race_time += t
        new_state.speed = level.car.limp_speed
        new_state.in_crawl = False   # limp mode exits crawl on straights

        # Level 1: degrade straight even in limp (tyre still rolling)
        cond = weather.condition
        rate = level.get_degradation_rate(state.tyre_id, cond)
        new_state.tyre_degradation += deg_straight(rate, straight_length)

        return SegmentResult(
            segment_id=seg.id, time_s=t, fuel_used_l=fuel,
            deg_added=0, entry_speed=entry_speed,
            exit_speed=level.car.limp_speed, peak_speed=level.car.limp_speed,
            crashed=False, limp_triggered=False, blowout=False,
            notes="LIMP"
        ), new_state

    #Weather multipliers 
    accel_eff = level.car.accel * weather.acceleration_multiplier
    brake_eff = level.car.brake * weather.deceleration_multiplier
    crawl = level.car.crawl_speed
    max_speed = level.car.max_speed

    target_speed = min(float(strat_seg.get("target_m/s", max_speed)), max_speed)
    brake_start_m = float(strat_seg.get("brake_start_m_before_next", 0))

    # Assumption 11: entry speed ≥ target → no acceleration
    if entry_speed >= target_speed:
        cruise_speed = entry_speed
        dist_accel = 0.0
        time_accel = 0.0
        fuel_accel = 0.0
        deg_accel = 0.0
    else:
        cruise_speed = target_speed
        dist_accel = accel_distance(entry_speed, cruise_speed, accel_eff)
        time_accel = accel_time(entry_speed, cruise_speed, accel_eff)
        fuel_accel = fuel_used(entry_speed, cruise_speed, dist_accel)
        cond = weather.condition
        rate = level.get_degradation_rate(state.tyre_id, cond)
        deg_accel = deg_straight(rate, dist_accel)

    # Edge case: accel + brake > straight_length 
    available_for_brake = straight_length - dist_accel
    if available_for_brake <= 0:
        # No room: car is still accelerating through the entire straight.
        # Find exit speed using kinematics: v² = u² + 2as
        v_exit_sq = entry_speed ** 2 + 2 * accel_eff * straight_length
        v_exit = math.sqrt(min(v_exit_sq, max_speed ** 2))
        v_exit = max(crawl, v_exit)

        t = (v_exit - entry_speed) / accel_eff
        f = fuel_used(entry_speed, v_exit, straight_length)
        cond = weather.condition
        rate = level.get_degradation_rate(state.tyre_id, cond)
        d = deg_straight(rate, straight_length)

        new_state.speed = v_exit
        new_state.race_time += t
        new_state.fuel = max(0.0, new_state.fuel - f)
        new_state.tyre_degradation += d
        new_state.in_crawl = False

        return SegmentResult(
            segment_id=seg.id, time_s=t, fuel_used_l=f,
            deg_added=d, entry_speed=entry_speed,
            exit_speed=v_exit, peak_speed=v_exit,
            crashed=False, limp_triggered=False, blowout=False,
            notes="FULL_ACCEL"
        ), new_state

    # Available braking distance (capped by actual straight remaining)
    actual_brake = min(brake_start_m, available_for_brake)
    dist_cruise = available_for_brake - actual_brake

    cond = weather.condition
    rate = level.get_degradation_rate(state.tyre_id, cond)

    # Phase 2: cruise 
    if dist_cruise > 0:
        time_cruise = dist_cruise / cruise_speed
        fuel_cruise = fuel_used(cruise_speed, cruise_speed, dist_cruise)
        deg_cruise = deg_straight(rate, dist_cruise)
    else:
        time_cruise = 0.0
        fuel_cruise = 0.0
        deg_cruise = 0.0

    # Phase 3: braking 
    v_exit = brake_exit_speed(cruise_speed, brake_eff, actual_brake)
    v_exit = max(crawl, v_exit)
    time_brake = (cruise_speed - v_exit) / brake_eff if actual_brake > 0 else 0.0
    fuel_brake = fuel_used(cruise_speed, v_exit, actual_brake)
    deg_brake_val = deg_braking(rate, cruise_speed, v_exit)
    deg_brake_straight = deg_straight(rate, actual_brake)

    # Totals
    total_time = time_accel + time_cruise + time_brake
    total_fuel = fuel_accel + fuel_cruise + fuel_brake
    total_deg = deg_accel + deg_cruise + deg_brake_val + deg_brake_straight

    # Fuel depletion check
    limp_triggered = False
    if total_fuel > new_state.fuel:
        # Simplified: enter limp from this point — remaining segment at limp speed
        limp_triggered = True
        new_state.in_limp = True
        total_fuel = new_state.fuel

    new_state.fuel = max(0.0, new_state.fuel - total_fuel)
    new_state.race_time += total_time
    new_state.speed = v_exit
    new_state.tyre_degradation += total_deg
    new_state.in_crawl = False   # reaching a straight resets crawl

    # Blowout check (Level 4 relevant, but guard always present) 
    blowout = False
    if new_state.tyre_degradation >= level.get_life_span(state.tyre_id):
        blowout = True
        new_state.in_limp = True
        new_state.blowout_count += 1

    return SegmentResult(
        segment_id=seg.id,
        time_s=total_time,
        fuel_used_l=total_fuel,
        deg_added=total_deg,
        entry_speed=entry_speed,
        exit_speed=v_exit,
        peak_speed=cruise_speed,
        crashed=False,
        limp_triggered=limp_triggered,
        blowout=blowout,
    ), new_state


# Corner simulation 

def simulate_corner(seg, state: CarState, weather: WeatherCondition, level: Level):
    """
    Simulate a corner segment. Returns (SegmentResult, new_state).
    """
    new_state = state.copy()
    entry_speed = state.speed
    crawl = level.car.crawl_speed
    cond = weather.condition

    # Limp mode 
    if state.in_limp:
        t = seg.length_m / level.car.limp_speed
        f = fuel_used(level.car.limp_speed, level.car.limp_speed, seg.length_m)
        new_state.fuel = max(0.0, new_state.fuel - f)
        new_state.race_time += t
        new_state.speed = level.car.limp_speed
        rate = level.get_degradation_rate(state.tyre_id, cond)
        d = deg_corner(rate, level.car.limp_speed, seg.radius_m)
        new_state.tyre_degradation += d
        return SegmentResult(
            segment_id=seg.id, time_s=t, fuel_used_l=f,
            deg_added=d, entry_speed=entry_speed,
            exit_speed=level.car.limp_speed, peak_speed=level.car.limp_speed,
            crashed=False, limp_triggered=False, blowout=False,
            notes="LIMP"
        ), new_state

    # Compute tyre friction
    base_coeff = level.get_base_friction(state.tyre_id)
    friction_mult = level.get_friction_mult(state.tyre_id, cond)
    tyre_friction = compute_tyre_friction(base_coeff, state.tyre_degradation, friction_mult)
    max_spd = max_corner_speed(tyre_friction, seg.radius_m, crawl)

    # Crawl mode: skip safety check, use crawl speed 
    if state.in_crawl:
        corner_speed = crawl
        crashed = False
        new_state.in_crawl = False   # reset on reaching next corner (already in crawl)
        # Note: in_crawl resets when a STRAIGHT is reached — but consecutive corners
        # in crawl mode stay at crawl speed. Keep in_crawl True for next segment
        # until a straight is found.
        new_state.in_crawl = True   # stays True until a straight resets it
    elif entry_speed > max_spd:
        # CRASH 
        crashed = True
        new_state.race_time += level.race.corner_crash_penalty
        new_state.tyre_degradation += 0.1
        new_state.in_crawl = True
        corner_speed = crawl
        new_state.crash_count += 1
    else:
        crashed = False
        corner_speed = entry_speed

    # Corner time, fuel, degradation 
    t = seg.length_m / corner_speed
    f = fuel_used(corner_speed, corner_speed, seg.length_m)
    rate = level.get_degradation_rate(state.tyre_id, cond)
    d = deg_corner(rate, corner_speed, seg.radius_m)

    # Fuel check
    limp_triggered = False
    if f > new_state.fuel:
        limp_triggered = True
        new_state.in_limp = True
        f = new_state.fuel

    new_state.fuel = max(0.0, new_state.fuel - f)
    new_state.race_time += t
    new_state.speed = corner_speed
    new_state.tyre_degradation += d

    # Blowout check
    blowout = False
    if new_state.tyre_degradation >= level.get_life_span(state.tyre_id):
        blowout = True
        new_state.in_limp = True
        new_state.blowout_count += 1

    return SegmentResult(
        segment_id=seg.id,
        time_s=t + (level.race.corner_crash_penalty if crashed else 0),
        fuel_used_l=f,
        deg_added=d,
        entry_speed=entry_speed,
        exit_speed=corner_speed,
        peak_speed=corner_speed,
        crashed=crashed,
        limp_triggered=limp_triggered,
        blowout=blowout,
    ), new_state


# Pit stop simulation 

def simulate_pit(pit_action: dict, state: CarState, level: Level):
    """
    Apply pit stop actions. Returns (new_state, pit_time_seconds).
    pit_action keys: 'enter', 'tyre_change_set_id', 'fuel_refuel_amount_l'
    """
    if not pit_action.get("enter", False):
        return state, 0.0

    new_state = state.copy()
    pit_time = level.race.base_pit_stop_time

    # Tyre change
    if pit_action.get("tyre_change_set_id"):
        tyre_id = pit_action["tyre_change_set_id"]
        new_state.tyre_id = tyre_id
        new_state.tyre_compound = level.get_compound_for_id(tyre_id)
        new_state.tyre_degradation = 0.0   # fresh set; Level 4 would track per-ID wear
        pit_time += level.race.pit_tyre_swap_time

    # Refuel 
    refuel_amount = pit_action.get("fuel_refuel_amount_l", 0)
    if refuel_amount and refuel_amount > 0:
        max_refuel = level.car.fuel_tank_capacity - new_state.fuel
        actual_refuel = min(refuel_amount, max_refuel)
        pit_time += actual_refuel / level.race.pit_refuel_rate
        new_state.fuel += actual_refuel

    # Reset limp mode if root cause fixed
    if new_state.fuel > 0 and new_state.tyre_degradation < level.get_life_span(new_state.tyre_id):
        new_state.in_limp = False

    # Exit speed
    new_state.speed = level.race.pit_exit_speed
    new_state.race_time += pit_time

    return new_state, pit_time


# Lap simulation

def simulate_lap(lap_strategy: dict, state: CarState, level: Level):
    """
    Simulate a single lap using the provided strategy.
    Returns (LapResult, new_state).
    """
    lap_start_time = state.race_time
    seg_results: List[SegmentResult] = []

    # Build a lookup of strategy segment data by segment ID
    strat_segs = {s["id"]: s for s in lap_strategy.get("segments", [])}

    for seg in level.segments:
        weather = _get_active_weather(state, level)
        strat_seg = strat_segs.get(seg.id, {})

        if seg.type == "straight":
            result, state = simulate_straight(seg, state, strat_seg, weather, level)
        elif seg.type == "corner":
            result, state = simulate_corner(seg, state, weather, level)
        else:
            raise ValueError(f"Unknown segment type: {seg.type}")

        seg_results.append(result)

    # Pit stop
    pit_action = lap_strategy.get("pit", {"enter": False})
    state, pit_time = simulate_pit(pit_action, state, level)

    lap_time = state.race_time - lap_start_time - pit_time
    return LapResult(
        lap=lap_strategy["lap"],
        segments=seg_results,
        pit_time=pit_time,
        total_lap_time=lap_time,
    ), state


# Race simulation

def simulate_race(strategy: dict, level: Level) -> RaceResult:
    """
    Simulate the full race.
    strategy: parsed JSON with 'initial_tyre_id' and 'laps' list.
    Returns RaceResult with total_time and fuel_used as top-level fields.
    """
    initial_tyre_id = strategy["initial_tyre_id"]
    state = CarState(
        speed=0.0,
        fuel=level.car.initial_fuel,
        tyre_id=initial_tyre_id,
        tyre_compound=level.get_compound_for_id(initial_tyre_id),
        tyre_degradation=0.0,
        race_time=0.0,
        in_limp=False,
        in_crawl=False,
        lap=1,
    )

    lap_results: List[LapResult] = []
    tyre_history: List[Dict] = []
    fuel_start = state.fuel

    for lap_strat in strategy["laps"]:
        state.lap = lap_strat["lap"]
        lap_result, state = simulate_lap(lap_strat, state, level)
        lap_results.append(lap_result)

        # Record tyre state after each lap
        tyre_history.append({
            "lap": lap_strat["lap"],
            "tyre_id": state.tyre_id,
            "compound": state.tyre_compound,
            "degradation": round(state.tyre_degradation, 6),
        })

    fuel_used_total = fuel_start - state.fuel

    return RaceResult(
        total_time=state.race_time,
        fuel_used=fuel_used_total,
        laps=lap_results,
        tyre_history=tyre_history,
        crashes=state.crash_count,
        blowouts=state.blowout_count,
    )