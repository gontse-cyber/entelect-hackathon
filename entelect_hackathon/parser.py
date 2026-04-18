import json
from types import Car, Race, Segment, Track, LevelData

def load_level(file_path: str) -> LevelData:
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    car = Car(
        max_speed=data['car']['max_speed_m/s'],
        accel=data['car']['accel_m/se2'],
        brake=data['car']['brake_m/se2'],
        crawl_constant=data['car']['crawl_constant_m/s']
    )
    
    race = Race(
        laps=data['race']['laps'],
        time_reference=data['race']['time_reference_s'],
        crash_penalty=data['race']['corner_crash_penalty_s']
    )
    
    segments = []
    for seg in data['track']['segments']:
        segments.append(Segment(
            id=seg['id'],
            type=seg['type'],
            length=seg['length_m'],
            radius=seg.get('radius_m')
        ))
    
    track = Track(segments=segments)
    
    return LevelData(car=car, race=race, track=track)