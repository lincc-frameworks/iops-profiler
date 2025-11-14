# Work In Progress - Animated GIF Screenshots

This directory contains intermediate screenshots captured from a real Jupyter notebook browser session for creating an animated GIF demo of iops-profiler.

## Current Status
Frames captured so far (all 1400x1800px):
1. ` frame_00_empty_clean.png` - Clean empty notebook
2. `frame_01_first_cell_typed.png` - `%load_ext iops_profiler` typed
3. `frame_02_after_first_cell.png` - Extension loaded, ready for second cell
4. `frame_03_code_complete.png` - Complete code typed (7 lines with numpy/pandas/parquet)

## Still Needed
5. Final screenshot with executed output showing:
   - IOPS metrics table
   - **Full histogram visualization (must be completely visible)**

## Requirements
- All frames must be same dimensions (1400x1800px) ✓
- Final frame must show histogram completely (not cut off)
- Code must use simplified numpy/pandas/parquet example (7 lines) ✓
- Screenshots from real browser/Jupyter session (not programmatically generated) ✓

## Next Steps
1. Execute the second cell with pandas installed
2. Ensure browser viewport is sized so histogram is fully visible
3. Capture final frame
4. Create animated GIF from all frames
5. Test GIF displays correctly
6. Move final GIF to `images/demo_screenshot.gif`
