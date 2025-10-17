"""Detector modules for PyRefactor."""

from .boolean_logic import BooleanLogicDetector
from .complexity import ComplexityDetector
from .duplication import DuplicationDetector
from .loops import LoopsDetector
from .performance import PerformanceDetector

__all__ = [
    "ComplexityDetector",
    "PerformanceDetector",
    "DuplicationDetector",
    "BooleanLogicDetector",
    "LoopsDetector",
]

