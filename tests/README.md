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
- **Bug Documentation**: Tests marked with `xfail` document that RdData/WrData syscalls are not recognized by current parser
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

#### Bug Documentation
Tests marked with `@pytest.mark.xfail` document known issues or edge cases:
- **fs_usage RdData/WrData**: Current parser doesn't recognize macOS fs_usage syscall names like "RdData" and "WrData"
- **Large PIDs**: Very large process IDs might cause issues
- **Extremely large byte counts**: Values larger than 64-bit int might overflow

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

Run only passing tests (exclude xfail):
```bash
pytest tests/ --ignore-xfail
```

## Test Statistics

- Total tests: 112
- Passing: 108
- Expected failures (xfail): 2 (document bugs)
- Unexpected passes (xpass): 2

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

## Bugs Documented

The test suite documents the following bugs (as failing tests per issue requirements):

1. **fs_usage parser limitation** (`test_parsing.py`):
   - Parser looks for substring 'read' or 'write' in syscall names
   - Doesn't recognize macOS-specific syscall names like "RdData" and "WrData"
   - Tests: `test_basic_read_operation_rddata`, `test_basic_write_operation_wrdata`
   - Status: Tests marked as xfail to document the bug

2. **Potential integer overflow** (`test_integration.py`):
   - Very large PIDs or byte counts might cause issues
   - Tests: `test_strace_extremely_large_pid`, `test_strace_extremely_large_byte_count`
   - Status: Tests marked as xfail to document potential future issues
