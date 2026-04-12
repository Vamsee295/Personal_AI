import sys
import os

print(f"Python Version: {sys.version}")
print(f"CWD: {os.getcwd()}")

print("\n--- Package Check ---")
try:
    import pyttsx3
    print("✅ pyttsx3 is installed")
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print(f"✅ pyttsx3 init success. Found {len(voices)} voices.")
except Exception as e:
    print(f"❌ pyttsx3 failure: {e}")

try:
    import speech_recognition as sr
    print("✅ speech_recognition is installed")
except Exception as e:
    print(f"❌ speech_recognition failure: {e}")

try:
    import faster_whisper
    print("✅ faster_whisper is installed")
except Exception as e:
    print(f"❌ faster_whisper failure: {e}")

try:
    import pyaudio
    print("✅ pyaudio is installed")
    pa = pyaudio.PyAudio()
    print("\n--- Audio Devices ---")
    info = pa.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if (pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print(f"Input Device ID {i} - {pa.get_device_info_by_host_api_device_index(0, i).get('name')}")
    
    try:
        default_in = pa.get_default_input_device_info()
        print(f"\nDefault Input Device: ID {default_in['index']} - {default_in['name']}")
    except Exception as e:
        print(f"❌ Could not get default input device: {e}")

except Exception as e:
    print(f"❌ pyaudio failure: {e}")

print("\n--- Selenium Check ---")
try:
    from selenium import webdriver
    print("✅ selenium is installed")
except Exception as e:
    print(f"❌ selenium failure: {e}")
