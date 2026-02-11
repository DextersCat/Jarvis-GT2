import whisper
import torch
import sys
import logging

# Basic logger to provide clear, timestamped output
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def verify_npu_offload():
    """
    A minimal, isolated test to verify if openvino-whisper can successfully
    load a model and offload it to the NPU via the "AUTO" device specifier.
    This removes all complexity from jarvis_main.py to isolate the root cause.
    """
    logger.info("--- Starting NPU Verification Test ---")

    try:
        # Step 1: Attempt to load the model using "AUTO" device selection.
        # This is the exact operation that fails inside jarvis_main.py.
        logger.info("Attempting to load Whisper 'base' model with device='AUTO'...")
        model = whisper.load_model("base", device="AUTO")

        # Step 2: If successful, check the device the model was actually loaded on.
        # For your hardware, we expect this to be 'NPU'.
        device = model.device
        logger.info("✅ SUCCESS: Model loaded successfully.")
        logger.info(f"✅ Detected Device: {device}")

        if "NPU" in str(device).upper():
            logger.info("✅ VERIFIED: The model has been successfully offloaded to the NPU.")
        elif "CPU" in str(device).upper():
            logger.warning("⚠️  WARNING: Model loaded on CPU. NPU was not selected by the AUTO device plugin.")
            logger.warning("   This means transcription will work, but without NPU acceleration.")
        else:
            logger.warning(f"⚠️  WARNING: Model loaded on an unexpected device: {device}.")

    except RuntimeError as e:
        # Step 3: If the RuntimeError occurs, we have isolated the problem.
        logger.error("❌ FAILURE: The exact same RuntimeError occurred in isolation.")
        logger.error(f"   Error: {e}")
        logger.error("---")
        logger.error("CONCLUSION: This confirms the issue is not with jarvis_main.py, but with the underlying")
        logger.error("            openvino-whisper library, PyTorch, or the NPU driver installation.")
        logger.error("            The library is failing to correctly handle the 'AUTO' device tag on your system.")
        return False

    except Exception as e:
        logger.error("❌ FAILURE: An unexpected error occurred during model loading.", exc_info=True)
        return False

    return True

if __name__ == "__main__":
    verify_npu_offload()