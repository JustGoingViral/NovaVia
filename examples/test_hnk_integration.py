"""
Test HNK Integration with IRIP Agents
Verifies that HNK model integrates correctly with medication and biohacking agents
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'irip', 'agents'))

from hnk_model import (
    HNKPharmacodynamicsAgent,
    PatientCovariates,
    MetabolismProfile,
    HormonalPhase
)


def test_hnk_agent_initialization():
    """Test 1: HNK Agent Initialization"""
    print("Test 1: HNK Agent Initialization")
    try:
        agent = HNKPharmacodynamicsAgent()
        print("  ✓ HNK Agent initialized successfully")
        print(f"    - PK clearance: {agent.pk.clearance_ml_min_kg} mL/min/kg")
        print(f"    - Half-life: {agent.pk.half_life_hours} hours")
        print(f"    - EC50 BDNF: {agent.pd.ec50_bdnf_mg_kg} mg/kg")
        print(f"    - Dissociation risk: {agent.pd.dissociation_risk * 100}%")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_patient_covariates():
    """Test 2: Patient Covariates Creation"""
    print("\nTest 2: Patient Covariates Creation")
    try:
        patient = PatientCovariates(
            body_weight_kg=70.0,
            age_years=35,
            sex="female",
            metabolism_profile=MetabolismProfile.NORMAL,
            hormonal_phase=HormonalPhase.FOLLICULAR,
            baseline_bdnf_ng_ml=15.0,
            depression_severity_score=0.7
        )
        print("  ✓ Patient covariates created successfully")
        print(f"    - Metabolism factor: {patient.get_metabolism_factor()}")
        print(f"    - Hormonal efficacy modifier: {patient.get_hormonal_efficacy_modifier()}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_dose_optimization():
    """Test 3: Optimal Dose Calculation"""
    print("\nTest 3: Optimal Dose Calculation")
    try:
        agent = HNKPharmacodynamicsAgent()
        patient = PatientCovariates(
            body_weight_kg=65.0,
            age_years=32,
            sex="female",
            metabolism_profile=MetabolismProfile.NORMAL,
            hormonal_phase=HormonalPhase.POSTPARTUM_LOW_ESTROGEN,
            baseline_bdnf_ng_ml=12.0,
            depression_severity_score=0.8
        )
        
        result = agent.calculate_optimal_dose(patient, target_bdnf_increase=1.5)
        
        print("  ✓ Dose optimization completed")
        print(f"    - Optimal dose: {result['optimal_dose_mg_kg']} mg/kg")
        print(f"    - Total dose: {result['optimal_dose_mg']} mg")
        print(f"    - Predicted BDNF increase: {result['predicted_bdnf_fold_increase']}x")
        print(f"    - Predicted mood improvement: {result['predicted_mood_improvement_score']}")
        print(f"    - Dissociation risk: {result['dissociation_risk'] * 100}%")
        print(f"    - Safety margin: {result['safety_margin']}")
        
        # Validate results
        assert 0.05 <= result['optimal_dose_mg_kg'] <= 0.5, "Dose outside safe range"
        assert result['dissociation_risk'] <= 0.1, "Dissociation risk too high"
        assert result['safety_margin'] >= 0, "Negative safety margin"
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_monte_carlo_simulation():
    """Test 4: Monte Carlo Simulation"""
    print("\nTest 4: Monte Carlo Simulation")
    try:
        agent = HNKPharmacodynamicsAgent()
        patient = PatientCovariates(
            body_weight_kg=70.0,
            age_years=35,
            sex="female",
            baseline_bdnf_ng_ml=15.0
        )
        
        result = agent.monte_carlo_simulation(
            dose_mg_kg=0.3,
            n_simulations=100,  # Reduced for speed
            base_patient=patient
        )
        
        print("  ✓ Monte Carlo simulation completed")
        print(f"    - Simulations: {result['n_simulations']}")
        print(f"    - Mean BDNF increase: {result['bdnf_fold_increase']['mean']}x")
        print(f"    - BDNF variability (std): {result['bdnf_fold_increase']['std']}x")
        print(f"    - Responder rate: {result['responder_rate_percent']}%")
        
        # Validate results
        assert result['n_simulations'] == 100, "Wrong number of simulations"
        assert result['bdnf_fold_increase']['mean'] >= 1.0, "BDNF increase below baseline"
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_treatment_protocol_generation():
    """Test 5: Treatment Protocol Generation"""
    print("\nTest 5: Treatment Protocol Generation")
    try:
        agent = HNKPharmacodynamicsAgent()
        patient = PatientCovariates(
            body_weight_kg=68.0,
            age_years=38,
            sex="female",
            metabolism_profile=MetabolismProfile.NORMAL,
            hormonal_phase=HormonalPhase.FOLLICULAR,
            baseline_bdnf_ng_ml=14.0,
            depression_severity_score=0.7
        )
        
        protocol = agent.generate_treatment_protocol(patient, treatment_weeks=4)
        
        print("  ✓ Treatment protocol generated")
        print(f"    - Duration: {protocol['duration_weeks']} weeks")
        print(f"    - Total sessions: {protocol['total_sessions']}")
        print(f"    - Dosing frequency: {protocol['dosing_frequency']}")
        print(f"    - Optimal dose: {protocol['optimal_dose_mg_kg']} mg/kg")
        
        # Validate protocol structure
        assert protocol['duration_weeks'] == 4, "Wrong duration"
        assert protocol['total_sessions'] > 0, "No sessions scheduled"
        assert len(protocol['sessions']) == protocol['total_sessions'], "Session count mismatch"
        assert 'integration_with_biohacking' in protocol, "Missing biohacking integration"
        assert 'contraindications' in protocol, "Missing contraindications"
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_json_export():
    """Test 6: JSON Export for IRIP Integration"""
    print("\nTest 6: JSON Export for IRIP Integration")
    try:
        agent = HNKPharmacodynamicsAgent()
        patient = PatientCovariates(
            body_weight_kg=70.0,
            age_years=35,
            sex="female",
            hormonal_phase=HormonalPhase.OVULATORY,
            baseline_bdnf_ng_ml=16.0
        )
        
        result = agent.calculate_optimal_dose(patient)
        
        # Create IRIP output
        irip_output = {
            "predicted_plasticity_score": result["predicted_mood_improvement_score"],
            "dissociation_risk": result["dissociation_risk"],
            "optimal_dose_mgkg": result["optimal_dose_mg_kg"]
        }
        
        # Export to JSON
        output_file = "/tmp/test_hnk_irip_output.json"
        agent.export_to_json(irip_output, output_file)
        
        # Verify file exists and is valid JSON
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)
        
        print("  ✓ JSON export successful")
        print(f"    - Output file: {output_file}")
        print(f"    - Data keys: {list(loaded_data.keys())}")
        
        # Validate JSON structure
        assert 'predicted_plasticity_score' in loaded_data, "Missing plasticity score"
        assert 'dissociation_risk' in loaded_data, "Missing dissociation risk"
        assert 'optimal_dose_mgkg' in loaded_data, "Missing optimal dose"
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_hormonal_modulation():
    """Test 7: Hormonal Phase Modulation"""
    print("\nTest 7: Hormonal Phase Modulation")
    try:
        agent = HNKPharmacodynamicsAgent()
        
        # Test different hormonal phases
        phases = [
            HormonalPhase.FOLLICULAR,
            HormonalPhase.OVULATORY,
            HormonalPhase.LUTEAL,
            HormonalPhase.POSTPARTUM_LOW_ESTROGEN
        ]
        
        results = {}
        for phase in phases:
            patient = PatientCovariates(
                body_weight_kg=65.0,
                age_years=32,
                sex="female",
                hormonal_phase=phase,
                baseline_bdnf_ng_ml=14.0
            )
            
            result = agent.calculate_optimal_dose(patient)
            results[phase.value] = {
                "efficacy_modifier": patient.get_hormonal_efficacy_modifier(),
                "optimal_dose": result["optimal_dose_mg_kg"],
                "predicted_bdnf": result["predicted_bdnf_fold_increase"]
            }
        
        print("  ✓ Hormonal modulation tested")
        for phase, data in results.items():
            print(f"    - {phase}: efficacy={data['efficacy_modifier']}, dose={data['optimal_dose']} mg/kg")
        
        # Validate that hormonal phases affect efficacy
        assert results['follicular']['efficacy_modifier'] > results['postpartum_low_estrogen']['efficacy_modifier'], \
            "Follicular phase should have higher efficacy than postpartum"
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_metabolism_variability():
    """Test 8: Metabolism Profile Variability"""
    print("\nTest 8: Metabolism Profile Variability")
    try:
        agent = HNKPharmacodynamicsAgent()
        
        # Test different metabolism profiles
        profiles = [
            MetabolismProfile.SLOW,
            MetabolismProfile.NORMAL,
            MetabolismProfile.RAPID,
            MetabolismProfile.ULTRA_RAPID
        ]
        
        results = {}
        for profile in profiles:
            patient = PatientCovariates(
                body_weight_kg=70.0,
                age_years=35,
                metabolism_profile=profile,
                baseline_bdnf_ng_ml=15.0
            )
            
            result = agent.calculate_optimal_dose(patient)
            results[profile.value] = {
                "metabolism_factor": patient.get_metabolism_factor(),
                "optimal_dose": result["optimal_dose_mg_kg"]
            }
        
        print("  ✓ Metabolism variability tested")
        for profile, data in results.items():
            print(f"    - {profile}: factor={data['metabolism_factor']}, dose={data['optimal_dose']} mg/kg")
        
        # Validate metabolism factors
        assert results['slow']['metabolism_factor'] < results['rapid']['metabolism_factor'], \
            "Slow metabolism should have lower factor than rapid"
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("HNK Integration Test Suite")
    print("=" * 80)
    print()
    
    tests = [
        test_hnk_agent_initialization,
        test_patient_covariates,
        test_dose_optimization,
        test_monte_carlo_simulation,
        test_treatment_protocol_generation,
        test_json_export,
        test_hormonal_modulation,
        test_metabolism_variability
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n  ✗ Test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 80)
    
    if failed == 0:
        print("\n✓ All tests passed! HNK integration is working correctly.")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
