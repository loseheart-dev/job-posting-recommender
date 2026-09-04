"""Recalculate the committed expanded-job fixture statistics."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "tests/fixtures/expanded_jobs.csv"
DEFAULT_METADATA = ROOT / "tests/fixtures/expanded_jobs_metadata.json"


def calculate(csv_path: Path, metadata_path: Path) -> dict:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = reader.fieldnames or []

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    cleaning = metadata["cleaning"]["statistics"]
    collection = metadata["collection"]
    city_counts = Counter(row.get("city", "") for row in rows if row.get("city"))
    job_ids = {row["job_id"] for row in rows if row.get("job_id")}
    input_count = int(cleaning["input_count"])
    output_count = len(rows)
    duplicate_count = input_count - output_count
    if output_count != int(cleaning["output_count"]):
        raise ValueError("fixture row count does not match cleaning metadata")
    if duplicate_count != int(cleaning["duplicate_count"]):
        raise ValueError("derived duplicate count does not match cleaning metadata")

    primary_rows = city_counts.get("上海", 0) + city_counts.get("杭州", 0)
    other_counts = [count for city, count in city_counts.items() if city not in {"上海", "杭州"}]
    return {
        "fixture": csv_path.name,
        "source": metadata["source"],
        "rows": output_count,
        "columns": len(columns),
        "unique_job_id": len(job_ids),
        "input_count": input_count,
        "duplicate_count": duplicate_count,
        "keyword_count": len(set(collection["keywords"])),
        "city_count": len(city_counts),
        "city_counts": dict(sorted(city_counts.items())),
        "shanghai_hangzhou_rows": primary_rows,
        "shanghai_hangzhou_share": round(primary_rows / output_count, 6) if output_count else 0,
        "other_city_min": min(other_counts) if other_counts else 0,
        "other_city_max": max(other_counts) if other_counts else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(calculate(args.csv, args.metadata), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
