"""
NOVA ViA Red Light Therapy Adapter
Advanced photobiomodulation with wavelength optimization
"""

import asyncio
import time
import math
from typing import Dict, Any, Optional
from .base_adapter import (
    BaseDeviceAdapter, DeviceStatus, DeviceCapability, 
    DeviceParameter, SafetyLimit, DeviceMetrics
)


class RedLightAdapter(BaseDeviceAdapter):
    """Red light therapy device with neuroplasticity-optimized wavelengths"""
    
    def __init__(self, device_id: str, connection_config: Dict[str, Any]):
        super().__init__(device_id, connection_config)
        
        self.device_type = "red_light_therapy"
        self.manufacturer = "NOVA ViA Photonics"
        self.model = "NeuroLight-Pro"
        self.firmware_version = "3.2.1"
        
        self.capabilities = [
            DeviceCapability.LIGHT_THERAPY,
            DeviceCapability.REAL_TIME_MONITORING,
            DeviceCapability.SAFETY_SHUTOFF
        ]
        
        self.supported_parameters = [
            DeviceParameter("wavelength_nm", "int", 630, 850, 660, "nm", "Primary wavelength"),
            DeviceParameter("intensity_percent", "float", 0, 100, 50, "%", "Light intensity"),
            DeviceParameter("pulse_frequency_hz", "float", 0.1, 100, 10, "Hz", "Pulse frequency"),
            DeviceParameter("treatment_duration_min", "int", 1, 60, 20, "min", "Treatment duration"),
            DeviceParameter("beam_angle_degrees", "int", 15, 120, 60, "°", "Beam angle")
        ]
        
        self.safety_limits = [
            SafetyLimit("intensity_percent", 0, 90, 100, 85),
            SafetyLimit("treatment_duration_min", 1, 45, 60, 40)
        ]
        
        # Device state
        self.current_wavelength = 660
        self.current_intensity = 0.0
        self.pulse_frequency = 10.0
        self.treatment_active = False
        self.simulation_mode = True
    
    async def initialize(self) -> bool:
        try:
            await self.connect()
            await self.start_monitoring()
            self.status = DeviceStatus.READY
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    async def connect(self) -> bool:
        if self.simulation_mode:
            await asyncio.sleep(0.3)
            self.is_connected = True
            self.status = DeviceStatus.ONLINE
            self.logger.info(f"Connected to red light therapy simulator")
            return True
        return False
    
    async def disconnect(self):
        await self.stop_monitoring()
        self.is_connected = False
        self.status = DeviceStatus.OFFLINE
    
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if command == "start_treatment":
            return await self._start_treatment(parameters)
        elif command == "stop_treatment":
            return await self._stop_treatment()
        elif command == "set_intensity":
            intensity = parameters.get("intensity_percent", 50)
            self.current_intensity = max(0, min(100, intensity))
            return {"success": True, "intensity": self.current_intensity}
        elif command == "set_wavelength":
            wavelength = parameters.get("wavelength_nm", 660)
            self.current_wavelength = max(630, min(850, wavelength))
            return {"success": True, "wavelength": self.current_wavelength}
        else:
            return {"success": False, "error": f"Unknown command: {command}"}
    
    async def get_status(self) -> DeviceStatus:
        return self.status
    
    async def emergency_stop(self) -> bool:
        self.current_intensity = 0.0
        self.treatment_active = False
        self.emergency_stop_triggered = True
        self.status = DeviceStatus.EMERGENCY_STOP
        return True
    
    async def _start_treatment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        await self.update_parameters(parameters)
        self.treatment_active = True
        self.status = DeviceStatus.ACTIVE
        
        # Simulate gradual intensity ramp
        asyncio.create_task(self._ramp_intensity())
        
        return {
            "success": True,
            "wavelength_nm": self.current_wavelength,
            "target_intensity": parameters.get("intensity_percent", 50)
        }
    
    async def _stop_treatment(self) -> Dict[str, Any]:
        self.treatment_active = False
        await self._ramp_down_intensity()
        self.status = DeviceStatus.READY
        return {"success": True}
    
    async def _ramp_intensity(self):
        target = self.current_parameters.get("intensity_percent", 50)
        while self.current_intensity < target and self.treatment_active:
            self.current_intensity = min(self.current_intensity + 2, target)
            await asyncio.sleep(0.5)
    
    async def _ramp_down_intensity(self):
        while self.current_intensity > 0:
            self.current_intensity = max(self.current_intensity - 5, 0)
            await asyncio.sleep(0.2)
    
    async def get_metrics(self) -> DeviceMetrics:
        return DeviceMetrics(
            device_id=self.device_id,
            timestamp=time.time(),
            status=self.status,
            parameters={
                "wavelength_nm": self.current_wavelength,
                "intensity_percent": self.current_intensity,
                "pulse_frequency_hz": self.pulse_frequency
            },
            safety_status={},
            health_indicators={
                "led_temperature": 45.2 + (self.current_intensity * 0.3),
                "power_efficiency": 0.92,
                "beam_uniformity": 0.95
            },
            power_consumption=2.5 * (self.current_intensity / 100)
        )
