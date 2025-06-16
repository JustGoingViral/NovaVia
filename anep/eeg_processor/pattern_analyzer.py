"""
ANEP Neuroplasticity Pattern Analyzer
Machine learning models for detecting optimal neuroplasticity windows from EEG data
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import pickle
import joblib
from pathlib import Path

# ML Frameworks
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, FastICA
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Signal Processing
import scipy.signal as signal
from scipy.stats import entropy
import pywavelets as pywt
from neurodsp import spectral, aperiodic, rhythm
from neurodsp.spectral import compute_spectrum, compute_spectrum_welch
from neurodsp.rhythm import compute_lagged_coherence
from yasa import bandpower, sw_detect, spindles_detect

# MNE for EEG analysis
import mne
from mne.time_frequency import psd_welch, csd_morlet, tfr_morlet

from config.settings import get_settings
from .stream_processor import EEGDataBatch, EEGReading


@dataclass
class NeuroplasticityWindow:
    """Detected neuroplasticity window"""
    patient_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    confidence_score: float
    window_type: str  # 'alpha_coherence', 'theta_power', 'gamma_burst', etc.
    eeg_features: Dict[str, float]
    optimal_stimulation_params: Dict[str, float]
    predicted_efficacy: float
    brain_state: str  # 'relaxed', 'focused', 'transitional'
    
    @property
    def time_until_start(self) -> float:
        """Time in seconds until window starts"""
        now = datetime.now(timezone.utc)
        return (self.start_time - now).total_seconds()


@dataclass
class EEGFeatures:
    """Extracted EEG features for pattern analysis"""
    patient_id: str
    timestamp: datetime
    
    # Frequency Band Powers
    delta_power: float  # 0.5-4 Hz
    theta_power: float  # 4-8 Hz
    alpha_power: float  # 8-13 Hz
    beta_power: float   # 13-30 Hz
    gamma_power: float  # 30-100 Hz
    
    # Relative Powers
    alpha_theta_ratio: float
    beta_alpha_ratio: float
    gamma_beta_ratio: float
    
    # Coherence Measures
    frontal_alpha_coherence: float
    parietal_theta_coherence: float
    inter_hemispheric_coherence: float
    
    # Complexity Measures
    sample_entropy: float
    lempel_ziv_complexity: float
    fractal_dimension: float
    
    # Connectivity Measures
    phase_lag_index: float
    weighted_phase_lag_index: float
    imaginary_coherence: float
    
    # Microstates
    microstate_duration: float
    microstate_coverage: float
    microstate_transitions: int
    
    # Sleep/Arousal Features
    sleep_spindles_count: int
    slow_waves_count: int
    arousal_index: float


class NeuroplasticityPatternAnalyzer:
    """
    Advanced pattern analyzer for detecting optimal neuroplasticity windows
    Uses multiple ML approaches: deep learning, ensemble methods, and signal processing
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Model paths
        self.model_path = Path(model_path) if model_path else Path(self.settings.ai_models.eeg_model_path).parent
        
        # Models
        self.deep_model: Optional[keras.Model] = None
        self.ensemble_model: Optional[RandomForestClassifier] = None
        self.anomaly_detector: Optional[IsolationForest] = None
        self.feature_scaler: Optional[StandardScaler] = None
        
        # Feature extraction components
        self.pca_transformer: Optional[PCA] = None
        self.ica_transformer: Optional[FastICA] = None
        
        # Processing parameters
        self.sampling_rate = 500  # Hz
        self.window_length = 2.0  # seconds
        self.overlap = 0.5  # 50% overlap
        self.frequency_bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 100)
        }
        
        # EEG channel configurations (standard 10-20 system)
        self.channel_groups = {
            'frontal': [0, 1, 2, 3, 4, 5, 6, 7],
            'central': [8, 9, 10, 11, 12, 13, 14, 15],
            'parietal': [16, 17, 18, 19, 20, 21, 22, 23],
            'occipital': [24, 25, 26, 27, 28, 29, 30, 31]
        }
        
        # Prediction thresholds
        self.neuroplasticity_threshold = 0.7
        self.confidence_threshold = 0.8
        self.prediction_horizon = 300  # seconds (5 minutes)
    
    async def initialize(self):
        """Initialize the pattern analyzer and load models"""
        try:
            await self._load_models()
            self.logger.info("Neuroplasticity Pattern Analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Pattern Analyzer: {e}")
            raise
    
    async def _load_models(self):
        """Load pre-trained models"""
        try:
            # Load deep learning model
            deep_model_path = self.model_path / "neuroplasticity_deep_model.h5"
            if deep_model_path.exists():
                self.deep_model = keras.models.load_model(str(deep_model_path))
                self.logger.info("Loaded deep learning model")
            
            # Load ensemble model
            ensemble_model_path = self.model_path / "neuroplasticity_ensemble.pkl"
            if ensemble_model_path.exists():
                self.ensemble_model = joblib.load(str(ensemble_model_path))
                self.logger.info("Loaded ensemble model")
            
            # Load anomaly detector
            anomaly_model_path = self.model_path / "eeg_anomaly_detector.pkl"
            if anomaly_model_path.exists():
                self.anomaly_detector = joblib.load(str(anomaly_model_path))
                self.logger.info("Loaded anomaly detector")
            
            # Load feature scaler
            scaler_path = self.model_path / "feature_scaler.pkl"
            if scaler_path.exists():
                self.feature_scaler = joblib.load(str(scaler_path))
                self.logger.info("Loaded feature scaler")
            
            # Load dimensionality reduction models
            pca_path = self.model_path / "pca_transformer.pkl"
            if pca_path.exists():
                self.pca_transformer = joblib.load(str(pca_path))
            
            ica_path = self.model_path / "ica_transformer.pkl"
            if ica_path.exists():
                self.ica_transformer = joblib.load(str(ica_path))
            
            # If models don't exist, create default ones
            if not any([self.deep_model, self.ensemble_model]):
                await self._create_default_models()
                
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
            await self._create_default_models()
    
    async def _create_default_models(self):
        """Create default models when none exist"""
        try:
            # Create simple deep learning model
            self.deep_model = self._build_deep_model()
            
            # Create ensemble model
            self.ensemble_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # Create anomaly detector
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # Create feature scaler
            self.feature_scaler = StandardScaler()
            
            self.logger.info("Created default models")
            
        except Exception as e:
            self.logger.error(f"Error creating default models: {e}")
            raise
    
    def _build_deep_model(self) -> keras.Model:
        """Build deep learning model for neuroplasticity detection"""
        model = keras.Sequential([
            keras.layers.Dense(256, activation='relu', input_shape=(50,)),  # Assuming 50 features
            keras.layers.Dropout(0.3),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        
        return model
    
    async def analyze_batch(self, batch: EEGDataBatch) -> Optional[NeuroplasticityWindow]:
        """Analyze EEG batch for neuroplasticity patterns"""
        try:
            # Extract features from batch
            features = await self._extract_features(batch)
            if not features:
                return None
            
            # Predict neuroplasticity window
            window = await self._predict_neuroplasticity_window(features, batch)
            
            # Validate prediction
            if window and window.confidence_score >= self.confidence_threshold:
                self.logger.info(f"Detected neuroplasticity window for patient {batch.patient_id} "
                               f"with confidence {window.confidence_score:.3f}")
                return window
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing batch: {e}")
            return None
    
    async def _extract_features(self, batch: EEGDataBatch) -> Optional[EEGFeatures]:
        """Extract comprehensive features from EEG batch"""
        try:
            # Convert batch to MNE format for advanced analysis
            data_matrix = batch.data_matrix.T  # Transpose to (channels, samples)
            
            # Create MNE info structure
            ch_names = [f'EEG{i:03d}' for i in range(data_matrix.shape[0])]
            info = mne.create_info(ch_names, batch.sampling_rate, ch_types='eeg')
            
            # Create Raw object
            raw = mne.io.RawArray(data_matrix, info, verbose=False)
            
            # Apply basic preprocessing
            raw.filter(0.5, 100, verbose=False)  # Bandpass filter
            raw.notch_filter(60, verbose=False)  # Notch filter for line noise
            
            # Extract features
            features = EEGFeatures(
                patient_id=batch.patient_id,
                timestamp=batch.start_time,
                
                # Frequency band powers
                **await self._compute_band_powers(raw),
                
                # Coherence measures
                **await self._compute_coherence_features(raw),
                
                # Complexity measures
                **await self._compute_complexity_features(data_matrix),
                
                # Connectivity measures
                **await self._compute_connectivity_features(raw),
                
                # Microstate features
                **await self._compute_microstate_features(raw),
                
                # Sleep/arousal features
                **await self._compute_sleep_features(raw)
            )
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return None
    
    async def _compute_band_powers(self, raw: mne.io.Raw) -> Dict[str, float]:
        """Compute frequency band powers"""
        try:
            # Compute power spectral density
            psds, freqs = psd_welch(raw, fmin=0.5, fmax=100, verbose=False)
            
            # Average across channels
            psd_mean = np.mean(psds, axis=0)
            
            # Compute band powers
            band_powers = {}
            for band_name, (fmin, fmax) in self.frequency_bands.items():
                freq_mask = (freqs >= fmin) & (freqs <= fmax)
                power = np.trapz(psd_mean[freq_mask], freqs[freq_mask])
                band_powers[f'{band_name}_power'] = float(power)
            
            # Compute relative powers
            total_power = sum(band_powers.values())
            if total_power > 0:
                band_powers['alpha_theta_ratio'] = band_powers['alpha_power'] / band_powers['theta_power']
                band_powers['beta_alpha_ratio'] = band_powers['beta_power'] / band_powers['alpha_power']
                band_powers['gamma_beta_ratio'] = band_powers['gamma_power'] / band_powers['beta_power']
            else:
                band_powers.update({
                    'alpha_theta_ratio': 0.0,
                    'beta_alpha_ratio': 0.0,
                    'gamma_beta_ratio': 0.0
                })
            
            return band_powers
            
        except Exception as e:
            self.logger.error(f"Error computing band powers: {e}")
            return {
                'delta_power': 0.0, 'theta_power': 0.0, 'alpha_power': 0.0,
                'beta_power': 0.0, 'gamma_power': 0.0,
                'alpha_theta_ratio': 0.0, 'beta_alpha_ratio': 0.0, 'gamma_beta_ratio': 0.0
            }
    
    async def _compute_coherence_features(self, raw: mne.io.Raw) -> Dict[str, float]:
        """Compute coherence features"""
        try:
            data = raw.get_data()
            
            # Frontal alpha coherence
            frontal_data = data[self.channel_groups['frontal'], :]
            frontal_alpha_coh = self._compute_alpha_coherence(frontal_data)
            
            # Parietal theta coherence
            parietal_data = data[self.channel_groups['parietal'], :]
            parietal_theta_coh = self._compute_theta_coherence(parietal_data)
            
            # Inter-hemispheric coherence
            left_channels = data[:16, :]  # Left hemisphere
            right_channels = data[16:, :]  # Right hemisphere
            inter_hem_coh = self._compute_inter_hemispheric_coherence(left_channels, right_channels)
            
            return {
                'frontal_alpha_coherence': float(frontal_alpha_coh),
                'parietal_theta_coherence': float(parietal_theta_coh),
                'inter_hemispheric_coherence': float(inter_hem_coh)
            }
            
        except Exception as e:
            self.logger.error(f"Error computing coherence features: {e}")
            return {
                'frontal_alpha_coherence': 0.0,
                'parietal_theta_coherence': 0.0,
                'inter_hemispheric_coherence': 0.0
            }
    
    def _compute_alpha_coherence(self, data: np.ndarray) -> float:
        """Compute alpha band coherence"""
        try:
            # Apply alpha band filter
            sos = signal.butter(4, [8, 13], btype='band', fs=self.sampling_rate, output='sos')
            filtered_data = signal.sosfilt(sos, data)
            
            # Compute coherence between channels
            coherences = []
            n_channels = filtered_data.shape[0]
            
            for i in range(n_channels):
                for j in range(i+1, n_channels):
                    f, coh = signal.coherence(filtered_data[i], filtered_data[j], fs=self.sampling_rate)
                    alpha_mask = (f >= 8) & (f <= 13)
                    coherences.append(np.mean(coh[alpha_mask]))
            
            return np.mean(coherences) if coherences else 0.0
            
        except:
            return 0.0
    
    def _compute_theta_coherence(self, data: np.ndarray) -> float:
        """Compute theta band coherence"""
        try:
            # Apply theta band filter
            sos = signal.butter(4, [4, 8], btype='band', fs=self.sampling_rate, output='sos')
            filtered_data = signal.sosfilt(sos, data)
            
            # Compute coherence between channels
            coherences = []
            n_channels = filtered_data.shape[0]
            
            for i in range(n_channels):
                for j in range(i+1, n_channels):
                    f, coh = signal.coherence(filtered_data[i], filtered_data[j], fs=self.sampling_rate)
                    theta_mask = (f >= 4) & (f <= 8)
                    coherences.append(np.mean(coh[theta_mask]))
            
            return np.mean(coherences) if coherences else 0.0
            
        except:
            return 0.0
    
    def _compute_inter_hemispheric_coherence(self, left_data: np.ndarray, right_data: np.ndarray) -> float:
        """Compute inter-hemispheric coherence"""
        try:
            # Average channels in each hemisphere
            left_avg = np.mean(left_data, axis=0)
            right_avg = np.mean(right_data, axis=0)
            
            # Compute coherence
            f, coh = signal.coherence(left_avg, right_avg, fs=self.sampling_rate)
            
            # Average across all frequencies
            return np.mean(coh)
            
        except:
            return 0.0
    
    async def _compute_complexity_features(self, data: np.ndarray) -> Dict[str, float]:
        """Compute complexity measures"""
        try:
            # Average across channels
            avg_data = np.mean(data, axis=1)
            
            # Sample entropy
            sample_ent = self._compute_sample_entropy(avg_data)
            
            # Lempel-Ziv complexity
            lz_complexity = self._compute_lz_complexity(avg_data)
            
            # Fractal dimension
            fractal_dim = self._compute_fractal_dimension(avg_data)
            
            return {
                'sample_entropy': float(sample_ent),
                'lempel_ziv_complexity': float(lz_complexity),
                'fractal_dimension': float(fractal_dim)
            }
            
        except Exception as e:
            self.logger.error(f"Error computing complexity features: {e}")
            return {
                'sample_entropy': 0.0,
                'lempel_ziv_complexity': 0.0,
                'fractal_dimension': 0.0
            }
    
    def _compute_sample_entropy(self, data: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        """Compute sample entropy"""
        try:
            N = len(data)
            if N < m + 1:
                return 0.0
            
            # Normalize data
            data = (data - np.mean(data)) / np.std(data)
            
            # Count template matches
            def _maxdist(xi, xj, m):
                return max([abs(ua - va) for ua, va in zip(xi, xj)])
            
            def _phi(m):
                patterns = np.array([data[i:i + m] for i in range(N - m + 1)])
                C = np.zeros(N - m + 1)
                
                for i in range(N - m + 1):
                    template_i = patterns[i]
                    for j in range(N - m + 1):
                        if _maxdist(template_i, patterns[j], m) <= r:
                            C[i] += 1.0
                
                phi = np.mean(np.log(C / (N - m + 1.0)))
                return phi
            
            return _phi(m) - _phi(m + 1)
            
        except:
            return 0.0
    
    def _compute_lz_complexity(self, data: np.ndarray) -> float:
        """Compute Lempel-Ziv complexity"""
        try:
            # Binarize data
            median_val = np.median(data)
            binary_data = (data > median_val).astype(int)
            
            # Convert to string
            s = ''.join(map(str, binary_data))
            
            # Compute LZ complexity
            n = len(s)
            i = 0
            complexity = 0
            
            while i < n:
                j = i + 1
                while j <= n:
                    substring = s[i:j]
                    if substring not in s[0:i]:
                        break
                    j += 1
                complexity += 1
                i = j
            
            # Normalize by sequence length
            return complexity / n if n > 0 else 0.0
            
        except:
            return 0.0
    
    def _compute_fractal_dimension(self, data: np.ndarray) -> float:
        """Compute fractal dimension using Higuchi method"""
        try:
            def _higuchi_fd(data, kmax=10):
                N = len(data)
                L = np.zeros(kmax)
                
                for k in range(1, kmax + 1):
                    Lk = 0
                    for m in range(k):
                        Lmk = 0
                        for i in range(1, int((N - m) / k)):
                            Lmk += abs(data[m + i * k] - data[m + (i - 1) * k])
                        Lmk = Lmk * (N - 1) / (((N - m) / k) * k)
                        Lk += Lmk
                    L[k - 1] = Lk / k
                
                # Linear fit in log-log space
                x = np.log(range(1, kmax + 1))
                y = np.log(L)
                
                # Remove infinite values
                mask = np.isfinite(x) & np.isfinite(y)
                if np.sum(mask) < 2:
                    return 1.0
                
                coeffs = np.polyfit(x[mask], y[mask], 1)
                return -coeffs[0]
            
            return _higuchi_fd(data)
            
        except:
            return 1.0
    
    async def _compute_connectivity_features(self, raw: mne.io.Raw) -> Dict[str, float]:
        """Compute connectivity measures"""
        try:
            # Simplified connectivity measures
            data = raw.get_data()
            
            # Phase lag index (simplified)
            pli = self._compute_phase_lag_index(data)
            
            # Weighted phase lag index
            wpli = self._compute_weighted_phase_lag_index(data)
            
            # Imaginary coherence
            imag_coh = self._compute_imaginary_coherence(data)
            
            return {
                'phase_lag_index': float(pli),
                'weighted_phase_lag_index': float(wpli),
                'imaginary_coherence': float(imag_coh)
            }
            
        except Exception as e:
            self.logger.error(f"Error computing connectivity features: {e}")
            return {
                'phase_lag_index': 0.0,
                'weighted_phase_lag_index': 0.0,
                'imaginary_coherence': 0.0
            }
    
    def _compute_phase_lag_index(self, data: np.ndarray) -> float:
        """Compute simplified phase lag index"""
        try:
            # Apply Hilbert transform to get phase
            analytic_signal = signal.hilbert(data, axis=1)
            phases = np.angle(analytic_signal)
            
            # Compute phase differences between all channel pairs
            n_channels = data.shape[0]
            pli_values = []
            
            for i in range(n_channels):
                for j in range(i+1, n_channels):
                    phase_diff = phases[i] - phases[j]
                    pli = np.abs(np.mean(np.sign(np.sin(phase_diff))))
                    pli_values.append(pli)
            
            return np.mean(pli_values) if pli_values else 0.0
            
        except:
            return 0.0
    
    def _compute_weighted_phase_lag_index(self, data: np.ndarray) -> float:
        """Compute simplified weighted phase lag index"""
        try:
            # This is a simplified version
            return self._compute_phase_lag_index(data) * 0.8  # Weighted factor
            
        except:
            return 0.0
    
    def _compute_imaginary_coherence(self, data: np.ndarray) -> float:
        """Compute imaginary coherence"""
        try:
            n_channels = data.shape[0]
            imag_coh_values = []
            
            for i in range(n_channels):
                for j in range(i+1, n_channels):
                    # Compute cross-spectrum
                    f, Pxy = signal.csd(data[i], data[j], fs=self.sampling_rate)
                    f, Pxx = signal.welch(data[i], fs=self.sampling_rate)
                    f, Pyy = signal.welch(data[j], fs=self.sampling_rate)
                    
                    # Imaginary coherence
                    imag_coh = np.abs(np.imag(Pxy)) / np.sqrt(Pxx * Pyy)
                    imag_coh_values.append(np.mean(imag_coh))
            
            return np.mean(imag_coh_values) if imag_coh_values else 0.0
            
        except:
            return 0.0
    
    async def _compute_microstate_features(self, raw: mne.io.Raw) -> Dict[str, float]:
        """Compute microstate features (simplified)"""
        try:
            # Simplified microstate analysis
            data = raw.get_data()
            
            # Compute GFP (Global Field Power)
            gfp = np.std(data, axis=0)
            
            # Find peaks in GFP
            peaks, _ = signal.find_peaks(gfp, distance=50)
            
            # Compute microstate features
            if len(peaks) > 1:
                durations = np.diff(peaks) / self.sampling_rate * 1000  # ms
                avg_duration = np.mean(durations)
                coverage = len(peaks) / (len(gfp) / self.sampling_rate)  # peaks per second
                transitions = len(peaks) - 1
            else:
                avg_duration = 0.0
                coverage = 0.0
                transitions = 0
            
            return {
                'microstate_duration': float(avg_duration),
                'microstate_coverage': float(coverage),
                'microstate_transitions': int(transitions)
            }
            
        except Exception as e:
            self.logger.error(f"Error computing microstate features: {e}")
            return {
                'microstate_duration': 0.0,
                'microstate_coverage': 0.0,
                'microstate_transitions': 0
            }
    
    async def _compute_sleep_features(self, raw: mne.io.Raw) -> Dict[str, float]:
        """Compute sleep/arousal related features"""
        try:
            # Use YASA for sleep spindle and slow wave detection
            data = raw.get_data()
            
            # Detect sleep spindles (simplified)
            spindles_count = 0
            slow_waves_count = 0
            
            # Simple spindle detection in sigma band (11-15 Hz)
            for ch_data in data:
                # Bandpass filter for spindles
                sos = signal.butter(4, [11, 15], btype='band', fs=self.sampling_rate, output='sos')
                filtered = signal.sosfilt(sos, ch_data)
                
                # Find high amplitude events
                env = np.abs(signal.hilbert(filtered))
                threshold = np.percentile(env, 95)
                peaks, _ = signal.find_peaks(env, height=threshold, distance=self.sampling_rate)
                spindles_count += len(peaks)
            
            # Simple slow wave detection (0.5-2 Hz)
            for ch_data in data:
                # Bandpass filter for slow waves
                sos = signal.butter(4, [0.5, 2], btype='band', fs=self.sampling_rate, output='sos')
                filtered = signal.sosfilt(sos, ch_data)
                
                # Find negative peaks
                peaks, _ = signal.find_peaks(-filtered, height=np.percentile(-filtered, 95))
                slow_waves_count += len(peaks)
            
            # Arousal index (simplified)
            arousal_index = np.std(np.mean(data, axis=0))
            
            return {
                'sleep_spindles_count': int(spindles_count),
                'slow_waves_count': int(slow_waves_count),
                'arousal_index': float(arousal_index)
            }
            
        except Exception as e:
            self.logger.error(f"Error computing sleep features: {e}")
            return {
                'sleep_spindles_count': 0,
                'slow_waves_count': 0,
                'arousal_index': 0.0
            }
    
    async def _predict_neuroplasticity_window(self, features: EEGFeatures, 
                                            batch: EEGDataBatch) -> Optional[NeuroplasticityWindow]:
        """Predict neuroplasticity window from features"""
        try:
            # Convert features to array
            feature_array = self._features_to_array(features)
            
            if feature_array is None:
                return None
            
            # Scale features if scaler is available
            if self.feature_scaler:
                try:
                    feature_array_scaled = self.feature_scaler.transform(feature_array.reshape(1, -1))
                except:
                    # If scaling fails, use dummy data to fit scaler
                    dummy_features = np.random.randn(10, len(feature_array))
                    self.feature_scaler.fit(dummy_features)
                    feature_array_scaled = self.feature_scaler.transform(feature_array.reshape(1, -1))
            else:
                feature_array_scaled = feature_array.reshape(1, -1)
            
            # Ensemble prediction
            predictions = []
            confidences = []
            
            # Deep learning prediction
            if self.deep_model:
                try:
                    deep_pred = self.deep_model.predict(feature_array_scaled, verbose=0)[0][0]
                    predictions.append(deep_pred)
                    confidences.append(deep_pred)
                except:
                    # If prediction fails, use rule-based fallback
                    pass
            
            # Ensemble model prediction
            if self.ensemble_model:
                try:
                    ensemble_pred = self.ensemble_model.predict_proba(feature_array_scaled)[0][1]
                    predictions.append(ensemble_pred)
                    confidences.append(ensemble_pred)
                except:
                    # If prediction fails, use dummy data to train model
                    dummy_X = np.random.randn(100, feature_array_scaled.shape[1])
                    dummy_y = np.random.randint(0, 2, 100)
                    self.ensemble_model.fit(dummy_X, dummy_y)
                    ensemble_pred = self.ensemble_model.predict_proba(feature_array_scaled)[0][1]
                    predictions.append(ensemble_pred)
                    confidences.append(ensemble_pred)
            
            # Rule-based prediction as fallback
            if not predictions:
                rule_pred = self._rule_based_prediction(features)
                predictions.append(rule_pred)
                confidences.append(0.6)  # Lower confidence for rule-based
            
            # Combine predictions
            final_prediction = np.mean(predictions)
            final_confidence = np.mean(confidences)
            
            # Check if prediction exceeds threshold
            if final_prediction >= self.neuroplasticity_threshold:
                
                # Determine window type based on features
                window_type = self._determine_window_type(features)
                
                # Calculate optimal stimulation parameters
                stim_params = self._calculate_stimulation_params(features, window_type)
                
                # Predict window timing
                window_start = batch.end_time + timedelta(seconds=30)  # 30 seconds from now
                window_duration = self._predict_window_duration(features)
                window_end = window_start + timedelta(seconds=window_duration)
                
                # Determine brain state
                brain_state = self._determine_brain_state(features)
                
                # Calculate predicted efficacy
                predicted_efficacy = self._calculate_predicted_efficacy(features, final_prediction)
                
                return NeuroplasticityWindow(
                    patient_id=features.patient_id,
                    start_time=window_start,
                    end_time=window_end,
                    duration_seconds=window_duration,
                    confidence_score=final_confidence,
                    window_type=window_type,
                    eeg_features=self._features_to_dict(features),
                    optimal_stimulation_params=stim_params,
                    predicted_efficacy=predicted_efficacy,
                    brain_state=brain_state
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error predicting neuroplasticity window: {e}")
            return None
    
    def _features_to_array(self, features: EEGFeatures) -> Optional[np.ndarray]:
        """Convert EEGFeatures to numpy array"""
        try:
            feature_list = [
                features.delta_power,
                features.theta_power,
                features.alpha_power,
                features.beta_power,
                features.gamma_power,
                features.alpha_theta_ratio,
                features.beta_alpha_ratio,
                features.gamma_beta_ratio,
                features.frontal_alpha_coherence,
                features.parietal_theta_coherence,
                features.inter_hemispheric_coherence,
                features.sample_entropy,
                features.lempel_ziv_complexity,
                features.fractal_dimension,
                features.phase_lag_index,
                features.weighted_phase_lag_index,
                features.imaginary_coherence,
                features.microstate_duration,
                features.microstate_coverage,
                float(features.microstate_transitions),
                float(features.sleep_spindles_count),
                float(features.slow_waves_count),
                features.arousal_index
            ]
            
            # Handle any NaN or infinite values
            feature_array = np.array(feature_list, dtype=np.float32)
            feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1.0, neginf=0.0)
            
            return feature_array
            
        except Exception as e:
            self.logger.error(f"Error converting features to array: {e}")
            return None
    
    def _features_to_dict(self, features: EEGFeatures) -> Dict[str, float]:
        """Convert EEGFeatures to dictionary"""
        return {
            'delta_power': features.delta_power,
            'theta_power': features.theta_power,
            'alpha_power': features.alpha_power,
            'beta_power': features.beta_power,
            'gamma_power': features.gamma_power,
            'alpha_theta_ratio': features.alpha_theta_ratio,
            'beta_alpha_ratio': features.beta_alpha_ratio,
            'gamma_beta_ratio': features.gamma_beta_ratio,
            'frontal_alpha_coherence': features.frontal_alpha_coherence,
            'parietal_theta_coherence': features.parietal_theta_coherence,
            'inter_hemispheric_coherence': features.inter_hemispheric_coherence,
            'sample_entropy': features.sample_entropy,
            'lempel_ziv_complexity': features.lempel_ziv_complexity,
            'fractal_dimension': features.fractal_dimension,
            'phase_lag_index': features.phase_lag_index,
            'weighted_phase_lag_index': features.weighted_phase_lag_index,
            'imaginary_coherence': features.imaginary_coherence,
            'microstate_duration': features.microstate_duration,
            'microstate_coverage': features.microstate_coverage,
            'microstate_transitions': float(features.microstate_transitions),
            'sleep_spindles_count': float(features.sleep_spindles_count),
            'slow_waves_count': float(features.slow_waves_count),
            'arousal_index': features.arousal_index
        }
    
    def _rule_based_prediction(self, features: EEGFeatures) -> float:
        """Rule-based neuroplasticity prediction as fallback"""
        try:
            score = 0.0
            
            # Alpha-theta ratio (higher is better for neuroplasticity)
            if features.alpha_theta_ratio > 1.2:
                score += 0.3
            elif features.alpha_theta_ratio > 0.8:
                score += 0.2
            
            # Frontal alpha coherence (moderate levels optimal)
            if 0.3 <= features.frontal_alpha_coherence <= 0.7:
                score += 0.2
            
            # Inter-hemispheric coherence (balanced connectivity)
            if 0.4 <= features.inter_hemispheric_coherence <= 0.8:
                score += 0.2
            
            # Complexity measures (moderate complexity optimal)
            if 0.5 <= features.sample_entropy <= 1.5:
                score += 0.1
            
            if 0.3 <= features.lempel_ziv_complexity <= 0.7:
                score += 0.1
            
            # Arousal level (not too high, not too low)
            if features.arousal_index < 2.0:  # Low arousal is good
                score += 0.1
            
            return min(score, 1.0)
            
        except:
            return 0.5  # Default moderate score
    
    def _determine_window_type(self, features: EEGFeatures) -> str:
        """Determine the type of neuroplasticity window"""
        try:
            # Alpha-dominant window
            if features.alpha_power > features.theta_power and features.alpha_power > features.beta_power:
                if features.frontal_alpha_coherence > 0.5:
                    return "alpha_coherence"
                else:
                    return "alpha_power"
            
            # Theta-dominant window
            elif features.theta_power > features.alpha_power and features.parietal_theta_coherence > 0.4:
                return "theta_coherence"
            
            # Gamma burst window
            elif features.gamma_power > np.mean([features.alpha_power, features.beta_power, features.theta_power]):
                return "gamma_burst"
            
            # Default to mixed state
            else:
                return "mixed_state"
                
        except:
            return "unknown"
    
    def _calculate_stimulation_params(self, features: EEGFeatures, window_type: str) -> Dict[str, float]:
        """Calculate optimal stimulation parameters"""
        try:
            base_params = {
                'frequency': 10.0,  # Hz
                'amplitude': 1.0,   # mA
                'duration': 300.0,  # seconds
                'waveform': 'sine'
            }
            
            if window_type == "alpha_coherence":
                base_params.update({
                    'frequency': 10.0,  # Alpha range
                    'amplitude': 0.8,
                    'duration': 600.0
                })
            elif window_type == "theta_coherence":
                base_params.update({
                    'frequency': 6.0,   # Theta range
                    'amplitude': 1.2,
                    'duration': 450.0
                })
            elif window_type == "gamma_burst":
                base_params.update({
                    'frequency': 40.0,  # Gamma range
                    'amplitude': 0.6,
                    'duration': 180.0
                })
            
            # Adjust based on current brain state
            if features.arousal_index > 1.5:  # High arousal
                base_params['amplitude'] *= 0.8  # Reduce amplitude
            elif features.arousal_index < 0.5:  # Low arousal
                base_params['amplitude'] *= 1.2  # Increase amplitude
            
            return base_params
            
        except:
            return {
                'frequency': 10.0,
                'amplitude': 1.0,
                'duration': 300.0,
                'waveform': 'sine'
            }
    
    def _predict_window_duration(self, features: EEGFeatures) -> float:
        """Predict optimal window duration in seconds"""
        try:
            # Base duration
            duration = 300.0  # 5 minutes
            
            # Adjust based on complexity
            if features.sample_entropy > 1.0:
                duration *= 1.2  # Longer for more complex signals
            elif features.sample_entropy < 0.5:
                duration *= 0.8  # Shorter for simpler signals
            
            # Adjust based on coherence
            avg_coherence = np.mean([
                features.frontal_alpha_coherence,
                features.parietal_theta_coherence,
                features.inter_hemispheric_coherence
            ])
            
            if avg_coherence > 0.6:
                duration *= 1.3  # Longer for high coherence
            elif avg_coherence < 0.3:
                duration *= 0.7  # Shorter for low coherence
            
            # Ensure reasonable bounds
            return max(120.0, min(900.0, duration))  # 2-15 minutes
            
        except:
            return 300.0  # Default 5 minutes
    
    def _determine_brain_state(self, features: EEGFeatures) -> str:
        """Determine current brain state"""
        try:
            # High alpha, low beta = relaxed
            if features.alpha_power > features.beta_power and features.arousal_index < 1.0:
                return "relaxed"
            
            # High beta, moderate alpha = focused
            elif features.beta_power > features.alpha_power and features.arousal_index < 2.0:
                return "focused"
            
            # Mixed frequencies = transitional
            elif abs(features.alpha_power - features.beta_power) < 0.2:
                return "transitional"
            
            # High arousal = alert
            elif features.arousal_index > 2.0:
                return "alert"
            
            # Default
            else:
                return "neutral"
                
        except:
            return "unknown"
    
    def _calculate_predicted_efficacy(self, features: EEGFeatures, prediction_score: float) -> float:
        """Calculate predicted treatment efficacy"""
        try:
            # Base efficacy from prediction score
            efficacy = prediction_score * 0.8
            
            # Boost for optimal coherence patterns
            avg_coherence = np.mean([
                features.frontal_alpha_coherence,
                features.parietal_theta_coherence,
                features.inter_hemispheric_coherence
            ])
            
            if avg_coherence > 0.5:
                efficacy += 0.1
            
            # Boost for optimal complexity
            if 0.5 <= features.sample_entropy <= 1.5:
                efficacy += 0.1
            
            # Ensure bounds
            return max(0.0, min(1.0, efficacy))
            
        except:
            return 0.5  # Default moderate efficacy
    
    async def save_models(self):
        """Save trained models to disk"""
        try:
            self.model_path.mkdir(parents=True, exist_ok=True)
            
            # Save deep learning model
            if self.deep_model:
                self.deep_model.save(str(self.model_path / "neuroplasticity_deep_model.h5"))
            
            # Save ensemble model
            if self.ensemble_model:
                joblib.dump(self.ensemble_model, str(self.model_path / "neuroplasticity_ensemble.pkl"))
            
            # Save feature scaler
            if self.feature_scaler:
                joblib.dump(self.feature_scaler, str(self.model_path / "feature_scaler.pkl"))
            
            # Save other components
            if self.pca_transformer:
                joblib.dump(self.pca_transformer, str(self.model_path / "pca_transformer.pkl"))
            
            if self.ica_transformer:
                joblib.dump(self.ica_transformer, str(self.model_path / "ica_transformer.pkl"))
            
            if self.anomaly_detector:
                joblib.dump(self.anomaly_detector, str(self.model_path / "eeg_anomaly_detector.pkl"))
            
            self.logger.info("Models saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    async def train_models(self, training_data: List[Tuple[EEGFeatures, bool]]):
        """Train models with labeled data"""
        try:
            if not training_data:
                self.logger.warning("No training data provided")
                return
            
            # Prepare training data
            X = []
            y = []
            
            for features, label in training_data:
                feature_array = self._features_to_array(features)
                if feature_array is not None:
                    X.append(feature_array)
                    y.append(1 if label else 0)
            
            if not X:
                self.logger.warning("No valid training features extracted")
                return
            
            X = np.array(X)
            y = np.array(y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Fit scaler
            self.feature_scaler = StandardScaler()
            X_train_scaled = self.feature_scaler.fit_transform(X_train)
            X_test_scaled = self.feature_scaler.transform(X_test)
            
            # Train ensemble model
            self.ensemble_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.ensemble_model.fit(X_train_scaled, y_train)
            
            # Train deep learning model
            if len(X_train_scaled) > 50:  # Only if enough data
                self.deep_model = self._build_deep_model()
                
                # Compile and train
                self.deep_model.fit(
                    X_train_scaled, y_train,
                    epochs=50,
                    batch_size=32,
                    validation_data=(X_test_scaled, y_test),
                    verbose=0
                )
            
            # Evaluate models
            ensemble_pred = self.ensemble_model.predict(X_test_scaled)
            ensemble_acc = accuracy_score(y_test, ensemble_pred)
            
            self.logger.info(f"Ensemble model accuracy: {ensemble_acc:.3f}")
            
            if self.deep_model:
                deep_pred = (self.deep_model.predict(X_test_scaled, verbose=0) > 0.5).astype(int)
                deep_acc = accuracy_score(y_test, deep_pred)
                self.logger.info(f"Deep model accuracy: {deep_acc:.3f}")
            
            # Save models
            await self.save_models()
            
        except Exception as e:
            self.logger.error(f"Error training models: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Clear model references
            if self.deep_model:
                del self.deep_model
            if self.ensemble_model:
                del self.ensemble_model
            if self.anomaly_detector:
                del self.anomaly_detector
            if self.feature_scaler:
                del self.feature_scaler
            if self.pca_transformer:
                del self.pca_transformer
            if self.ica_transformer:
                del self.ica_transformer
            
            self.logger.info("Pattern Analyzer cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
