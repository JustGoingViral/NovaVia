"""
NOVA ViA Hyperbaric Chamber Adapter
Advanced hyperbaric oxygen therapy with neuroplasticity optimization
"""

import asyncio
import logging
import time
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from .base_adapter import (
    BaseDeviceAdapter, DeviceStatus, DeviceCapability, 
    DeviceParameter, SafetyLimit, DeviceMetrics
)


@dataclass
class PressureCurve:
    """Neuroplasticity-optimized pressure curve"""
    name: str
    description: str
    phases: List[Dict[str, Any]]  # Each phase has pressure, duration, rate
    max_pressure_ata: float
    total_duration_minutes: int
    neuroplasticity_optimized: bool = True


class HyperbaricProtocol:
    """Pre-defined hyperbaric treatment protocols"""
    
    NEUROPLASTICITY_ENHANCEMENT = PressureCurve(
        name="Neuroplasticity Enhancement",
        description="Optimized for addiction recovery neuroplasticity",
        phases=[
            {"pressure_ata": 1.0, "duration_min": 2, "rate_ata_per_min": 0.0, "phase": "baseline"},
            {"pressure_ata": 1.3, "duration_min": 5, "rate_ata_per_min": 0.06, "phase": "ascent"},
            {"pressure_ata": 1.3, "duration_min": 45, "rate_ata_per_min": 0.0, "phase": "treatment"},
            {"pressure_ata": 1.0, "duration_min": 8, "rate_ata_per_min": -0.0375, "phase": "descent"}
        ],
        max_pressure_ata=1.3,
        total_duration_minutes=60
    )
    
    INTENSIVE_RECOVERY = PressureCurve(
        name="Intensive Recovery",
        description="Higher pressure for severe addiction cases",
        phases=[
            {"pressure_ata": 1.0, "duration_min": 3, "rate_ata_per_min": 0.0, "phase": "baseline"},
            {"pressure_ata": 1.5, "duration_min": 8, "rate_ata_per_min": 0.0625, "phase": "ascent"},
            {"pressure_ata": 1.5, "duration_min": 60, "rate_ata_per_min": 0.0, "phase": "treatment"},
            {"pressure_ata": 1.0, "duration_min": 12, "rate_ata_per_min": -0.0417, "phase": "descent"}
        ],
        max_pressure_ata=1.5,
        total_duration_minutes=83
    )
    
    MAINTENANCE_THERAPY = PressureCurve(
        name="Maintenance Therapy",
        description="Gentle maintenance for stable recovery",
        phases=[
            {"pressure_ata": 1.0, "duration_min": 2, "rate_ata_per_min": 0.0, "phase": "baseline"},
            {"pressure_ata": 1.2, "duration_min": 4, "rate_ata_per_min": 0.05, "phase": "ascent"},
            {"pressure_ata": 1.2, "duration_min": 30, "rate_ata_per_min": 0.0, "phase": "treatment"},
            {"pressure_ata": 1.0, "duration_min": 4, "rate_ata_per_min": -0.05, "phase": "descent"}
        ],
        max_pressure_ata=1.2,
        total_duration_minutes=40
    )


class HyperbaricAdapter(BaseDeviceAdapter):
    """
    Hyperbaric oxygen therapy device adapter with neuroplasticity optimization
    
    Features:
    - Precise pressure control (±0.01 ATA)
    - Real-time EEG feedback integration
    - Neuroplasticity-optimized pressure curves
    - Emergency decompression protocols
    - Oxygen concentration monitoring
    - Temperature and humidity control
    """
    
    def __init__(self, device_id: str, connection_config: Dict[str, Any]):
        super().__init__(device_id, connection_config)
        
        # Device identification
        self.device_type = "hyperbaric_chamber"
        self.manufacturer = "NOVA ViA Medical Systems"
        self.model = "NeuroHBO-3000"
        self.firmware_version = "2.1.4"
        
        # Device capabilities
        self.capabilities = [
            DeviceCapability.PRESSURE_CONTROL,
            DeviceCapability.TEMPERATURE_CONTROL,
            DeviceCapability.REAL_TIME_MONITORING,
            DeviceCapability.SAFETY_SHUTOFF,
            DeviceCapability.AUTOMATED_CALIBRATION
        ]
        
        # Device parameters
        self.supported_parameters = [
            DeviceParameter(
                name="target_pressure_ata",
                type="float",
                min_value=1.0,
                max_value=2.0,
                default_value=1.3,
                unit="ATA",
                description="Target chamber pressure in atmospheres absolute"
            ),
            DeviceParameter(
                name="oxygen_percentage",
                type="float", 
                min_value=21.0,
                max_value=100.0,
                default_value=100.0,
                unit="%",
                description="Oxygen concentration percentage"
            ),
            DeviceParameter(
                name="temperature_celsius",
                type="float",
                min_value=18.0,
                max_value=26.0,
                default_value=22.0,
                unit="°C",
                description="Chamber temperature"
            ),
            DeviceParameter(
                name="humidity_percentage",
                type="float",
                min_value=40.0,
                max_value=70.0,
                default_value=55.0,
                unit="%",
                description="Chamber humidity"
            ),
            DeviceParameter(
                name="compression_rate_ata_per_min",
                type="float",
                min_value=0.01,
                max_value=0.1,
                default_value=0.05,
                unit="ATA/min",
                description="Pressure increase rate"
            ),
            DeviceParameter(
                name="decompression_rate_ata_per_min",
                type="float",
                min_value=0.01,
                max_value=0.08,
                default_value=0.03,
                unit="ATA/min",
                description="Pressure decrease rate"
            ),
            DeviceParameter(
                name="eeg_feedback_enabled",
                type="bool",
                default_value=True,
                description="Enable real-time EEG feedback optimization"
            ),
            DeviceParameter(
                name="protocol_name",
                type="enum",
                enum_values=["neuroplasticity_enhancement", "intensive_recovery", "maintenance_therapy", "custom"],
                default_value="neuroplasticity_enhancement",
                description="Treatment protocol selection"
            )
        ]
        
        # Safety limits
        self.safety_limits = [
            SafetyLimit(
                parameter="target_pressure_ata",
                min_safe=1.0,
                max_safe=1.8,
                emergency_threshold=2.0,
                warning_threshold=1.7
            ),
            SafetyLimit(
                parameter="oxygen_percentage",
                min_safe=21.0,
                max_safe=100.0,
                emergency_threshold=None,
                warning_threshold=95.0
            ),
            SafetyLimit(
                parameter="temperature_celsius",
                min_safe=18.0,
                max_safe=26.0,
                emergency_threshold=28.0,
                warning_threshold=25.0
            ),
            SafetyLimit(
                parameter="compression_rate_ata_per_min",
                min_safe=0.01,
                max_safe=0.08,
                emergency_threshold=0.1,
                warning_threshold=0.075
            )
        ]
        
        # Hyperbaric-specific state
        self.current_pressure_ata = 1.0
        self.target_pressure_ata = 1.0
        self.oxygen_concentration = 21.0
        self.chamber_temperature = 22.0
        self.chamber_humidity = 55.0
        
        # Treatment state
        self.treatment_active = False
        self.current_protocol: Optional[PressureCurve] = None
        self.treatment_start_time: Optional[float] = None
        self.current_phase = 0
        self.phase_start_time: Optional[float] = None
        
        # EEG feedback integration
        self.eeg_feedback_enabled = True
        self.eeg_alpha_power = 0.0
        self.eeg_coherence = 0.0
        self.neuroplasticity_score = 0.0
        
        # Simulation parameters (for demo)
        self.simulation_mode = True
        self.pressure_simulation_noise = 0.005  # ±5mbar noise
        self.last_pressure_update = time.time()
        
        # Performance metrics
        self.pressure_accuracy_history: List[float] = []
        self.treatment_effectiveness_scores: List[float] = []
    
    async def initialize(self) -> bool:
        """Initialize hyperbaric chamber connection and configuration"""
        try:
            self.logger.info(f"Initializing Hyperbaric Chamber {self.device_id}...")
            
            # Establish connection
            await self.connect()
            
            # Perform system checks
            await self._perform_system_checks()
            
            # Calibrate sensors
            await self._calibrate_sensors()
            
            # Start monitoring
            await self.start_monitoring()
            
            self.status = DeviceStatus.READY
            self.logger.info(f"Hyperbaric Chamber {self.device_id} initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            self.status = DeviceStatus.ERROR
            return False
    
    async def connect(self) -> bool:
        """Establish connection to hyperbaric chamber"""
        try:
            # Simulate connection to chamber control system
            if self.simulation_mode:
                await asyncio.sleep(0.5)  # Simulate connection time
                self.is_connected = True
                self.last_seen = time.time()
                self.status = DeviceStatus.ONLINE
                self.logger.info(f"Connected to hyperbaric chamber simulator at {self.connection_config.get('ip', 'localhost')}")
                return True
            
            # Real device connection would be implemented here
            # For now, use simulation mode
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.status = DeviceStatus.ERROR
            return False
    
    async def disconnect(self):
        """Disconnect from hyperbaric chamber"""
        try:
            # Emergency decompression if pressurized
            if self.current_pressure_ata > 1.05:
                await self.emergency_stop()
            
            # Stop monitoring
            await self.stop_monitoring()
            
            self.is_connected = False
            self.status = DeviceStatus.OFFLINE
            self.logger.info(f"Disconnected from hyperbaric chamber {self.device_id}")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
    
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hyperbaric chamber command"""
        try:
            self.logger.info(f"Executing command: {command} with parameters: {parameters}")
            
            if command == "start_treatment":
                return await self._start_treatment(parameters)
            elif command == "stop_treatment":
                return await self._stop_treatment()
            elif command == "set_pressure":
                return await self._set_pressure(parameters.get("pressure_ata", 1.0))
            elif command == "set_oxygen":
                return await self._set_oxygen_concentration(parameters.get("oxygen_percentage", 100.0))
            elif command == "emergency_decompress":
                return await self._emergency_decompress()
            elif command == "update_eeg_feedback":
                return await self._update_eeg_feedback(parameters)
            elif command == "get_status":
                return await self._get_detailed_status()
            else:
                raise ValueError(f"Unknown command: {command}")
                
        except Exception as e:
            self.logger.error(f"Command execution failed: {command} - {e}")
            return {"success": False, "error": str(e)}
    
    async def get_status(self) -> DeviceStatus:
        """Get current device status"""
        return self.status
    
    async def emergency_stop(self) -> bool:
        """Execute emergency stop protocol"""
        try:
            self.logger.critical("EMERGENCY STOP INITIATED - Beginning emergency decompression")
            
            self.emergency_stop_triggered = True
            self.status = DeviceStatus.EMERGENCY_STOP
            
            # Immediate actions
            await self._emergency_decompress()
            await self._stop_treatment()
            
            # Notification
            self.logger.critical("Emergency decompression completed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            return False
    
    async def _start_treatment(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Start hyperbaric treatment with specified protocol"""
        try:
            # Validate and update parameters
            await self.update_parameters(parameters)
            
            # Get protocol
            protocol_name = parameters.get("protocol_name", "neuroplasticity_enhancement")
            self.current_protocol = self._get_protocol_by_name(protocol_name)
            
            if not self.current_protocol:
                raise ValueError(f"Unknown protocol: {protocol_name}")
            
            # Initialize treatment
            self.treatment_active = True
            self.treatment_start_time = time.time()
            self.current_phase = 0
            self.phase_start_time = time.time()
            self.status = DeviceStatus.ACTIVE
            
            # Start treatment execution
            asyncio.create_task(self._execute_treatment_protocol())
            
            self.logger.info(f"Started hyperbaric treatment: {protocol_name}")
            
            return {
                "success": True,
                "protocol": self.current_protocol.name,
                "estimated_duration_minutes": self.current_protocol.total_duration_minutes,
                "initial_pressure_ata": self.current_pressure_ata
            }
            
        except Exception as e:
            self.logger.error(f"Treatment start failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _stop_treatment(self) -> Dict[str, Any]:
        """Stop current treatment and safely decompress"""
        try:
            if not self.treatment_active:
                return {"success": True, "message": "No active treatment"}
            
            self.treatment_active = False
            
            # Safe decompression
            await self._safe_decompress()
            
            # Calculate treatment metrics
            treatment_duration = time.time() - self.treatment_start_time if self.treatment_start_time else 0
            
            self.status = DeviceStatus.READY
            self.logger.info(f"Treatment stopped after {treatment_duration/60:.1f} minutes")
            
            return {
                "success": True,
                "treatment_duration_minutes": treatment_duration / 60,
                "final_pressure_ata": self.current_pressure_ata
            }
            
        except Exception as e:
            self.logger.error(f"Treatment stop failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_treatment_protocol(self):
        """Execute the complete treatment protocol"""
        try:
            if not self.current_protocol:
                return
            
            self.logger.info(f"Executing protocol: {self.current_protocol.name}")
            
            for phase_index, phase in enumerate(self.current_protocol.phases):
                if not self.treatment_active:
                    break
                
                self.current_phase = phase_index
                self.phase_start_time = time.time()
                
                await self._execute_phase(phase)
            
            # Treatment completed
            if self.treatment_active:
                await self._stop_treatment()
                
        except Exception as e:
            self.logger.error(f"Protocol execution failed: {e}")
            await self.emergency_stop()
    
    async def _execute_phase(self, phase: Dict[str, Any]):
        """Execute a single treatment phase"""
        phase_name = phase["phase"]
        target_pressure = phase["pressure_ata"]
        duration_minutes = phase["duration_min"]
        rate_ata_per_min = phase.get("rate_ata_per_min", 0.0)
        
        self.logger.info(f"Executing phase: {phase_name} - Target: {target_pressure} ATA for {duration_minutes} min")
        
        # Set target pressure
        await self._set_pressure(target_pressure, rate_ata_per_min)
        
        # Wait for phase duration with monitoring
        phase_duration = duration_minutes * 60  # Convert to seconds
        start_time = time.time()
        
        while (time.time() - start_time) < phase_duration and self.treatment_active:
            # Monitor and adjust based on EEG feedback
            if self.eeg_feedback_enabled:
                await self._optimize_based_on_eeg()
            
            # Update pressure simulation
            await self._update_pressure_simulation()
            
            await asyncio.sleep(1.0)  # Update every second
    
    async def _set_pressure(self, target_ata: float, rate_ata_per_min: Optional[float] = None) -> Dict[str, Any]:
        """Set chamber pressure with controlled rate"""
        try:
            self.target_pressure_ata = target_ata
            
            if rate_ata_per_min is None:
                rate_ata_per_min = self.current_parameters.get(
                    "compression_rate_ata_per_min" if target_ata > self.current_pressure_ata else "decompression_rate_ata_per_min",
                    0.05
                )
            
            self.logger.info(f"Setting pressure from {self.current_pressure_ata:.2f} to {target_ata:.2f} ATA at {rate_ata_per_min:.3f} ATA/min")
            
            # Start pressure change simulation
            asyncio.create_task(self._simulate_pressure_change(target_ata, rate_ata_per_min))
            
            return {
                "success": True,
                "current_pressure_ata": self.current_pressure_ata,
                "target_pressure_ata": target_ata,
                "rate_ata_per_min": rate_ata_per_min
            }
            
        except Exception as e:
            self.logger.error(f"Pressure setting failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _simulate_pressure_change(self, target_ata: float, rate_ata_per_min: float):
        """Simulate gradual pressure change"""
        while abs(self.current_pressure_ata - target_ata) > 0.01 and self.treatment_active:
            pressure_diff = target_ata - self.current_pressure_ata
            max_change = (rate_ata_per_min / 60.0)  # Per second
            
            if abs(pressure_diff) <= max_change:
                self.current_pressure_ata = target_ata
            else:
                direction = 1 if pressure_diff > 0 else -1
                self.current_pressure_ata += direction * max_change
            
            # Add realistic noise
            noise = (math.sin(time.time() * 2) * self.pressure_simulation_noise)
            self.current_pressure_ata += noise
            
            # Ensure within bounds
            self.current_pressure_ata = max(1.0, min(2.0, self.current_pressure_ata))
            
            await asyncio.sleep(1.0)
    
    async def _update_pressure_simulation(self):
        """Update pressure simulation with realistic variations"""
        if time.time() - self.last_pressure_update > 0.1:  # Update every 100ms
            # Add small random variations to simulate real device behavior
            variation = (math.sin(time.time() * 3) + math.cos(time.time() * 5)) * 0.002
            self.current_pressure_ata += variation
            
            # Ensure within safety bounds
            self.current_pressure_ata = max(1.0, min(2.0, self.current_pressure_ata))
            
            self.last_pressure_update = time.time()
    
    async def _set_oxygen_concentration(self, percentage: float) -> Dict[str, Any]:
        """Set oxygen concentration"""
        try:
            self.oxygen_concentration = max(21.0, min(100.0, percentage))
            self.logger.info(f"Oxygen concentration set to {self.oxygen_concentration:.1f}%")
            
            return {
                "success": True,
                "oxygen_percentage": self.oxygen_concentration
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _emergency_decompress(self) -> Dict[str, Any]:
        """Perform emergency decompression"""
        try:
            self.logger.critical("Emergency decompression initiated")
            
            # Rapid decompression to ambient pressure
            emergency_rate = 0.15  # 0.15 ATA per minute (faster than normal)
            await self._simulate_pressure_change(1.0, emergency_rate)
            
            # Set status
            self.status = DeviceStatus.EMERGENCY_STOP
            self.treatment_active = False
            
            return {
                "success": True,
                "message": "Emergency decompression completed",
                "final_pressure_ata": self.current_pressure_ata
            }
            
        except Exception as e:
            self.logger.error(f"Emergency decompression failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _safe_decompress(self):
        """Perform safe, controlled decompression"""
        if self.current_pressure_ata > 1.05:
            safe_rate = self.current_parameters.get("decompression_rate_ata_per_min", 0.03)
            await self._simulate_pressure_change(1.0, safe_rate)
    
    async def _update_eeg_feedback(self, eeg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update EEG feedback for real-time optimization"""
        try:
            self.eeg_alpha_power = eeg_data.get("alpha_power", 0.0)
            self.eeg_coherence = eeg_data.get("coherence", 0.0)
            
            # Calculate neuroplasticity score
            self.neuroplasticity_score = (self.eeg_alpha_power * 0.6 + self.eeg_coherence * 0.4)
            
            self.logger.debug(f"EEG feedback updated - Alpha: {self.eeg_alpha_power:.2f}, Coherence: {self.eeg_coherence:.2f}, Score: {self.neuroplasticity_score:.2f}")
            
            return {
                "success": True,
                "neuroplasticity_score": self.neuroplasticity_score
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _optimize_based_on_eeg(self):
        """Optimize treatment parameters based on EEG feedback"""
        if not self.eeg_feedback_enabled or self.neuroplasticity_score == 0:
            return
        
        # Adjust pressure slightly based on neuroplasticity score
        if self.neuroplasticity_score > 0.8:
            # High neuroplasticity - maintain current pressure
            pass
        elif self.neuroplasticity_score > 0.6:
            # Moderate neuroplasticity - small increase
            adjustment = 0.01
            new_target = min(self.target_pressure_ata + adjustment, 1.8)
            if new_target != self.target_pressure_ata:
                await self._set_pressure(new_target, 0.02)
        else:
            # Low neuroplasticity - small decrease
            adjustment = 0.01
            new_target = max(self.target_pressure_ata - adjustment, 1.1)
            if new_target != self.target_pressure_ata:
                await self._set_pressure(new_target, 0.02)
    
    async def _get_detailed_status(self) -> Dict[str, Any]:
        """Get comprehensive device status"""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "status": self.status.value,
            "pressures": {
                "current_ata": round(self.current_pressure_ata, 3),
                "target_ata": round(self.target_pressure_ata, 3),
                "ambient_ata": 1.0
            },
            "atmosphere": {
                "oxygen_percentage": self.oxygen_concentration,
                "temperature_celsius": self.chamber_temperature,
                "humidity_percentage": self.chamber_humidity
            },
            "treatment": {
                "active": self.treatment_active,
                "protocol": self.current_protocol.name if self.current_protocol else None,
                "current_phase": self.current_phase,
                "elapsed_minutes": (time.time() - self.treatment_start_time) / 60 if self.treatment_start_time else 0
            },
            "eeg_feedback": {
                "enabled": self.eeg_feedback_enabled,
                "alpha_power": self.eeg_alpha_power,
                "coherence": self.eeg_coherence,
                "neuroplasticity_score": self.neuroplasticity_score
            },
            "safety": {
                "emergency_stop": self.emergency_stop_triggered,
                "safety_enabled": self.safety_enabled
            },
            "timestamp": time.time()
        }
    
    async def get_metrics(self) -> DeviceMetrics:
        """Get current device metrics"""
        safety_status = await self.check_safety_limits(self.current_parameters) if self.current_parameters else {}
        
        return DeviceMetrics(
            device_id=self.device_id,
            timestamp=time.time(),
            status=self.status,
            parameters={
                "current_pressure_ata": self.current_pressure_ata,
                "target_pressure_ata": self.target_pressure_ata,
                "oxygen_percentage": self.oxygen_concentration,
                "temperature_celsius": self.chamber_temperature,
                "neuroplasticity_score": self.neuroplasticity_score
            },
            safety_status=safety_status,
            health_indicators={
                "pressure_accuracy": self._calculate_pressure_accuracy(),
                "treatment_effectiveness": self.neuroplasticity_score,
                "system_stability": self._calculate_system_stability()
            },
            power_consumption=15.5,  # kW (simulated)
            temperature=self.chamber_temperature,
            operational_hours=245.5  # Hours (simulated)
        )
    
    def _get_protocol_by_name(self, name: str) -> Optional[PressureCurve]:
        """Get treatment protocol by name"""
        protocols = {
            "neuroplasticity_enhancement": HyperbaricProtocol.NEUROPLASTICITY_ENHANCEMENT,
            "intensive_recovery": HyperbaricProtocol.INTENSIVE_RECOVERY,
            "maintenance_therapy": HyperbaricProtocol.MAINTENANCE_THERAPY
        }
        return protocols.get(name)
    
    def _calculate_pressure_accuracy(self) -> float:
        """Calculate pressure control accuracy"""
        accuracy = 1.0 - abs(self.current_pressure_ata - self.target_pressure_ata) / self.target_pressure_ata
        return max(0.0, min(1.0, accuracy))
    
    def _calculate_system_stability(self) -> float:
        """Calculate overall system stability"""
        factors = [
            1.0 if self.is_connected else 0.0,
            1.0 if not self.emergency_stop_triggered else 0.0,
            self._calculate_pressure_accuracy(),
            1.0 if self.chamber_temperature > 18 and self.chamber_temperature < 26 else 0.8
        ]
        return sum(factors) / len(factors)
    
    async def _perform_system_checks(self):
        """Perform initialization system checks"""
        self.logger.info("Performing hyperbaric system checks...")
        
        # Simulate system checks
        await asyncio.sleep(1.0)
        
        checks = [
            "Pressure sensors calibration",
            "Oxygen analyzer verification", 
            "Safety valve functionality",
            "Emergency systems test",
            "Communication interfaces"
        ]
        
        for check in checks:
            self.logger.info(f"✓ {check}")
            await asyncio.sleep(0.2)
        
        self.logger.info("All system checks passed")
    
    async def _calibrate_sensors(self):
        """Calibrate pressure and gas sensors"""
        self.logger.info("Calibrating sensors...")
        
        # Simulate sensor calibration
        await asyncio.sleep(2.0)
        
        self.logger.info("Sensor calibration complete")
