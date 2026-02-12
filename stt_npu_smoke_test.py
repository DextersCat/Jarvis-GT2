#!/usr/bin/env python3
"""
STT NPU Smoke Test (OpenVINO-first)

Why this exists:
- `openai-whisper` (PyTorch backend) is CPU/CUDA-oriented and does not provide
  a native `NPU`/`AUTO` device path for Intel NPU.
- For Intel NPU STT, use OpenVINO Whisper pipeline (`openvino_genai`).

This script:
1) Diagnoses your current stack (openai-whisper vs openvino/openvino_genai).
2) Tests OpenVINO Whisper pipeline load on NPU/AUTO/CPU if available.
3) Falls back to openai-whisper CPU sanity check for baseline functionality.

Usage:
  .\\.venv\\Scripts\\python.exe stt_npu_smoke_test.py --model-dir C:\\models\\whisper-small-int8-ov
  .\\.venv\\Scripts\\python.exe stt_npu_smoke_test.py --model-dir C:\\models\\whisper-small-int8-ov --audio sample.wav
  .\\.venv\\Scripts\\python.exe stt_npu_smoke_test.py --openai-cpu-only
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import traceback
import wave
import struct
import time
from datetime import datetime


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def print_header() -> None:
    print(f"[{ts()}] STT NPU smoke test")
    print(f"[{ts()}] Python: {sys.version.split()[0]}")


def diagnose_stack() -> None:
    print(f"[{ts()}] Stack diagnosis:")
    print(f"  - openai-whisper: {'yes' if has_module('whisper') else 'no'}")
    print(f"  - openvino: {'yes' if has_module('openvino') else 'no'}")
    print(f"  - openvino_genai: {'yes' if has_module('openvino_genai') else 'no'}")


def test_openai_whisper_cpu(audio_path: str | None, model_name: str) -> bool:
    print(f"[{ts()}] Testing openai-whisper CPU baseline ...")
    try:
        import whisper  # type: ignore

        t0 = time.perf_counter()
        model = whisper.load_model(model_name, device="cpu")
        load_s = time.perf_counter() - t0
        print(f"[{ts()}] PASS openai-whisper load on CPU. model.device={getattr(model, 'device', 'unknown')}")
        print(f"[{ts()}] openai-whisper CPU load_time_s={load_s:.3f}")

        if audio_path and os.path.exists(audio_path):
            t1 = time.perf_counter()
            result = model.transcribe(audio_path, language="en")
            tr_s = time.perf_counter() - t1
            text = (result.get("text") or "").strip()
            preview = text[:120] + ("..." if len(text) > 120 else "")
            print(f"[{ts()}] PASS openai-whisper transcribe on CPU. text={preview!r}")
            print(f"[{ts()}] openai-whisper CPU transcribe_time_s={tr_s:.3f}")
        return True
    except Exception as exc:
        print(f"[{ts()}] FAIL openai-whisper CPU: {exc}")
        print(traceback.format_exc(limit=4))
        return False


def test_openvino_whisper(model_dir: str, device: str, audio_path: str | None) -> bool:
    print(f"[{ts()}] Testing OpenVINO Whisper load on device={device!r} ...")
    try:
        import openvino as ov  # type: ignore
        import openvino_genai as ov_genai  # type: ignore

        if not os.path.isdir(model_dir):
            print(f"[{ts()}] FAIL model directory not found: {model_dir}")
            return False

        # Validate requested device exists in runtime.
        core = ov.Core()
        devices = core.available_devices
        print(f"[{ts()}] OpenVINO available devices: {devices}")
        if device.upper() != "AUTO" and device.upper() not in devices:
            print(f"[{ts()}] FAIL requested device {device!r} not in available devices")
            return False

        # Load pipeline (this is the critical NPU-path compile step).
        t0 = time.perf_counter()
        pipe = ov_genai.WhisperPipeline(model_dir, device.upper())
        load_s = time.perf_counter() - t0
        print(f"[{ts()}] PASS OpenVINO Whisper pipeline loaded on {device.upper()}")
        print(f"[{ts()}] OpenVINO {device.upper()} load_time_s={load_s:.3f}")

        if audio_path:
            if not os.path.exists(audio_path):
                print(f"[{ts()}] WARN audio file not found, skipping transcribe: {audio_path}")
            else:
                raw = load_wav_as_float32(audio_path)
                t1 = time.perf_counter()
                result = pipe.generate(raw)
                tr_s = time.perf_counter() - t1
                out = extract_whisper_result_text(result)[:120]
                print(f"[{ts()}] PASS OpenVINO Whisper transcribe on {device.upper()}: {out!r}")
                print(f"[{ts()}] OpenVINO {device.upper()} transcribe_time_s={tr_s:.3f}")
        return True
    except Exception as exc:
        print(f"[{ts()}] FAIL OpenVINO Whisper on {device!r}: {exc}")
        print(traceback.format_exc(limit=5))
        return False


def print_fix_guidance() -> None:
    print(f"[{ts()}] Guidance:")
    print("  Your current setup appears to use openai-whisper only.")
    print("  For Intel NPU STT, install OpenVINO runtime + GenAI and use an exported Whisper OpenVINO model dir.")
    print("  Typical steps:")
    print("    1) pip install -U openvino openvino-genai")
    print("    2) Prepare/export a Whisper OpenVINO model directory")
    print("    3) Re-run this script with --model-dir <path> and device NPU/AUTO")


def load_wav_as_float32(path: str) -> list[float]:
    """Load mono/stereo PCM WAV and return normalized mono float list (-1..1)."""
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)

    if sampwidth != 2:
        raise ValueError("Only 16-bit PCM WAV is supported by this smoke test.")

    total_samples = len(data) // 2
    samples = struct.unpack("<" + "h" * total_samples, data)

    if channels == 1:
        mono = samples
    else:
        mono = []
        for i in range(0, len(samples), channels):
            frame = samples[i:i + channels]
            mono.append(int(sum(frame) / len(frame)))

    return [max(-1.0, min(1.0, s / 32768.0)) for s in mono]


def extract_whisper_result_text(result) -> str:
    """Extract text across common openvino_genai Whisper result shapes."""
    if result is None:
        return ""
    # Some versions expose result.texts (list[str])
    texts = getattr(result, "texts", None)
    if texts and isinstance(texts, (list, tuple)):
        return " ".join(str(t) for t in texts if t is not None).strip()
    # Some versions may expose text directly
    text = getattr(result, "text", None)
    if text:
        return str(text).strip()
    # Fallback
    return str(result).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate STT NPU readiness and load path")
    parser.add_argument("--model", default="base", help="openai-whisper model for CPU baseline (default: base)")
    parser.add_argument("--model-dir", default="", help="OpenVINO Whisper model directory")
    parser.add_argument("--audio", default="", help="Optional audio file for transcription test")
    parser.add_argument("--device", default="NPU", choices=["NPU", "AUTO", "CPU"], help="Primary OpenVINO device to test")
    parser.add_argument("--openai-cpu-only", action="store_true", help="Only run openai-whisper CPU baseline")
    args = parser.parse_args()

    print_header()
    diagnose_stack()

    audio_path = args.audio or None

    if args.openai_cpu_only:
        ok = test_openai_whisper_cpu(audio_path, args.model)
        return 0 if ok else 1

    ran_openvino = False
    openvino_pass = False

    if has_module("openvino") and has_module("openvino_genai") and args.model_dir:
        ran_openvino = True
        for dev in [args.device, "AUTO", "CPU"]:
            if dev == args.device:
                openvino_pass = test_openvino_whisper(args.model_dir, dev, audio_path) or openvino_pass
            elif dev != args.device:
                # Additional fallback checks (quick compile sanity).
                test_openvino_whisper(args.model_dir, dev, None)
    else:
        print(f"[{ts()}] OpenVINO path not runnable yet (missing packages and/or --model-dir).")

    cpu_ok = test_openai_whisper_cpu(audio_path, args.model)

    print(f"\n[{ts()}] Summary:")
    print(f"  - OpenVINO NPU-capable path tested: {'yes' if ran_openvino else 'no'}")
    print(f"  - OpenVINO primary pass: {'yes' if openvino_pass else 'no'}")
    print(f"  - openai-whisper CPU baseline: {'yes' if cpu_ok else 'no'}")

    if openvino_pass:
        print(f"[{ts()}] RESULT: NPU-capable STT path is available.")
        return 0

    print(f"[{ts()}] RESULT: NPU STT path not available yet.")
    print_fix_guidance()
    # Non-zero to make this CI-friendly for readiness checks.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
