#!/usr/bin/env python3
"""TCX file pause remover that removes gaps/pauses from indoor rides.

Strava doesn't respect pauses in TCX files, treating elapsed time = moving time.
This tool detects gaps in trackpoints and adjusts timestamps to remove pause time.

This version preserves the exact XML formatting by doing text-based replacements.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class Gap:
    """Represents a detected gap in the activity."""

    start_time: datetime
    end_time: datetime
    duration_seconds: float

    @property
    def duration_str(self) -> str:
        """Human-readable gap duration."""
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes}m {seconds}s"


class TCXPauseRemover:
    """Removes pauses from TCX files by adjusting timestamps."""

    def __init__(self, gap_threshold_seconds: float = 5.0):
        """Initialize pause remover.

        Args:
            gap_threshold_seconds: Minimum gap duration to detect (default 5s)
        """
        self.gap_threshold = gap_threshold_seconds
        self.gaps: list[Gap] = []

    def parse_tcx_time(self, time_str: str) -> datetime:
        """Parse TCX timestamp format."""
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

    def format_tcx_time(self, dt: datetime) -> str:
        """Format datetime to TCX timestamp format."""
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def detect_gaps(self, content: str) -> list[Gap]:
        """Detect gaps between trackpoints by analyzing timestamps.

        Args:
            content: TCX file content as string

        Returns:
            List of detected gaps
        """
        # Extract all timestamps
        time_pattern = r'<Time>([\d\-T:.Z]+)</Time>'
        timestamps = []
        for match in re.finditer(time_pattern, content):
            timestamps.append(self.parse_tcx_time(match.group(1)))

        # Find gaps
        gaps = []
        for i in range(1, len(timestamps)):
            gap_seconds = (timestamps[i] - timestamps[i-1]).total_seconds()
            if gap_seconds > self.gap_threshold:
                gaps.append(
                    Gap(
                        start_time=timestamps[i-1],
                        end_time=timestamps[i],
                        duration_seconds=gap_seconds,
                    )
                )

        return gaps

    def remove_pauses(self, input_file: Path, output_file: Path = None, dry_run: bool = False) -> None:
        """Remove pauses from TCX file.

        Args:
            input_file: Path to input TCX file
            output_file: Path to output TCX file (default: {input}_no_pauses.tcx)
            dry_run: If True, detect gaps but don't write output
        """
        if output_file is None:
            output_file = input_file.parent / f"{input_file.stem}_no_pauses.tcx"

        # Read file as text
        with open(input_file, 'r', encoding='UTF-8') as f:
            content = f.read()

        # Detect gaps
        self.gaps = self.detect_gaps(content)

        if not self.gaps:
            print("No gaps detected - file already clean")
            return

        # Report gaps
        print(f"\nFound {len(self.gaps)} pause(s):")
        total_gap_time = 0.0
        for i, gap in enumerate(self.gaps, 1):
            print(f"  {i}. {gap.start_time.strftime('%H:%M:%S')} to {gap.end_time.strftime('%H:%M:%S')} "
                  f"({gap.duration_str})")
            total_gap_time += gap.duration_seconds

        print(f"\nTotal pause time: {int(total_gap_time // 60)}m {int(total_gap_time % 60)}s")

        if dry_run:
            print("\nDry run mode - no files modified")
            return

        # Build timestamp replacement map
        replacements = {}
        cumulative_offset = timedelta(0)
        gap_index = 0

        time_pattern = r'<Time>([\d\-T:.Z]+)</Time>'
        for match in re.finditer(time_pattern, content):
            original_time_str = match.group(1)
            original_time = self.parse_tcx_time(original_time_str)

            # Check if we've passed a gap (use >= to include the gap end time)
            if gap_index < len(self.gaps) and original_time >= self.gaps[gap_index].end_time:
                cumulative_offset += timedelta(seconds=self.gaps[gap_index].duration_seconds)
                gap_index += 1

            # Calculate adjusted time
            adjusted_time = original_time - cumulative_offset
            adjusted_time_str = self.format_tcx_time(adjusted_time)

            # Store replacement if time changed
            if original_time_str != adjusted_time_str:
                replacements[original_time_str] = adjusted_time_str

        # Apply replacements
        modified_content = content
        for original, adjusted in replacements.items():
            modified_content = modified_content.replace(f'<Time>{original}</Time>',
                                                       f'<Time>{adjusted}</Time>')
            # Also update StartTime attributes
            modified_content = modified_content.replace(f'StartTime="{original}"',
                                                       f'StartTime="{adjusted}"')

        # Update TotalTimeSeconds - find all occurrences and calculate actual duration
        # Extract first and last adjusted timestamps
        adjusted_times = []
        for match in re.finditer(time_pattern, modified_content):
            adjusted_times.append(self.parse_tcx_time(match.group(1)))

        if adjusted_times:
            actual_duration = (adjusted_times[-1] - adjusted_times[0]).total_seconds()

            # Replace TotalTimeSeconds values
            total_time_pattern = r'<TotalTimeSeconds>[\d.]+</TotalTimeSeconds>'
            modified_content = re.sub(total_time_pattern,
                                     f'<TotalTimeSeconds>{actual_duration}</TotalTimeSeconds>',
                                     modified_content)

            # Write output
            with open(output_file, 'w', encoding='UTF-8') as f:
                f.write(modified_content)

            print(f"\nProcessed TCX written to: {output_file}")
            print(f"  New duration: {int(actual_duration // 60)}m {int(actual_duration % 60)}s")
            print(f"  Removed: {int(total_gap_time // 60)}m {int(total_gap_time % 60)}s")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Remove pauses from TCX files to fix Strava's elapsed time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect pauses and create cleaned file
  %(prog)s activity.tcx

  # Dry run to see pauses without modifying
  %(prog)s activity.tcx --dry-run

  # Custom pause threshold (default 5s)
  %(prog)s activity.tcx --pause-threshold 10

  # Specify output file
  %(prog)s activity.tcx --output cleaned.tcx
        """,
    )
    parser.add_argument("input_file", type=Path, help="Input TCX file")
    parser.add_argument("-o", "--output", type=Path, help="Output TCX file (default: {input}_no_pauses.tcx)")
    parser.add_argument(
        "-t",
        "--pause-threshold",
        type=float,
        default=5.0,
        help="Minimum pause duration in seconds to detect (default: 5.0)",
    )
    parser.add_argument("-d", "--dry-run", action="store_true", help="Detect pauses but don't write output")

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"ERROR: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    remover = TCXPauseRemover(gap_threshold_seconds=args.pause_threshold)
    remover.remove_pauses(args.input_file, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
