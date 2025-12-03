"""
Display module for IOPS Profiler.

This module contains all the display and visualization functionality including:
- Environment detection (notebook vs terminal)
- Result formatting and display (HTML and plain text)
- Histogram generation
- Byte formatting utilities
"""

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    plt = None
    np = None

from IPython.display import HTML, display

# Constants for heatmap generation
HEATMAP_SIZE_BIN_EXPANSION = 0.01  # 1% expansion for size bins (0.99 to 1.01)
HEATMAP_SINGLE_VALUE_EXPANSION = 0.1  # 10% expansion for single value (0.9 to 1.1)
HEATMAP_SIZE_BINS = 30  # Number of bins for operation size (log scale)
HEATMAP_TIME_BINS = 50  # Number of bins for time


def is_notebook_environment():
    """Detect if running in a graphical notebook environment vs plain IPython.

    Returns:
        bool: True if in a notebook with display capabilities, False for plain IPython
    """
    try:
        # Check if we're in IPython
        from IPython import get_ipython

        ipython = get_ipython()
        if ipython is None:
            return False

        # Check the IPython kernel type
        # TerminalInteractiveShell is definitively non-graphical (plain IPython)
        # Everything else (ZMQInteractiveShell, etc.) is treated as graphical
        # This handles Jupyter notebooks, JupyterLab, Google Colab, and other
        # interactive environments with display capabilities
        ipython_type = type(ipython).__name__

        # Return False only for TerminalInteractiveShell (plain IPython)
        # Return True for all other types (assume graphical capabilities)
        return ipython_type != "TerminalInteractiveShell"
    except (ImportError, AttributeError, Exception):
        # If we can't determine, assume plain environment
        return False


def format_bytes(bytes_val):
    """Format bytes into human-readable string"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def format_time_axis(max_time_seconds):
    """Determine appropriate time unit and formatting for axis display.

    Args:
        max_time_seconds: Maximum time value in seconds

    Returns:
        tuple: (time_unit_name, time_divisor, decimal_places)
    """
    if max_time_seconds >= 1.0:
        # Use seconds
        return "s", 1.0, 2
    elif max_time_seconds >= 0.001:
        # Use milliseconds
        return "ms", 0.001, 1
    elif max_time_seconds >= 0.000001:
        # Use microseconds
        return "μs", 0.000001, 1
    else:
        # Use nanoseconds
        return "ns", 0.000000001, 0


def generate_heatmap(operations, elapsed_time):
    """Generate time-series heatmaps for I/O operations over time

    Args:
        operations: List of dicts with 'type', 'bytes', and 'timestamp' keys
        elapsed_time: Total elapsed time of the profiled code
    """
    if not plt or not np:
        print("⚠️ matplotlib or numpy not available. Cannot generate heatmaps.")
        return

    if not operations:
        print("⚠️ No operations captured for heatmap generation.")
        return

    # Filter operations with timestamps and non-zero bytes
    ops_with_time = [op for op in operations if "timestamp" in op and op["bytes"] > 0]

    if not ops_with_time:
        print("⚠️ No operations with timestamps for heatmap generation.")
        return

    # Convert timestamps to relative time (seconds from start)
    # Handle both Unix timestamp format (strace) and HH:MM:SS.ffffff format (fs_usage)
    start_timestamp = None
    relative_times = []

    for op in ops_with_time:
        ts_str = op["timestamp"]
        # Check if it's Unix timestamp format (decimal number)
        if ":" not in ts_str:
            # Unix timestamp from strace
            timestamp = float(ts_str)
            if start_timestamp is None:
                start_timestamp = timestamp
            relative_times.append(timestamp - start_timestamp)
        else:
            # HH:MM:SS.ffffff format from fs_usage
            # Parse the time format
            parts = ts_str.split(":")
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                timestamp = hours * 3600 + minutes * 60 + seconds
                if start_timestamp is None:
                    start_timestamp = timestamp
                relative_times.append(timestamp - start_timestamp)

    # Handle case where no valid timestamps were extracted
    if not relative_times:
        print("⚠️ Could not parse timestamps for heatmap generation.")
        return

    # Extract byte sizes
    byte_sizes = [op["bytes"] for op in ops_with_time]

    # Create log-scale bins for byte sizes
    min_bytes = max(1, min(byte_sizes))
    max_bytes = max(byte_sizes)

    if min_bytes == max_bytes:
        # Single value case: expand range to create meaningful bins
        expansion_factor = 1 - HEATMAP_SINGLE_VALUE_EXPANSION
        size_bins = np.array([min_bytes * expansion_factor, min_bytes / expansion_factor])
    else:
        # Create bins in log space - using fewer bins for heatmap
        expansion_factor = 1 - HEATMAP_SIZE_BIN_EXPANSION
        size_bins = np.logspace(
            np.log10(min_bytes * expansion_factor),
            np.log10(max_bytes / expansion_factor),
            HEATMAP_SIZE_BINS,
        )

    # Create time bins
    max_time = max(relative_times)
    if max_time == 0:
        max_time = elapsed_time
    time_bins = np.linspace(0, max_time, HEATMAP_TIME_BINS)

    # Determine appropriate time unit and formatting for axis
    time_unit, time_divisor, decimal_places = format_time_axis(max_time)

    # Create 2D histograms for operation counts
    all_count_hist, time_edges, size_edges = np.histogram2d(
        relative_times, byte_sizes, bins=[time_bins, size_bins]
    )

    # Create 2D histograms for total bytes
    all_bytes_hist, _, _ = np.histogram2d(
        relative_times, byte_sizes, bins=[time_bins, size_bins], weights=byte_sizes
    )

    # Create figure with 2 subplots (operation count and total bytes)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Operation count heatmap
    # Use pcolormesh for heatmap visualization
    time_centers = (time_edges[:-1] + time_edges[1:]) / 2
    size_centers = (size_edges[:-1] + size_edges[1:]) / 2
    # Convert time to appropriate unit for display
    time_mesh, size_mesh = np.meshgrid(time_centers / time_divisor, size_centers)

    im1 = ax1.pcolormesh(time_mesh, size_mesh, all_count_hist.T, cmap="viridis", shading="auto")
    ax1.set_yscale("log")
    ax1.set_xlabel(f"Time ({time_unit})")
    ax1.set_ylabel("Operation Size (bytes, log scale)")
    ax1.set_title("I/O Operation Count Over Time")
    plt.colorbar(im1, ax=ax1, label="Number of Operations")
    ax1.grid(True, alpha=0.3)

    # Format x-axis tick labels with limited decimal places
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.{decimal_places}f}'))

    # Plot 2: Total bytes spectrogram (with auto-scaling)
    max_bytes_in_bin = np.max(all_bytes_hist) if all_bytes_hist.size > 0 else 0
    if max_bytes_in_bin < 1024:
        unit, divisor = "B", 1
    elif max_bytes_in_bin < 1024**2:
        unit, divisor = "KB", 1024
    elif max_bytes_in_bin < 1024**3:
        unit, divisor = "MB", 1024**2
    elif max_bytes_in_bin < 1024**4:
        unit, divisor = "GB", 1024**3
    else:
        unit, divisor = "TB", 1024**4

    im2 = ax2.pcolormesh(time_mesh, size_mesh, (all_bytes_hist / divisor).T, cmap="plasma", shading="auto")
    ax2.set_yscale("log")
    ax2.set_xlabel(f"Time ({time_unit})")
    ax2.set_ylabel("Operation Size (bytes, log scale)")
    ax2.set_title("I/O Total Bytes Over Time")
    plt.colorbar(im2, ax=ax2, label=f"Total Bytes ({unit})")
    ax2.grid(True, alpha=0.3)

    # Format x-axis tick labels with limited decimal places
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.{decimal_places}f}'))

    plt.tight_layout()

    # Check if running in plain IPython vs notebook environment
    if is_notebook_environment():
        # In notebook, show the plot inline
        plt.show()
    else:
        # In plain IPython, save to file
        output_file = "iops_heatmap.png"
        plt.savefig(output_file, dpi=100, bbox_inches="tight")
        plt.close(fig)
        print(f"📊 Heatmap saved to: {output_file}")


def generate_histograms(operations):
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
    read_ops = [op["bytes"] for op in operations if op["type"] == "read" and op["bytes"] > 0]
    write_ops = [op["bytes"] for op in operations if op["type"] == "write" and op["bytes"] > 0]
    all_ops = [op["bytes"] for op in operations if op["bytes"] > 0]

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
        # Generate 200 bins evenly spaced in log space
        # Expand the range slightly to ensure min and max values are included
        bin_edges = np.logspace(np.log10(min_bytes * 0.99), np.log10(max_bytes * 1.01), 201)

    # Compute histograms using numpy
    all_counts, _ = np.histogram(all_ops, bins=bin_edges)
    read_counts, _ = (
        np.histogram(read_ops, bins=bin_edges) if read_ops else (np.zeros(len(bin_edges) - 1), bin_edges)
    )
    write_counts, _ = (
        np.histogram(write_ops, bins=bin_edges) if write_ops else (np.zeros(len(bin_edges) - 1), bin_edges)
    )

    # Compute byte sums per bin using weighted histograms
    all_bytes, _ = np.histogram(all_ops, bins=bin_edges, weights=all_ops)
    read_bytes, _ = (
        np.histogram(read_ops, bins=bin_edges, weights=read_ops)
        if read_ops
        else (np.zeros(len(bin_edges) - 1), bin_edges)
    )
    write_bytes, _ = (
        np.histogram(write_ops, bins=bin_edges, weights=write_ops)
        if write_ops
        else (np.zeros(len(bin_edges) - 1), bin_edges)
    )

    # Compute bin centers for plotting
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Operation count histogram
    # Use different line styles to ensure visibility when lines overlap
    ax1.plot(bin_centers, all_counts, label="All Operations", linewidth=2, alpha=0.8, linestyle="-")
    if read_ops:
        ax1.plot(bin_centers, read_counts, label="Reads", linewidth=2, alpha=0.8, linestyle="--")
    if write_ops:
        ax1.plot(bin_centers, write_counts, label="Writes", linewidth=2, alpha=0.8, linestyle=":")
    ax1.set_xscale("log")
    ax1.set_xlabel("Bytes per Operation (log scale)")
    ax1.set_ylabel("Count of Operations")
    ax1.set_title("I/O Operation Count Distribution")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Total bytes histogram (with auto-scaling)
    max_bytes_in_bin = np.max(all_bytes) if len(all_bytes) > 0 else 0
    if max_bytes_in_bin < 1024:
        unit, divisor = "B", 1
    elif max_bytes_in_bin < 1024**2:
        unit, divisor = "KB", 1024
    elif max_bytes_in_bin < 1024**3:
        unit, divisor = "MB", 1024**2
    elif max_bytes_in_bin < 1024**4:
        unit, divisor = "GB", 1024**3
    else:
        unit, divisor = "TB", 1024**4

    # Use different line styles to ensure visibility when lines overlap
    ax2.plot(bin_centers, all_bytes / divisor, label="All Operations", linewidth=2, alpha=0.8, linestyle="-")
    if read_ops:
        ax2.plot(bin_centers, read_bytes / divisor, label="Reads", linewidth=2, alpha=0.8, linestyle="--")
    if write_ops:
        ax2.plot(bin_centers, write_bytes / divisor, label="Writes", linewidth=2, alpha=0.8, linestyle=":")
    ax2.set_xscale("log")
    ax2.set_xlabel("Bytes per Operation (log scale)")
    ax2.set_ylabel(f"Total Bytes ({unit})")
    ax2.set_title("I/O Total Bytes Distribution")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Check if running in plain IPython vs notebook environment
    if is_notebook_environment():
        # In notebook, show the plot inline
        plt.show()
    else:
        # In plain IPython, save to file
        # Using fixed filename as specified - overwrites on repeated runs
        output_file = "iops_histogram.png"
        plt.savefig(output_file, dpi=100, bbox_inches="tight")
        plt.close(fig)
        print(f"📊 Histogram saved to: {output_file}")


def display_results_plain_text(results):
    """Display results in plain text format for terminal/console environments.

    Args:
        results: Dictionary containing profiling results
    """
    total_ops = results["read_count"] + results["write_count"]
    total_bytes = results["read_bytes"] + results["write_bytes"]
    iops = total_ops / results["elapsed_time"] if results["elapsed_time"] > 0 else 0
    throughput = total_bytes / results["elapsed_time"] if results["elapsed_time"] > 0 else 0

    # Create a simple text-based table
    print("\n" + "=" * 70)
    print(f"IOPS Profile Results ({results['method']})")
    print("=" * 70)
    print(f"{'Execution Time:':<30} {results['elapsed_time']:.4f} seconds")
    print(f"{'Read Operations:':<30} {results['read_count']:,}")
    print(f"{'Write Operations:':<30} {results['write_count']:,}")
    print(f"{'Total Operations:':<30} {total_ops:,}")
    print(f"{'Bytes Read:':<30} {format_bytes(results['read_bytes'])} ({results['read_bytes']:,} bytes)")
    print(f"{'Bytes Written:':<30} {format_bytes(results['write_bytes'])} ({results['write_bytes']:,} bytes)")
    print(f"{'Total Bytes:':<30} {format_bytes(total_bytes)} ({total_bytes:,} bytes)")
    print("-" * 70)
    print(f"{'IOPS:':<30} {iops:.2f} operations/second")
    print(f"{'Throughput:':<30} {format_bytes(throughput)}/second")
    print("=" * 70)

    if "⚠️" in results["method"]:
        print("\n⚠️  Warning: System-wide measurement includes I/O from all processes.")
        print("   Results may not accurately reflect your code's I/O activity.\n")


def display_results_html(results):
    """Display results in HTML format for notebook environments.

    Args:
        results: Dictionary containing profiling results
    """
    total_ops = results["read_count"] + results["write_count"]
    total_bytes = results["read_bytes"] + results["write_bytes"]
    iops = total_ops / results["elapsed_time"] if results["elapsed_time"] > 0 else 0
    throughput = total_bytes / results["elapsed_time"] if results["elapsed_time"] > 0 else 0

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
                <td colspan="2">IOPS Profile Results ({results["method"]})</td>
            </tr>
            <tr>
                <td>Execution Time</td>
                <td>{results["elapsed_time"]:.4f} seconds</td>
            </tr>
            <tr>
                <td>Read Operations</td>
                <td>{results["read_count"]:,}</td>
            </tr>
            <tr>
                <td>Write Operations</td>
                <td>{results["write_count"]:,}</td>
            </tr>
            <tr>
                <td>Total Operations</td>
                <td>{total_ops:,}</td>
            </tr>
            <tr>
                <td>Bytes Read</td>
                <td>{format_bytes(results["read_bytes"])} ({results["read_bytes"]:,} bytes)</td>
            </tr>
            <tr>
                <td>Bytes Written</td>
                <td>{format_bytes(results["write_bytes"])} ({results["write_bytes"]:,} bytes)</td>
            </tr>
            <tr>
                <td>Total Bytes</td>
                <td>{format_bytes(total_bytes)} ({total_bytes:,} bytes)</td>
            </tr>
            <tr>
                <td><strong>IOPS</strong></td>
                <td><strong>{iops:.2f} operations/second</strong></td>
            </tr>
            <tr>
                <td><strong>Throughput</strong></td>
                <td><strong>{format_bytes(throughput)}/second</strong></td>
            </tr>
        </table>
    """

    if "⚠️" in results["method"]:
        html += """
        <div class="iops-warning">
            ⚠️ Warning: System-wide measurement includes I/O from all processes.
            Results may not accurately reflect your code's I/O activity.
        </div>
        """

    html += "</div>"
    display(HTML(html))


def display_results(results):
    """Display results in appropriate format based on environment.

    Args:
        results: Dictionary containing profiling results
    """
    if is_notebook_environment():
        display_results_html(results)
    else:
        display_results_plain_text(results)
