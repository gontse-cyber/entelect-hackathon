from strategy import build_strategy
from level_loader import load_level
from simulator import simulate_race   

level_data = load_level("levels/level1.json")

strategy = build_strategy(level_data)


result = simulate_race(strategy, level_data)

print("Total time:", result.total_time)
print("Fuel used:", result.fuel_used)
print("Crashes:", result.crashes)
print("Blowouts:", result.blowouts)