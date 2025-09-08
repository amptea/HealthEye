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




def page_notification_settings():
    st.header("Notification Settings (Email)")
    cfg = _load_app_config()
    email_cfg = cfg.get("email", {})
    notif_cfg = cfg.get("notifications", {})

    with st.form("email_settings_form"):
        st.subheader("SMTP Configuration")
        enable_notifications = st.checkbox(
            "Enable email notifications (global)",
            value=bool(notif_cfg.get("enable_email", True)),
        )
        email_enabled = st.checkbox(
            "Enable SMTP sending (email.enabled)",
            value=bool(email_cfg.get("enabled", False)),
        )
        smtp_server = st.text_input("SMTP server", value=email_cfg.get("smtp_server", "smtp.gmail.com"))
        smtp_port = st.number_input("SMTP port", min_value=1, max_value=65535, value=int(email_cfg.get("smtp_port", 587)))
        username = st.text_input("SMTP username", value=email_cfg.get("username", ""))
        password = st.text_input("SMTP password / app password", type="password", value=email_cfg.get("password", ""))
        from_addr = st.text_input("From address", value=email_cfg.get("from_address", ""))
        to_addrs_str = st.text_area(
            "To addresses (comma-separated)",
            value=", ".join(email_cfg.get("to_addresses", [])),
        )

        saved = st.form_submit_button("Save Settings")

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
            st.success("Email settings saved. Alert system will use these settings.")
        except Exception as e:
            st.error(f"Failed to save config: {e}")

    st.divider()
    st.subheader("Send Test Email")
    st.caption("Creates a test critical alert which triggers an email send.")
    if st.button("Send Test Alert Email"):
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
            st.success(f"Triggered alert {alert.id}. Check inboxes in to_addresses.")
        except Exception as e:
            st.error(f"Failed to trigger test email: {e}")


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


def main():
    st.set_page_config(page_title="HealthEye - Elderly Monitoring", layout="wide")
    st.title("HealthEye - Elderly Home Monitoring")

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


