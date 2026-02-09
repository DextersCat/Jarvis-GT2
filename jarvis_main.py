import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import requests
import tempfile
import os
import subprocess
import re
from flask import Flask, request
import threading
import numpy as np
import time
import pyaudio
from openwakeword.model import Model
from openwakeword.utils import download_models
import scipy.signal as signal
try:
    import winsound
except Exception:
    winsound = None


# --- CONFIGURATION ---
BRAIN_URL = "http://192.168.1.27:11434/api/generate"
LLM_MODEL = "llama3.1:8b"
VOICE_MODEL = "jarvis-high.onnx"
FS = 16000  # Sample rate
SILENCE_THRESHOLD = 0.010
SILENCE_SECONDS = 1.0
MAX_RECORD_SECONDS = 12.0
MIC_DEVICE_INDEX = 17  # Elgato Wave:3

WAKE_WORD = "hey_jarvis"
WAKE_RATE = 16000
WAKE_CHUNK = 1280  # 80 ms
WAKE_THRESHOLD = 0.3
WAKE_PATIENCE = 1
WAKE_DEVICE_INDEX = MIC_DEVICE_INDEX  # Elgato Wave:3

SHORT_TERM_MEMORY = []
MAX_MEMORY = 5

app = Flask(__name__)


@app.route('/speak', methods=['POST'])
def receive_speak():
    data = request.get_json(force=True)
    sender = data.get("sender", "Unknown")
    subject = data.get("subject", "No Subject")
    email_id = data.get("id")

    SHORT_TERM_MEMORY.append({
        "sender": sender,
        "subject": subject,
        "id": email_id,
    })
    if len(SHORT_TERM_MEMORY) > MAX_MEMORY:
        SHORT_TERM_MEMORY.pop(0)
    
    # Jarvis builds his own sentence
    full_sentence = f"Sir, you have a new email from {sender} regarding {subject}."
    
    jarvis_speak(full_sentence)
    return {"status": "success"}, 200


# We run this in the background so it doesn't stop your main loop
def start_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

threading.Thread(target=start_flask, daemon=True).start()



print("Systems online. Loading neural patterns...")
stt_model = whisper.load_model("base")


download_models([WAKE_WORD])
wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")



def jarvis_speak(text):
    # This filter removes asterisks and markdown symbols before speaking
    clean_text = re.sub(r'[*_#~>]', '', text) 
    print(f"\nJARVIS: {clean_text}")
    
    model = VOICE_MODEL
    temp_speech = tempfile.mktemp(suffix='.wav')
    
    # We use the cleaned text here
    cmd = f'piper --model {model} --output_file {temp_speech}'
    subprocess.run(cmd, input=clean_text.encode('utf-8'), shell=True, capture_output=True)
    
    if os.path.exists(temp_speech):
        subprocess.run(f'ffplay -nodisp -autoexit -loglevel quiet {temp_speech}', shell=True)
        os.remove(temp_speech)


def play_ding():
    if winsound:
        winsound.Beep(880, 150)
        return
    print("\a", end="", flush=True)




def wait_for_wake_word():
    NATIVE_RATE = 48000 
    TARGET_RATE = 16000
    
    print(f"\n>>> [IDLE] Monitoring at {NATIVE_RATE}Hz...")

    # This function runs every time the mic has data
    def callback(indata, frames, time, status):
        if status:
            print(status)
        
        # 1. Safe channel extraction (handles both mono and stereo)
        audio_mono = indata[:, 0] if len(indata.shape) == 2 else indata
        
        # 2. Convert to 16kHz using professional resampling
        audio_16k = signal.resample_poly(audio_mono, 1, 3)
        
        # 3. Guarantee exact buffer size (1280 samples required)
        if len(audio_16k) != 1280:
            if len(audio_16k) < 1280:
                audio_16k = np.pad(audio_16k, (0, 1280 - len(audio_16k)))
            else:
                audio_16k = audio_16k[:1280]
        
        # 4. Ensure contiguous float32 memory layout
        audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
        
        # 5. Feed to Jarvis
        preds = wake_model.predict(audio_16k)
        score = preds.get(WAKE_WORD, 0.0)
        
        # 6. Visual feedback so you know he's 'thinking'
        if score > 0.01:
            print(f"Confidence: {score:.2f}", end="\r")

        if score >= WAKE_THRESHOLD:
            print(f"\n>>> [WAKE] Detected: {WAKE_WORD}!")
            raise sd.CallbackStop

    # Start the stable 'sounddevice' stream
    with sd.InputStream(samplerate=NATIVE_RATE, device=MIC_DEVICE_INDEX, 
                        channels=1, callback=callback, blocksize=WAKE_CHUNK * 3):
        while True:
            sd.sleep(100)
# def wait_for_wake_word():
#     # Mic-specific settings
#     NATIVE_RATE = 48000 
#     RESAMPLE_FACTOR = 3  # 48000 / 16000
    
#     print(f"\n>>> [IDLE] Monitoring at {NATIVE_RATE}Hz...")
#     pa = pyaudio.PyAudio()
    
#     # We must read 3x the data to result in the correct chunk size for the model
#     stream = pa.open(
#         format=pyaudio.paInt16,
#         channels=1,
#         rate=NATIVE_RATE,
#         input=True,
#         frames_per_buffer=WAKE_CHUNK * RESAMPLE_FACTOR,
#         input_device_index=WAKE_DEVICE_INDEX,
#     )

#     try:
#         while True:
#             # Read a larger chunk from the 48k hardware
#             data = stream.read(WAKE_CHUNK * RESAMPLE_FACTOR, exception_on_overflow=False)
#             audio_native = np.frombuffer(data, dtype=np.int16)
            
#             # DECIMATION: Take every 3rd sample to get back to 16000Hz
#             audio_resampled = audio_native[::RESAMPLE_FACTOR].astype(np.float32) / 32768.0
            
#             # Predict using the 16k data
#             preds = wake_model.predict(audio_resampled)
#             score = preds.get(WAKE_WORD, 0.0)
            
#             # DEBUG: Now you should finally see these numbers move!
#             if score > 0.01:
#                 print(f"Confidence: {score:.2f}", end="\r")

#             if score >= WAKE_THRESHOLD:
#                 print(f"\n>>> [WAKE] Detected: {WAKE_WORD}!")
#                 return
#     finally:
#         stream.stop_stream()
#         stream.close()
#         pa.terminate()
# def wait_for_wake_word():
#     print("\n>>> [IDLE] Waiting for 'Jarvis'...")
#     pa = pyaudio.PyAudio()
#     stream = pa.open(
#         format=pyaudio.paInt16,
#         channels=1,
#         rate=WAKE_RATE,
#         input=True,
#         frames_per_buffer=WAKE_CHUNK,
#         input_device_index=WAKE_DEVICE_INDEX,
#     )

#     consecutive = 0
#     try:
#         while True:
#             data = stream.read(WAKE_CHUNK, exception_on_overflow=False)
#             audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
#             preds = wake_model.predict(audio)
#             # Inside the while True loop of wait_for_wake_word
#             score = preds.get(WAKE_WORD, 0.0)
#             if score > 0.01: # Only print if there is a tiny bit of a match
#                 print(f"Confidence: {score:.4f}")
#             if score >= WAKE_THRESHOLD:
#                 consecutive += 1
#                 if consecutive >= WAKE_PATIENCE:
#                     print(f">>> [WAKE] Detected {WAKE_WORD} ({score:.2f})")
#                     return
#             else:
#                 consecutive = 0
#     finally:
#         stream.stop_stream()
#         stream.close()
#         pa.terminate()
# def wait_for_wake_word():
#     print("\n>>> [DEBUG] Checking Raw Audio Stream...")
#     pa = pyaudio.PyAudio()
#     stream = pa.open(
#         format=pyaudio.paInt16,
#         channels=1,
#         rate=WAKE_RATE,
#         input=True,
#         frames_per_buffer=WAKE_CHUNK,
#         input_device_index=WAKE_DEVICE_INDEX,
#     )

#     try:
#         for _ in range(50): # Just check 50 chunks
#             data = stream.read(WAKE_CHUNK, exception_on_overflow=False)
#             audio = np.frombuffer(data, dtype=np.int16)
#             peak = np.abs(audio).max() # Get the loudest sound in this chunk
#             print(f"Peak Volume: {peak}") 
#     finally:
#         stream.close()
#         pa.terminate()

def listen():
    """Record a command after wake, stopping on silence."""
    print("\n>>> [LISTENING]...")

    block_size = int(FS * 0.5)
    silence_blocks_needed = int(SILENCE_SECONDS / 0.5)
    silence_blocks = 0
    heard_speech = False
    frames = []

    start_time = time.time()
    while True:
        block = sd.rec(
            block_size,
            samplerate=FS,
            channels=1,
            device=MIC_DEVICE_INDEX,
            blocking=True,
        )
        frames.append(block)

        volume_norm = np.linalg.norm(block) / np.sqrt(len(block))
        if volume_norm >= SILENCE_THRESHOLD:
            heard_speech = True
            silence_blocks = 0
        else:
            if heard_speech:
                silence_blocks += 1

        if heard_speech and silence_blocks >= silence_blocks_needed:
            break
        if time.time() - start_time >= MAX_RECORD_SECONDS:
            break

    recording = np.concatenate(frames, axis=0)
    volume_norm = np.linalg.norm(recording) / np.sqrt(len(recording))
    print(f"Volume Level: {volume_norm:.4f}")

    if volume_norm < SILENCE_THRESHOLD:
        print(">>> [SILENCE DETECTED - SKIPPING]")
        return None

    temp_path = tempfile.mktemp(suffix=".wav")
    write(temp_path, FS, recording)
    return temp_path

def think(text):
    """The Brain: Sends text to the 5070 Ti and gets a response."""
    payload = {
        "model": LLM_MODEL,
        "prompt": f"You are JARVIS. Be helpful, concise, and British. Spencer said: {text}",
        "stream": False
    }
    try:
        response = requests.post(BRAIN_URL, json=payload, timeout=60)
        return response.json().get('response', "I'm having trouble thinking, Spencer.")
    except Exception as e:
        return f"Connection to the 5070 Ti brain failed: {e}"

if __name__ == "__main__":
    jarvis_speak("Hello Spencer. Systems are stable. I am monitoring the Elgato feed now.")
    
    try:
        while True:
            # 1. WAKE WORD (idle)
            wait_for_wake_word()
            play_ding()

            # 2. LISTEN
            audio_file = listen()
            
            # If listen() returned None, just start over
            if audio_file is None:
                continue
            
            # 3. TRANSCRIBE
            result = stt_model.transcribe(audio_file, fp16=False)
            user_input = str(result.get("text", "")).strip()
            
            if len(user_input) > 2:
                print(f"You said: {user_input}")

                lowered = user_input.lower()
                if any(k in lowered for k in ["who", "last", "repeat"]):
                    if SHORT_TERM_MEMORY:
                        last = SHORT_TERM_MEMORY[-1]
                        reply = (
                            f"The last email was from {last['sender']} "
                            f"regarding {last['subject']}."
                        )
                    else:
                        reply = "I do not have any recent emails in memory yet, Spencer."
                else:
                    # 4. THINK
                    reply = think(user_input)
                
                # 5. SPEAK
                jarvis_speak(reply)
            
            # Clean up audio file
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
    except KeyboardInterrupt:
        print("\nJarvis going offline. Sleep well, Spencer.")
