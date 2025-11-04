"""
IOPS Profiler - Jupyter Magic for measuring I/O operations per second
"""

__version__ = "0.1.0"

from .iops_profiler import IOPSProfiler, load_ipython_extension, unload_ipython_extension

__all__ = ["IOPSProfiler", "load_ipython_extension", "unload_ipython_extension", "__version__"]
