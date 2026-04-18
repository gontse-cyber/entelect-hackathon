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


def build_strategy(level_data):
    car = level_data.car
    track = level_data.segments

    max_speed = car.max_speed
    brake = car.brake
    crawl = car.crawl_speed

    tyre_id = 1
    compound = level_data.get_compound_for_id(tyre_id)

    friction = get_base_friction(compound)

    laps = []

    for lap in range(1, level_data.race.laps + 1):
        segments = []

        for i, seg in enumerate(track):

            if seg.type == "straight":
                next_seg = track[(i + 1) % len(track)]

                if next_seg.type == "corner":
                    corner_speed = safe_corner_speed(
                        next_seg.radius_m,
                        friction,
                        crawl
                    )

                    target_speed = min(max_speed, corner_speed + 20)

                    d_brake = (target_speed**2 - corner_speed**2) / (2 * brake)
                    d_brake = max(0, min(d_brake, seg.length_m))

                    segments.append({
                        "id": seg.id,
                        "type": "straight",
                        "target_m/s": round(target_speed, 2),
                        "brake_start_m_before_next": round(d_brake, 2)
                    })

                else:
                    segments.append({
                        "id": seg.id,
                        "type": "straight",
                        "target_m/s": max_speed,
                        "brake_start_m_before_next": 0
                    })

            else:
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