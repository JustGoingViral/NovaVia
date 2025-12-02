"""
ANEP: Adaptive Neuroplasticity Enhancement Protocol

Core module for EEG processing, neuroplasticity prediction, and device orchestration.
"""

__version__ = "1.0.0"
__author__ = "NOVA ViA Systems"

# Import classes only when explicitly requested to avoid dependency issues
# Users should import directly from submodules:
# from anep.device_orchestrator.device_manager import DeviceOrchestrator
# from anep.eeg_processor.pattern_analyzer import NeuroplasticityPatternAnalyzer

__all__ = [
    "device_orchestrator",
    "eeg_processor",
]
