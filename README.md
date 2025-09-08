# HealthEye

Agentic elderly home monitoring using Amazon Bedrock + deterministic anomaly checks.

How to run:

1. pip install -r requirements.txt
2. streamlit run streamlit_app.py

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

## Usage Options

### 1. Analyze Single Reading

Enter a reading and see the agent combine KB retrieval and anomaly detection to decide status, severity, and recommendations.

### 2. Alerts Page (Escalation & Ack Loop)

See pending alerts, acknowledge/resolve/escalate them.

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
├── streamlit_app.py       # App entry point
├── config.json            # Configuration file
├── requirements.txt       # Python dependencies
├── src/
│   ├── alert_system.py    # Alert management system
│   ├── anomaly_tool.py    # Anomaly detection using statistical analysis
│   ├── daily_tracker.py   # Daily usage tracking
│   ├── data_processing.py # Preprocess historical electricity and gas usage data
│   ├── elderly_monitor.py # Main monitoring system
│   ├── notify.py          # Handle email notifications for serious cases
│   └── upload_s3.py       # Upload historical data to S3 for use in Knowledge Base
├── data/
│   ├── 2324_combined.csv  # Historical data for electricity and gas usage
│   ├── core_memory.json   # Store user profiles and snooze events
│   └── outputs/           # Generated files for Knowledge Base
```
