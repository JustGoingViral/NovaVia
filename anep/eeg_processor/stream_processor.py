"""
ANEP EEG Stream Processor
Real-time EEG data ingestion and preprocessing for neuroplasticity window detection
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import websockets
import json
import struct
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import redis
import kafka
from kafka import KafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from .data_models import EEGReading, EEGDataBatch, ProcessingStatus


@dataclass
class EEGStreamConfig:
    """Configuration for EEG stream processing"""
    sampling_rate: int = 500  # Hz
    channels: int = 32
    buffer_size: int = 10000  # samples
    batch_size: int = 250  # samples per batch (0.5 seconds at 500Hz)
    quality_threshold: float = 0.8  # minimum signal quality
    artifact_rejection: bool = True
    real_time_processing: bool = True


@dataclass
class EEGReading:
    """Single EEG data reading"""
    timestamp: datetime
    patient_id: str
    channels_data: np.ndarray  # shape: (channels,)
    signal_quality: Dict[int, float]  # channel -> quality score
    impedance: Dict[int, float]  # channel -> impedance value
    sampling_rate: int
    sequence_number: int
    device_id: str = "wavi-001"
    
    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class EEGDataBatch:
    """Batch of EEG readings for processing"""
    readings: List[EEGReading]
    patient_id: str
    start_time: datetime
    end_time: datetime
    duration_ms: int
    average_quality: float
    channels_count: int
    sampling_rate: int
    
    @property
    def data_matrix(self) -> np.ndarray:
        """Convert batch to numpy matrix (samples x channels)"""
        return np.array([reading.channels_data for reading in self.readings])


class EEGStreamProcessor:
    """
    Real-time EEG stream processor for ANEP system
    Handles data ingestion, preprocessing, and quality control
    """
    
    def __init__(self, config: EEGStreamConfig = None):
        self.config = config or EEGStreamConfig()
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Data buffers
        self._data_buffer: Dict[str, deque] = {}  # patient_id -> deque of readings
        self._quality_buffer: Dict[str, deque] = {}  # patient_id -> quality scores
        
        # Processing state
        self.is_streaming = False
        self.connected_devices: Dict[str, Dict] = {}
        self.active_patients: set = set()
        
        # Async components
        self._redis_client: Optional[redis.Redis] = None
        self._kafka_producer: Optional[KafkaProducer] = None
        self._websocket_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Threading
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._processing_tasks: List[asyncio.Task] = []
        
        # Callbacks
        self._data_callbacks: List[Callable[[EEGDataBatch], None]] = []
        self._quality_callbacks: List[Callable[[str, float], None]] = []
        self._alert_callbacks: List[Callable[[str, str], None]] = []
    
    async def initialize(self):
        """Initialize the EEG stream processor"""
        try:
            # Initialize Redis connection
            self._redis_client = redis.Redis.from_url(
                self.settings.redis.url,
                password=self.settings.redis.password,
                db=self.settings.redis.db,
                decode_responses=True
            )
            
            # Initialize Kafka producer
            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            self.logger.info("EEG Stream Processor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize EEG Stream Processor: {e}")
            raise
    
    async def connect_wavi_device(self, device_ip: str, device_port: int, 
                                 patient_id: str) -> bool:
        """Connect to WAVi EEG device"""
        try:
            device_id = f"wavi-{device_ip}-{device_port}"
            
            # Establish WebSocket connection to WAVi device
            uri = f"ws://{device_ip}:{device_port}/eeg-stream"
            websocket = await websockets.connect(uri)
            
            self._websocket_connections[device_id] = websocket
            self.connected_devices[device_id] = {
                'ip': device_ip,
                'port': device_port,
                'patient_id': patient_id,
                'connected_at': datetime.now(timezone.utc),
                'status': 'connected'
            }
            
            # Initialize patient buffers
            if patient_id not in self._data_buffer:
                self._data_buffer[patient_id] = deque(maxlen=self.config.buffer_size)
                self._quality_buffer[patient_id] = deque(maxlen=1000)
            
            self.active_patients.add(patient_id)
            
            self.logger.info(f"Connected to WAVi device {device_id} for patient {patient_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to WAVi device {device_ip}:{device_port}: {e}")
            return False
    
    async def start_streaming(self, patient_id: str) -> bool:
        """Start EEG data streaming for a patient"""
        try:
            if patient_id not in self.active_patients:
                raise ValueError(f"No connected device for patient {patient_id}")
            
            # Start streaming tasks
            device_id = None
            for dev_id, dev_info in self.connected_devices.items():
                if dev_info['patient_id'] == patient_id:
                    device_id = dev_id
                    break
            
            if not device_id:
                raise ValueError(f"No device found for patient {patient_id}")
            
            # Create streaming task
            task = asyncio.create_task(
                self._stream_data_task(device_id, patient_id)
            )
            self._processing_tasks.append(task)
            
            # Create processing task
            processing_task = asyncio.create_task(
                self._process_data_task(patient_id)
            )
            self._processing_tasks.append(processing_task)
            
            self.is_streaming = True
            self.logger.info(f"Started EEG streaming for patient {patient_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming for patient {patient_id}: {e}")
            return False
    
    async def _stream_data_task(self, device_id: str, patient_id: str):
        """Background task for streaming EEG data"""
        websocket = self._websocket_connections.get(device_id)
        if not websocket:
            self.logger.error(f"No websocket connection for device {device_id}")
            return
        
        sequence_number = 0
        
        try:
            while self.is_streaming:
                # Receive data from WAVi device
                data = await websocket.recv()
                
                if isinstance(data, bytes):
                    # Binary data format
                    reading = self._parse_binary_eeg_data(
                        data, patient_id, sequence_number, device_id
                    )
                else:
                    # JSON data format
                    data_dict = json.loads(data)
                    reading = self._parse_json_eeg_data(
                        data_dict, patient_id, sequence_number, device_id
                    )
                
                if reading:
                    # Add to buffer
                    self._data_buffer[patient_id].append(reading)
                    
                    # Update quality metrics
                    avg_quality = np.mean(list(reading.signal_quality.values()))
                    self._quality_buffer[patient_id].append(avg_quality)
                    
                    # Store in Redis for real-time access
                    await self._store_reading_redis(reading)
                    
                    # Send to Kafka for downstream processing
                    await self._send_to_kafka(reading)
                    
                    sequence_number += 1
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"WebSocket connection closed for device {device_id}")
        except Exception as e:
            self.logger.error(f"Error in streaming task for device {device_id}: {e}")
        finally:
            # Cleanup
            if device_id in self.connected_devices:
                self.connected_devices[device_id]['status'] = 'disconnected'
    
    def _parse_binary_eeg_data(self, data: bytes, patient_id: str, 
                              sequence_number: int, device_id: str) -> Optional[EEGReading]:
        """Parse binary EEG data from WAVi device"""
        try:
            # WAVi binary format: timestamp(8) + channels(32*4) + quality(32*4) + impedance(32*4)
            expected_size = 8 + (32 * 4) + (32 * 4) + (32 * 4)
            
            if len(data) != expected_size:
                self.logger.warning(f"Unexpected data size: {len(data)}, expected: {expected_size}")
                return None
            
            # Parse timestamp (8 bytes, double)
            timestamp_ms = struct.unpack('<d', data[:8])[0]
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
            
            # Parse channel data (32 channels, 4 bytes each, float)
            channels_data = np.array(struct.unpack('<32f', data[8:136]))
            
            # Parse signal quality (32 values, 4 bytes each, float)
            quality_data = struct.unpack('<32f', data[136:264])
            signal_quality = {i: quality_data[i] for i in range(32)}
            
            # Parse impedance (32 values, 4 bytes each, float)
            impedance_data = struct.unpack('<32f', data[264:392])
            impedance = {i: impedance_data[i] for i in range(32)}
            
            return EEGReading(
                timestamp=timestamp,
                patient_id=patient_id,
                channels_data=channels_data,
                signal_quality=signal_quality,
                impedance=impedance,
                sampling_rate=self.config.sampling_rate,
                sequence_number=sequence_number,
                device_id=device_id
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse binary EEG data: {e}")
            return None
    
    def _parse_json_eeg_data(self, data: Dict, patient_id: str, 
                            sequence_number: int, device_id: str) -> Optional[EEGReading]:
        """Parse JSON EEG data from WAVi device"""
        try:
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            channels_data = np.array(data['channels'])
            signal_quality = {int(k): float(v) for k, v in data.get('quality', {}).items()}
            impedance = {int(k): float(v) for k, v in data.get('impedance', {}).items()}
            
            return EEGReading(
                timestamp=timestamp,
                patient_id=patient_id,
                channels_data=channels_data,
                signal_quality=signal_quality,
                impedance=impedance,
                sampling_rate=data.get('sampling_rate', self.config.sampling_rate),
                sequence_number=sequence_number,
                device_id=device_id
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse JSON EEG data: {e}")
            return None
    
    async def _process_data_task(self, patient_id: str):
        """Background task for processing EEG data batches"""
        while self.is_streaming and patient_id in self.active_patients:
            try:
                # Check if we have enough data for a batch
                buffer = self._data_buffer.get(patient_id)
                if not buffer or len(buffer) < self.config.batch_size:
                    await asyncio.sleep(0.1)  # 100ms
                    continue
                
                # Extract batch
                batch_readings = []
                for _ in range(self.config.batch_size):
                    if buffer:
                        batch_readings.append(buffer.popleft())
                
                if not batch_readings:
                    continue
                
                # Create batch object
                batch = EEGDataBatch(
                    readings=batch_readings,
                    patient_id=patient_id,
                    start_time=batch_readings[0].timestamp,
                    end_time=batch_readings[-1].timestamp,
                    duration_ms=int((batch_readings[-1].timestamp - batch_readings[0].timestamp).total_seconds() * 1000),
                    average_quality=np.mean([np.mean(list(r.signal_quality.values())) for r in batch_readings]),
                    channels_count=len(batch_readings[0].channels_data),
                    sampling_rate=batch_readings[0].sampling_rate
                )
                
                # Quality check
                if batch.average_quality < self.config.quality_threshold:
                    self.logger.warning(f"Low quality EEG batch for patient {patient_id}: {batch.average_quality}")
                    continue
                
                # Process batch
                await self._process_batch(batch)
                
                # Notify callbacks
                for callback in self._data_callbacks:
                    try:
                        callback(batch)
                    except Exception as e:
                        self.logger.error(f"Error in data callback: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in data processing task for patient {patient_id}: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: EEGDataBatch):
        """Process a batch of EEG data"""
        try:
            # Artifact rejection
            if self.config.artifact_rejection:
                cleaned_batch = await self._reject_artifacts(batch)
            else:
                cleaned_batch = batch
            
            # Store processed batch
            await self._store_batch_redis(cleaned_batch)
            
            # Send to Kafka for neuroplasticity analysis
            await self._send_batch_to_kafka(cleaned_batch)
            
        except Exception as e:
            self.logger.error(f"Error processing batch: {e}")
    
    async def _reject_artifacts(self, batch: EEGDataBatch) -> EEGDataBatch:
        """Apply artifact rejection to EEG batch"""
        # Simple artifact rejection based on amplitude thresholds
        cleaned_readings = []
        
        for reading in batch.readings:
            # Check for extreme values (artifacts)
            if np.any(np.abs(reading.channels_data) > 100):  # 100 μV threshold
                continue
            
            # Check for flat signals
            if np.std(reading.channels_data) < 0.1:
                continue
            
            cleaned_readings.append(reading)
        
        # Create new batch with cleaned data
        if cleaned_readings:
            return EEGDataBatch(
                readings=cleaned_readings,
                patient_id=batch.patient_id,
                start_time=cleaned_readings[0].timestamp,
                end_time=cleaned_readings[-1].timestamp,
                duration_ms=batch.duration_ms,
                average_quality=np.mean([np.mean(list(r.signal_quality.values())) for r in cleaned_readings]),
                channels_count=batch.channels_count,
                sampling_rate=batch.sampling_rate
            )
        else:
            return batch  # Return original if all data rejected
    
    async def _store_reading_redis(self, reading: EEGReading):
        """Store individual reading in Redis"""
        try:
            key = f"eeg:realtime:{reading.patient_id}"
            data = {
                'timestamp': reading.timestamp.isoformat(),
                'channels': reading.channels_data.tolist(),
                'quality': reading.signal_quality,
                'sequence': reading.sequence_number
            }
            
            # Store with 60 second expiration
            await self._redis_client.setex(key, 60, json.dumps(data))
            
        except Exception as e:
            self.logger.error(f"Failed to store reading in Redis: {e}")
    
    async def _store_batch_redis(self, batch: EEGDataBatch):
        """Store processed batch in Redis"""
        try:
            key = f"eeg:batch:{batch.patient_id}:{int(batch.start_time.timestamp())}"
            data = {
                'patient_id': batch.patient_id,
                'start_time': batch.start_time.isoformat(),
                'end_time': batch.end_time.isoformat(),
                'duration_ms': batch.duration_ms,
                'average_quality': batch.average_quality,
                'channels_count': batch.channels_count,
                'sampling_rate': batch.sampling_rate,
                'data_shape': batch.data_matrix.shape
            }
            
            # Store with 10 minute expiration
            await self._redis_client.setex(key, 600, json.dumps(data))
            
        except Exception as e:
            self.logger.error(f"Failed to store batch in Redis: {e}")
    
    async def _send_to_kafka(self, reading: EEGReading):
        """Send reading to Kafka"""
        try:
            message = {
                'patient_id': reading.patient_id,
                'timestamp': reading.timestamp.isoformat(),
                'channels_data': reading.channels_data.tolist(),
                'signal_quality': reading.signal_quality,
                'sequence_number': reading.sequence_number,
                'device_id': reading.device_id
            }
            
            self._kafka_producer.send(
                'eeg-realtime',
                key=reading.patient_id,
                value=message
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send reading to Kafka: {e}")
    
    async def _send_batch_to_kafka(self, batch: EEGDataBatch):
        """Send batch to Kafka for analysis"""
        try:
            message = {
                'patient_id': batch.patient_id,
                'start_time': batch.start_time.isoformat(),
                'end_time': batch.end_time.isoformat(),
                'duration_ms': batch.duration_ms,
                'average_quality': batch.average_quality,
                'channels_count': batch.channels_count,
                'sampling_rate': batch.sampling_rate,
                'data_matrix': batch.data_matrix.tolist()
            }
            
            self._kafka_producer.send(
                'eeg-batch-analysis',
                key=batch.patient_id,
                value=message
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send batch to Kafka: {e}")
    
    def add_data_callback(self, callback: Callable[[EEGDataBatch], None]):
        """Add callback for processed EEG data"""
        self._data_callbacks.append(callback)
    
    def add_quality_callback(self, callback: Callable[[str, float], None]):
        """Add callback for quality updates"""
        self._quality_callbacks.append(callback)
    
    async def stop_streaming(self, patient_id: str = None):
        """Stop EEG streaming"""
        try:
            if patient_id:
                self.active_patients.discard(patient_id)
                # Close specific device connections
                for device_id, device_info in self.connected_devices.items():
                    if device_info['patient_id'] == patient_id:
                        if device_id in self._websocket_connections:
                            await self._websocket_connections[device_id].close()
                            del self._websocket_connections[device_id]
            else:
                # Stop all streaming
                self.is_streaming = False
                self.active_patients.clear()
                
                # Close all websocket connections
                for websocket in self._websocket_connections.values():
                    await websocket.close()
                self._websocket_connections.clear()
                
                # Cancel all tasks
                for task in self._processing_tasks:
                    task.cancel()
                self._processing_tasks.clear()
            
            self.logger.info(f"Stopped EEG streaming for patient: {patient_id or 'all'}")
            
        except Exception as e:
            self.logger.error(f"Error stopping streaming: {e}")
    
    async def get_current_quality(self, patient_id: str) -> Optional[float]:
        """Get current signal quality for patient"""
        quality_buffer = self._quality_buffer.get(patient_id)
        if quality_buffer:
            return np.mean(list(quality_buffer)[-10:])  # Average of last 10 readings
        return None
    
    async def get_buffer_status(self, patient_id: str) -> Dict:
        """Get buffer status for patient"""
        data_buffer = self._data_buffer.get(patient_id)
        quality_buffer = self._quality_buffer.get(patient_id)
        
        return {
            'patient_id': patient_id,
            'data_buffer_size': len(data_buffer) if data_buffer else 0,
            'quality_buffer_size': len(quality_buffer) if quality_buffer else 0,
            'is_streaming': patient_id in self.active_patients,
            'current_quality': await self.get_current_quality(patient_id)
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.stop_streaming()
            
            if self._kafka_producer:
                self._kafka_producer.close()
            
            if self._redis_client:
                await self._redis_client.close()
            
            self._executor.shutdown(wait=True)
            
            self.logger.info("EEG Stream Processor cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
