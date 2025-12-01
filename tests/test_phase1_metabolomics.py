"""
Phase 1 Tests: Metabolomics Agent

Tests for gut-brain axis analysis and BDNF correlation prediction.
"""

import pytest
import numpy as np
import asyncio

try:
    from irip.agents.metabolomics_agent import (
        MetabolomicsAgent,
        MetabolomicsProfile,
        MetaboliteType,
        BDNFPrediction,
        generate_synthetic_metabolomics_profile
    )
    METABOLOMICS_AVAILABLE = True
except ImportError:
    METABOLOMICS_AVAILABLE = False


@pytest.mark.skipif(not METABOLOMICS_AVAILABLE, reason="Metabolomics module not available")
class TestMetabolomicsAgent:
    """Test suite for Metabolomics Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = MetabolomicsAgent()
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes with trained model"""
        assert agent.agent_id == "metabolomics_agent"
        assert agent._is_trained == True
        assert agent.model is not None
    
    @pytest.mark.asyncio
    async def test_correlate_metabolites_healthy(self, agent):
        """Test metabolite correlation with healthy profile"""
        profiling = {
            'butyrate': 100.0,
            'propionate': 40.0,
            'acetate': 90.0,
            'kynurenine': 0.8,
            'gaba': 4.0,
            'firmicutes': 0.48,
            'bacteroidetes': 0.42
        }
        
        result = await agent.correlate_metabolites(profiling)
        
        assert 'bdnf_response' in result
        assert 'correlation_r' in result
        assert 'confidence' in result
        assert '95_ci' in result
        
        # Healthy profile should predict good BDNF response
        assert result['bdnf_response'] > 1.0
        assert result['correlation_r'] >= 0.6  # Target: r > 0.6
        assert len(result['95_ci']) == 2
    
    @pytest.mark.asyncio
    async def test_correlate_metabolites_suboptimal(self, agent):
        """Test metabolite correlation with suboptimal profile"""
        profiling = {
            'butyrate': 25.0,  # Low
            'propionate': 20.0,
            'acetate': 40.0,
            'kynurenine': 2.5,  # Elevated (inflammation)
            'gaba': 2.0,
            'firmicutes': 0.65,  # High
            'bacteroidetes': 0.30  # Low
        }
        
        result = await agent.correlate_metabolites(profiling)
        
        # Suboptimal profile should predict lower BDNF response
        assert result['bdnf_response'] < 1.5
        assert result['correlation_r'] < 0.7  # Inflammation reduces correlation
    
    @pytest.mark.asyncio
    async def test_predict_bdnf_response(self, agent):
        """Test comprehensive BDNF prediction"""
        profile = generate_synthetic_metabolomics_profile("patient_001", "healthy")
        
        prediction = await agent.predict_bdnf_response(profile)
        
        assert isinstance(prediction, BDNFPrediction)
        assert prediction.patient_id == "patient_001"
        assert 0.5 <= prediction.predicted_bdnf_response <= 3.0
        assert len(prediction.confidence_interval_95) == 2
        assert isinstance(prediction.contributing_metabolites, dict)
        assert 0.0 <= prediction.microbiome_health_score <= 1.0
        assert len(prediction.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_microbiome_health_score(self, agent):
        """Test microbiome health score calculation"""
        # Healthy profile
        healthy_profile = generate_synthetic_metabolomics_profile("pt_healthy", "healthy")
        healthy_pred = await agent.predict_bdnf_response(healthy_profile)
        
        # Dysbiotic profile
        dysbiotic_profile = generate_synthetic_metabolomics_profile("pt_dysbiotic", "dysbiotic")
        dysbiotic_pred = await agent.predict_bdnf_response(dysbiotic_profile)
        
        # Healthy should have higher score
        assert healthy_pred.microbiome_health_score > dysbiotic_pred.microbiome_health_score
    
    @pytest.mark.asyncio
    async def test_hnk_integration(self, agent):
        """Test integration with HNK dosing"""
        profile = generate_synthetic_metabolomics_profile("patient_002", "normal")
        
        result = await agent.integrate_with_hnk(profile, hnk_dose_mg_kg=0.3)
        
        assert 'hnk_dose_mg_kg' in result
        assert 'metabolome_bdnf_prediction' in result
        assert 'efficacy_modifier' in result
        assert 'expected_combined_bdnf_fold_change' in result
        assert 'proceed_with_hnk' in result
        assert 'recommendations' in result
        
        # Efficacy modifier should be reasonable
        assert 0.7 <= result['efficacy_modifier'] <= 1.3
        
        # Combined effect should be > HNK alone (synergy)
        assert result['expected_combined_bdnf_fold_change'] > 1.5
    
    @pytest.mark.asyncio
    async def test_recommendations_low_butyrate(self, agent):
        """Test that low butyrate triggers appropriate recommendations"""
        profile = generate_synthetic_metabolomics_profile("pt_low_butyrate", "suboptimal")
        # Force low butyrate
        profile.metabolites['butyrate'] = 20.0
        
        prediction = await agent.predict_bdnf_response(profile)
        
        # Should recommend fiber/probiotic
        recs = ' '.join(prediction.recommendations).lower()
        assert 'fiber' in recs or 'probiotic' in recs or 'butyrate' in recs
    
    @pytest.mark.asyncio
    async def test_recommendations_high_kynurenine(self, agent):
        """Test that high kynurenine triggers inflammation recommendations"""
        profile = generate_synthetic_metabolomics_profile("pt_inflamed", "suboptimal")
        # Force high kynurenine
        profile.metabolites['kynurenine'] = 3.0
        
        prediction = await agent.predict_bdnf_response(profile)
        
        # Should recommend anti-inflammatory
        recs = ' '.join(prediction.recommendations).lower()
        assert 'inflammat' in recs or 'omega' in recs
    
    @pytest.mark.asyncio
    async def test_antibiotics_penalty(self, agent):
        """Test that recent antibiotics reduces health score"""
        # Profile without antibiotics
        profile_clean = generate_synthetic_metabolomics_profile("pt_clean", "normal")
        profile_clean.antibiotics_recent = False
        
        # Profile with recent antibiotics
        profile_abx = generate_synthetic_metabolomics_profile("pt_clean", "normal")
        profile_abx.antibiotics_recent = True
        profile_abx.metabolites = profile_clean.metabolites.copy()
        profile_abx.microbiome_abundance = profile_clean.microbiome_abundance.copy()
        
        pred_clean = await agent.predict_bdnf_response(profile_clean)
        pred_abx = await agent.predict_bdnf_response(profile_abx)
        
        # Antibiotics should reduce health score
        assert pred_clean.microbiome_health_score > pred_abx.microbiome_health_score
    
    def test_synthetic_profile_generation(self):
        """Test synthetic profile generator"""
        for status in ["healthy", "normal", "suboptimal", "dysbiotic"]:
            profile = generate_synthetic_metabolomics_profile(f"pt_{status}", status)
            
            assert profile.patient_id == f"pt_{status}"
            assert 'butyrate' in profile.metabolites
            assert 'firmicutes' in profile.microbiome_abundance
            assert 0 < profile.quality_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_correlation_above_threshold(self, agent):
        """Test that butyrate-BDNF correlation exceeds r > 0.6 threshold"""
        # Use optimal butyrate range
        profiling = {
            'butyrate': 90.0,  # In optimal range (50-150)
            'propionate': 35.0,
            'acetate': 85.0,
            'kynurenine': 1.0,  # Low (healthy)
            'gaba': 4.5,
            'firmicutes': 0.45,
            'bacteroidetes': 0.42
        }
        
        result = await agent.correlate_metabolites(profiling)
        
        # Per Valles-Colomer et al. (2019), expect r > 0.6
        assert result['correlation_r'] >= 0.6, \
            f"Correlation {result['correlation_r']} below target 0.6"


def test_metabolite_type_enum():
    """Test metabolite type enumeration"""
    assert MetaboliteType.BUTYRATE.value == "butyrate"
    assert MetaboliteType.KYNURENINE.value == "kynurenine"


def test_reference_ranges():
    """Test that reference ranges are defined"""
    from irip.agents.metabolomics_agent import MetabolomicsAgent
    
    assert MetabolomicsAgent.BUTYRATE_OPTIMAL_RANGE == (50, 150)
    assert MetabolomicsAgent.KYNURENINE_HEALTHY_MAX == 2.0
