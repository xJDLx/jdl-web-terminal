import json
import csv

# Read all items from portfolio.csv
portfolio_items = []
with open('portfolio.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        portfolio_items.append(row['Item Name'])

# Common CS2 knife items
knife_items = [
    "★ Bayonet", "★ Bayonet | Autotronic (Factory New)", "★ Bayonet | Black Laminate (Minimal Wear)",
    "★ Bowie Knife", "★ Bowie Knife | Fade (Factory New)", "★ Bowie Knife | Tiger Tooth (Factory New)",
    "★ Butterfly Knife", "★ Butterfly Knife | Doppler (Factory New)", "★ Butterfly Knife | Fade (Factory New)",
    "★ Falchion Knife", "★ Falchion Knife | Doppler (Factory New)", "★ Falchion Knife | Marble Fade (Factory New)",
    "★ Karambit", "★ Karambit | Doppler (Factory New)", "★ Karambit | Marble Fade (Factory New)",
    "★ M9 Bayonet", "★ M9 Bayonet | Doppler (Factory New)", "★ M9 Bayonet | Fade (Factory New)",
    "★ Huntsman Knife", "★ Huntsman Knife | Doppler (Factory New)", "★ Huntsman Knife | Fade (Factory New)",
]

# Common weapon items
weapon_items = [
    "AK-47 | Phantom Disruptor", "M4A1-S | Nightwish", "AWP | Wildfire", "Deagle | Mecha Industries",
    "USP-S | Printstream", "P250 | Supernova", "Five-SeveN | Neon Rider", "CZ75-Auto | Eco",
    "MP5-SD | Condition Zero", "UMP-45 | Momentum", "MAC-10 | Heat", "P90 | Emerald Dragon",
    "Galil AR | Phantom Disruptor", "SG 553 | Phantom Disruptor", "AUG | Momentum"
]

# Combine all items
all_items = list(set(portfolio_items + knife_items + weapon_items))
all_items.sort()

# Create JSON
data = {"items": all_items}

# Write to file
with open('csgo_api_v47.json', 'w', encoding='utf-8-sig') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Added {len(all_items)} items to csgo_api_v47.json")
print(f"   - Portfolio items: {len(portfolio_items)}")
print(f"   - Knife items: {len(knife_items)}")
print(f"   - Weapon items: {len(weapon_items)}")

