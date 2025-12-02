"""
Phase 2 Tests: Psychedelic Modeling Agent

Tests for safety screening, dose-response curves, and session protocols.
"""

import pytest
import numpy as np
import asyncio
from datetime import datetime, timedelta

try:
    from irip.agents.psychedelic_modeling_agent import (
        PsychedelicModelingAgent,
        PsychedelicType,
        SafetyScreening,
        DoseResponse,
        SessionProtocol,
        generate_synthetic_patient_data
    )
    PSYCHEDELIC_AVAILABLE = True
except ImportError:
    PSYCHEDELIC_AVAILABLE = False


@pytest.mark.skipif(not PSYCHEDELIC_AVAILABLE, reason="Psychedelic module not available")
class TestPsychedelicModelingAgent:
    """Test suite for Psychedelic Modeling Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = PsychedelicModelingAgent()
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes with MAPS protocols"""
        assert agent.agent_id == "psychedelic_modeling_agent"
        assert PsychedelicType.PSILOCYBIN in agent.STANDARD_DOSES
        assert agent.QTC_MAX_MALE_MS == 450
    
    def test_screen_protocol_cleared_patient(self, agent):
        """Test screening passes for eligible patient"""
        patient_data = {
            'qtc': 420,
            'sex': 'male',
            'psychosis_history': False,
            'family_psychosis_history': False,
            'bp_systolic': 120,
            'bp_diastolic': 75,
            'suicide_risk': 'low'
        }
        
        result = agent.screen_protocol(patient_data)
        assert result == True
    
    def test_screen_protocol_qtc_fail(self, agent):
        """Test screening fails for elevated QTc"""
        patient_data = {
            'qtc': 460,  # Exceeds male limit of 450
            'sex': 'male',
            'psychosis_history': False,
            'bp_systolic': 120,
            'bp_diastolic': 75
        }
        
        result = agent.screen_protocol(patient_data)
        assert result == False
    
    def test_screen_protocol_psychosis_fail(self, agent):
        """Test screening fails for psychosis history"""
        patient_data = {
            'qtc': 400,
            'sex': 'female',
            'psychosis_history': True,  # Absolute contraindication
            'bp_systolic': 120,
            'bp_diastolic': 75
        }
        
        result = agent.screen_protocol(patient_data)
        assert result == False
    
    def test_screen_protocol_female_qtc_limit(self, agent):
        """Test female QTc limit is higher (470ms)"""
        patient_data = {
            'qtc': 460,  # Exceeds male limit but not female
            'sex': 'female',
            'psychosis_history': False,
            'family_psychosis_history': False,
            'bp_systolic': 120,
            'bp_diastolic': 75,
            'suicide_risk': 'low'
        }
        
        result = agent.screen_protocol(patient_data)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_safety_screening_comprehensive(self, agent):
        """Test comprehensive safety screening"""
        patient_data = generate_synthetic_patient_data(cleared=True)
        
        screening = await agent.perform_safety_screening(
            "patient_test_001",
            patient_data,
            PsychedelicType.PSILOCYBIN
        )
        
        assert isinstance(screening, SafetyScreening)
        assert screening.patient_id == "patient_test_001"
        assert screening.cleared_for_treatment == True
        assert len(screening.contraindications) == 0 or all(
            c['severity'] == 'relative' for c in screening.contraindications
        )
    
    @pytest.mark.asyncio
    async def test_safety_screening_contraindicated(self, agent):
        """Test safety screening for contraindicated patient"""
        patient_data = generate_synthetic_patient_data(cleared=False)
        
        screening = await agent.perform_safety_screening(
            "patient_test_002",
            patient_data,
            PsychedelicType.PSILOCYBIN
        )
        
        assert screening.cleared_for_treatment == False
        assert len(screening.contraindications) > 0
        
        # Should have absolute contraindication (psychosis history)
        absolute = [c for c in screening.contraindications if c['severity'] == 'absolute']
        assert len(absolute) > 0
    
    @pytest.mark.asyncio
    async def test_medication_contraindication(self, agent):
        """Test medication contraindication detection"""
        patient_data = {
            'qtc': 400,
            'sex': 'male',
            'psychosis_history': False,
            'family_psychosis_history': False,
            'bp_systolic': 120,
            'bp_diastolic': 75,
            'medications': ['fluoxetine', 'sertraline'],  # SSRIs
            'suicide_risk': 'low'
        }
        
        screening = await agent.perform_safety_screening(
            "patient_test_003",
            patient_data,
            PsychedelicType.PSILOCYBIN
        )
        
        # Should have medication contraindication
        med_contras = [c for c in screening.contraindications 
                       if c['type'] == 'medication']
        assert len(med_contras) > 0
    
    @pytest.mark.asyncio
    async def test_dose_response_psilocybin(self, agent):
        """Test psilocybin dose-response prediction"""
        response = await agent.predict_dose_response(
            PsychedelicType.PSILOCYBIN,
            dose_mg=25.0,
            weight_kg=70.0
        )
        
        assert isinstance(response, DoseResponse)
        assert response.compound == PsychedelicType.PSILOCYBIN
        assert response.dose_mg == 25.0
        assert response.dose_mg_kg == pytest.approx(0.357, rel=0.01)
        
        # BDNF fold change should be in expected range (1.3-1.8x)
        assert 1.0 < response.predicted_bdnf_fold_change < 2.0
        
        # Timing estimates
        assert response.onset_hours == 0.5
        assert response.peak_hours == 2.0
        assert response.duration_hours == 6.0
    
    @pytest.mark.asyncio
    async def test_dose_response_mdma(self, agent):
        """Test MDMA dose-response prediction"""
        response = await agent.predict_dose_response(
            PsychedelicType.MDMA,
            dose_mg=120.0,
            weight_kg=70.0
        )
        
        assert response.compound == PsychedelicType.MDMA
        assert 1.0 < response.predicted_bdnf_fold_change < 1.6
        
        # Confidence interval should be present
        assert len(response.confidence_interval_95) == 2
        assert response.confidence_interval_95[0] < response.predicted_bdnf_fold_change
        assert response.confidence_interval_95[1] > response.predicted_bdnf_fold_change
    
    @pytest.mark.asyncio
    async def test_session_protocol_creation(self, agent):
        """Test MAPS-style session protocol creation"""
        scheduled = datetime.now() + timedelta(weeks=2)
        
        protocol = await agent.create_session_protocol(
            patient_id="patient_test_004",
            compound=PsychedelicType.PSILOCYBIN,
            dose_mg=25.0,
            scheduled_date=scheduled
        )
        
        assert isinstance(protocol, SessionProtocol)
        assert protocol.compound == PsychedelicType.PSILOCYBIN
        assert protocol.dose_mg == 25.0
        assert protocol.preparation_sessions >= 2
        assert protocol.integration_sessions >= 3
        
        # Setting requirements
        assert 'room_type' in protocol.setting_requirements
        assert 'emergency_equipment' in protocol.setting_requirements
        assert 'therapist_ratio' in protocol.setting_requirements
        
        # Emergency protocols
        assert len(protocol.emergency_protocols) >= 4
        assert 'psychotic_break_protocol' in protocol.emergency_protocols
    
    @pytest.mark.asyncio
    async def test_mystical_experience_prediction(self, agent):
        """Test MEQ30 score prediction"""
        response = await agent.predict_dose_response(
            PsychedelicType.PSILOCYBIN,
            dose_mg=25.0,
            weight_kg=70.0
        )
        
        # Standard dose should predict high MEQ score
        assert 0.5 < response.expected_mystical_experience_score <= 1.0
        
        # Low dose should predict lower MEQ
        low_response = await agent.predict_dose_response(
            PsychedelicType.PSILOCYBIN,
            dose_mg=10.0,
            weight_kg=70.0
        )
        
        assert low_response.expected_mystical_experience_score < response.expected_mystical_experience_score


def test_psychedelic_type_enum():
    """Test psychedelic type enumeration"""
    assert PsychedelicType.PSILOCYBIN.value == "psilocybin"
    assert PsychedelicType.MDMA.value == "mdma"


def test_synthetic_data_generation():
    """Test synthetic patient data generator"""
    cleared_data = generate_synthetic_patient_data(cleared=True)
    assert 'qtc' in cleared_data
    assert cleared_data['psychosis_history'] == False
    
    not_cleared = generate_synthetic_patient_data(cleared=False)
    assert not_cleared['psychosis_history'] == True
