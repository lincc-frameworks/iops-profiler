"""
Tests for display mode detection and plain text vs HTML output.

This module tests the environment detection and appropriate display mode selection.
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


class TestEnvironmentDetection:
    """Test cases for _is_notebook_environment method"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_detect_terminal_ipython(self, profiler):
        """Test detection of plain IPython (TerminalInteractiveShell) returns False"""
        mock_ipython = MagicMock()
        mock_ipython.__class__.__name__ = "TerminalInteractiveShell"

        with patch("IPython.get_ipython", return_value=mock_ipython):
            assert display.is_notebook_environment() is False

    def test_detect_graphical_environments(self, profiler):
        """Test detection of graphical environments returns True"""
        # Test various graphical IPython environments
        for shell_type in ["ZMQInteractiveShell", "InteractiveShell", "CustomShell"]:
            mock_ipython = MagicMock()
            mock_ipython.__class__.__name__ = shell_type

            with patch("IPython.get_ipython", return_value=mock_ipython):
                assert display.is_notebook_environment() is True, f"Failed for {shell_type}"

    def test_no_ipython_available(self, profiler):
        """Test when IPython is not available"""
        with patch("IPython.get_ipython", return_value=None):
            assert display.is_notebook_environment() is False

    def test_exception_during_detection(self, profiler):
        """Test graceful handling when detection raises exception"""
        with patch("IPython.get_ipython", side_effect=Exception("Test error")):
            assert display.is_notebook_environment() is False


class TestDisplayFunctions:
    """Test display functions work correctly"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    def test_plain_text_display(self, profiler, capsys):
        """Test plain text display outputs correctly and handles edge cases"""
        results = {
            "read_count": 10,
            "write_count": 5,
            "read_bytes": 10240,
            "write_bytes": 5120,
            "elapsed_time": 1.0,
            "method": "psutil (per-process)",
        }

        display.display_results_plain_text(results)
        captured = capsys.readouterr()

        # Verify key information is present
        assert "IOPS Profile Results" in captured.out
        assert "operations/second" in captured.out

        # Test with warning
        results["method"] = "⚠️ SYSTEM-WIDE (includes all processes)"
        display.display_results_plain_text(results)
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "⚠️" in captured.out

    @patch("iops_profiler.display.display")
    def test_html_display(self, mock_display, profiler):
        """Test HTML display calls display() with HTML object"""
        results = {
            "read_count": 10,
            "write_count": 5,
            "read_bytes": 10240,
            "write_bytes": 5120,
            "elapsed_time": 1.0,
            "method": "psutil (per-process)",
        }

        display.display_results_html(results)
        mock_display.assert_called_once()

    def test_display_routing(self, profiler):
        """Test display_results routes to correct display method"""
        results = {
            "read_count": 10,
            "write_count": 5,
            "read_bytes": 10240,
            "write_bytes": 5120,
            "elapsed_time": 1.0,
            "method": "psutil (per-process)",
        }

        # Test notebook routing
        with patch("iops_profiler.display.is_notebook_environment", return_value=True):
            with patch("iops_profiler.display.display_results_html") as mock_html:
                display.display_results(results)
                mock_html.assert_called_once_with(results)

        # Test terminal routing
        with patch("iops_profiler.display.is_notebook_environment", return_value=False):
            with patch("iops_profiler.display.display_results_plain_text") as mock_plain:
                display.display_results(results)
                mock_plain.assert_called_once_with(results)


class TestHistogramBehavior:
    """Test histogram display behavior in different environments"""

    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()

    @patch("iops_profiler.display.plt")
    @patch("iops_profiler.display.np")
    def test_histogram_behavior(self, mock_np, mock_plt, profiler, capsys):
        """Test histogram saves to file in terminal and shows inline in notebook"""
        import numpy as np

        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max

        operations = [
            {"type": "read", "bytes": 1024},
            {"type": "write", "bytes": 2048},
        ]

        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

        # Test terminal mode - saves to file
        with patch("iops_profiler.display.is_notebook_environment", return_value=False):
            display.generate_histograms(operations)

        mock_plt.savefig.assert_called_once()
        mock_plt.show.assert_not_called()
        mock_plt.close.assert_called_once_with(mock_fig)
        captured = capsys.readouterr()
        assert "iops_histogram.png" in captured.out

        # Reset mocks
        mock_plt.reset_mock()

        # Test notebook mode - shows inline
        with patch("iops_profiler.display.is_notebook_environment", return_value=True):
            display.generate_histograms(operations)

        mock_plt.show.assert_called_once()
        mock_plt.savefig.assert_not_called()
        mock_plt.close.assert_not_called()
