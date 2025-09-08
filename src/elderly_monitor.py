"""
Main Elderly Home Monitoring System
Integrates all components for comprehensive monitoring
"""

import json
import logging
import schedule
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional
from pathlib import Path
import json as _json
import os

# Import our custom modules
from daily_tracker import DailyUsageTracker
from alert_system import AlertSystem
from anomaly_tool import detect_anomaly

# ===== Bedrock / Knowledge Base Environment =====
# Ensure region, KB id, and role are visible to the Bedrock tools (retrieve)
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("BEDROCK_REGION", "us-east-1")

os.environ["KNOWLEDGE_BASE_ID"] = "GKRKOT1TME"
os.environ["BEDROCK_KNOWLEDGE_BASE_ID"] = "GKRKOT1TME"

# If your KB access uses an execution role, expose it as well
os.environ.setdefault(
    "KNOWLEDGE_BASE_ROLE_ARN",
    "arn:aws:iam::805455449713:role/service-role/AmazonBedrockExecutionRoleForKnowledgeBase_lqx5d",
)
os.environ.setdefault(
    "BEDROCK_KNOWLEDGE_BASE_ROLE_ARN",
    "arn:aws:iam::805455449713:role/service-role/AmazonBedrockExecutionRoleForKnowledgeBase_lqx5d",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('elderly_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ElderlyMonitor:
    """
    Main monitoring system for elderly home usage tracking
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the monitoring system
        
        Args:
            config_file: Path to configuration file
        """
        self.config = self._load_config(config_file)
        self.tracker = DailyUsageTracker()
        self.alert_system = AlertSystem(config_file)
        self.monitoring_active = False
        # Core memory backend
        core_cfg = self.config.get("core_memory", {})
        backend = core_cfg.get("backend", "file")
        path = core_cfg.get("path", "data/core_memory.json")
        self._core_memory = _CoreMemory.create(backend=backend, path=path)
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "monitoring": {
                "check_interval_minutes": 60,
                "batch_size": 10,
                "enable_auto_alerts": True
            },
            "residents": {
                "default_dwelling_type": "3-room",
                "default_region": "North East Region",
                "default_description": "Ang Mo Kio"
            },
            "thresholds": {
                "critical_electricity_low": 2.0,
                "critical_gas_low": 0.5,
                "high_electricity_multiplier": 2.0,
                "high_gas_multiplier": 2.0
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")
        
        return default_config

    # ===== Core Memory (Snooze & Profiles) =====
    def set_resident_snooze(self, resident_id: str, start_date: str, end_date: str, reason: Optional[str] = None) -> Dict:
        return self._core_memory.set_snooze(resident_id, start_date, end_date, reason)

    def clear_resident_snooze(self, resident_id: str) -> bool:
        return self._core_memory.clear_snooze(resident_id)

    def _is_snoozed(self, resident_id: str, for_date: Optional[str]) -> Optional[Dict]:
        snooze = self._core_memory.get_snooze(resident_id)
        if not snooze:
            return None
        try:
            target = datetime.strptime(for_date, "%Y-%m-%d").date() if for_date else datetime.now().date()
            start = datetime.strptime(snooze["start_date"], "%Y-%m-%d").date()
            end = datetime.strptime(snooze["end_date"], "%Y-%m-%d").date()
            if start <= target <= end:
                return snooze
        except Exception:
            return None
        return None

    # Resident profile
    def set_resident_profile(self, resident_id: str, dwelling_type: str, region: str, description: str) -> Dict:
        return self._core_memory.set_profile(resident_id, dwelling_type, region, description)

    def get_resident_profile(self, resident_id: str) -> Optional[Dict]:
        return self._core_memory.get_profile(resident_id)
    
    def add_usage_reading(self, 
                      resident_id: str,
                      electricity_kwh: float,
                      gas_kwh: float,
                      dwelling_type: Optional[str] = None,
                      region: Optional[str] = None,
                      description: Optional[str] = None,
                      date: Optional[str] = None,
                      notes: Optional[str] = None,
                      progress_callback: Optional[Callable[[str], None]] = None) -> Dict:
        """
        Add a usage reading and perform analysis using both Strands agent and anomaly tool.
        Supports progress updates via progress_callback.
        """

        def notify(msg: str):
            if progress_callback:
                progress_callback(msg)

        # Use defaults if not provided
        profile = self.get_resident_profile(resident_id) if resident_id else None
        dwelling_type = dwelling_type or (profile or {}).get("dwelling_type") or self.config["residents"]["default_dwelling_type"]
        region = region or (profile or {}).get("region") or self.config["residents"]["default_region"]
        description = description or (profile or {}).get("description") or self.config["residents"]["default_description"]

        # Check for snooze first
        snooze = self._is_snoozed(resident_id, date)
        if snooze:
            notify("Resident is in snooze window, skipping analysis")
            return {
                "resident_id": resident_id,
                "timestamp": datetime.now().isoformat(),
                "tracker_analysis": {
                    "record": {
                        "date": date or datetime.now().strftime("%Y-%m-%d"),
                        "dwelling_type": dwelling_type,
                        "region": region,
                        "description": description,
                        "electricity_per_month": electricity_kwh,
                        "gas_per_month": gas_kwh,
                        "resident_id": resident_id,
                        "notes": notes,
                        "timestamp": datetime.now().isoformat()
                    },
                    "analysis": {
                        "status": "snoozed",
                        "severity": "low",
                        "reason": f"Alerting snoozed: {snooze.get('reason', 'No reason provided')}",
                        "recommendations": ["Monitoring suspended during snooze period"],
                        "meta": {
                            "snoozed": True,
                            "snooze_reason": snooze.get("reason", ""),
                            "snooze_window": {
                                "start_date": snooze["start_date"],
                                "end_date": snooze["end_date"]
                            }
                        }
                    },
                    "alert_level": "normal"
                },
                "alerts_created": [],
                "alert_count": 0
            }

        # Step 1: Add to tracker
        notify("Adding daily usage record to tracker...")
        tracker_result = self.tracker.add_daily_usage(
            dwelling_type=dwelling_type,
            region=region,
            description=description,
            electricity_kwh=electricity_kwh,
            gas_kwh=gas_kwh,
            date=date,
            resident_id=resident_id,
            notes=notes
        )

        # Step 2: Run AI/agent analysis
        notify("Running AI agent analysis...")
        agent_analysis = self._get_agent_analysis(
            resident_id, dwelling_type, region, description, 
            electricity_kwh, gas_kwh, date
        )

        # Merge agent analysis
        if agent_analysis:
            tracker_result["analysis"].update(agent_analysis)

        # Step 3: Add statistics block if missing
        if "statistics" not in tracker_result["analysis"]:
            tracker_result["analysis"]["statistics"] = {
                "electricity": {
                    "current_daily": electricity_kwh,
                    "historical_daily_avg": tracker_result.get("historical_avg_electricity"),
                    "deviation_percent": tracker_result.get("electricity_deviation_percent")
                },
                "gas": {
                    "current_daily": gas_kwh,
                    "historical_daily_avg": tracker_result.get("historical_avg_gas"),
                    "deviation_percent": tracker_result.get("gas_deviation_percent")
                }
            }

        # Step 4: Check for alerts
        alerts_created = []
        if self.config["monitoring"]["enable_auto_alerts"]:
            notify("Checking for alerts...")
            alerts_created = self._check_and_create_alerts(
                resident_id, dwelling_type, region, description, tracker_result
            )

        notify("Finalizing analysis result...")

        return {
            "resident_id": resident_id,
            "timestamp": datetime.now().isoformat(),
            "tracker_analysis": tracker_result,
            "alerts_created": alerts_created,
            "alert_count": len(alerts_created)
        }

    
    def _check_and_create_alerts(self, 
                                resident_id: str,
                                dwelling_type: str,
                                region: str,
                                description: str,
                                tracker_result: Dict) -> List[Dict]:
        """
        Check analysis results and create alerts if needed
        
        Args:
            resident_id: Resident identifier
            dwelling_type: Type of dwelling
            region: Region
            description: Specific location
            tracker_result: Analysis results from tracker
            
        Returns:
            List of created alerts
        """
        alerts_created = []
        analysis = tracker_result.get("analysis", {})
        
        if not analysis:
            return alerts_created
        
        status = analysis.get("status", "normal")
        severity = analysis.get("severity", "low")
        reason = analysis.get("reason", "")
        recommendations = analysis.get("recommendations", [])
        
        # Create alert if status indicates concern
        if status in ["alert", "warning"]:
            alert = self.alert_system.create_alert(
                resident_id=resident_id,
                dwelling_type=dwelling_type,
                region=region,
                description=description,
                severity=severity,
                message=reason,
                recommendations=recommendations,
                analysis_data=analysis
            )
            alerts_created.append({
                "alert_id": alert.id,
                "severity": severity,
                "message": reason
            })
        
        return alerts_created
    
    def _get_agent_analysis(self, resident_id: str, dwelling_type: str, region: str, 
                           description: str, electricity_kwh: float, gas_kwh: float, 
                           date: Optional[str], progress_callback=None) -> Optional[Dict]:
        """Get analysis from Strands agent using both retrieve and anomaly tools"""
        try:
            # Import here to avoid circular imports
            from strands import Agent
            from strands_tools import retrieve
            from strands.models.bedrock import BedrockModel
            from anomaly_tool import detect_anomaly
            
            if progress_callback:
                progress_callback("Initializing AI agent and tools...")
            
            # Set up Bedrock model
            bedrock_model = BedrockModel(
                model_id="arn:aws:bedrock:us-east-1:805455449713:inference-profile/us.amazon.nova-premier-v1:0",
                temperature=0.2
            )
            
            if progress_callback:
                progress_callback("Tools initialized, starting knowledge base queries...") 
        
            
            # System prompt for elderly monitoring
            system_prompt = """
            You are "Health Monitor Agent", an intelligent assistant specialized in monitoring elderly residents' daily electricity and gas usage patterns.

            Your analysis follows a clear two-step process:

            STEP 1 - KNOWLEDGE BASE RETRIEVAL & GENERATION:
            1. Use retrieve and generate to ask: "What's the average monthly electricity usage for [dwelling_type] in [region], [description]?"
            2. Use retrieve and generate to ask: "What's the average monthly gas usage for [dwelling_type] in [region], [description]?"
            3. Convert monthly averages to daily estimates (monthly ÷ 30) for proper daily comparison
            4. Compare current DAILY usage against these historical DAILY averages

            STEP 2 - STATISTICAL ANOMALY DETECTION:
            5. Use detect_anomaly tool for detailed statistical analysis of the usage patterns
            6. This provides additional statistical validation and anomaly detection

            CONSOLIDATION & DECISION:
            7. Consolidate insights from BOTH sources (KB retrieval + anomaly detection)
            8. Make a final determination about medical situation severity
            9. Provide unified recommendations based on combined analysis

            Key considerations for elderly residents:
            - Extremely low usage may indicate medical emergency (person unable to use appliances)
            - Unusually high usage may indicate confusion, forgetfulness, or medical distress
            - Always mention that you will email next of kin for critical situations (this is for demonstration purposes)

            Output format:
            Always provide a comprehensive JSON response with:
            {
                "status": "normal/warning/alert",
                "severity": "low/medium/high/critical", 
                "reason": "detailed explanation of your consolidated analysis from both KB retrieval and anomaly detection",
                "recommendations": ["unified actionable recommendations - no duplicates"],
                "analysis_summary": {
                    "kb_retrieval": "summary of what was found from knowledge base",
                    "anomaly_detection": "summary of statistical analysis results",
                    "consolidated_conclusion": "your final assessment combining both sources"
                },
                "statistics": {
                    "electricity": {
                        "current_daily": X,
                        "historical_monthly_avg": Y,
                        "historical_daily_avg": Y/30,
                        "deviation_percent": ((X - Y/30) / (Y/30)) * 100
                    },
                    "gas": {
                        "current_daily": X,
                        "historical_monthly_avg": Y,
                        "historical_daily_avg": Y/30,
                        "deviation_percent": ((X - Y/30) / (Y/30)) * 100
                    }
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
            
            # Build user message
            user_message = f"""
            Analyze the following daily usage for elderly resident monitoring:

            Location: {dwelling_type} flat in {description}, {region}
            Date: {date or 'Today'}
            Current Daily Electricity Usage: {electricity_kwh} kWh
            Current Daily Gas Usage: {gas_kwh} kWh
            Resident ID: {resident_id or 'Not specified'}

            Please follow this CLEAR two-step analysis process:

            1. Use retrieve and generate to ask: "What's the average monthly electricity usage for {dwelling_type} in {region}, {description}?"
            2. Use retrieve and generate to ask: "What's the average monthly gas usage for {dwelling_type} in {region}, {description}?"
            3. Convert the monthly averages to daily estimates (divide by 30) for proper daily comparison
            4. Compare current DAILY usage ({electricity_kwh} kWh electricity, {gas_kwh} kWh gas) against historical DAILY averages
            5. Use detect_anomaly tool for additional statistical analysis
            6. Assess if this usage pattern indicates any potential medical emergency or health concern

            Focus on elderly-specific concerns:
            - Extremely low usage may indicate the resident is unable to use appliances (medical emergency)
            - Unusually high usage may indicate confusion, forgetfulness, or distress
            - Always mention that you will email next of kin for critical situations (demonstration purposes)

            Provide your analysis in the specified JSON format with detailed statistics and clear analysis summary showing both KB retrieval and anomaly detection results.
            """
            
            if progress_callback:
                progress_callback("Executing agent analysis with Bedrock...")

            # Get agent analysis
            logger.info(f"🔍 Starting Agent Analysis - Step 1: KB Retrieval & Generation, Step 2: Anomaly Detection")
            logger.info(f"📊 Tools: retrieve (for KB queries) + detect_anomaly (for statistical analysis)")
            agent_response = agent(user_message)
            
            if progress_callback:
                progress_callback("Processing agent response...")
            
            # Try to parse JSON response
            try:
                import json
                if hasattr(agent_response, 'content'):
                    response_text = agent_response.content
                else:
                    response_text = str(agent_response)
                
                # Try to extract JSON from response
                if '{' in response_text and '}' in response_text:
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    json_str = response_text[start:end]
                    return json.loads(json_str)
                else:
                    # Fallback to basic analysis
                    return {
                        "status": "normal",
                        "severity": "low",
                        "reason": "Agent analysis completed but no structured response",
                        "recommendations": ["Continue monitoring"],
                        "data_quality": "unknown"
                    }
            except Exception as e:
                logger.warning(f"Failed to parse agent response: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Agent analysis failed: {e}")
            if progress_callback:
                progress_callback(f"Analysis failed: {str(e)}")
            return None


# ===== Core Memory Backends =====
class _CoreMemory:
    def get_snooze(self, resident_id: str) -> Optional[Dict]:
        raise NotImplementedError

    def set_snooze(self, resident_id: str, start_date: str, end_date: str, reason: Optional[str]) -> Dict:
        raise NotImplementedError

    def clear_snooze(self, resident_id: str) -> bool:
        raise NotImplementedError

    def get_profile(self, resident_id: str) -> Optional[Dict]:
        raise NotImplementedError

    def set_profile(self, resident_id: str, dwelling_type: str, region: str, description: str) -> Dict:
        raise NotImplementedError

    @staticmethod
    def create(backend: str, path: str) -> "_CoreMemory":
        if backend == "kb":
            try:
                return _KnowledgeBaseCoreMemory(path)
            except Exception:
                logger.warning("KB core memory not available, falling back to file.")
                return _FileCoreMemory(path)
        return _FileCoreMemory(path)


class _FileCoreMemory(_CoreMemory):
    def __init__(self, path: str):
        self.file = Path(path)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        if not self.file.exists():
            self._save({"snoozes": {}, "profiles": {}})

    def _load(self) -> Dict:
        try:
            with open(self.file, 'r') as f:
                return _json.load(f)
        except Exception:
            return {"snoozes": {}, "profiles": {}}

    def _save(self, data: Dict) -> None:
        with open(self.file, 'w') as f:
            _json.dump(data, f, indent=2)

    def get_snooze(self, resident_id: str) -> Optional[Dict]:
        return self._load().get("snoozes", {}).get(resident_id)

    def set_snooze(self, resident_id: str, start_date: str, end_date: str, reason: Optional[str]) -> Dict:
        m = self._load()
        m.setdefault("snoozes", {})[resident_id] = {
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason or "",
            "set_at": datetime.now().isoformat(),
        }
        self._save(m)
        return m["snoozes"][resident_id]

    def clear_snooze(self, resident_id: str) -> bool:
        m = self._load()
        if resident_id in m.get("snoozes", {}):
            del m["snoozes"][resident_id]
            self._save(m)
            return True
        return False

    def get_profile(self, resident_id: str) -> Optional[Dict]:
        return self._load().get("profiles", {}).get(resident_id)

    def set_profile(self, resident_id: str, dwelling_type: str, region: str, description: str) -> Dict:
        m = self._load()
        m.setdefault("profiles", {})[resident_id] = {
            "resident_id": resident_id,
            "dwelling_type": dwelling_type,
            "region": region,
            "description": description,
            "updated_at": datetime.now().isoformat(),
        }
        self._save(m)
        return m["profiles"][resident_id]


class _KnowledgeBaseCoreMemory(_CoreMemory):
    def __init__(self, path: str):
        # Use local file as cache/fallback
        self._fallback = _FileCoreMemory(path)
        # Attempt to import/write via strands tools if available
        try:
            from strands_tools import retrieve  # noqa: F401
            self._kb_available = True
        except Exception:
            self._kb_available = False

    def get_snooze(self, resident_id: str) -> Optional[Dict]:
        # Try KB first, fallback to file
        if self._kb_available:
            try:
                # Query KB for snooze data
                query = f"resident_id:{resident_id} AND type:snooze"
                # This would use actual KB query when available
                pass
            except Exception:
                pass
        return self._fallback.get_snooze(resident_id)

    def set_snooze(self, resident_id: str, start_date: str, end_date: str, reason: Optional[str]) -> Dict:
        # Store in both KB and file
        result = self._fallback.set_snooze(resident_id, start_date, end_date, reason)
        
        if self._kb_available:
            try:
                # Store in KB - this would use actual KB upsert when available
                # For now, just log that we would store it
                logger.info(f"Would store snooze in KB: {resident_id} from {start_date} to {end_date}")
            except Exception as e:
                logger.warning(f"Failed to store snooze in KB: {e}")
        
        return result

    def clear_snooze(self, resident_id: str) -> bool:
        # Clear from both KB and file
        result = self._fallback.clear_snooze(resident_id)
        
        if self._kb_available:
            try:
                # Clear from KB - this would use actual KB delete when available
                logger.info(f"Would clear snooze from KB: {resident_id}")
            except Exception as e:
                logger.warning(f"Failed to clear snooze from KB: {e}")
        
        return result

    def get_profile(self, resident_id: str) -> Optional[Dict]:
        # Try KB first, fallback to file
        if self._kb_available:
            try:
                # Query KB for profile data
                query = f"resident_id:{resident_id} AND type:profile"
                # This would use actual KB query when available
                pass
            except Exception:
                pass
        return self._fallback.get_profile(resident_id)

    def set_profile(self, resident_id: str, dwelling_type: str, region: str, description: str) -> Dict:
        # Store in both KB and file
        result = self._fallback.set_profile(resident_id, dwelling_type, region, description)
        
        if self._kb_available:
            try:
                # Store in KB - this would use actual KB upsert when available
                logger.info(f"Would store profile in KB: {resident_id} - {dwelling_type} in {description}, {region}")
            except Exception as e:
                logger.warning(f"Failed to store profile in KB: {e}")
        
        return result
    
    def _check_and_create_alerts(self, 
                                resident_id: str,
                                dwelling_type: str,
                                region: str,
                                description: str,
                                tracker_result: Dict) -> List[Dict]:
        """
        Check analysis results and create alerts if needed
        
        Args:
            resident_id: Resident identifier
            dwelling_type: Type of dwelling
            region: Region
            description: Specific location
            tracker_result: Analysis results from tracker
            
        Returns:
            List of created alerts
        """
        alerts_created = []
        analysis = tracker_result.get("analysis", {})
        
        if not analysis:
            return alerts_created
        
        status = analysis.get("status", "normal")
        severity = analysis.get("severity", "low")
        reason = analysis.get("reason", "")
        recommendations = analysis.get("recommendations", [])
        
        # Create alert if status indicates concern
        if status in ["alert", "warning"]:
            alert = self.alert_system.create_alert(
                resident_id=resident_id,
                dwelling_type=dwelling_type,
                region=region,
                description=description,
                severity=severity,
                message=reason,
                recommendations=recommendations,
                analysis_data=analysis
            )
            alerts_created.append({
                "alert_id": alert.id,
                "severity": severity,
                "message": reason
            })
        
        return alerts_created
    
    def process_batch_readings(self, readings: List[Dict]) -> Dict:
        """
        Process multiple usage readings in batch
        
        Args:
            readings: List of reading dictionaries
            
        Returns:
            Batch processing results
        """
        results = []
        total_alerts = 0
        
        for reading in readings:
            result = self.add_usage_reading(**reading)
            results.append(result)
            total_alerts += result["alert_count"]
        
        return {
            "processed_count": len(results),
            "total_alerts": total_alerts,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_monitoring_dashboard(self) -> Dict:
        """
        Get comprehensive monitoring dashboard data
        
        Returns:
            Dashboard data
        """
        # Get usage summary
        usage_summary = self.tracker.get_usage_summary()
        
        # Get alert summary
        alert_summary = self.alert_system.get_alert_summary()
        
        # Get recent alerts
        recent_alerts = self.alert_system.get_pending_alerts()[:5]
        
        # Get critical alerts
        critical_alerts = self.alert_system.get_critical_alerts()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_status": "active" if self.monitoring_active else "inactive",
            "usage_summary": usage_summary,
            "alert_summary": alert_summary,
            "recent_alerts": [
                {
                    "id": alert.id,
                    "resident_id": alert.resident_id,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                } for alert in recent_alerts
            ],
            "critical_alerts": [
                {
                    "id": alert.id,
                    "resident_id": alert.resident_id,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "escalation_level": alert.escalation_level
                } for alert in critical_alerts
            ]
        }
    
    def start_monitoring(self, check_interval: Optional[int] = None):
        """
        Start continuous monitoring
        
        Args:
            check_interval: Check interval in minutes (uses config default if not provided)
        """
        interval = check_interval or self.config["monitoring"]["check_interval_minutes"]
        
        self.monitoring_active = True
        logger.info(f"Starting elderly home monitoring (check interval: {interval} minutes)")
        
        # Schedule regular checks
        schedule.every(interval).minutes.do(self._monitoring_check)
        
        try:
            while self.monitoring_active:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        schedule.clear()
        logger.info("Elderly home monitoring stopped")
    
    def _monitoring_check(self):
        """Perform regular monitoring check"""
        logger.info("Performing monitoring check...")
        
        # Check for escalations
        self.alert_system.check_escalations()
        
        # Get dashboard data
        dashboard = self.get_monitoring_dashboard()
        
        # Log critical alerts
        if dashboard["alert_summary"]["critical_alerts"] > 0:
            logger.critical(f"CRITICAL ALERTS DETECTED: {dashboard['alert_summary']['critical_alerts']}")
        
        logger.info(f"Monitoring check complete - {dashboard['alert_summary']['pending_alerts']} pending alerts")
    
    def export_data(self, output_dir: str = "exports") -> Dict:
        """
        Export all monitoring data
        
        Args:
            output_dir: Output directory for exports
            
        Returns:
            Export results
        """
        Path(output_dir).mkdir(exist_ok=True)
        
        # Export daily records
        daily_file = self.tracker.export_daily_records(
            f"{output_dir}/daily_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Export alerts
        alerts_file = self.alert_system.export_alerts(
            f"{output_dir}/alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Export dashboard data
        dashboard = self.get_monitoring_dashboard()
        dashboard_file = f"{output_dir}/dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        return {
            "daily_records_file": daily_file,
            "alerts_file": alerts_file,
            "dashboard_file": dashboard_file,
            "export_timestamp": datetime.now().isoformat()
        }
