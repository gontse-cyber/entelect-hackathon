def calculate_score(total_time, reference_time):
    """
    Basic scoring:
    - Faster than reference = positive score
    - Slower = 0
    """
    score = reference_time - total_time
    return max(0, round(score, 2))