"""
NOVA ViA AI Systems - Configuration Settings
HIPAA-compliant medical AI system configuration
"""

import os
from typing import List, Optional, Any
from pydantic import BaseSettings, Field, validator
from pydantic_settings import BaseSettings as PydanticBaseSettings
import secrets


class DatabaseSettings(PydanticBaseSettings):
    """Database configuration settings"""
    
    url: str = Field(default="postgresql://postgres:password@localhost:5432/novavia")
    timescaledb_url: str = Field(default="postgresql://postgres:password@localhost:5433/novavia_timeseries")
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=10)
    echo: bool = Field(default=False)
    
    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(PydanticBaseSettings):
    """Redis configuration settings"""
    
    url: str = Field(default="redis://localhost:6379")
    password: Optional[str] = Field(default="redispassword")
    db: int = Field(default=0)
    decode_responses: bool = Field(default=True)
    
    class Config:
        env_prefix = "REDIS_"


class SecuritySettings(PydanticBaseSettings):
    """Security and HIPAA compliance settings"""
    
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    encryption_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=30)
    
    # HIPAA Compliance
    audit_logging: bool = Field(default=True)
    data_encryption_at_rest: bool = Field(default=True)
    data_encryption_in_transit: bool = Field(default=True)
    phi_access_logging: bool = Field(default=True)
    session_timeout_minutes: int = Field(default=30)
    
    @validator('secret_key', 'encryption_key', 'jwt_secret_key')
    def validate_key_length(cls, v):
        if len(v) < 32:
            raise ValueError('Keys must be at least 32 characters long for HIPAA compliance')
        return v
    
    class Config:
        env_prefix = ""


class MedicalDeviceSettings(PydanticBaseSettings):
    """Medical device integration settings"""
    
    # WAVi EEG Configuration
    wavi_eeg_ip: str = Field(default="192.168.1.100")
    wavi_eeg_port: int = Field(default=8080)
    wavi_sampling_rate: int = Field(default=500)
    wavi_channels: int = Field(default=32)
    wavi_api_key: Optional[str] = Field(default=None)
    
    # Biohacking Devices
    hyperbaric_chamber_ip: str = Field(default="192.168.1.101")
    hyperbaric_chamber_port: int = Field(default=8081)
    redlight_therapy_ip: str = Field(default="192.168.1.102")
    redlight_therapy_port: int = Field(default=8082)
    pemf_device_ip: str = Field(default="192.168.1.103")
    pemf_device_port: int = Field(default=8083)
    frequency_device_ip: str = Field(default="192.168.1.104")
    frequency_device_port: int = Field(default=8084)
    
    # Lab Integration
    lab_system_ip: str = Field(default="192.168.1.105")
    lab_system_port: int = Field(default=8085)
    lab_api_key: Optional[str] = Field(default=None)
    lab_results_endpoint: str = Field(default="/api/v1/results")
    
    class Config:
        env_prefix = ""


class AIModelSettings(PydanticBaseSettings):
    """AI model configuration settings"""
    
    # API Keys
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    huggingface_api_key: Optional[str] = Field(default=None)
    
    # Model Paths
    eeg_model_path: str = Field(default="./anep/eeg_processor/models/neuroplasticity_predictor.pkl")
    circadian_model_path: str = Field(default="./anep/circadian_optimizer/models/circadian_analyzer.pkl")
    risk_assessment_model_path: str = Field(default="./irip/analytics/models/risk_predictor.pkl")
    outcome_prediction_model_path: str = Field(default="./irip/analytics/models/outcome_predictor.pkl")
    
    # Performance Settings
    max_concurrent_patients: int = Field(default=1000)
    eeg_buffer_size: int = Field(default=10000)
    device_command_timeout_ms: int = Field(default=100)
    prediction_cache_ttl_seconds: int = Field(default=300)
    
    class Config:
        env_prefix = ""


class TreatmentProtocolSettings(PydanticBaseSettings):
    """Treatment protocol configuration"""
    
    # Medication Limits
    methadone_max_dose: int = Field(default=120)
    suboxone_max_dose: int = Field(default=24)
    
    # Treatment Options
    ketamine_enabled: bool = Field(default=True)
    plant_medicine_enabled: bool = Field(default=True)
    plant_medicine_supervisors_required: int = Field(default=2)
    
    # Emergency Settings
    emergency_contact_phone: str = Field(default="+1-800-EMERGENCY")
    emergency_email: str = Field(default="emergency@novavia.com")
    crisis_intervention_enabled: bool = Field(default=True)
    
    class Config:
        env_prefix = ""


class CloudStorageSettings(PydanticBaseSettings):
    """Cloud storage configuration"""
    
    # AWS S3
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_region: str = Field(default="us-west-2")
    aws_s3_bucket: str = Field(default="novavia-data-storage")
    
    # Azure (Alternative)
    azure_storage_account: Optional[str] = Field(default=None)
    azure_storage_key: Optional[str] = Field(default=None)
    azure_container_name: str = Field(default="patient-data")
    
    # Google Cloud (Alternative)
    google_application_credentials: Optional[str] = Field(default=None)
    gcp_project_id: Optional[str] = Field(default=None)
    gcp_bucket_name: str = Field(default="novavia-gcp-storage")
    
    class Config:
        env_prefix = ""


class MonitoringSettings(PydanticBaseSettings):
    """Monitoring and logging configuration"""
    
    log_level: str = Field(default="INFO")
    structured_logging: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)
    grafana_port: int = Field(default=3001)
    
    # Email Alerts
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    smtp_use_tls: bool = Field(default=True)
    
    class Config:
        env_prefix = ""


class Settings(PydanticBaseSettings):
    """Main application settings"""
    
    app_name: str = Field(default="NOVA_ViA_AI_Systems")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    
    # Service Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)
    api_timeout: int = Field(default=300)
    
    anep_host: str = Field(default="0.0.0.0")
    anep_port: int = Field(default=8001)
    anep_workers: int = Field(default=2)
    
    irip_host: str = Field(default="0.0.0.0")
    irip_port: int = Field(default=8002)
    irip_workers: int = Field(default=2)
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_group_id: str = Field(default="novavia-ai-systems")
    kafka_auto_offset_reset: str = Field(default="earliest")
    
    # Feature Flags
    enable_experimental_features: bool = Field(default=False)
    enable_device_simulation: bool = Field(default=True)
    enable_mock_eeg_data: bool = Field(default=True)
    enable_advanced_analytics: bool = Field(default=True)
    
    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    medical_devices: MedicalDeviceSettings = Field(default_factory=MedicalDeviceSettings)
    ai_models: AIModelSettings = Field(default_factory=AIModelSettings)
    treatment_protocols: TreatmentProtocolSettings = Field(default_factory=TreatmentProtocolSettings)
    cloud_storage: CloudStorageSettings = Field(default_factory=CloudStorageSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_environments = ['development', 'staging', 'production']
        if v not in allowed_environments:
            raise ValueError(f'Environment must be one of: {allowed_environments}')
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Validation for HIPAA compliance
def validate_hipaa_compliance():
    """Validate HIPAA compliance requirements"""
    errors = []
    
    if not settings.security.audit_logging:
        errors.append("Audit logging must be enabled for HIPAA compliance")
    
    if not settings.security.data_encryption_at_rest:
        errors.append("Data encryption at rest must be enabled for HIPAA compliance")
    
    if not settings.security.data_encryption_in_transit:
        errors.append("Data encryption in transit must be enabled for HIPAA compliance")
    
    if not settings.security.phi_access_logging:
        errors.append("PHI access logging must be enabled for HIPAA compliance")
    
    if settings.security.session_timeout_minutes > 30:
        errors.append("Session timeout must be 30 minutes or less for HIPAA compliance")
    
    if errors:
        raise ValueError(f"HIPAA compliance validation failed: {'; '.join(errors)}")
    
    return True


# Initialize and validate settings on import
if settings.is_production:
    validate_hipaa_compliance()
