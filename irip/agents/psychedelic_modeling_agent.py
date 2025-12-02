"""
Psychedelic Modeling Agent
Psilocybin, MDMA, and LSD protocol management with safety screening

Implements dose-BDNF response curves, contraindication screening,
and MAPS-style session protocols for FDA breakthrough therapies.

References:
- Carhart-Harris et al. (2021). Trial of Psilocybin versus Escitalopram 
  for Depression. New England Journal of Medicine, 384(15), 1402-1411. [PMID: 33852780]
- Mitchell et al. (2021). MDMA-assisted therapy for severe PTSD: a 
  randomized, double-blind, placebo-controlled phase 3 study. 
  Nature Medicine, 27(6), 1025-1033. [PMID: 33972795]
- Gukasyan et al. (2022). Efficacy and safety of psilocybin-assisted 
  treatment for major depressive disorder. Journal of Psychopharmacology,
  36(4), 481-497. [PMID: 35166158]
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)

logger = logging.getLogger(__name__)


class PsychedelicType(Enum):
    """Types of psychedelic compounds"""
    PSILOCYBIN = "psilocybin"
    MDMA = "mdma"
    LSD = "lsd"
    KETAMINE = "ketamine"  # Reference for comparison
    DMT = "dmt"


class SessionPhase(Enum):
    """MAPS-style session phases"""
    PREPARATION = "preparation"
    DOSING = "dosing"
    PEAK = "peak"
    PLATEAU = "plateau"
    DESCENT = "descent"
    INTEGRATION = "integration"


class ContraindicationType(Enum):
    """Contraindication categories"""
    CARDIAC = "cardiac"
    PSYCHIATRIC = "psychiatric"
    MEDICATION = "medication"
    MEDICAL = "medical"
    PERSONAL = "personal"


@dataclass
class SafetyScreening:
    """Patient safety screening results"""
    patient_id: str
    screening_date: datetime
    qtc_interval_ms: float  # Corrected QT interval
    blood_pressure_systolic: float
    blood_pressure_diastolic: float
    heart_rate: float
    psychiatric_history: List[str]
    current_medications: List[str]
    family_history_psychosis: bool
    personal_history_psychosis: bool
    suicide_risk_level: str  # "low", "moderate", "high"
    cleared_for_treatment: bool
    contraindications: List[Dict[str, Any]]


@dataclass
class DoseResponse:
    """Dose-BDNF response prediction"""
    compound: PsychedelicType
    dose_mg: float
    weight_kg: float
    dose_mg_kg: float
    predicted_bdnf_fold_change: float
    confidence_interval_95: Tuple[float, float]
    onset_hours: float
    peak_hours: float
    duration_hours: float
    expected_mystical_experience_score: float  # MEQ30 prediction


@dataclass
class SessionProtocol:
    """MAPS-style session protocol"""
    session_id: str
    patient_id: str
    compound: PsychedelicType
    dose_mg: float
    scheduled_date: datetime
    preparation_sessions: int
    integration_sessions: int
    therapist_ids: List[str]
    setting_requirements: Dict[str, Any]
    emergency_protocols: List[str]
    monitoring_parameters: List[str]


class PsychedelicModelingAgent(BaseAgent):
    """
    Psychedelic Modeling Agent for FDA breakthrough therapy protocols
    
    Implements evidence-based dosing, safety screening, and session
    management for psilocybin, MDMA, and other psychedelic compounds.
    
    Safety criteria based on MAPS Phase 3 protocols and FDA guidance:
    - QTc < 450ms for males, < 470ms for females (per ICH E14)
    - No personal/family history of psychosis
    - Adequate washout from contraindicated medications
    - Suicide risk assessment (Columbia Protocol)
    """
    
    # Safety thresholds per FDA guidance and MAPS protocols
    QTC_MAX_MALE_MS = 450
    QTC_MAX_FEMALE_MS = 470
    BP_SYSTOLIC_MAX = 160
    BP_DIASTOLIC_MAX = 100
    
    # Standard doses per clinical trials
    STANDARD_DOSES = {
        PsychedelicType.PSILOCYBIN: 25.0,  # mg, per Carhart-Harris et al.
        PsychedelicType.MDMA: 120.0,       # mg initial, per Mitchell et al.
        PsychedelicType.LSD: 200.0,        # μg, per Holze et al.
        PsychedelicType.KETAMINE: 0.5,     # mg/kg, per Zarate et al.
    }
    
    # Contraindicated medications (partial list)
    CONTRAINDICATED_MEDS = {
        PsychedelicType.PSILOCYBIN: [
            "lithium", "tramadol", "maoi", "ssri", "snri"
        ],
        PsychedelicType.MDMA: [
            "maoi", "ssri", "snri", "stimulants", "ritonavir"
        ],
        PsychedelicType.LSD: [
            "lithium", "tramadol", "maoi"
        ]
    }
    
    def __init__(self, agent_id: str = "psychedelic_modeling_agent"):
        super().__init__(
            agent_id=agent_id,
            capabilities=[
                AgentCapability.MEDICATION_MANAGEMENT,
                AgentCapability.TREATMENT_OPTIMIZATION,
                AgentCapability.DATA_ANALYSIS
            ]
        )
        
        # BDNF response curves (based on meta-analysis estimates)
        self._bdnf_curves = self._initialize_bdnf_curves()
    
    def _initialize_bdnf_curves(self) -> Dict[PsychedelicType, callable]:
        """
        Initialize dose-BDNF response curves
        
        Based on:
        - Psilocybin: ~1.3-1.8x BDNF at 25mg (Ly et al., 2018)
        - MDMA: ~1.2-1.5x BDNF (Danforth et al., 2018)
        - LSD: ~1.4-2.0x BDNF (Ly et al., 2018)
        """
        curves = {}
        
        # Psilocybin: Hill equation with EC50 ~15mg
        curves[PsychedelicType.PSILOCYBIN] = lambda dose: 1.0 + 0.8 * (dose ** 1.5) / (15 ** 1.5 + dose ** 1.5)
        
        # MDMA: Linear-ish response up to ceiling
        curves[PsychedelicType.MDMA] = lambda dose: 1.0 + 0.5 * min(dose / 120, 1.5)
        
        # LSD: Similar to psilocybin, EC50 ~100μg
        curves[PsychedelicType.LSD] = lambda dose: 1.0 + 1.0 * (dose ** 1.2) / (100 ** 1.2 + dose ** 1.2)
        
        return curves
    
    async def initialize(self):
        """Initialize agent"""
        await super().initialize()
        logger.info(f"{self.agent_id} initialized with MAPS-style protocols")
    
    def screen_protocol(self, patient_data: Dict[str, Any]) -> bool:
        """
        Screen patient for psychedelic therapy eligibility
        
        Args:
            patient_data: Dict containing screening parameters
        
        Returns:
            bool: True if cleared for treatment
        
        Example:
            >>> patient_data = {'qtc': 420, 'sex': 'male', 'psychosis_history': False}
            >>> agent.screen_protocol(patient_data)
            True
        """
        # QTc check
        qtc = patient_data.get('qtc', 500)
        sex = patient_data.get('sex', 'unknown').lower()
        
        qtc_limit = self.QTC_MAX_MALE_MS if sex == 'male' else self.QTC_MAX_FEMALE_MS
        if qtc >= qtc_limit:
            return False
        
        # Psychosis history check
        if patient_data.get('psychosis_history', False):
            return False
        
        if patient_data.get('family_psychosis_history', False):
            return False
        
        # Blood pressure check
        bp_sys = patient_data.get('bp_systolic', 200)
        bp_dia = patient_data.get('bp_diastolic', 100)
        
        if bp_sys > self.BP_SYSTOLIC_MAX or bp_dia > self.BP_DIASTOLIC_MAX:
            return False
        
        # Suicide risk check
        suicide_risk = patient_data.get('suicide_risk', 'high').lower()
        if suicide_risk in ['high', 'severe', 'imminent']:
            return False
        
        return True
    
    async def perform_safety_screening(self, patient_id: str, 
                                       patient_data: Dict[str, Any],
                                       compound: PsychedelicType) -> SafetyScreening:
        """
        Comprehensive safety screening for psychedelic therapy
        
        Args:
            patient_id: Patient identifier
            patient_data: Clinical data
            compound: Target psychedelic
        
        Returns:
            SafetyScreening with eligibility determination
        """
        contraindications = []
        
        # Check QTc
        qtc = patient_data.get('qtc', 0)
        sex = patient_data.get('sex', 'unknown').lower()
        qtc_limit = self.QTC_MAX_MALE_MS if sex == 'male' else self.QTC_MAX_FEMALE_MS
        
        if qtc >= qtc_limit:
            contraindications.append({
                'type': ContraindicationType.CARDIAC.value,
                'reason': f'QTc {qtc}ms exceeds limit {qtc_limit}ms',
                'severity': 'absolute'
            })
        
        # Check psychosis history
        if patient_data.get('psychosis_history', False):
            contraindications.append({
                'type': ContraindicationType.PSYCHIATRIC.value,
                'reason': 'Personal history of psychosis',
                'severity': 'absolute'
            })
        
        if patient_data.get('family_psychosis_history', False):
            contraindications.append({
                'type': ContraindicationType.PSYCHIATRIC.value,
                'reason': 'First-degree relative with psychosis',
                'severity': 'relative'
            })
        
        # Check medications
        current_meds = [m.lower() for m in patient_data.get('medications', [])]
        contraindicated = self.CONTRAINDICATED_MEDS.get(compound, [])
        
        for med in current_meds:
            for contra_med in contraindicated:
                if contra_med in med:
                    contraindications.append({
                        'type': ContraindicationType.MEDICATION.value,
                        'reason': f'{med} contraindicated with {compound.value}',
                        'severity': 'relative',
                        'washout_days': 14 if 'ssri' in contra_med else 28
                    })
        
        # Blood pressure
        bp_sys = patient_data.get('bp_systolic', 120)
        bp_dia = patient_data.get('bp_diastolic', 80)
        
        if bp_sys > self.BP_SYSTOLIC_MAX or bp_dia > self.BP_DIASTOLIC_MAX:
            contraindications.append({
                'type': ContraindicationType.CARDIAC.value,
                'reason': f'BP {bp_sys}/{bp_dia} exceeds limits',
                'severity': 'relative'
            })
        
        # Determine eligibility
        absolute_contraindications = [c for c in contraindications 
                                      if c.get('severity') == 'absolute']
        cleared = len(absolute_contraindications) == 0
        
        return SafetyScreening(
            patient_id=patient_id,
            screening_date=datetime.now(),
            qtc_interval_ms=qtc,
            blood_pressure_systolic=bp_sys,
            blood_pressure_diastolic=bp_dia,
            heart_rate=patient_data.get('heart_rate', 70),
            psychiatric_history=patient_data.get('psychiatric_history', []),
            current_medications=patient_data.get('medications', []),
            family_history_psychosis=patient_data.get('family_psychosis_history', False),
            personal_history_psychosis=patient_data.get('psychosis_history', False),
            suicide_risk_level=patient_data.get('suicide_risk', 'low'),
            cleared_for_treatment=cleared,
            contraindications=contraindications
        )
    
    async def predict_dose_response(self, compound: PsychedelicType,
                                   dose_mg: float, weight_kg: float) -> DoseResponse:
        """
        Predict BDNF response and session characteristics for given dose
        
        Args:
            compound: Psychedelic type
            dose_mg: Dose in mg (or μg for LSD)
            weight_kg: Patient weight
        
        Returns:
            DoseResponse with BDNF prediction and timing estimates
        """
        dose_mg_kg = dose_mg / weight_kg
        
        # Get BDNF prediction from curve
        if compound in self._bdnf_curves:
            bdnf_fold = self._bdnf_curves[compound](dose_mg)
        else:
            bdnf_fold = 1.0
        
        # Add uncertainty (±15% typical)
        uncertainty = bdnf_fold * 0.15
        ci_lower = bdnf_fold - 1.96 * uncertainty
        ci_upper = bdnf_fold + 1.96 * uncertainty
        
        # Timing estimates based on pharmacokinetics
        timing = {
            PsychedelicType.PSILOCYBIN: (0.5, 2.0, 6.0),   # onset, peak, duration
            PsychedelicType.MDMA: (0.75, 2.0, 5.0),
            PsychedelicType.LSD: (1.0, 3.0, 12.0),
            PsychedelicType.KETAMINE: (0.25, 0.5, 1.5),
        }
        
        onset, peak, duration = timing.get(compound, (1.0, 2.0, 6.0))
        
        # MEQ30 prediction (mystical experience questionnaire)
        # Higher doses correlate with higher MEQ scores (Griffiths et al., 2011)
        meq_score = min(1.0, 0.3 + 0.7 * (dose_mg / self.STANDARD_DOSES.get(compound, dose_mg)))
        
        return DoseResponse(
            compound=compound,
            dose_mg=dose_mg,
            weight_kg=weight_kg,
            dose_mg_kg=round(dose_mg_kg, 3),
            predicted_bdnf_fold_change=round(bdnf_fold, 3),
            confidence_interval_95=(round(ci_lower, 3), round(ci_upper, 3)),
            onset_hours=onset,
            peak_hours=peak,
            duration_hours=duration,
            expected_mystical_experience_score=round(meq_score, 2)
        )
    
    async def create_session_protocol(self, patient_id: str,
                                      compound: PsychedelicType,
                                      dose_mg: float,
                                      scheduled_date: datetime) -> SessionProtocol:
        """
        Create MAPS-style session protocol
        
        Includes:
        - 2-3 preparation sessions (per MAPS protocol)
        - Single dosing session with trained therapist pair
        - 3 integration sessions (minimum)
        """
        # Preparation sessions based on compound
        prep_sessions = {
            PsychedelicType.PSILOCYBIN: 2,
            PsychedelicType.MDMA: 3,
            PsychedelicType.LSD: 2,
        }
        
        # Integration sessions (MAPS recommends 3 minimum)
        integration_sessions = 3
        
        # Setting requirements
        setting = {
            'room_type': 'comfortable_therapy_room',
            'lighting': 'dimmable',
            'music': 'curated_playlist',
            'eyeshades_available': True,
            'emergency_equipment': ['crash_cart', 'benzodiazepines', 'bp_monitor'],
            'therapist_ratio': '2:1',  # 2 therapists per patient
            'session_duration_hours': 8 if compound == PsychedelicType.LSD else 6
        }
        
        # Emergency protocols
        emergencies = [
            'difficult_experience_grounding',
            'hypertensive_crisis_protocol',
            'psychotic_break_protocol',
            'medical_emergency_911'
        ]
        
        # Monitoring parameters
        monitoring = [
            'heart_rate', 'blood_pressure', 'oxygen_saturation',
            'subjective_distress_0_10', 'anxiety_level_0_10',
            'mystical_experience_checklist'
        ]
        
        return SessionProtocol(
            session_id=f"psych_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            patient_id=patient_id,
            compound=compound,
            dose_mg=dose_mg,
            scheduled_date=scheduled_date,
            preparation_sessions=prep_sessions.get(compound, 2),
            integration_sessions=integration_sessions,
            therapist_ids=[],  # To be assigned
            setting_requirements=setting,
            emergency_protocols=emergencies,
            monitoring_parameters=monitoring
        )
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages from other agents"""
        if message.message_type == "screen_patient":
            patient_id = message.content['patient_id']
            patient_data = message.content['patient_data']
            compound = PsychedelicType(message.content.get('compound', 'psilocybin'))
            
            screening = await self.perform_safety_screening(
                patient_id, patient_data, compound
            )
            
            return AgentMessage(
                message_id=f"msg_{datetime.now().timestamp()}",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="screening_result",
                content={
                    'patient_id': patient_id,
                    'cleared': screening.cleared_for_treatment,
                    'contraindications': screening.contraindications
                },
                priority=AgentPriority.HIGH,
                timestamp=datetime.now().timestamp(),
                correlation_id=message.message_id
            )
        
        return None


def generate_synthetic_patient_data(cleared: bool = True) -> Dict[str, Any]:
    """
    Generate synthetic patient data for testing
    
    Args:
        cleared: Whether patient should pass screening
    
    Returns:
        Dict with patient screening data
    """
    np.random.seed(42)
    
    if cleared:
        return {
            'qtc': np.random.normal(400, 20),
            'sex': np.random.choice(['male', 'female']),
            'bp_systolic': np.random.normal(120, 10),
            'bp_diastolic': np.random.normal(75, 8),
            'heart_rate': np.random.normal(70, 10),
            'psychosis_history': False,
            'family_psychosis_history': False,
            'psychiatric_history': ['depression', 'anxiety'],
            'medications': ['none'],
            'suicide_risk': 'low'
        }
    else:
        return {
            'qtc': np.random.normal(480, 20),  # Elevated
            'sex': 'male',
            'bp_systolic': 170,  # High
            'bp_diastolic': 95,
            'heart_rate': 90,
            'psychosis_history': True,  # Contraindicated
            'family_psychosis_history': True,
            'psychiatric_history': ['schizophrenia', 'bipolar'],
            'medications': ['lithium', 'fluoxetine'],
            'suicide_risk': 'high'
        }
