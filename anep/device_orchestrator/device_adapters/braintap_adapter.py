"""
NOVA ViA Brain Tap Adapter
Advanced brainwave entrainment and neurofeedback integration
"""

import asyncio
import time
import math
import statistics
from typing import Dict, Any, List
from dataclasses import dataclass
from .base_adapter import (
    BaseDeviceAdapter, DeviceStatus, DeviceCapability, 
    DeviceParameter, SafetyLimit, DeviceMetrics
)


@dataclass
class BrainTapSession:
    """Brain Tap session configuration"""
    session_id: str
    session_type: str  # meditation, addiction_recovery, sleep, focus
    duration_minutes: int
    brainwave_target: str  # alpha, beta, theta, delta, gamma
    light_pattern: str
    audio_program: str
    vibration_enabled: bool = True


class BrainTapProtocols:
    """Pre-defined Brain Tap protocols for addiction recovery"""
    
    ADDICTION_RECOVERY_ALPHA = BrainTapSession(
        session_id="addiction_alpha_01",
        session_type="addiction_recovery",
        duration_minutes=30,
        brainwave_target="alpha",
        light_pattern="alpha_enhancement",
        audio_program="recovery_affirmations",
        vibration_enabled=True
    )
    
    CRAVING_SUPPRESSION = BrainTapSession(
        session_id="craving_suppress_01", 
        session_type="craving_control",
        duration_minutes=15,
        brainwave_target="theta",
        light_pattern="theta_deep",
        audio_program="craving_reduction",
        vibration_enabled=True
    )
    
    STRESS_REDUCTION = BrainTapSession(
        session_id="stress_reduce_01",
        session_type="stress_management",
        duration_minutes=20,
        brainwave_target="alpha",
        light_pattern="calming_blue",
        audio_program="stress_relief",
        vibration_enabled=False
    )
    
    SLEEP_RECOVERY = BrainTapSession(
        session_id="sleep_recovery_01",
        session_type="sleep_enhancement",
        duration_minutes=45,
        brainwave_target="delta",
        light_pattern="delta_sleep",
        audio_program="deep_sleep",
        vibration_enabled=False
    )


class BrainTapAdapter(BaseDeviceAdapter):
    """
    Brain Tap neurofeedback device adapter for addiction recovery
    
    Features:
    - Brainwave entrainment (Alpha, Beta, Theta, Delta, Gamma)
    - Light therapy integration with binaural beats
    - Vibrational feedback for enhanced neuroplasticity
    - EEG-guided session optimization
    - Addiction-specific protocols
    """
    
    def __init__(self, device_id: str, connection_config: Dict[str, Any]):
        super().__init__(device_id, connection_config)
        
        # Device identification
        self.device_type = "brain_tap"
        self.manufacturer = "NOVA ViA Neurotechnology"
        self.model = "BrainTap-Pro-Recovery"
        self.firmware_version = "4.2.1"
        
        # Device capabilities
        self.capabilities = [
            DeviceCapability.NEUROFEEDBACK,
            DeviceCapability.LIGHT_THERAPY,
            DeviceCapability.AUDIO_THERAPY,
            DeviceCapability.VIBRATIONAL_FEEDBACK,
            DeviceCapability.REAL_TIME_MONITORING,
            DeviceCapability.EEG_INTEGRATION
        ]
        
        # Device parameters
        self.supported_parameters = [
            DeviceParameter(
                name="brainwave_target",
                type="enum",
                enum_values=["alpha", "beta", "theta", "delta", "gamma"],
                default_value="alpha",
                description="Target brainwave frequency band"
            ),
            DeviceParameter(
                name="light_intensity",
                type="float",
                min_value=0.0,
                max_value=100.0,
                default_value=50.0,
                unit="%",
                description="Light therapy intensity"
            ),
            DeviceParameter(
                name="audio_volume",
                type="float",
                min_value=0.0,
                max_value=100.0,
                default_value=30.0,
                unit="%",
                description="Audio program volume"
            ),
            DeviceParameter(
                name="vibration_intensity",
                type="float",
                min_value=0.0,
                max_value=100.0,
                default_value=25.0,
                unit="%",
                description="Vibrational feedback intensity"
            ),
            DeviceParameter(
                name="session_duration",
                type="int",
                min_value=5,
                max_value=90,
                default_value=30,
                unit="minutes",
                description="Session duration"
            ),
            DeviceParameter(
                name="eeg_feedback_enabled",
                type="bool",
                default_value=True,
                description="Enable real-time EEG feedback optimization"
            ),
            DeviceParameter(
                name="protocol_type",
                type="enum",
                enum_values=["addiction_recovery", "craving_control", "stress_management", "sleep_enhancement", "custom"],
                default_value="addiction_recovery",
                description="Treatment protocol type"
            )
        ]
        
        # Safety limits
        self.safety_limits = [
            SafetyLimit(
                parameter="light_intensity",
                min_safe=0.0,
                max_safe=80.0,
                emergency_threshold=95.0,
                warning_threshold=75.0
            ),
            SafetyLimit(
                parameter="audio_volume",
                min_safe=0.0,
                max_safe=70.0,
                emergency_threshold=85.0,
                warning_threshold=65.0
            ),
            SafetyLimit(
                parameter="session_duration",
                min_safe=5,
                max_safe=60,
                emergency_threshold=90,
                warning_threshold=75
            )
        ]
        
        # Brain Tap specific state
        self.current_brainwave_target = "alpha"
        self.light_intensity = 0.0
        self.audio_volume = 0.0
        self.vibration_intensity = 0.0
        
        # Session state
        self.session_active = False
        self.current_session: BrainTapSession = None
        self.session_start_time = None
        self.session_progress = 0.0  # 0.0 to 1.0
        
        # EEG integration
        self.eeg_feedback_enabled = True
        self.current_brainwave_power = {}  # alpha, beta, theta, delta, gamma
        self.target_achievement_score = 0.0  # How well achieving target brainwave
        
        # Neurofeedback metrics
        self.session_effectiveness_scores = []
        self.brainwave_coherence_history = []
        
        # Simulation mode
        self.simulation_mode = True
        self.simulated_brainwave_response = 0.5
    
    async def initialize(self) -> bool:
        """Initialize Brain Tap device connection and configuration"""
        try:
            self.logger.info(f"Initializing Brain Tap device {self.device_id}...")
            
            # Establish connection
            await self.connect()
            
            # Perform device calibration
            await self._calibrate_sensors()
            
            # Load addiction recovery protocols
            await self._load_recovery_protocols()
            
            # Start monitoring
            await self.start_monitoring()
            
            self.status = DeviceStatus.READY
            self.logger.info(f"Brain Tap device {self.device_id} initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Brain Tap initialization failed: {e}")
            self.status = DeviceStatus.ERROR
            return False
    
    async def connect(self) -> bool:
        """Establish connection to Brain Tap device"""
        try:
            if self.simulation_mode:
                await asyncio.sleep(0.3)  # Simulate connection time
                self.is_connected = True
                self.last_seen = time.time()
                self.status = DeviceStatus.ONLINE
                self.logger.info(f"Connected to Brain Tap simulator at {self.connection_config.get('ip', 'localhost')}")
                return True
            
            # Real device connection would be implemented here
            return True
            
        except Exception as e:
            self.logger.error(f"Brain Tap connection failed: {e}")
            self.status = DeviceStatus.ERROR
            return False
    
    async def disconnect(self):
        """Disconnect from Brain Tap device"""
        try:
            # Stop any active session
            if self.session_active:
                await self._stop_session()
            
            await self.stop_monitoring()
            
            self.is_connected = False
            self.status = DeviceStatus.OFFLINE
            self.logger.info(f"Disconnected from Brain Tap device {self.device_id}")
            
        except Exception as e:
            self.logger.error(f"Brain Tap disconnect error: {e}")
    
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Brain Tap device command"""
        try:
            self.logger.info(f"Executing Brain Tap command: {command} with parameters: {parameters}")
            
            if command == "start_session":
                return await self._start_session(parameters)
            elif command == "stop_session":
                return await self._stop_session()
            elif command == "set_light_intensity":
                return await self._set_light_intensity(parameters.get("intensity", 50.0))
            elif command == "set_audio_volume":
                return await self._set_audio_volume(parameters.get("volume", 30.0))
            elif command == "set_vibration":
                return await self._set_vibration_intensity(parameters.get("intensity", 25.0))
            elif command == "update_eeg_feedback":
                return await self._update_eeg_feedback(parameters)
            elif command == "get_session_progress":
                return await self._get_session_progress()
            elif command == "get_brainwave_metrics":
                return await self._get_brainwave_metrics()
            else:
                raise ValueError(f"Unknown Brain Tap command: {command}")
                
        except Exception as e:
            self.logger.error(f"Brain Tap command execution failed: {command} - {e}")
            return {"success": False, "error": str(e)}
    
    async def get_status(self) -> DeviceStatus:
        """Get current device status"""
        return self.status
    
    async def emergency_stop(self) -> bool:
        """Execute emergency stop protocol"""
        try:
            self.logger.critical("EMERGENCY STOP INITIATED - Stopping Brain Tap session")
            
            self.emergency_stop_triggered = True
            self.status = DeviceStatus.EMERGENCY_STOP
            
            # Immediate actions
            await self._stop_session()
            self.light_intensity = 0.0
            self.audio_volume = 0.0
            self.vibration_intensity = 0.0
            
            self.logger.critical("Brain Tap emergency stop completed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Brain Tap emergency stop failed: {e}")
            return False
    
    async def _start_session(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Start Brain Tap neurofeedback session"""
        try:
            # Validate and update parameters
            await self.update_parameters(parameters)
            
            # Get protocol
            protocol_type = parameters.get("protocol_type", "addiction_recovery")
            self.current_session = self._get_protocol_by_type(protocol_type)
            
            if not self.current_session:
                # Create custom session
                self.current_session = BrainTapSession(
                    session_id=f"custom_{int(time.time())}",
                    session_type="custom",
                    duration_minutes=parameters.get("session_duration", 30),
                    brainwave_target=parameters.get("brainwave_target", "alpha"),
                    light_pattern="custom",
                    audio_program="custom",
                    vibration_enabled=parameters.get("vibration_intensity", 0) > 0
                )
            
            # Initialize session
            self.session_active = True
            self.session_start_time = time.time()
            self.session_progress = 0.0
            self.status = DeviceStatus.ACTIVE
            
            # Start session execution
            asyncio.create_task(self._execute_session())
            
            self.logger.info(f"Started Brain Tap session: {self.current_session.session_type}")
            
            return {
                "success": True,
                "session_id": self.current_session.session_id,
                "session_type": self.current_session.session_type,
                "target_brainwave": self.current_session.brainwave_target,
                "duration_minutes": self.current_session.duration_minutes
            }
            
        except Exception as e:
            self.logger.error(f"Brain Tap session start failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _stop_session(self) -> Dict[str, Any]:
        """Stop current Brain Tap session"""
        try:
            if not self.session_active:
                return {"success": True, "message": "No active session"}
            
            self.session_active = False
            
            # Calculate session metrics
            session_duration = time.time() - self.session_start_time if self.session_start_time else 0
            effectiveness_score = self.target_achievement_score
            
            # Gradual ramp down
            await self._ramp_down_stimulation()
            
            self.status = DeviceStatus.READY
            self.logger.info(f"Brain Tap session stopped after {session_duration/60:.1f} minutes")
            
            return {
                "success": True,
                "session_duration_minutes": session_duration / 60,
                "effectiveness_score": effectiveness_score,
                "target_achievement": self.target_achievement_score
            }
            
        except Exception as e:
            self.logger.error(f"Brain Tap session stop failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_session(self):
        """Execute the complete Brain Tap session"""
        try:
            if not self.current_session:
                return
            
            session_duration = self.current_session.duration_minutes * 60  # Convert to seconds
            
            # Ramp up phase (first 10% of session)
            await self._ramp_up_stimulation()
            
            # Main session loop
            start_time = time.time()
            
            while (time.time() - start_time) < session_duration and self.session_active:
                # Update session progress
                elapsed = time.time() - start_time
                self.session_progress = min(elapsed / session_duration, 1.0)
                
                # Apply EEG feedback optimization
                if self.eeg_feedback_enabled:
                    await self._optimize_based_on_eeg()
                
                # Update brainwave simulation
                await self._simulate_brainwave_response()
                
                await asyncio.sleep(1.0)  # Update every second
            
            # Session completed
            if self.session_active:
                await self._stop_session()
                
        except Exception as e:
            self.logger.error(f"Brain Tap session execution failed: {e}")
            await self.emergency_stop()
    
    async def _ramp_up_stimulation(self):
        """Gradually ramp up stimulation parameters"""
        target_light = self.current_parameters.get("light_intensity", 50.0)
        target_audio = self.current_parameters.get("audio_volume", 30.0)
        target_vibration = self.current_parameters.get("vibration_intensity", 25.0)
        
        # Gradual ramp over 30 seconds
        ramp_duration = 30
        steps = 30
        
        for i in range(steps):
            if not self.session_active:
                break
                
            progress = (i + 1) / steps
            
            self.light_intensity = target_light * progress
            self.audio_volume = target_audio * progress  
            self.vibration_intensity = target_vibration * progress
            
            await asyncio.sleep(ramp_duration / steps)
    
    async def _ramp_down_stimulation(self):
        """Gradually ramp down stimulation parameters"""
        current_light = self.light_intensity
        current_audio = self.audio_volume
        current_vibration = self.vibration_intensity
        
        # Gradual ramp down over 15 seconds
        ramp_duration = 15
        steps = 15
        
        for i in range(steps):
            progress = 1.0 - ((i + 1) / steps)
            
            self.light_intensity = current_light * progress
            self.audio_volume = current_audio * progress
            self.vibration_intensity = current_vibration * progress
            
            await asyncio.sleep(ramp_duration / steps)
        
        # Ensure complete stop
        self.light_intensity = 0.0
        self.audio_volume = 0.0
        self.vibration_intensity = 0.0
    
    async def _set_light_intensity(self, intensity: float) -> Dict[str, Any]:
        """Set light therapy intensity"""
        try:
            self.light_intensity = max(0.0, min(100.0, intensity))
            self.logger.info(f"Brain Tap light intensity set to {self.light_intensity:.1f}%")
            
            return {
                "success": True,
                "light_intensity": self.light_intensity
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _set_audio_volume(self, volume: float) -> Dict[str, Any]:
        """Set audio therapy volume"""
        try:
            self.audio_volume = max(0.0, min(100.0, volume))
            self.logger.info(f"Brain Tap audio volume set to {self.audio_volume:.1f}%")
            
            return {
                "success": True,
                "audio_volume": self.audio_volume
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _set_vibration_intensity(self, intensity: float) -> Dict[str, Any]:
        """Set vibrational feedback intensity"""
        try:
            self.vibration_intensity = max(0.0, min(100.0, intensity))
            self.logger.info(f"Brain Tap vibration intensity set to {self.vibration_intensity:.1f}%")
            
            return {
                "success": True,
                "vibration_intensity": self.vibration_intensity
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_eeg_feedback(self, eeg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update EEG feedback for real-time optimization"""
        try:
            # Update brainwave power levels
            self.current_brainwave_power = {
                "alpha": eeg_data.get("alpha_power", 0.0),
                "beta": eeg_data.get("beta_power", 0.0),
                "theta": eeg_data.get("theta_power", 0.0),
                "delta": eeg_data.get("delta_power", 0.0),
                "gamma": eeg_data.get("gamma_power", 0.0)
            }
            
            # Calculate target achievement score
            target_power = self.current_brainwave_power.get(self.current_brainwave_target, 0.0)
            self.target_achievement_score = min(target_power * 2.0, 1.0)  # Scale to 0-1
            
            self.logger.debug(f"Brain Tap EEG feedback updated - Target: {self.current_brainwave_target}, Achievement: {self.target_achievement_score:.2f}")
            
            return {
                "success": True,
                "target_achievement_score": self.target_achievement_score,
                "brainwave_power": self.current_brainwave_power
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _optimize_based_on_eeg(self):
        """Optimize stimulation based on real-time EEG feedback"""
        if not self.eeg_feedback_enabled or self.target_achievement_score == 0:
            return
        
        # Adjust stimulation intensity based on target achievement
        if self.target_achievement_score > 0.8:
            # High achievement - maintain current settings
            pass
        elif self.target_achievement_score > 0.5:
            # Moderate achievement - small increase
            adjustment = 1.05
            self.light_intensity = min(self.light_intensity * adjustment, 80.0)
        else:
            # Low achievement - increase stimulation
            adjustment = 1.1
            self.light_intensity = min(self.light_intensity * adjustment, 80.0)
            self.vibration_intensity = min(self.vibration_intensity * 1.05, 80.0)
    
    async def _simulate_brainwave_response(self):
        """Simulate brainwave response for demo purposes"""
        if self.simulation_mode and self.session_active:
            # Simulate gradual improvement in target brainwave
            target_factor = 1.0 if self.current_brainwave_target == "alpha" else 0.8
            
            # Simulate response based on stimulation intensity
            stimulation_factor = (self.light_intensity + self.vibration_intensity) / 200.0
            
            self.simulated_brainwave_response = min(
                self.simulated_brainwave_response + (stimulation_factor * 0.01),
                target_factor
            )
            
            # Update achievement score
            self.target_achievement_score = self.simulated_brainwave_response
    
    async def _get_session_progress(self) -> Dict[str, Any]:
        """Get current session progress"""
        return {
            "success": True,
            "session_active": self.session_active,
            "progress_percentage": self.session_progress * 100,
            "target_achievement_score": self.target_achievement_score,
            "elapsed_minutes": (time.time() - self.session_start_time) / 60 if self.session_start_time else 0
        }
    
    async def _get_brainwave_metrics(self) -> Dict[str, Any]:
        """Get current brainwave metrics"""
        return {
            "success": True,
            "brainwave_power": self.current_brainwave_power,
            "target_brainwave": self.current_brainwave_target,
            "achievement_score": self.target_achievement_score,
            "session_effectiveness": statistics.mean(self.session_effectiveness_scores) if self.session_effectiveness_scores else 0.0
        }
    
    async def get_metrics(self) -> DeviceMetrics:
        """Get current device metrics"""
        safety_status = await self.check_safety_limits(self.current_parameters) if self.current_parameters else {}
        
        return DeviceMetrics(
            device_id=self.device_id,
            timestamp=time.time(),
            status=self.status,
            parameters={
                "light_intensity": self.light_intensity,
                "audio_volume": self.audio_volume,
                "vibration_intensity": self.vibration_intensity,
                "target_brainwave": self.current_brainwave_target,
                "achievement_score": self.target_achievement_score
            },
            safety_status=safety_status,
            health_indicators={
                "session_effectiveness": self.target_achievement_score,
                "device_temperature": 35.2,  # Simulated
                "light_led_health": 0.98,
                "audio_system_health": 0.96
            },
            power_consumption=2.8,  # Watts
            temperature=35.2
        )
    
    def _get_protocol_by_type(self, protocol_type: str) -> BrainTapSession:
        """Get Brain Tap protocol by type"""
        protocols = {
            "addiction_recovery": BrainTapProtocols.ADDICTION_RECOVERY_ALPHA,
            "craving_control": BrainTapProtocols.CRAVING_SUPPRESSION,
            "stress_management": BrainTapProtocols.STRESS_REDUCTION,
            "sleep_enhancement": BrainTapProtocols.SLEEP_RECOVERY
        }
        return protocols.get(protocol_type)
    
    async def _calibrate_sensors(self):
        """Calibrate Brain Tap sensors"""
        self.logger.info("Calibrating Brain Tap sensors...")
        
        # Simulate sensor calibration
        await asyncio.sleep(1.5)
        
        self.logger.info("Brain Tap sensor calibration complete")
    
    async def _load_recovery_protocols(self):
        """Load addiction recovery specific protocols"""
        self.logger.info("Loading Brain Tap addiction recovery protocols...")
        
        # Simulate protocol loading
        await asyncio.sleep(0.5)
        
        self.logger.info("Brain Tap recovery protocols loaded")
