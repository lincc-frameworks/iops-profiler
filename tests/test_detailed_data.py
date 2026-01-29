"""
Tests for detailed I/O data collection and injection into user namespace.

This module tests the new detailed data collection feature that provides
file paths, syscalls, and operation details via the iops_detailed_data variable.
"""

from unittest.mock import MagicMock

import pytest

from iops_profiler import collector
from iops_profiler.magic import IOPSProfiler


def create_test_profiler():
    """Helper function to create a test profiler instance"""
    mock_shell = MagicMock()
    mock_shell.configurables = []
    mock_shell.user_ns = {}  # Mock user namespace
    profiler = IOPSProfiler.__new__(IOPSProfiler)
    profiler.shell = mock_shell
    # Initialize the profiler attributes manually to avoid traitlets
    import sys

    profiler.platform = sys.platform
    # Initialize the collector with the mock shell
    from iops_profiler.collector import Collector

    profiler.collector = Collector(mock_shell)
    return profiler


class TestDetailedDataParsing:
    """Test cases for detailed data parsing"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_strace_detailed_with_path(self, profiler):
        """Test parsing strace line with -y flag (file path included)"""
        line = '3385  read(3</tmp/test.txt>, "data", 4096) = 133'
        result = profiler.collector.parse_strace_line(line, collect_detailed=True)

        assert result is not None
        assert isinstance(result, dict)
        assert result["path"] == "/tmp/test.txt"
        assert result["operation"] == "read"
        assert result["syscall"] == "read"
        assert result["size_bytes"] == 133

    def test_strace_detailed_without_path(self, profiler):
        """Test parsing strace line without -y flag (no file path)"""
        line = '3385  write(3, "Hello World...", 1100) = 1100'
        result = profiler.collector.parse_strace_line(line, collect_detailed=True)

        assert result is not None
        assert isinstance(result, dict)
        assert result["path"] == ""  # No path available
        assert result["operation"] == "write"
        assert result["syscall"] == "write"
        assert result["size_bytes"] == 1100

    def test_strace_detailed_pread64_with_path(self, profiler):
        """Test parsing pread64 operation with path"""
        line = '3385  pread64(3</var/log/test.log>, "...", 1024, 0) = 1024'
        result = profiler.collector.parse_strace_line(line, collect_detailed=True)

        assert result is not None
        assert result["path"] == "/var/log/test.log"
        assert result["operation"] == "read"
        assert result["syscall"] == "pread64"
        assert result["size_bytes"] == 1024

    def test_strace_detailed_error_returns_none(self, profiler):
        """Test parsing error operation returns None"""
        line = "3385  read(3, 0x..., 4096) = -1 EBADF"
        result = profiler.collector.parse_strace_line(line, collect_detailed=True)

        assert result is None

    def test_fs_usage_detailed_basic(self, profiler):
        """Test parsing fs_usage line with detailed collection"""
        line = "12:34:56  read  B=0x1000  /path/to/file.txt  Python"
        result = profiler.collector.parse_fs_usage_line(line, collect_detailed=True)

        assert result is not None
        assert isinstance(result, dict)
        assert result["path"] == "/path/to/file.txt"
        assert result["operation"] == "read"
        assert result["syscall"] == "read"
        assert result["size_bytes"] == 0x1000

    def test_fs_usage_detailed_write(self, profiler):
        """Test parsing fs_usage write operation"""
        line = "12:34:57  write  B=0x800  /tmp/output.dat  Python"
        result = profiler.collector.parse_fs_usage_line(line, collect_detailed=True)

        assert result is not None
        assert result["path"] == "/tmp/output.dat"
        assert result["operation"] == "write"
        assert result["syscall"] == "write"
        assert result["size_bytes"] == 0x800

    def test_fs_usage_detailed_pread(self, profiler):
        """Test parsing fs_usage pread operation"""
        line = "12:34:58  pread  B=0x400  /data/file.bin  Python"
        result = profiler.collector.parse_fs_usage_line(line, collect_detailed=True)

        assert result is not None
        assert result["path"] == "/data/file.bin"
        assert result["operation"] == "read"
        assert result["syscall"] == "pread"
        assert result["size_bytes"] == 0x400

    def test_fs_usage_detailed_non_io_returns_none(self, profiler):
        """Test parsing non-I/O operation returns None"""
        line = "12:34:59  open  B=0x1000  /path/to/file  Python"
        result = profiler.collector.parse_fs_usage_line(line, collect_detailed=True)

        assert result is None


class TestDetailedDataCollection:
    """Test cases for detailed data collection in measurement methods"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_detailed_data_keys_in_result(self, profiler):
        """Test that detailed_data key is added when collect_detailed=True"""
        # We can't fully test the measurement methods without actual I/O
        # but we can test the parsing logic
        strace_lines = [
            '3385  read(3</tmp/test1.txt>, "data", 100) = 100',
            '3385  write(4</tmp/test2.txt>, "info", 200) = 200',
        ]

        detailed_data = []
        for line in strace_lines:
            detail = profiler.collector.parse_strace_line(line, collect_detailed=True)
            if detail:
                detailed_data.append(detail)

        assert len(detailed_data) == 2
        assert detailed_data[0]["path"] == "/tmp/test1.txt"
        assert detailed_data[0]["operation"] == "read"
        assert detailed_data[0]["size_bytes"] == 100
        assert detailed_data[1]["path"] == "/tmp/test2.txt"
        assert detailed_data[1]["operation"] == "write"
        assert detailed_data[1]["size_bytes"] == 200


class TestDetailedDataBackwardCompatibility:
    """Test backward compatibility of parsing functions"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_strace_parsing_without_collect_detailed(self, profiler):
        """Test that original parsing still works without collect_detailed"""
        line = '3385  read(3</tmp/test.txt>, "data", 4096) = 133'

        # Test with collect_ops=False (default)
        op_type, bytes_transferred = profiler.collector.parse_strace_line(line)
        assert op_type == "read"
        assert bytes_transferred == 133

        # Test with collect_ops=True
        result = profiler.collector.parse_strace_line(line, collect_ops=True)
        assert result["type"] == "read"
        assert result["bytes"] == 133

    def test_fs_usage_parsing_without_collect_detailed(self, profiler):
        """Test that original fs_usage parsing still works"""
        line = "12:34:56  read  B=0x1000  /path/to/file  Python"

        # Test with default mode
        op_type, bytes_transferred = profiler.collector.parse_fs_usage_line(line)
        assert op_type == "read"
        assert bytes_transferred == 0x1000

        # Test with collect_ops=True
        result = profiler.collector.parse_fs_usage_line(line, collect_ops=True)
        assert result["type"] == "read"
        assert result["bytes"] == 0x1000


class TestModuleLevelFunctionsWithDetailed:
    """Test module-level backward compatibility functions with detailed mode"""

    def test_module_level_parse_strace_line_with_detailed(self):
        """Test module-level parse_strace_line function with collect_detailed"""
        import re

        from iops_profiler.collector import STRACE_IO_SYSCALLS

        strace_pattern = re.compile(r"^\s*(\d+)\s+(\w+)\([^)]+\)\s*=\s*(-?\d+)")
        io_syscalls = set(STRACE_IO_SYSCALLS)

        line = '3385  read(3</tmp/test.txt>, "data", 4096) = 133'
        result = collector.parse_strace_line(line, strace_pattern, io_syscalls, collect_detailed=True)

        assert result is not None
        assert result["path"] == "/tmp/test.txt"
        assert result["operation"] == "read"
        assert result["size_bytes"] == 133

    def test_module_level_parse_fs_usage_line_with_detailed(self):
        """Test module-level parse_fs_usage_line function with collect_detailed"""
        line = "12:34:56  read  B=0x1000  /path/to/file.txt  Python"
        result = collector.parse_fs_usage_line(line, collect_detailed=True)

        assert result is not None
        assert result["path"] == "/path/to/file.txt"
        assert result["operation"] == "read"
        assert result["size_bytes"] == 0x1000
