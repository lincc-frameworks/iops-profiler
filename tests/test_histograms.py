"""
Tests for histogram generation and summary statistics in iops_profiler.

This module focuses on testing histogram generation and formatting functions,
including various edge cases like empty data, single values, and boundary conditions.
"""

from unittest.mock import MagicMock, patch

import pytest
from iops_profiler import display
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
    from iops_profiler.collector import Collector

    profiler.collector = Collector(mock_shell)
    return profiler


class TestFormatBytes:
    """Test cases for _format_bytes method"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_bytes_formatting(self, profiler):
        """Test formatting bytes (< 1 KB)"""
        assert display.format_bytes(0) == "0.00 B"
        assert display.format_bytes(1) == "1.00 B"
        assert display.format_bytes(512) == "512.00 B"
        assert display.format_bytes(1023) == "1023.00 B"

    def test_kilobytes_formatting(self, profiler):
        """Test formatting kilobytes"""
        assert display.format_bytes(1024) == "1.00 KB"
        assert display.format_bytes(1536) == "1.50 KB"
        assert display.format_bytes(2048) == "2.00 KB"
        assert display.format_bytes(1024 * 1023) == "1023.00 KB"

    def test_megabytes_formatting(self, profiler):
        """Test formatting megabytes"""
        assert display.format_bytes(1024 * 1024) == "1.00 MB"
        assert display.format_bytes(1024 * 1024 * 1.5) == "1.50 MB"
        assert display.format_bytes(1024 * 1024 * 100) == "100.00 MB"

    def test_gigabytes_formatting(self, profiler):
        """Test formatting gigabytes"""
        assert display.format_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert display.format_bytes(1024 * 1024 * 1024 * 2.5) == "2.50 GB"

    def test_terabytes_formatting(self, profiler):
        """Test formatting terabytes"""
        assert display.format_bytes(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        assert display.format_bytes(1024 * 1024 * 1024 * 1024 * 5.25) == "5.25 TB"

    def test_very_large_values(self, profiler):
        """Test formatting very large values (> 1 PB)"""
        # Values larger than 1024 TB should still show as TB
        result = display.format_bytes(1024 * 1024 * 1024 * 1024 * 2000)
        assert "TB" in result
        assert float(result.split()[0]) > 1000

    def test_edge_case_boundary_values(self, profiler):
        """Test boundary values between units"""
        assert "B" in display.format_bytes(1023.9)
        assert "KB" in display.format_bytes(1024.1)
        assert "KB" in display.format_bytes(1024 * 1023.9)
        assert "MB" in display.format_bytes(1024 * 1024.1)

    def test_fractional_bytes(self, profiler):
        """Test formatting fractional byte values"""
        result = display.format_bytes(100.5)
        assert result == "100.50 B"

    def test_negative_values(self, profiler):
        """Test formatting negative values (edge case, shouldn't happen in practice)"""
        # The function doesn't explicitly handle negative values,
        # but we should document the behavior
        result = display.format_bytes(-1024)
        assert "-" in result or result.startswith("-")


class TestGenerateHistograms:
    """Test cases for _generate_histograms method"""

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
        """Mock _is_notebook_environment to return True for histogram tests"""
        with patch("iops_profiler.display.is_notebook_environment", return_value=True):
            yield

    @patch("iops_profiler.display.plt.show")
    def test_empty_operations_list(self, mock_show, profiler):
        """Test histogram generation with empty operations list"""
        import matplotlib.pyplot as plt

        operations = []
        # Should print warning and return early
        display.generate_histograms(operations)

        # plt.show should not be called since no plots were created
        mock_show.assert_not_called()

        # No figures should have been created
        assert len(plt.get_fignums()) == 0

    @patch("iops_profiler.display.plt.show")
    def test_operations_with_all_zeros(self, mock_show, profiler):
        """Test histogram generation when all operations have zero bytes"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 0},
            {"type": "write", "bytes": 0},
            {"type": "read", "bytes": 0},
        ]
        # Should print warning and return early
        display.generate_histograms(operations)

        # plt.show should not be called since no plots were created
        mock_show.assert_not_called()

        # No figures should have been created
        assert len(plt.get_fignums()) == 0

    @patch("iops_profiler.display.plt.show")
    def test_single_operation_single_value(self, mock_show, profiler):
        """Test histogram generation with single operation"""
        import matplotlib.pyplot as plt

        operations = [{"type": "read", "bytes": 1024}]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure
        figs = plt.get_fignums()
        assert len(figs) == 1

        # Get the figure and axes
        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2  # Two subplots

        # Check first subplot (operation count)
        ax1 = axes[0]
        assert ax1.get_xscale() == "log"
        assert "Count of Operations" in ax1.get_ylabel()
        assert "Bytes per Operation" in ax1.get_xlabel()

        # Check that lines were plotted
        lines = ax1.get_lines()
        assert len(lines) >= 1  # At least "All Operations" line

        # Check second subplot (total bytes)
        ax2 = axes[1]
        assert ax2.get_xscale() == "log"
        assert "Total Bytes" in ax2.get_ylabel()
        assert "Bytes per Operation" in ax2.get_xlabel()

        # Check that lines were plotted
        lines = ax2.get_lines()
        assert len(lines) >= 1  # At least "All Operations" line

    @patch("iops_profiler.display.plt.show")
    def test_all_operations_same_size(self, mock_show, profiler):
        """Test histogram generation when all operations have the same byte size"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 4096},
            {"type": "write", "bytes": 4096},
            {"type": "read", "bytes": 4096},
            {"type": "write", "bytes": 4096},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Verify that both axes have data plotted
        ax1 = axes[0]
        lines = ax1.get_lines()
        assert len(lines) >= 3  # All, Reads, Writes

        # Verify the data contains correct counts
        # All operations line should show 4 operations total
        all_ops_line = [line for line in lines if line.get_label() == "All Operations"][0]
        ydata = all_ops_line.get_ydata()
        assert sum(ydata) == 4  # 4 total operations

    @patch("iops_profiler.display.plt.show")
    def test_mixed_operations(self, mock_show, profiler):
        """Test histogram generation with mixed read and write operations"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1024},
            {"type": "write", "bytes": 2048},
            {"type": "read", "bytes": 4096},
            {"type": "write", "bytes": 8192},
            {"type": "read", "bytes": 512},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Check first subplot has three lines (All, Reads, Writes)
        ax1 = axes[0]
        lines = ax1.get_lines()
        assert len(lines) == 3
        labels = [line.get_label() for line in lines]
        assert "All Operations" in labels
        assert "Reads" in labels
        assert "Writes" in labels

        # Verify correct operation counts
        all_ops_line = [line for line in lines if line.get_label() == "All Operations"][0]
        reads_line = [line for line in lines if line.get_label() == "Reads"][0]
        writes_line = [line for line in lines if line.get_label() == "Writes"][0]

        assert sum(all_ops_line.get_ydata()) == 5  # 5 total operations
        assert sum(reads_line.get_ydata()) == 3  # 3 read operations
        assert sum(writes_line.get_ydata()) == 2  # 2 write operations

    @patch("iops_profiler.display.plt.show")
    def test_only_reads(self, mock_show, profiler):
        """Test histogram generation with only read operations"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1024},
            {"type": "read", "bytes": 2048},
            {"type": "read", "bytes": 4096},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Check first subplot has two lines (All, Reads only)
        ax1 = axes[0]
        lines = ax1.get_lines()
        assert len(lines) == 2
        labels = [line.get_label() for line in lines]
        assert "All Operations" in labels
        assert "Reads" in labels
        assert "Writes" not in labels  # No writes should be present

        # Verify correct operation counts
        all_ops_line = [line for line in lines if line.get_label() == "All Operations"][0]
        reads_line = [line for line in lines if line.get_label() == "Reads"][0]

        assert sum(all_ops_line.get_ydata()) == 3  # 3 total operations
        assert sum(reads_line.get_ydata()) == 3  # 3 read operations

    @patch("iops_profiler.display.plt.show")
    def test_only_writes(self, mock_show, profiler):
        """Test histogram generation with only write operations"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "write", "bytes": 1024},
            {"type": "write", "bytes": 2048},
            {"type": "write", "bytes": 4096},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Check first subplot has two lines (All, Writes only)
        ax1 = axes[0]
        lines = ax1.get_lines()
        assert len(lines) == 2
        labels = [line.get_label() for line in lines]
        assert "All Operations" in labels
        assert "Writes" in labels
        assert "Reads" not in labels  # No reads should be present

        # Verify correct operation counts
        all_ops_line = [line for line in lines if line.get_label() == "All Operations"][0]
        writes_line = [line for line in lines if line.get_label() == "Writes"][0]

        assert sum(all_ops_line.get_ydata()) == 3  # 3 total operations
        assert sum(writes_line.get_ydata()) == 3  # 3 write operations

    @patch("iops_profiler.display.plt.show")
    def test_wide_range_of_byte_sizes(self, mock_show, profiler):
        """Test histogram generation with wide range of byte sizes (1 byte to 1 GB)"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1},
            {"type": "write", "bytes": 10},
            {"type": "read", "bytes": 100},
            {"type": "write", "bytes": 1000},
            {"type": "read", "bytes": 10000},
            {"type": "write", "bytes": 100000},
            {"type": "read", "bytes": 1000000},
            {"type": "write", "bytes": 10000000},
            {"type": "read", "bytes": 100000000},
            {"type": "write", "bytes": 1000000000},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Both axes should have log scale on x-axis
        ax1, ax2 = axes
        assert ax1.get_xscale() == "log"
        assert ax2.get_xscale() == "log"

        # Verify the data spans a wide range
        all_ops_line = [line for line in ax1.get_lines() if line.get_label() == "All Operations"][0]
        xdata = all_ops_line.get_xdata()
        assert min(xdata) >= 1  # At least 1 byte
        assert max(xdata) <= 1000000000  # At most 1 GB

    @patch("iops_profiler.display.plt.show")
    def test_many_operations(self, mock_show, profiler):
        """Test histogram generation with many operations"""
        import matplotlib.pyplot as plt

        # Generate 10000 operations
        operations = []
        for i in range(10000):
            operations.append({"type": "read" if i % 2 == 0 else "write", "bytes": (i % 100 + 1) * 100})

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Verify correct operation counts
        ax1 = axes[0]
        all_ops_line = [line for line in ax1.get_lines() if line.get_label() == "All Operations"][0]
        reads_line = [line for line in ax1.get_lines() if line.get_label() == "Reads"][0]
        writes_line = [line for line in ax1.get_lines() if line.get_label() == "Writes"][0]

        assert sum(all_ops_line.get_ydata()) == 10000  # 10000 total operations
        assert sum(reads_line.get_ydata()) == 5000  # 5000 read operations
        assert sum(writes_line.get_ydata()) == 5000  # 5000 write operations

    def test_no_matplotlib_installed(self, profiler):
        """Test histogram generation when matplotlib is not available"""
        # Save original plt
        from iops_profiler import display

        original_plt = display.plt

        # Set plt to None
        display.plt = None

        try:
            operations = [{"type": "read", "bytes": 1024}]
            # Should print warning and return early
            display.generate_histograms(operations)
        finally:
            # Restore original plt
            display.plt = original_plt

    def test_no_numpy_installed(self, profiler):
        """Test histogram generation when numpy is not available"""
        # Save original np
        from iops_profiler import display

        original_np = display.np

        # Set np to None
        display.np = None

        try:
            operations = [{"type": "read", "bytes": 1024}]
            # Should print warning and return early
            display.generate_histograms(operations)
        finally:
            # Restore original np
            display.np = original_np

    @patch("iops_profiler.display.plt.show")
    def test_mixed_zero_and_nonzero_bytes(self, mock_show, profiler):
        """Test histogram generation with mixed zero and non-zero bytes"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 0},
            {"type": "write", "bytes": 1024},
            {"type": "read", "bytes": 0},
            {"type": "write", "bytes": 2048},
            {"type": "read", "bytes": 0},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Should only count non-zero byte operations (2 writes)
        ax1 = axes[0]
        all_ops_line = [line for line in ax1.get_lines() if line.get_label() == "All Operations"][0]
        writes_line = [line for line in ax1.get_lines() if line.get_label() == "Writes"][0]

        assert sum(all_ops_line.get_ydata()) == 2  # Only 2 non-zero operations
        assert sum(writes_line.get_ydata()) == 2  # 2 write operations

    @patch("iops_profiler.display.plt.show")
    def test_very_small_bytes(self, mock_show, profiler):
        """Test histogram generation with very small byte counts (1-10 bytes)"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1},
            {"type": "write", "bytes": 2},
            {"type": "read", "bytes": 3},
            {"type": "write", "bytes": 5},
            {"type": "read", "bytes": 8},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Verify correct operation counts for small values
        ax1 = axes[0]
        all_ops_line = [line for line in ax1.get_lines() if line.get_label() == "All Operations"][0]
        reads_line = [line for line in ax1.get_lines() if line.get_label() == "Reads"][0]
        writes_line = [line for line in ax1.get_lines() if line.get_label() == "Writes"][0]

        assert sum(all_ops_line.get_ydata()) == 5  # 5 total operations
        assert sum(reads_line.get_ydata()) == 3  # 3 read operations
        assert sum(writes_line.get_ydata()) == 2  # 2 write operations


class TestDisplayResults:
    """Test cases for _display_results method"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    @pytest.fixture(autouse=True)
    def mock_notebook_environment(self, profiler):
        """Mock _is_notebook_environment to return True for display tests"""
        with patch("iops_profiler.display.is_notebook_environment", return_value=True):
            yield

    @patch("iops_profiler.display.display")
    def test_display_basic_results(self, mock_display, profiler):
        """Test displaying basic results"""
        results = {
            "read_count": 10,
            "write_count": 5,
            "read_bytes": 10240,
            "write_bytes": 5120,
            "elapsed_time": 1.0,
            "method": "psutil (per-process)",
        }

        display.display_results(results)
        mock_display.assert_called_once()

    @patch("iops_profiler.display.display")
    def test_display_zero_operations(self, mock_display, profiler):
        """Test displaying results with zero operations"""
        results = {
            "read_count": 0,
            "write_count": 0,
            "read_bytes": 0,
            "write_bytes": 0,
            "elapsed_time": 1.0,
            "method": "psutil (per-process)",
        }

        display.display_results(results)
        mock_display.assert_called_once()

    @patch("iops_profiler.display.display")
    def test_display_zero_time(self, mock_display, profiler):
        """Test displaying results with zero elapsed time"""
        results = {
            "read_count": 10,
            "write_count": 5,
            "read_bytes": 10240,
            "write_bytes": 5120,
            "elapsed_time": 0.0,
            "method": "psutil (per-process)",
        }

        # Should handle division by zero gracefully
        display.display_results(results)
        mock_display.assert_called_once()

    @patch("iops_profiler.display.display")
    def test_display_very_small_time(self, mock_display, profiler):
        """Test displaying results with very small elapsed time"""
        results = {
            "read_count": 100,
            "write_count": 50,
            "read_bytes": 102400,
            "write_bytes": 51200,
            "elapsed_time": 0.001,
            "method": "psutil (per-process)",
        }

        display.display_results(results)
        mock_display.assert_called_once()

    @patch("iops_profiler.display.display")
    def test_display_system_wide_warning(self, mock_display, profiler):
        """Test that system-wide measurement shows warning"""
        results = {
            "read_count": 10,
            "write_count": 5,
            "read_bytes": 10240,
            "write_bytes": 5120,
            "elapsed_time": 1.0,
            "method": "⚠️ SYSTEM-WIDE (includes all processes)",
        }

        display.display_results(results)
        # Check that display was called
        mock_display.assert_called_once()
        # Get the HTML argument - it's an HTML object, so we need to access its data
        call_args = mock_display.call_args
        html_obj = call_args[0][0]
        # Get the actual HTML content from the HTML object
        html_content = html_obj.data if hasattr(html_obj, "data") else str(html_obj)
        # Should contain warning text
        assert "Warning" in html_content or "⚠️" in html_content

    @patch("iops_profiler.display.display")
    def test_display_large_numbers(self, mock_display, profiler):
        """Test displaying results with large numbers"""
        results = {
            "read_count": 1000000,
            "write_count": 500000,
            "read_bytes": 1024 * 1024 * 1024 * 10,  # 10 GB
            "write_bytes": 1024 * 1024 * 1024 * 5,  # 5 GB
            "elapsed_time": 60.0,
            "method": "strace (per-process)",
        }

        display.display_results(results)
        mock_display.assert_called_once()

    @patch("iops_profiler.display.display")
    def test_display_fractional_time(self, mock_display, profiler):
        """Test displaying results with fractional elapsed time"""
        results = {
            "read_count": 42,
            "write_count": 13,
            "read_bytes": 43008,
            "write_bytes": 13312,
            "elapsed_time": 1.2345,
            "method": "psutil (per-process)",
        }

        display.display_results(results)
        mock_display.assert_called_once()


class TestHistogramEdgeCases:
    """Test edge cases specific to histogram generation"""

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
        """Mock _is_notebook_environment to return True for histogram tests"""
        with patch("iops_profiler.display.is_notebook_environment", return_value=True):
            yield

    @patch("iops_profiler.display.plt.show")
    def test_single_byte_minimum(self, mock_show, profiler):
        """Test histogram when minimum byte size is 1"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1},
            {"type": "write", "bytes": 2},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Verify correct operation counts
        ax1 = axes[0]
        all_ops_line = [line for line in ax1.get_lines() if line.get_label() == "All Operations"][0]
        assert sum(all_ops_line.get_ydata()) == 2  # 2 total operations

        # Verify x-axis data includes small values
        xdata = all_ops_line.get_xdata()
        assert min(xdata) >= 0.99  # Minimum should be close to 1 byte (0.99 due to range expansion)

    @patch("iops_profiler.display.plt.show")
    def test_power_of_two_sizes(self, mock_show, profiler):
        """Test histogram with power-of-two byte sizes"""
        import matplotlib.pyplot as plt

        operations = [
            {"type": "read", "bytes": 1},
            {"type": "write", "bytes": 2},
            {"type": "read", "bytes": 4},
            {"type": "write", "bytes": 8},
            {"type": "read", "bytes": 16},
            {"type": "write", "bytes": 32},
            {"type": "read", "bytes": 64},
            {"type": "write", "bytes": 128},
            {"type": "read", "bytes": 256},
            {"type": "write", "bytes": 512},
            {"type": "read", "bytes": 1024},
        ]

        display.generate_histograms(operations)

        # plt.show should be called once
        mock_show.assert_called_once()

        # Should create one figure with two subplots
        figs = plt.get_fignums()
        assert len(figs) == 1

        fig = plt.figure(figs[0])
        axes = fig.get_axes()
        assert len(axes) == 2

        # Verify correct operation counts
        ax1 = axes[0]
        all_ops_line = [line for line in ax1.get_lines() if line.get_label() == "All Operations"][0]
        reads_line = [line for line in ax1.get_lines() if line.get_label() == "Reads"][0]
        writes_line = [line for line in ax1.get_lines() if line.get_label() == "Writes"][0]

        assert sum(all_ops_line.get_ydata()) == 11  # 11 total operations
        assert sum(reads_line.get_ydata()) == 6  # 6 read operations
        assert sum(writes_line.get_ydata()) == 5  # 5 write operations
