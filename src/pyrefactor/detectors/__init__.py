"""Detector modules for PyRefactor."""

from .boolean_logic import BooleanLogicDetector
from .comparisons import ComparisonsDetector
from .complexity import ComplexityDetector
from .context_manager import ContextManagerDetector
from .control_flow import ControlFlowDetector
from .dict_operations import DictOperationsDetector
from .duplication import DuplicationDetector
from .loops import LoopsDetector
from .performance import PerformanceDetector

__all__ = [
    "BooleanLogicDetector",
    "ComparisonsDetector",
    "ComplexityDetector",
    "ContextManagerDetector",
    "ControlFlowDetector",
    "DictOperationsDetector",
    "DuplicationDetector",
    "LoopsDetector",
    "PerformanceDetector",
]
