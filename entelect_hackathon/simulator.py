import math
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Dict

from utils import (
    accel_time, accel_distance, brake_exit_speed,
    fuel_used, max_corner_speed, compute_tyre_friction,
    deg_straight, deg_braking, deg_corner,
    get_weather,
)
from level_loader import Level, WeatherCondition


# =====================
# DATA STRUCTURES
# =====================

@dataclass
class CarState:
    speed: float
    fuel: float
    tyre_id: int
    tyre_compound: str
    tyre_degradation: float
    race_time: float
    in_limp: bool
    in_crawl: bool
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
    total_lap_time: float


@dataclass
class RaceResult:
    total_time: float
    fuel_used: float
    laps: List[LapResult]
    tyre_history: List[Dict]
    crashes: int
    blowouts: int


# =====================
# WEATHER
# =====================

def _get_active_weather(state: CarState, level: Level) -> WeatherCondition:
    return get_weather(state.race_time, level.weather_conditions)


# =====================
# STRAIGHT
# =====================

def simulate_straight(seg, state: CarState, strat_seg: dict, weather, level: Level):
    new_state = state.copy()
    entry_speed = state.speed
    L = seg.length_m

    if state.in_limp:
        v = level.car.limp_speed
        t = L / v
        f = fuel_used(v, v, L)

        new_state.speed = v
        new_state.fuel -= f
        new_state.race_time += t
        new_state.in_crawl = False

        return SegmentResult(seg.id, t, f, 0, entry_speed, v, v, False, False, False), new_state

    accel = level.car.accel * weather.acceleration_multiplier
    brake = level.car.brake * weather.deceleration_multiplier
    max_speed = level.car.max_speed
    crawl = level.car.crawl_speed

    target = min(strat_seg.get("target_m/s", max_speed), max_speed)
    brake_dist = strat_seg.get("brake_start_m_before_next", 0)

    # ACCELERATION
    if entry_speed >= target:
        v_peak = entry_speed
        d_accel = 0
        t_accel = 0
    else:
        v_peak = target
        d_accel = accel_distance(entry_speed, v_peak, accel)
        t_accel = accel_time(entry_speed, v_peak, accel)

    # Not enough space
    if d_accel >= L:
        v_exit = math.sqrt(entry_speed**2 + 2 * accel * L)
        v_exit = min(v_exit, max_speed)

        t = (v_exit - entry_speed) / accel
        f = fuel_used(entry_speed, v_exit, L)

        new_state.speed = v_exit
        new_state.fuel -= f
        new_state.race_time += t

        return SegmentResult(seg.id, t, f, 0, entry_speed, v_exit, v_exit, False, False, False), new_state

    # CRUISE + BRAKE
    d_remaining = L - d_accel
    d_brake = min(brake_dist, d_remaining)
    d_cruise = d_remaining - d_brake

    t_cruise = d_cruise / v_peak if d_cruise > 0 else 0
    f_cruise = fuel_used(v_peak, v_peak, d_cruise)

    v_exit = brake_exit_speed(v_peak, brake, d_brake)
    v_exit = max(v_exit, crawl)

    t_brake = (v_peak - v_exit) / brake if d_brake > 0 else 0
    f_brake = fuel_used(v_peak, v_exit, d_brake)

    total_time = t_accel + t_cruise + t_brake
    total_fuel = f_cruise + f_brake

    new_state.speed = v_exit
    new_state.fuel -= total_fuel
    new_state.race_time += total_time
    new_state.in_crawl = False

    return SegmentResult(seg.id, total_time, total_fuel, 0, entry_speed, v_exit, v_peak, False, False, False), new_state


# =====================
# CORNER
# =====================

def simulate_corner(seg, state: CarState, weather, level: Level):
    new_state = state.copy()
    entry_speed = state.speed
    crawl = level.car.crawl_speed

    if state.in_limp:
        v = level.car.limp_speed
        t = seg.length_m / v
        f = fuel_used(v, v, seg.length_m)

        new_state.speed = v
        new_state.fuel -= f
        new_state.race_time += t

        return SegmentResult(seg.id, t, f, 0, entry_speed, v, v, False, False, False), new_state

    friction = compute_tyre_friction(
        level.get_base_friction(state.tyre_id),
        state.tyre_degradation,
        level.get_friction_mult(state.tyre_id, weather.condition)
    )

    max_speed_corner = max_corner_speed(friction, seg.radius_m, crawl)

    # CRASH
    if entry_speed > max_speed_corner:
        new_state.crash_count += 1
        new_state.race_time += level.race.corner_crash_penalty
        new_state.in_crawl = True
        v = crawl
        crashed = True
    else:
        v = entry_speed
        crashed = False
        new_state.in_crawl = False

    t = seg.length_m / v
    f = fuel_used(v, v, seg.length_m)

    new_state.speed = v
    new_state.fuel -= f
    new_state.race_time += t

    return SegmentResult(seg.id, t, f, 0, entry_speed, v, v, crashed, False, False), new_state


# =====================
# PIT
# =====================

def simulate_pit(pit_action: dict, state: CarState, level: Level):
    if not pit_action.get("enter", False):
        return state, 0

    new_state = state.copy()
    pit_time = level.race.base_pit_stop_time

    if pit_action.get("tyre_change_set_id"):
        tyre_id = pit_action["tyre_change_set_id"]
        new_state.tyre_id = tyre_id
        new_state.tyre_compound = level.get_compound_for_id(tyre_id)
        new_state.tyre_degradation = 0
        pit_time += level.race.pit_tyre_swap_time

    refuel = pit_action.get("fuel_refuel_amount_l", 0)
    if refuel > 0:
        pit_time += refuel / level.race.pit_refuel_rate
        new_state.fuel += refuel

    new_state.speed = level.race.pit_exit_speed
    new_state.race_time += pit_time
    new_state.in_limp = False

    return new_state, pit_time


# =====================
# LAP
# =====================

def simulate_lap(lap_strategy, state, level):
    start_time = state.race_time
    results = []

    strat_map = {s["id"]: s for s in lap_strategy["segments"]}

    for seg in level.segments:
        weather = _get_active_weather(state, level)
        strat = strat_map.get(seg.id, {})

        if seg.type == "straight":
            res, state = simulate_straight(seg, state, strat, weather, level)
        else:
            res, state = simulate_corner(seg, state, weather, level)

        results.append(res)

    state, pit_time = simulate_pit(lap_strategy.get("pit", {}), state, level)

    lap_time = state.race_time - start_time - pit_time

    return LapResult(lap_strategy["lap"], results, pit_time, lap_time), state


# =====================
# RACE
# =====================

def simulate_race(strategy, level: Level):
    state = CarState(
        speed=0,
        fuel=level.car.initial_fuel,
        tyre_id=strategy["initial_tyre_id"],
        tyre_compound=level.get_compound_for_id(strategy["initial_tyre_id"]),
        tyre_degradation=0,
        race_time=0,
        in_limp=False,
        in_crawl=False,
        lap=1
    )

    laps = []
    tyre_history = []
    fuel_start = state.fuel

    for lap in strategy["laps"]:
        state.lap = lap["lap"]
        res, state = simulate_lap(lap, state, level)
        laps.append(res)

        tyre_history.append({
            "lap": lap["lap"],
            "tyre_id": state.tyre_id,
            "degradation": state.tyre_degradation
        })

    return RaceResult(
        total_time=state.race_time,
        fuel_used=fuel_start - state.fuel,
        laps=laps,
        tyre_history=tyre_history,
        crashes=state.crash_count,
        blowouts=state.blowout_count
    )