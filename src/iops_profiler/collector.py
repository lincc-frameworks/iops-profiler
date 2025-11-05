"""
Data collection module for IOPS Profiler.

This module contains all the data collection functionality including:
- Parsing strace and fs_usage output
- Platform-specific measurement methods (Linux, macOS, Windows)
- Helper functions for collecting I/O statistics
"""

import os
import re
import subprocess
import sys
import tempfile
import time

try:
    import psutil
except ImportError:
    psutil = None


# Timing constants for strace attachment and capture
STRACE_ATTACH_DELAY = 0.5  # seconds to wait for strace to attach to process
STRACE_CAPTURE_DELAY = 0.5  # seconds to wait for strace to capture final I/O

# I/O syscalls to trace with strace
STRACE_IO_SYSCALLS = [
    "read",
    "write",  # Basic I/O
    "pread64",
    "pwrite64",  # Positional I/O
    "readv",
    "writev",  # Vectored I/O
    "preadv",
    "pwritev",  # Positional vectored I/O
    "preadv2",
    "pwritev2",  # Extended vectored I/O
]

# Regex pattern for extracting byte count from fs_usage output
FS_USAGE_BYTE_PATTERN = r"B=0x([0-9a-fA-F]+)"


class Collector:
    """Collector class for I/O profiling data collection.

    This class encapsulates all data collection functionality and maintains
    necessary state like the IPython shell, strace patterns, and syscall sets.
    """

    def __init__(self, shell):
        """Initialize the Collector with IPython shell context.

        Args:
            shell: IPython shell instance for executing code
        """
        self.shell = shell
        self.platform = sys.platform
        # Compile regex patterns for better performance
        # Pattern matches: PID syscall(args) = result
        self._strace_pattern = re.compile(r"^\s*(\d+)\s+(\w+)\([^)]+\)\s*=\s*(-?\d+)")
        # Pattern matches: B=0x[hex] in fs_usage output
        self._fs_usage_byte_pattern = re.compile(FS_USAGE_BYTE_PATTERN)
        # Set of syscall names for I/O operations (lowercase)
        self._io_syscalls = set(STRACE_IO_SYSCALLS)

    @staticmethod
    def parse_fs_usage_line_static(line, byte_pattern=None, collect_ops=False):
        """Parse a single fs_usage output line for I/O operations (static version)

        Args:
            line: The line to parse
            byte_pattern: Compiled regex pattern for extracting byte count (optional)
            collect_ops: If True, return full operation info for histogram collection

        Returns:
            If collect_ops is False: (op_type, bytes_transferred)
            If collect_ops is True: {'type': op_type, 'bytes': bytes_transferred}
        """
        parts = line.split()
        if len(parts) < 2:
            return None if collect_ops else (None, 0)

        syscall = parts[1].lower()
        is_read = "read" in syscall
        is_write = "write" in syscall

        if not (is_read or is_write):
            return None if collect_ops else (None, 0)

        # Extract byte count from B=0x[hex] pattern using compiled regex
        if byte_pattern is None:
            # Fallback to inline regex if no pattern provided (for backward compatibility)
            byte_match = re.search(FS_USAGE_BYTE_PATTERN, line)
        else:
            byte_match = byte_pattern.search(line)
        bytes_transferred = int(byte_match.group(1), 16) if byte_match else 0

        op_type = "read" if is_read else "write"

        if collect_ops:
            return {"type": op_type, "bytes": bytes_transferred}
        return op_type, bytes_transferred

    def parse_fs_usage_line(self, line, collect_ops=False):
        """Parse a single fs_usage output line for I/O operations (instance method)

        This is a convenience wrapper that uses the instance's compiled byte pattern.
        """
        return self.parse_fs_usage_line_static(line, self._fs_usage_byte_pattern, collect_ops)

    @staticmethod
    def parse_strace_line_static(line, strace_pattern, io_syscalls, collect_ops=False):
        """Parse a single strace output line for I/O operations (static version)

        Example strace lines:
        3385  write(3, "Hello World...", 1100) = 1100
        3385  read(3, "data", 4096) = 133
        3385  pread64(3, "...", 1024, 0) = 1024

        Note: Lines with <unfinished ...> or <... resumed> are not matched
        as they don't contain complete result information in a single line.

        Args:
            line: The line to parse
            strace_pattern: Compiled regex pattern for strace output
            io_syscalls: Set of I/O syscall names to track
            collect_ops: If True, return full operation info for histogram collection

        Returns:
            If collect_ops is False: (op_type, bytes_transferred)
            If collect_ops is True: {'type': op_type, 'bytes': bytes_transferred}
        """
        # Match patterns like: PID syscall(fd, ..., size) = result
        match = strace_pattern.match(line)
        if not match:
            return None if collect_ops else (None, 0)

        pid, syscall, result = match.groups()
        syscall = syscall.lower()

        # Check if it's one of the I/O syscalls we're tracking
        if syscall not in io_syscalls:
            return None if collect_ops else (None, 0)

        # Determine if it's a read or write operation based on syscall name
        if "read" in syscall:
            is_read = True
        elif "write" in syscall:
            is_read = False
        else:
            return None if collect_ops else (None, 0)

        # The return value is the number of bytes transferred (or -1 on error)
        bytes_transferred = int(result)
        if bytes_transferred < 0:
            return None if collect_ops else (None, 0)

        op_type = "read" if is_read else "write"

        if collect_ops:
            return {"type": op_type, "bytes": bytes_transferred}
        return op_type, bytes_transferred

    def parse_strace_line(self, line, collect_ops=False):
        """Parse a single strace output line for I/O operations (instance method)

        This is a convenience wrapper that uses the instance's strace pattern and syscalls.
        """
        return self.parse_strace_line_static(line, self._strace_pattern, self._io_syscalls, collect_ops)

    @staticmethod
    def _create_helper_script(pid, output_file, control_file):
        """Create a bash helper script that runs fs_usage with elevated privileges"""
        script_content = f"""#!/bin/bash
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
"""
        return script_content

    def _launch_helper_via_osascript(self, helper_script_path):
        """Launch helper script with sudo via osascript (prompts for password)"""
        applescript = f"""
        do shell script "bash {helper_script_path}" with administrator privileges
        """

        proc = subprocess.Popen(
            ["osascript", "-e", applescript], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return proc

    def measure_macos_osascript(self, code, collect_ops=False):
        """Measure IOPS on macOS using fs_usage via osascript

        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram
        """
        pid = os.getpid()

        # Create temporary files
        # Create temporary files - we need the names, not file handles
        output_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False).name  # noqa: SIM115
        control_file = tempfile.NamedTemporaryFile(mode="w", suffix=".ctrl", delete=False).name  # noqa: SIM115
        helper_script = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False).name  # noqa: SIM115

        try:
            # Write the helper script
            script_content = self._create_helper_script(pid, output_file, control_file)
            with open(helper_script, "w") as f:
                f.write(script_content)
            os.chmod(helper_script, 0o755)

            # Initialize control file
            with open(control_file, "w") as f:
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
            with open(control_file, "w") as f:
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
                with open(output_file, "r") as f:
                    for line in f:
                        if collect_ops:
                            op = self.parse_fs_usage_line(line, collect_ops=True)
                            if op:
                                operations.append(op)
                                if op["type"] == "read":
                                    read_count += 1
                                    read_bytes += op["bytes"]
                                elif op["type"] == "write":
                                    write_count += 1
                                    write_bytes += op["bytes"]
                        else:
                            op_type, bytes_transferred = self.parse_fs_usage_line(line)
                            if op_type == "read":
                                read_count += 1
                                read_bytes += bytes_transferred
                            elif op_type == "write":
                                write_count += 1
                                write_bytes += bytes_transferred

            result = {
                "read_count": read_count,
                "write_count": write_count,
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "elapsed_time": elapsed_time,
                "method": "fs_usage (per-process)",
            }

            if collect_ops:
                result["operations"] = operations

            return result

        finally:
            # Cleanup - try to kill fs_usage processes
            try:  # noqa: SIM105
                subprocess.run(
                    ["sudo", "killall", "-9", "fs_usage"], capture_output=True, timeout=2, check=False
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass  # sudo or killall not available or timed out

            for filepath in [
                output_file,
                control_file,
                helper_script,
                f"{control_file}.pid",
                f"{output_file}.err",
            ]:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except OSError:
                    pass  # File already deleted or permission issue

    def measure_linux_strace(self, code, collect_ops=False):
        """Measure IOPS on Linux using strace (no elevated privileges required)

        Args:
            code: The code to profile
            collect_ops: If True, collect individual operation sizes for histogram
        """
        pid = os.getpid()

        # Allow this process to be ptraced (required on systems with Yama LSM)
        try:
            import ctypes
            import ctypes.util

            libc = ctypes.CDLL(ctypes.util.find_library("c"))
            PR_SET_PTRACER = 0x59616D61  # noqa: N806 - system constant
            PR_SET_PTRACER_ANY = -1  # noqa: N806 - system constant
            libc.prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0)
        except Exception:
            pass

        # Create temporary file for strace output - we need the name, not file handle
        output_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False).name  # noqa: SIM115

        try:
            # Start strace in the background
            syscalls_to_trace = ",".join(STRACE_IO_SYSCALLS)
            strace_cmd = [
                "strace",
                "-f",  # Follow forks
                "-e",
                f"trace={syscalls_to_trace}",
                "-o",
                output_file,
                "-p",
                str(pid),
            ]

            # Start strace process
            strace_proc = subprocess.Popen(
                strace_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Give strace a moment to attach
            time.sleep(STRACE_ATTACH_DELAY)

            # Check if strace started successfully
            if strace_proc.poll() is not None:
                stdout, stderr = strace_proc.communicate()
                if "Operation not permitted" in stderr:
                    raise RuntimeError(
                        "strace failed - ptrace not permitted. This may be due to kernel security settings."
                    )
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
                    with open(output_file, "r", errors="ignore") as f:
                        for line in f:
                            if collect_ops:
                                op = self.parse_strace_line(line, collect_ops=True)
                                if op:
                                    operations.append(op)
                                    if op["type"] == "read":
                                        read_count += 1
                                        read_bytes += op["bytes"]
                                    elif op["type"] == "write":
                                        write_count += 1
                                        write_bytes += op["bytes"]
                            else:
                                op_type, bytes_transferred = self.parse_strace_line(line)
                                if op_type == "read":
                                    read_count += 1
                                    read_bytes += bytes_transferred
                                elif op_type == "write":
                                    write_count += 1
                                    write_bytes += bytes_transferred
                except OSError:
                    pass

            result = {
                "read_count": read_count,
                "write_count": write_count,
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "elapsed_time": elapsed_time,
                "method": "strace (per-process)",
            }

            if collect_ops:
                result["operations"] = operations

            return result

        finally:
            # Cleanup
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except OSError:  # File cleanup may fail, not critical
                pass

    def measure_linux_windows(self, code):
        """Measure IOPS on Linux/Windows using psutil"""
        if not psutil:
            raise RuntimeError("psutil not installed. Run: pip install psutil")

        process = psutil.Process()

        # Get initial I/O counters
        try:
            io_before = process.io_counters()
        except AttributeError as e:
            raise RuntimeError(f"psutil.Process.io_counters() not supported on {self.platform}") from e  # noqa: B904

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
            "read_count": read_count,
            "write_count": write_count,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes,
            "elapsed_time": elapsed_time,
            "method": "psutil (per-process)",
        }

    def measure_systemwide_fallback(self, code):
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
            "read_count": read_count,
            "write_count": write_count,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes,
            "elapsed_time": elapsed_time,
            "method": "⚠️ SYSTEM-WIDE (includes all processes)",
        }


# Module-level functions for backward compatibility with tests
# These directly reference the static methods to avoid code duplication
parse_fs_usage_line = Collector.parse_fs_usage_line_static
parse_strace_line = Collector.parse_strace_line_static


create_helper_script = Collector._create_helper_script
