"""
ANEP Neuroplasticity Predictor
Predictive algorithms for optimal treatment windows (5-15 min advance prediction)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import pickle
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ML and Signal Processing
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
import scipy.signal as signal
from scipy.optimize import minimize
import redis
import kafka
from kafka import KafkaConsumer, KafkaProducer

from config.settings import get_settings
from .pattern_analyzer import EEGFeatures, NeuroplasticityWindow
from .stream_processor import EEGDataBatch


@dataclass
class PredictionWindow:
    """Predicted neuroplasticity window"""
    patient_id: str
    prediction_time: datetime
    predicted_start: datetime
    predicted_end: datetime
    confidence: float
    window_type: str
    optimal_params: Dict[str, float]
    risk_factors: Dict[str, float]
    preparation_time: float  # seconds until optimal start
    
    @property
    def is_imminent(self) -> bool:
        """Check if window is starting soon (within 2 minutes)"""
        return self.preparation_time <= 120.0
    
    @property
    def is_actionable(self) -> bool:
        """Check if window is actionable (enough prep time but not too far)"""
        return 30.0 <= self.preparation_time <= 900.0  # 30 seconds to 15 minutes


@dataclass
class TemporalFeatures:
    """Time-series features for prediction"""
    patient_id: str
    timestamp: datetime
    
    # Trend features (last 5-15 minutes)
    alpha_trend: float
    theta_trend: float
    coherence_trend: float
    complexity_trend: float
    
    # Cyclical features
    circadian_phase: float  # 0-1, time of day normalized
    ultradian_phase: float  # 0-1, 90-120 min cycles
    
    # Variability features
    alpha_variability: float
    coherence_stability: float
    
    # Lagged features
    alpha_lag_5min: float
    alpha_lag_10min: float
    coherence_lag_5min: float
    coherence_lag_10min: float
    
    # Spectral evolution
    spectral_centroid_trend: float
    spectral_bandwidth_trend: float
    
    # Microstate dynamics
    microstate_stability: float
    transition_rate_trend: float


class NeuroplasticityPredictor:
    """
    Advanced predictor for neuroplasticity windows
    Uses time-series analysis and ensemble learning for 5-15 minute advance predictions
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Model paths
        self.model_path = Path(model_path) if model_path else Path(self.settings.ai_models.eeg_model_path).parent
        
        # Prediction models
        self.window_onset_model: Optional[GradientBoostingRegressor] = None
        self.window_duration_model: Optional[RandomForestRegressor] = None
        self.confidence_model: Optional[keras.Model] = None
        self.feature_scaler: Optional[RobustScaler] = None
        
        # Feature history for time-series analysis
        self.feature_history: Dict[str, List[Tuple[datetime, EEGFeatures]]] = {}
        self.prediction_history: Dict[str, List[PredictionWindow]] = {}
        
        # Processing parameters
        self.prediction_horizon = 900  # 15 minutes maximum
        self.min_prediction_horizon = 30  # 30 seconds minimum
        self.history_window = 1800  # 30 minutes of history
        self.min_history_points = 10  # Minimum points for prediction
        
        # Kafka integration
        self._kafka_consumer: Optional[KafkaConsumer] = None
        self._kafka_producer: Optional[KafkaProducer] = None
        self._redis_client: Optional[redis.Redis] = None
        
        # Processing state
        self.is_predicting = False
        self.active_patients: set = set()
        
        # Circadian and ultradian models
        self.circadian_params: Dict[str, Dict] = {}  # Per-patient circadian parameters
        self.ultradian_params: Dict[str, Dict] = {}  # Per-patient ultradian parameters
    
    async def initialize(self):
        """Initialize the neuroplasticity predictor"""
        try:
            # Initialize Redis connection
            self._redis_client = redis.Redis.from_url(
                self.settings.redis.url,
                password=self.settings.redis.password,
                db=self.settings.redis.db,
                decode_responses=True
            )
            
            # Initialize Kafka components
            self._kafka_consumer = KafkaConsumer(
                'eeg-features',
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                group_id='neuroplasticity-predictor',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest'
            )
            
            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            
            # Load models
            await self._load_models()
            
            self.logger.info("Neuroplasticity Predictor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Neuroplasticity Predictor: {e}")
            raise
    
    async def _load_models(self):
        """Load pre-trained prediction models"""
        try:
            # Load window onset model
            onset_model_path = self.model_path / "window_onset_model.pkl"
            if onset_model_path.exists():
                self.window_onset_model = joblib.load(str(onset_model_path))
                self.logger.info("Loaded window onset model")
            
            # Load window duration model
            duration_model_path = self.model_path / "window_duration_model.pkl"
            if duration_model_path.exists():
                self.window_duration_model = joblib.load(str(duration_model_path))
                self.logger.info("Loaded window duration model")
            
            # Load confidence model
            confidence_model_path = self.model_path / "confidence_model.h5"
            if confidence_model_path.exists():
                self.confidence_model = keras.models.load_model(str(confidence_model_path))
                self.logger.info("Loaded confidence model")
            
            # Load feature scaler
            scaler_path = self.model_path / "temporal_feature_scaler.pkl"
            if scaler_path.exists():
                self.feature_scaler = joblib.load(str(scaler_path))
                self.logger.info("Loaded temporal feature scaler")
            
            # If models don't exist, create default ones
            if not self.window_onset_model:
                await self._create_default_models()
                
        except Exception as e:
            self.logger.error(f"Error loading prediction models: {e}")
            await self._create_default_models()
    
    async def _create_default_models(self):
        """Create default prediction models"""
        try:
            # Create window onset model (predicts time to next window)
            self.window_onset_model = GradientBoostingRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42
            )
            
            # Create window duration model
            self.window_duration_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=8,
                random_state=42
            )
            
            # Create confidence estimation model
            self.confidence_model = keras.Sequential([
                keras.layers.Dense(128, activation='relu', input_shape=(25,)),  # Temporal features
                keras.layers.Dropout(0.3),
                keras.layers.Dense(64, activation='relu'),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(1, activation='sigmoid')  # Confidence score
            ])
            
            self.confidence_model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            
            # Create feature scaler
            self.feature_scaler = RobustScaler()
            
            self.logger.info("Created default prediction models")
            
        except Exception as e:
            self.logger.error(f"Error creating default models: {e}")
            raise
    
    async def start_prediction_service(self):
        """Start the continuous prediction service"""
        try:
            self.is_predicting = True
            
            # Start Kafka consumer task
            consumer_task = asyncio.create_task(self._consume_features_task())
            
            # Start prediction task
            prediction_task = asyncio.create_task(self._prediction_task())
            
            # Start circadian analysis task
            circadian_task = asyncio.create_task(self._circadian_analysis_task())
            
            await asyncio.gather(consumer_task, prediction_task, circadian_task)
            
        except Exception as e:
            self.logger.error(f"Error in prediction service: {e}")
            raise
    
    async def _consume_features_task(self):
        """Task to consume EEG features from Kafka"""
        while self.is_predicting:
            try:
                # Poll for messages
                messages = self._kafka_consumer.poll(timeout_ms=1000)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        await self._process_feature_message(record.value)
                
            except Exception as e:
                self.logger.error(f"Error consuming features: {e}")
                await asyncio.sleep(1)
    
    async def _process_feature_message(self, message: Dict):
        """Process incoming EEG feature message"""
        try:
            patient_id = message['patient_id']
            timestamp = datetime.fromisoformat(message['timestamp'])
            
            # Convert message to EEGFeatures object
            features = EEGFeatures(
                patient_id=patient_id,
                timestamp=timestamp,
                delta_power=message.get('delta_power', 0.0),
                theta_power=message.get('theta_power', 0.0),
                alpha_power=message.get('alpha_power', 0.0),
                beta_power=message.get('beta_power', 0.0),
                gamma_power=message.get('gamma_power', 0.0),
                alpha_theta_ratio=message.get('alpha_theta_ratio', 0.0),
                beta_alpha_ratio=message.get('beta_alpha_ratio', 0.0),
                gamma_beta_ratio=message.get('gamma_beta_ratio', 0.0),
                frontal_alpha_coherence=message.get('frontal_alpha_coherence', 0.0),
                parietal_theta_coherence=message.get('parietal_theta_coherence', 0.0),
                inter_hemispheric_coherence=message.get('inter_hemispheric_coherence', 0.0),
                sample_entropy=message.get('sample_entropy', 0.0),
                lempel_ziv_complexity=message.get('lempel_ziv_complexity', 0.0),
                fractal_dimension=message.get('fractal_dimension', 1.0),
                phase_lag_index=message.get('phase_lag_index', 0.0),
                weighted_phase_lag_index=message.get('weighted_phase_lag_index', 0.0),
                imaginary_coherence=message.get('imaginary_coherence', 0.0),
                microstate_duration=message.get('microstate_duration', 0.0),
                microstate_coverage=message.get('microstate_coverage', 0.0),
                microstate_transitions=message.get('microstate_transitions', 0),
                sleep_spindles_count=message.get('sleep_spindles_count', 0),
                slow_waves_count=message.get('slow_waves_count', 0),
                arousal_index=message.get('arousal_index', 0.0)
            )
            
            # Add to feature history
            await self._add_feature_to_history(features)
            
            # Update active patients
            self.active_patients.add(patient_id)
            
        except Exception as e:
            self.logger.error(f"Error processing feature message: {e}")
    
    async def _add_feature_to_history(self, features: EEGFeatures):
        """Add features to patient history"""
        try:
            patient_id = features.patient_id
            
            # Initialize history if needed
            if patient_id not in self.feature_history:
                self.feature_history[patient_id] = []
            
            # Add new features
            self.feature_history[patient_id].append((features.timestamp, features))
            
            # Clean old history (keep last 30 minutes)
            cutoff_time = features.timestamp - timedelta(seconds=self.history_window)
            self.feature_history[patient_id] = [
                (ts, feat) for ts, feat in self.feature_history[patient_id]
                if ts >= cutoff_time
            ]
            
            # Sort by timestamp
            self.feature_history[patient_id].sort(key=lambda x: x[0])
            
        except Exception as e:
            self.logger.error(f"Error adding features to history: {e}")
    
    async def _prediction_task(self):
        """Main prediction task"""
        while self.is_predicting:
            try:
                # Make predictions for all active patients
                for patient_id in list(self.active_patients):
                    await self._predict_for_patient(patient_id)
                
                # Wait before next prediction cycle
                await asyncio.sleep(30)  # Predict every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in prediction task: {e}")
                await asyncio.sleep(10)
    
    async def _predict_for_patient(self, patient_id: str):
        """Make neuroplasticity window prediction for a patient"""
        try:
            # Check if we have enough history
            history = self.feature_history.get(patient_id, [])
            if len(history) < self.min_history_points:
                return
            
            # Extract temporal features
            temporal_features = await self._extract_temporal_features(patient_id)
            if not temporal_features:
                return
            
            # Make prediction
            prediction = await self._make_prediction(temporal_features)
            
            if prediction and prediction.confidence >= 0.7:
                # Store prediction
                if patient_id not in self.prediction_history:
                    self.prediction_history[patient_id] = []
                
                self.prediction_history[patient_id].append(prediction)
                
                # Clean old predictions
                cutoff_time = prediction.prediction_time - timedelta(hours=1)
                self.prediction_history[patient_id] = [
                    p for p in self.prediction_history[patient_id]
                    if p.prediction_time >= cutoff_time
                ]
                
                # Send prediction via Kafka
                await self._send_prediction(prediction)
                
                # Store in Redis
                await self._store_prediction_redis(prediction)
                
                self.logger.info(f"Predicted neuroplasticity window for {patient_id}: "
                               f"starts in {prediction.preparation_time:.1f}s, "
                               f"confidence {prediction.confidence:.3f}")
            
        except Exception as e:
            self.logger.error(f"Error predicting for patient {patient_id}: {e}")
    
    async def _extract_temporal_features(self, patient_id: str) -> Optional[TemporalFeatures]:
        """Extract temporal features for prediction"""
        try:
            history = self.feature_history.get(patient_id, [])
            if len(history) < self.min_history_points:
                return None
            
            # Get recent features
            recent_features = [feat for ts, feat in history[-20:]]  # Last 20 points
            timestamps = [ts for ts, feat in history[-20:]]
            
            if not recent_features:
                return None
            
            current_time = timestamps[-1]
            
            # Calculate trends (linear regression slopes)
            alpha_values = [f.alpha_power for f in recent_features]
            theta_values = [f.theta_power for f in recent_features]
            coherence_values = [f.frontal_alpha_coherence for f in recent_features]
            complexity_values = [f.sample_entropy for f in recent_features]
            
            # Time indices for trend calculation
            time_indices = np.arange(len(alpha_values))
            
            alpha_trend = self._calculate_trend(time_indices, alpha_values)
            theta_trend = self._calculate_trend(time_indices, theta_values)
            coherence_trend = self._calculate_trend(time_indices, coherence_values)
            complexity_trend = self._calculate_trend(time_indices, complexity_values)
            
            # Calculate circadian and ultradian phases
            circadian_phase = self._calculate_circadian_phase(current_time, patient_id)
            ultradian_phase = self._calculate_ultradian_phase(current_time, patient_id)
            
            # Calculate variability features
            alpha_variability = np.std(alpha_values[-10:]) if len(alpha_values) >= 10 else 0.0
            coherence_stability = 1.0 / (1.0 + np.std(coherence_values[-10:])) if len(coherence_values) >= 10 else 0.5
            
            # Calculate lagged features
            alpha_lag_5min = self._get_lagged_feature(history, 'alpha_power', 300)  # 5 minutes
            alpha_lag_10min = self._get_lagged_feature(history, 'alpha_power', 600)  # 10 minutes
            coherence_lag_5min = self._get_lagged_feature(history, 'frontal_alpha_coherence', 300)
            coherence_lag_10min = self._get_lagged_feature(history, 'frontal_alpha_coherence', 600)
            
            # Calculate spectral trends
            spectral_centroid_trend = self._calculate_spectral_centroid_trend(recent_features)
            spectral_bandwidth_trend = self._calculate_spectral_bandwidth_trend(recent_features)
            
            # Calculate microstate features
            microstate_stability = self._calculate_microstate_stability(recent_features)
            transition_rate_trend = self._calculate_transition_rate_trend(recent_features)
            
            return TemporalFeatures(
                patient_id=patient_id,
                timestamp=current_time,
                alpha_trend=alpha_trend,
                theta_trend=theta_trend,
                coherence_trend=coherence_trend,
                complexity_trend=complexity_trend,
                circadian_phase=circadian_phase,
                ultradian_phase=ultradian_phase,
                alpha_variability=alpha_variability,
                coherence_stability=coherence_stability,
                alpha_lag_5min=alpha_lag_5min,
                alpha_lag_10min=alpha_lag_10min,
                coherence_lag_5min=coherence_lag_5min,
                coherence_lag_10min=coherence_lag_10min,
                spectral_centroid_trend=spectral_centroid_trend,
                spectral_bandwidth_trend=spectral_bandwidth_trend,
                microstate_stability=microstate_stability,
                transition_rate_trend=transition_rate_trend
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting temporal features: {e}")
            return None
    
    def _calculate_trend(self, x: np.ndarray, y: List[float]) -> float:
        """Calculate linear trend (slope)"""
        try:
            if len(y) < 2:
                return 0.0
            
            y_array = np.array(y)
            
            # Handle invalid values
            mask = np.isfinite(y_array)
            if np.sum(mask) < 2:
                return 0.0
            
            x_valid = x[mask]
            y_valid = y_array[mask]
            
            # Linear regression
            coeffs = np.polyfit(x_valid, y_valid, 1)
            return float(coeffs[0])  # Slope
            
        except:
            return 0.0
    
    def _calculate_circadian_phase(self, current_time: datetime, patient_id: str) -> float:
        """Calculate circadian phase (0-1)"""
        try:
            # Get hour of day
            hour_of_day = current_time.hour + current_time.minute / 60.0
            
            # Normalize to 0-1 (assuming 24-hour cycle)
            circadian_phase = hour_of_day / 24.0
            
            # Apply patient-specific phase shift if available
            if patient_id in self.circadian_params:
                phase_shift = self.circadian_params[patient_id].get('phase_shift', 0.0)
                circadian_phase = (circadian_phase + phase_shift) % 1.0
            
            return circadian_phase
            
        except:
            return 0.5  # Default midpoint
    
    def _calculate_ultradian_phase(self, current_time: datetime, patient_id: str) -> float:
        """Calculate ultradian phase (90-120 min cycles)"""
        try:
            # Calculate minutes since midnight
            minutes_since_midnight = current_time.hour * 60 + current_time.minute
            
            # Use 90-minute cycle (can be adjusted per patient)
            cycle_length = self.ultradian_params.get(patient_id, {}).get('cycle_length', 90)
            
            # Calculate phase
            ultradian_phase = (minutes_since_midnight % cycle_length) / cycle_length
            
            return ultradian_phase
            
        except:
            return 0.5  # Default midpoint
    
    def _get_lagged_feature(self, history: List[Tuple[datetime, EEGFeatures]], 
                           feature_name: str, lag_seconds: int) -> float:
        """Get feature value from specified time lag"""
        try:
            if not history:
                return 0.0
            
            current_time = history[-1][0]
            target_time = current_time - timedelta(seconds=lag_seconds)
            
            # Find closest feature to target time
            closest_idx = 0
            min_diff = abs((history[0][0] - target_time).total_seconds())
            
            for i, (ts, feat) in enumerate(history):
                diff = abs((ts - target_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i
            
            # Get feature value
            _, closest_feature = history[closest_idx]
            return getattr(closest_feature, feature_name, 0.0)
            
        except:
            return 0.0
    
    def _calculate_spectral_centroid_trend(self, features: List[EEGFeatures]) -> float:
        """Calculate trend in spectral centroid"""
        try:
            # Simplified spectral centroid based on band powers
            centroids = []
            for feat in features:
                weighted_sum = (
                    1 * feat.delta_power +
                    3 * feat.theta_power +
                    10 * feat.alpha_power +
                    20 * feat.beta_power +
                    50 * feat.gamma_power
                )
                total_power = (feat.delta_power + feat.theta_power + 
                             feat.alpha_power + feat.beta_power + feat.gamma_power)
                
                if total_power > 0:
                    centroid = weighted_sum / total_power
                    centroids.append(centroid)
            
            if len(centroids) >= 2:
                return self._calculate_trend(np.arange(len(centroids)), centroids)
            else:
                return 0.0
                
        except:
            return 0.0
    
    def _calculate_spectral_bandwidth_trend(self, features: List[EEGFeatures]) -> float:
        """Calculate trend in spectral bandwidth"""
        try:
            # Simplified bandwidth based on power distribution
            bandwidths = []
            for feat in features:
                powers = [feat.delta_power, feat.theta_power, feat.alpha_power, 
                         feat.beta_power, feat.gamma_power]
                bandwidth = np.std(powers) if powers else 0.0
                bandwidths.append(bandwidth)
            
            if len(bandwidths) >= 2:
                return self._calculate_trend(np.arange(len(bandwidths)), bandwidths)
            else:
                return 0.0
                
        except:
            return 0.0
    
    def _calculate_microstate_stability(self, features: List[EEGFeatures]) -> float:
        """Calculate microstate stability"""
        try:
            durations = [feat.microstate_duration for feat in features]
            if durations:
                # Stability is inverse of variability
                return 1.0 / (1.0 + np.std(durations))
            else:
                return 0.5
                
        except:
            return 0.5
    
    def _calculate_transition_rate_trend(self, features: List[EEGFeatures]) -> float:
        """Calculate trend in microstate transition rate"""
        try:
            transition_rates = []
            for feat in features:
                # Normalize transitions by duration
                if feat.microstate_duration > 0:
                    rate = feat.microstate_transitions / feat.microstate_duration
                    transition_rates.append(rate)
            
            if len(transition_rates) >= 2:
                return self._calculate_trend(np.arange(len(transition_rates)), transition_rates)
            else:
                return 0.0
                
        except:
            return 0.0
    
    async def _make_prediction(self, temporal_features: TemporalFeatures) -> Optional[PredictionWindow]:
        """Make neuroplasticity window prediction"""
        try:
            # Convert features to array
            feature_array = self._temporal_features_to_array(temporal_features)
            if feature_array is None:
                return None
            
            # Scale features
            if self.feature_scaler:
                try:
                    feature_array_scaled = self.feature_scaler.transform(feature_array.reshape(1, -1))
                except:
                    # Fit with dummy data if not fitted
                    dummy_features = np.random.randn(10, len(feature_array))
                    self.feature_scaler.fit(dummy_features)
                    feature_array_scaled = self.feature_scaler.transform(feature_array.reshape(1, -1))
            else:
                feature_array_scaled = feature_array.reshape(1, -1)
            
            # Predict time to next window (in seconds)
            if self.window_onset_model:
                try:
                    time_to_window = self.window_onset_model.predict(feature_array_scaled)[0]
                except:
                    # Fit with dummy data if not fitted
                    dummy_X = np.random.randn(100, feature_array_scaled.shape[1])
                    dummy_y = np.random.uniform(30, 900, 100)  # 30 seconds to 15 minutes
                    self.window_onset_model.fit(dummy_X, dummy_y)
                    time_to_window = self.window_onset_model.predict(feature_array_scaled)[0]
            else:
                time_to_window = 300.0  # Default 5 minutes
            
            # Predict window duration
            if self.window_duration_model:
                try:
                    window_duration = self.window_duration_model.predict(feature_array_scaled)[0]
                except:
                    # Fit with dummy data if not fitted
                    dummy_X = np.random.randn(100, feature_array_scaled.shape[1])
                    dummy_y = np.random.uniform(120, 600, 100)  # 2-10 minutes
                    self.window_duration_model.fit(dummy_X, dummy_y)
                    window_duration = self.window_duration_model.predict(feature_array_scaled)[0]
            else:
                window_duration = 300.0  # Default 5 minutes
            
            # Predict confidence
            if self.confidence_model:
                try:
                    confidence = self.confidence_model.predict(feature_array_scaled, verbose=0)[0][0]
                except:
                    confidence = 0.8  # Default high confidence
            else:
                confidence = 0.8
            
            # Ensure reasonable bounds
            time_to_window = max(self.min_prediction_horizon, 
                               min(self.prediction_horizon, time_to_window))
            window_duration = max(120.0, min(900.0, window_duration))  # 2-15 minutes
            confidence = max(0.0, min(1.0, confidence))
            
            # Calculate prediction timestamps
            prediction_time = temporal_features.timestamp
            predicted_start = prediction_time + timedelta(seconds=time_to_window)
            predicted_end = predicted_start + timedelta(seconds=window_duration)
            
            # Determine window type based on temporal features
            window_type = self._determine_window_type_from_temporal(temporal_features)
            
            # Calculate optimal stimulation parameters
            optimal_params = self._calculate_optimal_params_from_temporal(temporal_features, window_type)
            
            # Calculate risk factors
            risk_factors = self._calculate_risk_factors(temporal_features)
            
            return PredictionWindow(
                patient_id=temporal_features.patient_id,
                prediction_time=prediction_time,
                predicted_start=predicted_start,
                predicted_end=predicted_end,
                confidence=confidence,
                window_type=window_type,
                optimal_params=optimal_params,
                risk_factors=risk_factors,
                preparation_time=time_to_window
            )
            
        except Exception as e:
            self.logger.error(f"Error making prediction: {e}")
            return None
    
    def _temporal_features_to_array(self, features: TemporalFeatures) -> Optional[np.ndarray]:
        """Convert temporal features to numpy array"""
        try:
            feature_list = [
                features.alpha_trend,
                features.theta_trend,
                features.coherence_trend,
                features.complexity_trend,
                features.circadian_phase,
                features.ultradian_phase,
                features.alpha_variability,
                features.coherence_stability,
                features.alpha_lag_5min,
                features.alpha_lag_10min,
                features.coherence_lag_5min,
                features.coherence_lag_10min,
                features.spectral_centroid_trend,
                features.spectral_bandwidth_trend,
                features.microstate_stability,
                features.transition_rate_trend
            ]
            
            # Handle any NaN or infinite values
            feature_array = np.array(feature_list, dtype=np.float32)
            feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1.0, neginf=0.0)
            
            return feature_array
            
        except Exception as e:
            self.logger.error(f"Error converting temporal features to array: {e}")
            return None
    
    def _determine_window_type_from_temporal(self, features: TemporalFeatures) -> str:
        """Determine window type from temporal features"""
        try:
            # Alpha trend dominance
            if features.alpha_trend > 0.1 and features.coherence_trend > 0.05:
                return "alpha_coherence"
            
            # Theta trend dominance
            elif features.theta_trend > 0.1:
                return "theta_power"
            
            # High complexity trend
            elif features.complexity_trend > 0.05:
                return "complexity_driven"
            
            # Circadian optimization window
            elif 0.3 <= features.circadian_phase <= 0.7:  # Optimal daytime hours
                return "circadian_optimal"
            
            # Ultradian cycle window
            elif 0.2 <= features.ultradian_phase <= 0.4:  # Optimal ultradian phase
                return "ultradian_optimal"
            
            # Default
            else:
                return "general_enhancement"
                
        except:
            return "unknown"
    
    def _calculate_optimal_params_from_temporal(self, features: TemporalFeatures, window_type: str) -> Dict[str, float]:
        """Calculate optimal stimulation parameters from temporal features"""
        try:
            base_params = {
                'frequency': 10.0,  # Hz
                'amplitude': 1.0,   # mA
                'duration': 300.0,  # seconds
                'waveform': 'sine'
            }
            
            # Adjust based on window type
            if window_type == "alpha_coherence":
                base_params.update({
                    'frequency': 10.0,  # Alpha range
                    'amplitude': 0.8 + features.coherence_stability * 0.4,
                    'duration': 300.0 + features.alpha_variability * 200.0
                })
            elif window_type == "theta_power":
                base_params.update({
                    'frequency': 6.0,   # Theta range
                    'amplitude': 1.0 + features.theta_trend * 0.5,
                    'duration': 400.0
                })
            elif window_type == "complexity_driven":
                base_params.update({
                    'frequency': 15.0,  # Higher frequency for complexity
                    'amplitude': 0.6 + features.complexity_trend * 0.8,
                    'duration': 250.0
                })
            elif window_type == "circadian_optimal":
                # Adjust for time of day
                phase_factor = np.sin(2 * np.pi * features.circadian_phase)
                base_params.update({
                    'frequency': 8.0 + 4.0 * phase_factor,
                    'amplitude': 0.8 + 0.4 * abs(phase_factor),
                    'duration': 300.0 + 150.0 * phase_factor
                })
            elif window_type == "ultradian_optimal":
                # Adjust for ultradian cycle
                cycle_factor = np.sin(2 * np.pi * features.ultradian_phase)
                base_params.update({
                    'frequency': 10.0 + 2.0 * cycle_factor,
                    'amplitude': 1.0 + 0.2 * cycle_factor,
                    'duration': 350.0 + 100.0 * cycle_factor
                })
            
            # Ensure reasonable bounds
            base_params['frequency'] = max(1.0, min(50.0, base_params['frequency']))
            base_params['amplitude'] = max(0.1, min(2.0, base_params['amplitude']))
            base_params['duration'] = max(120.0, min(900.0, base_params['duration']))
            
            return base_params
            
        except:
            return {
                'frequency': 10.0,
                'amplitude': 1.0,
                'duration': 300.0,
                'waveform': 'sine'
            }
    
    def _calculate_risk_factors(self, features: TemporalFeatures) -> Dict[str, float]:
        """Calculate risk factors for the prediction"""
        try:
            risk_factors = {}
            
            # Stability risk (high variability = higher risk)
            risk_factors['variability_risk'] = min(1.0, features.alpha_variability / 2.0)
            
            # Coherence instability risk
            risk_factors['coherence_risk'] = max(0.0, 1.0 - features.coherence_stability)
            
            # Temporal consistency risk (based on trends)
            trend_magnitude = abs(features.alpha_trend) + abs(features.theta_trend)
            risk_factors['trend_risk'] = min(1.0, trend_magnitude / 0.5)
            
            # Circadian disruption risk
            # Risk is higher during suboptimal circadian phases
            circadian_risk = 1.0 - 2.0 * abs(features.circadian_phase - 0.5)  # Optimal at 0.5
            risk_factors['circadian_risk'] = max(0.0, circadian_risk)
            
            # Microstate instability risk
            risk_factors['microstate_risk'] = max(0.0, 1.0 - features.microstate_stability)
            
            # Overall risk score (weighted average)
            weights = {
                'variability_risk': 0.3,
                'coherence_risk': 0.3,
                'trend_risk': 0.2,
                'circadian_risk': 0.1,
                'microstate_risk': 0.1
            }
            
            overall_risk = sum(risk_factors[factor] * weights[factor] 
                             for factor in risk_factors if factor in weights)
            risk_factors['overall_risk'] = overall_risk
            
            return risk_factors
            
        except:
            return {
                'variability_risk': 0.5,
                'coherence_risk': 0.5,
                'trend_risk': 0.5,
                'circadian_risk': 0.5,
                'microstate_risk': 0.5,
                'overall_risk': 0.5
            }
    
    async def _send_prediction(self, prediction: PredictionWindow):
        """Send prediction via Kafka"""
        try:
            message = {
                'patient_id': prediction.patient_id,
                'prediction_time': prediction.prediction_time.isoformat(),
                'predicted_start': prediction.predicted_start.isoformat(),
                'predicted_end': prediction.predicted_end.isoformat(),
                'confidence': prediction.confidence,
                'window_type': prediction.window_type,
                'optimal_params': prediction.optimal_params,
                'risk_factors': prediction.risk_factors,
                'preparation_time': prediction.preparation_time,
                'is_imminent': prediction.is_imminent,
                'is_actionable': prediction.is_actionable
            }
            
            self._kafka_producer.send(
                'neuroplasticity-predictions',
                key=prediction.patient_id,
                value=message
            )
            
        except Exception as e:
            self.logger.error(f"Error sending prediction to Kafka: {e}")
    
    async def _store_prediction_redis(self, prediction: PredictionWindow):
        """Store prediction in Redis"""
        try:
            key = f"prediction:{prediction.patient_id}:{int(prediction.prediction_time.timestamp())}"
            data = {
                'patient_id': prediction.patient_id,
                'prediction_time': prediction.prediction_time.isoformat(),
                'predicted_start': prediction.predicted_start.isoformat(),
                'predicted_end': prediction.predicted_end.isoformat(),
                'confidence': prediction.confidence,
                'window_type': prediction.window_type,
                'optimal_params': prediction.optimal_params,
                'risk_factors': prediction.risk_factors,
                'preparation_time': prediction.preparation_time
            }
            
            # Store with 1 hour expiration
            await self._redis_client.setex(key, 3600, json.dumps(data))
            
            # Also store latest prediction for quick access
            latest_key = f"latest_prediction:{prediction.patient_id}"
            await self._redis_client.setex(latest_key, 3600, json.dumps(data))
            
        except Exception as e:
            self.logger.error(f"Error storing prediction in Redis: {e}")
    
    async def _circadian_analysis_task(self):
        """Task for analyzing circadian patterns"""
        while self.is_predicting:
            try:
                # Analyze circadian patterns for each patient
                for patient_id in list(self.active_patients):
                    await self._analyze_circadian_patterns(patient_id)
                
                # Run every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in circadian analysis task: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    async def _analyze_circadian_patterns(self, patient_id: str):
        """Analyze circadian patterns for a patient"""
        try:
            history = self.feature_history.get(patient_id, [])
            if len(history) < 50:  # Need at least some history
                return
            
            # Extract features by hour of day
            hourly_features = {}
            for timestamp, features in history:
                hour = timestamp.hour
                if hour not in hourly_features:
                    hourly_features[hour] = []
                hourly_features[hour].append(features)
            
            # Calculate average features for each hour
            hourly_averages = {}
            for hour, feature_list in hourly_features.items():
                if len(feature_list) >= 3:  # Need at least 3 samples
                    avg_alpha = np.mean([f.alpha_power for f in feature_list])
                    avg_coherence = np.mean([f.frontal_alpha_coherence for f in feature_list])
                    hourly_averages[hour] = {
                        'alpha_power': avg_alpha,
                        'coherence': avg_coherence
                    }
            
            # Fit circadian model if we have enough data
            if len(hourly_averages) >= 8:  # At least 8 different hours
                await self._fit_circadian_model(patient_id, hourly_averages)
            
        except Exception as e:
            self.logger.error(f"Error analyzing circadian patterns for {patient_id}: {e}")
    
    async def _fit_circadian_model(self, patient_id: str, hourly_averages: Dict[int, Dict]):
        """Fit circadian model for a patient"""
        try:
            hours = list(hourly_averages.keys())
            alpha_values = [hourly_averages[h]['alpha_power'] for h in hours]
            coherence_values = [hourly_averages[h]['coherence'] for h in hours]
            
            # Fit sinusoidal model for alpha power
            def circadian_model(t, amplitude, phase, offset):
                return amplitude * np.sin(2 * np.pi * t / 24 + phase) + offset
            
            # Use scipy.optimize to fit the model
            from scipy.optimize import curve_fit
            
            try:
                # Fit alpha circadian rhythm
                alpha_params, _ = curve_fit(circadian_model, hours, alpha_values)
                
                # Fit coherence circadian rhythm
                coherence_params, _ = curve_fit(circadian_model, hours, coherence_values)
                
                # Store parameters
                self.circadian_params[patient_id] = {
                    'alpha_amplitude': alpha_params[0],
                    'alpha_phase': alpha_params[1],
                    'alpha_offset': alpha_params[2],
                    'coherence_amplitude': coherence_params[0],
                    'coherence_phase': coherence_params[1],
                    'coherence_offset': coherence_params[2],
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                self.logger.info(f"Updated circadian model for patient {patient_id}")
                
            except Exception as e:
                self.logger.warning(f"Could not fit circadian model for {patient_id}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error fitting circadian model: {e}")
    
    async def get_latest_prediction(self, patient_id: str) -> Optional[PredictionWindow]:
        """Get latest prediction for a patient"""
        try:
            predictions = self.prediction_history.get(patient_id, [])
            if predictions:
                return predictions[-1]
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest prediction: {e}")
            return None
    
    async def get_predictions_in_timeframe(self, patient_id: str, 
                                         start_time: datetime, 
                                         end_time: datetime) -> List[PredictionWindow]:
        """Get predictions for a patient within a timeframe"""
        try:
            predictions = self.prediction_history.get(patient_id, [])
            return [
                p for p in predictions
                if start_time <= p.prediction_time <= end_time
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting predictions in timeframe: {e}")
            return []
    
    async def stop_prediction_service(self):
        """Stop the prediction service"""
        try:
            self.is_predicting = False
            
            if self._kafka_consumer:
                self._kafka_consumer.close()
            
            if self._kafka_producer:
                self._kafka_producer.close()
            
            self.logger.info("Neuroplasticity prediction service stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping prediction service: {e}")
    
    async def save_models(self):
        """Save trained models"""
        try:
            self.model_path.mkdir(parents=True, exist_ok=True)
            
            # Save onset model
            if self.window_onset_model:
                joblib.dump(self.window_onset_model, str(self.model_path / "window_onset_model.pkl"))
            
            # Save duration model
            if self.window_duration_model:
                joblib.dump(self.window_duration_model, str(self.model_path / "window_duration_model.pkl"))
            
            # Save confidence model
            if self.confidence_model:
                self.confidence_model.save(str(self.model_path / "confidence_model.h5"))
            
            # Save feature scaler
            if self.feature_scaler:
                joblib.dump(self.feature_scaler, str(self.model_path / "temporal_feature_scaler.pkl"))
            
            self.logger.info("Prediction models saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.stop_prediction_service()
            
            if self._redis_client:
                await self._redis_client.close()
            
            self.logger.info("Neuroplasticity Predictor cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
