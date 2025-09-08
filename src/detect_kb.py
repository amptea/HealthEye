# detect_anomaly_with_kb.py
import json
import numpy as np
from strands import tool
from strands_tools import retrieve

@tool
def detect_anomaly_with_kb(dwelling_type: str, region: str, description: str, current_electricity: float, current_gas: float):
    """
    Detect anomalies in today's electricity and gas usage by retrieving historical averages from the KB
    and comparing them with current values.
    """

    # Step 1 - Retrieve historical usage from KB
    query = f"What is the average monthly electricity and gas usage for {dwelling_type} flats in {description}, {region}?"
    kb_response = retrieve(query)

    # Parse KB result (this depends on your KB content formatting)
    try:
        kb_text = str(kb_response)
        # Very naive parse: look for numbers in response
        import re
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", kb_text)
        electricity_avg = float(numbers[0]) if len(numbers) > 0 else None
        gas_avg = float(numbers[1]) if len(numbers) > 1 else None
    except Exception as e:
        return {
            "status": "alert",
            "reason": f"Failed to parse KB response: {e}",
            "analysis_summary": {
                "kb_retrieval": kb_text if 'kb_text' in locals() else "no data",
                "anomaly_detection": "not performed",
                "consolidated_conclusion": "could not analyze"
            }
        }

    if electricity_avg is None or gas_avg is None:
        return {
            "status": "alert",
            "reason": "No usable historical data found in KB",
            "analysis_summary": {
                "kb_retrieval": kb_text,
                "anomaly_detection": "not performed",
                "consolidated_conclusion": "could not analyze"
            }
        }

    # Step 2 - Convert monthly → daily
    hist_elec_daily = electricity_avg / 30.0
    hist_gas_daily = gas_avg / 30.0

    # Step 3 - Statistical anomaly detection (z-score style deviation)
    def check_anomaly(current, expected):
        if expected == 0:
            return 0.0, False
        deviation_percent = ((current - expected) / expected) * 100
        is_anomaly = abs(deviation_percent) > 50  # threshold e.g., ±50%
        return deviation_percent, is_anomaly

    elec_dev, elec_anomaly = check_anomaly(current_electricity, hist_elec_daily)
    gas_dev, gas_anomaly = check_anomaly(current_gas, hist_gas_daily)

    # Step 4 - Consolidate
    status = "normal"
    severity = "low"
    if elec_anomaly or gas_anomaly:
        status = "alert"
        severity = "high"

    return {
        "status": status,
        "severity": severity,
        "reason": "Electricity or gas usage deviates significantly from KB averages" if status == "alert" else "Usage is within normal range",
        "analysis_summary": {
            "kb_retrieval": f"Electricity avg={electricity_avg}, Gas avg={gas_avg}",
            "anomaly_detection": f"Electricity dev={elec_dev:.1f}%, Gas dev={gas_dev:.1f}%",
            "consolidated_conclusion": "Significant deviation detected" if status == "alert" else "No anomaly detected"
        },
        "statistics": {
            "electricity": {
                "current_daily": current_electricity,
                "historical_monthly_avg": electricity_avg,
                "historical_daily_avg": hist_elec_daily,
                "deviation_percent": elec_dev
            },
            "gas": {
                "current_daily": current_gas,
                "historical_monthly_avg": gas_avg,
                "historical_daily_avg": hist_gas_daily,
                "deviation_percent": gas_dev
            }
        },
        "data_quality": "historical data retrieved successfully" if (electricity_avg and gas_avg) else "incomplete data"
    }
