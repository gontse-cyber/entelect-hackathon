def calculate_score(total_time: float, reference_time: float) -> float:
    """Calculate Level 1 score"""
    if total_time <= 0:
        return 0
    return 500000 * (reference_time / total_time) ** 3
