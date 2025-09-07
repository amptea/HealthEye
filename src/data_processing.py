import pandas as pd
import json

# Load electricity and town gas Excel files
df_elec = pd.read_csv("data/electricity.csv")
df_gas = pd.read_csv("data/town_gas.csv")

records = []

# Flatten electricity
for idx, row in df_elec.iterrows():
    records.append({
        "text": f"{row['Dwelling Type']} in {row['Description']} ({row['Region']}) during {row['Month']}/{row['Year']} used {row['Kwh Per Acc']} kWh electricity",
        "dwelling_type": row["Dwelling Type"],
        "region": row["Region"],
        "description": row["Description"],
        "year": row["Year"],
        "month": row["Month"],
        "value": row["Kwh Per Acc"],
        "type": "electricity"
    })

# Flatten town gas
for idx, row in df_gas.iterrows():
    records.append({
        "text": f"{row['Dwelling Type']} in {row['Description']} ({row['Region']}) during {row['Month']}/{row['Year']} used {row['Kwh Per Acc']} units town gas",
        "dwelling_type": row["Dwelling Type"],
        "region": row["Region"],
        "description": row["Description"],
        "year": row["Year"],
        "month": row["Month"],
        "value": row["Kwh Per Acc"],
        "type": "town_gas"
    })

# Save flattened JSON
with open("data/flattened_usage.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Flattened {len(records)} records and saved to flattened_usage.json")
