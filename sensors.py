"""Read HC-SR04 on Raspberry Pi (BCM numbering)."""
from gpiozero import DistanceSensor
from config import TRIGGER_PIN, ECHO_PIN

class Sensors:
    def __init__(self):
        self.ultrasonic = DistanceSensor(echo=ECHO_PIN, trigger=TRIGGER_PIN,
                                         max_distance=4, queue_len=5)

    def read(self):
        result = {}
        try:
            result['distance'] = round(self.ultrasonic.distance * 100, 1)
        except Exception as exc:
            print('[HC-SR04] Read failed:', exc)
        return result
    def close(self):
    def close(self):
        self.ultrasonic.close()
