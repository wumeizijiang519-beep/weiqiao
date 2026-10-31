"""Frozen simulator-only progress labels for Progress-Pairwise QGF V1."""

import numpy as np


BINDINGS = {
    "KITCHEN_SCENE4": {
        "distances": [("akita_black_bowl_1_main", "white_cabinet_1_bottom_region")],
        "articulation": ("white_cabinet_1_bottom_level", 0.0, 0.16),
    },
    "KITCHEN_SCENE6": {
        "distances": [("white_yellow_mug_1_main", "microwave_1_heating_region")],
        "articulation": ("microwave_1_microjoint", 0.0, 2.094),
    },
    "LIVING_ROOM_SCENE2": {
        "distances": [
            ("alphabet_soup_1_main", "basket_1_contain_region"),
            ("tomato_sauce_1_main", "basket_1_contain_region"),
        ],
        "articulation": None,
    },
    "LIVING_ROOM_SCENE5": {
        "distances": [
            ("porcelain_mug_1_main", "plate_1_default_site"),
            ("white_yellow_mug_1_main", "plate_2_default_site"),
        ],
        "articulation": None,
    },
}


def family_key(family):
    keys = [key for key in BINDINGS if family.startswith(key + "_")]
    if len(keys) != 1:
        raise RuntimeError("Unknown or ambiguous family: " + family)
    return keys[0]


def _ids(model, binding):
    body, site = binding
    body_id = int(model.body_name2id(body))
    site_id = int(model.site_name2id(site))
    if body_id < 0 or site_id < 0:
        raise RuntimeError("Missing progress binding: " + repr(binding))
    return body_id, site_id


def capture(env, family):
    base = env.env if hasattr(env, "env") else env
    sim = base.sim
    spec = BINDINGS[family_key(family)]
    distances = []
    for binding in spec["distances"]:
        body_id, site_id = _ids(sim.model, binding)
        delta = np.asarray(sim.data.body_xpos[body_id]) - np.asarray(sim.data.site_xpos[site_id])
        distances.append(float(np.linalg.norm(delta)))
    articulation = None
    if spec["articulation"] is not None:
        joint, closed, span = spec["articulation"]
        joint_id = int(sim.model.joint_name2id(joint))
        if joint_id < 0:
            raise RuntimeError("Missing progress joint: " + joint)
        address = int(sim.model.jnt_qposadr[joint_id])
        articulation = float(sim.data.qpos[address])
        if not np.isfinite(articulation) or span <= 0:
            raise RuntimeError("Invalid articulation progress state")
    result = {"distances": distances, "articulation": articulation}
    if not np.isfinite(np.asarray(distances)).all():
        raise RuntimeError("Non-finite distance progress state")
    return result


def relative_progress(boundary, current, family):
    key = family_key(family)
    before = np.asarray(boundary["distances"], dtype=np.float64)
    after = np.asarray(current["distances"], dtype=np.float64)
    expected = len(BINDINGS[key]["distances"])
    if before.shape != (expected,) or after.shape != (expected,):
        raise RuntimeError("Progress distance shape mismatch")
    scale = np.maximum(before, 0.05)
    components = np.clip((before - after) / scale, -1.0, 1.0).tolist()
    if BINDINGS[key]["articulation"] is not None:
        _, closed, span = BINDINGS[key]["articulation"]
        if boundary["articulation"] is None or current["articulation"] is None:
            raise RuntimeError("Missing articulation value")
        before_error = abs(float(boundary["articulation"]) - closed)
        after_error = abs(float(current["articulation"]) - closed)
        components.append(float(np.clip((before_error - after_error) / span, -1.0, 1.0)))
    value = float(np.mean(components))
    if not np.isfinite(value):
        raise RuntimeError("Non-finite progress value")
    return {"value": value, "components": components}
