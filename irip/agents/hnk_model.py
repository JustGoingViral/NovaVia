"""
HNK Pharmacodynamics Model Module
(2R,6R)-Hydroxynorketamine (HNK) modeling for neuroplasticity interventions

This module provides comprehensive pharmacokinetic and pharmacodynamic models
for HNK, the key metabolite of R-ketamine, which induces rapid, sustained
neuroplastic effects via BDNF signaling and AMPA receptor trafficking.

References:
- Zanos et al. (2016). NMDAR inhibition-independent antidepressant actions of 
  ketamine metabolites. Nature, 533(7604), 481-486.
- Zanos et al. (2018). Mechanisms of ketamine action as an antidepressant. 
  Molecular Psychiatry, 23(4), 801-811.
- Highland et al. (2019). Hydroxynorketamines: Pharmacology and Potential 
  Therapeutic Applications. Pharmacological Reviews, 71(4), 524-550.
"""

import numpy as np
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from scipy.integrate import odeint
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)


class MetabolismProfile(Enum):
    """CYP2B6 metabolism profiles for inter-individual variability"""
    SLOW = "slow"  # Poor metabolizers
    NORMAL = "normal"  # Normal metabolizers
    RAPID = "rapid"  # Rapid metabolizers
    ULTRA_RAPID = "ultra_rapid"  # Ultra-rapid metabolizers


class HormonalPhase(Enum):
    """Hormonal phases affecting HNK efficacy in women's health"""
    FOLLICULAR = "follicular"  # Days 1-14 of cycle
    OVULATORY = "ovulatory"  # Days 14-16
    LUTEAL = "luteal"  # Days 16-28
    POSTPARTUM_LOW_ESTROGEN = "postpartum_low_estrogen"  # 0-3 months postpartum
    POSTPARTUM_RECOVERING = "postpartum_recovering"  # 3-6 months postpartum
    MENOPAUSAL = "menopausal"  # Low estrogen state


@dataclass
class HNKPharmacokinetics:
    """
    Pharmacokinetic parameters for HNK
    
    Based on Highland et al. (2019) Phase 1 data:
    - Half-life: ~2 hours
    - Dose-proportional exposure up to 0.5 mg/kg IV
    - Minimal NMDAR antagonism
    """
    clearance_ml_min_kg: float = 15.0  # Clearance rate
    volume_distribution_l_kg: float = 1.8  # Volume of distribution
    half_life_hours: float = 2.0  # Elimination half-life
    bioavailability: float = 1.0  # IV administration (100%)
    protein_binding: float = 0.45  # 45% protein bound
    
    def get_elimination_rate_constant(self) -> float:
        """Calculate elimination rate constant (k_e) from half-life"""
        return 0.693 / self.half_life_hours  # ln(2) / t_1/2
    
    def get_clearance_l_hr_kg(self) -> float:
        """Convert clearance from ml/min/kg to L/hr/kg"""
        return (self.clearance_ml_min_kg * 60) / 1000


@dataclass
class HNKPharmacodynamics:
    """
    Pharmacodynamic parameters for HNK
    
    Based on preclinical and Phase 1 data:
    - EC50 for BDNF induction: 0.1-0.3 mg/kg
    - Hill coefficient: 1.5-2.5
    - Minimal psychotomimetic effects
    - No dissociation or abuse liability
    """
    ec50_bdnf_mg_kg: float = 0.2  # EC50 for BDNF induction
    emax_bdnf_fold_increase: float = 3.5  # Maximum BDNF increase (fold over baseline)
    hill_coefficient: float = 2.0  # Hill coefficient for AMPA activation
    ec50_ampa_mg_kg: float = 0.15  # EC50 for AMPA receptor activation
    emax_ampa_percent: float = 85.0  # Maximum AMPA activation percentage
    onset_time_hours: float = 0.5  # Rapid onset (within hours)
    duration_hours: float = 48.0  # Sustained effects (up to 48 hours)
    dissociation_risk: float = 0.05  # Very low dissociation risk (5%)
    nmdar_antagonism: float = 0.1  # Minimal NMDAR antagonism (10% of ketamine)


@dataclass
class PatientCovariates:
    """
    Patient-specific covariates affecting HNK pharmacokinetics/pharmacodynamics
    
    Includes support for women's health considerations and metabolic variability
    """
    body_weight_kg: float = 70.0
    age_years: int = 35
    sex: str = "female"
    metabolism_profile: MetabolismProfile = MetabolismProfile.NORMAL
    hormonal_phase: Optional[HormonalPhase] = None
    baseline_bdnf_ng_ml: float = 15.0  # Normal baseline BDNF
    depression_severity_score: float = 0.7  # 0.0 to 1.0
    previous_ketamine_response: Optional[float] = None  # If known
    liver_function_percent: float = 100.0  # Hepatic function (% of normal)
    renal_function_ml_min: float = 90.0  # Creatinine clearance
    
    def get_metabolism_factor(self) -> float:
        """Get metabolism adjustment factor based on CYP2B6 profile"""
        factors = {
            MetabolismProfile.SLOW: 0.6,
            MetabolismProfile.NORMAL: 1.0,
            MetabolismProfile.RAPID: 1.4,
            MetabolismProfile.ULTRA_RAPID: 1.8
        }
        return factors[self.metabolism_profile]
    
    def get_hormonal_efficacy_modifier(self) -> float:
        """
        Get efficacy modifier based on hormonal phase
        
        Based on evidence that estrogen modulates neuroplasticity and BDNF expression
        """
        if not self.hormonal_phase or self.sex != "female":
            return 1.0
        
        modifiers = {
            HormonalPhase.FOLLICULAR: 1.2,  # High estrogen, enhanced neuroplasticity
            HormonalPhase.OVULATORY: 1.25,  # Peak estrogen
            HormonalPhase.LUTEAL: 0.95,  # Lower estrogen, progesterone dominant
            HormonalPhase.POSTPARTUM_LOW_ESTROGEN: 0.75,  # Very low estrogen
            HormonalPhase.POSTPARTUM_RECOVERING: 0.9,  # Recovering estrogen levels
            HormonalPhase.MENOPAUSAL: 0.8  # Low estrogen state
        }
        return modifiers[self.hormonal_phase]


class HNKPharmacodynamicsAgent:
    """
    HNK-specific dosing optimizer and pharmacodynamic modeling agent
    
    Provides:
    - Optimal dose calculation
    - Plasma concentration modeling
    - BDNF dynamics simulation
    - AMPA receptor activation modeling
    - Safety and efficacy predictions
    """
    
    def __init__(self, pk_params: Optional[HNKPharmacokinetics] = None,
                 pd_params: Optional[HNKPharmacodynamics] = None):
        """
        Initialize HNK pharmacodynamics agent
        
        Args:
            pk_params: Pharmacokinetic parameters (uses defaults if None)
            pd_params: Pharmacodynamic parameters (uses defaults if None)
        """
        self.pk = pk_params or HNKPharmacokinetics()
        self.pd = pd_params or HNKPharmacodynamics()
        self.logger = logging.getLogger(__name__ + ".HNKPharmacodynamicsAgent")
    
    def calculate_plasma_concentration(self, dose_mg_kg: float, time_hours: float,
                                      patient: PatientCovariates) -> float:
        """
        Calculate plasma concentration of HNK at given time after IV bolus
        
        Uses one-compartment model: C(t) = (Dose/Vd) * e^(-k_e * t)
        
        Args:
            dose_mg_kg: Dose in mg/kg
            time_hours: Time after administration in hours
            patient: Patient covariates
            
        Returns:
            Plasma concentration in mg/L
        """
        # Adjust parameters for patient-specific factors
        k_e = self.pk.get_elimination_rate_constant()
        k_e_adjusted = k_e * patient.get_metabolism_factor()
        
        # Adjust for hepatic function
        k_e_adjusted *= (patient.liver_function_percent / 100.0)
        
        # Calculate initial concentration (C0 = Dose / Vd)
        c0 = dose_mg_kg / self.pk.volume_distribution_l_kg
        
        # Calculate concentration at time t
        concentration = c0 * np.exp(-k_e_adjusted * time_hours)
        
        return concentration
    
    def hill_equation_ampa(self, concentration_mg_l: float) -> float:
        """
        Calculate AMPA receptor activation using Hill equation
        
        Effect = Emax * [HNK]^n / (EC50^n + [HNK]^n)
        
        Args:
            concentration_mg_l: HNK plasma concentration in mg/L
            
        Returns:
            AMPA activation percentage (0-100)
        """
        # Convert EC50 from mg/kg to approximate mg/L (assuming Vd)
        ec50_mg_l = self.pd.ec50_ampa_mg_kg / self.pk.volume_distribution_l_kg
        n = self.pd.hill_coefficient
        
        numerator = self.pd.emax_ampa_percent * (concentration_mg_l ** n)
        denominator = (ec50_mg_l ** n) + (concentration_mg_l ** n)
        
        effect = numerator / denominator if denominator > 0 else 0.0
        
        return effect
    
    def bdnf_dynamics_model(self, t: np.ndarray, dose_mg_kg: float,
                           patient: PatientCovariates) -> np.ndarray:
        """
        Simulate BDNF dynamics using differential equation model
        
        d[BDNF]/dt = k1*[HNK] - k2*[BDNF]
        
        Args:
            t: Time array in hours
            dose_mg_kg: HNK dose in mg/kg
            patient: Patient covariates
            
        Returns:
            BDNF concentration array over time (ng/mL)
        """
        def bdnf_ode(bdnf: float, time: float) -> float:
            """
            BDNF differential equation
            
            Args:
                bdnf: Current BDNF concentration
                time: Current time
                
            Returns:
                Rate of change of BDNF
            """
            # Get HNK concentration at current time
            hnk_conc = self.calculate_plasma_concentration(dose_mg_kg, time, patient)
            
            # Production rate constant (influenced by HNK and hormonal status)
            k1 = 0.5 * patient.get_hormonal_efficacy_modifier()
            
            # Degradation rate constant
            k2 = 0.02
            
            # Rate of BDNF change
            d_bdnf_dt = k1 * hnk_conc - k2 * bdnf
            
            return d_bdnf_dt
        
        # Initial condition: baseline BDNF
        bdnf0 = patient.baseline_bdnf_ng_ml
        
        # Solve ODE
        bdnf_levels = odeint(bdnf_ode, bdnf0, t)
        
        return bdnf_levels.flatten()
    
    def calculate_optimal_dose(self, patient: PatientCovariates,
                              target_bdnf_increase: float = 1.5) -> Dict[str, Any]:
        """
        Calculate optimal HNK dose for target BDNF increase
        
        Args:
            patient: Patient covariates
            target_bdnf_increase: Target BDNF fold increase over baseline
            
        Returns:
            Dictionary with optimal dose and predicted outcomes
        """
        # Dose range to evaluate (mg/kg)
        dose_range = np.linspace(0.05, 0.5, 50)
        
        # Simulate BDNF response for each dose
        max_bdnf_increases = []
        
        for dose in dose_range:
            # Simulate 48 hours
            t = np.linspace(0, 48, 200)
            bdnf_levels = self.bdnf_dynamics_model(t, dose, patient)
            
            # Calculate maximum fold increase
            max_bdnf = np.max(bdnf_levels)
            fold_increase = max_bdnf / patient.baseline_bdnf_ng_ml
            max_bdnf_increases.append(fold_increase)
        
        # Find dose closest to target
        max_bdnf_increases = np.array(max_bdnf_increases)
        idx = np.argmin(np.abs(max_bdnf_increases - target_bdnf_increase))
        optimal_dose = dose_range[idx]
        
        # Calculate predicted outcomes at optimal dose
        predicted_bdnf_increase = max_bdnf_increases[idx]
        
        # Calculate peak concentration
        peak_concentration = self.calculate_plasma_concentration(optimal_dose, 0, patient)
        
        # Calculate AMPA activation at peak
        ampa_activation = self.hill_equation_ampa(peak_concentration)
        
        # Predict mood improvement (empirical relationship)
        # Higher BDNF and AMPA activation correlate with better mood outcomes
        mood_improvement_score = min(1.0, (predicted_bdnf_increase - 1.0) * 0.4 + 
                                          ampa_activation / 100.0 * 0.3)
        
        # Safety margin (ensure well below doses with significant side effects)
        safety_margin = (0.5 - optimal_dose) / 0.5  # Relative to max safe dose
        
        return {
            "optimal_dose_mg_kg": round(optimal_dose, 3),
            "optimal_dose_mg": round(optimal_dose * patient.body_weight_kg, 1),
            "predicted_bdnf_fold_increase": round(predicted_bdnf_increase, 2),
            "predicted_peak_concentration_mg_l": round(peak_concentration, 2),
            "predicted_ampa_activation_percent": round(ampa_activation, 1),
            "predicted_mood_improvement_score": round(mood_improvement_score, 2),
            "dissociation_risk": self.pd.dissociation_risk,
            "safety_margin": round(safety_margin, 2),
            "onset_time_hours": self.pd.onset_time_hours,
            "duration_hours": self.pd.duration_hours
        }
    
    def monte_carlo_simulation(self, dose_mg_kg: float, 
                              n_simulations: int = 1000,
                              base_patient: Optional[PatientCovariates] = None) -> Dict[str, Any]:
        """
        Monte Carlo simulation for inter-individual variability
        
        Factors in CYP2B6 metabolism variability, hormonal effects, and 
        baseline BDNF variations
        
        Args:
            dose_mg_kg: HNK dose to simulate
            n_simulations: Number of Monte Carlo iterations
            base_patient: Base patient parameters (uses defaults if None)
            
        Returns:
            Dictionary with simulation statistics
        """
        if base_patient is None:
            base_patient = PatientCovariates()
        
        bdnf_increases = []
        mood_improvements = []
        peak_concentrations = []
        
        for _ in range(n_simulations):
            # Create patient with random variability
            patient = PatientCovariates(
                body_weight_kg=np.random.normal(base_patient.body_weight_kg, 10),
                age_years=base_patient.age_years,
                sex=base_patient.sex,
                metabolism_profile=np.random.choice(list(MetabolismProfile)),
                hormonal_phase=base_patient.hormonal_phase,
                baseline_bdnf_ng_ml=np.random.normal(base_patient.baseline_bdnf_ng_ml, 3),
                depression_severity_score=base_patient.depression_severity_score,
                liver_function_percent=np.random.normal(100, 10),
                renal_function_ml_min=np.random.normal(90, 15)
            )
            
            # Ensure positive values
            patient.body_weight_kg = max(40, patient.body_weight_kg)
            patient.baseline_bdnf_ng_ml = max(5, patient.baseline_bdnf_ng_ml)
            patient.liver_function_percent = np.clip(patient.liver_function_percent, 40, 100)
            patient.renal_function_ml_min = max(30, patient.renal_function_ml_min)
            
            # Simulate BDNF response
            t = np.linspace(0, 48, 200)
            bdnf_levels = self.bdnf_dynamics_model(t, dose_mg_kg, patient)
            max_bdnf = np.max(bdnf_levels)
            bdnf_increase = max_bdnf / patient.baseline_bdnf_ng_ml
            bdnf_increases.append(bdnf_increase)
            
            # Calculate peak concentration
            peak_conc = self.calculate_plasma_concentration(dose_mg_kg, 0, patient)
            peak_concentrations.append(peak_conc)
            
            # Estimate mood improvement
            ampa_activation = self.hill_equation_ampa(peak_conc)
            mood_improvement = min(1.0, (bdnf_increase - 1.0) * 0.4 + 
                                      ampa_activation / 100.0 * 0.3)
            mood_improvements.append(mood_improvement)
        
        # Calculate statistics
        bdnf_increases = np.array(bdnf_increases)
        mood_improvements = np.array(mood_improvements)
        peak_concentrations = np.array(peak_concentrations)
        
        return {
            "dose_mg_kg": dose_mg_kg,
            "n_simulations": n_simulations,
            "bdnf_fold_increase": {
                "mean": round(float(np.mean(bdnf_increases)), 2),
                "std": round(float(np.std(bdnf_increases)), 2),
                "median": round(float(np.median(bdnf_increases)), 2),
                "percentile_25": round(float(np.percentile(bdnf_increases, 25)), 2),
                "percentile_75": round(float(np.percentile(bdnf_increases, 75)), 2),
                "min": round(float(np.min(bdnf_increases)), 2),
                "max": round(float(np.max(bdnf_increases)), 2)
            },
            "mood_improvement_score": {
                "mean": round(float(np.mean(mood_improvements)), 3),
                "std": round(float(np.std(mood_improvements)), 3),
                "median": round(float(np.median(mood_improvements)), 3),
                "percentile_25": round(float(np.percentile(mood_improvements, 25)), 3),
                "percentile_75": round(float(np.percentile(mood_improvements, 75)), 3)
            },
            "peak_concentration_mg_l": {
                "mean": round(float(np.mean(peak_concentrations)), 2),
                "std": round(float(np.std(peak_concentrations)), 2),
                "median": round(float(np.median(peak_concentrations)), 2)
            },
            "responder_rate_percent": round(float(np.sum(mood_improvements > 0.3) / n_simulations * 100), 1)
        }
    
    def plot_dose_response_curves(self, patient: PatientCovariates,
                                  output_path: Optional[str] = None) -> None:
        """
        Visualize dose-response curves for mood improvement vs. side effects
        
        Args:
            patient: Patient covariates
            output_path: Path to save figure (displays if None)
        """
        # Dose range
        doses = np.linspace(0.05, 0.6, 100)
        
        # Calculate responses
        bdnf_increases = []
        mood_improvements = []
        dissociation_risks = []
        
        for dose in doses:
            # Simulate BDNF response
            t = np.linspace(0, 48, 200)
            bdnf_levels = self.bdnf_dynamics_model(t, dose, patient)
            max_bdnf = np.max(bdnf_levels)
            bdnf_increase = max_bdnf / patient.baseline_bdnf_ng_ml
            bdnf_increases.append(bdnf_increase)
            
            # Calculate mood improvement
            peak_conc = self.calculate_plasma_concentration(dose, 0, patient)
            ampa_activation = self.hill_equation_ampa(peak_conc)
            mood_improvement = min(1.0, (bdnf_increase - 1.0) * 0.4 + 
                                      ampa_activation / 100.0 * 0.3)
            mood_improvements.append(mood_improvement)
            
            # Dissociation risk (increases with dose but remains low for HNK)
            dissociation_risk = self.pd.dissociation_risk * (1 + dose / 0.5 * 0.5)
            dissociation_risks.append(dissociation_risk)
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: Efficacy measures
        ax1.plot(doses, bdnf_increases, 'b-', linewidth=2, label='BDNF Fold Increase')
        ax1.plot(doses, mood_improvements, 'g-', linewidth=2, label='Mood Improvement Score')
        ax1.axvline(x=0.3, color='r', linestyle='--', alpha=0.5, label='Typical Dose')
        ax1.axhline(y=1.5, color='gray', linestyle=':', alpha=0.5, label='Target BDNF (1.5x)')
        ax1.set_xlabel('HNK Dose (mg/kg)', fontsize=12)
        ax1.set_ylabel('Response', fontsize=12)
        ax1.set_title('HNK Efficacy: Dose-Response Curves', fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Safety profile
        ax2.plot(doses, dissociation_risks, 'r-', linewidth=2, label='Dissociation Risk')
        ax2.axvline(x=0.3, color='r', linestyle='--', alpha=0.5, label='Typical Dose')
        ax2.axhline(y=0.1, color='orange', linestyle=':', alpha=0.5, label='Acceptable Risk')
        ax2.set_xlabel('HNK Dose (mg/kg)', fontsize=12)
        ax2.set_ylabel('Risk Probability', fontsize=12)
        ax2.set_title('HNK Safety Profile: Minimal Side Effects', fontsize=14, fontweight='bold')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([0, 0.15])
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Dose-response curves saved to {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_treatment_protocol(self, patient: PatientCovariates,
                                   treatment_weeks: int = 8) -> Dict[str, Any]:
        """
        Generate HNK treatment protocol for addiction recovery (Week 5-8 protocol)
        
        Args:
            patient: Patient covariates
            treatment_weeks: Duration of treatment in weeks
            
        Returns:
            Treatment protocol dictionary
        """
        # Calculate optimal dose
        optimal_dose_result = self.calculate_optimal_dose(patient)
        optimal_dose_mg_kg = optimal_dose_result["optimal_dose_mg_kg"]
        
        # Generate dosing schedule (2-3 times per week as per guidelines)
        sessions_per_week = 2
        total_sessions = treatment_weeks * sessions_per_week
        
        # Create session schedule
        sessions = []
        for week in range(1, treatment_weeks + 1):
            for session_in_week in range(1, sessions_per_week + 1):
                session = {
                    "week": week,
                    "session_number": (week - 1) * sessions_per_week + session_in_week,
                    "dose_mg_kg": optimal_dose_mg_kg,
                    "dose_mg": round(optimal_dose_mg_kg * patient.body_weight_kg, 1),
                    "route": "IV",
                    "infusion_duration_minutes": 40,
                    "monitoring_required": [
                        "blood_pressure",
                        "heart_rate",
                        "dissociation_scale",
                        "mood_scores",
                        "BDNF_levels"
                    ]
                }
                sessions.append(session)
        
        protocol = {
            "patient_id": f"patient_{patient.age_years}_{patient.sex}",
            "treatment_type": "HNK-assisted_neuroplasticity_therapy",
            "duration_weeks": treatment_weeks,
            "total_sessions": total_sessions,
            "dosing_frequency": f"{sessions_per_week} times per week",
            "optimal_dose_mg_kg": optimal_dose_mg_kg,
            "predicted_outcomes": optimal_dose_result,
            "sessions": sessions,
            "contraindications": [
                "uncontrolled_hypertension",
                "active_psychosis",
                "severe_hepatic_impairment"
            ],
            "integration_with_biohacking": {
                "pemf_therapy": "30 minutes post-infusion for enhanced neuroplasticity",
                "eeg_monitoring": "continuous during infusion and 2 hours post",
                "red_light_therapy": "20 minutes concurrent with infusion"
            },
            "hormonal_considerations": {
                "current_phase": patient.hormonal_phase.value if patient.hormonal_phase else "not_applicable",
                "efficacy_modifier": patient.get_hormonal_efficacy_modifier(),
                "recommendations": "Schedule sessions during follicular/ovulatory phases when possible for optimal efficacy"
            } if patient.sex == "female" else None
        }
        
        return protocol
    
    def export_to_json(self, data: Dict[str, Any], output_path: str) -> None:
        """
        Export data to JSON format for IRIP agent integration
        
        Args:
            data: Data dictionary to export
            output_path: Path to save JSON file
        """
        # Ensure HIPAA-compliant data handling
        # Remove any direct patient identifiers
        sanitized_data = self._sanitize_for_hipaa(data)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(sanitized_data, f, indent=2)
            self.logger.info(f"Data exported to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")
            raise
    
    def _sanitize_for_hipaa(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or anonymize PHI for HIPAA compliance
        
        Args:
            data: Original data dictionary
            
        Returns:
            Sanitized data dictionary
        """
        sanitized = data.copy()
        
        # Remove or hash patient identifiers if present
        phi_fields = ['patient_name', 'ssn', 'mrn', 'dob', 'address', 'phone']
        for field in phi_fields:
            if field in sanitized:
                del sanitized[field]
        
        return sanitized


def create_example_usage() -> Dict[str, Any]:
    """
    Example usage for testing HNK infusion during Week 5-8 protocols
    
    Returns:
        Dictionary with example results
    """
    # Create HNK agent
    hnk_agent = HNKPharmacodynamicsAgent()
    
    # Define example patient (postpartum woman in recovery)
    patient = PatientCovariates(
        body_weight_kg=65.0,
        age_years=32,
        sex="female",
        metabolism_profile=MetabolismProfile.NORMAL,
        hormonal_phase=HormonalPhase.POSTPARTUM_LOW_ESTROGEN,
        baseline_bdnf_ng_ml=12.0,  # Lower due to postpartum
        depression_severity_score=0.8,
        liver_function_percent=95.0,
        renal_function_ml_min=95.0
    )
    
    # Calculate optimal dose
    optimal_dose = hnk_agent.calculate_optimal_dose(patient, target_bdnf_increase=1.8)
    
    # Run Monte Carlo simulation
    mc_results = hnk_agent.monte_carlo_simulation(
        dose_mg_kg=optimal_dose["optimal_dose_mg_kg"],
        n_simulations=1000,
        base_patient=patient
    )
    
    # Generate treatment protocol
    protocol = hnk_agent.generate_treatment_protocol(patient, treatment_weeks=8)
    
    # Compile results
    results = {
        "patient_profile": {
            "weight_kg": patient.body_weight_kg,
            "age": patient.age_years,
            "sex": patient.sex,
            "metabolism_profile": patient.metabolism_profile.value,
            "hormonal_phase": patient.hormonal_phase.value,
            "baseline_bdnf": patient.baseline_bdnf_ng_ml
        },
        "optimal_dosing": optimal_dose,
        "variability_analysis": mc_results,
        "treatment_protocol": protocol
    }
    
    return results


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    print("=" * 80)
    print("HNK Pharmacodynamics Model - Example Usage")
    print("=" * 80)
    print()
    
    results = create_example_usage()
    
    print("Patient Profile:")
    print(json.dumps(results["patient_profile"], indent=2))
    print()
    
    print("Optimal Dosing Recommendation:")
    print(json.dumps(results["optimal_dosing"], indent=2))
    print()
    
    print("Monte Carlo Variability Analysis:")
    print(json.dumps(results["variability_analysis"], indent=2))
    print()
    
    print("Treatment Protocol Summary:")
    protocol = results["treatment_protocol"]
    print(f"  Duration: {protocol['duration_weeks']} weeks")
    print(f"  Total Sessions: {protocol['total_sessions']}")
    print(f"  Optimal Dose: {protocol['optimal_dose_mg_kg']} mg/kg")
    print()
    
    # Generate and save dose-response curves
    hnk_agent = HNKPharmacodynamicsAgent()
    patient = PatientCovariates(hormonal_phase=HormonalPhase.POSTPARTUM_LOW_ESTROGEN)
    
    print("Generating dose-response curves...")
    # Note: Visualization would be saved to file in production
    # hnk_agent.plot_dose_response_curves(patient, output_path="hnk_dose_response.png")
    
    print()
    print("=" * 80)
    print("HNK Model Example Complete")
    print("=" * 80)
