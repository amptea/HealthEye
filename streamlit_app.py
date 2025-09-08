import sys
from pathlib import Path
import time
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


def _load_app_config() -> dict:
    try:
        import json
        return json.loads(Path("config.json").read_text())
    except Exception:
        return {}


def _save_app_config(cfg: dict) -> None:
    import json
    Path("config.json").write_text(json.dumps(cfg, indent=2))


def page_analyze_single():
    st.header("📊 Analyze Single Reading")
    
    # Use columns to organize the form better
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True, height=485):
            st.subheader("Resident Information")
            resident_id = st.text_input("Resident ID", value="RES001", help="Unique identifier for the resident")
            monitor = get_monitor()
            profile = monitor.get_resident_profile(resident_id) or {}
            dwelling_type = st.selectbox("Dwelling Type", 
                                       options=["1-room", "2-room", "3-room", "4-room", "5-room", "Executive"],
                                       index=2 if profile.get("dwelling_type") == "3-room" else 0)
            region = st.selectbox("Region", 
                                options=["North East Region", "North West Region", "Central Region", 
                                         "East Region", "West Region"],
                                index=0 if profile.get("region") == "North East Region" else 0)
            description = st.text_input("Description", value=profile.get("description", "Ang Mo Kio"))
    
    with col2:
        with st.container(border=True):
            st.subheader("Usage Data")
            electricity_kwh = st.number_input("Electricity (kWh)", min_value=0.0, value=15.0, step=0.1)
            gas_kwh = st.number_input("Gas (kWh)", min_value=0.0, value=5.0, step=0.1)
            date = st.date_input("Date")
            notes = st.text_area("Notes", value="", height=100)
            save_profile = st.checkbox("Save as resident profile")
    
    submitted = st.button("Run Analysis", type="primary", use_container_width=True)
    
    if submitted:
        # Create a status container to show the actual AI agent steps
        with st.status("🤖 Starting AI Analysis...", expanded=True) as status:
            progress_container = st.container()
            progress_bar = st.progress(0, text="Starting...")
            
            def progress_callback(message):
                with progress_container:
                    st.info(f"🔄 {message}")
            
            # Get monitor instance
            monitor = get_monitor()
            
            if save_profile:
                progress_callback("Saving resident profile...")
                monitor.set_resident_profile(resident_id, dwelling_type, region, description)
                progress_callback("Resident profile saved")
            
            # Run the analysis with progress updates
            result = monitor.add_usage_reading(
                resident_id=resident_id,
                electricity_kwh=electricity_kwh,
                gas_kwh=gas_kwh,
                dwelling_type=dwelling_type,
                region=region,
                description=description,
                date=str(date),
                notes=notes or None,
                progress_callback=progress_callback  # Pass the callback
            )
            
            progress_bar.progress(1.0, text="✅ Complete!")
            status.update(label="Analysis Complete!", state="complete")
        
        # Display the results
        st.subheader("Analysis Results")
        
        # Use columns for metrics
        analysis = result.get("tracker_analysis", {}).get("analysis", {})
        status_val = analysis.get("status", "unknown").lower()
        severity = analysis.get("severity", "low").lower()
        
        # Color coding based on status and severity
        if status_val == "normal":
            status_color = "#28a745"
            status_icon = "✅"
        elif status_val == "alert":
            status_color = "#dc3545"
            status_icon = "⚠️"
        elif status_val == "snoozed":
            status_color = "#6c757d"
            status_icon = "⏸️"
        else:
            status_color = "#6c757d"
            status_icon = "❓"
        
        if severity == "critical":
            severity_color = "#dc3545"
            severity_icon = "🔴"
        elif severity == "high":
            severity_color = "#fd7e14"
            severity_icon = "🟠"
        elif severity == "medium":
            severity_color = "#ffc107"
            severity_icon = "🟡"
        elif severity == "low":
            severity_color = "#28a745"
            severity_icon = "🟢"
        else:
            severity_color = "#6c757d"
            severity_icon = "⚪"
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'''
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid {status_color};">
                <h3 style="margin: 0; color: #495057;">Status</h3>
                <h2 style="margin: 5px 0; color: {status_color};">{status_icon} {status_val.upper()}</h2>
            </div>
            ''', unsafe_allow_html=True)
        with col2:
            st.markdown(f'''
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid {severity_color};">
                <h3 style="margin: 0; color: #495057;">Severity</h3>
                <h2 style="margin: 5px 0; color: {severity_color};">{severity_icon} {severity.upper()}</h2>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        # Show analysis details
        with st.expander("📋 Detailed Analysis", expanded=True):
            st.markdown("**Reason:**")
            
            reason_text = analysis.get("reason", "No reason provided")
            if "no historical data" in reason_text.lower():
                st.info(f"📊 {reason_text}", icon="ℹ️")
            elif "unusual" in reason_text.lower() or "abnormal" in reason_text.lower():
                st.warning(f"⚠️ {reason_text}", icon="⚠️")
            elif "snoozed" in reason_text.lower():
                st.info(f"⏸️ {reason_text}", icon="⏸️")
            else:
                st.info(f"ℹ️ {reason_text}", icon="ℹ️")
            
            if recs := analysis.get("recommendations"):
                st.markdown("**Recommendations:**")
                for i, r in enumerate(recs, 1):
                    st.markdown(f"{i}. {r}")
            
            # Show analysis summary if available
            if analysis_summary := analysis.get("analysis_summary"):
                st.markdown("**Analysis Summary:**")
                if kb_retrieval := analysis_summary.get("kb_retrieval"):
                    st.markdown(f"*Knowledge Base Retrieval:* {kb_retrieval}")
                if anomaly_detection := analysis_summary.get("anomaly_detection"):
                    st.markdown(f"*Anomaly Detection:* {anomaly_detection}")
                if consolidated := analysis_summary.get("consolidated_conclusion"):
                    st.markdown(f"*Final Assessment:* {consolidated}")
            
            # Show statistics if available - FIXED VERSION
            if statistics := analysis.get("statistics"):
                st.markdown("**Usage Statistics:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    if electricity := statistics.get("electricity"):
                        st.markdown("**Electricity:**")
                        st.markdown(f"Current Daily: {electricity.get('current_daily', 'N/A')} kWh")
                        
                        # Safely handle historical daily average
                        hist_daily_avg = electricity.get('historical_daily_avg', 'N/A')
                        if isinstance(hist_daily_avg, (int, float)):
                            st.markdown(f"Historical Daily Avg: {hist_daily_avg:.2f} kWh")
                        else:
                            st.markdown(f"Historical Daily Avg: {hist_daily_avg} kWh")
                        
                        if deviation := electricity.get('deviation_percent'):
                            if isinstance(deviation, (int, float)):
                                st.markdown(f"Deviation: {deviation:.1f}%")
                            else:
                                st.markdown(f"Deviation: {deviation}%")
                
                with col2:
                    if gas := statistics.get("gas"):
                        st.markdown("**Gas:**")
                        st.markdown(f"Current Daily: {gas.get('current_daily', 'N/A')} kWh")
                        
                        # Safely handle historical daily average
                        hist_daily_avg = gas.get('historical_daily_avg', 'N/A')
                        if isinstance(hist_daily_avg, (int, float)):
                            st.markdown(f"Historical Daily Avg: {hist_daily_avg:.2f} kWh")
                        else:
                            st.markdown(f"Historical Daily Avg: {hist_daily_avg} kWh")
                        
                        if deviation := gas.get('deviation_percent'):
                            if isinstance(deviation, (int, float)):
                                st.markdown(f"Deviation: {deviation:.1f}%")
                            else:
                                st.markdown(f"Deviation: {deviation}%")
        
        # Show alerts if any were created
        if alerts_created := result.get("alerts_created", []):
            st.markdown("**🚨 Alerts Generated:**")
            for alert in alerts_created:
                st.error(f"Alert {alert.get('alert_id', 'N/A')}: {alert.get('message', 'No message')}")
        
        # Raw data expander
        with st.expander("📄 Raw Output"):
            st.json(result)




def page_notification_settings():
    st.header("🔔 Notification Settings (Email)")
    
    # Use tabs to organize the settings
    tab1, tab2 = st.tabs(["Configuration", "Test Email"])
    
    with tab1:
        cfg = _load_app_config()
        email_cfg = cfg.get("email", {})
        notif_cfg = cfg.get("notifications", {})

        with st.form("email_settings_form"):
            st.subheader("Global Settings")
            enable_notifications = st.checkbox(
                "Enable email notifications",
                value=bool(notif_cfg.get("enable_email", True)),
                help="Master switch for all email notifications"
            )
            
            st.subheader("SMTP Configuration")
            email_enabled = st.checkbox(
                "Enable SMTP sending",
                value=bool(email_cfg.get("enabled", False)),
                help="Must be enabled to send emails"
            )
            
            # Use columns for server settings
            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input("SMTP server", value=email_cfg.get("smtp_server", "smtp.gmail.com"))
            with col2:
                smtp_port = st.number_input("SMTP port", min_value=1, max_value=65535, 
                                          value=int(email_cfg.get("smtp_port", 587)))
            
            # Authentication details
            username = st.text_input("SMTP username", value=email_cfg.get("username", ""))
            password = st.text_input("SMTP password / app password", type="password", 
                                   value=email_cfg.get("password", ""))
            
            # Address details
            col1, col2 = st.columns(2)
            with col1:
                from_addr = st.text_input("From address", value=email_cfg.get("from_address", ""))
            with col2:
                to_addrs_str = st.text_area(
                    "To addresses (comma-separated)",
                    value=", ".join(email_cfg.get("to_addresses", [])),
                    help="Separate multiple addresses with commas"
                )

            saved = st.form_submit_button("Save Settings", type="primary")

        if saved:
            cfg.setdefault("notifications", {})["enable_email"] = bool(enable_notifications)
            cfg.setdefault("email", {})
            cfg["email"]["enabled"] = bool(email_enabled)
            cfg["email"]["smtp_server"] = smtp_server.strip()
            cfg["email"]["smtp_port"] = int(smtp_port)
            cfg["email"]["username"] = username.strip()
            cfg["email"]["password"] = password
            cfg["email"]["from_address"] = from_addr.strip()
            to_list = [a.strip() for a in to_addrs_str.split(",") if a.strip()]
            cfg["email"]["to_addresses"] = to_list
            try:
                _save_app_config(cfg)
                # Reinitialize monitor so new settings load into AlertSystem
                st.session_state.pop("monitor", None)
                st.success("✅ Email settings saved successfully!")
            except Exception as e:
                st.error(f"❌ Failed to save config: {e}")
    
    with tab2:
        st.subheader("Send Test Email")
        st.info("This will create a test critical alert which triggers an email send.")
        
        if st.button("Send Test Alert Email", type="primary"):
            monitor = get_monitor()
            try:
                alert = monitor.alert_system.create_alert(
                    resident_id="RES-TEST",
                    dwelling_type="3-room",
                    region="North East Region",
                    description="Ang Mo Kio",
                    severity="critical",
                    message="Test email from HealthEye Streamlit",
                    recommendations=["This is a test alert email for demo"]
                )
                st.success(f"✅ Triggered alert {alert.id}. Check inboxes in to_addresses.")
            except Exception as e:
                st.error(f"❌ Failed to trigger test email: {e}")


def page_alerts():
    st.header("🚨 Alerts")
    monitor = get_monitor()
    pending = monitor.alert_system.get_pending_alerts()

    if not pending:
        st.info("No pending alerts.")
        return

    for alert in pending:
        # Color code based on severity
        if alert.severity.value == "critical":
            border_color = "#dc3545"
            icon = "🔴"
        elif alert.severity.value == "high":
            border_color = "#fd7e14"
            icon = "🟠"
        elif alert.severity.value == "medium":
            border_color = "#ffc107"
            icon = "🟡"
        else:
            border_color = "#6c757d"
            icon = "⚪"
            
        with st.container(border=True):
            st.markdown(f"""
            <div style="border-left: 5px solid {border_color}; padding-left: 15px;">
                <h3>{icon} {alert.severity.value.upper()}: {alert.message[:60]}...</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Resident:** {alert.resident_id}")
                st.write(f"**Location:** {alert.dwelling_type} in {alert.description}, {alert.region}")
                st.write(f"**Time:** {alert.timestamp}")
                
                with st.expander("View Recommendations"):
                    for r in alert.recommendations:
                        st.write(f"- {r}")
            
            with col2:
                st.write("**Actions:**")
                if st.button("Acknowledge", key=f"ack_{alert.id}", use_container_width=True):
                    monitor.alert_system.acknowledge_alert(alert.id, acknowledged_by="StreamlitUser")
                    st.rerun()
                if st.button("Resolve", key=f"res_{alert.id}", use_container_width=True):
                    monitor.alert_system.resolve_alert(alert.id)
                    st.rerun()
                if st.button("Escalate", key=f"esc_{alert.id}", use_container_width=True):
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


def main():
    st.set_page_config(
        page_title="HealthEye - Elderly Monitoring", 
        layout="wide",
        page_icon="👁️"  # Add an icon for visual interest
    )
    
    # Add custom CSS for styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #2E86AB;
        padding-bottom: 10px;
        border-bottom: 2px solid #F26419;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Update your title with the custom class
    st.markdown('<h1 class="main-header">HealthEye - Elderly Home Monitoring</h1>', unsafe_allow_html=True)


    page = st.sidebar.radio(
        "Navigate",
        [
            "Analyze Single Reading",
            "Alerts",
            "Resident Snooze",
            "Notification Settings",
        ],
    )

    if page == "Analyze Single Reading":
        page_analyze_single()
    elif page == "Alerts":
        page_alerts()
    elif page == "Resident Snooze":
        page_snooze()
    elif page == "Notification Settings":
        page_notification_settings()
    
if __name__ == "__main__":
    main()
