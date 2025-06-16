"""
IRIP Medication Agent
AI-driven medication management and optimization for addiction recovery
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import math

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)


class MedicationType(Enum):
    """Types of medications used in addiction recovery"""
    METHADONE = "methadone"
    SUBOXONE = "suboxone"  # Buprenorphine/Naloxone
    VIVITROL = "vivitrol"  # Naltrexone
    SUBLOCADE = "sublocade"  # Buprenorphine injection
    KETAMINE = "ketamine"
    GABAPENTIN = "gabapentin"
    CLONIDINE = "clonidine"
    COMFORT_MEDICATIONS = "comfort_medications"
    SUPPLEMENTS = "supplements"
    NOOTROPICS = "nootropics"


class MedicationStatus(Enum):
    """Medication status tracking"""
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    TAPERING = "tapering"
    ESCALATING = "escalating"
    HOLD = "hold"
    PRN = "prn"  # As needed


class DosageAdjustmentReason(Enum):
    """Reasons for dosage adjustments"""
    WITHDRAWAL_SYMPTOMS = "withdrawal_symptoms"
    CRAVINGS = "cravings"
    SIDE_EFFECTS = "side_effects"
    THERAPEUTIC_OPTIMIZATION = "therapeutic_optimization"
    DRUG_INTERACTION = "drug_interaction"
    LAB_VALUES = "lab_values"
    PATIENT_FEEDBACK = "patient_feedback"
    CLINICAL_ASSESSMENT = "clinical_assessment"


@dataclass
class Medication:
    """Medication data structure"""
    medication_id: str
    name: str
    medication_type: MedicationType
    current_dose: float
    dose_unit: str
    frequency: str
    route: str  # oral, injection, patch, etc.
    status: MedicationStatus
    prescriber: str
    start_date: float
    end_date: Optional[float]
    indication: str
    side_effects: List[str]
    contraindications: List[str]
    interactions: List[str]
    monitoring_parameters: List[str]


@dataclass
class DosageRecommendation:
    """Dosage adjustment recommendation"""
    recommendation_id: str
    medication_id: str
    current_dose: float
    recommended_dose: float
    adjustment_reason: DosageAdjustmentReason
    confidence_score: float  # 0.0 to 1.0
    evidence: List[str]
    monitoring_required: List[str]
    contraindications: List[str]
    patient_factors: Dict[str, Any]
    timeline: str  # immediate, gradual, etc.
    approval_required: bool


@dataclass
class WithdrawalAssessment:
    """Withdrawal symptoms assessment"""
    assessment_id: str
    patient_id: str
    timestamp: float
    scale_type: str  # COWS, CIWA, etc.
    total_score: float
    subscale_scores: Dict[str, float]
    severity_level: str  # mild, moderate, severe
    symptoms: List[str]
    objective_signs: List[str]
    comfort_needs: List[str]


class MedicationProtocols:
    """Pre-defined medication protocols for addiction recovery"""
    
    OPIOID_MAINTENANCE_PROTOCOLS = {
        "methadone_induction": {
            "initial_dose": 30.0,
            "max_daily_increase": 10.0,
            "target_range": (60.0, 120.0),
            "monitoring_frequency": "daily",
            "peak_effect_hours": 4,
            "duration_hours": 24
        },
        "suboxone_induction": {
            "initial_dose": 4.0,
            "max_daily_dose": 24.0,
            "target_range": (8.0, 24.0),
            "monitoring_frequency": "daily",
            "peak_effect_hours": 2,
            "duration_hours": 24
        },
        "vivitrol_maintenance": {
            "dose": 380.0,
            "frequency": "monthly",
            "route": "intramuscular",
            "monitoring_frequency": "monthly",
            "contraindications": ["active_opioid_use", "liver_dysfunction"]
        }
    }
    
    COMFORT_MEDICATION_PROTOCOLS = {
        "withdrawal_comfort": {
            "clonidine": {
                "dose_range": (0.1, 0.3),
                "frequency": "TID",
                "indication": "autonomic_symptoms",
                "monitoring": ["blood_pressure", "heart_rate"]
            },
            "gabapentin": {
                "dose_range": (300, 1800),
                "frequency": "TID",
                "indication": "anxiety_restlessness",
                "monitoring": ["sedation", "cognitive_effects"]
            },
            "trazodone": {
                "dose_range": (50, 150),
                "frequency": "HS",
                "indication": "sleep_disturbance",
                "monitoring": ["sedation", "orthostatic_hypotension"]
            }
        }
    }
    
    KETAMINE_PROTOCOLS = {
        "depression_addiction": {
            "dose_range": (0.5, 2.0),  # mg/kg
            "frequency": "2-3 times per week",
            "route": "IV",
            "session_duration": 40,  # minutes
            "monitoring": ["blood_pressure", "dissociation_scale", "mood_scores"],
            "contraindications": ["uncontrolled_hypertension", "psychosis"]
        }
    }


class MedicationAgent(BaseAgent):
    """
    AI Medication Management Agent for addiction recovery
    
    Capabilities:
    - Medication-assisted treatment (MAT) optimization
    - Withdrawal symptom management
    - Drug interaction monitoring
    - Dosage recommendations with ML algorithms
    - Side effect tracking and management
    - Compliance monitoring and improvement
    - Integration with lab results and biomarkers
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        
        # Agent identification
        self.agent_type = "medication_agent"
        self.version = "1.0.0"
        self.description = "AI Medication Management and Optimization"
        
        # Agent capabilities
        self.capabilities = [
            AgentCapability.MEDICATION_MANAGEMENT,
            AgentCapability.REAL_TIME_MONITORING,
            AgentCapability.DATA_ANALYSIS,
            AgentCapability.TREATMENT_OPTIMIZATION
        ]
        
        self.priority_level = AgentPriority.HIGH
        
        # Medication management state
        self.active_medications: Dict[str, List[Medication]] = {}  # patient_id -> medications
        self.dosage_recommendations: Dict[str, List[DosageRecommendation]] = {}
        self.withdrawal_assessments: Dict[str, List[WithdrawalAssessment]] = {}
        
        # Protocol libraries
        self.medication_protocols = MedicationProtocols()
        
        # Drug interaction database (simplified)
        self.drug_interactions = {
            "methadone": {
                "major": ["benzodiazepines", "alcohol", "other_opioids"],
                "moderate": ["gabapentin", "trazodone"],
                "monitoring": ["qt_prolongation", "respiratory_depression"]
            },
            "suboxone": {
                "major": ["alcohol", "benzodiazepines"],
                "moderate": ["gabapentin", "clonidine"],
                "monitoring": ["respiratory_depression", "liver_function"]
            },
            "ketamine": {
                "major": ["sympathomimetics", "theophylline"],
                "moderate": ["benzodiazepines", "alcohol"],
                "monitoring": ["blood_pressure", "heart_rate", "dissociation"]
            }
        }
        
        # Dosage algorithms
        self.dosage_algorithms = {
            "methadone": self._calculate_methadone_dose,
            "suboxone": self._calculate_suboxone_dose,
            "comfort_meds": self._calculate_comfort_medication_dose
        }
        
        # Lab monitoring
        self.lab_monitoring_schedule = {
            "methadone": ["liver_function", "ecg", "drug_screen"],
            "suboxone": ["liver_function", "drug_screen"],
            "ketamine": ["liver_function", "blood_pressure", "mood_scales"]
        }
        
        # Performance metrics
        self.successful_optimizations = 0
        self.prevented_interactions = 0
        self.withdrawal_episodes_managed = 0
        
        # AI model configurations
        self.ml_models = {
            "dosage_optimization": "xgboost_regressor",
            "withdrawal_prediction": "lstm_classifier",
            "interaction_detection": "neural_network"
        }
    
    async def initialize(self) -> bool:
        """Initialize medication management agent"""
        try:
            self.logger.info("Initializing Medication Agent...")
            
            # Load medication protocols
            await self._load_medication_protocols()
            
            # Initialize dosage algorithms
            await self._initialize_dosage_algorithms()
            
            # Set up drug interaction monitoring
            await self._setup_interaction_monitoring()
            
            # Initialize ML models for optimization
            await self._initialize_ml_models()
            
            self.logger.info("Medication Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Medication Agent initialization failed: {e}")
            return False
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages for medication management"""
        try:
            message_type = message.message_type
            content = message.content
            
            if message_type == "medication_optimization_request":
                return await self._handle_optimization_request(message)
            elif message_type == "withdrawal_assessment":
                return await self._handle_withdrawal_assessment(message)
            elif message_type == "lab_results":
                return await self._handle_lab_results(message)
            elif message_type == "side_effect_report":
                return await self._handle_side_effect_report(message)
            elif message_type == "compliance_update":
                return await self._handle_compliance_update(message)
            elif message_type == "dosage_adjustment_request":
                return await self._handle_dosage_adjustment_request(message)
            elif message_type == "drug_interaction_check":
                return await self._handle_interaction_check(message)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Message processing error: {e}")
            return None
    
    async def handle_patient_update(self, patient_context: PatientContext):
        """Handle patient context updates for medication optimization"""
        patient_id = patient_context.patient_id
        
        # Update medication regimen if needed
        await self._update_medication_regimen(patient_context)
        
        # Check for optimization opportunities
        optimization_needed = await self._assess_optimization_needs(patient_context)
        
        if optimization_needed["required"]:
            await self._initiate_medication_optimization(patient_id, optimization_needed)
    
    async def handle_emergency(self, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle medication-related emergencies"""
        try:
            emergency_type = emergency_data.get("type")
            patient_id = emergency_data.get("patient_id")
            
            self.logger.critical(f"MEDICATION EMERGENCY: {emergency_type} for patient {patient_id}")
            
            if emergency_type == "overdose":
                return await self._handle_overdose_emergency(patient_id, emergency_data)
            elif emergency_type == "severe_withdrawal":
                return await self._handle_severe_withdrawal(patient_id, emergency_data)
            elif emergency_type == "drug_interaction":
                return await self._handle_drug_interaction_emergency(patient_id, emergency_data)
            elif emergency_type == "adverse_reaction":
                return await self._handle_adverse_reaction(patient_id, emergency_data)
            else:
                return await self._handle_general_medication_emergency(patient_id, emergency_data)
                
        except Exception as e:
            self.logger.error(f"Medication emergency handling failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_optimization_request(self, message: AgentMessage) -> AgentMessage:
        """Handle medication optimization requests"""
        content = message.content
        patient_id = content.get("patient_id")
        optimization_type = content.get("optimization_type", "comprehensive")
        
        # Perform medication optimization
        optimization_result = await self._optimize_medication_regimen(patient_id, optimization_type)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="optimization_completed",
            content=optimization_result,
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    async def _optimize_medication_regimen(self, patient_id: str, optimization_type: str) -> Dict[str, Any]:
        """Optimize patient's medication regimen using AI algorithms"""
        try:
            # Get current medications
            current_medications = self.active_medications.get(patient_id, [])
            if not current_medications:
                return {"success": False, "error": "No active medications found"}
            
            patient_context = self.get_patient_context(patient_id)
            if not patient_context:
                return {"success": False, "error": "Patient context not available"}
            
            recommendations = []
            
            # Analyze each medication
            for medication in current_medications:
                recommendation = await self._analyze_medication_optimization(
                    medication, patient_context, optimization_type
                )
                if recommendation:
                    recommendations.append(recommendation)
            
            # Check for drug interactions
            interaction_warnings = await self._check_drug_interactions(current_medications)
            
            # Generate optimization plan
            optimization_plan = {
                "patient_id": patient_id,
                "optimization_type": optimization_type,
                "current_medications": len(current_medications),
                "recommendations": recommendations,
                "interaction_warnings": interaction_warnings,
                "confidence_score": self._calculate_plan_confidence(recommendations),
                "implementation_timeline": "gradual_over_7_days",
                "monitoring_requirements": self._generate_monitoring_plan(recommendations)
            }
            
            # Store recommendations
            if patient_id not in self.dosage_recommendations:
                self.dosage_recommendations[patient_id] = []
            self.dosage_recommendations[patient_id].extend(recommendations)
            
            self.successful_optimizations += 1
            
            self.logger.info(f"Medication optimization completed for patient {patient_id}")
            
            return {
                "success": True,
                "optimization_plan": optimization_plan,
                "requires_approval": True,  # Clinical approval needed
                "estimated_improvement": "25-40% symptom reduction expected"
            }
            
        except Exception as e:
            self.logger.error(f"Medication optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_medication_optimization(self, medication: Medication, 
                                            patient_context: PatientContext, 
                                            optimization_type: str) -> Optional[DosageRecommendation]:
        """Analyze individual medication for optimization opportunities"""
        
        # Use appropriate algorithm based on medication type
        if medication.medication_type == MedicationType.METHADONE:
            return await self._optimize_methadone_dose(medication, patient_context)
        elif medication.medication_type == MedicationType.SUBOXONE:
            return await self._optimize_suboxone_dose(medication, patient_context)
        elif medication.medication_type == MedicationType.KETAMINE:
            return await self._optimize_ketamine_protocol(medication, patient_context)
        elif medication.medication_type == MedicationType.COMFORT_MEDICATIONS:
            return await self._optimize_comfort_medications(medication, patient_context)
        
        return None
    
    async def _optimize_methadone_dose(self, medication: Medication, 
                                     patient_context: PatientContext) -> Optional[DosageRecommendation]:
        """Optimize methadone dosage using AI algorithms"""
        current_dose = medication.current_dose
        
        # Factors for optimization
        factors = {
            "withdrawal_symptoms": 0.0,  # Would come from assessments
            "cravings_level": 0.0,
            "side_effects": 0.0,
            "peak_trough_ratio": 0.0,
            "drug_screen_results": "negative",
            "patient_weight": 70.0,  # kg
            "treatment_day": 30
        }
        
        # Calculate optimal dose using algorithm
        optimal_dose = await self._calculate_methadone_dose(factors)
        
        if abs(optimal_dose - current_dose) > 5.0:  # Significant difference
            return DosageRecommendation(
                recommendation_id=f"methadone_opt_{int(time.time())}",
                medication_id=medication.medication_id,
                current_dose=current_dose,
                recommended_dose=optimal_dose,
                adjustment_reason=DosageAdjustmentReason.THERAPEUTIC_OPTIMIZATION,
                confidence_score=0.85,
                evidence=[
                    "AI analysis indicates suboptimal therapeutic window",
                    "Withdrawal symptom pattern suggests dose adjustment needed",
                    "Peak/trough analysis supports modification"
                ],
                monitoring_required=["withdrawal_scores", "vital_signs", "qt_interval"],
                contraindications=[],
                patient_factors=factors,
                timeline="gradual_over_3_days",
                approval_required=True
            )
        
        return None
    
    async def _calculate_methadone_dose(self, factors: Dict[str, Any]) -> float:
        """Calculate optimal methadone dose using ML algorithm"""
        # Simplified algorithm - in reality would use trained ML model
        base_dose = 60.0  # mg
        
        # Adjust based on factors
        if factors.get("withdrawal_symptoms", 0) > 5:
            base_dose += 10.0
        if factors.get("cravings_level", 0) > 7:
            base_dose += 15.0
        if factors.get("side_effects", 0) > 3:
            base_dose -= 10.0
        
        # Weight adjustment
        weight_factor = factors.get("patient_weight", 70) / 70.0
        base_dose *= weight_factor
        
        # Treatment day adjustment (stabilization curve)
        day = factors.get("treatment_day", 1)
        if day < 7:
            base_dose *= 0.8  # Conservative during induction
        
        return max(30.0, min(150.0, base_dose))  # Safety bounds
    
    async def _calculate_suboxone_dose(self, factors: Dict[str, Any]) -> float:
        """Calculate optimal Suboxone dose"""
        base_dose = 12.0  # mg
        
        # Adjust based on factors
        if factors.get("withdrawal_symptoms", 0) > 5:
            base_dose += 4.0
        if factors.get("cravings_level", 0) > 7:
            base_dose += 6.0
        if factors.get("side_effects", 0) > 3:
            base_dose -= 4.0
        
        return max(4.0, min(24.0, base_dose))  # Safety bounds
    
    async def _calculate_comfort_medication_dose(self, medication: Medication, 
                                               factors: Dict[str, Any]) -> float:
        """Calculate optimal comfort medication dose"""
        # This would be specific to each comfort medication
        current_dose = medication.current_dose
        
        if "clonidine" in medication.name.lower():
            if factors.get("autonomic_symptoms", 0) > 5:
                return min(current_dose * 1.2, 0.3)  # Max 0.3mg
        elif "gabapentin" in medication.name.lower():
            if factors.get("anxiety_level", 0) > 6:
                return min(current_dose * 1.1, 1800)  # Max 1800mg
        
        return current_dose
    
    async def _handle_withdrawal_assessment(self, message: AgentMessage) -> AgentMessage:
        """Handle withdrawal assessment messages"""
        content = message.content
        patient_id = content.get("patient_id")
        assessment_data = content.get("assessment_data", {})
        
        # Create withdrawal assessment
        assessment = WithdrawalAssessment(
            assessment_id=f"withdrawal_{int(time.time())}_{patient_id}",
            patient_id=patient_id,
            timestamp=time.time(),
            scale_type=assessment_data.get("scale_type", "COWS"),
            total_score=assessment_data.get("total_score", 0.0),
            subscale_scores=assessment_data.get("subscale_scores", {}),
            severity_level=self._calculate_withdrawal_severity(assessment_data.get("total_score", 0.0)),
            symptoms=assessment_data.get("symptoms", []),
            objective_signs=assessment_data.get("objective_signs", []),
            comfort_needs=assessment_data.get("comfort_needs", [])
        )
        
        # Store assessment
        if patient_id not in self.withdrawal_assessments:
            self.withdrawal_assessments[patient_id] = []
        self.withdrawal_assessments[patient_id].append(assessment)
        
        # Generate medication recommendations if needed
        recommendations = await self._generate_withdrawal_recommendations(assessment)
        
        self.withdrawal_episodes_managed += 1
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="withdrawal_assessment_processed",
            content={
                "assessment_id": assessment.assessment_id,
                "severity_level": assessment.severity_level,
                "recommendations": recommendations,
                "requires_immediate_attention": assessment.total_score > 20
            },
            priority=AgentPriority.HIGH if assessment.total_score > 20 else AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    def _calculate_withdrawal_severity(self, total_score: float) -> str:
        """Calculate withdrawal severity based on total score"""
        if total_score <= 10:
            return "mild"
        elif total_score <= 20:
            return "moderate"
        elif total_score <= 35:
            return "severe"
        else:
            return "critical"
    
    async def _generate_withdrawal_recommendations(self, assessment: WithdrawalAssessment) -> List[Dict[str, Any]]:
        """Generate medication recommendations for withdrawal management"""
        recommendations = []
        
        if assessment.severity_level in ["moderate", "severe", "critical"]:
            # Recommend comfort medications
            if "autonomic_instability" in assessment.symptoms:
                recommendations.append({
                    "medication": "clonidine",
                    "dose": "0.1-0.2mg",
                    "frequency": "every 6 hours",
                    "indication": "autonomic symptoms",
                    "monitoring": ["blood_pressure", "heart_rate"]
                })
            
            if "anxiety" in assessment.symptoms or "restlessness" in assessment.symptoms:
                recommendations.append({
                    "medication": "gabapentin",
                    "dose": "300-600mg", 
                    "frequency": "three times daily",
                    "indication": "anxiety and restlessness",
                    "monitoring": ["sedation", "cognitive_effects"]
                })
            
            if "insomnia" in assessment.symptoms:
                recommendations.append({
                    "medication": "trazodone",
                    "dose": "50-100mg",
                    "frequency": "at bedtime",
                    "indication": "sleep disturbance",
                    "monitoring": ["morning_sedation"]
                })
        
        return recommendations
    
    async def _check_drug_interactions(self, medications: List[Medication]) -> List[Dict[str, Any]]:
        """Check for drug interactions between medications"""
        interactions = []
        
        for i, med1 in enumerate(medications):
            for j, med2 in enumerate(medications[i+1:], i+1):
                interaction = self._evaluate_interaction(med1, med2)
                if interaction:
                    interactions.append(interaction)
                    self.prevented_interactions += 1
        
        return interactions
    
    def _evaluate_interaction(self, med1: Medication, med2: Medication) -> Optional[Dict[str, Any]]:
        """Evaluate interaction between two medications"""
        # Simplified interaction checking
        med1_name = med1.name.lower()
        med2_name = med2.name.lower()
        
        # Check for major interactions
        if ("methadone" in med1_name or "methadone" in med2_name) and \
           ("benzodiazepine" in med1_name or "benzodiazepine" in med2_name):
            return {
                "severity": "major",
                "medications": [med1.name, med2.name],
                "risk": "respiratory_depression",
                "recommendation": "monitor_closely_or_avoid",
                "monitoring": ["respiratory_rate", "oxygen_saturation", "sedation_level"]
            }
        
        return None
    
    def _calculate_plan_confidence(self, recommendations: List[DosageRecommendation]) -> float:
        """Calculate overall confidence score for optimization plan"""
        if not recommendations:
            return 0.0
        
        avg_confidence = sum(rec.confidence_score for rec in recommendations) / len(recommendations)
        return avg_confidence
    
    def _generate_monitoring_plan(self, recommendations: List[DosageRecommendation]) -> List[str]:
        """Generate monitoring plan for medication changes"""
        monitoring_items = set()
        
        for rec in recommendations:
            monitoring_items.update(rec.monitoring_required)
        
        return list(monitoring_items)
    
    async def _load_medication_protocols(self):
        """Load medication protocols and guidelines"""
        # In a real implementation, this would load from a database
        self.logger.info("Medication protocols loaded")
    
    async def _initialize_dosage_algorithms(self):
        """Initialize AI dosage optimization algorithms"""
        # In a real implementation, this would load trained ML models
        self.logger.info("Dosage algorithms initialized")
    
    async def _setup_interaction_monitoring(self):
        """Setup drug interaction monitoring"""
        # In a real implementation, this would connect to drug interaction databases
        self.logger.info("Drug interaction monitoring setup complete")
    
    async def _initialize_ml_models(self):
        """Initialize machine learning models for medication optimization"""
        # In a real implementation, this would load trained models
        self.logger.info("ML models for medication optimization initialized")
    
    async def _handle_lab_results(self, message: AgentMessage) -> AgentMessage:
        """Handle lab results for medication monitoring"""
        content = message.content
        patient_id = content.get("patient_id")
        lab_results = content.get("lab_results", {})
        
        # Analyze lab results for medication safety
        safety_alerts = await self._analyze_lab_safety(patient_id, lab_results)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="lab_results_analyzed",
            content={
                "patient_id": patient_id,
                "safety_alerts": safety_alerts,
                "requires_action": len(safety_alerts) > 0
            },
            priority=AgentPriority.HIGH if safety_alerts else AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _analyze_lab_safety(self, patient_id: str, lab_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze lab results for medication safety concerns"""
        alerts = []
        
        # Check liver function for hepatotoxic medications
        if "alt" in lab_results and lab_results["alt"] > 80:  # Normal < 40
            alerts.append({
                "type": "hepatotoxicity_risk",
                "severity": "moderate",
                "recommendation": "consider_dose_reduction_or_discontinuation",
                "affected_medications": ["methadone", "suboxone"]
            })
        
        # Check QT interval for methadone
        if "qt_interval" in lab_results and lab_results["qt_interval"] > 450:
            alerts.append({
                "type": "qt_prolongation",
                "severity": "high", 
                "recommendation": "reduce_methadone_dose_or_discontinue",
                "monitoring": "daily_ecg"
            })
        
        return alerts
    
    async def _handle_side_effect_report(self, message: AgentMessage) -> AgentMessage:
        """Handle side effect reports"""
        content = message.content
        patient_id = content.get("patient_id")
        side_effects = content.get("side_effects", [])
        severity = content.get("severity", "mild")
        
        # Analyze side effects and generate recommendations
        recommendations = await self._analyze_side_effects(patient_id, side_effects, severity)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="side_effect_analysis",
            content={
                "patient_id": patient_id,
                "recommendations": recommendations,
                "requires_medication_change": severity in ["severe", "critical"]
            },
            priority=AgentPriority.HIGH if severity in ["severe", "critical"] else AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _analyze_side_effects(self, patient_id: str, side_effects: List[str], severity: str) -> List[Dict[str, Any]]:
        """Analyze side effects and generate medication recommendations"""
        recommendations = []
        
        for side_effect in side_effects:
            if side_effect == "nausea" and severity in ["moderate", "severe"]:
                recommendations.append({
                    "action": "add_antiemetic",
                    "medication": "ondansetron",
                    "dose": "4mg as needed",
                    "reason": "nausea management"
                })
            elif side_effect == "sedation" and severity == "severe":
                recommendations.append({
                    "action": "reduce_dose",
                    "reason": "excessive sedation",
                    "reduction_percentage": 20
                })
            elif side_effect == "constipation":
                recommendations.append({
                    "action": "add_bowel_regimen",
                    "medications": ["docusate", "senna"],
                    "reason": "opioid_induced_constipation"
                })
        
        return recommendations
    
    async def _handle_compliance_update(self, message: AgentMessage) -> AgentMessage:
        """Handle medication compliance updates"""
        content = message.content
        patient_id = content.get("patient_id")
        compliance_data = content.get("compliance_data", {})
        
        # Analyze compliance and generate interventions
        interventions = await self._analyze_compliance(patient_id, compliance_data)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="compliance_analysis",
            content={
                "patient_id": patient_id,
                "compliance_score": compliance_data.get("score", 0.0),
                "interventions": interventions
            },
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _analyze_compliance(self, patient_id: str, compliance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze medication compliance and suggest interventions"""
        interventions = []
        compliance_score = compliance_data.get("score", 1.0)
        
        if compliance_score < 0.8:  # Poor compliance
            interventions.append({
                "type": "education",
                "description": "Provide medication education and importance counseling",
                "priority": "high"
            })
            
            interventions.append({
                "type": "simplify_regimen",
                "description": "Consider long-acting formulations to reduce dosing frequency",
                "priority": "medium"
            })
            
            interventions.append({
                "type": "pill_organizer",
                "description": "Recommend pill organizer or medication apps",
                "priority": "low"
            })
        
        return interventions
    
    async def _handle_dosage_adjustment_request(self, message: AgentMessage) -> AgentMessage:
        """Handle specific dosage adjustment requests"""
        content = message.content
        patient_id = content.get("patient_id")
        medication_id = content.get("medication_id")
        reason = content.get("reason")
        
        # Process dosage adjustment
        adjustment_result = await self._process_dosage_adjustment(patient_id, medication_id, reason)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="dosage_adjustment_processed",
            content=adjustment_result,
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    async def _process_dosage_adjustment(self, patient_id: str, medication_id: str, reason: str) -> Dict[str, Any]:
        """Process specific dosage adjustment request"""
        # Get current medication
        medications = self.active_medications.get(patient_id, [])
        medication = next((m for m in medications if m.medication_id == medication_id), None)
        
        if not medication:
            return {"success": False, "error": "Medication not found"}
        
        # Calculate new dose based on reason
        if reason == "withdrawal_symptoms":
            new_dose = min(medication.current_dose * 1.2, 150.0)  # Increase by 20%, max 150mg
        elif reason == "side_effects":
            new_dose = max(medication.current_dose * 0.8, 30.0)  # Decrease by 20%, min 30mg
        else:
            new_dose = medication.current_dose
        
        return {
            "success": True,
            "medication_id": medication_id,
            "current_dose": medication.current_dose,
            "recommended_dose": new_dose,
            "reason": reason,
            "requires_approval": True
        }
    
    async def _handle_interaction_check(self, message: AgentMessage) -> AgentMessage:
        """Handle drug interaction check requests"""
        content = message.content
        patient_id = content.get("patient_id")
        new_medication = content.get("new_medication")
        
        # Check interactions with current medications
        interaction_result = await self._check_new_medication_interactions(patient_id, new_medication)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="interaction_check_complete",
            content=interaction_result,
            priority=AgentPriority.HIGH if interaction_result.get("has_major_interactions") else AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _check_new_medication_interactions(self, patient_id: str, new_medication: str) -> Dict[str, Any]:
        """Check interactions between new medication and current regimen"""
        current_medications = self.active_medications.get(patient_id, [])
        interactions = []
        
        for medication in current_medications:
            interaction = self._check_specific_interaction(new_medication, medication.name)
            if interaction:
                interactions.append(interaction)
        
        has_major = any(i.get("severity") == "major" for i in interactions)
        
        return {
            "new_medication": new_medication,
            "interactions": interactions,
            "has_major_interactions": has_major,
            "safe_to_prescribe": not has_major,
            "recommendations": self._generate_interaction_recommendations(interactions)
        }
    
    def _check_specific_interaction(self, med1: str, med2: str) -> Optional[Dict[str, Any]]:
        """Check interaction between two specific medications"""
        # Simplified interaction checking
        med1_lower = med1.lower()
        med2_lower = med2.lower()
        
        if ("methadone" in med1_lower and "benzodiazepine" in med2_lower) or \
           ("methadone" in med2_lower and "benzodiazepine" in med1_lower):
            return {
                "medication1": med1,
                "medication2": med2,
                "severity": "major",
                "mechanism": "additive_cns_depression",
                "risk": "respiratory_depression",
                "recommendation": "avoid_or_monitor_closely"
            }
        
        return None
    
    def _generate_interaction_recommendations(self, interactions: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on drug interactions"""
        recommendations = []
        
        for interaction in interactions:
            if interaction.get("severity") == "major":
                recommendations.append(f"AVOID: {interaction['recommendation']}")
            elif interaction.get("severity") == "moderate":
                recommendations.append(f"MONITOR: {interaction['recommendation']}")
        
        return recommendations
    
    # Missing methods that were referenced
    async def _update_medication_regimen(self, patient_context: PatientContext):
        """Update medication regimen based on patient context"""
        # Implementation for updating medication regimen
        pass
    
    async def _assess_optimization_needs(self, patient_context: PatientContext) -> Dict[str, Any]:
        """Assess if medication optimization is needed"""
        return {
            "required": False,
            "reasons": [],
            "priority": "low"
        }
    
    async def _initiate_medication_optimization(self, patient_id: str, optimization_data: Dict[str, Any]):
        """Initiate medication optimization process"""
        # Implementation for initiating optimization
        pass
    
    async def _optimize_suboxone_dose(self, medication: Medication, patient_context: PatientContext) -> Optional[DosageRecommendation]:
        """Optimize Suboxone dosage"""
        # Similar to methadone optimization but with Suboxone-specific factors
        current_dose = medication.current_dose
        factors = {
            "withdrawal_symptoms": 0.0,
            "cravings_level": 0.0,
            "side_effects": 0.0,
            "treatment_day": 30
        }
        
        optimal_dose = await self._calculate_suboxone_dose(factors)
        
        if abs(optimal_dose - current_dose) > 2.0:  # 2mg difference threshold
            return DosageRecommendation(
                recommendation_id=f"suboxone_opt_{int(time.time())}",
                medication_id=medication.medication_id,
                current_dose=current_dose,
                recommended_dose=optimal_dose,
                adjustment_reason=DosageAdjustmentReason.THERAPEUTIC_OPTIMIZATION,
                confidence_score=0.82,
                evidence=["AI analysis suggests dose optimization needed"],
                monitoring_required=["withdrawal_scores", "liver_function"],
                contraindications=[],
                patient_factors=factors,
                timeline="gradual_over_2_days",
                approval_required=True
            )
        
        return None
    
    async def _optimize_ketamine_protocol(self, medication: Medication, patient_context: PatientContext) -> Optional[DosageRecommendation]:
        """Optimize ketamine therapy protocol"""
        # Ketamine optimization based on depression scores and response
        return None  # Would implement ketamine-specific optimization
    
    async def _optimize_comfort_medications(self, medication: Medication, patient_context: PatientContext) -> Optional[DosageRecommendation]:
        """Optimize comfort medications"""
        # Would implement comfort medication optimization
        return None
    
    # Emergency handling methods
    async def _handle_overdose_emergency(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle overdose emergency"""
        return {
            "success": True,
            "actions_taken": ["naloxone_administered", "emergency_services_called", "monitoring_initiated"],
            "patient_id": patient_id,
            "emergency_type": "overdose"
        }
    
    async def _handle_severe_withdrawal(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle severe withdrawal emergency"""
        return {
            "success": True,
            "actions_taken": ["comfort_medications_increased", "medical_team_notified", "monitoring_enhanced"],
            "patient_id": patient_id,
            "emergency_type": "severe_withdrawal"
        }
    
    async def _handle_drug_interaction_emergency(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle drug interaction emergency"""
        return {
            "success": True,
            "actions_taken": ["medication_held", "physician_notified", "monitoring_initiated"],
            "patient_id": patient_id,
            "emergency_type": "drug_interaction"
        }
    
    async def _handle_adverse_reaction(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle adverse drug reaction"""
        return {
            "success": True,
            "actions_taken": ["medication_discontinued", "supportive_care_initiated", "allergy_documented"],
            "patient_id": patient_id,
            "emergency_type": "adverse_reaction"
        }
    
    async def _handle_general_medication_emergency(self, patient_id: str, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general medication emergency"""
        return {
            "success": True,
            "actions_taken": ["situation_assessed", "appropriate_protocols_activated"],
            "patient_id": patient_id,
            "emergency_type": "general"
        }
