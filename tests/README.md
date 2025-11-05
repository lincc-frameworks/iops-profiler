# Test Suite for iops-profiler

This directory contains comprehensive tests for the iops-profiler package, focusing on parsing functions and histogram/summary statistics edge cases.

## Test Organization

### test_parsing.py
Comprehensive tests for parsing functions, covering:

#### Strace Line Parsing (`_parse_strace_line`)
- Basic read/write operations
- All I/O syscalls (read, write, pread64, pwrite64, readv, writev, preadv, pwritev, preadv2, pwritev2)
- Zero-byte operations (EOF)
- Error conditions (negative returns, interrupted syscalls, EAGAIN)
- Unfinished/resumed operations
- Non-I/O syscalls (should be ignored)
- Malformed and empty lines
- Very large byte counts (up to 1 GB+)
- Single-byte operations
- Partial reads/writes
- Multiple spaces and whitespace handling
- Unicode and special characters in content
- Different PID formats
- `collect_ops` mode for histogram collection

#### fs_usage Line Parsing (`_parse_fs_usage_line`)
- Read and write operations with 'read'/'write' substring matching
- Various byte count formats (zero, large, hex with different cases)
- Missing and malformed B= fields
- Non-I/O operations (should be ignored)
- Malformed and empty lines
- Special characters in paths
- `collect_ops` mode for histogram collection

### test_histograms.py
Comprehensive tests for histogram generation and formatting:

#### Byte Formatting (`_format_bytes`)
- All size units (B, KB, MB, GB, TB)
- Boundary values between units
- Fractional values
- Very large values (> 1 PB)
- Edge cases (negative values)

#### Histogram Generation (`_generate_histograms`)
- Empty operations list
- All-zero byte operations
- Single operation with single value
- All operations same size (edge case handling)
- Mixed read and write operations
- Only reads or only writes
- Wide range of byte sizes (1 byte to 1 GB)
- Many operations (10,000+)
- Missing matplotlib/numpy dependencies
- Mixed zero and non-zero bytes
- Very small byte counts (1-10 bytes)
- Power-of-two sizes
- Single-byte minimum values

#### Results Display (`_display_results`)
- Basic results display
- Zero operations
- Zero elapsed time (division by zero handling)
- Very small elapsed times
- System-wide measurement warning display
- Large numbers formatting
- Fractional times

### test_integration.py
Integration and utility tests:

#### Initialization
- Profiler initialization with mock shell
- I/O syscalls set population
- Strace pattern compilation

#### Extension Loading
- IPython extension loading/unloading

#### Helper Scripts (macOS)
- Helper script creation for fs_usage
- Script structure validation

#### Platform Detection
- Platform detection and storage

#### Edge Case Operations
- Multiple line parsing (strace and fs_usage)
- Mixed valid and invalid lines
- Operation collection mode

#### Results Calculation
- IOPS calculation
- Throughput calculation
- Zero-time handling



#### Async Operation Handling
- **test_async_write_across_two_lines**: Documents how strace async operations split across two lines are handled. The current implementation ignores both the `<unfinished ...>` and `<... resumed>` lines since neither contains complete operation information.

## Running Tests

Run all tests:
```bash
pytest tests/
```

Run specific test file:
```bash
pytest tests/test_parsing.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=iops_profiler --cov-report=html
```

Run skipped tests (to see failing bug tests):
```bash
pytest tests/ --run-skipped
```

## Test Statistics

- Total tests: 111
- Passing: 111

## Key Edge Cases Tested

1. **Zero-byte operations**: Read/write operations returning 0 bytes
2. **Error conditions**: Negative returns, interrupted syscalls
3. **Empty data**: Empty operation lists for histograms
4. **Single-value data**: All operations having the same byte size
5. **Zero elapsed time**: Division by zero in IOPS calculations
6. **Very large values**: GB-sized operations, millions of operations
7. **Malformed input**: Invalid hex values, truncated lines
8. **Missing dependencies**: matplotlib/numpy not available
9. **Unicode and special characters**: In file paths and data



## Implementation Notes

1. **Async operations in strace**: When strace traces async operations, it splits them across two lines with `<unfinished ...>` and `<... resumed>` markers. The current parser ignores both lines since neither contains complete operation information in a single line. This is documented in `test_async_write_across_two_lines`.

2. **Large values**: Tests for very large PIDs and byte counts pass successfully, showing the parser handles these edge cases correctly.
