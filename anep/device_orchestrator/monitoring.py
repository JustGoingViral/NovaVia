"""
NOVA ViA Device Monitoring System
Real-time device health monitoring and performance analytics
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import statistics
import json

from .device_adapters.base_adapter import BaseDeviceAdapter, DeviceMetrics


@dataclass
class SystemAlert:
    """System alert representation"""
    alert_id: str
    device_id: str
    alert_type: str
    severity: str  # low, medium, high, critical
    message: str
    timestamp: float
    acknowledged: bool = False
    resolved: bool = False


class DeviceMonitor:
    """
    Comprehensive device monitoring system for NOVA ViA biohacking devices
    
    Features:
    - Real-time health monitoring
    - Performance analytics
    - Alert management
    - Trend analysis
    - Predictive maintenance
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Monitored devices
        self.devices: Dict[str, BaseDeviceAdapter] = {}
        
        # Metrics storage
        self.device_metrics: Dict[str, List[DeviceMetrics]] = {}
        self.max_metrics_per_device = 10000
        
        # System health tracking
        self.system_health_score = 100.0
        self.last_health_update = time.time()
        
        # Alert management
        self.active_alerts: List[SystemAlert] = []
        self.alert_history: List[SystemAlert] = []
        self.max_alert_history = 1000
        
        # Performance tracking
        self.performance_metrics = {
            "total_devices": 0,
            "online_devices": 0,
            "active_treatments": 0,
            "total_alerts": 0,
            "critical_alerts": 0,
            "average_response_time_ms": 0.0,
            "system_uptime_hours": 0.0
        }
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_interval = 1.0  # seconds
        
        # Alert thresholds
        self.alert_thresholds = {
            "device_offline_timeout": 30.0,  # seconds
            "high_temperature_threshold": 70.0,  # celsius
            "low_power_efficiency_threshold": 0.7,  # 70%
            "high_response_time_threshold": 1000.0,  # ms
            "system_health_critical": 50.0,  # %
            "system_health_warning": 80.0   # %
        }
    
    async def initialize(self):
        """Initialize the device monitoring system"""
        self.logger.info("Initializing Device Monitoring System...")
        
        # Start monitoring
        await self.start_monitoring()
        
        self.logger.info("Device Monitoring System initialized successfully")
    
    async def add_device(self, device: BaseDeviceAdapter):
        """Add a device to monitoring"""
        device_id = device.device_id
        
        self.devices[device_id] = device
        self.device_metrics[device_id] = []
        
        self.performance_metrics["total_devices"] = len(self.devices)
        
        self.logger.info(f"Added device to monitoring: {device_id}")
    
    async def remove_device(self, device_id: str):
        """Remove a device from monitoring"""
        if device_id in self.devices:
            del self.devices[device_id]
            
        if device_id in self.device_metrics:
            del self.device_metrics[device_id]
        
        # Remove device-specific alerts
        self.active_alerts = [alert for alert in self.active_alerts if alert.device_id != device_id]
        
        self.performance_metrics["total_devices"] = len(self.devices)
        
        self.logger.info(f"Removed device from monitoring: {device_id}")
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Device monitoring started")
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_monitoring = False
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Device monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect metrics from all devices
                await self._collect_device_metrics()
                
                # Analyze system health
                await self._analyze_system_health()
                
                # Check for alerts
                await self._check_alerts()
                
                # Update performance metrics
                await self._update_performance_metrics()
                
                # Wait for next cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def _collect_device_metrics(self):
        """Collect metrics from all monitored devices"""
        for device_id, device in self.devices.items():
            try:
                # Get device metrics
                metrics = await device.get_metrics()
                
                # Store metrics
                device_metrics_list = self.device_metrics.setdefault(device_id, [])
                device_metrics_list.append(metrics)
                
                # Limit metrics history
                if len(device_metrics_list) > self.max_metrics_per_device:
                    device_metrics_list[:] = device_metrics_list[-self.max_metrics_per_device//2:]
                
            except Exception as e:
                self.logger.warning(f"Failed to collect metrics from {device_id}: {e}")
                
                # Create offline alert if device is unresponsive
                await self._create_alert(
                    device_id=device_id,
                    alert_type="device_unresponsive",
                    severity="high",
                    message=f"Device {device_id} is not responding to metrics requests"
                )
    
    async def _analyze_system_health(self):
        """Analyze overall system health"""
        if not self.devices:
            self.system_health_score = 100.0
            return
        
        health_factors = []
        
        for device_id, device in self.devices.items():
            device_health = await self._calculate_device_health(device_id)
            health_factors.append(device_health)
        
        # Calculate weighted average
        if health_factors:
            self.system_health_score = statistics.mean(health_factors)
        else:
            self.system_health_score = 0.0
        
        self.last_health_update = time.time()
        
        # Check for system-level alerts
        if self.system_health_score < self.alert_thresholds["system_health_critical"]:
            await self._create_alert(
                device_id="system",
                alert_type="system_health_critical",
                severity="critical",
                message=f"System health critically low: {self.system_health_score:.1f}%"
            )
        elif self.system_health_score < self.alert_thresholds["system_health_warning"]:
            await self._create_alert(
                device_id="system",
                alert_type="system_health_warning",
                severity="medium",
                message=f"System health warning: {self.system_health_score:.1f}%"
            )
    
    async def _calculate_device_health(self, device_id: str) -> float:
        """Calculate health score for a specific device"""
        device = self.devices.get(device_id)
        if not device:
            return 0.0
        
        metrics_list = self.device_metrics.get(device_id, [])
        if not metrics_list:
            return 50.0  # No data available
        
        latest_metrics = metrics_list[-1]
        
        health_score = 100.0
        
        # Connection health
        if not device.is_connected:
            health_score -= 30.0
        
        # Emergency stop status
        if device.emergency_stop_triggered:
            health_score -= 40.0
        
        # Temperature health (if available)
        if latest_metrics.temperature:
            if latest_metrics.temperature > self.alert_thresholds["high_temperature_threshold"]:
                health_score -= 15.0
        
        # Power efficiency (if available)
        power_efficiency = latest_metrics.health_indicators.get("power_efficiency", 1.0)
        if power_efficiency < self.alert_thresholds["low_power_efficiency_threshold"]:
            health_score -= 10.0
        
        # Safety status
        if latest_metrics.safety_status.get("emergency", False):
            health_score -= 50.0
        elif latest_metrics.safety_status.get("violations"):
            health_score -= 20.0
        elif latest_metrics.safety_status.get("warnings"):
            health_score -= 5.0
        
        return max(0.0, min(100.0, health_score))
    
    async def _check_alerts(self):
        """Check for new alerts across all devices"""
        for device_id, device in self.devices.items():
            await self._check_device_alerts(device_id, device)
    
    async def _check_device_alerts(self, device_id: str, device: BaseDeviceAdapter):
        """Check for alerts on a specific device"""
        # Check if device is offline
        time_since_last_seen = time.time() - device.last_seen
        if time_since_last_seen > self.alert_thresholds["device_offline_timeout"]:
            await self._create_alert(
                device_id=device_id,
                alert_type="device_offline",
                severity="high",
                message=f"Device {device_id} has been offline for {time_since_last_seen:.1f} seconds"
            )
        
        # Check device-specific metrics
        metrics_list = self.device_metrics.get(device_id, [])
        if metrics_list:
            latest_metrics = metrics_list[-1]
            
            # Temperature alerts
            if latest_metrics.temperature and latest_metrics.temperature > self.alert_thresholds["high_temperature_threshold"]:
                await self._create_alert(
                    device_id=device_id,
                    alert_type="high_temperature",
                    severity="medium",
                    message=f"Device {device_id} temperature is {latest_metrics.temperature:.1f}°C"
                )
            
            # Safety alerts
            if latest_metrics.safety_status.get("emergency", False):
                await self._create_alert(
                    device_id=device_id,
                    alert_type="safety_emergency",
                    severity="critical",
                    message=f"Emergency safety condition on device {device_id}"
                )
            
            # Performance alerts
            health_indicators = latest_metrics.health_indicators
            for indicator, value in health_indicators.items():
                if isinstance(value, (int, float)) and value < 0.5:  # Below 50% performance
                    await self._create_alert(
                        device_id=device_id,
                        alert_type="performance_degradation",
                        severity="medium",
                        message=f"Device {device_id} {indicator} is {value:.2f} (below normal)"
                    )
    
    async def _create_alert(self, device_id: str, alert_type: str, severity: str, message: str):
        """Create a new system alert"""
        # Check if similar alert already exists
        existing_alert = next(
            (alert for alert in self.active_alerts 
             if alert.device_id == device_id and alert.alert_type == alert_type and not alert.resolved),
            None
        )
        
        if existing_alert:
            return  # Don't create duplicate alerts
        
        alert = SystemAlert(
            alert_id=f"{device_id}_{alert_type}_{int(time.time())}",
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=time.time()
        )
        
        self.active_alerts.append(alert)
        
        # Log based on severity
        if severity == "critical":
            self.logger.critical(f"CRITICAL ALERT: {message}")
        elif severity == "high":
            self.logger.error(f"HIGH ALERT: {message}")
        elif severity == "medium":
            self.logger.warning(f"MEDIUM ALERT: {message}")
        else:
            self.logger.info(f"LOW ALERT: {message}")
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        alert = next((a for a in self.active_alerts if a.alert_id == alert_id), None)
        if alert:
            alert.acknowledged = True
            self.logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        alert = next((a for a in self.active_alerts if a.alert_id == alert_id), None)
        if alert:
            alert.resolved = True
            alert.acknowledged = True
            
            # Move to history
            self.alert_history.append(alert)
            self.active_alerts.remove(alert)
            
            # Limit history size
            if len(self.alert_history) > self.max_alert_history:
                self.alert_history = self.alert_history[-self.max_alert_history//2:]
            
            self.logger.info(f"Alert resolved: {alert_id}")
            return True
        return False
    
    async def _update_performance_metrics(self):
        """Update system performance metrics"""
        # Count online devices
        online_count = sum(1 for device in self.devices.values() if device.is_connected)
        self.performance_metrics["online_devices"] = online_count
        
        # Count active treatments
        active_treatments = sum(
            1 for device in self.devices.values() 
            if hasattr(device, 'treatment_active') and device.treatment_active
        )
        self.performance_metrics["active_treatments"] = active_treatments
        
        # Count alerts
        self.performance_metrics["total_alerts"] = len(self.active_alerts)
        self.performance_metrics["critical_alerts"] = sum(
            1 for alert in self.active_alerts if alert.severity == "critical"
        )
        
        # Calculate average response time (simulated for demo)
        self.performance_metrics["average_response_time_ms"] = 45.0 + (len(self.active_alerts) * 5)
        
        # System uptime (hours since monitoring started)
        self.performance_metrics["system_uptime_hours"] = (
            time.time() - self.last_health_update
        ) / 3600.0 if hasattr(self, 'start_time') else 0.0
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        return {
            "system_health_score": self.system_health_score,
            "performance_metrics": self.performance_metrics.copy(),
            "active_alerts_count": len(self.active_alerts),
            "critical_alerts_count": sum(1 for a in self.active_alerts if a.severity == "critical"),
            "monitoring_status": "active" if self.is_monitoring else "inactive",
            "last_update": self.last_health_update,
            "timestamp": time.time()
        }
    
    async def get_device_health(self, device_id: str) -> Dict[str, Any]:
        """Get health metrics for a specific device"""
        if device_id not in self.devices:
            return {"error": "Device not found"}
        
        device_health_score = await self._calculate_device_health(device_id)
        metrics_list = self.device_metrics.get(device_id, [])
        latest_metrics = metrics_list[-1] if metrics_list else None
        
        device_alerts = [
            alert for alert in self.active_alerts 
            if alert.device_id == device_id and not alert.resolved
        ]
        
        return {
            "device_id": device_id,
            "health_score": device_health_score,
            "metrics_count": len(metrics_list),
            "latest_metrics": latest_metrics.to_dict() if latest_metrics else None,
            "active_alerts": len(device_alerts),
            "critical_alerts": sum(1 for a in device_alerts if a.severity == "critical"),
            "last_seen": self.devices[device_id].last_seen,
            "status": self.devices[device_id].status.value
        }
    
    async def get_alerts(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Get system alerts"""
        alerts = self.active_alerts.copy()
        
        if include_resolved:
            alerts.extend(self.alert_history)
        
        return [
            {
                "alert_id": alert.alert_id,
                "device_id": alert.device_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved
            }
            for alert in sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        ]
    
    async def get_device_trends(self, device_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get device performance trends over time"""
        if device_id not in self.device_metrics:
            return {"error": "No metrics available for device"}
        
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [
            m for m in self.device_metrics[device_id] 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No recent metrics available"}
        
        # Calculate trends
        health_scores = []
        power_consumption = []
        temperatures = []
        
        for metrics in recent_metrics:
            health_score = await self._calculate_device_health(device_id)
            health_scores.append(health_score)
            
            if metrics.power_consumption:
                power_consumption.append(metrics.power_consumption)
            
            if metrics.temperature:
                temperatures.append(metrics.temperature)
        
        trends = {
            "device_id": device_id,
            "time_range_hours": hours,
            "metrics_count": len(recent_metrics),
            "health_trend": {
                "average": statistics.mean(health_scores) if health_scores else 0,
                "min": min(health_scores) if health_scores else 0,
                "max": max(health_scores) if health_scores else 0,
                "current": health_scores[-1] if health_scores else 0
            }
        }
        
        if power_consumption:
            trends["power_trend"] = {
                "average": statistics.mean(power_consumption),
                "min": min(power_consumption),
                "max": max(power_consumption),
                "current": power_consumption[-1]
            }
        
        if temperatures:
            trends["temperature_trend"] = {
                "average": statistics.mean(temperatures),
                "min": min(temperatures),
                "max": max(temperatures),
                "current": temperatures[-1]
            }
        
        return trends
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert monitoring state to dictionary"""
        return {
            "system_health_score": self.system_health_score,
            "total_devices": len(self.devices),
            "online_devices": sum(1 for d in self.devices.values() if d.is_connected),
            "active_alerts": len(self.active_alerts),
            "critical_alerts": sum(1 for a in self.active_alerts if a.severity == "critical"),
            "monitoring_active": self.is_monitoring,
            "last_update": self.last_health_update,
            "performance_metrics": self.performance_metrics
        }
