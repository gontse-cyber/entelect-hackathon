from strategy import build_strategy
from level_loader import load_level
from simulator import simulate_race   

# Load level
level_data = load_level("levels/level1.json")

# Build strategy
strategy = build_strategy(level_data)

# Run simulation
result = simulate_race(strategy, level_data)

# Print results
print("Total time:", result.total_time)
print("Fuel used:", result.fuel_used)
print("Crashes:", result.crashes)
print("Blowouts:", result.blowouts)

# Optional scoring
from scoring import calculate_score
score = calculate_score(result.total_time, 7000)
print("Score:", score)