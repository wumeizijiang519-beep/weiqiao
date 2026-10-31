"""Freeze and audit exact runtime bindings for the continuous progress label."""

import argparse
import hashlib
import json
from pathlib import Path

from progress_metric import BINDINGS, family_key


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exactly_once(values, name):
    if values.count(name) != 1:
        raise RuntimeError(f"Binding {name!r} occurs {values.count(name)} times")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--inventory-sha256", required=True)
    parser.add_argument("--metric-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha(args.inventory) != args.inventory_sha256:
        raise RuntimeError("Runtime inventory hash mismatch")
    inventory = json.loads(args.inventory.read_text())
    if inventory.get("status") != "RUNTIME_INVENTORY_ONLY_NO_ACTIONS":
        raise RuntimeError("Runtime inventory did not pass")
    reports = {}
    seen = set()
    for family, row in inventory["families"].items():
        key = family_key(family)
        if key in seen:
            raise RuntimeError("Duplicate task family key")
        seen.add(key)
        spec = BINDINGS[key]
        for body, site in spec["distances"]:
            exactly_once(row["bodies"], body)
            exactly_once(row["sites"], site)
        if spec["articulation"] is not None:
            joint, closed, span = spec["articulation"]
            exactly_once(row["joints"], joint)
            if closed != 0.0 or span <= 0:
                raise RuntimeError("Invalid articulation contract")
        reports[family] = spec
    if seen != set(BINDINGS):
        raise RuntimeError("Not all four frozen families were inventoried")
    result = {
        "status": "PROGRESS_CONTRACT_PASS",
        "inventory_sha256": args.inventory_sha256,
        "metric_source_sha256": sha(args.metric_source),
        "formula": "mean clipped relative boundary distance improvement; articulated tasks add clipped closed-qpos improvement",
        "distance_floor_m": 0.05,
        "component_clip": [-1.0, 1.0],
        "deployment_input": False,
        "training_label_only": True,
        "families": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / "PROGRESS_CONTRACT_PASS").write_text("\n")
    (args.output.parent / "REPORT_SHA256").write_text(sha(args.output) + "  REPORT.json\n")
    print(json.dumps({"status": result["status"], "families": len(reports)}, indent=2))


if __name__ == "__main__":
    main()
