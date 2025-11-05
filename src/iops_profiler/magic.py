"""
IPython magic module for IOPS Profiler.

This module contains the IPython magic command integration and orchestration:
- IOPSProfiler magics class
- Line/cell magic command handling
- Extension loading/unloading
- Coordination between data collection and display modules
"""

import sys

from IPython.core.magic import Magics, line_cell_magic, magics_class

from . import display
from .collector import Collector


@magics_class
class IOPSProfiler(Magics):
    """IPython magic commands for profiling I/O operations per second (IOPS).

    Provides %iops (line magic) and %%iops (cell magic) commands to measure
    I/O performance of Python code in Jupyter notebooks.
    """

    def __init__(self, shell):
        super().__init__(shell)
        self.platform = sys.platform
        # Initialize the collector with shell context
        self.collector = Collector(shell)

    def _profile_code(self, code, show_histogram=False):
        """
        Internal method to profile code with I/O measurements.

        Args:
            code: The code string to profile
            show_histogram: Whether to generate histograms

        Returns:
            Dictionary with profiling results
        """
        # Determine if we should collect individual operations
        collect_ops = show_histogram

        # Determine measurement method based on platform
        if self.platform == "darwin":  # macOS
            try:
                results = self.collector.measure_macos_osascript(code, collect_ops=collect_ops)
            except RuntimeError as e:
                if "Resource busy" in str(e):
                    print("⚠️ ktrace is busy. Falling back to system-wide measurement.")
                    print("Tip: Try running 'sudo killall fs_usage' and retry.\n")
                    results = self.collector.measure_systemwide_fallback(code)
                    if show_histogram:
                        print("⚠️ Histograms not available for system-wide measurement mode.")
                else:
                    print(f"⚠️ Could not start fs_usage: {e}")
                    print("Falling back to system-wide measurement.\n")
                    results = self.collector.measure_systemwide_fallback(code)
                    if show_histogram:
                        print("⚠️ Histograms not available for system-wide measurement mode.")

        elif self.platform in ("linux", "linux2"):
            # Use strace on Linux (no elevated privileges required)
            try:
                results = self.collector.measure_linux_strace(code, collect_ops=collect_ops)
            except (RuntimeError, FileNotFoundError) as e:
                print(f"⚠️ Could not use strace: {e}")
                print("Falling back to psutil per-process measurement.\n")
                results = self.collector.measure_linux_windows(code)
                if show_histogram:
                    print("⚠️ Histograms not available for psutil measurement mode.")

        elif self.platform == "win32":
            results = self.collector.measure_linux_windows(code)
            if show_histogram:
                print("⚠️ Histograms not available for psutil measurement mode on Windows.")

        else:
            print(f"⚠️ Platform '{self.platform}' not fully supported.")
            print("Attempting system-wide measurement as fallback.\n")
            results = self.collector.measure_systemwide_fallback(code)
            if show_histogram:
                print("⚠️ Histograms not available for system-wide measurement mode.")

        return results

    @line_cell_magic
    def iops(self, line, cell=None):
        """
        Measure I/O operations per second for code.

        Line magic usage (single line):
            %iops open('test.txt', 'w').write('data')
            %iops --histogram open('test.txt', 'w').write('data')

        Cell magic usage (multiple lines):
            %%iops
            # Your code here
            with open('test.txt', 'w') as f:
                f.write('data')

            %%iops --histogram
            # Your code here (with histograms)
            with open('test.txt', 'w') as f:
                f.write('data')
        """
        try:
            # Parse command line arguments
            show_histogram = False
            code = None

            # Determine what code to execute
            if cell is None:
                # Line magic mode - code is in the line parameter
                line_stripped = line.strip()
                if line_stripped == "--histogram" or line_stripped.startswith("--histogram "):
                    show_histogram = True
                    code = line_stripped[len("--histogram") :].strip()
                else:
                    code = line_stripped

                if not code:
                    print("❌ Error: No code provided to profile in line magic mode.")
                    print("   Usage: %iops [--histogram] <code>")
                    return
            else:
                # Cell magic mode - code is in the cell parameter
                show_histogram = "--histogram" in line
                code = cell

            # Profile the code
            results = self._profile_code(code, show_histogram)

            # Display results table
            display.display_results(results)

            # Display histograms if requested and available
            if show_histogram and "operations" in results:
                display.generate_histograms(results["operations"])

        except Exception as e:
            print(f"❌ Error during IOPS profiling: {e}")
            print("\nYour code was not executed. Please fix the profiling issue and try again.")
            raise


def load_ipython_extension(ipython):
    """Load the extension"""
    ipython.register_magics(IOPSProfiler)


def unload_ipython_extension(ipython):
    """Unload the extension"""
    pass
