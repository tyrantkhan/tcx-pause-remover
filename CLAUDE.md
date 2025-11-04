# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

TCX Pause Remover - A Python tool that removes pause/gap periods from TCX activity files to fix Strava's elapsed time calculation for indoor rides.

**The Problem:** Strava doesn't respect pauses in TCX files, treating elapsed time = moving time. If you pause during an indoor ride, Strava still counts that time.

**The Solution:** This tool detects gaps in trackpoint timestamps and adjusts all subsequent timestamps to remove pause periods, creating a continuous activity timeline.

**Tech Stack:**
- Python 3.7+ (uses only standard library, no external dependencies)
- Text-based XML manipulation to preserve formatting

## Usage

```bash
# Basic usage
python3 tcx_pause_remover.py activity.tcx

# Dry run to preview changes
python3 tcx_pause_remover.py activity.tcx --dry-run

# Custom pause threshold (default 5 seconds)
python3 tcx_pause_remover.py activity.tcx --pause-threshold 10

# Specify output file
python3 tcx_pause_remover.py activity.tcx --output cleaned.tcx
```

## How It Works

1. **Gap Detection**: Scans all `<Time>` elements to find gaps > threshold (default 5s)
2. **Timestamp Adjustment**: Subtracts cumulative pause time from all timestamps after each gap
3. **Boundary Handling**: Uses `>= gap.end_time` check to ensure gap end times are adjusted
4. **Metadata Updates**: Adjusts `Lap StartTime` attributes and `TotalTimeSeconds` values
5. **Format Preservation**: Text-based replacements maintain original XML structure and namespaces

## Key Implementation Details

- **No external dependencies**: Uses only Python standard library (re, datetime, pathlib)
- **Preserves XML format**: Text replacement instead of XML parsing prevents namespace prefix changes (ns0:, ns2: etc.)
- **Gap boundary fix**: Critical `>= gap.end_time` check ensures continuous timestamps (using `>` causes time to go backwards)
- **No trackpoint removal**: Only adjusts timestamps; indoor rides typically have no trackpoints during pauses anyway

## Architecture

```
tcx-cropper/
├── tcx_pause_remover.py    # Main script
├── README.md               # User documentation
├── CLAUDE.md               # This file
└── *.tcx                   # Sample/test files
```

### Core Algorithm (tcx_pause_remover.py:130-166)

```python
# Build timestamp replacement map
cumulative_offset = timedelta(0)
gap_index = 0

for each timestamp in file:
    # CRITICAL: Use >= to include gap end time
    if timestamp >= gaps[gap_index].end_time:
        cumulative_offset += gap_duration
        gap_index += 1

    # Adjust by cumulative offset
    adjusted_time = original_time - cumulative_offset

    # Store replacement
    replacements[original] = adjusted
```

### Gap Detection (tcx_pause_remover.py:54-82)

```python
# Extract all timestamps
timestamps = re.findall(r'<Time>([\d\-T:.Z]+)</Time>', content)

# Find gaps > threshold
for i in range(1, len(timestamps)):
    gap_seconds = (timestamps[i] - timestamps[i-1]).total_seconds()
    if gap_seconds > threshold:
        gaps.append(Gap(timestamps[i-1], timestamps[i], gap_seconds))
```

## Common Issues & Solutions

### Issue: Time goes backwards in output
**Cause:** Using `>` instead of `>=` for gap boundary check
**Fix:** Line 131 must use `>= gap.end_time` to adjust the gap end timestamp

### Issue: Strava still shows wrong duration
**Causes:**
1. Namespace prefixes changed (ns0:, ns2: instead of no prefix, ns3:)
2. TotalTimeSeconds not updated
3. Lap StartTime not adjusted
**Fix:** Use text-based replacement, not ElementTree (which changes namespaces)

### Issue: Original formatting lost
**Cause:** Using ElementTree.write() which reformats XML
**Fix:** Read as text, use regex replacements, write as text

## Testing

Verify output has continuous timestamps:
```python
# Check for time going backwards or gaps
prev = None
for timestamp in trackpoint_times:
    diff = (timestamp - prev).total_seconds()
    if diff < 0:
        print(f"ERROR: Time goes backwards")
    elif diff > 5:
        print(f"ERROR: Gap found")
```

Expected output: No errors, all timestamps continuous with ~1s intervals
