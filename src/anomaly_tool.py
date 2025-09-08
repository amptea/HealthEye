import pandas as pd
import json
import numpy as np
from datetime import datetime
from strands import tool

# Load historical usage CSV
df = pd.read_csv("data/2324_combined.csv")

@tool
def detect_anomaly(daily_usage_json: str) -> str:
    """
    Enhanced anomaly detection for elderly home monitoring - DAILY USAGE ANALYSIS.
    daily_usage_json: JSON string with keys:
        "dwelling_type", "region", "description", "electricity_per_month", "gas_per_month", "date" (optional)
    Note: electricity_per_month and gas_per_month should contain DAILY usage values for comparison
    Returns JSON string with status, severity, and detailed reason comparing daily usage.
    """
    try:
        daily_usage = json.loads(daily_usage_json)
    except json.JSONDecodeError:
        return json.dumps({
            "status": "alert",
            "severity": "high",
            "reason": "Invalid JSON input.",
            "recommendations": ["Check data format and retry"]
        })

    dwelling = daily_usage.get("dwelling_type")
    region = daily_usage.get("region")
    description = daily_usage.get("description", "")
    electricity_daily = daily_usage.get("electricity_per_month")  # This is actually daily usage
    gas_daily = daily_usage.get("gas_per_month")  # This is actually daily usage
    date = daily_usage.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Validate inputs
    if not all([dwelling, region, electricity_daily is not None, gas_daily is not None]):
        return json.dumps({
            "status": "alert",
            "severity": "high",
            "reason": "Missing required fields: dwelling_type, region, electricity_per_month, gas_per_month",
            "recommendations": ["Ensure all required fields are provided"]
        })

    # Filter historical data by Dwelling Type, Region, and Description (if available)
    mask = (df["Dwelling Type"] == dwelling) & (df["Region"] == region)
    if description:
        mask = mask & (df["Description"] == description)
    
    df_filtered = df[mask]

    if df_filtered.empty:
        return json.dumps({
            "status": "alert",
            "severity": "medium",
            "reason": f"No historical data found for dwelling type '{dwelling}' in region '{region}'" + 
                     (f" and description '{description}'" if description else ""),
            "recommendations": ["Check if location data is correct", "Consider using broader region data"]
        })

    # Convert historical monthly data to daily averages for comparison
    elec_monthly = df_filtered["electricity_per_month"].dropna()
    gas_monthly = df_filtered["gas_per_month"].dropna()
    
    if len(elec_monthly) < 3 or len(gas_monthly) < 3:
        return json.dumps({
            "status": "alert",
            "severity": "medium",
            "reason": "Insufficient historical data for reliable analysis",
            "recommendations": ["Collect more historical data", "Use broader filtering criteria"]
        })

    # Convert monthly to daily averages (divide by 30)
    elec_daily_historical = elec_monthly / 30
    gas_daily_historical = gas_monthly / 30

    # Calculate statistics for daily usage
    elec_mean = elec_daily_historical.mean()
    elec_std = elec_daily_historical.std()
    elec_q25 = elec_daily_historical.quantile(0.25)
    elec_q75 = elec_daily_historical.quantile(0.75)
    
    gas_mean = gas_daily_historical.mean()
    gas_std = gas_daily_historical.std()
    gas_q25 = gas_daily_historical.quantile(0.25)
    gas_q75 = gas_daily_historical.quantile(0.75)

    # Calculate Z-scores and percentiles for daily usage
    elec_z = (electricity_daily - elec_mean) / elec_std if elec_std != 0 else 0
    gas_z = (gas_daily - gas_mean) / gas_std if gas_std != 0 else 0
    
    # Calculate percentiles
    elec_percentile = (elec_daily_historical <= electricity_daily).mean() * 100
    gas_percentile = (gas_daily_historical <= gas_daily).mean() * 100

    # Elderly-specific thresholds (more sensitive)
    # Low usage thresholds (potential medical emergency - person not using appliances)
    elec_low_threshold = elec_q25 * 0.5  # 50% below 25th percentile
    gas_low_threshold = gas_q25 * 0.5
    
    # High usage thresholds (potential medical emergency - unusual activity)
    elec_high_threshold = elec_q75 * 2.0  # 200% above 75th percentile
    gas_high_threshold = gas_q75 * 2.0

    # Determine alert status and severity
    alert_reasons = []
    severity_levels = []
    recommendations = []

    # Check for extremely low usage (potential medical emergency)
    if electricity_daily < elec_low_threshold:
        alert_reasons.append(f"CRITICAL: Daily electricity usage ({electricity_daily:.1f} kWh) is extremely low - 50% below normal daily range ({elec_q25:.1f} kWh). This may indicate a medical emergency.")
        severity_levels.append("critical")
        recommendations.append("Immediate welfare check recommended")
    
    if gas_daily < gas_low_threshold:
        alert_reasons.append(f"CRITICAL: Daily gas usage ({gas_daily:.1f} kWh) is extremely low - 50% below normal daily range ({gas_q25:.1f} kWh). This may indicate a medical emergency.")
        severity_levels.append("critical")
        recommendations.append("Immediate welfare check recommended")

    # Check for moderate deviations
    if abs(elec_z) > 2.5:
        if electricity_daily > elec_high_threshold:
            alert_reasons.append(f"WARNING: Daily electricity usage ({electricity_daily:.1f} kWh) is significantly high - {elec_z:.1f} standard deviations above daily mean ({elec_mean:.1f} kWh).")
            severity_levels.append("high")
            recommendations.append("Check for unusual activity or appliance malfunction")
        else:
            alert_reasons.append(f"WARNING: Daily electricity usage ({electricity_daily:.1f} kWh) is significantly low - {abs(elec_z):.1f} standard deviations below daily mean ({elec_mean:.1f} kWh).")
            severity_levels.append("high")
            recommendations.append("Check resident welfare and appliance status")
    
    if abs(gas_z) > 2.5:
        if gas_daily > gas_high_threshold:
            alert_reasons.append(f"WARNING: Daily gas usage ({gas_daily:.1f} kWh) is significantly high - {gas_z:.1f} standard deviations above daily mean ({gas_mean:.1f} kWh).")
            severity_levels.append("high")
            recommendations.append("Check for unusual activity or appliance malfunction")
        else:
            alert_reasons.append(f"WARNING: Daily gas usage ({gas_daily:.1f} kWh) is significantly low - {abs(gas_z):.1f} standard deviations below daily mean ({gas_mean:.1f} kWh).")
            severity_levels.append("high")
            recommendations.append("Check resident welfare and appliance status")

    # Check for mild deviations
    if 1.5 < abs(elec_z) <= 2.5:
        alert_reasons.append(f"NOTICE: Daily electricity usage ({electricity_daily:.1f} kWh) is moderately different from historical daily average ({elec_mean:.1f} kWh).")
        severity_levels.append("medium")
        recommendations.append("Monitor for patterns over next few days")
    
    if 1.5 < abs(gas_z) <= 2.5:
        alert_reasons.append(f"NOTICE: Daily gas usage ({gas_daily:.1f} kWh) is moderately different from historical daily average ({gas_mean:.1f} kWh).")
        severity_levels.append("medium")
        recommendations.append("Monitor for patterns over next few days")

    # Determine overall status and severity
    if severity_levels:
        if "critical" in severity_levels:
            overall_severity = "critical"
            overall_status = "alert"
        elif "high" in severity_levels:
            overall_severity = "high"
            overall_status = "alert"
        else:
            overall_severity = "medium"
            overall_status = "warning"
    else:
        overall_status = "normal"
        overall_severity = "low"
        alert_reasons.append("Usage is within normal historical ranges.")
        recommendations.append("Continue regular monitoring")

    # Create detailed response
    response = {
        "status": overall_status,
        "severity": overall_severity,
        "reason": " ".join(alert_reasons),
        "recommendations": recommendations,
        "statistics": {
            "electricity": {
                "current_daily": electricity_daily,
                "historical_daily_mean": round(elec_mean, 2),
                "historical_daily_std": round(elec_std, 2),
                "z_score": round(elec_z, 2),
                "percentile": round(elec_percentile, 1),
                "normal_daily_range": f"{elec_q25:.1f} - {elec_q75:.1f} kWh"
            },
            "gas": {
                "current_daily": gas_daily,
                "historical_daily_mean": round(gas_mean, 2),
                "historical_daily_std": round(gas_std, 2),
                "z_score": round(gas_z, 2),
                "percentile": round(gas_percentile, 1),
                "normal_daily_range": f"{gas_q25:.1f} - {gas_q75:.1f} kWh"
            }
        },
        "data_points_analyzed": len(df_filtered),
        "analysis_date": date
    }

    return json.dumps(response, indent=2)
