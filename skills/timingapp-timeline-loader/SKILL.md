---
name: timingapp-timeline-loader
description: Load Timing App timeline data from local SQLite database for journaling summaries
---

# Timing App Timeline Loader

You are a productivity data analyst that retrieves work and timeline information from the Timing App. Your goal is to load this information into memory to provide a sense of what the user did over a specific range of time.

## Data Source

**Local SQLite Database**:
*   Path: `~/Library/Application Support/info.eurocomp.Timing2/SQLite.db`
*   **Why**: Contains granular "auto-tracked" data (Window Titles, File Paths, URLs) necessary for detailed activity logging.

## Usage

This skill includes a Python script `generate_timeline.py` that handles the entire extraction and formatting process.

### Command
Execute the script using the `bash` tool:

```bash
python3 ~/.claude/skills/timingapp-timeline-loader/generate_timeline.py --date YYYY-MM-DD --format json
```

- **Output**: Writes JSON to `./tmp/ttl=30d/<date>_timing/timeline.json` by default.
- **Stdout**: Use `--output -` to print the JSON directly.

### Summary Mode

For aggregated work sessions (grouped by time proximity, with project breakdown):

```bash
python3 ~/.claude/skills/timingapp-timeline-loader/generate_timeline.py --date YYYY-MM-DD --summary --output -
```

Returns JSON with: `date`, `total_hours`, `by_project` (hours per project), `work_sessions` (time ranges with project/app breakdown).

## Logic Overview (Internal)

The script performs the following steps:
1.  **Extract**: Uses a read-only SQLite backup to query `AppActivity`, `Application`, `Title`, and `Path`.
2.  **Normalize**: Converts timestamps to `America/Los_Angeles` and emits raw activity rows.
3.  **Format**: Outputs JSON (or Markdown if requested).
