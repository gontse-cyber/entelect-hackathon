# simulator.py - Clean & Fixed for Level 3
from dataclasses import dataclass
from level_loader import Level

@dataclass
class RaceResult:
    total_time: float
    fuel_used: float
    crashes: int

def simulate_race(strategy: dict, level: Level) -> RaceResult:
    fuel = level.car.initial_fuel
    race_time = 0.0
    crashes = 0
    fuel_start = fuel

    for lap_strat in strategy["laps"]:
        for seg in level.segments:
            if seg.type == "straight":
                speed = 87.0   # safe straight speed
            else:
                speed = 48.0   # much safer corner speed to reduce crashes

            distance = seg.length_m
            time_taken = distance / speed

            race_time += time_taken
            fuel -= 0.0005 * distance   # fixed fuel consumption

            if seg.type == "corner" and speed > 55:
                crashes += 1

        # Pit stop handling
        pit = lap_strat.get("pit", {"enter": False})
        if pit.get("enter", False):
            pit_time = level.race.base_pit_stop_time
            if "tyre_change_set_id" in pit:
                pit_time += level.race.pit_tyre_swap_time
            if "fuel_refuel_amount_l" in pit:
                refuel = pit["fuel_refuel_amount_l"]
                fuel += refuel
                pit_time += refuel / level.race.pit_refuel_rate
            race_time += pit_time

    return RaceResult(
        total_time=race_time,
        fuel_used=fuel_start - fuel,
        crashes=crashes
    )