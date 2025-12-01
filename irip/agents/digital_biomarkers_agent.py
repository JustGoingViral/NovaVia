"""
Digital Biomarkers Agent
Passive monitoring and relapse prediction using wearable/smartphone data

Implements LSTM-based forecasting for relapse risk using sleep, activity, HRV, 
and speech patterns as digital biomarkers.

References:
- Torous et al. (2020). Digital phenotyping for precision psychiatry. 
  Neuropsychopharmacology, 45(13), 2235-2249. [PMID: 32066828]
- Jacobson et al. (2020). Passive sensing of prediction of moment-to-moment 
  mood changes. JMIR mHealth uHealth, 8(3), e17336. [PMID: 32130131]
- Mohr et al. (2017). Personal sensing: understanding mental health using 
  ubiquitous sensors. Annual Review of Clinical Psychology, 13, 23-47.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)


logger = logging.getLogger(__name__)


class BiomarkerType(Enum):
    """Types of digital biomarkers"""
    SLEEP_EFFICIENCY = "sleep_efficiency"
    SLEEP_DURATION = "sleep_duration"
    ACTIVITY_LEVEL = "activity_level"
    HEART_RATE_VARIABILITY = "heart_rate_variability"
    RESTING_HEART_RATE = "resting_heart_rate"
    SPEECH_RATE = "speech_rate"
    SPEECH_PAUSE_DURATION = "speech_pause_duration"
    SOCIAL_INTERACTION = "social_interaction"
    LOCATION_VARIANCE = "location_variance"


class RelapseRiskLevel(Enum):
    """Relapse risk classification"""
    VERY_LOW = "very_low"       # <10% risk
    LOW = "low"                  # 10-25% risk
    MODERATE = "moderate"        # 25-50% risk
    HIGH = "high"                # 50-75% risk
    VERY_HIGH = "very_high"      # >75% risk


@dataclass
class BiomarkerReading:
    """Single biomarker reading"""
    patient_id: str
    timestamp: datetime
    biomarker_type: BiomarkerType
    value: float
    unit: str
    quality_score: float  # 0.0 to 1.0
    source_device: str


@dataclass
class RelapseRiskAssessment:
    """Relapse risk prediction output"""
    patient_id: str
    timestamp: datetime
    risk_score: float  # 0.0 to 1.0
    risk_level: RelapseRiskLevel
    confidence_interval_95: Tuple[float, float]
    contributing_factors: Dict[str, float]
    alert_triggered: bool
    recommended_actions: List[str]


class LSTMRelapsePredictor(nn.Module):
    """
    LSTM model for relapse prediction from time-series biomarkers
    
    Architecture based on Jacobson et al. (2020) achieving AUC ~0.75
    for mood prediction from passive sensing.
    """
    
    def __init__(self, input_size: int = 9, hidden_size: int = 64, 
                 num_layers: int = 2, dropout: float = 0.3):
        super(LSTMRelapsePredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc1 = nn.Linear(hidden_size, 32)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(32, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        """
        Forward pass through LSTM
        
        Args:
            x: (batch_size, sequence_length, input_size)
        
        Returns:
            risk_score: (batch_size, 1) in range [0, 1]
        """
        # LSTM layer
        lstm_out, _ = self.lstm(x)
        
        # Take last output
        last_output = lstm_out[:, -1, :]
        
        # Fully connected layers
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        risk_score = self.sigmoid(out)
        
        return risk_score


class DigitalBiomarkersAgent(BaseAgent):
    """
    Digital Biomarkers Agent for passive monitoring and relapse prediction
    
    Integrates data from:
    - Fitbit/Apple Watch: Sleep, activity, HRV
    - Smartphone: GPS, social interaction, app usage
    - Speech analysis: Rate, pauses, pitch variance
    
    Target AUC ~0.75 for 24-hour relapse prediction based on validation
    studies (Torous et al., 2020; Jacobson et al., 2020).
    """
    
    def __init__(self, agent_id: str = "digital_biomarkers_agent"):
        super().__init__(
            agent_id=agent_id,
            capabilities=[
                AgentCapability.REAL_TIME_MONITORING,
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.TREATMENT_OPTIMIZATION
            ]
        )
        
        self.model = LSTMRelapsePredictor()
        self.sequence_length = 168  # 7 days of hourly data
        self.alert_threshold = 0.5  # Risk > 50% triggers alert
        self.sleep_efficiency_threshold = 0.70  # <70% is concerning
        
        # Mock model weights (in production, load from trained checkpoint)
        self._initialize_mock_model()
    
    def _initialize_mock_model(self):
        """Initialize with mock weights for demonstration"""
        # In production: self.model.load_state_dict(torch.load('model.pth'))
        torch.manual_seed(42)  # Reproducible initialization
        logger.info(f"Initialized {self.agent_id} with mock LSTM weights")
    
    async def initialize(self):
        """Initialize agent"""
        await super().initialize()
        self.model.eval()  # Set to evaluation mode
        logger.info(f"{self.agent_id} initialized and ready")
    
    def preprocess_biomarkers(self, readings: List[BiomarkerReading]) -> np.ndarray:
        """
        Preprocess biomarker readings into model input
        
        Args:
            readings: List of biomarker readings
        
        Returns:
            features: (sequence_length, input_size) array
        """
        # Convert to DataFrame for easier manipulation
        data = []
        for reading in readings:
            data.append({
                'timestamp': reading.timestamp,
                'biomarker': reading.biomarker_type.value,
                'value': reading.value,
                'quality': reading.quality_score
            })
        
        df = pd.DataFrame(data)
        
        # Pivot to wide format
        df_pivot = df.pivot_table(
            index='timestamp',
            columns='biomarker',
            values='value',
            aggfunc='mean'
        )
        
        # Resample to hourly (interpolate missing values)
        df_hourly = df_pivot.resample('H').mean().interpolate(method='linear')
        
        # Take last sequence_length hours
        features = df_hourly.tail(self.sequence_length).values
        
        # Normalize features (z-score normalization)
        features = (features - np.mean(features, axis=0)) / (np.std(features, axis=0) + 1e-8)
        
        # Handle NaN values
        features = np.nan_to_num(features, nan=0.0)
        
        return features
    
    async def forecast_relapse(self, timeseries: pd.DataFrame) -> Dict[str, Any]:
        """
        Forecast relapse risk from time-series biomarker data
        
        Args:
            timeseries: DataFrame with columns for each biomarker type
        
        Returns:
            Prediction dict with risk score and confidence intervals
        
        Example:
            >>> timeseries = pd.DataFrame({
            ...     'sleep_efficiency': [0.85, 0.75, 0.65, ...],
            ...     'activity_level': [0.6, 0.5, 0.4, ...],
            ...     'hrv': [50, 45, 40, ...]
            ... })
            >>> result = await agent.forecast_relapse(timeseries)
            >>> print(result)
            {"risk": 0.22, "95_ci": [0.15, 0.29], "alert": False}
        """
        # Prepare input tensor
        features = timeseries.values
        
        # Normalize
        features = (features - np.mean(features, axis=0)) / (np.std(features, axis=0) + 1e-8)
        features = np.nan_to_num(features, nan=0.0)
        
        # Ensure correct shape
        if len(features) < self.sequence_length:
            # Pad with zeros if insufficient data
            padding = np.zeros((self.sequence_length - len(features), features.shape[1]))
            features = np.vstack([padding, features])
        else:
            # Take last sequence_length samples
            features = features[-self.sequence_length:]
        
        # Convert to tensor
        x = torch.FloatTensor(features).unsqueeze(0)  # (1, seq_len, features)
        
        # Predict
        with torch.no_grad():
            risk_score = self.model(x).item()
        
        # Monte Carlo dropout for uncertainty estimation
        # Run multiple forward passes with dropout enabled
        self.model.train()  # Enable dropout
        mc_samples = 100
        predictions = []
        
        with torch.no_grad():
            for _ in range(mc_samples):
                pred = self.model(x).item()
                predictions.append(pred)
        
        self.model.eval()  # Disable dropout
        
        # Calculate confidence intervals
        predictions = np.array(predictions)
        ci_lower = np.percentile(predictions, 2.5)
        ci_upper = np.percentile(predictions, 97.5)
        
        # Check for alert conditions
        alert = risk_score > self.alert_threshold
        
        # Additional alert: sleep efficiency < 70%
        if 'sleep_efficiency' in timeseries.columns:
            recent_sleep = timeseries['sleep_efficiency'].tail(3).mean()
            if recent_sleep < self.sleep_efficiency_threshold:
                alert = True
        
        return {
            "risk": round(risk_score, 3),
            "95_ci": [round(ci_lower, 3), round(ci_upper, 3)],
            "alert": alert,
            "alert_reason": "High relapse risk detected" if risk_score > self.alert_threshold 
                           else "Low sleep efficiency" if alert else None
        }
    
    async def assess_relapse_risk(self, patient_id: str, 
                                  readings: List[BiomarkerReading]) -> RelapseRiskAssessment:
        """
        Comprehensive relapse risk assessment
        
        Args:
            patient_id: Patient identifier
            readings: Recent biomarker readings (7 days recommended)
        
        Returns:
            RelapseRiskAssessment with predictions and recommendations
        """
        if not readings:
            raise ValueError("No biomarker readings provided")
        
        # Preprocess readings
        features = self.preprocess_biomarkers(readings)
        
        # Convert to DataFrame for forecast_relapse
        df = pd.DataFrame(features)
        
        # Get prediction
        prediction = await self.forecast_relapse(df)
        
        risk_score = prediction['risk']
        ci_lower, ci_upper = prediction['95_ci']
        
        # Classify risk level
        if risk_score < 0.10:
            risk_level = RelapseRiskLevel.VERY_LOW
        elif risk_score < 0.25:
            risk_level = RelapseRiskLevel.LOW
        elif risk_score < 0.50:
            risk_level = RelapseRiskLevel.MODERATE
        elif risk_score < 0.75:
            risk_level = RelapseRiskLevel.HIGH
        else:
            risk_level = RelapseRiskLevel.VERY_HIGH
        
        # Analyze contributing factors
        contributing_factors = self._analyze_contributing_factors(readings)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_level, contributing_factors)
        
        return RelapseRiskAssessment(
            patient_id=patient_id,
            timestamp=datetime.now(),
            risk_score=risk_score,
            risk_level=risk_level,
            confidence_interval_95=(ci_lower, ci_upper),
            contributing_factors=contributing_factors,
            alert_triggered=prediction['alert'],
            recommended_actions=recommendations
        )
    
    def _analyze_contributing_factors(self, readings: List[BiomarkerReading]) -> Dict[str, float]:
        """
        Analyze which biomarkers contribute most to risk
        
        Returns:
            Dict mapping biomarker to contribution score (0-1)
        """
        # Group by biomarker type
        biomarker_groups = {}
        for reading in readings:
            if reading.biomarker_type not in biomarker_groups:
                biomarker_groups[reading.biomarker_type] = []
            biomarker_groups[reading.biomarker_type].append(reading.value)
        
        # Calculate contribution scores based on deviation from healthy norms
        contributions = {}
        
        # Sleep efficiency (healthy: >0.85)
        if BiomarkerType.SLEEP_EFFICIENCY in biomarker_groups:
            sleep_eff = np.mean(biomarker_groups[BiomarkerType.SLEEP_EFFICIENCY])
            contributions['sleep_disruption'] = max(0, 0.85 - sleep_eff) / 0.85
        
        # Activity level (healthy: 0.6-0.8, normalized)
        if BiomarkerType.ACTIVITY_LEVEL in biomarker_groups:
            activity = np.mean(biomarker_groups[BiomarkerType.ACTIVITY_LEVEL])
            target = 0.7
            contributions['low_activity'] = max(0, target - activity) / target
        
        # HRV (healthy: >50 ms, higher is better)
        if BiomarkerType.HEART_RATE_VARIABILITY in biomarker_groups:
            hrv = np.mean(biomarker_groups[BiomarkerType.HEART_RATE_VARIABILITY])
            target = 50.0
            contributions['low_hrv'] = max(0, target - hrv) / target
        
        return contributions
    
    def _generate_recommendations(self, risk_level: RelapseRiskLevel,
                                  factors: Dict[str, float]) -> List[str]:
        """Generate actionable recommendations based on risk assessment"""
        recommendations = []
        
        if risk_level in [RelapseRiskLevel.HIGH, RelapseRiskLevel.VERY_HIGH]:
            recommendations.append("Immediate clinical check-in recommended")
            recommendations.append("Increase monitoring frequency to hourly")
        
        if risk_level == RelapseRiskLevel.VERY_HIGH:
            recommendations.append("Alert crisis intervention team")
        
        # Specific interventions based on factors
        if factors.get('sleep_disruption', 0) > 0.3:
            recommendations.append("Sleep hygiene intervention: Consider CBT-I or medication adjustment")
        
        if factors.get('low_activity', 0) > 0.3:
            recommendations.append("Physical activity intervention: Prescribe exercise protocol")
        
        if factors.get('low_hrv', 0) > 0.3:
            recommendations.append("Stress management: Recommend HRV biofeedback or meditation")
        
        if not recommendations:
            recommendations.append("Continue standard monitoring protocol")
        
        return recommendations
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages from other agents"""
        if message.message_type == "assess_relapse_risk":
            patient_id = message.content.get('patient_id')
            readings = message.content.get('readings', [])
            
            # Convert dict readings to BiomarkerReading objects
            reading_objects = []
            for r in readings:
                reading_objects.append(BiomarkerReading(
                    patient_id=r['patient_id'],
                    timestamp=datetime.fromisoformat(r['timestamp']),
                    biomarker_type=BiomarkerType(r['biomarker_type']),
                    value=r['value'],
                    unit=r['unit'],
                    quality_score=r.get('quality_score', 1.0),
                    source_device=r.get('source_device', 'unknown')
                ))
            
            assessment = await self.assess_relapse_risk(patient_id, reading_objects)
            
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="relapse_risk_assessment",
                content={
                    'assessment': {
                        'patient_id': assessment.patient_id,
                        'risk_score': assessment.risk_score,
                        'risk_level': assessment.risk_level.value,
                        'confidence_interval': assessment.confidence_interval_95,
                        'alert_triggered': assessment.alert_triggered,
                        'recommendations': assessment.recommended_actions
                    }
                },
                priority=AgentPriority.HIGH if assessment.alert_triggered else AgentPriority.NORMAL,
                timestamp=time.time(),
                correlation_id=message.message_id
            )
        
        return None


# Mock data generators for testing

def generate_mock_fitbit_data(days: int = 7) -> List[BiomarkerReading]:
    """
    Generate mock Fitbit data for testing
    
    Simulates realistic patterns with circadian rhythm and gradual decline
    """
    readings = []
    patient_id = "patient_test_001"
    base_time = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        # Sleep efficiency decreasing over time (simulating relapse prodrome)
        sleep_eff = 0.85 - (day * 0.03) + np.random.normal(0, 0.05)
        sleep_eff = np.clip(sleep_eff, 0.5, 0.95)
        
        readings.append(BiomarkerReading(
            patient_id=patient_id,
            timestamp=base_time + timedelta(days=day, hours=7),
            biomarker_type=BiomarkerType.SLEEP_EFFICIENCY,
            value=sleep_eff,
            unit="proportion",
            quality_score=0.95,
            source_device="Fitbit Charge 5"
        ))
        
        # Activity level (steps normalized to 0-1, declining)
        activity = 0.7 - (day * 0.05) + np.random.normal(0, 0.1)
        activity = np.clip(activity, 0.1, 0.9)
        
        readings.append(BiomarkerReading(
            patient_id=patient_id,
            timestamp=base_time + timedelta(days=day, hours=14),
            biomarker_type=BiomarkerType.ACTIVITY_LEVEL,
            value=activity,
            unit="normalized",
            quality_score=0.98,
            source_device="Fitbit Charge 5"
        ))
        
        # HRV (decreasing indicates stress)
        hrv = 55 - (day * 2) + np.random.normal(0, 5)
        hrv = np.clip(hrv, 20, 80)
        
        readings.append(BiomarkerReading(
            patient_id=patient_id,
            timestamp=base_time + timedelta(days=day, hours=7),
            biomarker_type=BiomarkerType.HEART_RATE_VARIABILITY,
            value=hrv,
            unit="ms",
            quality_score=0.92,
            source_device="Fitbit Charge 5"
        ))
    
    return readings


# Import uuid for message IDs
import uuid
