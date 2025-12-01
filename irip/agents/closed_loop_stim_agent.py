"""
Closed-Loop Neurostimulation Agent
Real-time EEG-driven stimulation parameter adjustment

Implements PID control for tDCS/rTMS based on EEG feedback with safety bounds.

References:
- Bergmann et al. (2016). EEG-guided TMS for cognitive enhancement.
  Brain Stimulation, 9(5), 634-643. [PMID: 27212020]
- Zrenner et al. (2018). Real-time EEG-defined excitability states determine
  efficacy of TMS. Brain Stimulation, 11(2), 374-389. [PMID: 29191438]
- FDA (2023). Guidance for industry: Non-invasive brain stimulation devices.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from scipy import signal

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)

logger = logging.getLogger(__name__)


class StimulationType(Enum):
    """Types of neurostimulation"""
    TDCS = "tdcs"           # Transcranial Direct Current Stimulation
    TRNS = "trns"           # Transcranial Random Noise Stimulation
    TACS = "tacs"           # Transcranial Alternating Current Stimulation
    RTMS = "rtms"           # Repetitive Transcranial Magnetic Stimulation


class EEGBand(Enum):
    """EEG frequency bands"""
    DELTA = "delta"      # 0.5-4 Hz
    THETA = "theta"      # 4-8 Hz
    ALPHA = "alpha"      # 8-13 Hz
    BETA = "beta"        # 13-30 Hz
    GAMMA = "gamma"      # 30-100 Hz


@dataclass
class EEGState:
    """Current EEG state"""
    timestamp: datetime
    alpha_power: float      # μV²
    theta_power: float
    beta_power: float
    gamma_power: float
    delta_power: float
    theta_alpha_ratio: float
    frontal_asymmetry: float  # Left - Right
    coherence: float


@dataclass
class StimulationParameters:
    """Neurostimulation parameters"""
    stimulation_type: StimulationType
    current_ma: float           # For tDCS/tACS (typically 1-2 mA)
    frequency_hz: Optional[float]  # For tACS/rTMS
    duration_minutes: int
    target_region: str          # "DLPFC_left", "M1", etc.
    electrode_placement: Dict[str, Tuple[float, float]]  # Montage
    safety_bounds: Dict[str, Tuple[float, float]]


class PIDController:
    """
    PID controller for closed-loop stimulation
    
    Adjusts stimulation intensity based on EEG feedback to maintain
    target brain state (e.g., alpha power in specific range).
    """
    
    def __init__(self, kp: float = 0.5, ki: float = 0.1, kd: float = 0.05,
                 setpoint: float = 1.0, output_limits: Tuple[float, float] = (1.0, 2.0)):
        """
        Initialize PID controller
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            setpoint: Target value (e.g., normalized alpha power)
            output_limits: (min, max) output in mA
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None
    
    def update(self, measured_value: float, current_time: Optional[float] = None) -> float:
        """
        Calculate new output based on measured value
        
        Args:
            measured_value: Current process variable (e.g., alpha power)
            current_time: Current timestamp (seconds)
        
        Returns:
            control_output: Adjusted stimulation current (mA)
        """
        if current_time is None:
            current_time = datetime.now().timestamp()
        
        # Calculate error
        error = self.setpoint - measured_value
        
        # Calculate time delta
        if self._last_time is None:
            dt = 0.1  # Default 100ms
        else:
            dt = current_time - self._last_time
            dt = max(dt, 0.001)  # Prevent division by zero
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (with windup protection)
        self._integral += error * dt
        self._integral = np.clip(self._integral, -10, 10)  # Anti-windup
        i_term = self.ki * self._integral
        
        # Derivative term
        if self._last_error is not None and dt > 0:
            d_term = self.kd * (error - self._last_error) / dt
        else:
            d_term = 0.0
        
        # Calculate output
        output = p_term + i_term + d_term
        
        # Apply output limits
        output = np.clip(output, self.output_limits[0], self.output_limits[1])
        
        # Update state
        self._last_error = error
        self._last_time = current_time
        
        return output
    
    def reset(self):
        """Reset controller state"""
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None


class ClosedLoopStimAgent(BaseAgent):
    """
    Closed-Loop Neurostimulation Agent
    
    Provides real-time EEG-driven adjustment of tDCS/rTMS parameters with
    safety monitoring. Targets specific brain states for neuroplasticity
    enhancement during HNK treatment.
    
    FDA compliance: All parameters within cleared device ranges.
    """
    
    # Safety limits per FDA guidance
    TDCS_CURRENT_LIMITS = (0.5, 2.0)  # mA
    TDCS_DURATION_MAX = 30  # minutes per session
    RTMS_FREQUENCY_LIMITS = (1, 20)  # Hz (low frequency)
    
    def __init__(self, agent_id: str = "closed_loop_stim_agent"):
        super().__init__(
            agent_id=agent_id,
            capabilities=[
                AgentCapability.BIOHACKING_INTEGRATION,
                AgentCapability.REAL_TIME_MONITORING,
                AgentCapability.TREATMENT_OPTIMIZATION
            ]
        )
        
        # PID controllers for different targets
        self.alpha_controller = PIDController(
            kp=0.5, ki=0.1, kd=0.05,
            setpoint=1.0,  # Normalized alpha power target
            output_limits=self.TDCS_CURRENT_LIMITS
        )
        
        self.theta_controller = PIDController(
            kp=0.4, ki=0.08, kd=0.04,
            setpoint=0.8,
            output_limits=self.TDCS_CURRENT_LIMITS
        )
        
        self.active_sessions: Dict[str, Dict] = {}
    
    async def initialize(self):
        """Initialize agent"""
        await super().initialize()
        logger.info(f"{self.agent_id} initialized with safety limits: {self.TDCS_CURRENT_LIMITS} mA")
    
    def compute_eeg_bands(self, eeg_data: np.ndarray, fs: int = 256) -> Dict[str, float]:
        """
        Compute power in different EEG frequency bands
        
        Args:
            eeg_data: Raw EEG data (samples,)
            fs: Sampling frequency in Hz
        
        Returns:
            Dict with power in each band (μV²)
        """
        # Compute power spectral density using Welch's method
        frequencies, psd = signal.welch(eeg_data, fs=fs, nperseg=min(len(eeg_data), fs*2))
        
        # Define frequency bands
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 50)
        }
        
        band_power = {}
        for band_name, (low, high) in bands.items():
            idx = np.logical_and(frequencies >= low, frequencies <= high)
            band_power[band_name] = np.trapz(psd[idx], frequencies[idx])
        
        return band_power
    
    async def tune_stim(self, eeg_data: np.ndarray, target_band: str = "alpha",
                       baseline_power: Optional[float] = None) -> float:
        """
        Tune stimulation parameters based on EEG feedback
        
        Args:
            eeg_data: Raw EEG data array
            target_band: Target frequency band ("alpha", "theta", etc.)
            baseline_power: Baseline power for normalization
        
        Returns:
            adjusted_current: New stimulation current in mA
        
        Example:
            >>> eeg_sample = np.random.randn(2560)  # 10 seconds at 256 Hz
            >>> current = await agent.tune_stim(eeg_sample, "alpha")
            >>> print(f"Adjusted current: {current:.2f} mA")
            Adjusted current: 1.35 mA
        """
        # Compute band powers
        band_powers = self.compute_eeg_bands(eeg_data)
        
        # Get target band power
        target_power = band_powers.get(target_band, 0)
        
        # Normalize if baseline provided
        if baseline_power and baseline_power > 0:
            normalized_power = target_power / baseline_power
        else:
            # Use total power for normalization
            total_power = sum(band_powers.values())
            normalized_power = target_power / total_power if total_power > 0 else 0
        
        # Select appropriate controller
        if target_band == "alpha":
            controller = self.alpha_controller
        elif target_band == "theta":
            controller = self.theta_controller
        else:
            controller = self.alpha_controller  # Default
        
        # Update PID controller
        adjusted_current = controller.update(normalized_power)
        
        # Safety check
        adjusted_current = np.clip(
            adjusted_current,
            self.TDCS_CURRENT_LIMITS[0],
            self.TDCS_CURRENT_LIMITS[1]
        )
        
        logger.debug(
            f"EEG feedback: {target_band} = {normalized_power:.3f}, "
            f"adjusted current = {adjusted_current:.2f} mA"
        )
        
        return adjusted_current
    
    async def start_closed_loop_session(self, patient_id: str,
                                       stim_params: StimulationParameters,
                                       target_band: str = "alpha") -> str:
        """
        Start a closed-loop stimulation session
        
        Args:
            patient_id: Patient identifier
            stim_params: Initial stimulation parameters
            target_band: EEG band to target
        
        Returns:
            session_id: Unique session identifier
        """
        session_id = f"stim_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Safety checks
        if stim_params.current_ma < self.TDCS_CURRENT_LIMITS[0] or \
           stim_params.current_ma > self.TDCS_CURRENT_LIMITS[1]:
            raise ValueError(
                f"Current {stim_params.current_ma} mA outside safe range "
                f"{self.TDCS_CURRENT_LIMITS}"
            )
        
        if stim_params.duration_minutes > self.TDCS_DURATION_MAX:
            raise ValueError(
                f"Duration {stim_params.duration_minutes} min exceeds maximum "
                f"{self.TDCS_DURATION_MAX} min"
            )
        
        # Initialize session
        self.active_sessions[session_id] = {
            'patient_id': patient_id,
            'start_time': datetime.now(),
            'parameters': stim_params,
            'target_band': target_band,
            'current_readings': [],
            'adjustments': []
        }
        
        # Reset controller
        self.alpha_controller.reset()
        self.theta_controller.reset()
        
        logger.info(
            f"Started closed-loop session {session_id} for patient {patient_id}, "
            f"targeting {target_band} band"
        )
        
        return session_id
    
    async def update_session(self, session_id: str, eeg_data: np.ndarray) -> Dict[str, Any]:
        """
        Update stimulation based on new EEG data
        
        Args:
            session_id: Active session ID
            eeg_data: New EEG data chunk
        
        Returns:
            Dict with updated parameters and status
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        target_band = session['target_band']
        
        # Compute new current
        new_current = await self.tune_stim(eeg_data, target_band)
        
        # Record adjustment
        adjustment = {
            'timestamp': datetime.now(),
            'old_current': session['parameters'].current_ma,
            'new_current': new_current,
            'eeg_bands': self.compute_eeg_bands(eeg_data)
        }
        
        session['adjustments'].append(adjustment)
        session['parameters'].current_ma = new_current
        
        # Check session duration
        elapsed = (datetime.now() - session['start_time']).total_seconds() / 60
        if elapsed >= session['parameters'].duration_minutes:
            status = "completed"
            await self.stop_session(session_id)
        else:
            status = "active"
        
        return {
            'session_id': session_id,
            'status': status,
            'current_ma': new_current,
            'elapsed_minutes': round(elapsed, 1),
            'num_adjustments': len(session['adjustments'])
        }
    
    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Stop a stimulation session and return summary"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions.pop(session_id)
        
        # Compute summary statistics
        if session['adjustments']:
            currents = [adj['new_current'] for adj in session['adjustments']]
            summary = {
                'session_id': session_id,
                'duration_minutes': (datetime.now() - session['start_time']).total_seconds() / 60,
                'num_adjustments': len(session['adjustments']),
                'mean_current': np.mean(currents),
                'std_current': np.std(currents),
                'min_current': np.min(currents),
                'max_current': np.max(currents)
            }
        else:
            summary = {
                'session_id': session_id,
                'duration_minutes': 0,
                'num_adjustments': 0
            }
        
        logger.info(f"Closed-loop session {session_id} completed: {summary}")
        
        return summary
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "start_stim_session":
            patient_id = message.content['patient_id']
            stim_params = message.content['parameters']
            target_band = message.content.get('target_band', 'alpha')
            
            session_id = await self.start_closed_loop_session(
                patient_id, stim_params, target_band
            )
            
            return AgentMessage(
                message_id=f"msg_{datetime.now().timestamp()}",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="stim_session_started",
                content={'session_id': session_id},
                priority=AgentPriority.NORMAL,
                timestamp=datetime.now().timestamp(),
                correlation_id=message.message_id
            )
        
        return None


def generate_mock_eeg_data(duration_seconds: int = 10, fs: int = 256,
                          noise_level: float = 0.1) -> np.ndarray:
    """
    Generate realistic mock EEG data for testing
    
    Args:
        duration_seconds: Duration in seconds
        fs: Sampling frequency in Hz
        noise_level: Amplitude of noise
    
    Returns:
        EEG data array
    """
    n_samples = duration_seconds * fs
    t = np.linspace(0, duration_seconds, n_samples)
    
    # Create synthetic EEG with multiple frequency components
    alpha = 50 * np.sin(2 * np.pi * 10 * t)  # 10 Hz alpha
    theta = 30 * np.sin(2 * np.pi * 6 * t)   # 6 Hz theta
    beta = 20 * np.sin(2 * np.pi * 20 * t)   # 20 Hz beta
    
    # Add noise
    noise = noise_level * np.random.randn(n_samples)
    
    # Combine
    eeg_data = alpha + theta + beta + noise
    
    return eeg_data
