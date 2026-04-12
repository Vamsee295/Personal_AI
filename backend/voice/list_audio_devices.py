import pyaudio
import sys

def list_devices():
    print(f"Python: {sys.version}")
    try:
        pa = pyaudio.PyAudio()
        info = pa.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        print(f"Found {numdevices} devices total.")
        
        for i in range(0, numdevices):
            device_info = pa.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"INPUT DEVICE: ID {i} - {device_info.get('name')} (Channels: {device_info.get('maxInputChannels')})")
        
        try:
            default_in = pa.get_default_input_device_info()
            print(f"DEFAULT INPUT DEVICE: ID {default_in['index']} - {default_in['name']}")
        except Exception as e:
            print(f"No default input device: {e}")
            
    except Exception as e:
        print(f"PyAudio Init Failed: {e}")

if __name__ == "__main__":
    list_devices()
