"""
IOPS Profiler - Jupyter Magic for measuring I/O operations per second
"""

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0+unknown"

from .magic import IOPSProfiler, load_ipython_extension, unload_ipython_extension

__all__ = ["__version__", "IOPSProfiler", "load_ipython_extension", "unload_ipython_extension"]
