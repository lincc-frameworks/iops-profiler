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
