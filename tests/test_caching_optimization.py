"""Test caching optimization for sanitize_for_speech and extract_sender_name."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from jarvis_main import JarvisGT2
import time

print("\n" + "="*60)
print("  CACHING OPTIMIZATION TEST")
print("="*60)

# Test 1: extract_sender_name caching
print("\n1. Testing extract_sender_name caching...")
sender = "John Doe <john.doe@example.com>"

# First call (cache miss)
start = time.time()
for _ in range(10000):
    result1 = JarvisGT2.extract_sender_name(sender)
first_call_time = time.time() - start

# Second call (cache hit)
start = time.time()
for _ in range(100000):
    result2 = JarvisGT2.extract_sender_name(sender)
cached_call_time = time.time() - start

print(f"   Result: '{result1}'")
print(f"   10K calls: {first_call_time*1000:.3f}ms")
print(f"   100K cached calls: {cached_call_time*1000:.3f}ms")
if cached_call_time > 0:
    print(f"   Speedup: {first_call_time / cached_call_time:.1f}x faster")
else:
    print(f"   ✓ Cache is extremely fast (sub-millisecond)")

# Test 2: sanitize_for_speech caching
print("\n2. Testing sanitize_for_speech caching...")
text = "Hello **World** with `code` and @mentions and more text!"

# First call (cache miss)
start = time.time()
for _ in range(10000):
    result1 = JarvisGT2.sanitize_for_speech(text)
first_call_time = time.time() - start

# Second call (cache hit)
start = time.time()
for _ in range(100000):
    result2 = JarvisGT2.sanitize_for_speech(text)
cached_call_time = time.time() - start

print(f"   Result: '{result1}'")
print(f"   10K calls: {first_call_time*1000:.3f}ms")
print(f"   100K cached calls: {cached_call_time*1000:.3f}ms")
if cached_call_time > 0:
    print(f"   Speedup: {first_call_time / cached_call_time:.1f}x faster")
else:
    print(f"   ✓ Cache is extremely fast (sub-millisecond)")

# Test 3: Cache info
print("\n3. Cache Statistics:")
info1 = JarvisGT2.extract_sender_name.cache_info()
info2 = JarvisGT2.sanitize_for_speech.cache_info()
print(f"   extract_sender_name: {info1.hits} hits, {info1.misses} misses (hit rate: {info1.hits/(info1.hits+info1.misses)*100:.1f}%)")
print(f"   sanitize_for_speech: {info2.hits} hits, {info2.misses} misses (hit rate: {info2.hits/(info2.hits+info2.misses)*100:.1f}%)")

print("\n" + "="*60)
print("✓ Caching optimization verified - functions are cached!")
print("="*60)
