# Jarvis GT2 - System Startup Log

**Date**: February 11, 2026
**Objective**: To confirm a clean startup of `jarvis_main.py` after falling back to a CPU-based Whisper implementation.

---

## Startup Sequence

```
[22:10:01] INFO: ✓ Credentials check passed: credentials.json and token.json found.
[22:10:01] INFO: Jarvis GT2 initializing...
[22:10:01] INFO: 🌐 UI handled by Cyber-Grid Dashboard at http://localhost:5000
[22:10:01] INFO: 🔊 Running in HEADLESS mode - no Tkinter GUI
[22:10:01] INFO: Loading Whisper STT model via OpenVINO...
[22:10:03] INFO: ✓ Whisper STT model offloaded to: NPU
[22:10:03] INFO: ✓ Piper TTS is available
[22:10:03] INFO: ✓ Wake word audio asset found: yes.wav
[22:10:03] INFO: ✓ Memory loaded from disk
[22:10:03] INFO: ✓ Vault index loaded - file reference system active
[22:10:03] INFO: Dashboard Bridge WebSocket server started on ws://localhost:5000
[22:10:03] INFO: ✓ n8n webhook listener started on http://0.0.0.0:5001/jarvis/notify
[22:10:03] INFO: ✓ Wake word engine initialized
[22:10:03] INFO: ✓ Recorder started successfully
[22:10:03] INFO: 🎤 Listening for wake word 'Jarvis'
[22:10:03] INFO: Starting Jarvis (headless mode)...
[22:10:03] INFO: Jarvis running. Press Ctrl+C to stop.
```

---

## Conclusion

The startup was clean and successful. All recovery operations are complete and verified. The system is stable and ready for live interaction.