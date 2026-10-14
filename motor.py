"""Four-wire stepper driver through a ULN2003A board."""
import time
from gpiozero import OutputDevice
from config import STEP_DELAY, STEPPER_PINS


class Motor:
    def __init__(self):
        if len(STEPPER_PINS) != 4 or len(set(STEPPER_PINS)) != 4:
            raise ValueError('STEPPER_PINS must contain four unique GPIO pins')
        if STEP_DELAY <= 0:
            raise ValueError('STEP_DELAY must be greater than zero')
        self.coils = [OutputDevice(pin, initial_value=False)
                      for pin in STEPPER_PINS]
        self.position = 0
        self.sequence_index = 0
        self.running = False

    # Four-phase sequence for a 28BYJ-48 motor and ULN2003A board.
    sequence = (
        (1, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
    )

    def set_running(self, running):
        if not isinstance(running, bool):
            raise ValueError('Running must be a boolean')
        self.running = running
        if not running:
            self._release()

    def step_once(self):
        if not self.running:
            return self.position
        self.sequence_index = (self.sequence_index + 1) % len(self.sequence)
        self._write_step(self.sequence[self.sequence_index])
        self.position += 1
        time.sleep(STEP_DELAY)
        return self.position

    def _write_step(self, values):
        for coil, value in zip(self.coils, values):
            coil.value = value

    def _release(self):
        for coil in self.coils:
            coil.off()

    def close(self):
        self._release()
        for coil in self.coils:
            coil.close()
