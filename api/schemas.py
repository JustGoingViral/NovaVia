"""
NOVA ViA API Schemas
Pydantic models for request/response validation
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator, ConfigDict


# Base schemas
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResponseModel(BaseModel):
    """Base response model"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Enums
class PatientStatus(str, Enum):
    ACTIVE = "active"
    DISCHARGED = "discharged"
    TRANSFERRED = "transferred"


class DeviceStatus(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    STREAMING = "streaming"
    CALIBRATING = "calibrating"
    ERROR = "error"


class TreatmentType(str, Enum):
    NEUROFEEDBACK = "neurofeedback"
    HYPERBARIC = "hyperbaric"
    RED_LIGHT = "red_light"
    PEMF = "pemf"
    FREQUENCY = "frequency"
    KETAMINE = "ketamine"
    MEDICATION = "medication"


# Patient schemas
class PatientBase(BaseModel):
    """Base patient data"""
    medical_record_number: str = Field(..., description="Unique medical record number")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: datetime
    gender: Optional[str] = Field(None, max_length=20)
    primary_substance: Optional[str] = Field(None, max_length=100)
    secondary_substances: Optional[List[str]] = None
    emergency_contact: Optional[Dict[str, str]] = None


class PatientCreate(PatientBase):
    """Create patient request"""
    treatment_plan: Optional[Dict[str, Any]] = None


class PatientUpdate(BaseModel):
    """Update patient request"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[str] = Field(None, max_length=20)
    status: Optional[PatientStatus] = None
    primary_substance: Optional[str] = Field(None, max_length=100)
    secondary_substances: Optional[List[str]] = None
    treatment_plan: Optional[Dict[str, Any]] = None
    emergency_contact: Optional[Dict[str, str]] = None


class PatientResponse(PatientBase, TimestampMixin):
    """Patient response"""
    id: uuid.UUID
    status: PatientStatus
    admission_date: datetime
    discharge_date: Optional[datetime] = None
    treatment_plan: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# EEG Device schemas
class EEGDeviceBase(BaseModel):
    """Base EEG device data"""
    device_id: str = Field(..., description="Unique device identifier")
    device_type: str = Field(default="wavi")
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    channels: int = Field(default=32, ge=1, le=256)
    sampling_rate: int = Field(default=500, ge=100, le=10000)


class EEGDeviceCreate(EEGDeviceBase):
    """Create EEG device request"""
    calibration_data: Optional[Dict[str, Any]] = None


class EEGDeviceUpdate(BaseModel):
    """Update EEG device request"""
    ip_address: Optional[str] = None
    port: Optional[int] = None
    status: Optional[DeviceStatus] = None
    calibration_data: Optional[Dict[str, Any]] = None
    current_patient_id: Optional[uuid.UUID] = None


class EEGDeviceResponse(EEGDeviceBase, TimestampMixin):
    """EEG device response"""
    id: uuid.UUID
    status: DeviceStatus
    last_seen: Optional[datetime] = None
    last_calibration: Optional[datetime] = None
    current_patient_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


# EEG Features schemas
class EEGFeatures(BaseModel):
    """EEG feature data"""
    timestamp: datetime
    delta_power: float = Field(..., ge=0)
    theta_power: float = Field(..., ge=0)
    alpha_power: float = Field(..., ge=0)
    beta_power: float = Field(..., ge=0)
    gamma_power: float = Field(..., ge=0)
    alpha_theta_ratio: float = Field(..., ge=0)
    beta_alpha_ratio: float = Field(..., ge=0)
    gamma_beta_ratio: float = Field(..., ge=0)
    frontal_alpha_coherence: float = Field(..., ge=0, le=1)
    parietal_theta_coherence: float = Field(..., ge=0, le=1)
    inter_hemispheric_coherence: float = Field(..., ge=0, le=1)
    sample_entropy: float = Field(..., ge=0)
    lempel_ziv_complexity: float = Field(..., ge=0, le=1)
    fractal_dimension: float = Field(..., ge=1, le=3)
    signal_quality: Optional[Dict[int, float]] = None
    artifacts: Optional[Dict[str, Any]] = None


# Neuroplasticity Prediction schemas
class OptimalStimulationParams(BaseModel):
    """Optimal stimulation parameters"""
    frequency: float = Field(..., ge=0.1, le=100, description="Frequency in Hz")
    amplitude: float = Field(..., ge=0.1, le=5.0, description="Amplitude in mA")
    duration: int = Field(..., ge=60, le=1800, description="Duration in seconds")
    waveform: str = Field(default="sine", description="Waveform type")


class RiskFactors(BaseModel):
    """Risk assessment factors"""
    variability_risk: float = Field(..., ge=0, le=1)
    coherence_risk: float = Field(..., ge=0, le=1)
    trend_risk: float = Field(..., ge=0, le=1)
    circadian_risk: float = Field(..., ge=0, le=1)
    microstate_risk: float = Field(..., ge=0, le=1)
    overall_risk: float = Field(..., ge=0, le=1)


class NeuroplasticityPredictionBase(BaseModel):
    """Base neuroplasticity prediction"""
    predicted_start: datetime
    predicted_end: datetime
    confidence_score: float = Field(..., ge=0, le=1)
    window_type: str
    optimal_params: OptimalStimulationParams
    risk_factors: RiskFactors


class NeuroplasticityPredictionCreate(NeuroplasticityPredictionBase):
    """Create prediction request"""
    patient_id: uuid.UUID
    eeg_features: Optional[Dict[str, Any]] = None


class NeuroplasticityPredictionResponse(NeuroplasticityPredictionBase, TimestampMixin):
    """Prediction response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    prediction_time: datetime
    was_used: bool = False
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    effectiveness_score: Optional[float] = None

    class Config:
        from_attributes = True


# Treatment schemas
class TreatmentBase(BaseModel):
    """Base treatment data"""
    treatment_type: TreatmentType
    start_time: datetime
    parameters: Dict[str, Any] = Field(default_factory=dict)
    protocol_name: Optional[str] = None
    devices_used: Optional[List[str]] = None
    administered_by: Optional[str] = None
    notes: Optional[str] = None


class TreatmentCreate(TreatmentBase):
    """Create treatment request"""
    patient_id: uuid.UUID
    prediction_id: Optional[uuid.UUID] = None
    pre_treatment_assessment: Optional[Dict[str, Any]] = None


class TreatmentUpdate(BaseModel):
    """Update treatment request"""
    end_time: Optional[datetime] = None
    post_treatment_assessment: Optional[Dict[str, Any]] = None
    effectiveness_score: Optional[float] = Field(None, ge=0, le=10)
    notes: Optional[str] = None
    adverse_events: Optional[Dict[str, Any]] = None


class TreatmentResponse(TreatmentBase, TimestampMixin):
    """Treatment response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    prediction_id: Optional[uuid.UUID] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    pre_treatment_assessment: Optional[Dict[str, Any]] = None
    post_treatment_assessment: Optional[Dict[str, Any]] = None
    effectiveness_score: Optional[float] = None
    adverse_events: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Lab Result schemas
class LabResultBase(BaseModel):
    """Base lab result data"""
    collection_time: datetime
    sample_type: str = Field(..., description="blood, urine, saliva")
    results: Dict[str, Any] = Field(default_factory=dict)
    cortisol_level: Optional[float] = None
    dopamine_metabolites: Optional[float] = None
    serotonin_metabolites: Optional[float] = None
    substance_levels: Optional[Dict[str, float]] = None
    interpretation: Optional[str] = None
    flags: Optional[List[str]] = None


class LabResultCreate(LabResultBase):
    """Create lab result request"""
    patient_id: uuid.UUID
    lab_technician: Optional[str] = None
    equipment_id: Optional[str] = None


class LabResultResponse(LabResultBase, TimestampMixin):
    """Lab result response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    result_time: datetime
    lab_technician: Optional[str] = None
    equipment_id: Optional[str] = None

    class Config:
        from_attributes = True


# Medication schemas
class MedicationAdministrationBase(BaseModel):
    """Base medication administration"""
    medication_name: str = Field(..., max_length=200)
    dosage: float = Field(..., gt=0)
    dosage_unit: str = Field(..., max_length=50)
    route: Optional[str] = Field(None, max_length=50)
    scheduled_time: datetime
    is_mat_medication: bool = False
    is_ketamine: bool = False
    requires_monitoring: bool = False


class MedicationAdministrationCreate(MedicationAdministrationBase):
    """Create medication administration request"""
    patient_id: uuid.UUID
    administered_by: Optional[str] = None
    lot_number: Optional[str] = None
    expiration_date: Optional[datetime] = None


class MedicationAdministrationUpdate(BaseModel):
    """Update medication administration"""
    administered_time: Optional[datetime] = None
    patient_response: Optional[str] = None
    side_effects: Optional[Dict[str, Any]] = None
    effectiveness_rating: Optional[int] = Field(None, ge=1, le=10)


class MedicationAdministrationResponse(MedicationAdministrationBase, TimestampMixin):
    """Medication administration response"""
    id: uuid.UUID
    patient_id: uuid.UUID
    administered_time: Optional[datetime] = None
    administered_by: Optional[str] = None
    patient_response: Optional[str] = None
    side_effects: Optional[Dict[str, Any]] = None
    effectiveness_rating: Optional[int] = None

    class Config:
        from_attributes = True


# Analytics schemas
class PatientAnalytics(BaseModel):
    """Patient analytics summary"""
    patient_id: uuid.UUID
    total_sessions: int
    total_predictions: int
    prediction_accuracy: float
    treatment_effectiveness: float
    latest_eeg_quality: float
    risk_score: float
    progress_indicators: Dict[str, float]


class SystemAnalytics(BaseModel):
    """System-wide analytics"""
    total_patients: int
    active_patients: int
    streaming_devices: int
    predictions_today: int
    treatments_today: int
    system_uptime: float
    prediction_accuracy: float
    device_health: Dict[str, Any]


# Device Control schemas
class DeviceCommand(BaseModel):
    """Device command"""
    device_id: str
    command: str = Field(..., description="Command to execute")
    parameters: Optional[Dict[str, Any]] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class DeviceCommandResponse(ResponseModel):
    """Device command response"""
    device_id: str
    command: str
    result: Optional[Dict[str, Any]] = None
    execution_time: float


# WebSocket schemas
class EEGStreamData(BaseModel):
    """Real-time EEG stream data"""
    patient_id: str
    timestamp: datetime
    eeg_data: Dict[str, float]
    neuroplasticity_window: Optional[Dict[str, Any]] = None
    signal_quality: Dict[int, float]


class PredictionStreamData(BaseModel):
    """Real-time prediction stream data"""
    patient_id: str
    prediction_time: datetime
    predicted_window: Dict[str, Any]
    risk_assessment: RiskFactors


# Pagination schemas
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

    @validator('pages', always=True)
    def calculate_pages(cls, v, values):
        total = values.get('total', 0)
        size = values.get('size', 20)
        return (total + size - 1) // size


# Error schemas
class ErrorDetail(BaseModel):
    """Error detail"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = None


# Authentication schemas
class LoginRequest(BaseModel):
    """Login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class SessionResponse(BaseModel):
    """Session authentication response"""
    session_token: str
    user_info: Dict[str, Any]
    expires_in: int = 28800  # 8 hours in seconds
    session_type: str = "session"


class LogoutRequest(BaseModel):
    """Logout request"""
    revoke_all_sessions: bool = False


class UserInfo(BaseModel):
    """User information"""
    id: str
    username: str
    email: str
    role: str
    permissions: List[str]
    last_activity: Optional[datetime] = None
    session_created: Optional[datetime] = None


class SessionInfo(BaseModel):
    """Session information"""
    session_token: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    active: bool
