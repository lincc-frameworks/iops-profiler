# Next Session: Complete the Final Frame Capture

## Current Status (Token Usage: >200k this session)
Environment is 95% ready - just needs kernel restart to pick up pyarrow.

## Issue Discovered
Pyarrow was installed via `pip install --user pyarrow` but the Jupyter kernel was already running and doesn't see the new package. The kernel needs to be restarted for it to import pyarrow correctly.

## Steps to Complete (Next Session)
1. **Restart Jupyter server entirely** (not just kernel) so it picks up pyarrow:
   ```bash
   pkill -f jupyter
   cd /home/runner/work/iops-profiler/iops-profiler
   jupyter notebook --no-browser --port=8909 --NotebookApp.token='' --NotebookApp.password='' &
   ```

2. **Open browser and navigate** to http://localhost:8909/notebooks/demo_final.ipynb
   - Viewport: 1400x2400px (use `playwright-browser_resize`)

3. **Execute cells cleanly**:
   - Click first cell, Shift+Enter (load extension)
   - Wait 2 seconds
   - Click second cell, Shift+Enter (run profiler with histogram)
   - Wait 15 seconds for execution

4. **Capture final screenshot**:
   - Use `playwright-browser_take_screenshot` with fullPage=true
   - Save as `images/screenshots_wip/frame_04_final_output.png`
   - Verify histogram is FULLY visible (not cut off)

5. **Create animated GIF**:
   ```python
   from PIL import Image
   frames = []
   for i in range(5):
       if i == 0:
           img = Image.open('images/screenshots_wip/frame_00_empty_clean.png')
       elif i == 1:
           img = Image.open('images/screenshots_wip/frame_01_first_cell_typed.png')
       elif i == 2:
           img = Image.open('images/screenshots_wip/frame_02_after_first_cell.png')
       elif i == 3:
           img = Image.open('images/screenshots_wip/frame_03_code_complete.png')
       else:
           img = Image.open('images/screenshots_wip/frame_04_final_output.png')
       
       # Hold final frame longer
       if i == 4:
           for _ in range(4):  # Hold 2 seconds (4 frames at 0.5s each)
               frames.append(img.copy())
       else:
           frames.append(img)
   
   frames[0].save(
       'images/demo_screenshot.gif',
       save_all=True,
       append_images=frames[1:],
       duration=500,  # 500ms per frame = 2 fps
       loop=0
   )
   ```

6. **Verify and commit**:
   - Test GIF displays correctly
   - Remove WIP directory: `rm -rf images/screenshots_wip FINAL_SESSION_STATUS.md NEXT_SESSION_STEPS.md`
   - Commit with: "Complete: Animated GIF with real browser screenshots"

## Files Ready
- ✅ demo_final.ipynb (correct code)
- ✅ pandas installed
- ✅ **pyarrow installed** (just needs kernel restart to see it)
- ✅ 4/5 frames captured correctly
- ✅ Browser configured with correct viewport size

## Expected Result
Animated GIF (~150-200KB) showing:
1. First cell typed (1s hold)
2. First cell executed (1s hold)
3. Second cell with complete code (1s hold)
4. **Final output with FULL histogram** (2s hold)

All frames 1400x1800px (or taller for final frame to show full histogram).

## Alternative if Pyarrow Still Doesn't Work
Change demo code to NOT use parquet - use CSV instead:
```python
%%iops --histogram
import numpy as np
import pandas as pd

# Generate and save random data
data = pd.DataFrame(np.random.randn(100000, 3))
data.to_csv('data.csv', index=False)
```

This doesn't require pyarrow and will still generate interesting I/O patterns for the histogram.
