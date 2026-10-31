"""Inventory task predicates and simulator names without policy or robot actions."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonable(value):
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def names(model, kind):
    count_fields = {"body": "nbody", "site": "nsite", "joint": "njnt", "geom": "ngeom"}
    if kind not in count_fields:
        raise ValueError("Unsupported MuJoCo object kind: " + kind)
    count = int(getattr(model, count_fields[kind]))
    lookup = getattr(model, kind + "_id2name")
    return [lookup(index) for index in range(count)]


def main():
    import torch
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha(args.manifest) != args.manifest_sha256:
        raise RuntimeError("Manifest hash mismatch")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "PROGRESS_PAIRWISE_QGF_V1_PROPOSED_NOT_GPU_AUTHORIZED":
        raise RuntimeError("Unexpected prospective manifest status")
    entries = {}
    for entry in manifest["entries"]:
        entries.setdefault(entry["family"], entry)
    if len(entries) != 4:
        raise RuntimeError("Expected exactly four task families")

    from experiments.libero.libero_utils import LIBERO_ENV_RESOLUTION, get_libero_env
    from libero.libero import benchmark

    suite = benchmark.get_benchmark_dict()["libero_10"]()
    report = {"status": "RUNTIME_INVENTORY_ONLY_NO_ACTIONS", "families": {}}
    for family in sorted(entries):
        entry = entries[family]
        for key, digest in (("bddl_path", "bddl_sha256"),
                            ("initial_state_path", "initial_file_sha256")):
            if sha(entry[key]) != entry[digest]:
                raise RuntimeError("Frozen scene asset changed")
        task = suite.get_task(entry["task_id"])
        states = np.asarray(torch.load(entry["initial_state_path"], map_location="cpu",
                                       weights_only=False))
        if "_add_" in Path(entry["initial_state_path"]).name or "_level" in Path(entry["initial_state_path"]).name:
            states = states.reshape(1, -1)
        initial = np.asarray(states[entry["initial_state_index"]], dtype="<f8")
        env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry["environment_seed"])
        env.reset()
        env.set_init_state(initial)
        base = env.env if hasattr(env, "env") else env
        model = base.sim.model
        state = np.asarray(env.get_sim_state(), dtype="<f8")
        report["families"][family] = {
            "episode_id": entry["episode_id"],
            "task_id": entry["task_id"],
            "task_name": task.name,
            "description": description,
            "goal_state": jsonable(base.parsed_problem.get("goal_state")),
            "objects_of_interest": jsonable(base.parsed_problem.get("obj_of_interest", [])),
            "bodies": names(model, "body"),
            "sites": names(model, "site"),
            "joints": names(model, "joint"),
            "geoms": names(model, "geom"),
            "initial_state_sha256": hashlib.sha256(initial.tobytes()).hexdigest(),
            "runtime_state_sha256": hashlib.sha256(state.tobytes()).hexdigest(),
            "runtime_state_shape": list(state.shape),
        }
        env.close()
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output.parent / "RUNTIME_INVENTORY_PASS").write_text("NO_POLICY_NO_ROBOT_ACTIONS\n")
    (args.output.parent / "REPORT_SHA256").write_text(sha(args.output) + "  REPORT.json\n")
    print(json.dumps({"status": report["status"], "families": list(report["families"])}, indent=2))


if __name__ == "__main__":
    main()
