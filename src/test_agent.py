from strands import Agent, S3KnowledgeBase
import json

# 1. Initialize KB (S3 vector store)
kb = S3KnowledgeBase(
    bucket_name="utilities-hackathon-2025",
    object_key="flattened_usage.json",
    embedding_model="titan-text-embeddings-v2"
)

# 2. Initialize the agent
agent = Agent(
    name="utility-monitor-agent",
    model="anthropic.claude-3-5-haiku-20241022-v1:0",
    knowledge_base=kb
)

# 3. Build prompt for agent reasoning
def build_prompt(daily_usage):
    return f"""
You are a smart agent monitoring elderly residents.

Today's usage: {json.dumps(daily_usage)}

Historical usage (monthly) is available in your knowledge base.

Compare today's electricity and gas usage against expected daily averages (monthly usage ÷ 30).
If today's usage is significantly lower or higher than expected, it may indicate a medical emergency.

Respond in JSON with:
{{ "status": "normal" or "alert", "reason": "<explanation>" }}
"""

# 4. Sample daily usage
daily_usage = {
    "dwelling_type": "3-room",
    "region": "Central Region",
    "description": "Novena",
    "date": "2025-09-07",
    "electricity_kwh": 15.0,
    "town_gas_units": 5.0
}

# 5. Run agent
prompt = build_prompt(daily_usage)
response = agent.run(prompt)

# 6. Print and parse response
print("Agent response:", response)
result = json.loads(response)

if result["status"] == "alert":
    print(f"ALERT! Reason: {result['reason']}")
else:
    print("Usage normal.")
