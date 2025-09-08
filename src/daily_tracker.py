"""
Daily Usage Tracker for Elderly Home Monitoring
Tracks and processes daily electricity and gas usage data
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailyUsageTracker:
    """
    Tracks daily usage patterns and detects anomalies for elderly residents
    """
    
    def __init__(self, historical_data_path: str = "data/2324_combined.csv"):
        """
        Initialize the tracker with historical data
        
        Args:
            historical_data_path: Path to historical usage data CSV
        """
        self.historical_data_path = historical_data_path
        self.daily_records = []
        self.load_historical_data()
        
    def load_historical_data(self):
        """Load historical usage data"""
        try:
            self.historical_df = pd.read_csv(self.historical_data_path)
            logger.info(f"Loaded historical data: {len(self.historical_df)} records")
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            self.historical_df = pd.DataFrame()
    
    def add_daily_usage(self, 
                       dwelling_type: str,
                       region: str,
                       description: str,
                       electricity_kwh: float,
                       gas_kwh: float,
                       date: Optional[str] = None,
                       resident_id: Optional[str] = None,
                       notes: Optional[str] = None) -> Dict:
        """
        Add daily usage record and perform anomaly detection
        
        Args:
            dwelling_type: Type of dwelling (e.g., "3-room", "1-room / 2-room")
            region: Region (e.g., "North East Region")
            description: Specific location (e.g., "Ang Mo Kio")
            electricity_kwh: Daily electricity usage in kWh
            gas_kwh: Daily gas usage in kWh
            date: Date in YYYY-MM-DD format (defaults to today)
            resident_id: Optional resident identifier
            notes: Optional notes about the reading
            
        Returns:
            Dict containing the record and analysis results
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        # Create usage record
        usage_record = {
            "date": date,
            "dwelling_type": dwelling_type,
            "region": region,
            "description": description,
            "electricity_per_month": electricity_kwh,
            "gas_per_month": gas_kwh,
            "resident_id": resident_id,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to daily records
        self.daily_records.append(usage_record)
        
        # Perform anomaly detection
        analysis_result = self.analyze_usage(usage_record)
        
        # Combine record with analysis
        result = {
            "record": usage_record,
            "analysis": analysis_result,
            "alert_level": self._determine_alert_level(analysis_result)
        }
        
        logger.info(f"Added daily usage for {dwelling_type} in {description}: {analysis_result.get('status', 'unknown')}")
        return result
    
    def analyze_usage(self, usage_record: Dict) -> Dict:
        """
        Analyze usage against historical patterns
        
        Args:
            usage_record: Daily usage record
            
        Returns:
            Analysis results
        """
        try:
            # Import here to avoid circular imports
            from anomaly_tool import detect_anomaly
            
            # Convert to JSON string for anomaly detection
            usage_json = json.dumps(usage_record)
            analysis_json = detect_anomaly(usage_json)
            
            return json.loads(analysis_json)
            
        except Exception as e:
            logger.error(f"Failed to analyze usage: {e}")
            return {
                "status": "error",
                "severity": "high",
                "reason": f"Analysis failed: {str(e)}",
                "recommendations": ["Check data format and retry"]
            }
    
    def _determine_alert_level(self, analysis: Dict) -> str:
        """
        Determine overall alert level based on analysis
        
        Args:
            analysis: Analysis results from detect_anomaly
            
        Returns:
            Alert level: "critical", "high", "medium", "low", "normal"
        """
        severity = analysis.get("severity", "low")
        status = analysis.get("status", "normal")
        
        if status == "alert" and severity == "critical":
            return "critical"
        elif status == "alert" and severity == "high":
            return "high"
        elif status == "warning" or severity == "medium":
            return "medium"
        elif status == "normal":
            return "normal"
        else:
            return "low"
    
    def get_recent_usage(self, days: int = 7) -> List[Dict]:
        """
        Get recent usage records
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent usage records
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_records = []
        
        for record in self.daily_records:
            record_date = datetime.fromisoformat(record["timestamp"])
            if record_date >= cutoff_date:
                recent_records.append(record)
        
        return sorted(recent_records, key=lambda x: x["timestamp"], reverse=True)
    
    def get_usage_summary(self, days: int = 7) -> Dict:
        """
        Get summary of recent usage patterns
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Usage summary statistics
        """
        recent_records = self.get_recent_usage(days)
        
        if not recent_records:
            return {
                "total_records": 0,
                "alert_count": 0,
                "critical_alerts": 0,
                "average_electricity": 0,
                "average_gas": 0,
                "trend": "no_data"
            }
        
        # Calculate statistics
        electricity_values = [r["electricity_per_month"] for r in recent_records]
        gas_values = [r["gas_per_month"] for r in recent_records]
        
        # Count alerts (this would need to be stored with each record)
        alert_count = sum(1 for r in recent_records if r.get("alert_level", "normal") != "normal")
        critical_count = sum(1 for r in recent_records if r.get("alert_level") == "critical")
        
        # Calculate trend (simplified)
        if len(electricity_values) >= 2:
            elec_trend = "increasing" if electricity_values[0] > electricity_values[-1] else "decreasing"
        else:
            elec_trend = "stable"
        
        return {
            "total_records": len(recent_records),
            "alert_count": alert_count,
            "critical_alerts": critical_count,
            "average_electricity": sum(electricity_values) / len(electricity_values),
            "average_gas": sum(gas_values) / len(gas_values),
            "trend": elec_trend,
            "date_range": {
                "from": recent_records[-1]["date"] if recent_records else None,
                "to": recent_records[0]["date"] if recent_records else None
            }
        }
    
    def export_daily_records(self, filename: Optional[str] = None) -> str:
        """
        Export daily records to CSV
        
        Args:
            filename: Output filename (defaults to timestamped name)
            
        Returns:
            Path to exported file
        """
        if not self.daily_records:
            logger.warning("No daily records to export")
            return None
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"daily_usage_{timestamp}.csv"
        
        df = pd.DataFrame(self.daily_records)
        df.to_csv(filename, index=False)
        logger.info(f"Exported {len(self.daily_records)} records to {filename}")
        return filename
    
    def get_historical_comparison(self, 
                                dwelling_type: str,
                                region: str,
                                description: str,
                                current_electricity: float,
                                current_gas: float) -> Dict:
        """
        Get detailed comparison with historical data
        
        Args:
            dwelling_type: Type of dwelling
            region: Region
            description: Specific location
            current_electricity: Current electricity usage
            current_gas: Current gas usage
            
        Returns:
            Detailed comparison with historical data
        """
        # Filter historical data
        mask = (self.historical_df["Dwelling Type"] == dwelling_type) & \
               (self.historical_df["Region"] == region) & \
               (self.historical_df["Description"] == description)
        
        filtered_df = self.historical_df[mask]
        
        if filtered_df.empty:
            return {
                "status": "no_data",
                "message": "No historical data found for this location"
            }
        
        # Calculate statistics
        elec_data = filtered_df["electricity_per_month"].dropna()
        gas_data = filtered_df["gas_per_month"].dropna()
        
        return {
            "status": "success",
            "data_points": len(filtered_df),
            "electricity": {
                "current": current_electricity,
                "historical_mean": elec_data.mean(),
                "historical_std": elec_data.std(),
                "historical_median": elec_data.median(),
                "percentile_25": elec_data.quantile(0.25),
                "percentile_75": elec_data.quantile(0.75),
                "min": elec_data.min(),
                "max": elec_data.max()
            },
            "gas": {
                "current": current_gas,
                "historical_mean": gas_data.mean(),
                "historical_std": gas_data.std(),
                "historical_median": gas_data.median(),
                "percentile_25": gas_data.quantile(0.25),
                "percentile_75": gas_data.quantile(0.75),
                "min": gas_data.min(),
                "max": gas_data.max()
            }
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize tracker
    tracker = DailyUsageTracker()
    
    # Add some test data
    test_usage = tracker.add_daily_usage(
        dwelling_type="3-room",
        region="North East Region", 
        description="Ang Mo Kio",
        electricity_kwh=15.0,
        gas_kwh=5.0,
        resident_id="RES001",
        notes="Morning reading"
    )
    
    print("Test Usage Analysis:")
    print(json.dumps(test_usage, indent=2))
    
    # Get summary
    summary = tracker.get_usage_summary()
    print("\nUsage Summary:")
    print(json.dumps(summary, indent=2))
