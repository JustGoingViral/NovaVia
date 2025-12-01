"""
Phase 1 Tests: Pharmacogenomics Panel

Tests for CPIC-based dose adjustments and PGx modeling.
"""

import pytest
import numpy as np

try:
    from irip.agents.pgx_panel_simulator import (
        PharmacogenomicsPanel,
        PharmacogenomicProfile,
        MetabolizerStatus,
        CYP2C19Phenotype,
        CYP3A4Activity,
        COMTGenotype,
        BDNFGenotype,
        DoseAdjustment,
        generate_synthetic_pgx_profile
    )
    PGX_AVAILABLE = True
except ImportError:
    PGX_AVAILABLE = False


@pytest.mark.skipif(not PGX_AVAILABLE, reason="PGx module not available")
class TestPharmacogenomicsPanel:
    """Test suite for Pharmacogenomics Panel"""
    
    def test_hnk_dose_adjustment_poor_metabolizer(self):
        """Test HNK dose reduction for poor metabolizer"""
        profile = PharmacogenomicProfile(
            patient_id="PT001",
            cyp2b6_status=MetabolizerStatus.POOR,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.98,
            test_date="2024-12-01"
        )
        
        adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, profile)
        
        # Poor metabolizer should get reduced dose
        assert adjustment.adjusted_dose < 0.3
        assert adjustment.adjusted_dose >= 0.1  # Safety lower bound
        assert adjustment.adjustment_factor < 1.0
        assert "CYP2B6" in adjustment.rationale
        assert "poor" in adjustment.rationale.lower()
    
    def test_hnk_dose_adjustment_ultra_rapid(self):
        """Test HNK dose increase for ultra-rapid metabolizer"""
        profile = PharmacogenomicProfile(
            patient_id="PT002",
            cyp2b6_status=MetabolizerStatus.ULTRA_RAPID,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.HIGH,
            comt_genotype=COMTGenotype.MET_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.95,
            test_date="2024-12-01"
        )
        
        adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, profile)
        
        # Ultra-rapid metabolizer may need higher dose
        assert adjustment.adjusted_dose >= 0.3
        assert adjustment.adjusted_dose <= 0.5  # Safety upper bound
    
    def test_hnk_dose_safety_bounds(self):
        """Test that adjusted doses stay within safety bounds (0.1-0.5 mg/kg)"""
        # Test extreme case
        profile = PharmacogenomicProfile(
            patient_id="PT003",
            cyp2b6_status=MetabolizerStatus.POOR,
            cyp2c19_phenotype=CYP2C19Phenotype.POOR,
            cyp3a4_activity=CYP3A4Activity.LOW,
            comt_genotype=COMTGenotype.VAL_VAL,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.90,
            test_date="2024-12-01"
        )
        
        adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, profile)
        
        # Must be within safety bounds
        assert 0.1 <= adjustment.adjusted_dose <= 0.5
    
    def test_bdnf_response_prediction(self):
        """Test BDNF genotype affects neuroplasticity response prediction"""
        profile_val_val = PharmacogenomicProfile(
            patient_id="PT004",
            cyp2b6_status=MetabolizerStatus.NORMAL,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.95,
            test_date="2024-12-01"
        )
        
        profile_met_met = PharmacogenomicProfile(
            patient_id="PT005",
            cyp2b6_status=MetabolizerStatus.NORMAL,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.MET_MET,
            confidence_score=0.95,
            test_date="2024-12-01"
        )
        
        adj_val_val = PharmacogenomicsPanel.adjust_hnk_dose(0.3, profile_val_val)
        adj_met_met = PharmacogenomicsPanel.adjust_hnk_dose(0.3, profile_met_met)
        
        # Met/Met should have warning about reduced response
        assert "BDNF" in adj_met_met.rationale
        assert "reduced" in adj_met_met.rationale.lower()
    
    def test_ssri_dose_adjustment_poor_metabolizer(self):
        """Test SSRI dose adjustment for CYP2C19 poor metabolizer"""
        profile = PharmacogenomicProfile(
            patient_id="PT006",
            cyp2b6_status=MetabolizerStatus.NORMAL,
            cyp2c19_phenotype=CYP2C19Phenotype.POOR,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.98,
            test_date="2024-12-01"
        )
        
        adjustment = PharmacogenomicsPanel.adjust_ssri_dose("Escitalopram", 10.0, profile)
        
        # Poor metabolizers need 50% dose reduction per CPIC
        assert adjustment.adjusted_dose == 5.0
        assert adjustment.adjustment_factor == 0.5
        assert adjustment.evidence_level == "1A"  # Strong evidence
    
    def test_neuroplasticity_response_prediction(self):
        """Test combined BDNF/COMT neuroplasticity response prediction"""
        # Best case: Val/Val BDNF + Met/Met COMT
        response = PharmacogenomicsPanel.predict_neuroplasticity_response(
            BDNFGenotype.VAL_VAL,
            COMTGenotype.MET_MET
        )
        
        assert response['expected_response_modifier'] >= 0.9
        assert len(response['recommendations']) >= 0
        
        # Worst case: Met/Met BDNF + Val/Val COMT
        response_poor = PharmacogenomicsPanel.predict_neuroplasticity_response(
            BDNFGenotype.MET_MET,
            COMTGenotype.VAL_VAL
        )
        
        assert response_poor['expected_response_modifier'] < response['expected_response_modifier']
        assert len(response_poor['recommendations']) > 0
        assert any('augmentation' in rec.lower() for rec in response_poor['recommendations'])
    
    def test_federated_pgx_score(self):
        """Test composite PGx score for federated learning"""
        profile = PharmacogenomicProfile(
            patient_id="PT007",
            cyp2b6_status=MetabolizerStatus.NORMAL,
            cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
            cyp3a4_activity=CYP3A4Activity.NORMAL,
            comt_genotype=COMTGenotype.VAL_MET,
            bdnf_genotype=BDNFGenotype.VAL_VAL,
            confidence_score=0.95,
            test_date="2024-12-01"
        )
        
        score = PharmacogenomicsPanel.generate_federated_pgx_score(profile)
        
        # Score should be in valid range
        assert 0 <= score <= 1
        assert isinstance(score, float)
    
    def test_synthetic_profile_generation(self):
        """Test synthetic PGx profile generator"""
        profile = generate_synthetic_pgx_profile("patient_test_123", population="european")
        
        assert profile.patient_id == "patient_test_123"
        assert isinstance(profile.cyp2b6_status, MetabolizerStatus)
        assert isinstance(profile.cyp2c19_phenotype, CYP2C19Phenotype)
        assert isinstance(profile.cyp3a4_activity, CYP3A4Activity)
        assert isinstance(profile.comt_genotype, COMTGenotype)
        assert isinstance(profile.bdnf_genotype, BDNFGenotype)
        assert 0.85 <= profile.confidence_score <= 1.0
    
    def test_dose_adjustment_within_bounds(self):
        """Test all dose adjustments stay within 0.1-2.0 mg/kg range"""
        # Test multiple scenarios
        metabolizer_statuses = list(MetabolizerStatus)
        
        for status in metabolizer_statuses:
            profile = PharmacogenomicProfile(
                patient_id=f"PT_{status.value}",
                cyp2b6_status=status,
                cyp2c19_phenotype=CYP2C19Phenotype.NORMAL,
                cyp3a4_activity=CYP3A4Activity.NORMAL,
                comt_genotype=COMTGenotype.VAL_MET,
                bdnf_genotype=BDNFGenotype.VAL_VAL,
                confidence_score=0.95,
                test_date="2024-12-01"
            )
            
            adjustment = PharmacogenomicsPanel.adjust_hnk_dose(0.3, profile)
            
            # Must be within safety bounds
            assert 0.1 <= adjustment.adjusted_dose <= 2.0, \
                f"Dose {adjustment.adjusted_dose} out of bounds for {status.value}"


def test_metabolizer_status_enum():
    """Test metabolizer status enumeration"""
    assert MetabolizerStatus.POOR.value == "poor"
    assert MetabolizerStatus.ULTRA_RAPID.value == "ultra_rapid"


def test_bdnf_genotype_enum():
    """Test BDNF genotype enumeration"""
    assert BDNFGenotype.VAL_VAL.value == "Val/Val"
    assert BDNFGenotype.MET_MET.value == "Met/Met"
