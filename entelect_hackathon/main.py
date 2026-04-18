from strategy import build_strategy
from level_loader import load_level
from simulator import simulate_race
from scoring import calculate_score

def main():
    # Load level
    level_data = load_level("levels/level1.json")

    # Build strategy (Person B)
    strategy = build_strategy(level_data)

    # Run simulation (Person A)
    result = simulate_race(strategy, level_data)

    # Print results
    print("Total time:", result.total_time)
    print("Fuel used:", result.fuel_used)
    print("Crashes:", result.crashes)
    print("Blowouts:", result.blowouts)

    # Score (Level 1 uses reference = 7300)
    reference_time = 7300
    print("Reference:", reference_time)

    score = calculate_score(result.total_time, reference_time)
    print("Score:", score)

if __name__ == "__main__":
    main()