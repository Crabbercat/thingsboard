import os

TB_HOST = os.getenv('TB_HOST', 'demo.thingsboard.io')
TB_PORT = int(os.getenv('TB_PORT', '8883'))
TB_TOKEN = os.getenv('TB_TOKEN', '')
SEND_INTERVAL = float(os.getenv('SEND_INTERVAL', '2'))
DHT_PIN = 4
TRIGGER_PIN = 23
ECHO_PIN = 24

# ULN2003A: IN1..IN4 are connected to the four inputs on the driver board.
STEPPER_PINS = tuple(int(pin) for pin in os.getenv(
    'STEPPER_PINS', '5,6,13,19').split(','))
STEP_DELAY = float(os.getenv('STEP_DELAY', '0.003'))
MAX_STEPS_PER_COMMAND = int(os.getenv('MAX_STEPS_PER_COMMAND', '10000'))
DISTANCE_THRESHOLD_CM = float(os.getenv('DISTANCE_THRESHOLD_CM', '20'))
