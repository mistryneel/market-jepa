"""mjepa_harness: point-in-time research harness for the market-jepa paper.

The package is deliberately *not* called ``market_jepa``: the Market-1T authors'
code uses that module name and we may install it alongside this harness.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mjepa-harness")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled tree
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
