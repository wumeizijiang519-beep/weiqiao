"""Build a fail-closed BDDL-side draft for continuous progress bindings."""

import argparse
import hashlib
import json
import re
from pathlib import Path


EXPECTED = {
    "KITCHEN_SCENE4": [
        ("Close", "white_cabinet_1_bottom_region"),
        ("In", "akita_black_bowl_1", "white_cabinet_1_bottom_region"),
    ],
    "KITCHEN_SCENE6": [
        ("In", "white_yellow_mug_1", "microwave_1_heating_region"),
        ("Close", "microwave_1"),
    ],
    "LIVING_ROOM_SCENE2": [
        ("In", "alphabet_soup_1", "basket_1_contain_region"),
        ("In", "tomato_sauce_1", "basket_1_contain_region"),
    ],
    "LIVING_ROOM_SCENE5": [
        ("On", "porcelain_mug_1", "plate_1"),
        ("On", "white_yellow_mug_1", "plate_2"),
    ],
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def family_key(family):
    matches = [key for key in EXPECTED if family.startswith(key + "_")]
    if len(matches) != 1:
        raise RuntimeError("Unknown or ambiguous family: " + family)
    return matches[0]


def goal_terms(text):
    match = re.search(r"\(:goal(.*?)\n\s*\)\s*\)", text, re.S)
    if not match:
        raise RuntimeError("Missing BDDL goal")
    terms = re.findall(r"\((In|On|Close)\s+([^()]+?)\)", match.group(1))
    return [tuple([predicate] + arguments.split()) for predicate, arguments in terms]


def proposed_components(key, terms):
    components = []
    for term in terms:
        if term[0] in ("In", "On"):
            components.append({
                "kind": "object_target_distance",
                "object_symbol": term[1],
                "target_symbol": term[2],
                "runtime_binding_required": ["object body or site", "target site or region geometry"],
            })
        elif term[0] == "Close":
            components.append({
                "kind": "articulation_close_progress",
                "articulation_symbol": term[1],
                "runtime_binding_required": ["hinge or slide joint", "closed reference qpos"],
            })
    if len(components) != 2:
        raise RuntimeError("Every frozen family must expose exactly two progress components: " + key)
    return components


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha(args.manifest) != args.manifest_sha256:
        raise RuntimeError("Manifest hash mismatch")
    manifest = json.loads(args.manifest.read_text())
    families = {}
    for entry in manifest["entries"]:
        if entry["family"] in families:
            continue
        if sha(entry["bddl_path"]) != entry["bddl_sha256"]:
            raise RuntimeError("Frozen BDDL changed")
        key = family_key(entry["family"])
        terms = goal_terms(Path(entry["bddl_path"]).read_text())
        if terms != EXPECTED[key]:
            raise RuntimeError("Unexpected goal contract for " + key + ": " + repr(terms))
        families[entry["family"]] = {
            "bddl_path": entry["bddl_path"],
            "bddl_sha256": entry["bddl_sha256"],
            "goal_terms": terms,
            "proposed_components": proposed_components(key, terms),
            "runtime_binding_status": "BLOCKED_PENDING_APPROVED_INVENTORY_RETRY",
        }
    if len(families) != 4:
        raise RuntimeError("Expected four frozen families")
    result = {
        "status": "BDDL_PROGRESS_DRAFT_ONLY_NOT_EXECUTION_READY",
        "manifest_sha256": args.manifest_sha256,
        "normalization": "pending runtime initial and official success-state calibration",
        "aggregation": "mean of two bounded component progresses; formula not frozen",
        "oracle_use": "training-label-only; forbidden from critic inputs and deployment selection",
        "families": families,
    }
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / "REPORT_SHA256").write_text(sha(args.output) + "  REPORT.json\n")
    print(json.dumps({"status": result["status"], "families": len(families)}, indent=2))


if __name__ == "__main__":
    main()
