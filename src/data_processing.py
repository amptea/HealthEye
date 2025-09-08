import pandas as pd

# Load Excel files
df_elec = pd.read_excel("data/2324_elec.xlsx")
df_gas = pd.read_excel("data/2324_gas.xlsx")

# Function to normalize monthly data
def normalize_month(df, value_column):
    # Convert value column to numeric
    df[value_column] = pd.to_numeric(df[value_column], errors='coerce')

    month_str = df['Month'].astype(str).str.strip().str.lower()

    # Handle "Annual" rows
    annual_mask = month_str == 'annual'
    df.loc[annual_mask, value_column] = df.loc[annual_mask, value_column] / 12
    df.loc[annual_mask, 'Month'] = 1
    # Ensure Month is integer
    df['Month'] = df['Month'].astype(int)
    return df

# Normalize electricity and gas
df_elec = normalize_month(df_elec, 'Kwh Per Acc')
df_gas = normalize_month(df_gas, 'Kwh Per Acc')

# Rename columns for clarity
df_elec = df_elec.rename(columns={'Kwh Per Acc': 'electricity_per_month'})
df_gas = df_gas.rename(columns={'Kwh Per Acc': 'gas_per_month'})

# Merge on keys
merge_keys = ['Dwelling Type', 'Year', 'Month', 'Region', 'Description']
df_combined = pd.merge(df_elec, df_gas, on=merge_keys, how='outer')

# Fill missing values with average per Dwelling Type
for col in ['electricity_per_month', 'gas_per_month']:
    df_combined[col] = df_combined.groupby('Dwelling Type')[col].transform(
        lambda x: x.fillna(x.mean())
    )
    # Round to whole numbers
    df_combined[col] = df_combined[col].round(0).astype(int)

# Filter for specific descriptions
allowed_descriptions = ['Ang Mo Kio', 'Bedok', 'Bishan', 'Bukit Batok']
df_combined = df_combined[df_combined['Description'].isin(allowed_descriptions)]

# Export to CSV
df_combined.to_csv("data/2324_combined.csv", index=False)

print("Merged CSV created: 2324_combined.csv")
