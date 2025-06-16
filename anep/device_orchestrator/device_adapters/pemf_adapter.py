"""NOVA ViA PEMF Device Adapter - Pulsed Electromagnetic Field Therapy"""

import asyncio
import time
from typing import Dict, Any
from .base_adapter import BaseDeviceAdapter, DeviceStatus, DeviceCapability, DeviceParameter, SafetyLimit, DeviceMetrics


class PEMFAdapter(BaseDeviceAdapter):
    """Pulsed Electromagnetic Field therapy device"""
    
    def __init__(self, device_id: str, connection_config: Dict[str, Any]):
        super().__init__(device_id, connection_config)
        
        self.device_type = "pemf_device"
        self.manufacturer = "NOVA ViA Magnetics"
        self.model = "NeuroPEMF-500"
        self.firmware_version = "1.8.3"
        
        self.capabilities = [DeviceCapability.MAGNETIC_FIELD, DeviceCapability.REAL_TIME_MONITORING, DeviceCapability.SAFETY_SHUTOFF]
        
        self.supported_parameters = [
            DeviceParameter("frequency_hz", "float", 0.1, 1000, 10, "Hz", "PEMF frequency"),
            DeviceParameter("intensity_percent", "float", 0, 100, 30, "%", "Field intensity"),
            DeviceParameter("pulse_width_ms", "float", 1, 500, 50, "ms", "Pulse width"),
            DeviceParameter("waveform_type", "enum", enum_values=["sine", "square", "sawtooth"], default_value="sine", description="Waveform type")
        ]
        
        self.safety_limits = [SafetyLimit("intensity_percent", 0, 80, 100, 75)]
        
        self.current_frequency = 10.0
        self.current_intensity = 0.0
        self.treatment_active = False
        self.simulation_mode = True
    
    async def initialize(self) -> bool:
        try:
            await self.connect()
            await self.start_monitoring()
            self.status = DeviceStatus.READY
            return True
        except Exception:
            return False
    
    async def connect(self) -> bool:
        if self.simulation_mode:
            await asyncio.sleep(0.4)
            self.is_connected = True
            self.status = DeviceStatus.ONLINE
            return True
        return False
    
    async def disconnect(self):
        await self.stop_monitoring()
        self.is_connected = False
        self.status = DeviceStatus.OFFLINE
    
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if command == "start_treatment":
            await self.update_parameters(parameters)
            self.treatment_active = True
            self.status = DeviceStatus.ACTIVE
            return {"success": True, "frequency": self.current_frequency}
        elif command == "stop_treatment":
            self.treatment_active = False
            self.current_intensity = 0.0
            self.status = DeviceStatus.READY
            return {"success": True}
        return {"success": False, "error": f"Unknown command: {command}"}
    
    async def get_status(self) -> DeviceStatus:
        return self.status
    
    async def emergency_stop(self) -> bool:
        self.current_intensity = 0.0
        self.treatment_active = False
        self.emergency_stop_triggered = True
        self.status = DeviceStatus.EMERGENCY_STOP
        return True
    
    async def get_metrics(self) -> DeviceMetrics:
        return DeviceMetrics(
            device_id=self.device_id,
            timestamp=time.time(),
            status=self.status,
            parameters={"frequency_hz": self.current_frequency, "intensity_percent": self.current_intensity},
            safety_status={},
            health_indicators={"coil_temperature": 35.0, "field_uniformity": 0.88},
            power_consumption=1.2 * (self.current_intensity / 100)
        )
