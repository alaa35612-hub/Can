"""Causal, stateful detector for Binance Futures upside precursor research."""
from .config import ScannerConfig
from .detector import CausalUpsideDetector
from .models import MarketBar, SignalAssessment

__all__ = ["CausalUpsideDetector", "MarketBar", "ScannerConfig", "SignalAssessment"]
__version__ = "1.0.0"
