"""Main loop: GPIO access on one thread, MQTT callback only queues commands."""
import queue
import time
from config import DISTANCE_THRESHOLD_CM, SEND_INTERVAL
from sensors import Sensors
from motor import Motor
from mqtt_client import ThingsBoardClient


def execute_rpc(request_id, request, motor, tb):
    method = request.get('method')
    try:
        if method != 'setStepperRunning':
            raise ValueError('Unknown RPC method: ' + str(method))
        params = request.get('params')
        running = params.get('running') if isinstance(params, dict) else params
        motor.set_running(running)
        tb.reply(request_id, {'success': True, 'running': running})
        print('[RPC] Stepper override:', 'running' if running else 'stopped')
    except (ValueError, TypeError) as exc:
        tb.reply(request_id, {'success': False, 'error': str(exc)})
        print('[RPC] Rejected:', exc)


def main():
    commands = queue.Queue(maxsize=100)
    sensors = Sensors()
    motor = Motor()
    tb = ThingsBoardClient(commands)
    try:
        tb.start()
        next_read = time.monotonic()
        print('Lab01 started. Ctrl+C to exit.')
        while True:
            try:
                request_id, request = commands.get(timeout=0.01)
                execute_rpc(request_id, request, motor, tb)
            except queue.Empty:
                pass

            now = time.monotonic()
            if now >= next_read:
                data = sensors.read()
                if data:
                    distance = data.get('distance')
                    motor.set_running(
                        distance is not None and
                        distance < DISTANCE_THRESHOLD_CM)
                    data['motorRunning'] = motor.running
                    data['stepperPosition'] = motor.step_once()
                    tb.telemetry(data)
                    print('[SENSOR]', data)
                else:
                    motor.set_running(False)
                next_read = now + SEND_INTERVAL
            elif motor.running:
                motor.step_once()
    except KeyboardInterrupt:
        print('\nStopping...')
    finally:
        tb.close()
        motor.close()
        sensors.close()


if __name__ == '__main__':
    main()
