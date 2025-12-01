"""
Phase 1 Tests: Digital Biomarkers Agent

Tests for passive monitoring, relapse prediction, and LSTM model.
"""

import pytest
import numpy as np
import pandas as pd
import asyncio
from datetime import datetime, timedelta

# Mock imports during testing (install with: pip install torch pandas)
try:
    from irip.agents.digital_biomarkers_agent import (
        DigitalBiomarkersAgent,
        BiomarkerReading,
        BiomarkerType,
        RelapseRiskLevel,
        generate_mock_fitbit_data
    )
    BIOMARKERS_AVAILABLE = True
except ImportError:
    BIOMARKERS_AVAILABLE = False


@pytest.mark.skipif(not BIOMARKERS_AVAILABLE, reason="PyTorch not installed")
class TestDigitalBiomarkersAgent:
    """Test suite for Digital Biomarkers Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = DigitalBiomarkersAgent()
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.agent_id == "digital_biomarkers_agent"
        assert agent.state == "ready"
        assert agent.model is not None
    
    @pytest.mark.asyncio
    async def test_forecast_relapse_high_risk(self, agent):
        """Test relapse forecasting with high-risk pattern"""
        # Create time series with declining sleep and activity
        n_days = 7
        hours = n_days * 24
        
        data = {
            'sleep_efficiency': np.linspace(0.85, 0.55, hours),  # Declining
            'activity_level': np.linspace(0.7, 0.3, hours),      # Declining
            'hrv': np.linspace(60, 30, hours)                    # Declining
        }
        
        df = pd.DataFrame(data)
        result = await agent.forecast_relapse(df)
        
        # Assertions
        assert 'risk' in result
        assert 'alert' in result
        assert 'alertreason' in result
        assert 0 <= result['risk'] <= 1
        assert isinstance(result['95_ci'], list)
        assert len(result['95_ci']) == 2
        
        # High risk should be detected
        assert result['risk'] > 0.3  # Expect elevated risk
    
    @pytest.mark.asyncio
    async def test_forecast_relapse_low_risk(self, agent):
        """Test relapse forecasting with healthy pattern"""
        n_days = 7
        hours = n_days * 24
        
        # Healthy stable patterns
        data = {
            'sleep_efficiency': np.full(hours, 0.85) + np.random.normal(0, 0.02, hours),
            'activity_level': np.full(hours, 0.7) + np.random.normal(0, 0.05, hours),
            'hrv': np.full(hours, 55) + np.random.normal(0, 3, hours)
        }
        
        df = pd.DataFrame(data)
        result = await agent.forecast_relapse(df)
        
        # Low risk expected
        assert result['risk'] < 0.5
        assert not result['alert'] or result['risk'] < 0.3
    
    @pytest.mark.asyncio
    async def test_sleep_efficiency_alert_trigger(self, agent):
        """Test that low sleep efficiency triggers alert"""
        n_days = 7
        hours = n_days * 24
        
        # Low sleep efficiency (< 70% threshold)
        data = {
            'sleep_efficiency': np.full(hours, 0.60),  # Below threshold
            'activity_level': np.full(hours, 0.7),
            'hrv': np.full(hours, 50)
        }
        
        df = pd.DataFrame(data)
        result = await agent.forecast_relapse(df)
        
        # Alert should be triggered
        assert result['alert'] == True
        assert 'sleep' in result.get('alert_reason', '').lower() or result['risk'] > 0.5
    
    @pytest.mark.asyncio
    async def test_assess_relapse_risk(self, agent):
        """Test comprehensive risk assessment"""
        # Generate mock readings
        readings = generate_mock_fitbit_data(days=7)
        patient_id = readings[0].patient_id
        
        assessment = await agent.assess_relapse_risk(patient_id, readings)
        
        # Verify assessment structure
        assert assessment.patient_id == patient_id
        assert isinstance(assessment.risk_score, float)
        assert 0 <= assessment.risk_score <= 1
        assert isinstance(assessment.risk_level, RelapseRiskLevel)
        assert len(assessment.confidence_interval_95) == 2
        assert isinstance(assessment.contributing_factors, dict)
        assert isinstance(assessment.recommended_actions, list)
        assert len(assessment.recommended_actions) > 0
    
    @pytest.mark.asyncio
    async def test_contributing_factors_analysis(self, agent):
        """Test identification of contributing risk factors"""
        readings = []
        patient_id = "test_patient"
        base_time = datetime.now()
        
        # Add readings with known poor patterns
        for i in range(7):
            # Very low sleep efficiency
            readings.append(BiomarkerReading(
                patient_id=patient_id,
                timestamp=base_time + timedelta(days=i),
                biomarker_type=BiomarkerType.SLEEP_EFFICIENCY,
                value=0.50,  # Very low
                unit="proportion",
                quality_score=0.95,
                source_device="Fitbit"
            ))
            
            # Low activity
            readings.append(BiomarkerReading(
                patient_id=patient_id,
                timestamp=base_time + timedelta(days=i),
                biomarker_type=BiomarkerType.ACTIVITY_LEVEL,
                value=0.2,  # Very low
                unit="normalized",
                quality_score=0.95,
                source_device="Fitbit"
            ))
        
        assessment = await agent.assess_relapse_risk(patient_id, readings)
        
        # Should identify sleep and activity as contributing factors
        factors = assessment.contributing_factors
        assert 'sleep_disruption' in factors or 'low_activity' in factors
        
        # Check recommendations address the factors
        recommendations = assessment.recommended_actions
        assert any('sleep' in rec.lower() or 'activity' in rec.lower() 
                  for rec in recommendations)
    
    def test_mock_data_generation(self):
        """Test mock Fitbit data generator"""
        readings = generate_mock_fitbit_data(days=7)
        
        assert len(readings) > 0
        assert len(readings) == 7 * 3  # 3 readings per day
        
        # Check data types
        for reading in readings:
            assert isinstance(reading, BiomarkerReading)
            assert reading.patient_id == "patient_test_001"
            assert 0 <= reading.value
            assert 0 <= reading.quality_score <= 1


def test_biomarker_types():
    """Test biomarker type enumeration"""
    assert BiomarkerType.SLEEP_EFFICIENCY.value == "sleep_efficiency"
    assert BiomarkerType.HEART_RATE_VARIABILITY.value == "heart_rate_variability"


def test_risk_level_classification():
    """Test risk level enum"""
    assert RelapseRiskLevel.VERY_LOW.value == "very_low"
    assert RelapseRiskLevel.VERY_HIGH.value == "very_high"
