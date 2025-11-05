"""
Tests for histogram generation and summary statistics in iops_profiler.

This module focuses on testing histogram generation and formatting functions,
including various edge cases like empty data, single values, and boundary conditions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
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


class TestFormatBytes:
    """Test cases for _format_bytes method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    def test_bytes_formatting(self, profiler):
        """Test formatting bytes (< 1 KB)"""
        assert profiler._format_bytes(0) == "0.00 B"
        assert profiler._format_bytes(1) == "1.00 B"
        assert profiler._format_bytes(512) == "512.00 B"
        assert profiler._format_bytes(1023) == "1023.00 B"
    
    def test_kilobytes_formatting(self, profiler):
        """Test formatting kilobytes"""
        assert profiler._format_bytes(1024) == "1.00 KB"
        assert profiler._format_bytes(1536) == "1.50 KB"
        assert profiler._format_bytes(2048) == "2.00 KB"
        assert profiler._format_bytes(1024 * 1023) == "1023.00 KB"
    
    def test_megabytes_formatting(self, profiler):
        """Test formatting megabytes"""
        assert profiler._format_bytes(1024 * 1024) == "1.00 MB"
        assert profiler._format_bytes(1024 * 1024 * 1.5) == "1.50 MB"
        assert profiler._format_bytes(1024 * 1024 * 100) == "100.00 MB"
    
    def test_gigabytes_formatting(self, profiler):
        """Test formatting gigabytes"""
        assert profiler._format_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert profiler._format_bytes(1024 * 1024 * 1024 * 2.5) == "2.50 GB"
    
    def test_terabytes_formatting(self, profiler):
        """Test formatting terabytes"""
        assert profiler._format_bytes(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        assert profiler._format_bytes(1024 * 1024 * 1024 * 1024 * 5.25) == "5.25 TB"
    
    def test_very_large_values(self, profiler):
        """Test formatting very large values (> 1 PB)"""
        # Values larger than 1024 TB should still show as TB
        result = profiler._format_bytes(1024 * 1024 * 1024 * 1024 * 2000)
        assert "TB" in result
        assert float(result.split()[0]) > 1000
    
    def test_edge_case_boundary_values(self, profiler):
        """Test boundary values between units"""
        assert "B" in profiler._format_bytes(1023.9)
        assert "KB" in profiler._format_bytes(1024.1)
        assert "KB" in profiler._format_bytes(1024 * 1023.9)
        assert "MB" in profiler._format_bytes(1024 * 1024.1)
    
    def test_fractional_bytes(self, profiler):
        """Test formatting fractional byte values"""
        result = profiler._format_bytes(100.5)
        assert result == "100.50 B"
    
    def test_negative_values(self, profiler):
        """Test formatting negative values (edge case, shouldn't happen in practice)"""
        # The function doesn't explicitly handle negative values,
        # but we should document the behavior
        result = profiler._format_bytes(-1024)
        assert "-" in result or result.startswith("-")


class TestGenerateHistograms:
    """Test cases for _generate_histograms method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_empty_operations_list(self, mock_np, mock_plt, profiler):
        """Test histogram generation with empty operations list"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = []
        # Should print warning and return early
        profiler._generate_histograms(operations)
        # plt.subplots should not be called
        mock_plt.subplots.assert_not_called()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_operations_with_all_zeros(self, mock_np, mock_plt, profiler):
        """Test histogram generation when all operations have zero bytes"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 0},
            {'type': 'write', 'bytes': 0},
            {'type': 'read', 'bytes': 0},
        ]
        # Should print warning and return early
        profiler._generate_histograms(operations)
        # plt.subplots should not be called
        mock_plt.subplots.assert_not_called()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_single_operation_single_value(self, mock_np, mock_plt, profiler):
        """Test histogram generation with single operation"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [{'type': 'read', 'bytes': 1024}]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should create plots with adjusted bin edges
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_all_operations_same_size(self, mock_np, mock_plt, profiler):
        """Test histogram generation when all operations have the same byte size"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 4096},
            {'type': 'write', 'bytes': 4096},
            {'type': 'read', 'bytes': 4096},
            {'type': 'write', 'bytes': 4096},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should handle edge case where min == max
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_mixed_operations(self, mock_np, mock_plt, profiler):
        """Test histogram generation with mixed read and write operations"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1024},
            {'type': 'write', 'bytes': 2048},
            {'type': 'read', 'bytes': 4096},
            {'type': 'write', 'bytes': 8192},
            {'type': 'read', 'bytes': 512},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._generate_histograms(operations)
        
        # Should create plots with separate read/write lines
        mock_plt.subplots.assert_called_once()
        mock_plt.tight_layout.assert_called_once()
        mock_plt.show.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_only_reads(self, mock_np, mock_plt, profiler):
        """Test histogram generation with only read operations"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1024},
            {'type': 'read', 'bytes': 2048},
            {'type': 'read', 'bytes': 4096},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should create plots with only read line
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_only_writes(self, mock_np, mock_plt, profiler):
        """Test histogram generation with only write operations"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'write', 'bytes': 1024},
            {'type': 'write', 'bytes': 2048},
            {'type': 'write', 'bytes': 4096},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should create plots with only write line
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_wide_range_of_byte_sizes(self, mock_np, mock_plt, profiler):
        """Test histogram generation with wide range of byte sizes (1 byte to 1 GB)"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1},
            {'type': 'write', 'bytes': 10},
            {'type': 'read', 'bytes': 100},
            {'type': 'write', 'bytes': 1000},
            {'type': 'read', 'bytes': 10000},
            {'type': 'write', 'bytes': 100000},
            {'type': 'read', 'bytes': 1000000},
            {'type': 'write', 'bytes': 10000000},
            {'type': 'read', 'bytes': 100000000},
            {'type': 'write', 'bytes': 1000000000},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should create plots with log scale
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_many_operations(self, mock_np, mock_plt, profiler):
        """Test histogram generation with many operations"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        # Generate 10000 operations
        operations = []
        for i in range(10000):
            operations.append({
                'type': 'read' if i % 2 == 0 else 'write',
                'bytes': (i % 100 + 1) * 100
            })
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should handle large datasets efficiently
        mock_plt.subplots.assert_called_once()
    
    def test_no_matplotlib_installed(self, profiler):
        """Test histogram generation when matplotlib is not available"""
        # Save original plt
        from iops_profiler import iops_profiler
        original_plt = iops_profiler.plt
        
        # Set plt to None
        iops_profiler.plt = None
        
        try:
            operations = [{'type': 'read', 'bytes': 1024}]
            # Should print warning and return early
            profiler._generate_histograms(operations)
        finally:
            # Restore original plt
            iops_profiler.plt = original_plt
    
    def test_no_numpy_installed(self, profiler):
        """Test histogram generation when numpy is not available"""
        # Save original np
        from iops_profiler import iops_profiler
        original_np = iops_profiler.np
        
        # Set np to None
        iops_profiler.np = None
        
        try:
            operations = [{'type': 'read', 'bytes': 1024}]
            # Should print warning and return early
            profiler._generate_histograms(operations)
        finally:
            # Restore original np
            iops_profiler.np = original_np
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_mixed_zero_and_nonzero_bytes(self, mock_np, mock_plt, profiler):
        """Test histogram generation with mixed zero and non-zero bytes"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 0},
            {'type': 'write', 'bytes': 1024},
            {'type': 'read', 'bytes': 0},
            {'type': 'write', 'bytes': 2048},
            {'type': 'read', 'bytes': 0},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should filter out zero-byte operations
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_very_small_bytes(self, mock_np, mock_plt, profiler):
        """Test histogram generation with very small byte counts (1-10 bytes)"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1},
            {'type': 'write', 'bytes': 2},
            {'type': 'read', 'bytes': 3},
            {'type': 'write', 'bytes': 5},
            {'type': 'read', 'bytes': 8},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should handle small values correctly
        mock_plt.subplots.assert_called_once()


class TestDisplayResults:
    """Test cases for _display_results method"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_basic_results(self, mock_display, profiler):
        """Test displaying basic results"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': 'psutil (per-process)'
        }
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        mock_display.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_zero_operations(self, mock_display, profiler):
        """Test displaying results with zero operations"""
        results = {
            'read_count': 0,
            'write_count': 0,
            'read_bytes': 0,
            'write_bytes': 0,
            'elapsed_time': 1.0,
            'method': 'psutil (per-process)'
        }
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        mock_display.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_zero_time(self, mock_display, profiler):
        """Test displaying results with zero elapsed time"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 0.0,
            'method': 'psutil (per-process)'
        }
        
        # Should handle division by zero gracefully
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        mock_display.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_very_small_time(self, mock_display, profiler):
        """Test displaying results with very small elapsed time"""
        results = {
            'read_count': 100,
            'write_count': 50,
            'read_bytes': 102400,
            'write_bytes': 51200,
            'elapsed_time': 0.001,
            'method': 'psutil (per-process)'
        }
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        mock_display.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_system_wide_warning(self, mock_display, profiler):
        """Test that system-wide measurement shows warning"""
        results = {
            'read_count': 10,
            'write_count': 5,
            'read_bytes': 10240,
            'write_bytes': 5120,
            'elapsed_time': 1.0,
            'method': '⚠️ SYSTEM-WIDE (includes all processes)'
        }
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        # Check that display was called
        mock_display.assert_called_once()
        # Get the HTML argument - it's an HTML object, so we need to access its data
        call_args = mock_display.call_args
        html_obj = call_args[0][0]
        # Get the actual HTML content from the HTML object
        html_content = html_obj.data if hasattr(html_obj, 'data') else str(html_obj)
        # Should contain warning text
        assert 'Warning' in html_content or '⚠️' in html_content
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_large_numbers(self, mock_display, profiler):
        """Test displaying results with large numbers"""
        results = {
            'read_count': 1000000,
            'write_count': 500000,
            'read_bytes': 1024 * 1024 * 1024 * 10,  # 10 GB
            'write_bytes': 1024 * 1024 * 1024 * 5,   # 5 GB
            'elapsed_time': 60.0,
            'method': 'strace (per-process)'
        }
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        mock_display.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.display')
    def test_display_fractional_time(self, mock_display, profiler):
        """Test displaying results with fractional elapsed time"""
        results = {
            'read_count': 42,
            'write_count': 13,
            'read_bytes': 43008,
            'write_bytes': 13312,
            'elapsed_time': 1.2345,
            'method': 'psutil (per-process)'
        }
        
        # Mock environment detection to simulate notebook environment
        with patch.object(profiler, '_is_notebook_environment', return_value=True):
            profiler._display_results(results)
        mock_display.assert_called_once()


class TestHistogramEdgeCases:
    """Test edge cases specific to histogram generation"""
    
    @pytest.fixture
    def profiler(self):
        """Create an IOPSProfiler instance with a mock shell"""
        return create_test_profiler()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_single_byte_minimum(self, mock_np, mock_plt, profiler):
        """Test histogram when minimum byte size is 1"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1},
            {'type': 'write', 'bytes': 2},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should handle minimum value of 1 correctly
        mock_plt.subplots.assert_called_once()
    
    @patch('iops_profiler.iops_profiler.plt')
    @patch('iops_profiler.iops_profiler.np')
    def test_power_of_two_sizes(self, mock_np, mock_plt, profiler):
        """Test histogram with power-of-two byte sizes"""
        mock_np.histogram = np.histogram
        mock_np.logspace = np.logspace
        mock_np.log10 = np.log10
        mock_np.array = np.array
        mock_np.zeros = np.zeros
        mock_np.max = np.max
        
        operations = [
            {'type': 'read', 'bytes': 1},
            {'type': 'write', 'bytes': 2},
            {'type': 'read', 'bytes': 4},
            {'type': 'write', 'bytes': 8},
            {'type': 'read', 'bytes': 16},
            {'type': 'write', 'bytes': 32},
            {'type': 'read', 'bytes': 64},
            {'type': 'write', 'bytes': 128},
            {'type': 'read', 'bytes': 256},
            {'type': 'write', 'bytes': 512},
            {'type': 'read', 'bytes': 1024},
        ]
        
        # Mock pyplot components
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        profiler._generate_histograms(operations)
        
        # Should create proper bins for power-of-two sizes
        mock_plt.subplots.assert_called_once()
