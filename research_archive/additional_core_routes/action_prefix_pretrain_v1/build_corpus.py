"""Build an outcome-blind, physical-group-deduplicated action corpus."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ALLOWED_ROOTS = ("progress_pairwise_qgf_v1", "paired_action_v1")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candidates = []
    rejected = []
    for root_name in ALLOWED_ROOTS:
        for bank in sorted((args.root / root_name).rglob("bank.npz")):
            config_path = bank.parent / "config.json"
            if not config_path.exists():
                rejected.append({"path": str(bank.relative_to(args.root)), "reason": "missing_config"})
                continue
            config = json.loads(config_path.read_text())
            group = config.get("physical_input_group")
            if not isinstance(group, str) or len(group) != 64:
                rejected.append({"path": str(bank.relative_to(args.root)), "reason": "invalid_group"})
                continue
            candidates.append((group, bank))

    actions, groups, sources, bank_hashes = [], [], [], []
    selected = {}
    for group, bank in sorted(candidates):
        if group in selected:
            continue
        with np.load(bank, allow_pickle=False) as payload:
            if "candidates_native" not in payload.files:
                rejected.append({"path": str(bank.relative_to(args.root)), "reason": "missing_native_actions"})
                continue
            value = np.asarray(payload["candidates_native"], dtype=np.float32)
        if value.shape != (8, 32, 7) or not np.isfinite(value).all():
            rejected.append({"path": str(bank.relative_to(args.root)), "reason": f"invalid_shape_{value.shape}"})
            continue
        selected[group] = bank
        actions.append(value)
        groups.append(group)
        sources.append(str(bank.relative_to(args.root)))
        bank_hashes.append(sha(bank))

    if len(actions) < 16:
        raise RuntimeError(f"Too few unique physical groups: {len(actions)}")
    split = np.asarray([int(group[:8], 16) % 10 < 8 for group in groups], dtype=np.bool_)
    if not split.any() or split.all():
        raise RuntimeError("Hash split lacks train or validation groups")
    args.output.parent.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(args.output, actions=np.stack(actions), groups=np.asarray(groups),
                        train=split, sources=np.asarray(sources), bank_sha256=np.asarray(bank_hashes))
    receipt = {
        "status": "ACTION_PREFIX_CORPUS_PASS",
        "allowed_roots": list(ALLOWED_ROOTS),
        "outcomes_read": False,
        "physical_groups": len(groups),
        "train_groups": int(split.sum()),
        "validation_groups": int((~split).sum()),
        "corpus_sha256": sha(args.output),
        "rejected": rejected,
    }
    (args.output.parent / "CORPUS_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()

