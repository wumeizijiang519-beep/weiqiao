import collections
import glob
import json
import pathlib

import numpy as np


base = pathlib.Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022/simplewam_visual_rl_v1")
run = base / "online_execution_v2_support_abstention"
registration = json.load(open(base / "online_registration_v2_support_abstention/REGISTRATION.json"))
arms = ["candidate0", "uniform_random", "critic_rerank", "visual_qgf"]
by_scene = collections.defaultdict(dict)
reports = {}

for task in registration["tasks"]:
    report = json.load(open(run / ("task_%03d" % task["task_index"]) / "REPORT.json"))
    by_scene[task["scene_index"]][task["arm"]] = int(report["official_success"])
    reports[(task["scene_index"], task["arm"])] = report

patterns = collections.Counter(tuple(values[arm] for arm in arms) for values in by_scene.values())
print("PATTERNS")
for pattern, count in sorted(patterns.items(), key=lambda item: (-item[1], item[0])):
    print(pattern, count)

print("DISCORDANT_SCENES")
for scene, values in sorted(by_scene.items()):
    if len(set(values.values())) > 1:
        print(scene, " ".join("%s=%d" % (arm, values[arm]) for arm in arms))

sample = json.load(open(sorted(glob.glob(str(run / "task_238/transition_*/decision.json")))[0]))
print("DECISION_KEYS", sorted(sample.keys()))
for key in sorted(sample.keys()):
    if key not in ("guidance_traces",):
        value = sample[key]
        if isinstance(value, (dict, list)):
            text = json.dumps(value, sort_keys=True)
            print("KEY", key, text[:1000])
        else:
            print("KEY", key, value)

summary = collections.defaultdict(list)
for task in registration["tasks"]:
    folder = run / ("task_%03d" % task["task_index"])
    for decision_path in sorted(folder.glob("transition_*/decision.json")):
        decision = json.load(open(decision_path))
        arm = task["arm"]
        for key in ("support_abstention", "selected_candidate", "native_selected_candidate", "qgf_selected_candidate"):
            if key in decision:
                summary[(arm, key)].append(decision[key])
        traces = decision.get("guidance_traces", [])
        if traces:
            all_used = []
            all_raw = []
            all_scores = []
            for candidate in traces:
                for trace in candidate.get("qgf", []):
                    all_used.extend(trace.get("used_grad_norm", []))
                    all_raw.extend(trace.get("raw_grad_norm", []))
                    all_scores.extend(trace.get("score", []))
            if all_used:
                summary[(arm, "mean_used_grad_norm")].append(float(np.mean(all_used)))
            if all_raw:
                summary[(arm, "mean_raw_grad_norm")].append(float(np.mean(all_raw)))
            if all_scores:
                summary[(arm, "mean_qgf_trace_score")].append(float(np.mean(all_scores)))

print("DECISION_SUMMARY")
for (arm, key), values in sorted(summary.items()):
    if not values:
        continue
    if all(isinstance(v, (bool, int, float)) for v in values):
        arr = np.asarray(values, dtype=np.float64)
        print(arm, key, "n", len(values), "mean", float(arr.mean()), "min", float(arr.min()), "max", float(arr.max()))
    else:
        print(arm, key, collections.Counter(map(str, values)).most_common(10))
