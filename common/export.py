import os
import csv
import json
from typing import List, Dict, Any, Iterable

def _flatten(prefix: str, obj: Any, out: Dict[str, Any]):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, out)
    elif isinstance(obj, list):
        # Store lists as JSON strings
        out[prefix] = json.dumps(obj, ensure_ascii=False)
    else:
        out[prefix] = obj

def to_rows(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for rec in records:
        flat = {}
        _flatten("", rec, flat)
        rows.append(flat)
    return rows

def export_csv(path: str, records: Iterable[Dict[str, Any]]):
    rows = to_rows(records)
    if not rows:
        # Still create an empty file with no header
        with open(path, "w", newline="", encoding="utf-8") as f:
            pass
        return
    # union of all keys
    fieldnames = sorted({k for row in rows for k in row.keys()})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def export_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)