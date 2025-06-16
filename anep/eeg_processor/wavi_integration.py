"""
ANEP WAVi EEG Integration
Hardware integration for WAVi EEG devices with real-time data streaming
"""

import asyncio
import logging
import json
import struct
import websockets
import aiohttp
import numpy as np
from typing import Dict, List, Optional, Callable, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import socket
import ssl
from pathlib import Path

from config.settings import get_settings
from .stream_processor import EEGReading, EEGStreamConfig


@dataclass
class WAViDeviceInfo:
    """WAVi device information"""
    device_id: str
    ip_address: str
    port: int
    firmware_version: str
    serial_number: str
    channels: int
    sampling_rate: int
    status: str  # 'disconnected', 'connecting', 'connected', 'streaming', 'error'
    last_seen: datetime
    patient_id: Optional[str] = None
    signal_quality: Dict[int, float] = field(default_factory=dict)
    impedance_values: Dict[int, float] = field(default_factory=dict)
    
    @property
    def is_online(self) -> bool:
        """Check if device is online (seen within last 30 seconds)"""
        return (datetime.now(timezone.utc) - self.last_seen).seconds < 30
    
    @property
    def average_signal_quality(self) -> float:
        """Calculate average signal quality across all channels"""
        if self.signal_quality:
            return np.mean(list(self.signal_quality.values()))
        return 0.0


@dataclass
class WAViCalibrationData:
    """WAVi device calibration parameters"""
    device_id: str
    channel_gains: Dict[int, float]
    channel_offsets: Dict[int, float]
    frequency_response: Dict[str, float]  # Band -> correction factor
    noise_floor: Dict[int, float]
    calibration_date: datetime
    is_valid: bool = True
    
    def apply_calibration(self, raw_data: np.ndarray, channel: int) -> np.ndarray:
        """Apply calibration to raw EEG data"""
        try:
            gain = self.channel_gains.get(channel, 1.0)
            offset = self.channel_offsets.get(channel, 0.0)
            return (raw_data - offset) * gain
        except:
            return raw_data


class WAViProtocol:
    """WAVi communication protocol handler"""
    
    # Protocol constants
    PACKET_HEADER = b'\xAA\xBB'
    PACKET_FOOTER = b'\xCC\xDD'
    
    # Command types
    CMD_GET_INFO = 0x01
    CMD_START_STREAM = 0x02
    CMD_STOP_STREAM = 0x03
    CMD_SET_CONFIG = 0x04
    CMD_GET_STATUS = 0x05
    CMD_CALIBRATE = 0x06
    CMD_GET_IMPEDANCE = 0x07
    
    # Response types
    RESP_INFO = 0x81
    RESP_CONFIG_ACK = 0x82
    RESP_STATUS = 0x83
    RESP_DATA = 0x84
    RESP_IMPEDANCE = 0x85
    RESP_ERROR = 0x8F
    
    @staticmethod
    def create_command_packet(command: int, data: bytes = b'') -> bytes:
        """Create a command packet"""
        packet = WAViProtocol.PACKET_HEADER
        packet += struct.pack('<H', len(data) + 1)  # Length
        packet += struct.pack('<B', command)  # Command
        packet += data  # Data
        
        # Calculate checksum
        checksum = sum(packet[2:]) & 0xFF
        packet += struct.pack('<B', checksum)
        packet += WAViProtocol.PACKET_FOOTER
        
        return packet
    
    @staticmethod
    def parse_response_packet(data: bytes) -> Optional[Tuple[int, bytes]]:
        """Parse a response packet"""
        try:
            if len(data) < 8:  # Minimum packet size
                return None
            
            # Check header
            if data[:2] != WAViProtocol.PACKET_HEADER:
                return None
            
            # Check footer
            if data[-2:] != WAViProtocol.PACKET_FOOTER:
                return None
            
            # Extract length and command
            length = struct.unpack('<H', data[2:4])[0]
            command = struct.unpack('<B', data[4:5])[0]
            
            # Extract payload
            payload = data[5:5+length-1]
            
            # Verify checksum
            expected_checksum = data[-3]
            actual_checksum = sum(data[2:-3]) & 0xFF
            
            if expected_checksum != actual_checksum:
                return None
            
            return command, payload
            
        except Exception:
            return None


class WAViEEGIntegration:
    """
    WAVi EEG device integration for ANEP system
    Handles device discovery, connection management, and real-time data streaming
    """
    
    def __init__(self, config: Optional[EEGStreamConfig] = None):
        self.settings = get_settings()
        self.config = config or EEGStreamConfig()
        self.logger = logging.getLogger(__name__)
        
        # Device management
        self.discovered_devices: Dict[str, WAViDeviceInfo] = {}
        self.connected_devices: Dict[str, WAViDeviceInfo] = {}
        self.calibration_data: Dict[str, WAViCalibrationData] = {}
        
        # Connection management
        self._websocket_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._tcp_connections: Dict[str, Tuple[socket.socket, threading.Thread]] = {}
        self._data_callbacks: List[Callable[[EEGReading], None]] = []
        self._status_callbacks: List[Callable[[str, str], None]] = []  # device_id, status
        
        # Discovery and monitoring
        self._discovery_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._discovery_active = False
        
        # Threading
        self._executor = ThreadPoolExecutor(max_workers=8)
        
        # Protocol handler
        self.protocol = WAViProtocol()
        
        # Device configuration
        self.default_config = {
            'sampling_rate': self.config.sampling_rate,
            'channels': self.config.channels,
            'gain': 1000,  # μV/bit
            'filter_low': 0.5,  # Hz
            'filter_high': 100.0,  # Hz
            'notch_filter': 60.0  # Hz
        }
    
    async def initialize(self):
        """Initialize WAVi integration"""
        try:
            # Load calibration data
            await self._load_calibration_data()
            
            # Start device discovery
            await self.start_discovery()
            
            # Start monitoring
            await self.start_monitoring()
            
            self.logger.info("WAVi EEG Integration initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WAVi integration: {e}")
            raise
    
    async def start_discovery(self):
        """Start device discovery process"""
        try:
            if self._discovery_active:
                return
            
            self._discovery_active = True
            self._discovery_task = asyncio.create_task(self._discovery_loop())
            
            self.logger.info("Started WAVi device discovery")
            
        except Exception as e:
            self.logger.error(f"Error starting discovery: {e}")
    
    async def stop_discovery(self):
        """Stop device discovery process"""
        try:
            self._discovery_active = False
            
            if self._discovery_task:
                self._discovery_task.cancel()
                try:
                    await self._discovery_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("Stopped WAVi device discovery")
            
        except Exception as e:
            self.logger.error(f"Error stopping discovery: {e}")
    
    async def _discovery_loop(self):
        """Main device discovery loop"""
        while self._discovery_active:
            try:
                # Network discovery
                await self._discover_network_devices()
                
                # USB discovery (if applicable)
                await self._discover_usb_devices()
                
                # Clean up old devices
                await self._cleanup_old_devices()
                
                # Wait before next discovery cycle
                await asyncio.sleep(30)  # Discover every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in discovery loop: {e}")
                await asyncio.sleep(10)
    
    async def _discover_network_devices(self):
        """Discover WAVi devices on the network"""
        try:
            # Scan common IP ranges for WAVi devices
            network_ranges = [
                "192.168.1.0/24",
                "192.168.0.0/24",
                "10.0.0.0/24"
            ]
            
            discovery_tasks = []
            
            for network_range in network_ranges:
                # Parse network range and create scan tasks
                base_ip = network_range.split('/')[0].rsplit('.', 1)[0]
                
                for i in range(1, 255):
                    ip = f"{base_ip}.{i}"
                    task = asyncio.create_task(self._probe_device(ip))
                    discovery_tasks.append(task)
            
            # Wait for all probes to complete (with timeout)
            await asyncio.wait_for(
                asyncio.gather(*discovery_tasks, return_exceptions=True),
                timeout=10.0
            )
            
        except asyncio.TimeoutError:
            self.logger.warning("Network discovery timeout")
        except Exception as e:
            self.logger.error(f"Error in network discovery: {e}")
    
    async def _probe_device(self, ip: str):
        """Probe a specific IP for WAVi device"""
        try:
            # Try common WAVi ports
            ports = [8080, 8081, 9999, 10000]
            
            for port in ports:
                try:
                    # Try WebSocket connection first
                    uri = f"ws://{ip}:{port}/wavi"
                    async with websockets.connect(
                        uri, 
                        timeout=2.0,
                        close_timeout=1.0
                    ) as websocket:
                        
                        # Send device info request
                        info_request = {
                            'command': 'get_info',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        
                        await websocket.send(json.dumps(info_request))
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        device_info = json.loads(response)
                        
                        # Validate response
                        if self._validate_device_info(device_info):
                            await self._register_discovered_device(ip, port, device_info)
                            return
                            
                except (websockets.exceptions.WebSocketException, 
                       asyncio.TimeoutError, 
                       ConnectionRefusedError):
                    continue
                
                # Try TCP connection as fallback
                try:
                    await self._probe_tcp_device(ip, port)
                except:
                    continue
                    
        except Exception as e:
            # Silent fail for individual probe attempts
            pass
    
    async def _probe_tcp_device(self, ip: str, port: int):
        """Probe device using TCP protocol"""
        try:
            # Create TCP connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=2.0
            )
            
            try:
                # Send device info command
                cmd_packet = self.protocol.create_command_packet(
                    self.protocol.CMD_GET_INFO
                )
                
                writer.write(cmd_packet)
                await writer.drain()
                
                # Read response
                response_data = await asyncio.wait_for(
                    reader.read(1024),
                    timeout=2.0
                )
                
                # Parse response
                parsed = self.protocol.parse_response_packet(response_data)
                if parsed and parsed[0] == self.protocol.RESP_INFO:
                    device_info = self._parse_device_info_binary(parsed[1])
                    if device_info:
                        await self._register_discovered_device(ip, port, device_info)
                
            finally:
                writer.close()
                await writer.wait_closed()
                
        except Exception as e:
            pass  # Silent fail
    
    def _validate_device_info(self, device_info: Dict) -> bool:
        """Validate device info response"""
        try:
            required_fields = ['device_id', 'firmware_version', 'channels', 'sampling_rate']
            return all(field in device_info for field in required_fields)
        except:
            return False
    
    def _parse_device_info_binary(self, data: bytes) -> Optional[Dict]:
        """Parse binary device info response"""
        try:
            if len(data) < 32:  # Minimum expected size
                return None
            
            # Parse binary device info structure
            device_id = data[:16].decode('utf-8').strip('\x00')
            firmware_version = data[16:24].decode('utf-8').strip('\x00')
            channels = struct.unpack('<H', data[24:26])[0]
            sampling_rate = struct.unpack('<H', data[26:28])[0]
            serial_number = data[28:44].decode('utf-8').strip('\x00')
            
            return {
                'device_id': device_id,
                'firmware_version': firmware_version,
                'channels': channels,
                'sampling_rate': sampling_rate,
                'serial_number': serial_number
            }
            
        except Exception:
            return None
    
    async def _register_discovered_device(self, ip: str, port: int, device_info: Dict):
        """Register a discovered WAVi device"""
        try:
            device_id = device_info['device_id']
            
            # Create device info object
            wavi_device = WAViDeviceInfo(
                device_id=device_id,
                ip_address=ip,
                port=port,
                firmware_version=device_info['firmware_version'],
                serial_number=device_info.get('serial_number', ''),
                channels=device_info['channels'],
                sampling_rate=device_info['sampling_rate'],
                status='discovered',
                last_seen=datetime.now(timezone.utc)
            )
            
            # Add to discovered devices
            self.discovered_devices[device_id] = wavi_device
            
            self.logger.info(f"Discovered WAVi device {device_id} at {ip}:{port}")
            
            # Notify status callbacks
            await self._notify_status_callbacks(device_id, 'discovered')
            
        except Exception as e:
            self.logger.error(f"Error registering discovered device: {e}")
    
    async def _discover_usb_devices(self):
        """Discover WAVi devices connected via USB"""
        try:
            # This would interface with USB/serial discovery
            # Implementation depends on specific WAVi USB protocol
            pass
        except Exception as e:
            self.logger.error(f"Error in USB discovery: {e}")
    
    async def _cleanup_old_devices(self):
        """Remove devices that haven't been seen recently"""
        try:
            current_time = datetime.now(timezone.utc)
            timeout_threshold = timedelta(minutes=5)
            
            # Clean discovered devices
            devices_to_remove = []
            for device_id, device in self.discovered_devices.items():
                if current_time - device.last_seen > timeout_threshold:
                    devices_to_remove.append(device_id)
            
            for device_id in devices_to_remove:
                del self.discovered_devices[device_id]
                self.logger.info(f"Removed stale device {device_id} from discovery")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old devices: {e}")
    
    async def connect_device(self, device_id: str, patient_id: Optional[str] = None) -> bool:
        """Connect to a specific WAVi device"""
        try:
            if device_id in self.connected_devices:
                self.logger.warning(f"Device {device_id} already connected")
                return True
            
            if device_id not in self.discovered_devices:
                self.logger.error(f"Device {device_id} not found in discovered devices")
                return False
            
            device = self.discovered_devices[device_id]
            device.status = 'connecting'
            
            # Try WebSocket connection first
            success = await self._connect_websocket(device)
            
            if not success:
                # Fallback to TCP connection
                success = await self._connect_tcp(device)
            
            if success:
                device.status = 'connected'
                device.patient_id = patient_id
                self.connected_devices[device_id] = device
                
                # Apply device configuration
                await self._configure_device(device)
                
                # Start impedance monitoring
                asyncio.create_task(self._monitor_device_impedance(device_id))
                
                self.logger.info(f"Successfully connected to WAVi device {device_id}")
                await self._notify_status_callbacks(device_id, 'connected')
                
                return True
            else:
                device.status = 'error'
                await self._notify_status_callbacks(device_id, 'error')
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to device {device_id}: {e}")
            return False
    
    async def _connect_websocket(self, device: WAViDeviceInfo) -> bool:
        """Connect to device via WebSocket"""
        try:
            uri = f"ws://{device.ip_address}:{device.port}/wavi"
            
            websocket = await websockets.connect(
                uri,
                timeout=5.0,
                max_size=1000000,  # 1MB max message size
                ping_interval=30,
                ping_timeout=10
            )
            
            self._websocket_connections[device.device_id] = websocket
            
            # Start data receiving task
            asyncio.create_task(self._websocket_data_handler(device.device_id))
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket connection failed for {device.device_id}: {e}")
            return False
    
    async def _connect_tcp(self, device: WAViDeviceInfo) -> bool:
        """Connect to device via TCP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((device.ip_address, device.port))
            
            # Start TCP handler thread
            handler_thread = threading.Thread(
                target=self._tcp_data_handler,
                args=(device.device_id, sock),
                daemon=True
            )
            handler_thread.start()
            
            self._tcp_connections[device.device_id] = (sock, handler_thread)
            
            return True
            
        except Exception as e:
            self.logger.error(f"TCP connection failed for {device.device_id}: {e}")
            return False
    
    async def _configure_device(self, device: WAViDeviceInfo):
        """Configure WAVi device settings"""
        try:
            config_data = {
                'sampling_rate': self.default_config['sampling_rate'],
                'channels': list(range(device.channels)),
                'gain': self.default_config['gain'],
                'filters': {
                    'low_pass': self.default_config['filter_high'],
                    'high_pass': self.default_config['filter_low'],
                    'notch': self.default_config['notch_filter']
                }
            }
            
            if device.device_id in self._websocket_connections:
                await self._send_websocket_command(device.device_id, 'configure', config_data)
            elif device.device_id in self._tcp_connections:
                await self._send_tcp_command(device.device_id, 'configure', config_data)
            
            self.logger.info(f"Configured device {device.device_id}")
            
        except Exception as e:
            self.logger.error(f"Error configuring device {device.device_id}: {e}")
    
    async def start_streaming(self, device_id: str) -> bool:
        """Start EEG data streaming from device"""
        try:
            if device_id not in self.connected_devices:
                self.logger.error(f"Device {device_id} not connected")
                return False
            
            device = self.connected_devices[device_id]
            
            if device.device_id in self._websocket_connections:
                await self._send_websocket_command(device_id, 'start_stream')
            elif device.device_id in self._tcp_connections:
                await self._send_tcp_command(device_id, 'start_stream')
            
            device.status = 'streaming'
            await self._notify_status_callbacks(device_id, 'streaming')
            
            self.logger.info(f"Started streaming from device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting stream for device {device_id}: {e}")
            return False
    
    async def stop_streaming(self, device_id: str) -> bool:
        """Stop EEG data streaming from device"""
        try:
            if device_id not in self.connected_devices:
                return True  # Already stopped
            
            device = self.connected_devices[device_id]
            
            if device.device_id in self._websocket_connections:
                await self._send_websocket_command(device_id, 'stop_stream')
            elif device.device_id in self._tcp_connections:
                await self._send_tcp_command(device_id, 'stop_stream')
            
            device.status = 'connected'
            await self._notify_status_callbacks(device_id, 'connected')
            
            self.logger.info(f"Stopped streaming from device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping stream for device {device_id}: {e}")
            return False
    
    async def _send_websocket_command(self, device_id: str, command: str, data: Dict = None):
        """Send command via WebSocket"""
        try:
            websocket = self._websocket_connections.get(device_id)
            if not websocket:
                raise ValueError(f"No WebSocket connection for device {device_id}")
            
            message = {
                'command': command,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': data or {}
            }
            
            await websocket.send(json.dumps(message))
            
        except Exception as e:
            self.logger.error(f"Error sending WebSocket command to {device_id}: {e}")
    
    async def _send_tcp_command(self, device_id: str, command: str, data: Dict = None):
        """Send command via TCP"""
        try:
            sock, _ = self._tcp_connections.get(device_id, (None, None))
            if not sock:
                raise ValueError(f"No TCP connection for device {device_id}")
            
            # Map command to protocol command
            cmd_map = {
                'configure': self.protocol.CMD_SET_CONFIG,
                'start_stream': self.protocol.CMD_START_STREAM,
                'stop_stream': self.protocol.CMD_STOP_STREAM,
                'get_status': self.protocol.CMD_GET_STATUS
            }
            
            cmd_code = cmd_map.get(command)
            if cmd_code is None:
                raise ValueError(f"Unknown command: {command}")
            
            # Serialize data if provided
            cmd_data = b''
            if data:
                cmd_data = json.dumps(data).encode('utf-8')
            
            packet = self.protocol.create_command_packet(cmd_code, cmd_data)
            
            await asyncio.get_event_loop().run_in_executor(
                self._executor, sock.send, packet
            )
            
        except Exception as e:
            self.logger.error(f"Error sending TCP command to {device_id}: {e}")
    
    async def _websocket_data_handler(self, device_id: str):
        """Handle incoming WebSocket data"""
        try:
            websocket = self._websocket_connections[device_id]
            device = self.connected_devices[device_id]
            
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        # JSON data
                        data = json.loads(message)
                        await self._process_json_data(device, data)
                    elif isinstance(message, bytes):
                        # Binary data
                        await self._process_binary_data(device, message)
                        
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket data from {device_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"WebSocket connection closed for device {device_id}")
            await self._handle_device_disconnection(device_id)
        except Exception as e:
            self.logger.error(f"Error in WebSocket data handler for {device_id}: {e}")
            await self._handle_device_disconnection(device_id)
    
    def _tcp_data_handler(self, device_id: str, sock: socket.socket):
        """Handle incoming TCP data (runs in separate thread)"""
        try:
            device = self.connected_devices[device_id]
            buffer = b''
            
            while True:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete packets
                    while len(buffer) >= 8:  # Minimum packet size
                        packet_start = buffer.find(self.protocol.PACKET_HEADER)
                        if packet_start == -1:
                            buffer = b''
                            break
                        
                        if packet_start > 0:
                            buffer = buffer[packet_start:]
                        
                        if len(buffer) < 4:
                            break
                        
                        # Get packet length
                        packet_length = struct.unpack('<H', buffer[2:4])[0] + 6  # +6 for header/footer/checksum
                        
                        if len(buffer) < packet_length:
                            break  # Wait for more data
                        
                        # Extract and process packet
                        packet = buffer[:packet_length]
                        buffer = buffer[packet_length:]
                        
                        # Process packet in event loop
                        asyncio.run_coroutine_threadsafe(
                            self._process_tcp_packet(device, packet),
                            asyncio.get_event_loop()
                        )
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error in TCP data handler for {device_id}: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"TCP data handler error for {device_id}: {e}")
        finally:
            # Clean up connection
            asyncio.run_coroutine_threadsafe(
                self._handle_device_disconnection(device_id),
                asyncio.get_event_loop()
            )
    
    async def _process_json_data(self, device: WAViDeviceInfo, data: Dict):
        """Process JSON format EEG data"""
        try:
            if data.get('type') == 'eeg_data':
                # Extract EEG reading
                timestamp = datetime.fromisoformat(data['timestamp'])
                channels_data = np.array(data['channels'])
                signal_quality = data.get('signal_quality', {})
                impedance = data.get('impedance', {})
                sequence_number = data.get('sequence', 0)
                
                # Apply calibration if available
                if device.device_id in self.calibration_data:
                    calibration = self.calibration_data[device.device_id]
                    for i in range(len(channels_data)):
                        channels_data[i] = calibration.apply_calibration(
                            np.array([channels_data[i]]), i
                        )[0]
                
                # Create EEG reading
                reading = EEGReading(
                    timestamp=timestamp,
                    patient_id=device.patient_id or 'unknown',
                    channels_data=channels_data,
                    signal_quality=signal_quality,
                    impedance=impedance,
                    sampling_rate=device.sampling_rate,
                    sequence_number=sequence_number,
                    device_id=device.device_id
                )
                
                # Update device status
                device.last_seen = datetime.now(timezone.utc)
                device.signal_quality = signal_quality
                device.impedance_values = impedance
                
                # Notify callbacks
                await self._notify_data_callbacks(reading)
                
        except Exception as e:
            self.logger.error(f"Error processing JSON data: {e}")
    
    async def _process_binary_data(self, device: WAViDeviceInfo, data: bytes):
        """Process binary format EEG data"""
        try:
            # WAVi binary format: timestamp(8) + sequence(4) + channels(N*4) + quality(N*4) + impedance(N*4)
            channels = device.channels
            expected_size = 8 + 4 + (channels * 4) + (channels * 4) + (channels * 4)
            
            if len(data) != expected_size:
                self.logger.warning(f"Unexpected binary data size: {len(data)}, expected: {expected_size}")
                return
            
            # Parse timestamp (8 bytes, double)
            timestamp_ms = struct.unpack('<d', data[:8])[0]
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
            
            # Parse sequence number (4 bytes, uint32)
            sequence_number = struct.unpack('<I', data[8:12])[0]
            
            # Parse channel data (N channels, 4 bytes each, float)
            offset = 12
            channels_data = struct.unpack(f'<{channels}f', data[offset:offset + channels * 4])
            channels_data = np.array(channels_data)
            offset += channels * 4
            
            # Parse signal quality (N values, 4 bytes each, float)
            quality_data = struct.unpack(f'<{channels}f', data[offset:offset + channels * 4])
            signal_quality = {i: quality_data[i] for i in range(channels)}
            offset += channels * 4
            
            # Parse impedance (N values, 4 bytes each, float)
            impedance_data = struct.unpack(f'<{channels}f', data[offset:offset + channels * 4])
            impedance = {i: impedance_data[i] for i in range(channels)}
            
            # Apply calibration if available
            if device.device_id in self.calibration_data:
                calibration = self.calibration_data[device.device_id]
                for i in range(len(channels_data)):
                    channels_data[i] = calibration.apply_calibration(
                        np.array([channels_data[i]]), i
                    )[0]
            
            # Create EEG reading
            reading = EEGReading(
                timestamp=timestamp,
                patient_id=device.patient_id or 'unknown',
                channels_data=channels_data,
                signal_quality=signal_quality,
                impedance=impedance,
                sampling_rate=device.sampling_rate,
                sequence_number=sequence_number,
                device_id=device.device_id
            )
            
            # Update device status
            device.last_seen = datetime.now(timezone.utc)
            device.signal_quality = signal_quality
            device.impedance_values = impedance
            
            # Notify callbacks
            await self._notify_data_callbacks(reading)
            
        except Exception as e:
            self.logger.error(f"Error processing binary EEG data: {e}")
    
    async def _process_tcp_packet(self, device: WAViDeviceInfo, packet: bytes):
        """Process TCP packet data"""
        try:
            parsed = self.protocol.parse_response_packet(packet)
            if not parsed:
                return
            
            command, payload = parsed
            
            if command == self.protocol.RESP_DATA:
                # EEG data packet
                await self._process_binary_data(device, payload)
            elif command == self.protocol.RESP_STATUS:
                # Device status update
                await self._process_status_update(device, payload)
            elif command == self.protocol.RESP_IMPEDANCE:
                # Impedance data
                await self._process_impedance_data(device, payload)
            
        except Exception as e:
            self.logger.error(f"Error processing TCP packet: {e}")
    
    async def _process_status_update(self, device: WAViDeviceInfo, data: bytes):
        """Process device status update"""
        try:
            if len(data) >= 4:
                status_code = struct.unpack('<I', data[:4])[0]
                status_map = {
                    0: 'idle',
                    1: 'streaming',
                    2: 'calibrating',
                    3: 'error'
                }
                
                new_status = status_map.get(status_code, 'unknown')
                if device.status != new_status:
                    device.status = new_status
                    await self._notify_status_callbacks(device.device_id, new_status)
                    
        except Exception as e:
            self.logger.error(f"Error processing status update: {e}")
    
    async def _process_impedance_data(self, device: WAViDeviceInfo, data: bytes):
        """Process impedance measurement data"""
        try:
            channels = device.channels
            expected_size = channels * 4  # 4 bytes per channel
            
            if len(data) >= expected_size:
                impedance_values = struct.unpack(f'<{channels}f', data[:expected_size])
                device.impedance_values = {i: impedance_values[i] for i in range(channels)}
                
        except Exception as e:
            self.logger.error(f"Error processing impedance data: {e}")
    
    async def _notify_data_callbacks(self, reading: EEGReading):
        """Notify all data callbacks"""
        for callback in self._data_callbacks:
            try:
                callback(reading)
            except Exception as e:
                self.logger.error(f"Error in data callback: {e}")
    
    async def _notify_status_callbacks(self, device_id: str, status: str):
        """Notify all status callbacks"""
        for callback in self._status_callbacks:
            try:
                callback(device_id, status)
            except Exception as e:
                self.logger.error(f"Error in status callback: {e}")
    
    async def _handle_device_disconnection(self, device_id: str):
        """Handle device disconnection"""
        try:
            # Clean up connections
            if device_id in self._websocket_connections:
                try:
                    await self._websocket_connections[device_id].close()
                except:
                    pass
                del self._websocket_connections[device_id]
            
            if device_id in self._tcp_connections:
                sock, thread = self._tcp_connections[device_id]
                try:
                    sock.close()
                except:
                    pass
                del self._tcp_connections[device_id]
            
            # Update device status
            if device_id in self.connected_devices:
                self.connected_devices[device_id].status = 'disconnected'
                await self._notify_status_callbacks(device_id, 'disconnected')
                del self.connected_devices[device_id]
            
            self.logger.info(f"Device {device_id} disconnected")
            
        except Exception as e:
            self.logger.error(f"Error handling device disconnection: {e}")
    
    async def start_monitoring(self):
        """Start device monitoring"""
        try:
            if self._monitoring_task:
                return
            
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Started device monitoring")
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Monitor connected devices
                for device_id in list(self.connected_devices.keys()):
                    await self._monitor_device_health(device_id)
                
                # Wait before next monitoring cycle
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_device_health(self, device_id: str):
        """Monitor individual device health"""
        try:
            device = self.connected_devices.get(device_id)
            if not device:
                return
            
            # Check if device is still responding
            current_time = datetime.now(timezone.utc)
            time_since_last_seen = (current_time - device.last_seen).total_seconds()
            
            if time_since_last_seen > 60:  # 60 seconds timeout
                self.logger.warning(f"Device {device_id} not responding, attempting reconnection")
                await self._handle_device_disconnection(device_id)
                # Try to reconnect
                await self.connect_device(device_id, device.patient_id)
            
            # Check signal quality
            if device.signal_quality:
                avg_quality = np.mean(list(device.signal_quality.values()))
                if avg_quality < 0.5:  # Poor signal quality
                    self.logger.warning(f"Poor signal quality on device {device_id}: {avg_quality:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error monitoring device {device_id}: {e}")
    
    async def _monitor_device_impedance(self, device_id: str):
        """Monitor device impedance periodically"""
        try:
            while device_id in self.connected_devices:
                # Request impedance measurement
                if device_id in self._websocket_connections:
                    await self._send_websocket_command(device_id, 'get_impedance')
                elif device_id in self._tcp_connections:
                    await self._send_tcp_command(device_id, 'get_impedance')
                
                # Wait 30 seconds before next measurement
                await asyncio.sleep(30)
                
        except Exception as e:
            self.logger.error(f"Error monitoring impedance for {device_id}: {e}")
    
    async def _load_calibration_data(self):
        """Load device calibration data"""
        try:
            calibration_dir = Path("./calibration")
            if not calibration_dir.exists():
                return
            
            for calibration_file in calibration_dir.glob("*.json"):
                try:
                    with open(calibration_file, 'r') as f:
                        cal_data = json.load(f)
                    
                    device_id = cal_data['device_id']
                    calibration = WAViCalibrationData(
                        device_id=device_id,
                        channel_gains=cal_data.get('channel_gains', {}),
                        channel_offsets=cal_data.get('channel_offsets', {}),
                        frequency_response=cal_data.get('frequency_response', {}),
                        noise_floor=cal_data.get('noise_floor', {}),
                        calibration_date=datetime.fromisoformat(cal_data['calibration_date'])
                    )
                    
                    self.calibration_data[device_id] = calibration
                    self.logger.info(f"Loaded calibration data for device {device_id}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading calibration file {calibration_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error loading calibration data: {e}")
    
    def add_data_callback(self, callback: Callable[[EEGReading], None]):
        """Add callback for EEG data"""
        self._data_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[str, str], None]):
        """Add callback for device status changes"""
        self._status_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable[[EEGReading], None]):
        """Remove data callback"""
        if callback in self._data_callbacks:
            self._data_callbacks.remove(callback)
    
    def remove_status_callback(self, callback: Callable[[str, str], None]):
        """Remove status callback"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a specific device"""
        try:
            if device_id not in self.connected_devices:
                return True  # Already disconnected
            
            # Stop streaming first
            await self.stop_streaming(device_id)
            
            # Handle disconnection
            await self._handle_device_disconnection(device_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting device {device_id}: {e}")
            return False
    
    async def get_device_info(self, device_id: str) -> Optional[WAViDeviceInfo]:
        """Get information about a specific device"""
        return self.connected_devices.get(device_id) or self.discovered_devices.get(device_id)
    
    async def get_all_devices(self) -> Dict[str, WAViDeviceInfo]:
        """Get information about all devices"""
        all_devices = {}
        all_devices.update(self.discovered_devices)
        all_devices.update(self.connected_devices)
        return all_devices
    
    async def get_connected_devices(self) -> Dict[str, WAViDeviceInfo]:
        """Get all connected devices"""
        return self.connected_devices.copy()
    
    async def calibrate_device(self, device_id: str) -> bool:
        """Initiate device calibration"""
        try:
            if device_id not in self.connected_devices:
                self.logger.error(f"Device {device_id} not connected")
                return False
            
            device = self.connected_devices[device_id]
            
            if device_id in self._websocket_connections:
                await self._send_websocket_command(device_id, 'calibrate')
            elif device_id in self._tcp_connections:
                await self._send_tcp_command(device_id, 'calibrate')
            
            device.status = 'calibrating'
            await self._notify_status_callbacks(device_id, 'calibrating')
            
            self.logger.info(f"Started calibration for device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error calibrating device {device_id}: {e}")
            return False
    
    async def check_device_impedance(self, device_id: str) -> Optional[Dict[int, float]]:
        """Check current impedance values for a device"""
        device = self.connected_devices.get(device_id)
        if device:
            return device.impedance_values.copy()
        return None
    
    async def get_signal_quality(self, device_id: str) -> Optional[Dict[int, float]]:
        """Get current signal quality for a device"""
        device = self.connected_devices.get(device_id)
        if device:
            return device.signal_quality.copy()
        return None
    
    async def cleanup(self):
        """Cleanup WAVi integration"""
        try:
            # Stop discovery
            await self.stop_discovery()
            
            # Disconnect all devices
            for device_id in list(self.connected_devices.keys()):
                await self.disconnect_device(device_id)
            
            # Stop monitoring
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown executor
            self._executor.shutdown(wait=True)
            
            self.logger.info("WAVi EEG Integration cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during WAVi integration cleanup: {e}")
