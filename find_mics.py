from pvrecorder import PvRecorder

for index, device in enumerate(PvRecorder.get_available_devices()):
    print(f"[{index}] {device}")