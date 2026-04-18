# strategy_generator.py - LEVEL 3 VERSION
from level_loader import Level

def generate_level3_strategy(level: Level) -> dict:
    """Basic working strategy for Level 3 (Spa)"""
    laps_data = []
    tyre_id = 1  # Start with Soft (ID 1)

    for lap_num in range(1, level.race.laps + 1):
        segments = []
        for seg in level.segments:
            if seg.type == "straight":
                segments.append({
                    "id": seg.id,
                    "type": "straight",
                    "target_m/s": 88.0,
                    "brake_start_m_before_next": 150.0
                })
            else:
                segments.append({"id": seg.id, "type": "corner"})

        # Pit every 14 laps for fuel and tyres
        pit = {"enter": False}
        if lap_num % 14 == 0 and lap_num < level.race.laps:
            if lap_num > 50:
                tyre_id = 3  # Hard
            elif lap_num > 28:
                tyre_id = 2  # Medium
            else:
                tyre_id = 1  # Soft

            pit = {
                "enter": True,
                "tyre_change_set_id": tyre_id,
                "fuel_refuel_amount_l": 180.0
            }

        laps_data.append({
            "lap": lap_num,
            "segments": segments,
            "pit": pit
        })

    return {
        "initial_tyre_id": 1,
        "laps": laps_data
    }