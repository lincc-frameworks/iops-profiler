"""
Tests for display mode detection and plain text vs HTML output.

This module tests the environment detection and appropriate display mode selection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from iops_profiler.iops_profiler import IOPSProfiler


def create_test_profiler():
    """Helper function to create a test profiler instance"""
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


class TestEnvironmentDetection:
    """Test cases for _is_notebook_environment method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    def test_detect_notebook_zmq_shell(self, profiler):
        """Test detection of Jupyter notebook (ZMQInteractiveShell)"""
        mock_ipython = MagicMock()
        mock_ipython.__class__.__name__ = 'ZMQInteractiveShell'
        
        with patch('IPython.get_ipython', return_value=mock_ipython):
            assert profiler._is_notebook_environment() is True
    
    def test_detect_terminal_ipython(self, profiler):
        """Test detection of plain IPython (TerminalInteractiveShell)"""
        mock_ipython = MagicMock()
        mock_ipython.__class__.__name__ = 'TerminalInteractiveShell'
        
        with patch('IPython.get_ipython', return_value=mock_ipython):
            assert profiler._is_notebook_environment() is False
    
    def test_no_ipython_available(self, profiler):
        """Test when IPython is not available"""
        with patch('IPython.get_ipython', return_value=None):
            assert profiler._is_notebook_environment() is False
    
    def test_exception_during_detection(self, profiler):
        """Test graceful handling when detection raises exception"""
        with patch('IPython.get_ipython', side_effect=Exception("Test error")):
            assert profiler._is_notebook_environment() is False


class TestPlainTextDisplay:
    """Test cases for plain text display mode"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    def test_plain_text_display_basic(self, profiler, capsys):
        """Test plain text display with basic results"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': 'psutil (per-process)'
        }
        
        profiler._display_results_plain_text(results)
        captured = capsys.readouterr()
        
        # Check that key information is present
        assert 'IOPS Profile Results' in captured.out
        assert '10' in captured.out  # read operations
        assert '5' in captured.out   # write operations
        assert '15' in captured.out  # total operations
        assert 'operations/second' in captured.out
    
    def test_plain_text_display_with_warning(self, profiler, capsys):
        """Test plain text display includes warning for system-wide measurement"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': '⚠️ SYSTEM-WIDE (includes all processes)'
        }
        
        profiler._display_results_plain_text(results)
        captured = capsys.readouterr()
        
        # Check that warning is present
        assert 'Warning' in captured.out or '⚠️' in captured.out
    
    def test_plain_text_display_zero_time(self, profiler, capsys):
        """Test plain text display handles zero elapsed time"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 0.0,
            'method': 'psutil (per-process)'
        }
        
        # Should not raise an error
        profiler._display_results_plain_text(results)
        captured = capsys.readouterr()
        
        # Should show 0.00 IOPS
        assert 'IOPS' in captured.out


class TestHTMLDisplay:
    """Test cases for HTML display mode"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_html_display_basic(self, mock_display, profiler):
        """Test HTML display with basic results"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': 'psutil (per-process)'
        }
        
        profiler._display_results_html(results)
        mock_display.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_html_display_with_warning(self, mock_display, profiler):
        """Test HTML display includes warning for system-wide measurement"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': '⚠️ SYSTEM-WIDE (includes all processes)'
        }
        
        profiler._display_results_html(results)
        mock_display.assert_called_once()
        
        # Get the HTML argument
        call_args = mock_display.call_args
        html_obj = call_args[0][0]
        html_content = html_obj.data if hasattr(html_obj, 'data') else str(html_obj)
        
        # Should contain warning
        assert 'Warning' in html_content or '⚠️' in html_content


class TestDisplayRouting:
    """Test that _display_results routes to correct display method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    def test_routes_to_html_in_notebook(self, profiler):
        """Test that notebook environment uses HTML display"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': 'psutil (per-process)'
        }
        
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            with patch.object(profiler, '_display_results_html') as mock_html:
                with patch.object(profiler, '_display_results_plain_text') as mock_plain:
                    profiler._display_results(results)
                    
                    mock_html.assert_called_once_with(results)
                    mock_plain.assert_not_called()
    
    def test_routes_to_plain_text_in_terminal(self, profiler):
        """Test that terminal environment uses plain text display"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': 'psutil (per-process)'
        }
        
        with patch.object(profiler, '_is_notebook_environment', return_value=False):
            with patch.object(profiler, '_display_results_html') as mock_html:
                with patch.object(profiler, '_display_results_plain_text') as mock_plain:
                    profiler._display_results(results)
                    
                    mock_plain.assert_called_once_with(results)
                    mock_html.assert_not_called()


class TestHistogramSaveToFile:
    """Test that histograms are saved to file in plain IPython"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_histogram_saves_to_file_in_terminal(self, mock_np, mock_plt, profiler, capsys):
        """Test that histogram is saved to file in plain IPython"""
        import numpy as np
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1024},
            {'type': 'write', 'bytes': 2048},
        ]
        
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        with patch.object(profiler, '_is_notebook_environment', return_value=False):
            profiler._generate_histograms(operations)
        
        # Should call savefig, not show
        mock_plt.savefig.assert_called_once()
        mock_plt.show.assert_not_called()
        mock_plt.close.assert_called_once_with(mock_fig)
        
        # Should print message about saved file
        captured = capsys.readouterr()
        assert 'iops_histogram.png' in captured.out
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_histogram_shows_inline_in_notebook(self, mock_np, mock_plt, profiler):
        """Test that histogram is shown inline in notebook"""
        import numpy as np
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1024},
            {'type': 'write', 'bytes': 2048},
        ]
        
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._generate_histograms(operations)
        
        # Should call show, not savefig
        mock_plt.show.assert_called_once()
        mock_plt.savefig.assert_not_called()
        mock_plt.close.assert_not_called()
