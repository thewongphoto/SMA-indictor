"""Elapsed-time phases for the upward-crossing logo, shared by native UI checks."""
from dataclasses import dataclass

LOGO_PERIOD = 1.4
DRAW_SECONDS = 1.0
CROSSING_SECONDS = .5


@dataclass(frozen=True)
class LogoFrame:
    progress: float
    plus_opacity: float
    opacity: float


def logo_frame(elapsed):
    phase = max(0, elapsed) % LOGO_PERIOD
    progress = min(1, phase / DRAW_SECONDS)
    pop = min(1, max(0, (phase-CROSSING_SECONDS)/.12))
    plus = pop * pop * (3-2*pop)
    opacity = 1-min(1, max(0, (phase-1.18)/.12))
    return LogoFrame(progress, plus, opacity)
