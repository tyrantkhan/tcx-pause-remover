# TCX Pause Remover

A Python tool that removes pause/gap periods from TCX activity files to fix Strava's elapsed time calculation for indoor rides.

## The Problem

Strava doesn't respect pauses in TCX files for indoor activities - it treats elapsed time = moving time. If you pause during an indoor ride (bathroom break, water refill, etc.), Strava will still count that time as part of your ride duration.

## The Solution

This tool detects gaps in your TCX file's trackpoints and:
1. Identifies pause periods (gaps > 5 seconds by default)
2. Adjusts all timestamps after each pause to remove the gap time
3. Updates lap metadata and total duration
4. Preserves the original XML formatting for compatibility

## Usage

```bash
# Basic usage - detects and removes pauses
python3 tcx_pause_remover.py activity.tcx

# Dry run to see what would be changed
python3 tcx_pause_remover.py activity.tcx --dry-run

# Custom pause threshold (default 5 seconds)
python3 tcx_pause_remover.py activity.tcx --pause-threshold 10

# Specify output file
python3 tcx_pause_remover.py activity.tcx --output cleaned.tcx
```

## Example Output

```
📊 Found 3 pause(s):
  1. 16:31:09 → 16:39:41 (8m 32s)
  2. 16:53:33 → 17:19:59 (26m 26s)
  3. 17:39:05 → 17:46:44 (7m 39s)

⏱️  Total pause time: 42m 37s

✓ Processed TCX written to: activity_no_pauses.tcx
  New duration: 101m 32s
  Removed: 42m 37s
```

## How It Works

1. **Gap Detection**: Scans all trackpoint timestamps to find gaps larger than the threshold
2. **Timestamp Adjustment**: Subtracts cumulative pause time from all timestamps after each gap
3. **Metadata Update**: Adjusts lap StartTime attributes and TotalTimeSeconds values
4. **Format Preservation**: Uses text-based replacements to maintain original XML structure

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Output

By default, creates a new file: `{original_name}_no_pauses.tcx`

The original file is never modified.

## Notes

- The tool preserves all activity data (heart rate, power, cadence, speed, etc.)
- Original XML formatting and namespace prefixes are maintained
- Works with multi-lap activities
- Safe to use - original files are never overwritten

## License

MIT
