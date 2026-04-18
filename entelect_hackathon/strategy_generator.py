# strategy_generator.py  -  Level 2 Version
from level_loader import Level

def generate_level2_strategy(level: Level) -> dict:
    """Working Level 2 strategy: Soft tyres early, Medium later, pit every 15 laps for fuel + tyres"""
    laps_data = []
    current_tyre_id = 1  # Start with Soft (ID 1)

    for lap_num in range(1, level.race.laps + 1):
        segments = []
        for seg in level.segments:
            if seg.type == "straight":
                segments.append({
                    "id": seg.id,
                    "type": "straight",
                    "target_m/s": 88.0,           # aggressive but safe
                    "brake_start_m_before_next": 160.0
                })
            else:
                segments.append({
                    "id": seg.id,
                    "type": "corner"
                })

        # Pit strategy: pit every 15 laps
        pit = {"enter": False}
        if lap_num % 15 == 0 and lap_num < level.race.laps:
            # Switch to Medium (ID 2) after lap 30
            current_tyre_id = 2 if lap_num > 30 else 1
            pit = {
                "enter": True,
                "tyre_change_set_id": current_tyre_id,
                "fuel_refuel_amount_l": 140.0   # safe refuel amount
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