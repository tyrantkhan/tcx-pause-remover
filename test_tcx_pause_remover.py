#!/usr/bin/env python3
"""Tests for TCX Pause Remover."""

import re
import tempfile
from datetime import datetime
from pathlib import Path

from tcx_pause_remover import TCXPauseRemover


def test_gap_detection():
    """Test that gaps are correctly detected."""
    # Create a sample TCX with known gaps
    content = """<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Biking">
      <Lap StartTime="2025-11-03T12:00:00.000Z">
        <Track>
          <Trackpoint><Time>2025-11-03T12:00:00.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:00:01.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:00:02.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:05:00.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:05:01.000Z</Time></Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>"""

    remover = TCXPauseRemover(gap_threshold_seconds=5.0)
    gaps = remover.detect_gaps(content)

    assert len(gaps) == 1, f"Expected 1 gap, found {len(gaps)}"
    assert gaps[0].duration_seconds == 298.0, f"Expected 298s gap, got {gaps[0].duration_seconds}s"
    print("✓ Gap detection test passed")


def test_timestamp_adjustment():
    """Test that timestamps are correctly adjusted after gaps."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tcx', delete=False) as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Biking">
      <Lap StartTime="2025-11-03T12:00:00.000Z">
        <TotalTimeSeconds>301.0</TotalTimeSeconds>
        <Track>
          <Trackpoint><Time>2025-11-03T12:00:00.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:00:01.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:00:02.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:05:00.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:05:01.000Z</Time></Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>""")
        input_file = Path(f.name)

    output_file = input_file.parent / f"{input_file.stem}_test_output.tcx"

    try:
        remover = TCXPauseRemover(gap_threshold_seconds=5.0)
        remover.remove_pauses(input_file, output_file)

        # Read output and verify
        with open(output_file, 'r') as f:
            content = f.read()

        # Extract trackpoint times
        times = re.findall(r'<Time>([\d\-T:.Z]+)</Time>', content)

        # Should have 5 trackpoints
        assert len(times) == 5, f"Expected 5 trackpoints, found {len(times)}"

        # Parse times
        parsed_times = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in times]

        # Check no time goes backwards
        for i in range(1, len(parsed_times)):
            diff = (parsed_times[i] - parsed_times[i-1]).total_seconds()
            assert diff >= 0, f"Time went backwards at index {i}: {diff}s"

        # Check no gaps > threshold
        for i in range(1, len(parsed_times)):
            diff = (parsed_times[i] - parsed_times[i-1]).total_seconds()
            assert diff <= 5, f"Gap found at index {i}: {diff}s"

        # Check total duration (5 trackpoints from 0-4 seconds, gap removed)
        total_duration = (parsed_times[-1] - parsed_times[0]).total_seconds()
        assert total_duration == 3.0, f"Expected 3s total duration, got {total_duration}s"

        # Verify TotalTimeSeconds was updated
        assert '<TotalTimeSeconds>3.0</TotalTimeSeconds>' in content, "TotalTimeSeconds not updated"

        print("✓ Timestamp adjustment test passed")

    finally:
        input_file.unlink()
        if output_file.exists():
            output_file.unlink()


def test_no_gaps():
    """Test file with no gaps passes through correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tcx', delete=False) as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Biking">
      <Lap StartTime="2025-11-03T12:00:00.000Z">
        <Track>
          <Trackpoint><Time>2025-11-03T12:00:00.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:00:01.000Z</Time></Trackpoint>
          <Trackpoint><Time>2025-11-03T12:00:02.000Z</Time></Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>""")
        input_file = Path(f.name)

    try:
        remover = TCXPauseRemover(gap_threshold_seconds=5.0)
        gaps = remover.detect_gaps(open(input_file).read())

        assert len(gaps) == 0, f"Expected no gaps, found {len(gaps)}"
        print("✓ No gaps test passed")

    finally:
        input_file.unlink()


def test_example_file():
    """Test the example.tcx file in the repo."""
    example_file = Path(__file__).parent / "example.tcx"

    if not example_file.exists():
        print("⚠ Skipping example.tcx test (file not found)")
        return

    remover = TCXPauseRemover(gap_threshold_seconds=5.0)

    with open(example_file, 'r') as f:
        content = f.read()

    gaps = remover.detect_gaps(content)

    assert len(gaps) > 0, "Expected at least one gap in example.tcx"
    print(f"✓ Example file test passed (found {len(gaps)} gap(s))")


if __name__ == "__main__":
    print("Running TCX Pause Remover tests...\n")

    test_gap_detection()
    test_timestamp_adjustment()
    test_no_gaps()
    test_example_file()

    print("\n✅ All tests passed!")
