"""
Tests for spectrogram generation and timestamp parsing in iops_profiler.

This module focuses on testing spectrogram generation and timestamp extraction
from strace and fs_usage output.
"""

from unittest.mock import MagicMock, patch

import pytest

from iops_profiler import display
from iops_profiler.collector import Collector
from iops_profiler.magic import IOPSProfiler


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
    profiler.collector = Collector(mock_shell)
    return profiler


class TestTimestampParsing:
    """Test cases for timestamp parsing in strace and fs_usage output"""

    @pytest.fixture
    def collector(self):
        """Create a Collector instance with a mock shell"""
        mock_shell = MagicMock()
        return Collector(mock_shell)

    def test_strace_with_unix_timestamp(self, collector):
        """Test parsing strace line with Unix timestamp"""
        line = "1234567890.123456 3385  write(3, \"Hello\", 5) = 5"
        result = collector.parse_strace_line(line, collect_ops=True)

        assert result is not None
        assert result["type"] == "write"
        assert result["bytes"] == 5
        assert result["timestamp"] == "1234567890.123456"

    def test_strace_without_timestamp(self, collector):
        """Test parsing strace line without timestamp (backward compatibility)"""
        line = "3385  write(3, \"Hello\", 5) = 5"
        result = collector.parse_strace_line(line, collect_ops=True)

        assert result is not None
        assert result["type"] == "write"
        assert result["bytes"] == 5
        assert "timestamp" not in result

    def test_strace_read_with_timestamp(self, collector):
        """Test parsing strace read operation with timestamp"""
        line = "1234567890.654321 3385  read(3, \"data\", 4096) = 1024"
        result = collector.parse_strace_line(line, collect_ops=True)

        assert result is not None
        assert result["type"] == "read"
        assert result["bytes"] == 1024
        assert result["timestamp"] == "1234567890.654321"

    def test_fs_usage_with_timestamp(self, collector):
        """Test parsing fs_usage line with timestamp"""
        line = "12:34:56.789012  write  B=0x1000  /path/to/file  Python"
        result = collector.parse_fs_usage_line(line, collect_ops=True)

        assert result is not None
        assert result["type"] == "write"
        assert result["bytes"] == 4096  # 0x1000 in hex
        assert result["timestamp"] == "12:34:56.789012"

    def test_fs_usage_read_with_timestamp(self, collector):
        """Test parsing fs_usage read operation with timestamp"""
        line = "01:23:45.123456  read  B=0x800  /path/to/file  Python"
        result = collector.parse_fs_usage_line(line, collect_ops=True)

        assert result is not None
        assert result["type"] == "read"
        assert result["bytes"] == 2048  # 0x800 in hex
        assert result["timestamp"] == "01:23:45.123456"

    def test_fs_usage_without_timestamp(self, collector):
        """Test parsing fs_usage line without timestamp field"""
        line = "write  B=0x1000  /path/to/file  Python"
        result = collector.parse_fs_usage_line(line, collect_ops=True)

        assert result is not None
        assert result["type"] == "write"
        assert result["bytes"] == 4096
        # timestamp field may or may not be present depending on the line format


class TestSpectrogramGeneration:
    """Test cases for spectrogram generation"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    @pytest.fixture(autouse=True)
    def close_figures(self):
        """Automatically close all matplotlib figures after each test"""
        import matplotlib.pyplot as plt

        yield
        plt.close("all")

    @pytest.fixture(autouse=True)
    def mock_notebook_environment(self, profiler):
        """Mock is_notebook_environment to return True for spectrogram tests"""
        with patch("iops_profiler.display.is_notebook_environment", return_value=True):
            yield

    @patch("iops_profiler.display.plt.show")
    def test_empty_operations_list(self, mock_show, profiler):
        """Test spectrogram generation with empty operations list"""
        import matplotlib.pyplot as plt

        operations = []
        display.generate_spectrogram(operations, 1.0)

        # plt.show should not be called since no plots were created
        mock_show.assert_not_called()

        # No figures should have been created
        assert len(plt.get_fignums()) == 0

    @patch("iops_profiler.display.plt.show")
    def test_operations_without_timestamps(self, mock_show, profiler):
        """Test spectrogram generation when operations lack timestamps"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1024},
            {"type": "write", "bytes": 2048},
        ]
        display.generate_spectrogram(operations, 1.0)

        # plt.show should not be called since no plots were created
        mock_show.assert_not_called()

        # No figures should have been created
        assert len(plt.get_fignums()) == 0

    @patch("iops_profiler.display.plt.show")
    def test_unix_timestamp_format(self, mock_show, profiler):
        """Test spectrogram with Unix timestamp format (strace)"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1024, "timestamp": "1234567890.100000"},
            {"type": "write", "bytes": 2048, "timestamp": "1234567890.200000"},
            {"type": "read", "bytes": 512, "timestamp": "1234567890.300000"},
            {"type": "write", "bytes": 4096, "timestamp": "1234567890.400000"},
        ]
        display.generate_spectrogram(operations, 1.0)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots (plus colorbars)
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        # 4 axes total: 2 main plots + 2 colorbars
        assert len(axes) >= 2

        # Check first subplot (operation count)
        ax1 = axes[0]
        assert "Time" in ax1.get_xlabel()
        assert "Operation Size" in ax1.get_ylabel()
        assert ax1.get_yscale() == "log"

        # Check second subplot (total bytes)
        ax2 = axes[1]
        assert "Time" in ax2.get_xlabel()
        assert "Operation Size" in ax2.get_ylabel()
        assert ax2.get_yscale() == "log"

    @patch("iops_profiler.display.plt.show")
    def test_fs_usage_timestamp_format(self, mock_show, profiler):
        """Test spectrogram with HH:MM:SS.ffffff timestamp format (fs_usage)"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1024, "timestamp": "12:34:56.100000"},
            {"type": "write", "bytes": 2048, "timestamp": "12:34:56.200000"},
            {"type": "read", "bytes": 512, "timestamp": "12:34:56.300000"},
            {"type": "write", "bytes": 4096, "timestamp": "12:34:56.400000"},
        ]
        display.generate_spectrogram(operations, 1.0)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots (plus colorbars)
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        # 4 axes total: 2 main plots + 2 colorbars
        assert len(axes) >= 2

    @patch("iops_profiler.display.plt.show")
    def test_wide_range_of_sizes_over_time(self, mock_show, profiler):
        """Test spectrogram with wide range of operation sizes over time"""
        import matplotlib.pyplot as plt

        operations = []
        # Generate operations with varying sizes over time
        for i in range(20):
            timestamp = f"1234567890.{i:06d}"
            byte_size = 2 ** (i % 10 + 1)  # Sizes from 2 to 1024 bytes
            op_type = "read" if i % 2 == 0 else "write"
            operations.append({"type": op_type, "bytes": byte_size, "timestamp": timestamp})

        display.generate_spectrogram(operations, 1.0)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots (plus colorbars)
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        # 4 axes total: 2 main plots + 2 colorbars
        assert len(axes) >= 2

    @patch("iops_profiler.display.plt.show")
    def test_many_operations_over_time(self, mock_show, profiler):
        """Test spectrogram with many operations"""
        import matplotlib.pyplot as plt

        operations = []
        # Use 200 operations to validate handling of larger datasets without excessive test time
        for i in range(200):
            timestamp = f"1234567890.{i:06d}"
            byte_size = (i % 100 + 1) * 100
            op_type = "read" if i % 2 == 0 else "write"
            operations.append({"type": op_type, "bytes": byte_size, "timestamp": timestamp})

        display.generate_spectrogram(operations, 10.0)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

    @patch("iops_profiler.display.plt.show")
    def test_operations_with_zero_bytes_ignored(self, mock_show, profiler):
        """Test that operations with zero bytes are ignored in spectrogram"""
        operations = [
            {"type": "read", "bytes": 0, "timestamp": "1234567890.100000"},
            {"type": "write", "bytes": 2048, "timestamp": "1234567890.200000"},
            {"type": "read", "bytes": 0, "timestamp": "1234567890.300000"},
        ]
        display.generate_spectrogram(operations, 1.0)

        # Should still create a plot (has one non-zero operation)
        mock_show.assert_called_once()

    def test_no_matplotlib_installed(self, profiler):
        """Test spectrogram generation when matplotlib is not available"""
        from iops_profiler import display

        original_plt = display.plt

        # Set plt to None
        display.plt = None

        try:
            operations = [{"type": "read", "bytes": 1024, "timestamp": "1234567890.100000"}]
            # Should print warning and return early
            display.generate_spectrogram(operations, 1.0)
        finally:
            # Restore original plt
            display.plt = original_plt

    def test_no_numpy_installed(self, profiler):
        """Test spectrogram generation when numpy is not available"""
        from iops_profiler import display

        original_np = display.np

        # Set np to None
        display.np = None

        try:
            operations = [{"type": "read", "bytes": 1024, "timestamp": "1234567890.100000"}]
            # Should print warning and return early
            display.generate_spectrogram(operations, 1.0)
        finally:
            # Restore original np
            display.np = original_np

    @patch("iops_profiler.display.plt")
    @patch("iops_profiler.display.np")
    def test_spectrogram_saves_to_file_in_terminal(self, mock_np, mock_plt, profiler, capsys):
        """Test spectrogram saves to file in terminal mode"""
        import numpy as np

        mock_np.histogram2d = np.histogram2d
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.linspace = np.linspace
        mock_np.array = np.array
        mock_np.meshgrid = np.meshgrid
        mock_np.max = np.max

        operations = [
            {"type": "read", "bytes": 1024, "timestamp": "1234567890.100000"},
            {"type": "write", "bytes": 2048, "timestamp": "1234567890.200000"},
        ]

        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

        # Test terminal mode - saves to file
        with patch("iops_profiler.display.is_notebook_environment", return_value=False):
            display.generate_spectrogram(operations, 1.0)

        mock_plt.savefig.assert_called_once()
        mock_plt.show.assert_not_called()
        mock_plt.close.assert_called_once_with(mock_fig)
        captured = capsys.readouterr()
        assert "iops_spectrogram.png" in captured.out
