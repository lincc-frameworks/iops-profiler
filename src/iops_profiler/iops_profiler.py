"""
IOPS Profiler - Jupyter Magic for measuring I/O operations per second

Usage:
    %load_ext iops_profiler
    %%iops
    # Your code here
    with open('test.txt', 'w') as f:
        f.write('Hello World')
"""

import os
import sys
import time
import re
import subprocess
import tempfile
from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.display import display, HTML

try:
    import psutil
except ImportError:
    psutil = None

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    plt = None
    np = None

# Timing constants for strace attachment and capture
STRACE_ATTACH_DELAY = 0.5  # seconds to wait for strace to attach to process
STRACE_CAPTURE_DELAY = 0.5  # seconds to wait for strace to capture final I/O

# I/O syscalls to trace with strace
STRACE_IO_SYSCALLS = [
    'read', 'write',           # Basic I/O
    'pread64', 'pwrite64',     # Positional I/O
    'readv', 'writev',         # Vectored I/O
    'preadv', 'pwritev',       # Positional vectored I/O
    'preadv2', 'pwritev2',     # Extended vectored I/O
]


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
        self._io_syscalls = set(STRACE_IO_SYSCALLS)
        
    def _measure_linux_windows(self, code, collect_ops=False):
        """Measure IOPS on Linux/Windows using psutil
        
        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram (Windows only)
        """
        if not psutil:
            raise RuntimeError("psutil not installed. Run: pip install psutil")
        
        process = psutil.Process()
        
        # Get initial I/O counters
        try:
            io_before = process.io_counters()
        except AttributeError:
            raise RuntimeError(f"psutil.Process.io_counters() not supported on {self.platform}")
        
        # On Windows, use Python-level I/O tracking if granular data is requested
        if collect_ops and self.platform == 'win32':
            return self._measure_windows_python_io(code, io_before)
        
        # Execute the code
        start_time = time.time()
        self.shell.run_cell(code)
        elapsed_time = time.time() - start_time
        
        # Get final I/O counters
        io_after = process.io_counters()
        
        # Calculate differences
        read_count = io_after.read_count - io_before.read_count
        write_count = io_after.write_count - io_before.write_count
        read_bytes = io_after.read_bytes - io_before.read_bytes
        write_bytes = io_after.write_bytes - io_before.write_bytes
        
        return {
            'read_count': read_count,
            'write_count': write_count,
            'read_bytes': read_bytes,
            'write_bytes': write_bytes,
            'elapsed_time': elapsed_time,
            'method': 'psutil (per-process)'
        }
    
    def _measure_windows_python_io(self, code, io_before):
        """Measure IOPS on Windows with Python-level I/O tracking for granular data
        
        This method intercepts Python's built-in open() function to track individual
        read and write operations at the Python level.
        
        Note: Only captures Python-level I/O (open/read/write), not native C extensions.
        
        Args:
            code: The code to profile
            io_before: Initial psutil I/O counters for verification
        """
        operations = []
        
        # Import builtins to patch open()
        import builtins
        
        original_open = builtins.open
        
        class IOTracker:
            """Wrapper to track I/O operations on file objects"""
            def __init__(self, file_obj, mode):
                self.file = file_obj
                self.mode = mode
                
            def read(self, size=-1):
                result = self.file.read(size)
                if result:
                    bytes_read = len(result) if isinstance(result, (bytes, str)) else 0
                    if bytes_read > 0:
                        operations.append({'type': 'read', 'bytes': bytes_read})
                return result
            
            def readline(self, size=-1):
                result = self.file.readline(size)
                if result:
                    bytes_read = len(result) if isinstance(result, (bytes, str)) else 0
                    if bytes_read > 0:
                        operations.append({'type': 'read', 'bytes': bytes_read})
                return result
            
            def readlines(self, hint=-1):
                result = self.file.readlines(hint)
                if result:
                    total_bytes = sum(len(line) for line in result)
                    if total_bytes > 0:
                        # Record as individual operations to better reflect actual I/O
                        for line in result:
                            if line:
                                operations.append({'type': 'read', 'bytes': len(line)})
                return result
            
            def write(self, data):
                result = self.file.write(data)
                bytes_written = len(data) if isinstance(data, (bytes, str)) else 0
                if bytes_written > 0:
                    operations.append({'type': 'write', 'bytes': bytes_written})
                return result
            
            def writelines(self, lines):
                result = self.file.writelines(lines)
                # Record as individual operations
                for line in lines:
                    if line:
                        bytes_written = len(line) if isinstance(line, (bytes, str)) else 0
                        if bytes_written > 0:
                            operations.append({'type': 'write', 'bytes': bytes_written})
                return result
            
            def __enter__(self):
                # Return self to allow our wrapper methods to be used
                # The wrapped file's __enter__ is called automatically on the underlying file
                self.file.__enter__()
                return self
            
            def __exit__(self, *args):
                return self.file.__exit__(*args)
            
            def __iter__(self):
                return self
            
            def __next__(self):
                # Let StopIteration propagate naturally
                line = self.file.__next__()
                # Track the operation only if successful
                if line:
                    bytes_read = len(line) if isinstance(line, (bytes, str)) else 0
                    if bytes_read > 0:
                        operations.append({'type': 'read', 'bytes': bytes_read})
                return line
            
            def close(self):
                """Close the file"""
                return self.file.close()
            
            def flush(self):
                """Flush the file buffer"""
                return self.file.flush()
            
            def seek(self, offset, whence=0):
                """Seek to a position in the file"""
                return self.file.seek(offset, whence)
            
            def tell(self):
                """Return current file position"""
                return self.file.tell()
            
            def __getattr__(self, name):
                """Fallback for any other file methods"""
                return getattr(self.file, name)
        
        def tracked_open(file, mode='r', *args, **kwargs):
            """Wrapper for open() that tracks I/O operations"""
            file_obj = original_open(file, mode, *args, **kwargs)
            # Only track readable/writable files
            if 'r' in mode or 'w' in mode or 'a' in mode or '+' in mode:
                return IOTracker(file_obj, mode)
            return file_obj
        
        try:
            # Install the tracking wrapper in builtins
            builtins.open = tracked_open
            
            # Also inject into the IPython namespace to ensure it's used
            # Save whether 'open' was already in the namespace
            had_open_in_ns = 'open' in self.shell.user_ns
            shell_open = self.shell.user_ns.get('open') if had_open_in_ns else None
            self.shell.user_ns['open'] = tracked_open
            
            # Execute the code
            start_time = time.time()
            self.shell.run_cell(code)
            elapsed_time = time.time() - start_time
            
        finally:
            # Restore original open in both places
            builtins.open = original_open
            # Restore the IPython namespace
            if had_open_in_ns and shell_open is not None:
                self.shell.user_ns['open'] = shell_open
            else:
                # Remove 'open' from namespace if it wasn't there before
                self.shell.user_ns.pop('open', None)
        
        # Get final I/O counters for aggregate counts
        process = psutil.Process()
        io_after = process.io_counters()
        
        # Calculate aggregate differences from psutil
        read_count = io_after.read_count - io_before.read_count
        write_count = io_after.write_count - io_before.write_count
        read_bytes = io_after.read_bytes - io_before.read_bytes
        write_bytes = io_after.write_bytes - io_before.write_bytes
        
        # If we captured operations, use them; otherwise fall back to psutil counts
        if operations:
            # Count operations from our tracker
            tracked_read_count = sum(1 for op in operations if op['type'] == 'read')
            tracked_write_count = sum(1 for op in operations if op['type'] == 'write')
            tracked_read_bytes = sum(op['bytes'] for op in operations if op['type'] == 'read')
            tracked_write_bytes = sum(op['bytes'] for op in operations if op['type'] == 'write')
            
            # Prefer tracked counts if available, fall back to psutil
            result_read_count = tracked_read_count if tracked_read_count > 0 else read_count
            result_write_count = tracked_write_count if tracked_write_count > 0 else write_count
            result_read_bytes = tracked_read_bytes if tracked_read_bytes > 0 else read_bytes
            result_write_bytes = tracked_write_bytes if tracked_write_bytes > 0 else write_bytes
        else:
            # No operations tracked, use psutil counts
            result_read_count = read_count
            result_write_count = write_count
            result_read_bytes = read_bytes
            result_write_bytes = write_bytes
        
        return {
            'read_count': result_read_count,
            'write_count': result_write_count,
            'read_bytes': result_read_bytes,
            'write_bytes': result_write_bytes,
            'elapsed_time': elapsed_time,
            'method': 'Python I/O tracking (per-operation)',
            'operations': operations
        }
    
    def _parse_fs_usage_line(self, line, collect_ops=False):
        """Parse a single fs_usage output line for I/O operations
        
        Args:
            line: The line to parse
            collect_ops: If True, return full operation info for histogram collection
        
        Returns:
            If collect_ops is False: (op_type, bytes_transferred)
            If collect_ops is True: {'type': op_type, 'bytes': bytes_transferred}
        """
        parts = line.split()
        if len(parts) < 2:
            return None if collect_ops else (None, 0)
        
        syscall = parts[1].lower()
        is_read = 'read' in syscall
        is_write = 'write' in syscall
        
        if not (is_read or is_write):
            return None if collect_ops else (None, 0)
        
        # Extract byte count from B=0x[hex] pattern
        byte_match = re.search(r'B=0x([0-9a-fA-F]+)', line)
        bytes_transferred = int(byte_match.group(1), 16) if byte_match else 0
        
        op_type = 'read' if is_read else 'write'
        
        if collect_ops:
            return {'type': op_type, 'bytes': bytes_transferred}
        return op_type, bytes_transferred
    
    def _parse_strace_line(self, line, collect_ops=False):
        """Parse a single strace output line for I/O operations
        
        Example strace lines:
        3385  write(3, "Hello World...", 1100) = 1100
        3385  read(3, "data", 4096) = 133
        3385  pread64(3, "...", 1024, 0) = 1024
        
        Note: Lines with <unfinished ...> or <... resumed> are not matched
        as they don't contain complete result information in a single line.
        
        Args:
            line: The line to parse
            collect_ops: If True, return full operation info for histogram collection
        
        Returns:
            If collect_ops is False: (op_type, bytes_transferred)
            If collect_ops is True: {'type': op_type, 'bytes': bytes_transferred}
        """
        # Match patterns like: PID syscall(fd, ..., size) = result
        match = self._strace_pattern.match(line)
        if not match:
            return None if collect_ops else (None, 0)
        
        pid, syscall, result = match.groups()
        syscall = syscall.lower()
        
        # Check if it's one of the I/O syscalls we're tracking
        if syscall not in self._io_syscalls:
            return None if collect_ops else (None, 0)
        
        # Determine if it's a read or write operation based on syscall name
        # All I/O syscalls we track contain either 'read' or 'write' in their name
        # (e.g., read, pread64, readv, write, pwrite64, writev)
        # Note: No standard syscalls contain both 'read' and 'write' in their names
        if 'read' in syscall:
            op_type = 'read'
        elif 'write' in syscall:
            op_type = 'write'
        else:
            return None if collect_ops else (None, 0)
        
        # The return value is the number of bytes transferred (or -1 on error)
        bytes_transferred = int(result)
        if bytes_transferred < 0:
            return None if collect_ops else (None, 0)
        
        if collect_ops:
            return {'type': op_type, 'bytes': bytes_transferred}
        return op_type, bytes_transferred
    
    def _create_helper_script(self, pid, output_file, control_file):
        """Create a bash helper script that runs fs_usage with elevated privileges"""
        script_content = f'''#!/bin/bash
PID={pid}
OUTPUT_FILE="{output_file}"
CONTROL_FILE="{control_file}"
ERROR_FILE="${{OUTPUT_FILE}}.err"

# Try to clean up any existing fs_usage processes first
killall -9 fs_usage 2>/dev/null
sleep 0.5

# Start fs_usage and capture stderr separately
fs_usage -f filesystem -w "$PID" > "$OUTPUT_FILE" 2> "$ERROR_FILE" &
FS_USAGE_PID=$!

# Give fs_usage a moment to initialize
sleep 1

if ! kill -0 "$FS_USAGE_PID" 2>/dev/null; then
    exit 1
fi

echo "$FS_USAGE_PID" > "${{CONTROL_FILE}}.pid"

# Wait for stop signal
while [ "$(cat "$CONTROL_FILE" 2>/dev/null)" != "STOP" ]; do
    if ! kill -0 "$FS_USAGE_PID" 2>/dev/null; then
        exit 1
    fi
    sleep 0.1
done

# Terminate fs_usage
kill -TERM "$FS_USAGE_PID" 2>/dev/null
sleep 0.5
if kill -0 "$FS_USAGE_PID" 2>/dev/null; then
    kill -9 "$FS_USAGE_PID" 2>/dev/null
fi

exit 0
'''
        return script_content
    
    def _launch_helper_via_osascript(self, helper_script_path):
        """Launch helper script with sudo via osascript (prompts for password)"""
        applescript = f'''
        do shell script "bash {helper_script_path}" with administrator privileges
        '''
        
        proc = subprocess.Popen(
            ['osascript', '-e', applescript],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proc
    
    def _measure_macos_osascript(self, code, collect_ops=False):
        """Measure IOPS on macOS using fs_usage via osascript
        
        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram
        """
        pid = os.getpid()
        
        # Create temporary files
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False).name
        control_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ctrl', delete=False).name
        helper_script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False).name
        
        try:
            # Write the helper script
            script_content = self._create_helper_script(pid, output_file, control_file)
            with open(helper_script, 'w') as f:
                f.write(script_content)
            os.chmod(helper_script, 0o755)
            
            # Initialize control file
            with open(control_file, 'w') as f:
                f.write("INIT")
            
            print("⚠️  A password dialog will appear - please enter your password to enable I/O monitoring.")
            
            # Launch helper via osascript
            helper_proc = self._launch_helper_via_osascript(helper_script)
            
            # Wait for fs_usage to be ready
            pid_file = f"{control_file}.pid"
            max_wait = 30
            waited = 0
            while not os.path.exists(pid_file) and waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                
                if helper_proc.poll() is not None:
                    raise RuntimeError("Helper script failed to start fs_usage (may be Resource busy)")
            
            if not os.path.exists(pid_file):
                raise RuntimeError("Timeout waiting for fs_usage to start")
            
            # Execute the code
            start_time = time.time()
            self.shell.run_cell(code)
            elapsed_time = time.time() - start_time
            
            # Give fs_usage a moment to capture final I/O
            time.sleep(0.5)
            
            # Signal helper to stop
            with open(control_file, 'w') as f:
                f.write("STOP")
            
            # Wait for helper to finish
            try:
                helper_proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                helper_proc.kill()
                helper_proc.wait()
            
            # Parse the output
            read_count = 0
            write_count = 0
            read_bytes = 0
            write_bytes = 0
            operations = [] if collect_ops else None
            
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    for line in f:
                        if collect_ops:
                            op = self._parse_fs_usage_line(line, collect_ops=True)
                            if op:
                                operations.append(op)
                                if op['type'] == 'read':
                                    read_count += 1
                                    read_bytes += op['bytes']
                                elif op['type'] == 'write':
                                    write_count += 1
                                    write_bytes += op['bytes']
                        else:
                            op_type, bytes_transferred = self._parse_fs_usage_line(line)
                            if op_type == 'read':
                                read_count += 1
                                read_bytes += bytes_transferred
                            elif op_type == 'write':
                                write_count += 1
                                write_bytes += bytes_transferred
            
            result = {
                'read_count': read_count,
                'write_count': write_count,
                'read_bytes': read_bytes,
                'write_bytes': write_bytes,
                'elapsed_time': elapsed_time,
                'method': 'fs_usage (per-process)'
            }
            
            if collect_ops:
                result['operations'] = operations
            
            return result
        
        finally:
            # Cleanup - try to kill fs_usage processes
            try:
                subprocess.run(['sudo', 'killall', '-9', 'fs_usage'], 
                             capture_output=True, timeout=2, check=False)
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass  # sudo or killall not available or timed out
            
            for filepath in [output_file, control_file, helper_script, 
                           f"{control_file}.pid", f"{output_file}.err"]:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except (OSError, IOError):
                    pass  # File already deleted or permission issue
    
    def _measure_linux_strace(self, code, collect_ops=False):
        """Measure IOPS on Linux using strace (no elevated privileges required)
        
        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram
        """
        pid = os.getpid()
        
        # Allow this process to be ptraced (required on systems with Yama LSM)
        # This is safe as we're only allowing our own strace process to trace us
        try:
            import ctypes
            import ctypes.util
            libc = ctypes.CDLL(ctypes.util.find_library('c'))
            # PR_SET_PTRACER is a prctl constant defined in Linux kernel headers
            # The value 0x59616d61 is the standard constant value for PR_SET_PTRACER
            # It's related to the Yama Linux Security Module (Yama LSM)
            PR_SET_PTRACER = 0x59616d61
            PR_SET_PTRACER_ANY = -1
            libc.prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0)
        except Exception:
            # If prctl fails, we'll try strace anyway - it might work on some systems
            pass
        
        # Create temporary file for strace output
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False).name
        
        try:
            # Start strace in the background
            # -f: follow forks
            # -e trace=...: only trace I/O syscalls
            # -o: output to file
            syscalls_to_trace = ','.join(STRACE_IO_SYSCALLS)
            strace_cmd = [
                'strace',
                '-f',  # Follow forks
                '-e', f'trace={syscalls_to_trace}',
                '-o', output_file,
                '-p', str(pid)
            ]
            
            # Start strace process
            strace_proc = subprocess.Popen(
                strace_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give strace a moment to attach
            time.sleep(STRACE_ATTACH_DELAY)
            
            # Check if strace started successfully
            if strace_proc.poll() is not None:
                stdout, stderr = strace_proc.communicate()
                if 'Operation not permitted' in stderr:
                    raise RuntimeError("strace failed - ptrace not permitted. This may be due to kernel security settings.")
                raise RuntimeError(f"Failed to start strace: {stderr}")
            
            # Execute the code
            start_time = time.time()
            self.shell.run_cell(code)
            elapsed_time = time.time() - start_time
            
            # Give strace a moment to capture final I/O
            time.sleep(STRACE_CAPTURE_DELAY)
            
            # Terminate strace
            strace_proc.terminate()
            try:
                strace_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                strace_proc.kill()
                strace_proc.wait()
            
            # Parse the output
            read_count = 0
            write_count = 0
            read_bytes = 0
            write_bytes = 0
            operations = [] if collect_ops else None
            
            if os.path.exists(output_file):
                try:
                    # strace output is ASCII-compatible, but use errors='ignore' for safety
                    # The 'ignore' mode silently skips any bytes that cannot be decoded
                    with open(output_file, 'r', errors='ignore') as f:
                        for line in f:
                            if collect_ops:
                                op = self._parse_strace_line(line, collect_ops=True)
                                if op:
                                    operations.append(op)
                                    if op['type'] == 'read':
                                        read_count += 1
                                        read_bytes += op['bytes']
                                    elif op['type'] == 'write':
                                        write_count += 1
                                        write_bytes += op['bytes']
                            else:
                                op_type, bytes_transferred = self._parse_strace_line(line)
                                if op_type == 'read':
                                    read_count += 1
                                    read_bytes += bytes_transferred
                                elif op_type == 'write':
                                    write_count += 1
                                    write_bytes += bytes_transferred
                except (IOError, OSError):
                    # If we can't read the strace output, return zeros with a note
                    # The method field will still indicate strace was used
                    # This is better than failing completely
                    pass
            
            result = {
                'read_count': read_count,
                'write_count': write_count,
                'read_bytes': read_bytes,
                'write_bytes': write_bytes,
                'elapsed_time': elapsed_time,
                'method': 'strace (per-process)'
            }
            
            if collect_ops:
                result['operations'] = operations
            
            return result
        
        finally:
            # Cleanup
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except:
                pass
    
    def _measure_systemwide_fallback(self, code):
        """Fallback: system-wide I/O measurement using psutil"""
        if not psutil:
            raise RuntimeError("psutil not installed. Run: pip install psutil")
        
        # Get initial system-wide I/O counters
        io_before = psutil.disk_io_counters()
        if io_before is None:
            raise RuntimeError("System-wide disk I/O counters not available")
        
        # Execute the code
        start_time = time.time()
        self.shell.run_cell(code)
        elapsed_time = time.time() - start_time
        
        # Get final system-wide I/O counters
        io_after = psutil.disk_io_counters()
        
        # Calculate differences
        read_count = io_after.read_count - io_before.read_count
        write_count = io_after.write_count - io_before.write_count
        read_bytes = io_after.read_bytes - io_before.read_bytes
        write_bytes = io_after.write_bytes - io_before.write_bytes
        
        return {
            'read_count': read_count,
            'write_count': write_count,
            'read_bytes': read_bytes,
            'write_bytes': write_bytes,
            'elapsed_time': elapsed_time,
            'method': '⚠️ SYSTEM-WIDE (includes all processes)'
        }
    
    def _format_bytes(self, bytes_val):
        """Format bytes into human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"
    
    def _generate_histograms(self, operations):
        """Generate histograms for I/O operations using numpy
        
        Args:
            operations: List of dicts with 'type' and 'bytes' keys
        """
        if not plt or not np:
            print("⚠️ matplotlib or numpy not available. Cannot generate histograms.")
            return
        
        if not operations:
            print("⚠️ No operations captured for histogram generation.")
            return
        
        # Separate operations by type
        read_ops = [op['bytes'] for op in operations if op['type'] == 'read' and op['bytes'] > 0]
        write_ops = [op['bytes'] for op in operations if op['type'] == 'write' and op['bytes'] > 0]
        all_ops = [op['bytes'] for op in operations if op['bytes'] > 0]
        
        if not all_ops:
            print("⚠️ No operations with non-zero bytes for histogram generation.")
            return
        
        # Create log-scale bins
        min_bytes = max(1, min(all_ops))
        max_bytes = max(all_ops)
        
        # Handle edge case where all operations have the same size
        if min_bytes == max_bytes:
            bin_edges = np.array([min_bytes * 0.9, min_bytes * 1.1])
        else:
            # Generate 30 bins evenly spaced in log space
            bin_edges = np.logspace(np.log10(min_bytes), np.log10(max_bytes), 31)
        
        # Compute histograms using numpy
        all_counts, _ = np.histogram(all_ops, bins=bin_edges)
        read_counts, _ = np.histogram(read_ops, bins=bin_edges) if read_ops else (np.zeros(len(bin_edges) - 1), bin_edges)
        write_counts, _ = np.histogram(write_ops, bins=bin_edges) if write_ops else (np.zeros(len(bin_edges) - 1), bin_edges)
        
        # Compute byte sums per bin using weighted histograms
        all_bytes, _ = np.histogram(all_ops, bins=bin_edges, weights=all_ops)
        read_bytes, _ = np.histogram(read_ops, bins=bin_edges, weights=read_ops) if read_ops else (np.zeros(len(bin_edges) - 1), bin_edges)
        write_bytes, _ = np.histogram(write_ops, bins=bin_edges, weights=write_ops) if write_ops else (np.zeros(len(bin_edges) - 1), bin_edges)
        
        # Compute bin centers for plotting
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Plot 1: Operation count histogram
        ax1.plot(bin_centers, all_counts, label='All Operations', linewidth=2, alpha=0.8)
        if read_ops:
            ax1.plot(bin_centers, read_counts, label='Reads', linewidth=2, alpha=0.8)
        if write_ops:
            ax1.plot(bin_centers, write_counts, label='Writes', linewidth=2, alpha=0.8)
        ax1.set_xscale('log')
        ax1.set_xlabel('Bytes per Operation (log scale)')
        ax1.set_ylabel('Count of Operations')
        ax1.set_title('I/O Operation Count Distribution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Total bytes histogram (with auto-scaling)
        max_bytes_in_bin = np.max(all_bytes) if len(all_bytes) > 0 else 0
        if max_bytes_in_bin < 1024:
            unit, divisor = 'B', 1
        elif max_bytes_in_bin < 1024 ** 2:
            unit, divisor = 'KB', 1024
        elif max_bytes_in_bin < 1024 ** 3:
            unit, divisor = 'MB', 1024 ** 2
        elif max_bytes_in_bin < 1024 ** 4:
            unit, divisor = 'GB', 1024 ** 3
        else:
            unit, divisor = 'TB', 1024 ** 4
        
        ax2.plot(bin_centers, all_bytes / divisor, label='All Operations', linewidth=2, alpha=0.8)
        if read_ops:
            ax2.plot(bin_centers, read_bytes / divisor, label='Reads', linewidth=2, alpha=0.8)
        if write_ops:
            ax2.plot(bin_centers, write_bytes / divisor, label='Writes', linewidth=2, alpha=0.8)
        ax2.set_xscale('log')
        ax2.set_xlabel('Bytes per Operation (log scale)')
        ax2.set_ylabel(f'Total Bytes ({unit})')
        ax2.set_title('I/O Total Bytes Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def _display_results(self, results):
        """Display results in a formatted table"""
        total_ops = results['read_count'] + results['write_count']
        total_bytes = results['read_bytes'] + results['write_bytes']
        iops = total_ops / results['elapsed_time'] if results['elapsed_time'] > 0 else 0
        throughput = total_bytes / results['elapsed_time'] if results['elapsed_time'] > 0 else 0
        
        html = f"""
        <style>
            .iops-table {{
                border-collapse: collapse;
                margin: 10px 0;
                font-family: monospace;
                font-size: 14px;
            }}
            .iops-table td {{
                padding: 6px 12px;
                border: 1px solid #ddd;
            }}
            .iops-table tr:first-child td {{
                background-color: #f5f5f5;
                font-weight: bold;
            }}
            .iops-warning {{
                color: #ff6600;
                font-size: 12px;
                margin-top: 5px;
            }}
        </style>
        <div>
            <table class="iops-table">
                <tr>
                    <td colspan="2">IOPS Profile Results ({results['method']})</td>
                </tr>
                <tr>
                    <td>Execution Time</td>
                    <td>{results['elapsed_time']:.4f} seconds</td>
                </tr>
                <tr>
                    <td>Read Operations</td>
                    <td>{results['read_count']:,}</td>
                </tr>
                <tr>
                    <td>Write Operations</td>
                    <td>{results['write_count']:,}</td>
                </tr>
                <tr>
                    <td>Total Operations</td>
                    <td>{total_ops:,}</td>
                </tr>
                <tr>
                    <td>Bytes Read</td>
                    <td>{self._format_bytes(results['read_bytes'])} ({results['read_bytes']:,} bytes)</td>
                </tr>
                <tr>
                    <td>Bytes Written</td>
                    <td>{self._format_bytes(results['write_bytes'])} ({results['write_bytes']:,} bytes)</td>
                </tr>
                <tr>
                    <td>Total Bytes</td>
                    <td>{self._format_bytes(total_bytes)} ({total_bytes:,} bytes)</td>
                </tr>
                <tr>
                    <td><strong>IOPS</strong></td>
                    <td><strong>{iops:.2f} operations/second</strong></td>
                </tr>
                <tr>
                    <td><strong>Throughput</strong></td>
                    <td><strong>{self._format_bytes(throughput)}/second</strong></td>
                </tr>
            </table>
        """
        
        if '⚠️' in results['method']:
            html += """
            <div class="iops-warning">
                ⚠️ Warning: System-wide measurement includes I/O from all processes.
                Results may not accurately reflect your code's I/O activity.
            </div>
            """
        
        html += "</div>"
        display(HTML(html))
    
    @cell_magic
    def iops(self, line, cell):
        """
        Measure I/O operations per second for the code in the cell.
        
        Usage:
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
            # Split on whitespace to properly detect flags
            args = line.strip().split()
            show_histogram = '--histogram' in args
            
            # Determine if we should collect individual operations
            # Only collect for strace/fs_usage modes where detailed data is available
            collect_ops = show_histogram
            
            # Determine measurement method based on platform
            if self.platform == 'darwin':  # macOS
                try:
                    results = self._measure_macos_osascript(cell, collect_ops=collect_ops)
                except RuntimeError as e:
                    if 'Resource busy' in str(e):
                        print("⚠️ ktrace is busy. Falling back to system-wide measurement.")
                        print("Tip: Try running 'sudo killall fs_usage' and retry.\n")
                        results = self._measure_systemwide_fallback(cell)
                        if show_histogram:
                            print("⚠️ Histograms not available for system-wide measurement mode.")
                    else:
                        print(f"⚠️ Could not start fs_usage: {e}")
                        print("Falling back to system-wide measurement.\n")
                        results = self._measure_systemwide_fallback(cell)
                        if show_histogram:
                            print("⚠️ Histograms not available for system-wide measurement mode.")
            
            elif self.platform in ('linux', 'linux2'):
                # Use strace on Linux (no elevated privileges required)
                try:
                    results = self._measure_linux_strace(cell, collect_ops=collect_ops)
                except (RuntimeError, FileNotFoundError) as e:
                    print(f"⚠️ Could not use strace: {e}")
                    print("Falling back to psutil per-process measurement.\n")
                    results = self._measure_linux_windows(cell, collect_ops=False)
                    if show_histogram:
                        print("⚠️ Histograms not available for psutil measurement mode.")
            
            elif self.platform == 'win32':
                results = self._measure_linux_windows(cell, collect_ops=collect_ops)
            
            else:
                print(f"⚠️ Platform '{self.platform}' not fully supported.")
                print("Attempting system-wide measurement as fallback.\n")
                results = self._measure_systemwide_fallback(cell)
                if show_histogram:
                    print("⚠️ Histograms not available for system-wide measurement mode.")
            
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