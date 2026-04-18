import math

GRAVITY = 9.8
#Degradation constants
K_STRAIGHT = 0.0000166
K_BRAKING = 0.0398
K_CORNER = 0.000265

#Fuel constants
K_BASE = 0.0005
K_DRAG = 0.0000000015

#Base friction coefficients for different track conditions
BASE_FRICTION = {
    "Soft":         1.8,
    "Medium":       1.7,
    "Hard":         1.6,
    "Intermediate": 1.2,
    "Wet":          1.1,
}

def accel_time(v_init: float, v_final: float, accel_eff: float) -> float:
    """Time to accelerate from v_init to v_final"""
    return (v_final - v_init) / accel_eff

def accel_distance(v_init: float, v_final: float, accel_eff: float) -> float:
    """Distance covered while accelerating from v_init to v_final."""
    return (v_final ** 2 - v_init ** 2) / (2 * accel_eff)

def brake_exit_speed(v_init: float, brake_eff: float, distance: float) -> float:
    """Speed at end of braking phase; clamped to 0 (crawl applied separately)."""
    v2 = v_init ** 2 - 2 * brake_eff * distance
    return math.sqrt(max(0.0, v2))

def fuel_used(v_init: float, v_final: float, distance: float) -> float:
    """Fuel consumed (litres) over a distance with given initial/final speeds."""
    avg = (v_init + v_final) / 2
    return (K_BASE + K_DRAG * avg ** 2) * distance
 
 
def max_corner_speed(tyre_friction: float, radius_m: float, crawl: float) -> float:
    """Maximum safe corner speed (m/s) given tyre friction and corner radius."""
    return math.sqrt(tyre_friction * GRAVITY * radius_m) + crawl
 
 
def compute_tyre_friction(base_coeff: float, total_deg: float, weather_mult: float) -> float:
    """Current tyre friction; accounts for accumulated degradation and weather."""
    return (base_coeff - total_deg) * weather_mult
 
 
def deg_straight(rate: float, length_m: float) -> float:
    """Tyre degradation from travelling on a straight segment."""
    return rate * length_m * K_STRAIGHT
 
 
def deg_braking(rate: float, v_brake_start: float, v_exit: float) -> float:
    """Additional tyre degradation from the braking phase."""
    return ((v_brake_start / 100) ** 2 - (v_exit / 100) ** 2) * K_BRAKING * rate
 
 
def deg_corner(rate: float, speed: float, radius_m: float) -> float:
    """Tyre degradation from taking a corner."""
    return K_CORNER * (speed ** 2 / radius_m) * rate
 
 
def _dur(c) -> float:
    """Extract duration from either a dict or a WeatherCondition dataclass."""
    return c["duration_s"] if isinstance(c, dict) else c.duration_s
 
 
def get_weather(race_time_s: float, conditions: list):
    """
    Return the active weather condition for a given race time.
    Cycles through the condition list repeatedly once all durations expire.
    Works with both plain dicts and WeatherCondition dataclass instances.
    """
    total_duration = sum(_dur(c) for c in conditions)
    t = race_time_s % total_duration
    elapsed = 0.0
    for c in conditions:
        elapsed += _dur(c)
        if t < elapsed:
            return c
    return conditions[-1]