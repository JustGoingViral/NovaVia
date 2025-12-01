"""
HNK Week 5-8 Protocol Example
Demonstrates usage of HNK pharmacodynamics modeling for neuroplasticity interventions

This example shows how to use the HNK model for a typical patient during the
intensive neuroplasticity phase (Weeks 5-8) of addiction recovery treatment.
"""

import json
import sys
import os
import tempfile

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'irip', 'agents'))

from hnk_model import (
    HNKPharmacodynamicsAgent,
    PatientCovariates,
    MetabolismProfile,
    HormonalPhase,
    create_example_usage
)


def example_1_basic_dose_optimization():
    """Example 1: Basic dose optimization for a patient"""
    print("=" * 80)
    print("EXAMPLE 1: Basic HNK Dose Optimization")
    print("=" * 80)
    print()
    
    # Create HNK agent
    hnk_agent = HNKPharmacodynamicsAgent()
    
    # Define patient profile
    patient = PatientCovariates(
        body_weight_kg=68.0,
        age_years=38,
        sex="female",
        metabolism_profile=MetabolismProfile.NORMAL,
        hormonal_phase=HormonalPhase.FOLLICULAR,  # Optimal phase for neuroplasticity
        baseline_bdnf_ng_ml=14.0,
        depression_severity_score=0.75,
        liver_function_percent=95.0,
        renal_function_ml_min=90.0
    )
    
    print("Patient Profile:")
    print(f"  Weight: {patient.body_weight_kg} kg")
    print(f"  Age: {patient.age_years}")
    print(f"  Sex: {patient.sex}")
    print(f"  Metabolism: {patient.metabolism_profile.value}")
    print(f"  Hormonal Phase: {patient.hormonal_phase.value}")
    print(f"  Baseline BDNF: {patient.baseline_bdnf_ng_ml} ng/mL")
    print()
    
    # Calculate optimal dose
    optimal_result = hnk_agent.calculate_optimal_dose(patient, target_bdnf_increase=1.6)
    
    print("Optimal Dosing Recommendation:")
    print(json.dumps(optimal_result, indent=2))
    print()
    
    return optimal_result


def example_2_monte_carlo_variability():
    """Example 2: Monte Carlo simulation for treatment variability"""
    print("=" * 80)
    print("EXAMPLE 2: Monte Carlo Variability Analysis")
    print("=" * 80)
    print()
    
    hnk_agent = HNKPharmacodynamicsAgent()
    
    # Base patient profile
    base_patient = PatientCovariates(
        body_weight_kg=70.0,
        age_years=35,
        sex="female",
        metabolism_profile=MetabolismProfile.NORMAL,
        hormonal_phase=HormonalPhase.LUTEAL,
        baseline_bdnf_ng_ml=15.0,
        depression_severity_score=0.7
    )
    
    # Run Monte Carlo simulation
    print("Running 1000 simulations to assess inter-individual variability...")
    print()
    
    mc_results = hnk_agent.monte_carlo_simulation(
        dose_mg_kg=0.3,
        n_simulations=1000,
        base_patient=base_patient
    )
    
    print("Variability Analysis Results:")
    print(json.dumps(mc_results, indent=2))
    print()
    
    # Interpret results
    print("Clinical Interpretation:")
    print(f"  - Expected BDNF increase: {mc_results['bdnf_fold_increase']['mean']}x (±{mc_results['bdnf_fold_increase']['std']}x)")
    print(f"  - Responder rate: {mc_results['responder_rate_percent']}%")
    print(f"  - Variability range: {mc_results['bdnf_fold_increase']['percentile_25']}x to {mc_results['bdnf_fold_increase']['percentile_75']}x (IQR)")
    print()
    
    return mc_results


def example_3_full_treatment_protocol():
    """Example 3: Generate complete Week 5-8 treatment protocol"""
    print("=" * 80)
    print("EXAMPLE 3: Complete Week 5-8 Treatment Protocol")
    print("=" * 80)
    print()
    
    hnk_agent = HNKPharmacodynamicsAgent()
    
    # Postpartum patient example (special consideration)
    patient = PatientCovariates(
        body_weight_kg=62.0,
        age_years=29,
        sex="female",
        metabolism_profile=MetabolismProfile.NORMAL,
        hormonal_phase=HormonalPhase.POSTPARTUM_LOW_ESTROGEN,  # Requires dose adjustment
        baseline_bdnf_ng_ml=11.0,  # Lower due to postpartum
        depression_severity_score=0.85,  # Higher severity
        liver_function_percent=100.0,
        renal_function_ml_min=95.0
    )
    
    print("Patient: Postpartum woman with addiction history")
    print(f"  Hormonal Phase: {patient.hormonal_phase.value}")
    print(f"  Efficacy Modifier: {patient.get_hormonal_efficacy_modifier()}")
    print()
    
    # Generate protocol
    protocol = hnk_agent.generate_treatment_protocol(
        patient=patient,
        treatment_weeks=4  # Weeks 5-8
    )
    
    print("Treatment Protocol Summary:")
    print(f"  Duration: {protocol['duration_weeks']} weeks")
    print(f"  Total Sessions: {protocol['total_sessions']}")
    print(f"  Dosing Frequency: {protocol['dosing_frequency']}")
    print(f"  Optimal Dose: {protocol['optimal_dose_mg_kg']} mg/kg ({protocol['optimal_dose_mg_kg'] * patient.body_weight_kg:.1f} mg total)")
    print()
    
    print("Predicted Outcomes:")
    for key, value in protocol['predicted_outcomes'].items():
        print(f"  {key}: {value}")
    print()
    
    print("First 3 Sessions:")
    for session in protocol['sessions'][:3]:
        print(f"  Week {session['week']}, Session {session['session_number']}:")
        print(f"    Dose: {session['dose_mg']} mg IV over {session['infusion_duration_minutes']} minutes")
        print(f"    Monitoring: {', '.join(session['monitoring_required'][:3])}...")
    print()
    
    print("Biohacking Integration:")
    for device, timing in protocol['integration_with_biohacking'].items():
        print(f"  {device}: {timing}")
    print()
    
    if protocol.get('hormonal_considerations'):
        print("Hormonal Considerations:")
        print(f"  Current Phase: {protocol['hormonal_considerations']['current_phase']}")
        print(f"  Efficacy Modifier: {protocol['hormonal_considerations']['efficacy_modifier']}")
        print(f"  Recommendations: {protocol['hormonal_considerations']['recommendations']}")
        print()
    
    # Export to JSON for IRIP integration (cross-platform temp directory)
    output_file = os.path.join(tempfile.gettempdir(), "hnk_protocol_week5_8.json")
    hnk_agent.export_to_json(protocol, output_file)
    print(f"✓ Full protocol exported to: {output_file}")
    print()
    
    return protocol


def example_4_dose_response_visualization():
    """Example 4: Generate dose-response curves (visualization)"""
    print("=" * 80)
    print("EXAMPLE 4: Dose-Response Curve Visualization")
    print("=" * 80)
    print()
    
    hnk_agent = HNKPharmacodynamicsAgent()
    
    patient = PatientCovariates(
        body_weight_kg=75.0,
        age_years=42,
        sex="male",  # Also works for male patients
        metabolism_profile=MetabolismProfile.RAPID,  # Rapid metabolizer
        baseline_bdnf_ng_ml=13.0,
        depression_severity_score=0.6
    )
    
    print("Patient: Male patient with rapid metabolism")
    print(f"  Metabolism Factor: {patient.get_metabolism_factor()}")
    print()
    
    print("Generating dose-response curves...")
    print("  - Efficacy curves (BDNF increase, mood improvement)")
    print("  - Safety profile (dissociation risk)")
    print()
    
    # Generate and save curves (cross-platform temp directory)
    output_path = os.path.join(tempfile.gettempdir(), "hnk_dose_response_curves.png")
    hnk_agent.plot_dose_response_curves(patient, output_path=output_path)
    
    print(f"✓ Dose-response curves saved to: {output_path}")
    print()
    print("Key Observations:")
    print("  - HNK shows excellent efficacy with minimal dissociation risk")
    print("  - Optimal dose range: 0.2-0.4 mg/kg for most patients")
    print("  - Safety profile superior to traditional ketamine (5% vs 40-60% dissociation risk)")
    print()


def example_5_json_irip_integration():
    """Example 5: JSON output for IRIP agent integration"""
    print("=" * 80)
    print("EXAMPLE 5: JSON Output for IRIP Integration")
    print("=" * 80)
    print()
    
    hnk_agent = HNKPharmacodynamicsAgent()
    
    patient = PatientCovariates(
        body_weight_kg=65.0,
        age_years=34,
        sex="female",
        metabolism_profile=MetabolismProfile.NORMAL,
        hormonal_phase=HormonalPhase.OVULATORY,  # Peak efficacy
        baseline_bdnf_ng_ml=16.0,
        depression_severity_score=0.65
    )
    
    # Calculate optimal dose
    optimal_result = hnk_agent.calculate_optimal_dose(patient, target_bdnf_increase=1.7)
    
    # Create IRIP-compatible JSON output
    irip_output = {
        "patient_id": "patient_34_female_ovulatory",
        "protocol_type": "hnk_neuroplasticity_enhancement",
        "predicted_plasticity_score": optimal_result["predicted_mood_improvement_score"],
        "dissociation_risk": optimal_result["dissociation_risk"],
        "optimal_dose_mgkg": optimal_result["optimal_dose_mg_kg"],
        "optimal_dose_mg": optimal_result["optimal_dose_mg"],
        "predicted_bdnf_fold_increase": optimal_result["predicted_bdnf_fold_increase"],
        "predicted_ampa_activation_percent": optimal_result["predicted_ampa_activation_percent"],
        "onset_time_hours": optimal_result["onset_time_hours"],
        "duration_hours": optimal_result["duration_hours"],
        "safety_margin": optimal_result["safety_margin"],
        "hormonal_phase": patient.hormonal_phase.value,
        "efficacy_modifier": patient.get_hormonal_efficacy_modifier(),
        "monitoring_required": [
            "bdnf_levels",
            "mood_scales", 
            "eeg_patterns",
            "blood_pressure",
            "heart_rate"
        ],
        "biohacking_integration": {
            "pemf": "30_minutes_post_infusion",
            "eeg_monitoring": "continuous_during_and_2hrs_post",
            "red_light": "20_minutes_concurrent"
        }
    }
    
    print("IRIP-Compatible JSON Output:")
    print(json.dumps(irip_output, indent=2))
    print()
    
    # Save to file (cross-platform temp directory)
    output_file = os.path.join(tempfile.gettempdir(), "hnk_irip_output.json")
    hnk_agent.export_to_json(irip_output, output_file)
    print(f"✓ IRIP output exported to: {output_file}")
    print()
    
    return irip_output


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "HNK Week 5-8 Protocol Examples" + " " * 32 + "║")
    print("║" + " " * 10 + "Neuroplasticity-Based Addiction Recovery" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Run examples
    try:
        example_1_basic_dose_optimization()
        input("Press Enter to continue to Example 2...")
        print()
        
        example_2_monte_carlo_variability()
        input("Press Enter to continue to Example 3...")
        print()
        
        example_3_full_treatment_protocol()
        input("Press Enter to continue to Example 4...")
        print()
        
        example_4_dose_response_visualization()
        input("Press Enter to continue to Example 5...")
        print()
        
        example_5_json_irip_integration()
        
        print("=" * 80)
        print("All Examples Complete!")
        print("=" * 80)
        print()
        print("Next Steps:")
        print(f"  1. Review generated JSON files in {tempfile.gettempdir()}")
        print("  2. Examine dose-response curves visualization")
        print("  3. Integrate with IRIP medication and biohacking agents")
        print("  4. Deploy in clinical setting with proper monitoring")
        print()
        print("References:")
        print("  - Zanos et al. (2016). Nature, 533(7604), 481-486")
        print("  - Zanos et al. (2018). Molecular Psychiatry, 23(4), 801-811")
        print("  - Highland et al. (2019). Pharmacological Reviews, 71(4), 524-550")
        print()
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
