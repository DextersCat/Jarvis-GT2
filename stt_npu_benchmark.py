#!/usr/bin/env python3
"""
STT Benchmark: OpenVINO NPU vs CPU baselines

Runs repeated transcriptions on the same audio and reports:
- avg / min / max / p95 latency
- last transcript preview for sanity

Usage:
  .\\.venv\\Scripts\\python.exe stt_npu_benchmark.py --model-dir .\\whisper-base-with-past-ov2 --audio .\\yes.wav
"""

from __future__ import annotations

import argparse
import os
import statistics
import struct
import time
import wave
from typing import Callable, Dict, List, Tuple


def load_wav_as_float32(path: str) -> List[float]:
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)

    if sampwidth != 2:
        raise ValueError("Only 16-bit PCM WAV supported.")

    samples = struct.unpack("<" + "h" * (len(data) // 2), data)
    if channels == 1:
        mono = samples
    else:
        mono = []
        for i in range(0, len(samples), channels):
            frame = samples[i:i + channels]
            mono.append(int(sum(frame) / len(frame)))
    return [max(-1.0, min(1.0, s / 32768.0)) for s in mono]


def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    idx = int(round(0.95 * (len(s) - 1)))
    return s[idx]


def summarize(name: str, vals: List[float], preview: str) -> None:
    print(f"\n{name}")
    print(f"  runs={len(vals)} avg={statistics.mean(vals):.4f}s min={min(vals):.4f}s max={max(vals):.4f}s p95={p95(vals):.4f}s")
    print(f"  transcript={preview!r}")


def bench_runner(
    name: str,
    fn: Callable[[], str],
    warmup: int,
    runs: int,
) -> Tuple[List[float], str]:
    for _ in range(warmup):
        _ = fn()
    latencies = []
    out = ""
    for _ in range(runs):
        t0 = time.perf_counter()
        out = fn()
        latencies.append(time.perf_counter() - t0)
    return latencies, out[:120]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark STT latency across NPU/CPU paths")
    parser.add_argument("--model-dir", required=True, help="OpenVINO Whisper model directory")
    parser.add_argument("--audio", required=True, help="Audio WAV file")
    parser.add_argument("--runs", type=int, default=10, help="Measured runs per backend")
    parser.add_argument("--warmup", type=int, default=2, help="Warmup runs per backend")
    parser.add_argument("--skip-openai", action="store_true", help="Skip openai-whisper CPU baseline")
    args = parser.parse_args()

    if not os.path.isdir(args.model_dir):
        print(f"Model directory not found: {args.model_dir}")
        return 2
    if not os.path.exists(args.audio):
        print(f"Audio file not found: {args.audio}")
        return 2

    raw = load_wav_as_float32(args.audio)
    print("Loading backends...")

    import openvino as ov  # type: ignore
    import openvino_genai as ov_genai  # type: ignore

    core = ov.Core()
    devices = set(core.available_devices)
    print(f"OpenVINO devices: {sorted(devices)}")

    results: Dict[str, Tuple[List[float], str]] = {}

    # OpenVINO NPU
    if "NPU" in devices:
        npu_pipe = ov_genai.WhisperPipeline(args.model_dir, "NPU")

        def run_npu() -> str:
            r = npu_pipe.generate(raw)
            texts = getattr(r, "texts", None)
            if texts:
                return " ".join(str(t) for t in texts if t is not None).strip()
            t = getattr(r, "text", None)
            return str(t).strip() if t else str(r).strip()

        results["OpenVINO Whisper NPU"] = bench_runner("OpenVINO Whisper NPU", run_npu, args.warmup, args.runs)
    else:
        print("Skipping NPU benchmark: NPU device not available in OpenVINO.")

    # OpenVINO CPU
    cpu_pipe = ov_genai.WhisperPipeline(args.model_dir, "CPU")

    def run_ov_cpu() -> str:
        r = cpu_pipe.generate(raw)
        texts = getattr(r, "texts", None)
        if texts:
            return " ".join(str(t) for t in texts if t is not None).strip()
        t = getattr(r, "text", None)
        return str(t).strip() if t else str(r).strip()

    results["OpenVINO Whisper CPU"] = bench_runner("OpenVINO Whisper CPU", run_ov_cpu, args.warmup, args.runs)

    # openai-whisper CPU
    if not args.skip_openai:
        import whisper  # type: ignore
        w_model = whisper.load_model("base", device="cpu")

        def run_openai_cpu() -> str:
            r = w_model.transcribe(args.audio, language="en")
            return (r.get("text") or "").strip()

        results["openai-whisper CPU"] = bench_runner("openai-whisper CPU", run_openai_cpu, args.warmup, args.runs)

    print("\n=== STT Benchmark Results ===")
    for name, (vals, preview) in results.items():
        summarize(name, vals, preview)

    # Optional relative summary if both NPU and CPU OpenVINO exist.
    if "OpenVINO Whisper NPU" in results and "OpenVINO Whisper CPU" in results:
        npu_avg = statistics.mean(results["OpenVINO Whisper NPU"][0])
        cpu_avg = statistics.mean(results["OpenVINO Whisper CPU"][0])
        if npu_avg > 0:
            print(f"\nNPU speedup vs OpenVINO CPU: {cpu_avg / npu_avg:.2f}x")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

