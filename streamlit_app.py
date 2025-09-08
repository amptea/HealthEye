import sys
from pathlib import Path

import streamlit as st

# Ensure src is on the path
ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from elderly_monitor import ElderlyMonitor


def get_monitor() -> ElderlyMonitor:
    if "monitor" not in st.session_state:
        st.session_state.monitor = ElderlyMonitor("config.json")
    return st.session_state.monitor


def page_analyze_single():
    st.header("Analyze Single Reading")

    with st.form("single_reading_form"):
        resident_id = st.text_input("Resident ID", value="RES001")
        monitor = get_monitor()
        profile = monitor.get_resident_profile(resident_id) or {}
        dwelling_type = st.text_input("Dwelling Type", value=profile.get("dwelling_type", "3-room"))
        region = st.text_input("Region", value=profile.get("region", "North East Region"))
        description = st.text_input("Description", value=profile.get("description", "Ang Mo Kio"))
        electricity_kwh = st.number_input("Electricity (kWh)", min_value=0.0, value=15.0, step=0.1)
        gas_kwh = st.number_input("Gas (kWh)", min_value=0.0, value=5.0, step=0.1)
        date = st.date_input("Date")
        notes = st.text_input("Notes", value="")
        save_profile = st.checkbox("Save as resident profile")
        submitted = st.form_submit_button("Run Analysis")

    if submitted:
        monitor = get_monitor()
        if save_profile:
            monitor.set_resident_profile(resident_id, dwelling_type, region, description)
        result = monitor.add_usage_reading(
            resident_id=resident_id,
            electricity_kwh=electricity_kwh,
            gas_kwh=gas_kwh,
            dwelling_type=dwelling_type,
            region=region,
            description=description,
            date=str(date),
            notes=notes or None,
        )

        st.subheader("Result")
        analysis = result.get("tracker_analysis", {}).get("analysis", {})
        st.metric("Status", analysis.get("status", "unknown"))
        st.metric("Severity", analysis.get("severity", "low"))
        st.write("Reason:")
        st.write(analysis.get("reason", ""))

        if recs := analysis.get("recommendations"):
            st.write("Recommendations:")
            for r in recs:
                st.write(f"- {r}")

        st.write("Raw Output:")
        st.json(result)




def page_alerts():
    st.header("Alerts")
    monitor = get_monitor()
    pending = monitor.alert_system.get_pending_alerts()

    if not pending:
        st.info("No pending alerts.")
        return

    for alert in pending:
        with st.expander(f"{alert.id} - {alert.severity.value.upper()} - {alert.message[:60]}..."):
            st.write(f"Resident: {alert.resident_id}")
            st.write(f"Location: {alert.dwelling_type} in {alert.description}, {alert.region}")
            st.write(f"Time: {alert.timestamp}")
            st.write("Recommendations:")
            for r in alert.recommendations:
                st.write(f"- {r}")

            cols = st.columns(3)
            if cols[0].button("Acknowledge", key=f"ack_{alert.id}"):
                monitor.alert_system.acknowledge_alert(alert.id, acknowledged_by="StreamlitUser")
                st.rerun()
            if cols[1].button("Resolve", key=f"res_{alert.id}"):
                monitor.alert_system.resolve_alert(alert.id)
                st.rerun()
            if cols[2].button("Escalate", key=f"esc_{alert.id}"):
                monitor.alert_system.escalate_alert(alert.id)
                st.rerun()


def page_snooze():
    st.header("Resident Snooze (Core Memory)")
    monitor = get_monitor()

    with st.form("snooze_form"):
        resident_id = st.text_input("Resident ID", value="RES001")
        start = st.date_input("Start date")
        end = st.date_input("End date")
        reason = st.text_input("Reason", value="Staying with family for a week")
        submitted = st.form_submit_button("Set Snooze")
    if submitted:
        data = monitor.set_resident_snooze(resident_id, str(start), str(end), reason)
        st.success(f"Snoozed {resident_id} from {data['start_date']} to {data['end_date']}")

    st.subheader("Active Snoozes")
    try:
        import json
        memory_file = Path(monitor._core_memory.file)
        if memory_file.exists():
            memory = json.loads(memory_file.read_text())
            snoozes = memory.get("snoozes", {})
            if snoozes:
                for resident_id, snooze_data in snoozes.items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{resident_id}**: {snooze_data['start_date']} to {snooze_data['end_date']}")
                        st.write(f"Reason: {snooze_data.get('reason', 'No reason provided')}")
                    with col2:
                        if st.button("Clear", key=f"clear_{resident_id}"):
                            ok = monitor.clear_resident_snooze(resident_id)
                            if ok:
                                st.success("Cleared!")
                                st.rerun()
                            else:
                                st.error("Failed to clear")
            else:
                st.info("No snoozes set.")
        else:
            st.info("No memory file found.")
    except Exception as e:
        st.error(f"Error loading snoozes: {e}")

    st.divider()
    st.subheader("Clear Snooze by ID")
    clear_id = st.text_input("Resident ID to clear", value="")
    if st.button("Clear Snooze") and clear_id:
        ok = monitor.clear_resident_snooze(clear_id)
        if ok:
            st.success("Cleared!")
            st.rerun()
        else:
            st.error("No snooze found for this resident")


def page_analysis_demo():
    st.header("Analysis Process Demo")
    st.caption("This demonstrates the two-step analysis process used by the agent.")
    
    st.subheader("Step 1: Knowledge Base Retrieval & Generation")
    st.write("The agent uses retrieve and generate to ask:")
    st.code("""
    "What's the average monthly electricity usage for [dwelling_type] in [region], [description]?"
    "What's the average monthly gas usage for [dwelling_type] in [region], [description]?"
    """)
    st.write("Then converts monthly averages to daily estimates (÷ 30) for comparison.")
    
    st.subheader("Step 2: Statistical Anomaly Detection")
    st.write("The agent uses the detect_anomaly tool for detailed statistical analysis:")
    st.code("""
    - Z-score calculations
    - Percentile analysis
    - Elderly-specific thresholds
    - Pattern recognition
    """)
    
    st.subheader("Step 3: Consolidation & Decision")
    st.write("The agent consolidates insights from BOTH sources:")
    st.write("• **KB Retrieval**: Historical averages and trends")
    st.write("• **Anomaly Detection**: Statistical validation")
    st.write("• **Final Assessment**: Combined analysis for medical situation severity")
    
    st.subheader("Email Notifications (Demo)")
    st.info("For critical situations, the agent will mention that it will email next of kin. This is for demonstration purposes only - no actual emails are sent.")
    
    if st.button("Create Demo Alert"):
        monitor = get_monitor()
        alert = monitor.alert_system.create_alert(
            resident_id="RES-DEMO",
            dwelling_type="3-room",
            region="North East Region",
            description="Ang Mo Kio",
            severity="critical",
            message="Demo alert - Agent will email next of kin for this critical situation",
            recommendations=["This is a demonstration alert"]
        )
        st.success(f"Created {alert.id}. Agent would email next of kin for this critical situation.")


def main():
    st.set_page_config(page_title="HealthEye - Elderly Monitoring", layout="wide")
    st.title("HealthEye - Elderly Home Monitoring")

    page = st.sidebar.radio(
        "Navigate",
        [
            "Analyze Single Reading",
            "Alerts",
            "Resident Snooze",
            "Analysis Process Demo",
        ],
    )

    if page == "Analyze Single Reading":
        page_analyze_single()
    elif page == "Alerts":
        page_alerts()
    elif page == "Resident Snooze":
        page_snooze()
    elif page == "Analysis Process Demo":
        page_analysis_demo()


if __name__ == "__main__":
    main()


