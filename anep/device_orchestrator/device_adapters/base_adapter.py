"""
NOVA ViA Base Device Adapter
Abstract base class for all biohacking device integrations
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import uuid


class DeviceStatus(Enum):
    """Device status enumeration"""
    OFFLINE = "offline"
    ONLINE = "online"
    CALIBRATING = "calibrating"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class DeviceCapability(Enum):
    """Device capability types"""
    PRESSURE_CONTROL = "pressure_control"
    LIGHT_THERAPY = "light_therapy"
    MAGNETIC_FIELD = "magnetic_field"
    FREQUENCY_GENERATION = "frequency_generation"
    TEMPERATURE_CONTROL = "temperature_control"
    REAL_TIME_MONITORING = "real_time_monitoring"
    SAFETY_SHUTOFF = "safety_shutoff"
    AUTOMATED_CALIBRATION = "automated_calibration"


@dataclass
class DeviceParameter:
    """Device parameter specification"""
    name: str
    type: str  # int, float, bool, string, enum
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Any = None
    unit: Optional[str] = None
    description: str = ""
    enum_values: Optional[List[str]] = None


@dataclass
class SafetyLimit:
    """Safety limit specification"""
    parameter: str
    min_safe: Optional[float] = None
    max_safe: Optional[float] = None
    emergency_threshold: Optional[float] = None
    warning_threshold: Optional[float] = None


@dataclass
class DeviceMetrics:
    """Real-time device metrics"""
    device_id: str
    timestamp: float
    status: DeviceStatus
    parameters: Dict[str, Any]
    safety_status: Dict[str, Any]
    health_indicators: Dict[str, float]
    power_consumption: Optional[float] = None
    temperature: Optional[float] = None
    operational_hours: Optional[float] = None


class BaseDeviceAdapter(ABC):
    """
    Abstract base class for all biohacking device adapters
    
    Provides common functionality for device communication, safety monitoring,
    and integration with the orchestration system.
    """
    
    def __init__(self, device_id: str, connection_config: Dict[str, Any]):
        self.device_id = device_id
        self.connection_config = connection_config
        self.logger = logging.getLogger(f"{__name__}.{device_id}")
        
        # Device properties
        self.device_type: str = "unknown"
        self.manufacturer: str = "unknown"
        self.model: str = "unknown"
        self.firmware_version: str = "unknown"
        
        # State management
        self.status = DeviceStatus.OFFLINE
        self.last_seen = 0.0
        self.is_connected = False
        self.current_parameters: Dict[str, Any] = {}
        
        # Safety and monitoring
        self.safety_limits: List[SafetyLimit] = []
        self.safety_enabled = True
        self.emergency_stop_triggered = False
        
        # Capabilities and parameters
        self.capabilities: List[DeviceCapability] = []
        self.supported_parameters: List[DeviceParameter] = []
        
        # Metrics tracking
        self.metrics_history: List[DeviceMetrics] = []
        self.max_metrics_history = 1000
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize device connection and configuration"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the device"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the device"""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a device command with parameters"""
        pass
    
    @abstractmethod
    async def get_status(self) -> DeviceStatus:
        """Get current device status"""
        pass
    
    @abstractmethod
    async def emergency_stop(self) -> bool:
        """Execute emergency stop protocol"""
        pass
    
    def get_capabilities(self) -> List[str]:
        """Get list of device capabilities"""
        return [cap.value for cap in self.capabilities]
    
    def get_supported_parameters(self) -> List[Dict[str, Any]]:
        """Get list of supported parameters"""
        return [
            {
                "name": param.name,
                "type": param.type,
                "min_value": param.min_value,
                "max_value": param.max_value,
                "default_value": param.default_value,
                "unit": param.unit,
                "description": param.description,
                "enum_values": param.enum_values
            }
            for param in self.supported_parameters
        ]
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against device specifications"""
        validated = {}
        errors = []
        
        for param_name, value in parameters.items():
            param_spec = next(
                (p for p in self.supported_parameters if p.name == param_name),
                None
            )
            
            if not param_spec:
                errors.append(f"Unknown parameter: {param_name}")
                continue
            
            # Type validation
            try:
                if param_spec.type == "int":
                    value = int(value)
                elif param_spec.type == "float":
                    value = float(value)
                elif param_spec.type == "bool":
                    value = bool(value)
                elif param_spec.type == "string":
                    value = str(value)
                elif param_spec.type == "enum":
                    if value not in param_spec.enum_values:
                        errors.append(f"Invalid enum value for {param_name}: {value}")
                        continue
            except (ValueError, TypeError):
                errors.append(f"Invalid type for {param_name}: expected {param_spec.type}")
                continue
            
            # Range validation
            if param_spec.min_value is not None and value < param_spec.min_value:
                errors.append(f"Value for {param_name} below minimum: {value} < {param_spec.min_value}")
                continue
            
            if param_spec.max_value is not None and value > param_spec.max_value:
                errors.append(f"Value for {param_name} above maximum: {value} > {param_spec.max_value}")
                continue
            
            validated[param_name] = value
        
        if errors:
            raise ValueError(f"Parameter validation failed: {'; '.join(errors)}")
        
        return validated
    
    async def check_safety_limits(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Check parameters against safety limits"""
        safety_status = {
            "safe": True,
            "warnings": [],
            "violations": [],
            "emergency": False
        }
        
        for limit in self.safety_limits:
            if limit.parameter not in parameters:
                continue
            
            value = parameters[limit.parameter]
            
            # Check emergency thresholds
            if limit.emergency_threshold is not None:
                if (limit.min_safe is not None and value < limit.emergency_threshold) or \
                   (limit.max_safe is not None and value > limit.emergency_threshold):
                    safety_status["emergency"] = True
                    safety_status["safe"] = False
                    safety_status["violations"].append(
                        f"Emergency threshold exceeded for {limit.parameter}: {value}"
                    )
            
            # Check safety limits
            if limit.min_safe is not None and value < limit.min_safe:
                safety_status["safe"] = False
                safety_status["violations"].append(
                    f"Safety limit violated for {limit.parameter}: {value} < {limit.min_safe}"
                )
            
            if limit.max_safe is not None and value > limit.max_safe:
                safety_status["safe"] = False
                safety_status["violations"].append(
                    f"Safety limit violated for {limit.parameter}: {value} > {limit.max_safe}"
                )
            
            # Check warning thresholds
            if limit.warning_threshold is not None:
                if abs(value - limit.warning_threshold) < 0.1:  # Close to warning
                    safety_status["warnings"].append(
                        f"Approaching warning threshold for {limit.parameter}: {value}"
                    )
        
        return safety_status
    
    async def update_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Update device parameters with validation and safety checks"""
        try:
            # Validate parameters
            validated_params = await self.validate_parameters(parameters)
            
            # Check safety limits
            if self.safety_enabled:
                safety_status = await self.check_safety_limits(validated_params)
                
                if safety_status["emergency"]:
                    await self.emergency_stop()
                    raise ValueError(f"Emergency stop triggered: {safety_status['violations']}")
                
                if not safety_status["safe"]:
                    raise ValueError(f"Safety limits violated: {safety_status['violations']}")
                
                if safety_status["warnings"]:
                    self.logger.warning(f"Safety warnings: {safety_status['warnings']}")
            
            # Update current parameters
            self.current_parameters.update(validated_params)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Parameter update failed: {e}")
            raise
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get device health status"""
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "connected": self.is_connected,
            "last_seen": self.last_seen,
            "uptime": time.time() - self.last_seen if self.last_seen > 0 else 0,
            "parameters": self.current_parameters.copy(),
            "safety_enabled": self.safety_enabled,
            "emergency_stop": self.emergency_stop_triggered,
            "capabilities": self.get_capabilities(),
            "firmware_version": self.firmware_version
        }
    
    async def get_metrics(self) -> DeviceMetrics:
        """Get current device metrics"""
        # This should be implemented by subclasses to provide device-specific metrics
        return DeviceMetrics(
            device_id=self.device_id,
            timestamp=time.time(),
            status=self.status,
            parameters=self.current_parameters.copy(),
            safety_status=await self.check_safety_limits(self.current_parameters) if self.current_parameters else {},
            health_indicators={}
        )
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        if self.heartbeat_task is None or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        self.logger.info(f"Started monitoring for device {self.device_id}")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"Stopped monitoring for device {self.device_id}")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Collect metrics
                metrics = await self.get_metrics()
                
                # Store metrics
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_metrics_history:
                    self.metrics_history = self.metrics_history[-self.max_metrics_history//2:]
                
                # Check for issues
                await self._check_device_health(metrics)
                
                # Wait before next check
                await asyncio.sleep(1.0)  # Monitor every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def _heartbeat_loop(self):
        """Background heartbeat loop"""
        while True:
            try:
                # Send heartbeat to device
                if self.is_connected:
                    self.last_seen = time.time()
                
                await asyncio.sleep(5.0)  # Heartbeat every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"Heartbeat error: {e}")
                await asyncio.sleep(10.0)
    
    async def _check_device_health(self, metrics: DeviceMetrics):
        """Check device health and trigger actions if needed"""
        # Check for emergency conditions
        if metrics.safety_status.get("emergency", False):
            self.logger.critical(f"Emergency condition detected: {metrics.safety_status}")
            await self.emergency_stop()
        
        # Check for warnings
        if metrics.safety_status.get("warnings"):
            self.logger.warning(f"Safety warnings: {metrics.safety_status['warnings']}")
        
        # Update device status based on health
        if not self.is_connected:
            self.status = DeviceStatus.OFFLINE
        elif self.emergency_stop_triggered:
            self.status = DeviceStatus.EMERGENCY_STOP
        elif metrics.safety_status.get("violations"):
            self.status = DeviceStatus.ERROR
        else:
            # Status should be updated by device-specific logic
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device info to dictionary"""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "status": self.status.value,
            "capabilities": self.get_capabilities(),
            "parameters": self.get_supported_parameters(),
            "safety_limits": [
                {
                    "parameter": limit.parameter,
                    "min_safe": limit.min_safe,
                    "max_safe": limit.max_safe,
                    "emergency_threshold": limit.emergency_threshold,
                    "warning_threshold": limit.warning_threshold
                }
                for limit in self.safety_limits
            ],
            "current_parameters": self.current_parameters,
            "is_connected": self.is_connected,
            "last_seen": self.last_seen
        }
    
    def __str__(self) -> str:
        return f"{self.device_type}[{self.device_id}]({self.status.value})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.device_id} {self.status.value}>"
