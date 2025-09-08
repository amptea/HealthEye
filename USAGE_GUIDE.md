# Elderly Home Monitoring System - Usage Guide

## Overview
This system monitors daily electricity and gas usage for elderly residents and decides whether to notify caregivers using an agentic process that combines deterministic checks and LLM reasoning on Amazon Bedrock. It uses:
- Knowledge Base retrieval for location/dwelling historical norms
- Statistical anomaly detection for daily usage
- Snooze (core memory) and resident profiles
- An escalation and acknowledgement loop with visible state

## Key Features
- **Real-time Monitoring**: Track daily usage patterns
- **Anomaly Detection**: Identify unusual usage that may indicate medical emergencies
- **Alert System**: Multi-level alerts with escalation
- **Historical Analysis**: Compare against location-specific historical data
- **Dashboard**: Comprehensive monitoring dashboard

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Knowledge Base (optional for demo)
- Ensure your Bedrock Knowledge Base is synced with your data if you want live retrieval
- Set `KNOWLEDGE_BASE_ID` via environment variable if different from the code default

### 3. Run the Demo App
```bash
streamlit run streamlit_app.py
```

## Usage Options

### 1. Analyze Single Reading
Enter a reading and see the agent combine KB retrieval and anomaly detection to decide status, severity, and recommendations.

### 2. Add Manual Reading
Manually input usage data for a resident:
- Resident ID
- Electricity usage (kWh)
- Gas usage (kWh)
- Location details (optional)

### 3. Alerts Page (Escalation & Ack Loop)
See pending alerts, acknowledge/resolve/escalate them, and observe the visible state transitions and escalation levels.

### 4. Resident Snooze (Core Memory)
Set snooze windows per resident to suspend notifications during known absences. Active snoozes are listed and can be cleared.

### 5. Analysis Process Demo
Shows the three-step agent flow: KB retrieval, anomaly detection, and consolidation into a single decision.

## Alert Levels

### Critical (Red)
- Extremely low usage (50% below normal range)
- Indicates potential medical emergency
- Immediate welfare check recommended

### High (Orange)
- Significantly high/low usage (2.5+ standard deviations)
- Check for unusual activity or appliance issues
- Schedule welfare check

### Medium (Yellow)
- Moderately different usage (1.5-2.5 standard deviations)
- Monitor for patterns over next few days

### Low (Blue)
- Normal usage patterns
- Continue regular monitoring

## Configuration

Edit `config.json` to customize:
- Monitoring intervals
- Default locations
- Alert thresholds
- Email notifications
- Escalation rules

## File Structure

```
HealthEye/
├── main.py                 # Main entry point
├── config.json            # Configuration file
├── requirements.txt       # Python dependencies
├── src/
│   ├── elderly_monitor.py # Main monitoring system
│   ├── daily_tracker.py   # Usage tracking
│   ├── anomaly_tool.py    # Anomaly detection
│   ├── alert_system.py    # Alert management
│   └── test_agent.py      # Bedrock agent integration
├── data/
│   ├── 2324_combined.csv  # Historical data
│   └── outputs/           # Generated files for KB
└── exports/               # Exported data
```

## API Usage

### Python API
```python
from src.elderly_monitor import ElderlyMonitor

# Initialize
monitor = ElderlyMonitor("config.json")

# Add usage reading
result = monitor.add_usage_reading(
    resident_id="RES001",
    electricity_kwh=15.0,
    gas_kwh=5.0,
    dwelling_type="3-room",
    region="North East Region",
    description="Ang Mo Kio"
)

# Get dashboard
dashboard = monitor.get_monitoring_dashboard()
```

### Command Line (optional)
You can still use the CLI for scenarios/monitoring if desired:
```bash
python src/elderly_monitor.py --scenarios
python src/elderly_monitor.py --monitor --interval 30
python src/elderly_monitor.py --dashboard
python src/elderly_monitor.py --export exports/
```

## Troubleshooting

### No Historical Data Found
- Ensure `data/2324_combined.csv` exists
- Check if location fields match exactly (case-sensitive)

### Alerts Not Triggering
- Check threshold settings in `config.json`
- Verify anomaly detection is working with test data
- Review alert system configuration

### Email Notifications
- In the demo, email is simulated via logs/messages and not actually sent

## Monitoring Best Practices

1. **Regular Data Entry**: Input daily readings consistently
2. **Location Accuracy**: Use exact location names from historical data
3. **Alert Response**: Respond to alerts promptly based on severity
4. **Data Export**: Regularly export data for backup and analysis
5. **System Updates**: Keep historical data and KB synced

## Support

For issues or questions:
1. Check logs in `elderly_monitor.log`
2. Review configuration settings
3. Test with example scenarios first
4. Verify Knowledge Base connectivity

## Security Notes

- Store sensitive configuration in environment variables
- Use secure email credentials
- Regularly backup exported data
- Monitor system access and logs
