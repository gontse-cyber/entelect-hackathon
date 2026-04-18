from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Car:
    max_speed: float
    accel: float
    brake: float
    crawl_constant: float

@dataclass
class Race:
    laps: int
    time_reference: float
    crash_penalty: float

@dataclass
class Segment:
    id: int
    type: str  # "straight" or "corner"
    length: float
    radius: Optional[float] = None

@dataclass
class Track:
    segments: List[Segment]

@dataclass
class LevelData:
    car: Car
    race: Race
    track: Track

@dataclass
class SimulationResult:
    total_time: float
    valid: bool
    error_message: Optional[str] = None
