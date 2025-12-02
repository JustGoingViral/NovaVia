"""
Phase 1 Tests: Closed-Loop Neurostimulation

Tests for PID control and EEG-driven stimulation adjustment.
"""

import pytest
import numpy as np
import asyncio

try:
    from irip.agents.closed_loop_stim_agent import (
        ClosedLoopStimAgent,
        PIDController,
        StimulationParameters,
        StimulationType,
        generate_mock_eeg_data
    )
    STIM_AVAILABLE = True
except ImportError:
    STIM_AVAILABLE = False


@pytest.mark.skipif(not STIM_AVAILABLE, reason="SciPy not installed")
class TestClosedLoopStimAgent:
    """Test suite for Closed-Loop Neurostimulation Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = ClosedLoopStimAgent()
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes with safety limits"""
        assert agent.agent_id == "closed_loop_stim_agent"
        assert agent.TDCS_CURRENT_LIMITS == (0.5, 2.0)
        assert agent.TDCS_DURATION_MAX == 30
    
    @pytest.mark.asyncio
    async def test_tune_stim_output_range(self, agent):
        """Test stimulation tuning stays within safety bounds [1, 2] mA"""
        eeg_data = generate_mock_eeg_data(duration_seconds=10)
        
        current = await agent.tune_stim(eeg_data, target_band="alpha")
        
        # Must be within safety bounds
        assert 0.5 <= current <= 2.0, f"Current {current} outside safety bounds"
    
    @pytest.mark.asyncio
    async def test_tune_stim_multiple_bands(self, agent):
        """Test tuning for different EEG bands"""
        eeg_data = generate_mock_eeg_data(duration_seconds=10)
        
        alpha_current = await agent.tune_stim(eeg_data, target_band="alpha")
        theta_current = await agent.tune_stim(eeg_data, target_band="theta")
        
        assert 0.5 <= alpha_current <= 2.0
        assert 0.5 <= theta_current <= 2.0
    
    @pytest.mark.asyncio
    async def test_eeg_band_computation(self, agent):
        """Test EEG frequency band power computation"""
        eeg_data = generate_mock_eeg_data(duration_seconds=10, fs=256)
        
        band_powers = agent.compute_eeg_bands(eeg_data, fs=256)
        
        # Should have all bands
        assert 'delta' in band_powers
        assert 'theta' in band_powers
        assert 'alpha' in band_powers
        assert 'beta' in band_powers
        assert 'gamma' in band_powers
        
        # All powers should be positive
        for band, power in band_powers.items():
            assert power >= 0, f"{band} power should be non-negative"
    
    def test_pid_controller_basic(self):
        """Test PID controller basic functionality"""
        controller = PIDController(
            kp=0.5, ki=0.1, kd=0.05,
            setpoint=1.0,
            output_limits=(1.0, 2.0)
        )
        
        # Test with measured value below setpoint
        output1 = controller.update(0.8)
        assert 1.0 <= output1 <= 2.0
        
        # Test with measured value above setpoint
        controller.reset()
        output2 = controller.update(1.2)
        assert 1.0 <= output2 <= 2.0
    
    def test_pid_controller_output_limits(self):
        """Test PID controller respects output limits"""
        controller = PIDController(
            kp=10.0, ki=5.0, kd=2.0,  # High gains
            setpoint=1.0,
            output_limits=(1.0, 2.0)
        )
        
        # Even with high gains and large error, should respect limits
        output = controller.update(0.1)  # Large negative error
        assert 1.0 <= output <= 2.0
        
        output = controller.update(10.0)  # Large positive error
        assert 1.0 <= output <= 2.0
    
    @pytest.mark.asyncio
    async def test_start_session_safety_checks(self, agent):
        """Test that session start validates safety parameters"""
        stim_params = StimulationParameters(
            stimulation_type=StimulationType.TDCS,
            current_ma=1.5,
            frequency_hz=None,
            duration_minutes=20,
            target_region="DLPFC_left",
            electrode_placement={"anode": (0, 0), "cathode": (1, 1)},
            safety_bounds={"current": (0.5, 2.0)}
        )
        
        session_id = await agent.start_closed_loop_session(
            "patient_001",
            stim_params,
            target_band="alpha"
        )
        
        assert session_id is not None
        assert session_id.startswith("stim_patient_001")
        assert session_id in agent.active_sessions
    
    @pytest.mark.asyncio
    async def test_session_rejects_unsafe_current(self, agent):
        """Test that unsafe current levels are rejected"""
        unsafe_params = StimulationParameters(
            stimulation_type=StimulationType.TDCS,
            current_ma=5.0,  # Too high!
            frequency_hz=None,
            duration_minutes=20,
            target_region="DLPFC_left",
            electrode_placement={"anode": (0, 0), "cathode": (1, 1)},
            safety_bounds={"current": (0.5, 2.0)}
        )
        
        with pytest.raises(ValueError, match="outside safe range"):
            await agent.start_closed_loop_session(
                "patient_002",
                unsafe_params,
                target_band="alpha"
            )
    
    @pytest.mark.asyncio
    async def test_session_rejects_excessive_duration(self, agent):
        """Test that excessive duration is rejected"""
        excessive_params = StimulationParameters(
            stimulation_type=StimulationType.TDCS,
            current_ma=1.5,
            frequency_hz=None,
            duration_minutes=60,  # Too long!
            target_region="DLPFC_left",
            electrode_placement={"anode": (0, 0), "cathode": (1, 1)},
            safety_bounds={"current": (0.5, 2.0)}
        )
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            await agent.start_closed_loop_session(
                "patient_003",
                excessive_params,
                target_band="alpha"
            )
    
    @pytest.mark.asyncio
    async def test_session_update(self, agent):
        """Test updating session with new EEG data"""
        stim_params = StimulationParameters(
            stimulation_type=StimulationType.TDCS,
            current_ma=1.5,
            frequency_hz=None,
            duration_minutes=5,  # Short session for testing
            target_region="DLPFC_left",
            electrode_placement={"anode": (0, 0), "cathode": (1, 1)},
            safety_bounds={"current": (0.5, 2.0)}
        )
        
        session_id = await agent.start_closed_loop_session(
            "patient_004",
            stim_params,
            target_band="alpha"
        )
        
        # Update with new EEG data
        eeg_data = generate_mock_eeg_data(duration_seconds=10)
        update_result = await agent.update_session(session_id, eeg_data)
        
        assert 'session_id' in update_result
        assert 'status' in update_result
        assert 'current_ma' in update_result
        assert 0.5 <= update_result['current_ma'] <= 2.0
    
    @pytest.mark.asyncio
    async def test_session_completion(self, agent):
        """Test session stop and summary"""
        stim_params = StimulationParameters(
            stimulation_type=StimulationType.TDCS,
            current_ma=1.5,
            frequency_hz=None,
            duration_minutes=5,
            target_region="DLPFC_left",
            electrode_placement={"anode": (0, 0), "cathode": (1, 1)},
            safety_bounds={"current": (0.5, 2.0)}
        )
        
        session_id = await agent.start_closed_loop_session(
            "patient_005",
            stim_params,
            target_band="alpha"
        )
        
        # Perform a few updates
        for _ in range(3):
            eeg_data = generate_mock_eeg_data(duration_seconds=5)
            await agent.update_session(session_id, eeg_data)
        
        # Stop session
        summary = await agent.stop_session(session_id)
        
        assert 'session_id' in summary
        assert 'num_adjustments' in summary
        assert summary['num_adjustments'] >= 3
        
        # Session should be removed
        assert session_id not in agent.active_sessions


def test_mock_eeg_generation():
    """Test mock EEG data generation"""
    eeg_data = generate_mock_eeg_data(duration_seconds=10, fs=256)
    
    assert len(eeg_data) == 10 * 256  # 10 seconds at 256 Hz
    assert isinstance(eeg_data, np.ndarray)
    assert eeg_data.dtype in [np.float64, np.float32]


def test_stimulation_type_enum():
    """Test stimulation type enumeration"""
    assert StimulationType.TDCS.value == "tdcs"
    assert StimulationType.RTMS.value == "rtms"
