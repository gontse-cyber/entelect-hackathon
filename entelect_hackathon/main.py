from parser import load_level
from scoring import calculate_score

def main():
    level = load_level("levels/level_1.json") //1. Load the level
    
    # 2. Get the strategy from Person B (for now, we'll hardcode)
    #    Person B will replace this with their optimizer output
    initial_tyre_id = 1
    
    laps_data = []
    for lap_num in range(1, level.race.laps + 1):
        laps_data.append({
            "lap": lap_num,
            "segments": [
                {"id": 1, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 155.8},
                {"id": 2, "type": "corner"},
                {"id": 3, "type": "corner"},
                {"id": 4, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 157.9},
                {"id": 5, "type": "corner"},
                {"id": 6, "type": "corner"},
                {"id": 7, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 151.1},
                {"id": 8, "type": "corner"},
                {"id": 9, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 162.0},
                {"id": 10, "type": "corner"},
                {"id": 11, "type": "corner"},
                {"id": 12, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 139.3},
                {"id": 13, "type": "corner"},
                {"id": 14, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 154.5},
                {"id": 15, "type": "corner"}
            ],
            "pit": {"enter": False}
        })
    
    # 3. Save the strategy (Person B will call this)
    from strategy_writer import save_strategy
    save_strategy(initial_tyre_id, laps_data, "submission.txt")
    print("Strategy saved to submission.txt")
    
    # 4. Person A will run their simulator and give you total_time
    #    For now, let's say Person A gives you:
    total_time = 7300.0  # This will come from Person A's simulator
    
   
    score = calculate_score(total_time, level.race.time_reference) // 5. Calculate score
    print(f"Score: {score}")

if __name__ == "__main__":
    main()