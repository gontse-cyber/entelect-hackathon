import json

def save_strategy(initial_tyre_id: int, laps_data: list, output_path: str):
    """
    laps_data should look like:
    [
        {
            "lap": 1,
            "segments": [
                {"id": 1, "type": "straight", "target_m/s": 90, "brake_start_m_before_next": 155.8},
                {"id": 2, "type": "corner"},
                ...
            ],
            "pit": {"enter": False}
        },
        ...
    ]
    """
    output = {
        "initial_tyre_id": initial_tyre_id,
        "laps": laps_data
    }
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)