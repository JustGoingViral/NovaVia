"""NOVA ViA Frequency Therapy Adapter - Binaural Beats & Isochronic Tones"""

import asyncio
import time
from typing import Dict, Any
from .base_adapter import BaseDeviceAdapter, DeviceStatus, DeviceCapability, DeviceParameter, SafetyLimit, DeviceMetrics


class FrequencyAdapter(BaseDeviceAdapter):
    """Frequency therapy device for binaural beats and isochronic tones"""
    
    def __init__(self, device_id: str, connection_config: Dict[str, Any]):
        super().__init__(device_id, connection_config)
        
        self.device_type = "frequency_therapy"
        self.manufacturer = "NOVA ViA Audio"
        self.model = "NeuroFreq-X1"
        self.firmware_version = "2.5.0"
        
        self.capabilities = [DeviceCapability.FREQUENCY_GENERATION, DeviceCapability.REAL_TIME_MONITORING]
        
        self.supported_parameters = [
            DeviceParameter("base_frequency_hz", "float", 20, 20000, 440, "Hz", "Base carrier frequency"),
            DeviceParameter("binaural_beat_hz", "float", 0.1, 100, 10, "Hz", "Binaural beat frequency"),
            DeviceParameter("volume_percent", "float", 0, 100, 25, "%", "Audio volume"),
            DeviceParameter("waveform", "enum", enum_values=["sine", "square", "triangle", "pink_noise"], default_value="sine", description="Waveform type"),
            DeviceParameter("therapy_type", "enum", enum_values=["binaural", "isochronic", "monaural"], default_value="binaural", description="Therapy type")
        ]
        
        self.safety_limits = [SafetyLimit("volume_percent", 0, 70, 90, 65)]
        
        self.current_base_freq = 440.0
        self.current_binaural_freq = 10.0
        self.current_volume = 0.0
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
            await asyncio.sleep(0.2)
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
            return {"success": True, "binaural_frequency": self.current_binaural_freq}
        elif command == "stop_treatment":
            self.treatment_active = False
            self.current_volume = 0.0
            self.status = DeviceStatus.READY
            return {"success": True}
        return {"success": False, "error": f"Unknown command: {command}"}
    
    async def get_status(self) -> DeviceStatus:
        return self.status
    
    async def emergency_stop(self) -> bool:
        self.current_volume = 0.0
        self.treatment_active = False
        self.emergency_stop_triggered = True
        self.status = DeviceStatus.EMERGENCY_STOP
        return True
    
    async def get_metrics(self) -> DeviceMetrics:
        return DeviceMetrics(
            device_id=self.device_id,
            timestamp=time.time(),
            status=self.status,
            parameters={
                "base_frequency_hz": self.current_base_freq,
                "binaural_beat_hz": self.current_binaural_freq,
                "volume_percent": self.current_volume
            },
            safety_status={},
            health_indicators={"audio_quality": 0.95, "frequency_accuracy": 0.999},
            power_consumption=0.5 * (self.current_volume / 100)
        )
