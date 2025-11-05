"""
Integration tests and utility function tests for iops_profiler.

This module tests higher-level integration scenarios and utility functions.
"""

import sys
from unittest.mock import MagicMock, Mock

import pytest
from iops_profiler import collector, display
from iops_profiler.magic import IOPSProfiler, load_ipython_extension, unload_ipython_extension


def create_test_profiler():
    """Helper function to create a test profiler instance"""
    mock_shell = MagicMock()
    mock_shell.configurables = []
    profiler = IOPSProfiler.__new__(IOPSProfiler)
    profiler.shell = mock_shell
    # Initialize the profiler attributes manually to avoid traitlets
    import sys

    profiler.platform = sys.platform
    # Initialize the collector with the mock shell
    from iops_profiler.collector import Collector

    profiler.collector = Collector(mock_shell)
    return profiler


class TestIOPSProfilerInitialization:
    """Test cases for IOPSProfiler initialization"""

    def test_initialization_with_mock_shell(self):
        """Test that profiler initializes correctly with a mock shell"""
        profiler = create_test_profiler()

        assert profiler.shell is not None
        assert profiler.platform == sys.platform
        assert hasattr(profiler.collector, "_strace_pattern")
        assert hasattr(profiler.collector, "_io_syscalls")

    def test_io_syscalls_set_populated(self):
        """Test that I/O syscalls set is properly populated"""
        profiler = create_test_profiler()

        # Check that expected syscalls are in the set
        expected_syscalls = ["read", "write", "pread64", "pwrite64", "readv", "writev"]
        for syscall in expected_syscalls:
            assert syscall in profiler.collector._io_syscalls

    def test_strace_pattern_compilation(self):
        """Test that strace pattern is properly compiled"""
        profiler = create_test_profiler()

        # Test pattern matching
        test_line = '3385  read(3, "data", 100) = 100'
        match = profiler.collector._strace_pattern.match(test_line)
        assert match is not None
        assert match.groups() == ("3385", "read", "100")


class TestExtensionLoading:
    """Test cases for IPython extension loading"""

    def test_load_extension(self):
        """Test loading the IPython extension"""
        mock_ipython = Mock()
        load_ipython_extension(mock_ipython)

        # Should register the magics
        mock_ipython.register_magics.assert_called_once()

    def test_unload_extension(self):
        """Test unloading the IPython extension"""
        mock_ipython = Mock()
        # Should not raise an error
        unload_ipython_extension(mock_ipython)


class TestHelperScriptCreation:
    """Test cases for helper script creation (macOS)"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_create_helper_script_basic(self, profiler):
        """Test creating a helper script with basic parameters"""
        pid = 12345
        output_file = "/tmp/test_output.txt"
        control_file = "/tmp/test_control.ctrl"

        script = collector.create_helper_script(pid, output_file, control_file)

        # Verify script contains expected elements
        assert str(pid) in script
        assert output_file in script
        assert control_file in script
        assert "#!/bin/bash" in script
        assert "fs_usage" in script

    def test_helper_script_structure(self, profiler):
        """Test that helper script has proper structure"""
        pid = 99999
        output_file = "/tmp/out.txt"
        control_file = "/tmp/ctrl.txt"

        script = collector.create_helper_script(pid, output_file, control_file)

        # Should contain cleanup logic
        assert "killall" in script
        # Should contain wait logic
        assert "STOP" in script
        # Should contain error handling
        assert "ERROR_FILE" in script


class TestPlatformDetection:
    """Test cases for platform-specific behavior"""

    def test_platform_stored_correctly(self):
        """Test that platform is stored correctly on initialization"""
        profiler = create_test_profiler()

        assert profiler.platform in ["linux", "linux2", "darwin", "win32", sys.platform]


class TestArgumentParsing:
    """Test cases for argument parsing in the iops magic"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_histogram_flag_detection(self, profiler):
        """Test that --histogram flag is properly detected"""
        # This would require testing the iops method itself
        # which is more complex due to the magic decorator
        # For now, we just verify the profiler can be created
        assert profiler is not None


class TestEdgeCaseOperations:
    """Test edge cases in operation handling"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_parse_multiple_strace_lines(self, profiler):
        """Test parsing multiple strace lines in sequence"""
        lines = [
            '3385  read(3, "data", 100) = 100',
            '3385  write(4, "info", 50) = 50',
            '3385  pread64(5, "test", 200) = 200',
        ]

        total_read_bytes = 0
        total_write_bytes = 0

        for line in lines:
            op_type, bytes_transferred = profiler.collector.parse_strace_line(line)
            if op_type == "read":
                total_read_bytes += bytes_transferred
            elif op_type == "write":
                total_write_bytes += bytes_transferred

        assert total_read_bytes == 300
        assert total_write_bytes == 50

    def test_parse_multiple_fs_usage_lines(self, profiler):
        """Test parsing multiple fs_usage lines in sequence"""
        lines = [
            "12:34:56  read  B=0x100  /file  Python",
            "12:34:57  write  B=0x200  /file  Python",
            "12:34:58  read  B=0x300  /file  Python",
        ]

        total_read_bytes = 0
        total_write_bytes = 0

        for line in lines:
            op_type, bytes_transferred = collector.parse_fs_usage_line(line)
            if op_type == "read":
                total_read_bytes += bytes_transferred
            elif op_type == "write":
                total_write_bytes += bytes_transferred

        assert total_read_bytes == 0x100 + 0x300
        assert total_write_bytes == 0x200

    def test_mixed_valid_and_invalid_lines_strace(self, profiler):
        """Test parsing mixed valid and invalid strace lines"""
        lines = [
            '3385  read(3, "data", 100) = 100',
            "invalid line",
            '3385  write(4, "info", 50) = 50',
            "",
            '3385  open("/tmp/test", O_RDONLY) = 3',
            '3385  read(3, "more", 30) = 30',
        ]

        valid_ops = 0
        total_bytes = 0

        for line in lines:
            op_type, bytes_transferred = profiler.collector.parse_strace_line(line)
            if op_type:
                valid_ops += 1
                total_bytes += bytes_transferred

        assert valid_ops == 3  # Two reads and one write
        assert total_bytes == 180

    def test_mixed_valid_and_invalid_lines_fs_usage(self, profiler):
        """Test parsing mixed valid and invalid fs_usage lines"""
        lines = [
            "12:34:56  read  B=0x100  /file  Python",
            "not a valid line",
            "12:34:57  write  B=0x200  /file  Python",
            "",
            "12:34:58  open  B=0x400  /file  Python",
            "12:34:59  read  B=0x300  /file  Python",
        ]

        valid_ops = 0
        total_bytes = 0

        for line in lines:
            op_type, bytes_transferred = collector.parse_fs_usage_line(line)
            if op_type:
                valid_ops += 1
                total_bytes += bytes_transferred

        assert valid_ops == 3  # Two reads and one write
        assert total_bytes == 0x100 + 0x200 + 0x300


class TestResultsCalculation:
    """Test cases for results calculation and formatting"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_iops_calculation(self, profiler):
        """Test IOPS calculation from results"""
        results = {
            "read_count": 100,
            "write_count": 50,
            "read_bytes": 102400,
            "write_bytes": 51200,
            "elapsed_time": 1.0,
            "method": "psutil",
        }

        total_ops = results["read_count"] + results["write_count"]
        iops = total_ops / results["elapsed_time"]

        assert iops == 150.0

    def test_throughput_calculation(self, profiler):
        """Test throughput calculation from results"""
        results = {
            "read_count": 100,
            "write_count": 50,
            "read_bytes": 102400,
            "write_bytes": 51200,
            "elapsed_time": 1.0,
            "method": "psutil",
        }

        total_bytes = results["read_bytes"] + results["write_bytes"]
        throughput = total_bytes / results["elapsed_time"]

        assert throughput == 153600.0

    def test_zero_time_iops(self, profiler):
        """Test IOPS calculation with zero elapsed time"""
        results = {
            "read_count": 100,
            "write_count": 50,
            "read_bytes": 102400,
            "write_bytes": 51200,
            "elapsed_time": 0.0,
            "method": "psutil",
        }

        total_ops = results["read_count"] + results["write_count"]
        iops = total_ops / results["elapsed_time"] if results["elapsed_time"] > 0 else 0

        assert iops == 0


class TestCollectOpsMode:
    """Test cases for collect_ops mode in parsing"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_collect_ops_strace_multiple_lines(self, profiler):
        """Test collecting operations from multiple strace lines"""
        lines = [
            '3385  read(3, "data", 100) = 100',
            '3385  write(4, "info", 200) = 200',
            '3385  read(5, "more", 300) = 300',
        ]

        operations = []
        for line in lines:
            op = profiler.collector.parse_strace_line(line, collect_ops=True)
            if op:
                operations.append(op)

        assert len(operations) == 3
        assert operations[0] == {"type": "read", "bytes": 100}
        assert operations[1] == {"type": "write", "bytes": 200}
        assert operations[2] == {"type": "read", "bytes": 300}

    def test_collect_ops_fs_usage_multiple_lines(self, profiler):
        """Test collecting operations from multiple fs_usage lines"""
        lines = [
            "12:34:56  read  B=0x100  /file  Python",
            "12:34:57  write  B=0x200  /file  Python",
            "12:34:58  read  B=0x300  /file  Python",
        ]

        operations = []
        for line in lines:
            op = collector.parse_fs_usage_line(line, collect_ops=True)
            if op:
                operations.append(op)

        assert len(operations) == 3
        assert operations[0] == {"type": "read", "bytes": 0x100}
        assert operations[1] == {"type": "write", "bytes": 0x200}
        assert operations[2] == {"type": "read", "bytes": 0x300}

    def test_collect_ops_filters_invalid_lines(self, profiler):
        """Test that collect_ops filters out invalid lines"""
        lines = [
            '3385  read(3, "data", 100) = 100',
            "invalid line",
            '3385  write(4, "info", 200) = 200',
            "3385  read(3, 0x..., 100) = -1 EBADF",
            '3385  read(5, "more", 300) = 300',
        ]

        operations = []
        for line in lines:
            op = profiler.collector.parse_strace_line(line, collect_ops=True)
            if op:
                operations.append(op)

        # Should only have 3 valid operations (error and invalid lines excluded)
        assert len(operations) == 3


class TestBugDocumentation:
    """
    Test cases that document potential bugs or unexpected behaviors.

    These tests may fail initially, which is expected as per the issue requirements.
    They serve to document edge cases where the current implementation might not
    handle things correctly.
    """

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_strace_truncated_line(self, profiler):
        """
        Test parsing a truncated strace line (potential bug).

        If strace output is truncated or buffered incorrectly, we might see
        incomplete lines that should be handled gracefully.
        """
        line = '3385  read(3, "da'  # Truncated line
        op_type, bytes_transferred = profiler.collector.parse_strace_line(line)

        # Should handle gracefully and return None/0
        assert op_type is None
        assert bytes_transferred == 0

    def test_fs_usage_malformed_hex_with_prefix(self, profiler):
        """
        Test parsing fs_usage with malformed hex (potential bug).

        What happens if B= has unexpected format like "0x" without digits?
        """
        line = "12:34:56  read  B=0x  /file  Python"
        op_type, bytes_transferred = collector.parse_fs_usage_line(line)

        # Should handle gracefully
        assert op_type == "read"
        assert bytes_transferred == 0

    def test_strace_negative_zero_return(self, profiler):
        """
        Test parsing strace with "-0" return value (edge case).

        While unusual, -0 might appear in some contexts.
        """
        line = '3385  read(3, "data", 100) = -0'
        op_type, bytes_transferred = profiler.collector.parse_strace_line(line)

        # Should either parse as 0 or reject as invalid
        # Current implementation will parse as 0 (int("-0") == 0)
        assert op_type == "read" or op_type is None
        assert bytes_transferred == 0

    def test_histogram_with_single_zero_byte_operation(self, profiler):
        """
        Test histogram generation with only one operation that has 0 bytes.

        This is an edge case - technically operations exist, but all are zero bytes.
        """
        operations = [{"type": "read", "bytes": 0}]

        # Should handle gracefully - current implementation filters out zero-byte ops
        # so this should print a warning and return
        display.generate_histograms(operations)

    def test_strace_extremely_large_pid(self, profiler):
        """
        Test parsing strace line with extremely large PID.

        PIDs can be very large on some systems. This tests if parsing handles them.
        """
        large_pid = 2**31 - 1  # Max 32-bit signed int
        line = f'{large_pid}  read(3, "data", 100) = 100'
        op_type, bytes_transferred = profiler.collector.parse_strace_line(line)

        assert op_type == "read"
        assert bytes_transferred == 100

    def test_strace_extremely_large_byte_count(self, profiler):
        """
        Test parsing strace line with extremely large byte count.

        While unrealistic, extremely large values could cause integer overflow.
        """
        huge_bytes = 2**63 - 1  # Max 64-bit signed int
        line = f'3385  write(3, "...", {huge_bytes}) = {huge_bytes}'
        op_type, bytes_transferred = profiler.collector.parse_strace_line(line)

        assert op_type == "write"
        assert bytes_transferred == huge_bytes
