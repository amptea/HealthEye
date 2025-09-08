import os
from strands import Agent
from strands_tools import retrieve
from strands.models.bedrock import BedrockModel
from anomaly_tool import detect_anomaly
from daily_tracker import DailyUsageTracker

import json

# Bedrock model
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    temperature=0.2
)

# Set Knowledge Base ID as environment variable
os.environ["KNOWLEDGE_BASE_ID"] = "GKRKOT1TME"  # replace with your KB ID

# Initialize daily tracker
tracker = DailyUsageTracker()

# Enhanced system prompt for elderly home monitoring
system_prompt = """
You are "Health Monitor Agent", an intelligent assistant specialized in monitoring elderly residents' daily electricity and gas usage patterns.

Your primary responsibilities:
1. Retrieve and analyze historical usage data from the knowledge base
2. Compare current usage against historical patterns for the same dwelling type, region, and location
3. Detect anomalies that may indicate medical emergencies or health issues
4. Provide detailed analysis with severity levels and actionable recommendations

Key considerations for elderly residents:
- Extremely low usage may indicate medical emergency (person unable to use appliances)
- Unusually high usage may indicate confusion, forgetfulness, or medical distress
- Seasonal patterns and dwelling-specific norms are crucial for accurate assessment
- Location-specific data (Description field) provides the most accurate comparisons

Analysis process:
1. First, use the retrieve tool to find historical data matching the dwelling type, region, and description
2. Then use the detect_anomaly tool to perform detailed statistical analysis
3. Consider both electricity and gas usage patterns
4. Look for trends and patterns in the retrieved data

Output format:
Always provide a comprehensive JSON response with:
{
    "status": "normal/warning/alert",
    "severity": "low/medium/high/critical", 
    "reason": "detailed explanation of findings",
    "recommendations": ["actionable recommendations"],
    "statistics": {
        "electricity": {...},
        "gas": {...}
    },
    "data_quality": "assessment of available historical data"
}

Be thorough in your analysis and always consider the elderly resident's safety and wellbeing.
"""

# Initialize agent
agent = Agent(
    tools=[retrieve, detect_anomaly], 
    model=bedrock_model,
    system_prompt=system_prompt
)

def analyze_daily_usage(dwelling_type: str, 
                       region: str, 
                       description: str,
                       electricity_kwh: float,
                       gas_kwh: float,
                       date: str = None,
                       resident_id: str = None) -> dict:
    """
    Analyze daily usage for elderly resident
    
    Args:
        dwelling_type: Type of dwelling
        region: Region
        description: Specific location
        electricity_kwh: Daily electricity usage
        gas_kwh: Daily gas usage
        date: Date (defaults to today)
        resident_id: Optional resident ID
        
    Returns:
        Analysis results
    """
    # Add to daily tracker
    tracker_result = tracker.add_daily_usage(
        dwelling_type=dwelling_type,
        region=region,
        description=description,
        electricity_kwh=electricity_kwh,
        gas_kwh=gas_kwh,
        date=date,
        resident_id=resident_id
    )
    
    # Build enhanced user message for agent
    user_message = f"""
Analyze the following daily usage for elderly resident monitoring:

Location: {dwelling_type} flat in {description}, {region}
Date: {date or 'Today'}
Electricity Usage: {electricity_kwh} kWh
Gas Usage: {gas_kwh} kWh
Resident ID: {resident_id or 'Not specified'}

Please:
1. Retrieve historical usage data for this specific dwelling type, region, and description from the knowledge base
2. Perform detailed anomaly detection analysis
3. Assess if this usage pattern indicates any potential medical emergency or health concern
4. Provide comprehensive analysis with severity levels and recommendations

Focus on elderly-specific concerns:
- Extremely low usage may indicate the resident is unable to use appliances (medical emergency)
- Unusually high usage may indicate confusion, forgetfulness, or distress
- Consider seasonal patterns and location-specific norms

Provide your analysis in the specified JSON format with detailed statistics and recommendations.
"""
    
    # Get agent analysis
    print(f"🔍 Agent Analysis - Using tools: retrieve, detect_anomaly")
    print(f"📊 Query: {user_message[:100]}...")
    
    agent_response = agent(user_message)
    
    # Convert AgentResult to string for JSON serialization
    agent_response_str = str(agent_response) if hasattr(agent_response, '__str__') else str(agent_response)
    
    # Combine tracker and agent results
    return {
        "tracker_analysis": tracker_result,
        "agent_analysis": agent_response_str,
        "timestamp": datetime.now().isoformat()
    }

# Example usage scenarios
def run_example_scenarios():
    """Run example scenarios for testing"""
    
    print("=== Elderly Home Usage Monitoring Examples ===\n")
    
    # Scenario 1: Normal usage
    print("Scenario 1: Normal Usage")
    result1 = analyze_daily_usage(
        dwelling_type="3-room",
        region="North East Region",
        description="Ang Mo Kio",
        electricity_kwh=15.0,
        gas_kwh=5.0,
        resident_id="RES001"
    )
    print("Result:", json.dumps(result1, indent=2))
    print("\n" + "="*50 + "\n")
    
    # Scenario 2: Extremely low usage (potential emergency)
    print("Scenario 2: Extremely Low Usage (Potential Emergency)")
    result2 = analyze_daily_usage(
        dwelling_type="3-room",
        region="North East Region", 
        description="Ang Mo Kio",
        electricity_kwh=2.0,  # Very low
        gas_kwh=0.5,  # Very low
        resident_id="RES002"
    )
    print("Result:", json.dumps(result2, indent=2))
    print("\n" + "="*50 + "\n")
    
    # Scenario 3: High usage (potential concern)
    print("Scenario 3: High Usage (Potential Concern)")
    result3 = analyze_daily_usage(
        dwelling_type="3-room",
        region="North East Region",
        description="Ang Mo Kio", 
        electricity_kwh=50.0,  # High
        gas_kwh=15.0,  # High
        resident_id="RES003"
    )
    print("Result:", json.dumps(result3, indent=2))
    print("\n" + "="*50 + "\n")
    
    # Get usage summary
    summary = tracker.get_usage_summary()
    print("Usage Summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    from datetime import datetime
    run_example_scenarios()
