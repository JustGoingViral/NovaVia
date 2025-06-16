"""
NOVA ViA Database Models
SQLAlchemy models for all system data
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime, timezone
import uuid

Base = declarative_base()


class Patient(Base):
    """Patient information"""
    __tablename__ = 'patients'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_number = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(String(20))
    admission_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    discharge_date = Column(DateTime)
    status = Column(String(50), default='active')  # active, discharged, transferred
    
    # Treatment information
    primary_substance = Column(String(100))
    secondary_substances = Column(ARRAY(String))
    treatment_plan = Column(JSON)
    emergency_contact = Column(JSON)
    
    # Relationships
    eeg_sessions = relationship("EEGSession", back_populates="patient")
    treatments = relationship("Treatment", back_populates="patient")
    predictions = relationship("NeuroplasticityPrediction", back_populates="patient")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EEGDevice(Base):
    """EEG device information"""
    __tablename__ = 'eeg_devices'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(100), unique=True, nullable=False)
    device_type = Column(String(50), default='wavi')
    serial_number = Column(String(100))
    firmware_version = Column(String(50))
    ip_address = Column(String(45))  # IPv6 support
    port = Column(Integer)
    channels = Column(Integer, default=32)
    sampling_rate = Column(Integer, default=500)
    
    status = Column(String(50), default='offline')  # offline, online, streaming, calibrating, error
    last_seen = Column(DateTime)
    last_calibration = Column(DateTime)
    calibration_data = Column(JSON)
    
    # Current assignment
    current_patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'))
    current_patient = relationship("Patient")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EEGSession(Base):
    """EEG recording session"""
    __tablename__ = 'eeg_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('eeg_devices.id'), nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    
    session_type = Column(String(50))  # baseline, treatment, assessment
    quality_score = Column(Float)
    artifacts_detected = Column(Integer, default=0)
    
    # Data storage references
    raw_data_path = Column(String(500))  # Path to raw EEG data file
    processed_data_path = Column(String(500))  # Path to processed data
    
    # Session metadata
    notes = Column(Text)
    tags = Column(ARRAY(String))
    
    # Relationships
    patient = relationship("Patient", back_populates="eeg_sessions")
    device = relationship("EEGDevice")
    features = relationship("EEGFeatures", back_populates="session")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EEGFeatures(Base):
    """Extracted EEG features"""
    __tablename__ = 'eeg_features'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('eeg_sessions.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # Frequency band powers
    delta_power = Column(Float)
    theta_power = Column(Float)
    alpha_power = Column(Float)
    beta_power = Column(Float)
    gamma_power = Column(Float)
    
    # Band ratios
    alpha_theta_ratio = Column(Float)
    beta_alpha_ratio = Column(Float)
    gamma_beta_ratio = Column(Float)
    
    # Coherence measures
    frontal_alpha_coherence = Column(Float)
    parietal_theta_coherence = Column(Float)
    inter_hemispheric_coherence = Column(Float)
    
    # Complexity measures
    sample_entropy = Column(Float)
    lempel_ziv_complexity = Column(Float)
    fractal_dimension = Column(Float)
    
    # Connectivity
    phase_lag_index = Column(Float)
    weighted_phase_lag_index = Column(Float)
    imaginary_coherence = Column(Float)
    
    # Microstate features
    microstate_duration = Column(Float)
    microstate_coverage = Column(Float)
    microstate_transitions = Column(Integer)
    
    # Sleep/arousal
    sleep_spindles_count = Column(Integer)
    slow_waves_count = Column(Integer)
    arousal_index = Column(Float)
    
    # Quality metrics
    signal_quality = Column(JSON)  # Per-channel quality scores
    artifacts = Column(JSON)  # Detected artifacts
    
    # Relationships
    session = relationship("EEGSession", back_populates="features")
    
    __table_args__ = (
        Index('idx_features_timestamp', 'timestamp'),
        Index('idx_features_session_timestamp', 'session_id', 'timestamp'),
    )


class NeuroplasticityPrediction(Base):
    """Neuroplasticity window predictions"""
    __tablename__ = 'neuroplasticity_predictions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    
    prediction_time = Column(DateTime, nullable=False)
    predicted_start = Column(DateTime, nullable=False)
    predicted_end = Column(DateTime, nullable=False)
    
    confidence_score = Column(Float, nullable=False)
    window_type = Column(String(50))  # alpha_coherence, theta_power, gamma_burst, etc.
    
    # Optimal stimulation parameters
    optimal_frequency = Column(Float)
    optimal_amplitude = Column(Float)
    optimal_duration = Column(Integer)  # seconds
    optimal_waveform = Column(String(50))
    
    # Risk assessment
    risk_factors = Column(JSON)
    overall_risk_score = Column(Float)
    
    # Outcome tracking
    was_used = Column(Boolean, default=False)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    effectiveness_score = Column(Float)  # Post-treatment assessment
    
    # EEG features at prediction time
    eeg_features = Column(JSON)
    
    # Relationships
    patient = relationship("Patient", back_populates="predictions")
    
    __table_args__ = (
        Index('idx_predictions_patient_time', 'patient_id', 'prediction_time'),
        Index('idx_predictions_start_time', 'predicted_start'),
    )


class BiohackingDevice(Base):
    """Biohacking treatment devices"""
    __tablename__ = 'biohacking_devices'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(100), unique=True, nullable=False)
    device_type = Column(String(50), nullable=False)  # hyperbaric, redlight, pemf, frequency
    
    name = Column(String(200), nullable=False)
    location = Column(String(200))
    ip_address = Column(String(45))
    port = Column(Integer)
    
    # Device capabilities
    capabilities = Column(JSON)  # Frequency ranges, power levels, etc.
    current_settings = Column(JSON)
    
    status = Column(String(50), default='offline')  # offline, online, active, maintenance, error
    last_seen = Column(DateTime)
    last_maintenance = Column(DateTime)
    
    # Current assignment
    current_patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'))
    current_patient = relationship("Patient")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Treatment(Base):
    """Treatment sessions"""
    __tablename__ = 'treatments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey('neuroplasticity_predictions.id'))
    
    treatment_type = Column(String(100), nullable=False)  # neurofeedback, hyperbaric, etc.
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Treatment parameters
    parameters = Column(JSON)  # Device-specific parameters
    protocol_name = Column(String(200))
    
    # Devices used
    devices_used = Column(ARRAY(String))  # Device IDs
    
    # Outcome measures
    pre_treatment_assessment = Column(JSON)
    post_treatment_assessment = Column(JSON)
    effectiveness_score = Column(Float)
    
    # Staff and notes
    administered_by = Column(String(200))
    notes = Column(Text)
    adverse_events = Column(JSON)
    
    # Relationships
    patient = relationship("Patient", back_populates="treatments")
    prediction = relationship("NeuroplasticityPrediction")
    
    __table_args__ = (
        Index('idx_treatments_patient_time', 'patient_id', 'start_time'),
        Index('idx_treatments_type', 'treatment_type'),
    )


class LabResult(Base):
    """30-minute rapid lab results"""
    __tablename__ = 'lab_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    
    collection_time = Column(DateTime, nullable=False)
    result_time = Column(DateTime, nullable=False)
    sample_type = Column(String(50), nullable=False)  # blood, urine, saliva
    
    # Test results
    results = Column(JSON)  # All test values
    
    # Key biomarkers for addiction treatment
    cortisol_level = Column(Float)
    dopamine_metabolites = Column(Float)
    serotonin_metabolites = Column(Float)
    inflammatory_markers = Column(JSON)
    
    # Drug screening
    substance_levels = Column(JSON)
    metabolite_levels = Column(JSON)
    
    # Interpretation
    interpretation = Column(Text)
    flags = Column(ARRAY(String))  # Critical values, etc.
    
    # Lab info
    lab_technician = Column(String(200))
    equipment_id = Column(String(100))
    
    # Relationships
    patient = relationship("Patient")
    
    __table_args__ = (
        Index('idx_lab_patient_time', 'patient_id', 'collection_time'),
        Index('idx_lab_result_time', 'result_time'),
    )


class MedicationAdministration(Base):
    """Medication administration records"""
    __tablename__ = 'medication_administrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    
    medication_name = Column(String(200), nullable=False)
    dosage = Column(Float, nullable=False)
    dosage_unit = Column(String(50), nullable=False)
    route = Column(String(50))  # oral, IV, IM, etc.
    
    scheduled_time = Column(DateTime, nullable=False)
    administered_time = Column(DateTime)
    
    # Administration details
    administered_by = Column(String(200))
    lot_number = Column(String(100))
    expiration_date = Column(DateTime)
    
    # Patient response
    patient_response = Column(Text)
    side_effects = Column(JSON)
    effectiveness_rating = Column(Integer)  # 1-10 scale
    
    # Special medications
    is_mat_medication = Column(Boolean, default=False)  # Medication Assisted Treatment
    is_ketamine = Column(Boolean, default=False)
    requires_monitoring = Column(Boolean, default=False)
    
    # Relationships
    patient = relationship("Patient")
    
    __table_args__ = (
        Index('idx_med_patient_time', 'patient_id', 'administered_time'),
        Index('idx_med_scheduled_time', 'scheduled_time'),
    )


class AIAgent(Base):
    """IRIP AI agents"""
    __tablename__ = 'ai_agents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), unique=True, nullable=False)
    agent_type = Column(String(50), nullable=False)  # medication, therapy, biohacking, crisis, analytics
    
    status = Column(String(50), default='active')  # active, inactive, maintenance
    version = Column(String(20))
    
    # Configuration
    config = Column(JSON)
    model_parameters = Column(JSON)
    learning_rate = Column(Float)
    
    # Performance metrics
    decisions_made = Column(Integer, default=0)
    success_rate = Column(Float)
    confidence_scores = Column(JSON)  # Historical confidence scores
    
    # Last activity
    last_decision = Column(DateTime)
    last_training = Column(DateTime)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AgentDecision(Base):
    """AI agent decisions and recommendations"""
    __tablename__ = 'agent_decisions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('ai_agents.id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.id'), nullable=False)
    
    decision_time = Column(DateTime, nullable=False)
    decision_type = Column(String(100), nullable=False)
    
    # Decision details
    recommendation = Column(JSON)
    confidence_score = Column(Float)
    reasoning = Column(Text)
    
    # Input data used
    input_features = Column(JSON)
    data_sources = Column(ARRAY(String))
    
    # Outcome tracking
    was_implemented = Column(Boolean, default=False)
    implementation_time = Column(DateTime)
    outcome_score = Column(Float)
    feedback = Column(Text)
    
    # Relationships
    agent = relationship("AIAgent")
    patient = relationship("Patient")
    
    __table_args__ = (
        Index('idx_decisions_agent_time', 'agent_id', 'decision_time'),
        Index('idx_decisions_patient_time', 'patient_id', 'decision_time'),
    )


class SystemMetrics(Base):
    """System performance and health metrics"""
    __tablename__ = 'system_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False)
    metric_type = Column(String(100), nullable=False)
    
    # System metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_latency = Column(Float)
    
    # Application metrics
    active_patients = Column(Integer)
    streaming_devices = Column(Integer)
    predictions_per_hour = Column(Integer)
    treatment_sessions_active = Column(Integer)
    
    # Performance metrics
    prediction_accuracy = Column(Float)
    system_uptime = Column(Float)
    error_rate = Column(Float)
    
    # Custom metrics
    custom_metrics = Column(JSON)
    
    __table_args__ = (
        Index('idx_metrics_timestamp', 'timestamp'),
        Index('idx_metrics_type_time', 'metric_type', 'timestamp'),
    )
