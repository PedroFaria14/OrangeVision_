"""Detecção limitada a um quadro pendente; resultados preservam sua imagem de origem."""

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionSnapshot:
    sequence: int
    frame: object
    captured_at: str
    captured_monotonic: float
    detection: dict
    completed_at: float

    def fresh(self, now):
        return now - self.completed_at <= 2 and now - self.captured_monotonic <= 10


class LiveDetection:
    def __init__(self, detector, interval=0.5):
        self.detector = detector
        self.interval = interval
        self.condition = threading.Condition()
        self.pending = None
        self.result = None
        self.error = None
        self.sequence = 0
        self.generation = 0
        self.stopping = False
        self.thread = threading.Thread(target=self._run, name='orangevision-detect', daemon=True)

    def start(self):
        self.thread.start()

    def submit(self, frame, captured_at, now):
        with self.condition:
            self.sequence += 1
            self.pending = (self.sequence, frame.copy(), captured_at, now, self.generation)
            self.condition.notify()
            return self.sequence

    def latest(self):
        with self.condition:
            return self.result, self.error

    def reset(self):
        with self.condition:
            self.generation += 1
            self.pending = self.result = self.error = None

    def close(self):
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
        self.thread.join()

    def _run(self):
        next_start = 0
        while True:
            with self.condition:
                while not self.stopping:
                    delay = next_start - time.monotonic()
                    if self.pending is not None and delay <= 0:
                        break
                    self.condition.wait(timeout=max(0.001, delay) if self.pending else None)
                if self.stopping:
                    return
                sequence, frame, stamp, captured, generation = self.pending
                self.pending = None
            next_start = time.monotonic() + self.interval
            try:
                detection = self.detector.detect(frame)
            except Exception as exc:
                with self.condition:
                    if generation == self.generation:
                        self.result = None
                        self.error = exc
                        self.condition.notify_all()
            else:
                snapshot = DetectionSnapshot(
                    sequence, frame, stamp, captured, detection, time.monotonic()
                )
                with self.condition:
                    if generation == self.generation:
                        self.result, self.error = snapshot, None
                        self.condition.notify_all()
