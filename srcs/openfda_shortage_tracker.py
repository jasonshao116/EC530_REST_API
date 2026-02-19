from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


DEFAULT_BASE_URL = "https://api.fda.gov/drug/shortages.json"


@dataclass
class SnapshotDiff:
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]


def build_query_url(base_url: str, search: str | None, limit: int, skip: int) -> str:
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    if search:
        params["search"] = search
    return f"{base_url}?{urlencode(params)}"


def fetch_shortage_records(
    *,
    base_url: str = DEFAULT_BASE_URL,
    search: str | None = None,
    limit: int = 100,
    skip: int = 0,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    url = build_query_url(base_url=base_url, search=search, limit=limit, skip=skip)
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"openFDA HTTP error {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"openFDA network error: {exc.reason}") from exc

    results = payload.get("results", [])
    if not isinstance(results, list):
        raise RuntimeError("Unexpected API response: 'results' is not a list")
    return [item for item in results if isinstance(item, dict)]


def _pick_first(record: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _record_key(record: dict[str, Any]) -> str:
    candidate = _pick_first(
        record,
        [
            "id",
            "shortage_id",
            "shortage_number",
            "set_id",
            "application_number",
            "product_ndc",
        ],
    )
    if candidate is not None:
        return str(candidate)
    return json.dumps(record, sort_keys=True)


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": _record_key(record),
        "drug_name": _pick_first(
            record,
            ["drug_name", "proprietary_name", "generic_name", "product_description"],
        ),
        "status": _pick_first(
            record,
            ["status", "shortage_status", "current_status", "availability_status"],
        ),
        "reason": _pick_first(
            record,
            ["reason", "reason_for_shortage", "shortage_reason"],
        ),
        "last_updated": _pick_first(
            record,
            ["last_updated", "revision_date", "updated_at", "created"],
        ),
        "raw": record,
    }


def build_snapshot(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for record in records:
        normalized = normalize_record(record)
        snapshot[normalized["key"]] = normalized
    return snapshot


def diff_snapshots(
    old_snapshot: dict[str, dict[str, Any]],
    new_snapshot: dict[str, dict[str, Any]],
) -> SnapshotDiff:
    old_keys = set(old_snapshot)
    new_keys = set(new_snapshot)

    added = [new_snapshot[key] for key in sorted(new_keys - old_keys)]
    removed = [old_snapshot[key] for key in sorted(old_keys - new_keys)]

    changed: list[dict[str, Any]] = []
    for key in sorted(old_keys & new_keys):
        old_value = old_snapshot[key]
        new_value = new_snapshot[key]
        if old_value != new_value:
            changed.append(
                {
                    "key": key,
                    "before": old_value,
                    "after": new_value,
                }
            )

    return SnapshotDiff(added=added, removed=removed, changed=changed)


def load_snapshot(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise RuntimeError(f"Snapshot file is invalid JSON object: {path}")
    return content


def save_snapshot(path: Path, snapshot: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")


def track_shortages(
    *,
    snapshot_path: Path,
    base_url: str,
    search: str | None,
    limit: int,
    skip: int,
    save: bool,
) -> tuple[int, SnapshotDiff]:
    records = fetch_shortage_records(
        base_url=base_url,
        search=search,
        limit=limit,
        skip=skip,
    )
    new_snapshot = build_snapshot(records)
    old_snapshot = load_snapshot(snapshot_path)
    diff = diff_snapshots(old_snapshot, new_snapshot)

    if save:
        save_snapshot(snapshot_path, new_snapshot)

    return len(records), diff


def _format_preview(items: list[dict[str, Any]], label: str, max_items: int = 5) -> list[str]:
    lines = [f"{label}: {len(items)}"]
    for item in items[:max_items]:
        name = item.get("drug_name") or "unknown"
        key = item.get("key") or "unknown"
        status = item.get("status") or "n/a"
        lines.append(f"  - {name} [{key}] status={status}")
    if len(items) > max_items:
        lines.append(f"  ... and {len(items) - max_items} more")
    return lines


def _format_changed(changed: list[dict[str, Any]], max_items: int = 5) -> list[str]:
    lines = [f"Changed: {len(changed)}"]
    for item in changed[:max_items]:
        before = item["before"]
        after = item["after"]
        lines.append(
            "  - "
            f"{after.get('drug_name') or 'unknown'} [{item.get('key')}] "
            f"status {before.get('status')} -> {after.get('status')}"
        )
    if len(changed) > max_items:
        lines.append(f"  ... and {len(changed) - max_items} more")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track drug shortage updates from openFDA")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="openFDA shortage endpoint URL",
    )
    parser.add_argument("--search", default=None, help="openFDA search query")
    parser.add_argument("--limit", type=int, default=100, help="max records per request")
    parser.add_argument("--skip", type=int, default=0, help="result offset")
    parser.add_argument(
        "--snapshot",
        default="data/shortage_snapshot.json",
        help="path to local snapshot file",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="do not write snapshot to disk",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be > 0")
    if args.skip < 0:
        raise SystemExit("--skip must be >= 0")

    snapshot_path = Path(args.snapshot)
    total, diff = track_shortages(
        snapshot_path=snapshot_path,
        base_url=args.base_url,
        search=args.search,
        limit=args.limit,
        skip=args.skip,
        save=not args.no_save,
    )

    now = datetime.now(timezone.utc).isoformat()
    output_lines = [f"Timestamp (UTC): {now}", f"Fetched records: {total}"]
    output_lines.extend(_format_preview(diff.added, "Added"))
    output_lines.extend(_format_preview(diff.removed, "Removed"))
    output_lines.extend(_format_changed(diff.changed))
    print("\n".join(output_lines))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())