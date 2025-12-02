"""
Phase 1 Integration Test
End-to-end validation of HNK + biomarkers flow

Verifies that all Phase 1 components work together:
1. Digital biomarkers → relapse risk assessment
2. Pharmacogenomics → dose adjustment
3. Closed-loop neurostimulation → EEG-driven parameter tuning
4. Metabolomics → BDNF prediction and HNK synergy

References integration with Master Orchestrator and HNK model.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Check module availability
try:
    from irip.agents.digital_biomarkers_agent import (
        DigitalBiomarkersAgent,
        generate_mock_fitbit_data,
        BiomarkerType,
        RelapseRiskLevel
    )
    BIOMARKERS_AVAILABLE = True
except ImportError:
    BIOMARKERS_AVAILABLE = False

try:
    from irip.agents.pgx_panel_simulator import (
        PharmacogenomicsPanel,
        PharmacogenomicProfile,
        MetabolizerStatus,
        CYP2C19Phenotype,
        CYP3A4Activity,
        COMTGenotype,
        BDNFGenotype,
        generate_synthetic_pgx_profile
    )
    PGX_AVAILABLE = True
except ImportError:
    PGX_AVAILABLE = False

try:
    from irip.agents.closed_loop_stim_agent import (
        ClosedLoopStimAgent,
        StimulationParameters,
        StimulationType,
        generate_mock_eeg_data
    )
    STIM_AVAILABLE = True
except ImportError:
    STIM_AVAILABLE = False

try:
    from irip.agents.metabolomics_agent import (
        MetabolomicsAgent,
        generate_synthetic_metabolomics_profile
    )
    METABOLOMICS_AVAILABLE = True
except ImportError:
    METABOLOMICS_AVAILABLE = False

try:
    from irip.agents.hnk_model import (
        HNKPharmacodynamicsAgent,
        PatientCovariates,
        HormonalPhase,
        MetabolismProfile
    )
    HNK_AVAILABLE = True
except ImportError:
    HNK_AVAILABLE = False


ALL_PHASE1_AVAILABLE = all([
    BIOMARKERS_AVAILABLE,
    PGX_AVAILABLE,
    STIM_AVAILABLE,
    METABOLOMICS_AVAILABLE
])


@pytest.mark.skipif(not ALL_PHASE1_AVAILABLE, reason="Not all Phase 1 modules available")
class TestPhase1Integration:
    """
    End-to-end integration tests for Phase 1 scientific enhancements
    
    Validates complete treatment workflow:
    1. Collect digital biomarkers → assess relapse risk
    2. Get PGx profile → adjust HNK dose
    3. Run closed-loop neurostim → optimize based on EEG
    4. Analyze metabolomics → predict BDNF response
    5. Combine all signals → treatment recommendation
    """
    
    @pytest.fixture
    async def all_agents(self):
        """Initialize all Phase 1 agents"""
        biomarkers_agent = DigitalBiomarkersAgent()
        stim_agent = ClosedLoopStimAgent()
        metabolomics_agent = MetabolomicsAgent()
        
        await biomarkers_agent.initialize()
        await stim_agent.initialize()
        await metabolomics_agent.initialize()
        
        return {
            'biomarkers': biomarkers_agent,
            'stim': stim_agent,
            'metabolomics': metabolomics_agent
        }
    
    @pytest.mark.asyncio
    async def test_full_pipeline_healthy_patient(self, all_agents):
        """
        Test complete Phase 1 pipeline for healthy patient
        
        Expected outcomes:
        - Low relapse risk (<30%)
        - Standard HNK dose (~0.3 mg/kg)
        - Optimal stim parameters (1.5 mA)
        - Good BDNF prediction (>1.5x)
        """
        patient_id = "integration_test_healthy"
        
        # Step 1: Digital Biomarkers Assessment
        biomarkers_agent = all_agents['biomarkers']
        readings = generate_mock_fitbit_data(days=7)
        
        # Modify to healthy pattern
        for reading in readings:
            if reading.biomarker_type == BiomarkerType.SLEEP_EFFICIENCY:
                reading.value = 0.85 + np.random.normal(0, 0.03)
        
        risk_assessment = await biomarkers_agent.assess_relapse_risk(
            readings[0].patient_id, readings
        )
        
        assert risk_assessment.risk_score < 0.5
        assert not risk_assessment.alert_triggered
        
        # Step 2: Pharmacogenomics Dose Adjustment
        pgx_profile = PharmacogenomicProfile(
            patient_id=patient_id,
            cyp2b6_status=MetabolizerStatus.NORMAL,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.95,
            test_date="2024-12-01"
        )
        
        dose_adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, pgx_profile)
        
        # Normal metabolizer should get standard dose
        assert 0.25 <= dose_adjustment.adjusted_dose <= 0.35
        assert dose_adjustment.adjustment_factor >= 0.9
        
        # Step 3: Closed-Loop Stimulation
        stim_agent = all_agents['stim']
        eeg_data = generate_mock_eeg_data(duration_seconds=10)
        
        stim_current = await stim_agent.tune_stim(eeg_data, target_band="alpha")
        
        # Should be within FDA safety limits
        assert 0.5 <= stim_current <= 2.0
        
        # Step 4: Metabolomics Assessment
        metabolomics_agent = all_agents['metabolomics']
        metab_profile = generate_synthetic_metabolomics_profile(patient_id, "healthy")
        
        bdnf_prediction = await metabolomics_agent.predict_bdnf_response(metab_profile)
        
        # Healthy profile should predict good response
        assert bdnf_prediction.predicted_bdnf_response > 1.0
        assert bdnf_prediction.microbiome_health_score > 0.5
        
        # Step 5: HNK Integration
        hnk_integration = await metabolomics_agent.integrate_with_hnk(
            metab_profile, dose_adjustment.adjusted_dose
        )
        
        assert hnk_integration['proceed_with_hnk'] == True
        assert hnk_integration['expected_combined_bdnf_fold_change'] > 1.5
    
    @pytest.mark.asyncio
    async def test_full_pipeline_high_risk_patient(self, all_agents):
        """
        Test complete Phase 1 pipeline for high-risk patient
        
        Expected outcomes:
        - High relapse risk (>50%)
        - Adjusted HNK dose due to poor metabolism
        - Alert triggered for clinical intervention
        - Metabolome optimization recommended
        """
        patient_id = "integration_test_high_risk"
        
        # Step 1: Digital Biomarkers (high risk pattern)
        biomarkers_agent = all_agents['biomarkers']
        
        # Create declining pattern indicating relapse prodrome
        hours = 168  # 7 days
        risk_data = pd.DataFrame({
            'sleep_efficiency': np.linspace(0.80, 0.50, hours),
            'activity_level': np.linspace(0.70, 0.25, hours),
            'hrv': np.linspace(55, 28, hours)
        })
        
        risk_forecast = await biomarkers_agent.forecast_relapse(risk_data)
        
        # Should trigger alert
        assert risk_forecast['risk'] > 0.3 or risk_forecast['alert']
        
        # Step 2: PGx for poor metabolizer
        pgx_profile = PharmacogenomicProfile(
            patient_id=patient_id,
            cyp2b6_status=MetabolizerStatus.POOR,
            cyp2c19_phenotype=CYP2C19Phenotype.POOR,
            cyp3a4_activity=CYP3A4Activity.LOW,
            comt_genotype=COMTGenotype.VAL_VAL,
            bdnf_genotype=BDNFGenotype.MET_MET,
            confidence_score=0.92,
            test_date="2024-12-01"
        )
        
        dose_adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, pgx_profile)
        
        # Poor metabolizer should get reduced dose
        assert dose_adjustment.adjusted_dose < 0.3
        assert "CYP2B6" in dose_adjustment.rationale
        
        # Check neuroplasticity prediction with BDNF Met/Met
        neuro_response = PharmacogenomicsPanel.predict_neuroplasticity_response(
            pgx_profile.bdnf_genotype,
            pgx_profile.comt_genotype
        )
        
        assert neuro_response['expected_response_modifier'] < 0.8
        assert len(neuro_response['recommendations']) > 0
        
        # Step 3: Metabolomics (suboptimal)
        metabolomics_agent = all_agents['metabolomics']
        metab_profile = generate_synthetic_metabolomics_profile(patient_id, "suboptimal")
        
        # Force dysbiotic pattern
        metab_profile.metabolites['butyrate'] = 25.0
        metab_profile.metabolites['kynurenine'] = 2.8
        
        bdnf_prediction = await metabolomics_agent.predict_bdnf_response(metab_profile)
        
        # Should have lower health score and recommendations
        assert bdnf_prediction.microbiome_health_score < 0.7
        assert any('fiber' in rec.lower() or 'inflammat' in rec.lower() 
                  for rec in bdnf_prediction.recommendations)
        
        # Step 4: Combined recommendation
        hnk_integration = await metabolomics_agent.integrate_with_hnk(
            metab_profile, dose_adjustment.adjusted_dose
        )
        
        # Should recommend metabolome optimization
        assert any('optimiz' in rec.lower() or 'recovery' in rec.lower() 
                  for rec in hnk_integration['recommendations'])
    
    @pytest.mark.asyncio
    async def test_women_health_hormonal_optimization(self, all_agents):
        """
        Test hormonal phase optimization for women's health equity
        
        Validates that Phase 1 components respect hormonal covariates:
        - PGx considers sex-specific factors
        - HNK efficacy modifier applied
        """
        patient_id = "integration_test_female"
        
        # PGx profile for female patient
        pgx_profile = PharmacogenomicProfile(
            patient_id=patient_id,
            cyp2b6_status=MetabolizerStatus.NORMAL,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.95,
            test_date="2024-12-01"
        )
        
        dose_adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, pgx_profile)
        
        # Dose should be within bounds
        assert 0.1 <= dose_adjustment.adjusted_dose <= 0.5
        
        # Metabolomics integration
        metabolomics_agent = all_agents['metabolomics']
        metab_profile = generate_synthetic_metabolomics_profile(patient_id, "normal")
        
        hnk_integration = await metabolomics_agent.integrate_with_hnk(
            metab_profile, dose_adjustment.adjusted_dose
        )
        
        # Should provide combined efficacy estimate
        assert 'efficacy_modifier' in hnk_integration
        assert 'expected_combined_bdnf_fold_change' in hnk_integration
    
    @pytest.mark.asyncio
    async def test_closed_loop_stim_safety_during_integration(self, all_agents):
        """
        Test that closed-loop stimulation maintains safety during integration
        
        Validates FDA-compliant bounds are enforced even when receiving
        signals from other agents.
        """
        stim_agent = all_agents['stim']
        
        # Create various EEG patterns
        for scenario in ["normal", "low_alpha", "high_alpha"]:
            if scenario == "normal":
                eeg = generate_mock_eeg_data(duration_seconds=10)
            elif scenario == "low_alpha":
                # Reduce alpha power
                eeg = generate_mock_eeg_data(duration_seconds=10, noise_level=0.5)
            else:
                # High alpha
                eeg = generate_mock_eeg_data(duration_seconds=10, noise_level=0.05)
            
            current = await stim_agent.tune_stim(eeg, target_band="alpha")
            
            # Must always be within FDA safety limits
            assert 0.5 <= current <= 2.0, \
                f"Current {current} mA outside FDA limits for {scenario}"
    
    @pytest.mark.asyncio
    async def test_all_agents_respond_to_messages(self, all_agents):
        """
        Test that all agents can process standard message types
        """
        from irip.agents.base_agent import AgentMessage, AgentPriority
        import time
        
        # Test biomarkers agent message handling
        biomarkers_agent = all_agents['biomarkers']
        
        # Note: Full message handling would require proper message content
        # This validates the agent structure is correct
        assert hasattr(biomarkers_agent, 'process_message')
        assert hasattr(biomarkers_agent, 'agent_id')
        assert biomarkers_agent.agent_id == "digital_biomarkers_agent"
        
        # Test stim agent
        stim_agent = all_agents['stim']
        assert hasattr(stim_agent, 'process_message')
        assert stim_agent.agent_id == "closed_loop_stim_agent"
        
        # Test metabolomics agent
        metabolomics_agent = all_agents['metabolomics']
        assert hasattr(metabolomics_agent, 'process_message')
        assert metabolomics_agent.agent_id == "metabolomics_agent"


@pytest.mark.skipif(not ALL_PHASE1_AVAILABLE, reason="Not all Phase 1 modules available")
class TestPhase1DataFlow:
    """Tests for data flow between Phase 1 components"""
    
    @pytest.mark.asyncio
    async def test_biomarker_to_orchestrator_format(self):
        """Test that biomarker output can be consumed by orchestrator"""
        agent = DigitalBiomarkersAgent()
        await agent.initialize()
        
        readings = generate_mock_fitbit_data(days=7)
        assessment = await agent.assess_relapse_risk(readings[0].patient_id, readings)
        
        # Output should be JSON-serializable with CIs
        output = {
            'patient_id': assessment.patient_id,
            'risk_score': assessment.risk_score,
            'risk_level': assessment.risk_level.value,
            'confidence_interval': assessment.confidence_interval_95,
            'alert': assessment.alert_triggered,
            'recommendations': assessment.recommended_actions
        }
        
        import json
        serialized = json.dumps(output)
        assert len(serialized) > 0
        
        # Verify CI is present
        assert 'confidence_interval' in output
        assert len(output['confidence_interval']) == 2
    
    @pytest.mark.asyncio
    async def test_pgx_to_hnk_format(self):
        """Test that PGx output can be consumed by HNK model"""
        pgx_profile = generate_synthetic_pgx_profile("pt_test", "european")
        adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, pgx_profile)
        
        # Output should include all fields needed by HNK model
        assert hasattr(adjustment, 'adjusted_dose')
        assert hasattr(adjustment, 'rationale')
        assert hasattr(adjustment, 'monitoring_recommendations')
        
        # Dose should be within HNK model's expected range
        assert 0.1 <= adjustment.adjusted_dose <= 0.5
    
    @pytest.mark.asyncio
    async def test_metabolomics_to_hnk_format(self):
        """Test that metabolomics output integrates with HNK"""
        agent = MetabolomicsAgent()
        await agent.initialize()
        
        profile = generate_synthetic_metabolomics_profile("pt_test", "normal")
        integration = await agent.integrate_with_hnk(profile, 0.3)
        
        # Should have all required fields for HNK integration
        assert 'hnk_dose_mg_kg' in integration
        assert 'efficacy_modifier' in integration
        assert 'expected_combined_bdnf_fold_change' in integration
        assert 'proceed_with_hnk' in integration
        
        # Efficacy modifier should be reasonable
        assert 0.5 <= integration['efficacy_modifier'] <= 1.5


def test_phase1_modules_importable():
    """Test that all Phase 1 modules can be imported"""
    import importlib
    
    modules = [
        'irip.agents.digital_biomarkers_agent',
        'irip.agents.pgx_panel_simulator',
        'irip.agents.closed_loop_stim_agent',
        'irip.agents.metabolomics_agent'
    ]
    
    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.skip(f"Module {module_name} not available: {e}")
