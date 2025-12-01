"""
ANEP: Adaptive Neuroplasticity Enhancement Protocol

Core module for EEG processing, neuroplasticity prediction, and device orchestration.
"""

__version__ = "1.0.0"
__author__ = "NOVA ViA Systems"

from anep.device_orchestrator.device_manager import DeviceOrchestrator, TreatmentProtocol
from anep.eeg_processor.pattern_analyzer import NeuroplasticityPatternAnalyzer
from anep.eeg_processor.neuroplasticity_predictor import NeuroplasticityPredictor
from anep.eeg_processor.stream_processor import EEGStreamProcessor

__all__ = [
    "DeviceOrchestrator",
    "TreatmentProtocol",
    "NeuroplasticityPatternAnalyzer",
    "NeuroplasticityPredictor",
    "EEGStreamProcessor",
]
