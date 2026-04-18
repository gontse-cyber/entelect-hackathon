import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class CarSpec:
    max_speed: float          # m/s
    accel: float              # m/s²
    brake: float              # m/s²
    limp_speed: float         # m/s
    crawl_speed: float        # m/s
    fuel_tank_capacity: float # litres
    initial_fuel: float       # litres


@dataclass
class RaceSpec:
    name: str
    laps: int
    base_pit_stop_time: float   # s
    pit_tyre_swap_time: float   # s
    pit_refuel_rate: float      # l/s
    corner_crash_penalty: float # s
    pit_exit_speed: float       # m/s
    fuel_soft_cap: float        # litres
    starting_weather_id: int
    time_reference: float       # s


@dataclass
class Segment:
    id: int
    type: str           # 'straight' or 'corner'
    length_m: float
    radius_m: Optional[float] = None


@dataclass
class TyreProperties:
    compound: str
    life_span: float
    friction: Dict[str, float]   # keyed by condition name
    degradation: Dict[str, float]


@dataclass
class TyreSet:
    ids: List[int]
    compound: str


@dataclass
class WeatherCondition:
    id: int
    condition: str        # 'dry', 'cold', 'light_rain', 'heavy_rain'
    duration_s: float
    acceleration_multiplier: float
    deceleration_multiplier: float


@dataclass
class Level:
    car: CarSpec
    race: RaceSpec
    segments: List[Segment]
    tyre_properties: Dict[str, TyreProperties]   # compound -> properties
    tyre_sets: List[TyreSet]
    weather_conditions: List[WeatherCondition]

    # ── lookup helpers ───────────────────────────────────────────────────────

    def get_compound_for_id(self, tyre_id: int) -> str:
        """Return the compound name for a given tyre set ID."""
        for ts in self.tyre_sets:
            if tyre_id in ts.ids:
                return ts.compound
        raise ValueError(f"Tyre ID {tyre_id} not found in available sets")

    def get_tyre_props(self, tyre_id: int) -> TyreProperties:
        compound = self.get_compound_for_id(tyre_id)
        return self.tyre_properties[compound]

    def get_friction_mult(self, tyre_id: int, weather_condition: str) -> float:
        props = self.get_tyre_props(tyre_id)
        return props.friction[weather_condition]

    def get_degradation_rate(self, tyre_id: int, weather_condition: str) -> float:
        props = self.get_tyre_props(tyre_id)
        return props.degradation[weather_condition]

    def get_life_span(self, tyre_id: int) -> float:
        return self.get_tyre_props(tyre_id).life_span

    def get_base_friction(self, tyre_id: int) -> float:
        from utils import BASE_FRICTION
        return BASE_FRICTION[self.get_compound_for_id(tyre_id)]


def load_level(path: str) -> Level:
    with open(path) as f:
        d = json.load(f)

    car_d = d["car"]
    car = CarSpec(
        max_speed=car_d["max_speed_m/s"],
        accel=car_d["accel_m/se2"],
        brake=car_d["brake_m/se2"],
        limp_speed=car_d["limp_constant_m/s"],
        crawl_speed=car_d["crawl_constant_m/s"],
        fuel_tank_capacity=car_d["fuel_tank_capacity_l"],
        initial_fuel=car_d["initial_fuel_l"],
    )

    race_d = d["race"]
    race = RaceSpec(
        name=race_d["name"],
        laps=race_d["laps"],
        base_pit_stop_time=race_d["base_pit_stop_time_s"],
        pit_tyre_swap_time=race_d["pit_tyre_swap_time_s"],
        pit_refuel_rate=race_d["pit_refuel_rate_l/s"],
        corner_crash_penalty=race_d["corner_crash_penalty_s"],
        pit_exit_speed=race_d["pit_exit_speed_m/s"],
        fuel_soft_cap=race_d.get("fuel_soft_cap_limit_l", 9999.0),
        starting_weather_id=race_d["starting_weather_condition_id"],
        time_reference=race_d["time_reference_s"],
    )

    segments = []
    for s in d["track"]["segments"]:
        segments.append(Segment(
            id=s["id"],
            type=s["type"],
            length_m=s["length_m"],
            radius_m=s.get("radius_m"),
        ))

    FRICTION_KEY_MAP = {
        "dry": "dry_friction_multiplier",
        "cold": "cold_friction_multiplier",
        "light_rain": "light_rain_friction_multiplier",
        "heavy_rain": "heavy_rain_friction_multiplier",
    }
    DEGRAD_KEY_MAP = {
        "dry": "dry_degradation",
        "cold": "cold_degradation",
        "light_rain": "light_rain_degradation",
        "heavy_rain": "heavy_rain_degradation",
    }

    tyre_properties: Dict[str, TyreProperties] = {}
    for compound, props in d["tyres"]["properties"].items():
        friction = {cond: props[json_key] for cond, json_key in FRICTION_KEY_MAP.items()}
        degradation = {cond: props[json_key] for cond, json_key in DEGRAD_KEY_MAP.items()}
        tyre_properties[compound] = TyreProperties(
            compound=compound,
            life_span=props["life_span"],
            friction=friction,
            degradation=degradation,
        )

    tyre_sets = []
    for ts in d["available_sets"]:
        tyre_sets.append(TyreSet(ids=ts["ids"], compound=ts["compound"]))

    weather_conditions = []
    for w in d["weather"]["conditions"]:
        weather_conditions.append(WeatherCondition(
            id=w["id"],
            condition=w["condition"],
            duration_s=w["duration_s"],
            acceleration_multiplier=w["acceleration_multiplier"],
            deceleration_multiplier=w["deceleration_multiplier"],
        ))

    return Level(
        car=car,
        race=race,
        segments=segments,
        tyre_properties=tyre_properties,
        tyre_sets=tyre_sets,
        weather_conditions=weather_conditions,
    )