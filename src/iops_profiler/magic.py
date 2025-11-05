"""
IPython magic module for IOPS Profiler.

This module contains the IPython magic command integration and orchestration:
- IOPSProfiler magics class
- Line/cell magic command handling
- Extension loading/unloading
- Coordination between data collection and display modules
"""

import sys
import re
from IPython.core.magic import Magics, magics_class, line_cell_magic

from . import collector
from . import display


@magics_class
class IOPSProfiler(Magics):
    
    def __init__(self, shell):
        super().__init__(shell)
        self.platform = sys.platform
        # Compile regex patterns for better performance
        # Pattern matches: PID syscall(args) = result
        # This pattern skips unfinished/resumed calls as they don't have complete results yet
        self._strace_pattern = re.compile(r'^\s*(\d+)\s+(\w+)\([^)]+\)\s*=\s*(-?\d+)')
        # Set of syscall names for I/O operations (lowercase)
        self._io_syscalls = set(collector.STRACE_IO_SYSCALLS)
    
    def _parse_fs_usage_line(self, line, collect_ops=False):
        """Parse a single fs_usage output line for I/O operations
        
        This is a compatibility wrapper that delegates to the collector module.
        
        Args:
            line: The line to parse
            collect_ops: If True, return full operation info for histogram collection
        
        Returns:
            If collect_ops is False: (op_type, bytes_transferred)
            If collect_ops is True: {'type': op_type, 'bytes': bytes_transferred}
        """
        return collector.parse_fs_usage_line(line, collect_ops)
    
    def _parse_strace_line(self, line, collect_ops=False):
        """Parse a single strace output line for I/O operations
        
        This is a compatibility wrapper that delegates to the collector module.
        
        Args:
            line: The line to parse
            collect_ops: If True, return full operation info for histogram collection
        
        Returns:
            If collect_ops is False: (op_type, bytes_transferred)
            If collect_ops is True: {'type': op_type, 'bytes': bytes_transferred}
        """
        return collector.parse_strace_line(line, self._strace_pattern, self._io_syscalls, collect_ops)
    
    def _create_helper_script(self, pid, output_file, control_file):
        """Create a bash helper script that runs fs_usage with elevated privileges
        
        This is a compatibility wrapper that delegates to the collector module.
        """
        return collector.create_helper_script(pid, output_file, control_file)
    
    def _launch_helper_via_osascript(self, helper_script_path):
        """Launch helper script with sudo via osascript (prompts for password)
        
        This is a compatibility wrapper that delegates to the collector module.
        """
        return collector.launch_helper_via_osascript(helper_script_path)
    
    def _measure_macos_osascript(self, code, collect_ops=False):
        """Measure IOPS on macOS using fs_usage via osascript
        
        This is a compatibility wrapper that delegates to the collector module.
        
        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram
        """
        return collector.measure_macos_osascript(self.shell, code, collect_ops)
    
    def _measure_linux_strace(self, code, collect_ops=False):
        """Measure IOPS on Linux using strace (no elevated privileges required)
        
        This is a compatibility wrapper that delegates to the collector module.
        
        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram
        """
        return collector.measure_linux_strace(self.shell, self._strace_pattern, self._io_syscalls, code, collect_ops)
    
    def _measure_linux_windows(self, code):
        """Measure IOPS on Linux/Windows using psutil
        
        This is a compatibility wrapper that delegates to the collector module.
        """
        return collector.measure_linux_windows(self.shell, code)
    
    def _measure_systemwide_fallback(self, code):
        """Fallback: system-wide I/O measurement using psutil
        
        This is a compatibility wrapper that delegates to the collector module.
        """
        return collector.measure_systemwide_fallback(self.shell, code)
    
    def _is_notebook_environment(self):
        """Detect if running in a graphical notebook environment vs plain IPython.
        
        This is a compatibility wrapper that delegates to the display module.
        
        Returns:
            bool: True if in a notebook with display capabilities, False for plain IPython
        """
        return display.is_notebook_environment()
    
    def _format_bytes(self, bytes_val):
        """Format bytes into human-readable string
        
        This is a compatibility wrapper that delegates to the display module.
        """
        return display.format_bytes(bytes_val)
    
    def _generate_histograms(self, operations):
        """Generate histograms for I/O operations using numpy
        
        This is a compatibility wrapper that delegates to the display module.
        
        Args:
            operations: List of dicts with 'type' and 'bytes' keys
        """
        return display.generate_histograms(operations)
    
    def _display_results_plain_text(self, results):
        """Display results in plain text format for terminal/console environments.
        
        This is a compatibility wrapper that delegates to the display module.
        
        Args:
            results: Dictionary containing profiling results
        """
        return display.display_results_plain_text(results)
    
    def _display_results_html(self, results):
        """Display results in HTML format for notebook environments.
        
        This is a compatibility wrapper that delegates to the display module.
        
        Args:
            results: Dictionary containing profiling results
        """
        return display.display_results_html(results)
    
    def _display_results(self, results):
        """Display results in appropriate format based on environment.
        
        This is a compatibility wrapper that delegates to the display module.
        
        Args:
            results: Dictionary containing profiling results
        """
        if self._is_notebook_environment():
            self._display_results_html(results)
        else:
            self._display_results_plain_text(results)
    
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
        # Only collect for strace/fs_usage modes where detailed data is available
        collect_ops = show_histogram
        
        # Determine measurement method based on platform
        if self.platform == 'darwin':  # macOS
            try:
                results = self._measure_macos_osascript(code, collect_ops=collect_ops)
            except RuntimeError as e:
                if 'Resource busy' in str(e):
                    print("⚠️ ktrace is busy. Falling back to system-wide measurement.")
                    print("Tip: Try running 'sudo killall fs_usage' and retry.\n")
                    results = self._measure_systemwide_fallback(code)
                    if show_histogram:
                        print("⚠️ Histograms not available for system-wide measurement mode.")
                else:
                    print(f"⚠️ Could not start fs_usage: {e}")
                    print("Falling back to system-wide measurement.\n")
                    results = self._measure_systemwide_fallback(code)
                    if show_histogram:
                        print("⚠️ Histograms not available for system-wide measurement mode.")
        
        elif self.platform in ('linux', 'linux2'):
            # Use strace on Linux (no elevated privileges required)
            try:
                results = self._measure_linux_strace(code, collect_ops=collect_ops)
            except (RuntimeError, FileNotFoundError) as e:
                print(f"⚠️ Could not use strace: {e}")
                print("Falling back to psutil per-process measurement.\n")
                results = self._measure_linux_windows(code)
                if show_histogram:
                    print("⚠️ Histograms not available for psutil measurement mode.")
        
        elif self.platform == 'win32':
            results = self._measure_linux_windows(code)
            if show_histogram:
                print("⚠️ Histograms not available for psutil measurement mode on Windows.")
        
        else:
            print(f"⚠️ Platform '{self.platform}' not fully supported.")
            print("Attempting system-wide measurement as fallback.\n")
            results = self._measure_systemwide_fallback(code)
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
            # For line magic, check if --histogram appears at the start
            # For cell magic, check if --histogram is in the line parameter (not the cell)
            show_histogram = False
            code = None
            
            # Determine what code to execute
            if cell is None:
                # Line magic mode - code is in the line parameter
                # Check if line starts with --histogram flag (as a complete token)
                line_stripped = line.strip()
                if line_stripped == '--histogram' or line_stripped.startswith('--histogram '):
                    show_histogram = True
                    # Remove the --histogram prefix and any following whitespace
                    code = line_stripped[len('--histogram'):].strip()
                else:
                    code = line_stripped
                
                if not code:
                    print("❌ Error: No code provided to profile in line magic mode.")
                    print("   Usage: %iops [--histogram] <code>")
                    return
            else:
                # Cell magic mode - code is in the cell parameter
                # Check if --histogram flag is in the line parameter
                show_histogram = '--histogram' in line
                code = cell
            
            # Profile the code
            results = self._profile_code(code, show_histogram)
            
            # Display results table
            self._display_results(results)
            
            # Display histograms if requested and available
            if show_histogram and 'operations' in results:
                self._generate_histograms(results['operations'])
        
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
