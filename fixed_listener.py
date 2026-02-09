"""
PRODUCTION-READY WAKE WORD LISTENER
Optimized for 48kHz Windows microphones with openWakeWord
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model
import queue
import sys

# --- CONFIGURATION ---
WAKE_WORD = "hey_jarvis"
MIC_DEVICE_INDEX = 17  # Elgato Wave:3
NATIVE_RATE = 48000  # Your locked mic rate
TARGET_RATE = 16000  # OpenWakeWord requirement
WAKE_THRESHOLD = 0.5  # Confidence threshold
CHUNK_SIZE_16K = 1280  # Model requirement
CHUNK_SIZE_48K = CHUNK_SIZE_16K * 3  # 3840 @ 48kHz

class DirectBufferListener:
    """
    Direct buffer handling ensures perfect frame alignment
    without accumulation drift or sample loss
    """
    
    def __init__(self):
        print("Initializing Direct Buffer Listener...")
        
        # Load model
        self.wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
        print(f"✓ Model loaded for '{WAKE_WORD}'")
        
        # Buffer for maintaining exact sample counts
        self.buffer = np.array([], dtype=np.float32)
        self.detection_count = 0
        self.chunk_count = 0
        
    def process_audio(self, indata, frames, time, status):
        """
        Process audio with guaranteed buffer alignment
        """
        if status:
            print(f"Stream status: {status}", file=sys.stderr)
        
        try:
            # Step 1: Extract mono audio (handle both 1D and 2D arrays)
            if len(indata.shape) == 2:
                audio_mono = indata[:, 0].copy()
            else:
                audio_mono = indata.copy()
            
            # Step 2: Type verification - must be float32
            if audio_mono.dtype != np.float32:
                audio_mono = audio_mono.astype(np.float32)
            
            # Step 3: Resample 48kHz -> 16kHz using high-quality polyphase filter
            audio_16k = signal.resample_poly(audio_mono, up=1, down=3)
            
            # Step 4: Verify exact frame size (critical for model)
            if len(audio_16k) != CHUNK_SIZE_16K:
                print(f"⚠ Frame size mismatch: {len(audio_16k)} != {CHUNK_SIZE_16K}")
                # Pad or trim to exact size
                if len(audio_16k) < CHUNK_SIZE_16K:
                    audio_16k = np.pad(audio_16k, (0, CHUNK_SIZE_16K - len(audio_16k)))
                else:
                    audio_16k = audio_16k[:CHUNK_SIZE_16K]
            
            # Step 5: Ensure contiguous memory layout (some ops can fragment it)
            audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
            
            # Step 6: Feed to model
            predictions = self.wake_model.predict(audio_16k)
            score = predictions.get(WAKE_WORD, 0.0)
            
            self.chunk_count += 1
            
            # Step 7: Display confidence when above noise floor
            if score > 0.01:
                bar = "█" * int(score * 40)
                print(f"\rConfidence: {score:.3f} [{bar:<40}]", end="", flush=True)
            
            # Step 8: Detection
            if score >= WAKE_THRESHOLD:
                self.detection_count += 1
                print(f"\n\n🎯 WAKE WORD DETECTED! (#{self.detection_count})")
                print(f"   Confidence: {score:.3f} ({score*100:.1f}%)")
                print(f"   Chunks processed: {self.chunk_count}\n")
                return True
                
        except Exception as e:
            print(f"\nError in audio processing: {e}")
            import traceback
            traceback.print_exc()
        
        return False
    
    def start(self):
        """Start listening loop"""
        print(f"\n{'='*60}")
        print(f"👂 LISTENING FOR: '{WAKE_WORD}'")
        print(f"   Threshold: {WAKE_THRESHOLD}")
        print(f"   Native rate: {NATIVE_RATE} Hz")
        print(f"   Target rate: {TARGET_RATE} Hz")
        print(f"   Chunk size: {CHUNK_SIZE_48K} → {CHUNK_SIZE_16K}")
        print(f"{'='*60}\n")
        
        try:
            def callback(indata, frames, time, status):
                if self.process_audio(indata, frames, time, status):
                    # Optional: stop on detection
                    # raise sd.CallbackStop
                    pass
            
            with sd.InputStream(
                samplerate=NATIVE_RATE,
                device=MIC_DEVICE_INDEX,
                channels=1,  # Explicit mono
                callback=callback,
                blocksize=CHUNK_SIZE_48K,
                dtype='float32'  # Explicit float32
            ):
                print("Press Ctrl+C to stop...\n")
                while True:
                    sd.sleep(1000)
                    
        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print("LISTENER STOPPED")
            print(f"{'='*60}")
            print(f"Total detections: {self.detection_count}")
            print(f"Total chunks: {self.chunk_count}")
            if self.chunk_count > 0:
                print(f"Detection rate: {self.detection_count/self.chunk_count*100:.2f}%")
        except Exception as e:
            print(f"\nFatal error: {e}")
            import traceback
            traceback.print_exc()


class BufferedListener:
    """
    Alternative implementation using explicit buffer management
    Useful when blocksize doesn't divide evenly
    """
    
    def __init__(self):
        print("Initializing Buffered Listener...")
        self.wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
        self.buffer_16k = np.array([], dtype=np.float32)
        print(f"✓ Model loaded")
    
    def process_audio(self, indata, frames, time, status):
        """Process with accumulation buffer"""
        if status:
            print(f"Status: {status}", file=sys.stderr)
        
        # Extract and resample
        audio_mono = indata[:, 0] if len(indata.shape) == 2 else indata
        audio_16k = signal.resample_poly(audio_mono, 1, 3).astype(np.float32)
        
        # Add to buffer
        self.buffer_16k = np.concatenate([self.buffer_16k, audio_16k])
        
        # Process complete chunks
        while len(self.buffer_16k) >= CHUNK_SIZE_16K:
            chunk = self.buffer_16k[:CHUNK_SIZE_16K]
            self.buffer_16k = self.buffer_16k[CHUNK_SIZE_16K:]
            
            # Ensure contiguous
            chunk = np.ascontiguousarray(chunk, dtype=np.float32)
            
            # Predict
            predictions = self.wake_model.predict(chunk)
            score = predictions.get(WAKE_WORD, 0.0)
            
            if score > 0.01:
                print(f"\rScore: {score:.3f}", end="", flush=True)
            
            if score >= WAKE_THRESHOLD:
                print(f"\n🎯 DETECTED! Confidence: {score:.3f}\n")
    
    def start(self):
        """Start listening"""
        print(f"\n👂 Listening (buffered mode)...\n")
        
        try:
            with sd.InputStream(
                samplerate=NATIVE_RATE,
                device=MIC_DEVICE_INDEX,
                channels=1,
                callback=self.process_audio,
                blocksize=CHUNK_SIZE_48K,
                dtype='float32'
            ):
                print("Press Ctrl+C to stop...\n")
                while True:
                    sd.sleep(1000)
        except KeyboardInterrupt:
            print("\n\nStopped")


if __name__ == "__main__":
    print("\nSelect mode:")
    print("1. Direct Buffer (recommended)")
    print("2. Buffered accumulation")
    
    choice = input("\nChoice [1]: ").strip() or "1"
    
    if choice == "1":
        listener = DirectBufferListener()
    else:
        listener = BufferedListener()
    
    listener.start()
