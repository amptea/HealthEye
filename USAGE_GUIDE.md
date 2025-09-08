# Elderly Home Monitoring System - Usage Guide

## Overview
This system monitors daily electricity and gas usage for elderly residents to detect potential medical emergencies. It uses historical data from Amazon Bedrock Knowledge Base and advanced anomaly detection to identify unusual usage patterns.

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

### 2. Configure Knowledge Base
- Ensure your Bedrock Knowledge Base is synced with the updated metadata
- Update `KNOWLEDGE_BASE_ID` in `src/test_agent.py` if needed

### 3. Run the System
```bash
python main.py
```

## Usage Options

### 1. Run Example Scenarios
Tests the system with predefined scenarios:
- Normal usage pattern
- Extremely low usage (potential emergency)
- High usage (potential concern)

### 2. Add Manual Reading
Manually input usage data for a resident:
- Resident ID
- Electricity usage (kWh)
- Gas usage (kWh)
- Location details (optional)

### 3. Continuous Monitoring
Start automated monitoring with configurable intervals.

### 4. Dashboard
View current system status, alerts, and usage summaries.

### 5. Export Data
Export all monitoring data to files for analysis.

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

### Command Line
```bash
# Run scenarios
python src/elderly_monitor.py --scenarios

# Start monitoring
python src/elderly_monitor.py --monitor --interval 30

# Show dashboard
python src/elderly_monitor.py --dashboard

# Export data
python src/elderly_monitor.py --export exports/
```

## Troubleshooting

### No Historical Data Found
- Ensure Knowledge Base is synced with updated metadata
- Check if location data matches exactly (case-sensitive)
- Verify CSV files are properly uploaded to S3

### Alerts Not Triggering
- Check threshold settings in `config.json`
- Verify anomaly detection is working with test data
- Review alert system configuration

### Email Notifications Not Working
- Configure SMTP settings in `config.json`
- Enable email notifications in config
- Check credentials and server settings

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
