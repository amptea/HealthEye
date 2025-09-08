"""
Alert System for Elderly Home Monitoring
Handles different severity levels and notification channels
"""

import json
import smtplib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status"""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    resident_id: str
    dwelling_type: str
    region: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    recommendations: List[str]
    timestamp: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalation_level: int = 0

class AlertSystem:
    """
    Comprehensive alert system for elderly home monitoring
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize alert system
        
        Args:
            config_file: Path to configuration file
        """
        self.alerts = []
        self.alert_count = 0
        self.config = self._load_config(config_file)
        self.escalation_rules = self._setup_escalation_rules()
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_address": "",
                "to_addresses": []
            },
            "escalation": {
                "critical_timeout_minutes": 15,
                "high_timeout_minutes": 60,
                "medium_timeout_minutes": 240,
                "max_escalation_levels": 3
            },
            "notifications": {
                "enable_email": True,
                "enable_logging": True,
                "enable_console": True
            }
        }
        
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")
        
        return default_config
    
    def _setup_escalation_rules(self) -> Dict:
        """Setup escalation rules based on severity and time"""
        return {
            AlertSeverity.CRITICAL: {
                "timeout_minutes": self.config["escalation"]["critical_timeout_minutes"],
                "escalation_actions": ["immediate_notification", "call_emergency_services"]
            },
            AlertSeverity.HIGH: {
                "timeout_minutes": self.config["escalation"]["high_timeout_minutes"],
                "escalation_actions": ["notify_caregivers", "schedule_welfare_check"]
            },
            AlertSeverity.MEDIUM: {
                "timeout_minutes": self.config["escalation"]["medium_timeout_minutes"],
                "escalation_actions": ["notify_supervisor", "log_incident"]
            },
            AlertSeverity.LOW: {
                "timeout_minutes": 480,  # 8 hours
                "escalation_actions": ["log_incident"]
            }
        }
    
    def create_alert(self, 
                    resident_id: str,
                    dwelling_type: str,
                    region: str,
                    description: str,
                    severity: str,
                    message: str,
                    recommendations: List[str],
                    analysis_data: Optional[Dict] = None) -> Alert:
        """
        Create a new alert
        
        Args:
            resident_id: Resident identifier
            dwelling_type: Type of dwelling
            region: Region
            description: Specific location
            severity: Alert severity level
            message: Alert message
            recommendations: List of recommendations
            analysis_data: Optional analysis data
            
        Returns:
            Created alert
        """
        self.alert_count += 1
        alert_id = f"ALERT_{self.alert_count:06d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        alert = Alert(
            id=alert_id,
            resident_id=resident_id,
            dwelling_type=dwelling_type,
            region=region,
            description=description,
            severity=AlertSeverity(severity),
            status=AlertStatus.PENDING,
            message=message,
            recommendations=recommendations,
            timestamp=datetime.now(),
            escalation_level=0
        )
        
        self.alerts.append(alert)
        
        # Send immediate notifications
        self._send_notifications(alert)
        
        logger.info(f"Created alert {alert_id} for resident {resident_id} - {severity.upper()}")
        return alert
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        if self.config["notifications"]["enable_console"]:
            self._send_console_notification(alert)
        
        if self.config["notifications"]["enable_logging"]:
            self._send_log_notification(alert)
        
        if self.config["notifications"]["enable_email"] and self.config["email"]["enabled"]:
            self._send_email_notification(alert)
    
    def _send_console_notification(self, alert: Alert):
        """Send console notification"""
        severity_colors = {
            AlertSeverity.LOW: "\033[94m",      # Blue
            AlertSeverity.MEDIUM: "\033[93m",   # Yellow
            AlertSeverity.HIGH: "\033[91m",     # Red
            AlertSeverity.CRITICAL: "\033[95m"  # Magenta
        }
        
        color = severity_colors.get(alert.severity, "")
        reset = "\033[0m"
        
        print(f"\n{color}{'='*60}")
        print(f"🚨 ALERT: {alert.severity.value.upper()}")
        print(f"{'='*60}{reset}")
        print(f"Alert ID: {alert.id}")
        print(f"Resident: {alert.resident_id}")
        print(f"Location: {alert.dwelling_type} in {alert.description}, {alert.region}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Message: {alert.message}")
        print(f"Recommendations:")
        for i, rec in enumerate(alert.recommendations, 1):
            print(f"  {i}. {rec}")
        print(f"{color}{'='*60}{reset}\n")
    
    def _send_log_notification(self, alert: Alert):
        """Send log notification"""
        logger.critical(f"ALERT {alert.severity.value.upper()}: {alert.id} - {alert.message}")
        logger.critical(f"Resident: {alert.resident_id} | Location: {alert.description}")
        logger.critical(f"Recommendations: {'; '.join(alert.recommendations)}")
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification (Demo mode - just logs the action)"""
        try:
            # For hackathon demo - just log that we would send email
            logger.info(f"📧 DEMO: Would send email notification for alert {alert.id}")
            logger.info(f"📧 DEMO: Subject: 🚨 {alert.severity.value.upper()} ALERT - Elderly Home Monitoring")
            logger.info(f"📧 DEMO: To: Next of kin for resident {alert.resident_id}")
            logger.info(f"📧 DEMO: Message: {alert.message}")
            
            # In a real implementation, this would send the actual email
            # For now, we just mention it in the alert message
            if not hasattr(alert, '_email_mentioned'):
                alert.message += f" [DEMO: Next of kin will be notified via email]"
                alert._email_mentioned = True
            
        except Exception as e:
            logger.error(f"Failed to process email notification for alert {alert.id}: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: Person acknowledging the alert
            
        Returns:
            True if successful, False otherwise
        """
        alert = self.get_alert(alert_id)
        if alert and alert.status == AlertStatus.PENDING:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now()
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert
        
        Args:
            alert_id: Alert ID to resolve
            
        Returns:
            True if successful, False otherwise
        """
        alert = self.get_alert(alert_id)
        if alert and alert.status in [AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            logger.info(f"Alert {alert_id} resolved")
            return True
        return False
    
    def escalate_alert(self, alert_id: str) -> bool:
        """
        Escalate an alert to the next level
        
        Args:
            alert_id: Alert ID to escalate
            
        Returns:
            True if successful, False otherwise
        """
        alert = self.get_alert(alert_id)
        if not alert or alert.status == AlertStatus.RESOLVED:
            return False
        
        max_levels = self.config["escalation"]["max_escalation_levels"]
        if alert.escalation_level >= max_levels:
            logger.warning(f"Alert {alert_id} already at maximum escalation level")
            return False
        
        alert.escalation_level += 1
        alert.status = AlertStatus.ESCALATED
        
        # Send escalation notifications
        self._send_notifications(alert)
        
        logger.warning(f"Alert {alert_id} escalated to level {alert.escalation_level}")
        return True
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        for alert in self.alerts:
            if alert.id == alert_id:
                return alert
        return None
    
    def get_pending_alerts(self) -> List[Alert]:
        """Get all pending alerts"""
        return [alert for alert in self.alerts if alert.status == AlertStatus.PENDING]
    
    def get_critical_alerts(self) -> List[Alert]:
        """Get all critical alerts"""
        return [alert for alert in self.alerts if alert.severity == AlertSeverity.CRITICAL]
    
    def check_escalations(self):
        """Check for alerts that need escalation"""
        now = datetime.now()
        
        for alert in self.alerts:
            if alert.status in [AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]:
                rules = self.escalation_rules.get(alert.severity, {})
                timeout_minutes = rules.get("timeout_minutes", 480)
                
                time_since_creation = now - alert.timestamp
                if time_since_creation.total_seconds() > timeout_minutes * 60:
                    self.escalate_alert(alert.id)
    
    def get_alert_summary(self) -> Dict:
        """Get summary of all alerts"""
        total_alerts = len(self.alerts)
        pending_count = len(self.get_pending_alerts())
        critical_count = len(self.get_critical_alerts())
        
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([a for a in self.alerts if a.severity == severity])
        
        status_counts = {}
        for status in AlertStatus:
            status_counts[status.value] = len([a for a in self.alerts if a.status == status])
        
        return {
            "total_alerts": total_alerts,
            "pending_alerts": pending_count,
            "critical_alerts": critical_count,
            "severity_breakdown": severity_counts,
            "status_breakdown": status_counts,
            "last_updated": datetime.now().isoformat()
        }
    
    def export_alerts(self, filename: Optional[str] = None) -> str:
        """Export alerts to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alerts_export_{timestamp}.json"
        
        alerts_data = []
        for alert in self.alerts:
            alert_dict = {
                "id": alert.id,
                "resident_id": alert.resident_id,
                "dwelling_type": alert.dwelling_type,
                "region": alert.region,
                "description": alert.description,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "recommendations": alert.recommendations,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged_by": alert.acknowledged_by,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "escalation_level": alert.escalation_level
            }
            alerts_data.append(alert_dict)
        
        with open(filename, 'w') as f:
            json.dump(alerts_data, f, indent=2)
        
        logger.info(f"Exported {len(alerts_data)} alerts to {filename}")
        return filename


# Example usage
if __name__ == "__main__":
    # Initialize alert system
    alert_system = AlertSystem()
    
    # Create test alerts
    alert1 = alert_system.create_alert(
        resident_id="RES001",
        dwelling_type="3-room",
        region="North East Region",
        description="Ang Mo Kio",
        severity="critical",
        message="Extremely low electricity usage detected - potential medical emergency",
        recommendations=[
            "Immediate welfare check required",
            "Contact emergency services if no response",
            "Check if resident is conscious and mobile"
        ]
    )
    
    alert2 = alert_system.create_alert(
        resident_id="RES002",
        dwelling_type="1-room / 2-room",
        region="Central Region",
        description="Bishan",
        severity="high",
        message="Unusually high gas usage detected",
        recommendations=[
            "Check for appliance malfunction",
            "Verify resident is safe",
            "Schedule maintenance check"
        ]
    )
    
    # Get summary
    summary = alert_system.get_alert_summary()
    print("Alert Summary:", json.dumps(summary, indent=2))
