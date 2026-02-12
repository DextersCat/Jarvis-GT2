"""
WebSocket Dashboard Bridge for Jarvis GT2
Connects to the Cyber-Grid Dashboard and pushes real-time telemetry.
"""
import json
import threading
import time
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, Callable, List
import psutil

try:
    from websocket import WebSocketApp
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️  websocket-client not installed. Run: pip install websocket-client")

logger = logging.getLogger(__name__)


class DashboardBridge:
    """Manages WebSocket connection to Cyber-Grid Dashboard."""
    
    def __init__(self, dashboard_url: str = "ws://localhost:5000/ws"):
        if not WEBSOCKET_AVAILABLE:
            logger.warning("Dashboard bridge disabled - websocket-client not installed")
            self.enabled = False
            return
            
        self.dashboard_url = dashboard_url
        self.ws: Optional[WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.metrics_thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        self.enabled = True
        
        # Health tracking callback
        self.on_health_update: Optional[Callable[[str, int], None]] = None
        
        # State change callback (for UI control toggles)
        self.on_state_change: Optional[Callable[[str, Any], None]] = None
        
        # One-shot metric tracking
        self.is_transcribing = False
        self.stt_backend = "none"
        self.stt_device = "none"
        self.last_stt_latency_ms = 0
        self.last_stt_display_time = 0.0
        self.last_stt_display_value = 0
        self.last_ollama_response_time = 0
        self.last_ollama_display_time = 0.0
        self.last_ollama_display_value = 0

        # State tracking
        self.current_state = {
            "mode": "idle",
            "gamingMode": False,
            "muteMic": False,
            "conversationalMode": False
        }
        
        logger.info(f"Dashboard bridge initialized: {dashboard_url}")
    
    def start(self):
        """Start WebSocket connection and metrics loop."""
        if not self.enabled:
            return
            
        self.running = True
        
        # Start WebSocket connection thread
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self.metrics_thread.start()
        
        logger.info("✓ Dashboard bridge started")
    
    def stop(self):
        """Stop WebSocket connection and metrics loop."""
        if not self.enabled:
            return
            
        self.running = False
        if self.ws:
            self.ws.close()
        logger.info("Dashboard bridge stopped")
    
    def _run_websocket(self):
        """WebSocket connection loop with auto-reconnect."""
        while self.running:
            try:
                self.ws = WebSocketApp(
                    self.dashboard_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            if self.running:
                time.sleep(3)  # Wait before reconnecting
    
    def _on_open(self, ws):
        """WebSocket connection opened."""
        self.connected = True
        logger.info("✓ Connected to dashboard")
    
    def _on_message(self, ws, message):
        """Handle incoming messages from dashboard."""
        try:
            data = json.loads(message)
            
            # Handle toggle commands from UI (direct, if ever forwarded)
            if data.get("command") == "toggle":
                key = data.get("key")
                value = data.get("value")
                if key in self.current_state:
                    self.current_state[key] = value
                    logger.debug(f"Dashboard toggle: {key}={value}")
                    if self.on_state_change:
                        self.on_state_change(key, value)

            # Handle state broadcasts from server (e.g. after a UI toggle)
            elif data.get("type") == "state":
                incoming = data.get("data", {})
                for key in ("gamingMode", "muteMic", "conversationalMode"):
                    if key in incoming and incoming[key] != self.current_state.get(key):
                        self.current_state[key] = incoming[key]
                        logger.debug(f"State sync from server: {key}={incoming[key]}")
                        if self.on_state_change:
                            self.on_state_change(key, incoming[key])

            # Handle health updates (mood/pain tracker)
            elif data.get("command") == "health_update":
                metric_type = data.get("type")  # "pain" or "anxiety"
                level = data.get("level")  # 0-4
                
                if self.on_health_update:
                    self.on_health_update(metric_type, level)
                    
        except Exception as e:
            logger.error(f"Error processing dashboard message: {e}")
    
    def set_transcribing_status(self, status: bool):
        """Set by Jarvis to indicate active STT transcription window."""
        self.is_transcribing = status

    def set_stt_backend(self, backend: str, device: str):
        """Set active STT backend/device for accurate NPU metric behavior."""
        self.stt_backend = (backend or "none").lower()
        self.stt_device = (device or "none").upper()

    def set_stt_last_latency(self, ms: int):
        """Track recent STT latency and briefly reflect activity on NPU gauge."""
        self.last_stt_latency_ms = max(0, int(ms))
        self.last_stt_display_time = time.time()
        # Convert latency to a small post-transcription usage pulse.
        self.last_stt_display_value = max(8, min(30, int(self.last_stt_latency_ms / 80)))

    def set_last_ollama_response_time(self, ms: int):
        """Set by Jarvis after an LLM call to show response time."""
        self.last_ollama_response_time = ms
        self.last_ollama_display_time = time.time()
        self.last_ollama_display_value = ms

    def _on_error(self, ws, error):
        """WebSocket error handler."""
        logger.debug(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed."""
        self.connected = False
        logger.debug("Disconnected from dashboard")
    
    def _metrics_loop(self):
        """Collect and push system metrics every 500ms."""
        while self.running:
            try:
                if self.connected:
                    metrics = self._collect_metrics()
                    self.push_metrics(metrics)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
    
    def _collect_metrics(self) -> Dict[str, float]:
        """Collect system metrics using psutil."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            # Temperatures (if available)
            temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            cpu_temp = 0
            gpu_temp = 0
            
            # Try to get CPU temperature
            if temps:
                # Try common sensor names
                for sensor_name in ["coretemp", "cpu_thermal", "k10temp"]:
                    if sensor_name in temps:
                        cpu_temp = temps[sensor_name][0].current
                        break
                
                # Try to get GPU temperature
                for sensor_name in ["nvidia", "amdgpu", "radeon"]:
                    if sensor_name in temps:
                        gpu_temp = temps[sensor_name][0].current
                        break
            
            # Fallback: simulate temps based on CPU usage for demo
            if cpu_temp == 0:
                cpu_temp = 40 + (cpu_percent * 0.4)  # 40-80°C range
            if gpu_temp == 0:
                gpu_temp = 45 + (cpu_percent * 0.3)  # 45-75°C range
            
            # NPU usage: only non-zero when STT backend can use NPU.
            npu_usage = 0
            npu_capable = self.stt_backend == "openvino-whisper" and self.stt_device in {"NPU", "AUTO"}
            if npu_capable:
                if self.is_transcribing:
                    npu_usage = 75 if self.stt_device == "NPU" else 55
                elif (time.time() - self.last_stt_display_time) <= 5:
                    npu_usage = self.last_stt_display_value

            # Ollama response time (retain briefly so UI can render it clearly)
            ollama_ms = self.last_ollama_response_time
            if ollama_ms > 0:
                self.last_ollama_response_time = 0
                self.last_ollama_display_time = time.time()
                self.last_ollama_display_value = ollama_ms
            elif (time.time() - self.last_ollama_display_time) <= 10:
                ollama_ms = self.last_ollama_display_value
            else:
                ollama_ms = 0

            return {
                "cpu": round(cpu_percent, 1),
                "memory": round(memory_percent, 1),
                "cpuTemp": round(cpu_temp, 1),
                "gpuTemp": round(gpu_temp, 1),
                "npu": npu_usage,
                "ollama": ollama_ms
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {"cpu": 0, "memory": 0, "cpuTemp": 0, "gpuTemp": 0, "npu": 0, "ollama": 0}
    
    def push_state(self, mode: str = None, **kwargs):
        """Push Jarvis state update to dashboard.
        
        Args:
            mode: "idle", "listening", or "speaking"
            **kwargs: gamingMode, muteMic, conversationalMode
        """
        if not self.connected:
            return
        
        if mode:
            self.current_state["mode"] = mode
        
        for key, value in kwargs.items():
            if key in self.current_state:
                self.current_state[key] = value
        
        self._send({
            "type": "state",
            "data": self.current_state
        })
    
    def push_metrics(self, metrics: Dict[str, float]):
        """Push system metrics to dashboard."""
        if not self.connected:
            return
        
        self._send({
            "type": "metrics",
            "data": metrics
        })
    
    def push_log(self, level: str, message: str):
        """Push log entry to dashboard.
        
        Args:
            level: "info", "warn", "error", "success"
            message: Log message text
        """
        if not self.connected:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._send({
            "type": "log",
            "data": {
                "id": f"log-{int(time.time() * 1000)}",
                "timestamp": timestamp,
                "level": level,
                "message": message
            }
        })
    
    def push_focus(self, content_type: str, title: str, content: str):
        """Push focus window content to dashboard.
        
        Args:
            content_type: "code", "docs", or "email"
            title: Content title
            content: Content text
        """
        if not self.connected:
            return
        
        self._send({
            "type": "focus",
            "data": {
                "type": content_type,
                "title": title,
                "content": content
            }
        })
    
    def update_ticker(self, items: List[Dict[str, str]]):
        """Push ticker tape items to the dashboard.
        
        Args:
            items: A list of dicts, e.g., [{"short_key": "wr1", "label": "AI News"}]
        """
        if not self.connected:
            return
        
        self._send({
            "type": "ticker",
            "data": items
        })
        # Log for debugging that the ticker was updated
        short_keys = [item['short_key'] for item in items]
        logger.debug(f"Pushed to ticker: {short_keys}")

    def push_news_ticker(self, headlines: List[Dict[str, Any]]):
        """Push formatted News short-keys to ticker, e.g. 'News 1', 'News 2'."""
        items = []
        for idx, article in enumerate(headlines[:10], 1):
            title = str(article.get("title", "Untitled")).strip()
            items.append({"short_key": f"News {idx}", "label": title})
        self.update_ticker(items)
    
    def _send(self, data: Dict[str, Any]):
        """Send JSON message to dashboard."""
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                logger.debug(f"Error sending to dashboard: {e}")
