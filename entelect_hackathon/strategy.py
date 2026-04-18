import math


def get_base_friction(compound):
    return {
        "Soft": 1.8,
        "Medium": 1.7,
        "Hard": 1.6,
        "Intermediate": 1.2,
        "Wet": 1.1
    }[compound]


def safe_corner_speed(radius, friction, crawl):
    return math.sqrt(friction * 9.8 * radius) + crawl


def braking_distance(v_initial, v_target, brake_decel):
    if v_initial <= v_target:
        return 0.0
    return (v_initial**2 - v_target**2) / (2 * brake_decel)


def build_strategy(level_data):
    car = level_data.car
    track = level_data.segments

    max_speed = car.max_speed
    brake_decel = car.brake
    crawl = car.crawl_speed

    tyre_id = 1
    compound = level_data.get_compound_for_id(tyre_id)
    friction = get_base_friction(compound)

    safety_factor = 0.94      
    brake_buffer = 1.12       

    laps = []

    for lap in range(1, level_data.race.laps + 1):
        segments = []

        for i, seg in enumerate(track):
            if seg.type == "straight":
                next_seg = track[(i + 1) % len(track)]

                if next_seg.type == "corner":
                    corner_entry = safe_corner_speed(next_seg.radius_m, friction, crawl)
                    target_entry = corner_entry * safety_factor

                    # Calculate required braking distance
                    d_brake = braking_distance(max_speed, target_entry, brake_decel)
                    
                    # Add safety buffer
                    d_brake = d_brake * brake_buffer
                    
                    # Don't brake more than the straight length allows
                    d_brake = min(d_brake, seg.length_m * 0.95)

                    segments.append({
                        "id": seg.id,
                        "type": "straight",
                        "target_m/s": round(max_speed, 2),
                        "brake_start_m_before_next": round(d_brake, 2)
                    })

                else:
                    # Straight to straight
                    segments.append({
                        "id": seg.id,
                        "type": "straight",
                        "target_m/s": round(max_speed, 2),
                        "brake_start_m_before_next": 0
                    })

            else:
                # Corner
                segments.append({
                    "id": seg.id,
                    "type": "corner"
                })

        laps.append({
            "lap": lap,
            "segments": segments,
            "pit": {"enter": False}
        })

    return {
        "initial_tyre_id": tyre_id,
        "laps": laps
    }