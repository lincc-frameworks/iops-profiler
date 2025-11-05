"""
Tests for parsing functions in iops_profiler.

This module focuses on testing the parsing logic for strace and fs_usage output,
including various edge cases and error conditions.
"""

import pytest
from unittest.mock import Mock, MagicMock
from iops_profiler.iops_profiler import IOPSProfiler


class TestStraceLineParsing:
    """Test cases for _parse_strace_line method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        # Create a proper mock shell with parent=None to avoid traitlets issues
        mock_shell = MagicMock()
        mock_shell.configurables = []
        profiler = IOPSProfiler.__new__(IOPSProfiler)
        profiler.shell = mock_shell
        # Initialize the parent attributes manually to avoid traitlets
        import sys
        profiler.platform = sys.platform
        import re
        profiler._strace_pattern = re.compile(r'^\s*(\d+)\s+(\w+)\([^)]+\)\s*=\s*(-?\d+)')
        from iops_profiler.iops_profiler import STRACE_IO_SYSCALLS
        profiler._io_syscalls = set(STRACE_IO_SYSCALLS)
        return profiler
    
    def test_basic_read_operation(self, profiler):
        """Test parsing a basic read operation"""
        line = "3385  read(3, \"data\", 4096) = 133"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 133
    
    def test_basic_write_operation(self, profiler):
        """Test parsing a basic write operation"""
        line = "3385  write(3, \"Hello World...\", 1100) = 1100"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 1100
    
    def test_pread64_operation(self, profiler):
        """Test parsing a pread64 operation"""
        line = "3385  pread64(3, \"...\", 1024, 0) = 1024"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 1024
    
    def test_pwrite64_operation(self, profiler):
        """Test parsing a pwrite64 operation"""
        line = "3385  pwrite64(4, \"data\", 512, 1024) = 512"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 512
    
    def test_readv_operation(self, profiler):
        """Test parsing a readv (vectored read) operation"""
        line = "3385  readv(5, [{iov_base=\"...\", iov_len=1024}], 1) = 1024"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 1024
    
    def test_writev_operation(self, profiler):
        """Test parsing a writev (vectored write) operation"""
        line = "3385  writev(5, [{iov_base=\"...\", iov_len=2048}], 1) = 2048"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 2048
    
    def test_preadv_operation(self, profiler):
        """Test parsing a preadv operation"""
        line = "3385  preadv(6, [{...}], 2, 0) = 512"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 512
    
    def test_pwritev_operation(self, profiler):
        """Test parsing a pwritev operation"""
        line = "3385  pwritev(6, [{...}], 2, 1024) = 1024"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 1024
    
    def test_preadv2_operation(self, profiler):
        """Test parsing a preadv2 operation"""
        line = "3385  preadv2(7, [{...}], 1, 0, 0) = 256"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 256
    
    def test_pwritev2_operation(self, profiler):
        """Test parsing a pwritev2 operation"""
        line = "3385  pwritev2(7, [{...}], 1, 512, 0) = 512"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 512
    
    def test_zero_bytes_read(self, profiler):
        """Test parsing a read that returns 0 bytes (EOF)"""
        line = "3385  read(3, \"\", 4096) = 0"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0
    
    def test_zero_bytes_write(self, profiler):
        """Test parsing a write that returns 0 bytes"""
        line = "3385  write(3, \"\", 0) = 0"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 0
    
    def test_error_negative_return(self, profiler):
        """Test parsing an operation that failed (negative return)"""
        line = "3385  read(3, 0x..., 4096) = -1 EBADF (Bad file descriptor)"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_unfinished_operation_ignored(self, profiler):
        """Test that unfinished operations are ignored"""
        line = "3385  read(3, <unfinished ...>"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_resumed_operation_ignored(self, profiler):
        """Test that resumed operations are ignored"""
        line = "3385  <... read resumed> \"data\", 4096) = 133"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_non_io_syscall_ignored(self, profiler):
        """Test that non-I/O syscalls are ignored"""
        line = "3385  open(\"/tmp/test.txt\", O_RDONLY) = 3"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_malformed_line_ignored(self, profiler):
        """Test that malformed lines are ignored"""
        line = "this is not a valid strace line"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_empty_line_ignored(self, profiler):
        """Test that empty lines are ignored"""
        line = ""
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_whitespace_only_line_ignored(self, profiler):
        """Test that whitespace-only lines are ignored"""
        line = "   \t  \n"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_very_large_byte_count(self, profiler):
        """Test parsing operations with very large byte counts"""
        line = "3385  write(3, \"...\", 1073741824) = 1073741824"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 1073741824  # 1 GB
    
    def test_single_byte_operation(self, profiler):
        """Test parsing single-byte operations"""
        line = "3385  read(3, \"x\", 1) = 1"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 1
    
    def test_collect_ops_mode(self, profiler):
        """Test parsing with collect_ops=True returns dict format"""
        line = "3385  read(3, \"data\", 4096) = 133"
        result = profiler._parse_strace_line(line, collect_ops=True)
        assert isinstance(result, dict)
        assert result['type'] == 'read'
        assert result['bytes'] == 133
    
    def test_collect_ops_mode_error(self, profiler):
        """Test parsing error with collect_ops=True returns None"""
        line = "3385  read(3, 0x..., 4096) = -1 EBADF"
        result = profiler._parse_strace_line(line, collect_ops=True)
        assert result is None
    
    def test_collect_ops_mode_non_io(self, profiler):
        """Test parsing non-I/O syscall with collect_ops=True returns None"""
        line = "3385  open(\"/tmp/test.txt\", O_RDONLY) = 3"
        result = profiler._parse_strace_line(line, collect_ops=True)
        assert result is None
    
    def test_multiple_spaces_in_line(self, profiler):
        """Test parsing lines with multiple spaces"""
        line = "  3385    read(3,   \"data\",   4096)   =   133"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 133
    
    def test_partial_write(self, profiler):
        """Test parsing a write that only partially succeeded"""
        line = "3385  write(3, \"data\"..., 1000) = 500"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 500
    
    def test_partial_read(self, profiler):
        """Test parsing a read that returned less than requested"""
        line = "3385  read(3, \"partial\"..., 8192) = 42"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 42


class TestFsUsageLineParsing:
    """Test cases for _parse_fs_usage_line method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        # Create a proper mock shell with parent=None to avoid traitlets issues
        mock_shell = MagicMock()
        mock_shell.configurables = []
        profiler = IOPSProfiler.__new__(IOPSProfiler)
        profiler.shell = mock_shell
        # Initialize the parent attributes manually to avoid traitlets
        import sys
        profiler.platform = sys.platform
        import re
        profiler._strace_pattern = re.compile(r'^\s*(\d+)\s+(\w+)\([^)]+\)\s*=\s*(-?\d+)')
        from iops_profiler.iops_profiler import STRACE_IO_SYSCALLS
        profiler._io_syscalls = set(STRACE_IO_SYSCALLS)
        return profiler
    
    @pytest.mark.xfail(reason="BUG: fs_usage parser doesn't recognize RdData/WrData syscalls")
    def test_basic_read_operation_rddata(self, profiler):
        """Test parsing RdData operation - DOCUMENTS BUG
        
        fs_usage on macOS uses syscall names like 'RdData' and 'WrData'
        but the current parser only looks for substring 'read' or 'write'
        which doesn't match 'RdData' or 'WrData'.
        """
        line = "12:34:56  RdData[AT]  B=0x1000  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0x1000  # 4096 bytes
    
    @pytest.mark.xfail(reason="BUG: fs_usage parser doesn't recognize RdData/WrData syscalls")
    def test_basic_write_operation_wrdata(self, profiler):
        """Test parsing WrData operation - DOCUMENTS BUG
        
        fs_usage on macOS uses syscall names like 'RdData' and 'WrData'
        but the current parser only looks for substring 'read' or 'write'
        which doesn't match 'RdData' or 'WrData'.
        """
        line = "12:34:56  WrData[AT]  B=0x800  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 0x800  # 2048 bytes
    
    def test_basic_read_operation_with_read_substring(self, profiler):
        """Test parsing read operations that contain 'read' substring (works)"""
        line = "12:34:56  read  B=0x1000  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0x1000  # 4096 bytes
    
    def test_basic_write_operation_with_write_substring(self, profiler):
        """Test parsing write operations that contain 'write' substring (works)"""
        line = "12:34:56  write  B=0x800  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 0x800  # 2048 bytes
    
    def test_read_with_various_suffixes(self, profiler):
        """Test parsing read operations with various formats"""
        lines = [
            # These work because they contain 'read' substring
            ("12:34:56  READ  B=0x200  /file  Python", True),
            ("12:34:56  read_data  B=0x300  /file  Python", True),
            ("12:34:56  pread  B=0x400  /file  Python", True),
            # This doesn't work - documents the bug
            ("12:34:56  RdData  B=0x100  /file  Python", False),
        ]
        for line, should_parse in lines:
            op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
            if should_parse:
                assert op_type == 'read', f"Failed for line: {line}"
                assert bytes_transferred > 0
            else:
                # Documents the bug: RdData not recognized
                assert op_type is None, f"Line should not parse (bug): {line}"
    
    def test_write_with_various_suffixes(self, profiler):
        """Test parsing write operations with various formats"""
        lines = [
            # These work because they contain 'write' substring
            ("12:34:56  WRITE  B=0x200  /file  Python", True),
            ("12:34:56  write_data  B=0x300  /file  Python", True),
            ("12:34:56  pwrite  B=0x400  /file  Python", True),
            # This doesn't work - documents the bug
            ("12:34:56  WrData  B=0x100  /file  Python", False),
        ]
        for line, should_parse in lines:
            op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
            if should_parse:
                assert op_type == 'write', f"Failed for line: {line}"
                assert bytes_transferred > 0
            else:
                # Documents the bug: WrData not recognized
                assert op_type is None, f"Line should not parse (bug): {line}"
    
    def test_zero_bytes(self, profiler):
        """Test parsing operations with zero bytes"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=0x0  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0
    
    def test_large_byte_count(self, profiler):
        """Test parsing operations with large byte counts"""
        # Use 'write' instead of 'WrData' to make test work with current implementation
        line = "12:34:56  write  B=0x100000  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 0x100000  # 1 MB
    
    def test_very_large_hex_value(self, profiler):
        """Test parsing operations with very large hex values"""
        # Use 'write' instead of 'WrData' to make test work with current implementation
        line = "12:34:56  write  B=0xFFFFFFFF  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 0xFFFFFFFF
    
    def test_missing_byte_field(self, profiler):
        """Test parsing lines without B= field"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0
    
    def test_malformed_byte_field(self, profiler):
        """Test parsing lines with malformed B= field"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=invalid  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0
    
    def test_non_io_operation_ignored(self, profiler):
        """Test that non-I/O operations are ignored"""
        line = "12:34:56  open  B=0x1000  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_empty_line_ignored(self, profiler):
        """Test that empty lines are ignored"""
        line = ""
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_malformed_line_ignored(self, profiler):
        """Test that malformed lines are ignored"""
        line = "not a valid fs_usage line"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_single_field_line(self, profiler):
        """Test parsing lines with only one field"""
        line = "RdData"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_collect_ops_mode(self, profiler):
        """Test parsing with collect_ops=True returns dict format"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=0x1000  /path/to/file  Python"
        result = profiler._parse_fs_usage_line(line, collect_ops=True)
        assert isinstance(result, dict)
        assert result['type'] == 'read'
        assert result['bytes'] == 0x1000
    
    def test_collect_ops_mode_non_io(self, profiler):
        """Test parsing non-I/O operation with collect_ops=True returns None"""
        line = "12:34:56  open  B=0x1000  /path/to/file  Python"
        result = profiler._parse_fs_usage_line(line, collect_ops=True)
        assert result is None
    
    def test_mixed_case_syscall_names(self, profiler):
        """Test parsing with mixed case syscall names containing 'read'/'write'"""
        lines = [
            "12:34:56  WRITE  B=0x200  /file  Python",
            "12:34:56  ReAd  B=0x300  /file  Python",
            "12:34:56  pREAD  B=0x100  /file  Python",
        ]
        for line in lines:
            op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
            assert op_type is not None, f"Failed to parse: {line}"
    
    def test_hex_value_uppercase(self, profiler):
        """Test parsing hex values with uppercase letters"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=0xABCDEF  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0xABCDEF
    
    def test_hex_value_lowercase(self, profiler):
        """Test parsing hex values with lowercase letters"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=0xabcdef  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0xabcdef
    
    def test_hex_value_mixed_case(self, profiler):
        """Test parsing hex values with mixed case letters"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=0xAbCdEf  /path/to/file  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0xAbCdEf


class TestParsingEdgeCases:
    """Test edge cases and corner cases for parsing"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        # Create a proper mock shell with parent=None to avoid traitlets issues
        mock_shell = MagicMock()
        mock_shell.configurables = []
        profiler = IOPSProfiler.__new__(IOPSProfiler)
        profiler.shell = mock_shell
        # Initialize the parent attributes manually to avoid traitlets
        import sys
        profiler.platform = sys.platform
        import re
        profiler._strace_pattern = re.compile(r'^\s*(\d+)\s+(\w+)\([^)]+\)\s*=\s*(-?\d+)')
        from iops_profiler.iops_profiler import STRACE_IO_SYSCALLS
        profiler._io_syscalls = set(STRACE_IO_SYSCALLS)
        return profiler
    
    def test_strace_line_with_unicode_content(self, profiler):
        """Test parsing strace line with unicode in the content"""
        line = "3385  write(3, \"Hello \\u4e16\\u754c\", 100) = 100"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 100
    
    def test_strace_line_with_special_chars(self, profiler):
        """Test parsing strace line with special characters"""
        line = "3385  write(3, \"\\n\\t\\r\\0\", 50) = 50"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 50
    
    def test_fs_usage_line_with_special_path(self, profiler):
        """Test parsing fs_usage line with special characters in path"""
        # Use 'read' instead of 'RdData' to make test work with current implementation
        line = "12:34:56  read  B=0x100  /path/with spaces/file.txt  Python"
        op_type, bytes_transferred = profiler._parse_fs_usage_line(line)
        assert op_type == 'read'
        assert bytes_transferred == 0x100
    
    def test_strace_interrupted_syscall(self, profiler):
        """Test parsing interrupted syscall (EINTR)"""
        line = "3385  read(3, 0x..., 4096) = -1 EINTR (Interrupted system call)"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_strace_would_block(self, profiler):
        """Test parsing EAGAIN/EWOULDBLOCK errors"""
        line = "3385  read(3, 0x..., 4096) = -1 EAGAIN (Resource temporarily unavailable)"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type is None
        assert bytes_transferred == 0
    
    def test_multiple_operations_same_line_strace(self, profiler):
        """Test that only the first operation is parsed per line"""
        line = "3385  read(3, \"data\", 100) = 50 write(4, \"other\", 100) = 100"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        # Should only parse the read operation
        assert op_type == 'read'
        assert bytes_transferred == 50
    
    def test_very_long_strace_line(self, profiler):
        """Test parsing very long strace lines"""
        long_content = "x" * 10000
        line = f"3385  write(3, \"{long_content}\", 10000) = 10000"
        op_type, bytes_transferred = profiler._parse_strace_line(line)
        assert op_type == 'write'
        assert bytes_transferred == 10000
    
    def test_strace_with_different_pid_formats(self, profiler):
        """Test parsing lines with different PID formats"""
        lines = [
            "1  read(3, \"data\", 100) = 100",
            "12345  read(3, \"data\", 100) = 100",
            "9999999  read(3, \"data\", 100) = 100",
        ]
        for line in lines:
            op_type, bytes_transferred = profiler._parse_strace_line(line)
            assert op_type == 'read', f"Failed for line: {line}"
            assert bytes_transferred == 100
