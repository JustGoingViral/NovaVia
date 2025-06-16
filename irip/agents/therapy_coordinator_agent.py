"""
IRIP Therapy Coordinator Agent
AI-driven coordination of ketamine therapy and plant medicine protocols for addiction recovery
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import math
from datetime import datetime, timedelta

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)


class TherapyType(Enum):
    """Types of therapy protocols"""
    KETAMINE_IV = "ketamine_iv"
    KETAMINE_IM = "ketamine_im"
    KETAMINE_SUBLINGUAL = "ketamine_sublingual"
    PSILOCYBIN = "psilocybin"
    MDMA = "mdma"
    AYAHUASCA = "ayahuasca"
    IBOGAINE = "ibogaine"
    TRADITIONAL_THERAPY = "traditional_therapy"
    GROUP_THERAPY = "group_therapy"
    INTEGRATION_THERAPY = "integration_therapy"


class TherapyPhase(Enum):
    """Therapy protocol phases"""
    PREPARATION = "preparation"
    INDUCTION = "induction"
    ACUTE_PHASE = "acute_phase"
    INTEGRATION = "integration"
    MAINTENANCE = "maintenance"
    FOLLOW_UP = "follow_up"


class ReadinessLevel(Enum):
    """Patient readiness for therapy"""
    NOT_READY = "not_ready"
    PREPARING = "preparing"
    READY = "ready"
    OPTIMAL = "optimal"
    POST_SESSION = "post_session"


@dataclass
class TherapyProtocol:
    """Therapy protocol specification"""
    protocol_id: str
    therapy_type: TherapyType
    name: str
    indication: str
    dosage_range: Tuple[float, float]  # mg/kg or absolute mg
    duration_hours: float
    preparation_days: int
    integration_days: int
    contraindications: List[str]
    required_assessments: List[str]
    monitoring_parameters: List[str]
    safety_protocols: List[str]
    expected_outcomes: List[str]


@dataclass
class TherapySession:
    """Individual therapy session data"""
    session_id: str
    patient_id: str
    therapy_type: TherapyType
    protocol_id: str
    scheduled_time: float
    actual_start_time: Optional[float]
    duration_minutes: int
    dosage_mg: float
    setting: str  # clinical, retreat, etc.
    therapist_id: str
    co_therapist_id: Optional[str]
    pre_session_vitals: Optional[Dict[str, float]]
    post_session_vitals: Optional[Dict[str, float]]
    subjective_effects: Optional[Dict[str, Any]]
    integration_notes: Optional[str]
    outcomes: Optional[Dict[str, float]]
    adverse_events: List[str]
    session_rating: Optional[float]


@dataclass
class ReadinessAssessment:
    """Patient readiness assessment for therapy"""
    assessment_id: str
    patient_id: str
    timestamp: float
    therapy_type: TherapyType
    readiness_level: ReadinessLevel
    psychological_readiness: float  # 0.0 to 1.0
    medical_clearance: bool
    set_and_setting_score: float  # 0.0 to 1.0
    support_system_strength: float  # 0.0 to 1.0
    integration_capacity: float  # 0.0 to 1.0
    risk_factors: List[str]
    recommendations: List[str]
    estimated_optimal_timing: Optional[float]


class TherapyProtocols:
    """Pre-defined therapy protocols for addiction recovery"""
    
    KETAMINE_DEPRESSION_ADDICTION = TherapyProtocol(
        protocol_id="ketamine_depression_001",
        therapy_type=TherapyType.KETAMINE_IV,
        name="Ketamine for Depression and Addiction",
        indication="treatment_resistant_depression_with_addiction",
        dosage_range=(0.5, 2.0),  # mg/kg
        duration_hours=1.0,
        preparation_days=3,
        integration_days=7,
        contraindications=[
            "uncontrolled_hypertension",
            "history_of_psychosis",
            "active_manic_episode",
            "severe_cardiovascular_disease"
        ],
        required_assessments=[
            "medical_clearance",
            "psychiatric_evaluation",
            "addiction_severity_assessment",
            "readiness_assessment"
        ],
        monitoring_parameters=[
            "blood_pressure",
            "heart_rate",
            "oxygen_saturation",
            "dissociation_scale",
            "mood_scores",
            "suicidal_ideation"
        ],
        safety_protocols=[
            "continuous_monitoring",
            "emergency_protocols",
            "contraindication_screening",
            "drug_interaction_check"
        ],
        expected_outcomes=[
            "depression_reduction",
            "craving_reduction",
            "increased_neuroplasticity",
            "improved_mood_regulation"
        ]
    )
    
    PSILOCYBIN_ADDICTION = TherapyProtocol(
        protocol_id="psilocybin_addiction_001",
        therapy_type=TherapyType.PSILOCYBIN,
        name="Psilocybin for Addiction Recovery",
        indication="substance_use_disorder",
        dosage_range=(10.0, 30.0),  # mg absolute
        duration_hours=6.0,
        preparation_days=14,
        integration_days=21,
        contraindications=[
            "history_of_psychosis",
            "bipolar_disorder",
            "severe_personality_disorder",
            "active_suicidal_ideation"
        ],
        required_assessments=[
            "comprehensive_psychiatric_evaluation",
            "addiction_history_assessment",
            "psychological_readiness_evaluation",
            "social_support_assessment"
        ],
        monitoring_parameters=[
            "mystical_experience_questionnaire",
            "challenging_experience_questionnaire",
            "ego_dissolution_inventory",
            "addiction_severity_index",
            "depression_anxiety_scores"
        ],
        safety_protocols=[
            "trained_therapist_present",
            "medical_backup_available",
            "safe_therapeutic_setting",
            "integration_support"
        ],
        expected_outcomes=[
            "mystical_experience",
            "ego_dissolution",
            "increased_openness",
            "reduced_addiction_severity",
            "improved_psychological_flexibility"
        ]
    )
    
    IBOGAINE_OPIOID_DETOX = TherapyProtocol(
        protocol_id="ibogaine_detox_001",
        therapy_type=TherapyType.IBOGAINE,
        name="Ibogaine for Opioid Detoxification",
        indication="opioid_use_disorder_detoxification",
        dosage_range=(15.0, 25.0),  # mg/kg
        duration_hours=24.0,
        preparation_days=7,
        integration_days=30,
        contraindications=[
            "cardiac_conditions",
            "liver_disease",
            "kidney_disease",
            "recent_benzodiazepine_use",
            "eating_disorders"
        ],
        required_assessments=[
            "comprehensive_medical_evaluation",
            "cardiac_assessment",
            "liver_function_tests",
            "drug_screen",
            "psychological_evaluation"
        ],
        monitoring_parameters=[
            "continuous_ecg",
            "blood_pressure",
            "liver_enzymes",
            "electrolytes",
            "neurological_status",
            "withdrawal_symptoms"
        ],
        safety_protocols=[
            "medical_supervision_24h",
            "cardiac_monitoring",
            "emergency_medical_team",
            "intensive_aftercare"
        ],
        expected_outcomes=[
            "opioid_withdrawal_interruption",
            "craving_reduction",
            "psychological_insights",
            "motivation_enhancement"
        ]
    )


class TherapyCoordinatorAgent(BaseAgent):
    """
    AI Therapy Coordination Agent for addiction recovery
    
    Capabilities:
    - Ketamine therapy scheduling and optimization
    - Plant medicine protocol coordination
    - Readiness assessment and preparation
    - Integration therapy management
    - Safety monitoring and risk assessment
    - Multi-modal therapy sequencing
    - Outcome tracking and protocol optimization
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        
        # Agent identification
        self.agent_type = "therapy_coordinator_agent"
        self.version = "1.0.0"
        self.description = "AI Therapy Coordination and Protocol Management"
        
        # Agent capabilities
        self.capabilities = [
            AgentCapability.THERAPY_COORDINATION,
            AgentCapability.TREATMENT_OPTIMIZATION,
            AgentCapability.REAL_TIME_MONITORING,
            AgentCapability.DATA_ANALYSIS
        ]
        
        self.priority_level = AgentPriority.HIGH
        
        # Therapy management state
        self.active_protocols: Dict[str, TherapyProtocol] = {}  # patient_id -> protocol
        self.scheduled_sessions: Dict[str, List[TherapySession]] = {}  # patient_id -> sessions
        self.readiness_assessments: Dict[str, List[ReadinessAssessment]] = {}
        self.therapy_history: Dict[str, List[TherapySession]] = {}
        
        # Protocol library
        self.protocol_library = {
            "ketamine_depression_001": TherapyProtocols.KETAMINE_DEPRESSION_ADDICTION,
            "psilocybin_addiction_001": TherapyProtocols.PSILOCYBIN_ADDICTION,
            "ibogaine_detox_001": TherapyProtocols.IBOGAINE_OPIOID_DETOX
        }
        
        # Therapist and facility management
        self.therapist_availability: Dict[str, Dict[str, Any]] = {}
        self.facility_scheduling: Dict[str, List[float]] = {}  # facility_id -> booked times
        
        # Safety and contraindication database
        self.contraindication_matrix = {
            TherapyType.KETAMINE_IV: {
                "medications": ["maoi", "stimulants"],
                "conditions": ["uncontrolled_hypertension", "psychosis"],
                "interactions": ["alcohol", "benzodiazepines"]
            },
            TherapyType.PSILOCYBIN: {
                "medications": ["ssri", "antipsychotics"],
                "conditions": ["bipolar_disorder", "psychosis"],
                "interactions": ["lithium", "tramadol"]
            },
            TherapyType.IBOGAINE: {
                "medications": ["cardiac_drugs", "liver_toxic_drugs"],
                "conditions": ["cardiac_disease", "liver_disease"],
                "interactions": ["benzodiazepines", "alcohol"]
            }
        }
        
        # Optimization algorithms
        self.optimization_algorithms = {
            "dosage_optimization": self._optimize_dosage,
            "timing_optimization": self._optimize_session_timing,
            "sequence_optimization": self._optimize_therapy_sequence
        }
        
        # Performance metrics
        self.successful_sessions = 0
        self.protocol_completions = 0
        self.adverse_events = 0
        self.patient_satisfaction_scores = []
        
        # Machine learning models
        self.ml_models = {
            "readiness_predictor": "gradient_boosting_classifier",
            "outcome_predictor": "deep_neural_network",
            "dosage_optimizer": "bayesian_optimization"
        }
        
        # Integration therapy settings
        self.integration_protocols = {
            "immediate": "0-24h post session",
            "short_term": "1-7 days post session", 
            "medium_term": "1-4 weeks post session",
            "long_term": "1-6 months post session"
        }
    
    async def initialize(self) -> bool:
        """Initialize therapy coordinator agent"""
        try:
            self.logger.info("Initializing Therapy Coordinator Agent...")
            
            # Load therapy protocols
            await self._load_therapy_protocols()
            
            # Initialize therapist scheduling
            await self._initialize_therapist_scheduling()
            
            # Setup safety monitoring
            await self._setup_safety_monitoring()
            
            # Initialize ML models
            await self._initialize_ml_models()
            
            # Start therapy coordination
            await self._start_therapy_coordination()
            
            self.logger.info("Therapy Coordinator Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Therapy Coordinator Agent initialization failed: {e}")
            return False
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages for therapy coordination"""
        try:
            message_type = message.message_type
            content = message.content
            
            if message_type == "therapy_request":
                return await self._handle_therapy_request(message)
            elif message_type == "readiness_assessment_request":
                return await self._handle_readiness_assessment(message)
            elif message_type == "session_scheduling_request":
                return await self._handle_session_scheduling(message)
            elif message_type == "session_completion":
                return await self._handle_session_completion(message)
            elif message_type == "integration_support_request":
                return await self._handle_integration_support(message)
            elif message_type == "therapy_optimization_request":
                return await self._handle_optimization_request(message)
            elif message_type == "adverse_event_report":
                return await self._handle_adverse_event(message)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Message processing error: {e}")
            return None
    
    async def handle_patient_update(self, patient_context: PatientContext):
        """Handle patient context updates for therapy optimization"""
        patient_id = patient_context.patient_id
        
        # Assess therapy readiness
        readiness_needed = await self._assess_therapy_readiness_needs(patient_context)
        
        if readiness_needed["assessment_required"]:
            await self._conduct_readiness_assessment(patient_id, readiness_needed)
    
    async def handle_emergency(self, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle therapy-related emergencies"""
        try:
            emergency_type = emergency_data.get("type")
            patient_id = emergency_data.get("patient_id")
            
            self.logger.critical(f"THERAPY EMERGENCY: {emergency_type} for patient {patient_id}")
            
            if emergency_type == "adverse_reaction":
                return await self._handle_therapy_adverse_reaction(patient_id, emergency_data)
            elif emergency_type == "psychological_crisis":
                return await self._handle_psychological_crisis(patient_id, emergency_data)
            elif emergency_type == "medical_emergency":
                return await self._handle_medical_emergency(patient_id, emergency_data)
            else:
                return await self._handle_general_therapy_emergency(patient_id, emergency_data)
                
        except Exception as e:
            self.logger.error(f"Therapy emergency handling failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_therapy_request(self, message: AgentMessage) -> AgentMessage:
        """Handle therapy protocol requests"""
        content = message.content
        patient_id = content.get("patient_id")
        therapy_type = TherapyType(content.get("therapy_type"))
        indication = content.get("indication")
        
        # Assess eligibility and readiness
        eligibility = await self._assess_therapy_eligibility(patient_id, therapy_type, indication)
        
        if not eligibility["eligible"]:
            return AgentMessage(
                message_id="",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="therapy_request_denied",
                content={
                    "patient_id": patient_id,
                    "therapy_type": therapy_type.value,
                    "reason": eligibility["reason"],
                    "recommendations": eligibility.get("alternatives", [])
                },
                priority=AgentPriority.NORMAL,
                timestamp=time.time()
            )
        
        # Find appropriate protocol
        protocol = await self._select_therapy_protocol(patient_id, therapy_type, indication)
        
        if not protocol:
            return AgentMessage(
                message_id="",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="therapy_protocol_not_found",
                content={"error": "No suitable protocol found"},
                priority=AgentPriority.NORMAL,
                timestamp=time.time()
            )
        
        # Create therapy plan
        therapy_plan = await self._create_therapy_plan(patient_id, protocol)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="therapy_plan_created",
            content=therapy_plan,
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    async def _assess_therapy_eligibility(self, patient_id: str, therapy_type: TherapyType, 
                                        indication: str) -> Dict[str, Any]:
        """Assess patient eligibility for therapy"""
        patient_context = self.get_patient_context(patient_id)
        if not patient_context:
            return {"eligible": False, "reason": "Patient context not available"}
        
        # Check contraindications
        contraindications = self.contraindication_matrix.get(therapy_type, {})
        
        # Medical contraindications
        if patient_context.treatment_history:
            for condition in contraindications.get("conditions", []):
                # Would check patient medical history
                pass
        
        # Medication interactions
        current_medications = patient_context.medications
        for med in current_medications:
            med_name = med.get("name", "").lower()
            for contraindicated_med in contraindications.get("medications", []):
                if contraindicated_med in med_name:
                    return {
                        "eligible": False,
                        "reason": f"Contraindicated medication: {med_name}",
                        "alternatives": ["medication_adjustment_first"]
                    }
        
        # Treatment phase appropriateness
        if therapy_type == TherapyType.IBOGAINE and patient_context.treatment_phase != "detox":
            return {
                "eligible": False,
                "reason": "Ibogaine only appropriate during detox phase",
                "alternatives": ["ketamine_therapy", "psilocybin_therapy"]
            }
        
        return {"eligible": True, "reason": "All eligibility criteria met"}
    
    async def _select_therapy_protocol(self, patient_id: str, therapy_type: TherapyType, 
                                     indication: str) -> Optional[TherapyProtocol]:
        """Select appropriate therapy protocol"""
        
        # Map therapy types and indications to protocols
        protocol_mapping = {
            (TherapyType.KETAMINE_IV, "depression"): "ketamine_depression_001",
            (TherapyType.PSILOCYBIN, "addiction"): "psilocybin_addiction_001",
            (TherapyType.IBOGAINE, "opioid_detox"): "ibogaine_detox_001"
        }
        
        protocol_id = protocol_mapping.get((therapy_type, indication))
        
        if protocol_id and protocol_id in self.protocol_library:
            return self.protocol_library[protocol_id]
        
        return None
    
    async def _create_therapy_plan(self, patient_id: str, protocol: TherapyProtocol) -> Dict[str, Any]:
        """Create comprehensive therapy plan"""
        
        # Calculate optimal dosage
        optimal_dosage = await self._calculate_optimal_dosage(patient_id, protocol)
        
        # Schedule preparation phase
        preparation_start = time.time() + (24 * 3600)  # Start tomorrow
        session_time = preparation_start + (protocol.preparation_days * 24 * 3600)
        integration_end = session_time + (protocol.integration_days * 24 * 3600)
        
        # Assign therapist
        therapist = await self._assign_therapist(patient_id, protocol.therapy_type)
        
        therapy_plan = {
            "patient_id": patient_id,
            "protocol_id": protocol.protocol_id,
            "therapy_type": protocol.therapy_type.value,
            "preparation_phase": {
                "start_date": preparation_start,
                "duration_days": protocol.preparation_days,
                "activities": [
                    "medical_clearance",
                    "psychological_preparation",
                    "set_and_setting_optimization",
                    "expectation_management"
                ]
            },
            "therapy_session": {
                "scheduled_time": session_time,
                "duration_hours": protocol.duration_hours,
                "dosage_mg": optimal_dosage,
                "therapist_id": therapist["therapist_id"],
                "setting": "clinical_facility",
                "monitoring_level": "continuous"
            },
            "integration_phase": {
                "start_date": session_time + (24 * 3600),
                "duration_days": protocol.integration_days,
                "activities": [
                    "integration_therapy_sessions",
                    "journaling_and_reflection",
                    "lifestyle_modifications",
                    "follow_up_assessments"
                ]
            },
            "safety_protocols": protocol.safety_protocols,
            "expected_outcomes": protocol.expected_outcomes,
            "total_duration_days": protocol.preparation_days + 1 + protocol.integration_days
        }
        
        return therapy_plan
    
    async def _calculate_optimal_dosage(self, patient_id: str, protocol: TherapyProtocol) -> float:
        """Calculate optimal dosage for patient"""
        patient_context = self.get_patient_context(patient_id)
        
        # Base dosage calculation
        min_dose, max_dose = protocol.dosage_range
        
        # Factors affecting dosage
        factors = {
            "weight": 70.0,  # kg - would get from patient data
            "age": 35.0,     # years
            "therapy_experience": 0.0,  # 0.0 to 1.0
            "sensitivity": 0.5,  # 0.0 to 1.0
            "treatment_resistance": 0.3  # 0.0 to 1.0
        }
        
        # Dosage algorithm
        if protocol.therapy_type == TherapyType.KETAMINE_IV:
            # mg/kg dosing
            base_dose = (min_dose + max_dose) / 2  # Start with middle dose
            
            # Adjust for treatment resistance
            if factors["treatment_resistance"] > 0.5:
                base_dose *= 1.2
            
            # Adjust for sensitivity
            if factors["sensitivity"] > 0.7:
                base_dose *= 0.8
            
            # Final dose in mg
            optimal_dosage = base_dose * factors["weight"]
            
        else:
            # Absolute dosing for psychedelics
            base_dose = min_dose + (max_dose - min_dose) * 0.6  # Start at 60% of range
            
            # Adjust for experience
            if factors["therapy_experience"] > 0.5:
                base_dose *= 1.1
            
            optimal_dosage = base_dose
        
        # Safety bounds
        optimal_dosage = max(min_dose * factors.get("weight", 70), 
                           min(max_dose * factors.get("weight", 70), optimal_dosage))
        
        return round(optimal_dosage, 1)
    
    async def _assign_therapist(self, patient_id: str, therapy_type: TherapyType) -> Dict[str, Any]:
        """Assign optimal therapist for therapy session"""
        
        # Get available therapists
        available_therapists = []
        for therapist_id, therapist_data in self.therapist_availability.items():
            if (therapy_type.value in therapist_data.get("specializations", []) and
                therapist_data.get("available", True)):
                available_therapists.append({
                    "therapist_id": therapist_id,
                    "experience_score": therapist_data.get("experience_score", 0.5),
                    "patient_rating": therapist_data.get("average_rating", 4.0),
                    "specializations": therapist_data.get("specializations", [])
                })
        
        if not available_therapists:
            # Return default/emergency therapist
            return {
                "therapist_id": "default_therapist_001",
                "experience_score": 0.8,
                "specializations": [therapy_type.value]
            }
        
        # Select best therapist based on experience and ratings
        best_therapist = max(available_therapists, 
                           key=lambda t: t["experience_score"] * t["patient_rating"])
        
        return best_therapist
    
    async def _handle_readiness_assessment(self, message: AgentMessage) -> AgentMessage:
        """Handle readiness assessment requests"""
        content = message.content
        patient_id = content.get("patient_id")
        therapy_type = TherapyType(content.get("therapy_type"))
        
        # Conduct comprehensive readiness assessment
        assessment = await self._conduct_readiness_assessment(patient_id, {"therapy_type": therapy_type})
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="readiness_assessment_complete",
            content=assessment,
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _conduct_readiness_assessment(self, patient_id: str, 
                                          assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct comprehensive readiness assessment"""
        therapy_type = assessment_data.get("therapy_type", TherapyType.KETAMINE_IV)
        
        # Psychological readiness factors
        psychological_factors = {
            "motivation_level": 0.8,
            "emotional_stability": 0.7,
            "cognitive_functioning": 0.9,
            "insight_capacity": 0.6,
            "openness_to_experience": 0.8
        }
        
        psychological_readiness = sum(psychological_factors.values()) / len(psychological_factors)
        
        # Set and setting evaluation
        setting_factors = {
            "therapeutic_alliance": 0.8,
            "environmental_safety": 0.9,
            "support_system": 0.7,
            "schedule_flexibility": 0.8
        }
        
        set_and_setting_score = sum(setting_factors.values()) / len(setting_factors)
        
        # Integration capacity
        integration_factors = {
            "previous_therapy_experience": 0.5,
            "reflection_skills": 0.7,
            "lifestyle_stability": 0.6,
            "social_support": 0.8
        }
        
        integration_capacity = sum(integration_factors.values()) / len(integration_factors)
        
        # Overall readiness calculation
        overall_readiness = (psychological_readiness + set_and_setting_score + integration_capacity) / 3
        
        # Determine readiness level
        if overall_readiness >= 0.8:
            readiness_level = ReadinessLevel.OPTIMAL
        elif overall_readiness >= 0.7:
            readiness_level = ReadinessLevel.READY
        elif overall_readiness >= 0.5:
            readiness_level = ReadinessLevel.PREPARING
        else:
            readiness_level = ReadinessLevel.NOT_READY
        
        # Generate recommendations
        recommendations = []
        if psychological_readiness < 0.7:
            recommendations.append("Additional psychological preparation needed")
        if set_and_setting_score < 0.7:
            recommendations.append("Optimize therapeutic setting and support")
        if integration_capacity < 0.6:
            recommendations.append("Develop integration skills and support network")
        
        assessment = ReadinessAssessment(
            assessment_id=f"readiness_{int(time.time())}_{patient_id}",
            patient_id=patient_id,
            timestamp=time.time(),
            therapy_type=therapy_type,
            readiness_level=readiness_level,
            psychological_readiness=psychological_readiness,
            medical_clearance=True,  # Would verify from medical records
            set_and_setting_score=set_and_setting_score,
            support_system_strength=setting_factors["support_system"],
            integration_capacity=integration_capacity,
            risk_factors=[],  # Would identify from assessment
            recommendations=recommendations,
            estimated_optimal_timing=time.time() + (7 * 24 * 3600) if readiness_level == ReadinessLevel.READY else None
        )
        
        # Store assessment
        if patient_id not in self.readiness_assessments:
            self.readiness_assessments[patient_id] = []
        self.readiness_assessments[patient_id].append(assessment)
        
        return {
            "assessment_id": assessment.assessment_id,
            "readiness_level": readiness_level.value,
            "overall_readiness_score": overall_readiness,
            "psychological_readiness": psychological_readiness,
            "set_and_setting_score": set_and_setting_score,
            "integration_capacity": integration_capacity,
            "recommendations": recommendations,
            "estimated_optimal_timing": assessment.estimated_optimal_timing
        }
    
    # Additional methods for message handling
    async def _handle_session_scheduling(self, message: AgentMessage) -> AgentMessage:
        """Handle therapy session scheduling"""
        content = message.content
        patient_id = content.get("patient_id")
        protocol_id = content.get("protocol_id")
        preferred_time = content.get("preferred_time")
        
        # Get protocol
        protocol = self.protocol_library.get(protocol_id)
        if not protocol:
            return AgentMessage(
                message_id="",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="scheduling_error",
                content={"error": "Protocol not found"},
                priority=AgentPriority.NORMAL,
                timestamp=time.time()
            )
        
        # Find optimal scheduling time
        optimal_time = await self._find_optimal_session_time(patient_id, protocol, preferred_time)
        
        # Create therapy session
        session = TherapySession(
            session_id=f"session_{int(time.time())}_{patient_id}",
            patient_id=patient_id,
            therapy_type=protocol.therapy_type,
            protocol_id=protocol_id,
            scheduled_time=optimal_time,
            actual_start_time=None,
            duration_minutes=int(protocol.duration_hours * 60),
            dosage_mg=await self._calculate_optimal_dosage(patient_id, protocol),
            setting="clinical_facility",
            therapist_id=(await self._assign_therapist(patient_id, protocol.therapy_type))["therapist_id"],
            co_therapist_id=None,
            pre_session_vitals=None,
            post_session_vitals=None,
            subjective_effects=None,
            integration_notes=None,
            outcomes=None,
            adverse_events=[],
            session_rating=None
        )
        
        # Store scheduled session
        if patient_id not in self.scheduled_sessions:
            self.scheduled_sessions[patient_id] = []
        self.scheduled_sessions[patient_id].append(session)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="session_scheduled",
            content={
                "session_id": session.session_id,
                "scheduled_time": optimal_time,
                "therapist_id": session.therapist_id,
                "preparation_required": True
            },
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    async def _find_optimal_session_time(self, patient_id: str, protocol: TherapyProtocol, 
                                       preferred_time: Optional[float]) -> float:
        """Find optimal time for therapy session"""
        # If preferred time is given and available, use it
        if preferred_time:
            # Check therapist availability
            # Check facility availability
            # For now, just return preferred time
            return preferred_time
        
        # Otherwise, find optimal time based on various factors
        current_time = time.time()
        
        # Optimal times for different therapies
        optimal_hours = {
            TherapyType.KETAMINE_IV: 10,  # 10 AM
            TherapyType.PSILOCYBIN: 9,    # 9 AM
            TherapyType.IBOGAINE: 8       # 8 AM (long duration)
        }
        
        optimal_hour = optimal_hours.get(protocol.therapy_type, 10)
        
        # Schedule for next available day at optimal hour
        tomorrow = current_time + (24 * 3600)
        tomorrow_date = datetime.fromtimestamp(tomorrow)
        optimal_time = tomorrow_date.replace(hour=optimal_hour, minute=0, second=0)
        
        return optimal_time.timestamp()
    
    async def _handle_session_completion(self, message: AgentMessage) -> AgentMessage:
        """Handle therapy session completion"""
        content = message.content
        session_id = content.get("session_id")
        patient_id = content.get("patient_id")
        outcomes = content.get("outcomes", {})
        adverse_events = content.get("adverse_events", [])
        session_rating = content.get("session_rating")
        
        # Find and update session
        session = None
        if patient_id in self.scheduled_sessions:
            for s in self.scheduled_sessions[patient_id]:
                if s.session_id == session_id:
                    session = s
                    break
        
        if session:
            session.outcomes = outcomes
            session.adverse_events = adverse_events
            session.session_rating = session_rating
            session.actual_start_time = time.time()
            
            # Move to therapy history
            if patient_id not in self.therapy_history:
                self.therapy_history[patient_id] = []
            self.therapy_history[patient_id].append(session)
            
            # Remove from scheduled sessions
            self.scheduled_sessions[patient_id].remove(session)
            
            self.successful_sessions += 1
            if adverse_events:
                self.adverse_events += len(adverse_events)
            
            if session_rating:
                self.patient_satisfaction_scores.append(session_rating)
        
        # Schedule integration support
        integration_plan = await self._create_integration_plan(patient_id, session)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="session_completion_processed",
            content={
                "session_id": session_id,
                "integration_plan": integration_plan,
                "follow_up_scheduled": True
            },
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    async def _create_integration_plan(self, patient_id: str, session: Optional[TherapySession]) -> Dict[str, Any]:
        """Create integration support plan"""
        if not session:
            return {"error": "Session not found"}
        
        # Integration timeline based on therapy type
        integration_timeline = {
            TherapyType.KETAMINE_IV: {
                "immediate": 1,      # 1 day
                "short_term": 7,     # 1 week
                "medium_term": 21,   # 3 weeks
                "long_term": 84      # 12 weeks
            },
            TherapyType.PSILOCYBIN: {
                "immediate": 3,      # 3 days
                "short_term": 14,    # 2 weeks
                "medium_term": 42,   # 6 weeks
                "long_term": 168     # 24 weeks
            },
            TherapyType.IBOGAINE: {
                "immediate": 7,      # 1 week
                "short_term": 30,    # 1 month
                "medium_term": 90,   # 3 months
                "long_term": 365     # 1 year
            }
        }
        
        timeline = integration_timeline.get(session.therapy_type, integration_timeline[TherapyType.KETAMINE_IV])
        current_time = time.time()
        
        integration_plan = {
            "patient_id": patient_id,
            "session_id": session.session_id,
            "phases": {
                "immediate": {
                    "start_time": current_time,
                    "duration_days": timeline["immediate"],
                    "activities": ["rest_and_reflection", "gentle_integration", "journaling"]
                },
                "short_term": {
                    "start_time": current_time + (timeline["immediate"] * 24 * 3600),
                    "duration_days": timeline["short_term"],
                    "activities": ["integration_therapy", "lifestyle_changes", "meaning_making"]
                },
                "medium_term": {
                    "start_time": current_time + (timeline["short_term"] * 24 * 3600),
                    "duration_days": timeline["medium_term"],
                    "activities": ["behavior_change", "relationship_work", "ongoing_therapy"]
                },
                "long_term": {
                    "start_time": current_time + (timeline["medium_term"] * 24 * 3600),
                    "duration_days": timeline["long_term"],
                    "activities": ["maintenance", "follow_up_assessments", "booster_sessions"]
                }
            },
            "support_resources": [
                "integration_therapist",
                "peer_support_groups",
                "online_resources",
                "follow_up_appointments"
            ]
        }
        
        return integration_plan
    
    async def _handle_integration_support(self, message: AgentMessage) -> AgentMessage:
        """Handle integration support requests"""
        content = message.content
        patient_id = content.get("patient_id")
        integration_phase = content.get("phase", "immediate")
        support_type = content.get("support_type", "general")
        
        # Provide phase-appropriate integration support
        support_plan = await self._create_integration_support(patient_id, integration_phase, support_type)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="integration_support_provided",
            content=support_plan,
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _create_integration_support(self, patient_id: str, phase: str, support_type: str) -> Dict[str, Any]:
        """Create specific integration support plan"""
        support_activities = {
            "immediate": {
                "general": ["rest", "hydration", "gentle_reflection"],
                "challenging": ["crisis_support", "grounding_techniques", "emergency_contact"],
                "insights": ["journal_writing", "voice_recordings", "art_expression"]
            },
            "short_term": {
                "general": ["integration_therapy", "meaning_making", "lifestyle_planning"],
                "challenging": ["trauma_processing", "specialized_therapy", "additional_support"],
                "insights": ["insight_exploration", "behavior_planning", "goal_setting"]
            },
            "medium_term": {
                "general": ["behavior_change", "relationship_work", "skill_building"],
                "challenging": ["ongoing_therapy", "medication_adjustment", "specialist_referral"],
                "insights": ["implementation", "practice", "refinement"]
            },
            "long_term": {
                "general": ["maintenance", "monitoring", "lifestyle_optimization"],
                "challenging": ["long_term_therapy", "community_support", "professional_help"],
                "insights": ["integration_completion", "wisdom_sharing", "service_to_others"]
            }
        }
        
        activities = support_activities.get(phase, {}).get(support_type, ["general_support"])
        
        return {
            "patient_id": patient_id,
            "phase": phase,
            "support_type": support_type,
            "recommended_activities": activities,
            "duration_estimate": "varies",
            "resources_provided": True
        }
    
    async def _handle_optimization_request(self, message: AgentMessage) -> AgentMessage:
        """Handle therapy optimization requests"""
        content = message.content
        patient_id = content.get("patient_id")
        optimization_type = content.get("optimization_type", "comprehensive")
        
        # Perform therapy optimization
        optimization_result = await self._optimize_therapy_protocol(patient_id, optimization_type)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="therapy_optimization_complete",
            content=optimization_result,
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _optimize_therapy_protocol(self, patient_id: str, optimization_type: str) -> Dict[str, Any]:
        """Optimize therapy protocol for patient"""
        # Get therapy history
        history = self.therapy_history.get(patient_id, [])
        
        if not history:
            return {"success": False, "error": "No therapy history available"}
        
        # Analyze outcomes
        outcomes = []
        satisfaction_scores = []
        
        for session in history:
            if session.outcomes:
                outcomes.append(session.outcomes)
            if session.session_rating:
                satisfaction_scores.append(session.session_rating)
        
        # Calculate effectiveness metrics
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.0
        
        # Generate optimization recommendations
        recommendations = []
        if avg_satisfaction < 7.0:  # Scale of 1-10
            recommendations.append("Consider alternative therapy modalities")
            recommendations.append("Adjust dosage protocols")
            recommendations.append("Enhance preparation and integration support")
        
        if optimization_type == "dosage":
            dosage_rec = await self._optimize_dosage_recommendations(patient_id, history)
            recommendations.extend(dosage_rec)
        
        return {
            "success": True,
            "patient_id": patient_id,
            "optimization_type": optimization_type,
            "current_satisfaction": avg_satisfaction,
            "recommendations": recommendations,
            "sessions_analyzed": len(history)
        }
    
    async def _optimize_dosage_recommendations(self, patient_id: str, history: List[TherapySession]) -> List[str]:
        """Generate dosage optimization recommendations"""
        recommendations = []
        
        # Analyze dosage vs outcomes
        for session in history:
            if session.outcomes and session.dosage_mg:
                # Would implement sophisticated dosage analysis
                if session.session_rating and session.session_rating < 6:
                    if session.dosage_mg < 50:  # Example threshold
                        recommendations.append("Consider dosage increase for enhanced efficacy")
                    elif session.dosage_mg > 150:
                        recommendations.append("Consider dosage reduction to minimize side effects")
        
        return recommendations
    
    async def _handle_adverse_event(self, message: AgentMessage) -> AgentMessage:
        """Handle adverse event reports"""
        content = message.content
        patient_id = content.get("patient_id")
        event_type = content.get("event_type")
        severity = content.get("severity", "moderate")
        session_id = content.get("session_id")
        
        # Log adverse event
        self.adverse_events += 1
        
        # Determine response based on severity
        if severity == "severe":
            # Immediate medical attention
            response_actions = [
                "immediate_medical_evaluation",
                "session_termination",
                "emergency_protocols_activated",
                "medical_team_notification"
            ]
        elif severity == "moderate":
            response_actions = [
                "enhanced_monitoring",
                "supportive_care",
                "medical_consultation",
                "protocol_adjustment"
            ]
        else:  # mild
            response_actions = [
                "documentation",
                "supportive_care",
                "monitoring_continuation",
                "reassurance"
            ]
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="adverse_event_processed",
            content={
                "patient_id": patient_id,
                "event_type": event_type,
                "severity": severity,
                "response_actions": response_actions,
                "follow_up_required": severity in ["severe", "moderate"]
            },
            priority=AgentPriority.CRITICAL if severity == "severe" else AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    # Helper methods for initialization and management
    async def _assess_therapy_readiness_needs(self, patient_context: PatientContext) -> Dict[str, Any]:
        """Assess if patient needs therapy readiness assessment"""
        # Determine if assessment is needed based on treatment phase and history
        return {
            "assessment_required": True,  # Simplified logic
            "therapy_type": TherapyType.KETAMINE_IV,
            "priority": "high"
        }
    
    async def _load_therapy_protocols(self):
        """Load therapy protocols"""
        # Protocol library already initialized in __init__
        self.logger.info(f"Loaded {len(self.protocol_library)} therapy protocols")
    
    async def _initialize_therapist_scheduling(self):
        """Initialize therapist availability and scheduling"""
        # Initialize therapist database
        self.therapist_availability = {
            "therapist_001": {
                "available": True,
                "specializations": ["ketamine_iv", "integration_therapy"],
                "experience_score": 0.9,
                "average_rating": 4.8
            },
            "therapist_002": {
                "available": True,
                "specializations": ["psilocybin", "mdma", "integration_therapy"],
                "experience_score": 0.85,
                "average_rating": 4.7
            },
            "therapist_003": {
                "available": True,
                "specializations": ["ibogaine", "traditional_therapy"],
                "experience_score": 0.95,
                "average_rating": 4.9
            }
        }
        
        self.logger.info("Therapist scheduling initialized")
    
    async def _setup_safety_monitoring(self):
        """Setup safety monitoring protocols"""
        # Initialize safety monitoring systems
        self.logger.info("Safety monitoring protocols established")
    
    async def _initialize_ml_models(self):
        """Initialize machine learning models"""
        # Would load trained ML models
        self.logger.info("ML models for therapy optimization initialized")
    
    async def _start_therapy_coordination(self):
        """Start therapy coordination services"""
        # Would start background coordination tasks
        self.logger.info("Therapy coordination services started")
    
    # Optimization algorithm implementations
    async def _optimize_dosage(self, patient_data: Dict[str, Any], therapy_type: TherapyType) -> float:
        """Optimize dosage using ML algorithms"""
        # Simplified dosage optimization
        base_doses = {
            TherapyType.KETAMINE_IV: 1.0,  # mg/kg
            TherapyType.PSILOCYBIN: 20.0,  # mg
            TherapyType.IBOGAINE: 20.0     # mg/kg
        }
        
        return base_doses.get(therapy_type, 1.0)
    
    async def _optimize_session_timing(self, patient_data: Dict[str, Any], therapy_type: TherapyType) -> float:
        """Optimize session timing"""
        # Return optimal time (simplified)
        return time.time() + (7 * 24 * 3600)  # 1 week from now
    
    async def _optimize_therapy_sequence(self, patient_data: Dict[str, Any]) -> List[TherapyType]:
        """Optimize therapy sequence"""
        # Return optimal sequence based on patient data
        return [TherapyType.KETAMINE_IV, TherapyType.INTEGRATION_THERAPY]
    
    # Emergency handling methods
    async def _handle_therapy_adverse_reaction(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle therapy adverse reaction emergency"""
        reaction_type = emergency_data.get("reaction_type")
        severity = emergency_data.get("severity", "moderate")
        
        actions_taken = [
            "therapy_session_terminated",
            "medical_evaluation_initiated",
            "supportive_care_provided",
            "adverse_event_documented"
        ]
        
        if severity == "severe":
            actions_taken.extend([
                "emergency_medical_services_called",
                "intensive_monitoring_activated",
                "family_notified"
            ])
        
        return {
            "success": True,
            "emergency_type": "adverse_reaction",
            "patient_id": patient_id,
            "actions_taken": actions_taken,
            "severity": severity
        }
    
    async def _handle_psychological_crisis(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle psychological crisis during therapy"""
        crisis_type = emergency_data.get("crisis_type")
        
        actions_taken = [
            "crisis_intervention_initiated",
            "psychological_support_provided",
            "session_support_enhanced",
            "follow_up_care_arranged"
        ]
        
        return {
            "success": True,
            "emergency_type": "psychological_crisis",
            "patient_id": patient_id,
            "actions_taken": actions_taken,
            "crisis_type": crisis_type
        }
    
    async def _handle_medical_emergency(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle medical emergency during therapy"""
        emergency_type = emergency_data.get("medical_emergency_type")
        
        actions_taken = [
            "emergency_medical_services_called",
            "immediate_medical_intervention",
            "therapy_session_terminated",
            "hospital_transport_arranged",
            "medical_team_notified"
        ]
        
        return {
            "success": True,
            "emergency_type": "medical_emergency",
            "patient_id": patient_id,
            "actions_taken": actions_taken,
            "medical_emergency_type": emergency_type
        }
    
    async def _handle_general_therapy_emergency(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general therapy emergency"""
        actions_taken = [
            "situation_assessed",
            "appropriate_protocols_activated",
            "support_provided",
            "monitoring_enhanced"
        ]
        
        return {
            "success": True,
            "emergency_type": "general",
            "patient_id": patient_id,
            "actions_taken": actions_taken
        }
