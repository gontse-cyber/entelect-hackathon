from level_loader import load_level
from strategy_generator import generate_level2_strategy
from simulator import simulate_race
import json

# Load level
level = load_level("C:\\Users\\GontseM\\Documents\\GitHub\\entelect-hackathon\\entelect_hackathon\\levels\\level2.json", level_number=2)

# Generate strategy
strategy = generate_level2_strategy(level)

# Simulate
result = simulate_race(strategy, level)

print("=" * 60)
print("LEVEL 2 RACE RESULT")
print("=" * 60)
print(f"Total Time     : {result.total_time:.2f} seconds")
print(f"Fuel Used      : {result.fuel_used:.2f} L")
print(f"Crashes        : {result.crashes}")
print(f"Reference      : {level.race.time_reference} seconds")
print("=" * 60)

# Save submission
with open("submission.txt", "w", encoding="utf-8") as f:
    json.dump(strategy, f, indent=2)

print("✅ submission.txt has been created successfully!")
print("You can now submit this file for Level 2.")