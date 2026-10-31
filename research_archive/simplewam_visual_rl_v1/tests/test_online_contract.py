import torch

from simplewam_visual_rl.online_contract import (
    ARMS,
    frozen_arm_order,
    frozen_random_index,
    select_online_arm,
)


class FakeQ:
    def in_support(self, actions):
        return actions.abs().flatten(1).max(1).values <= 1

    def q(self, state, actions):
        del state
        return actions[:, 0, 0]


def test_arm_order_is_deterministic_and_complete():
    first = frozen_arm_order("scene-7", 202644501)
    assert first == frozen_arm_order("scene-7", 202644501)
    assert set(first) == set(ARMS)
    assert len(first) == len(set(first)) == 4


def test_random_index_is_stable_and_bounded():
    index = frozen_random_index("scene-2", 13, 4, 202644502)
    assert index == frozen_random_index("scene-2", 13, 4, 202644502)
    assert 0 <= index < 4


def test_all_arms_share_shadow_work_and_select_expected_bank():
    native = torch.zeros(4, 32, 7)
    native[:, 0, 0] = torch.tensor([0.1, 0.4, 0.3, 0.2])
    guided = native.clone()
    guided[:, 0, 0] = torch.tensor([0.2, 0.3, 0.8, 0.1])
    state = torch.zeros(1, 2057)
    traces = tuple({"applied": True, "candidate": i} for i in range(4))

    expected = {"candidate0": 0, "critic_rerank": 1, "visual_qgf": 2}
    for arm, index in expected.items():
        decision = select_online_arm(
            arm=arm, scene_key="scene", decision_index=0,
            selection_seed=202644503, frozen_q=FakeQ(), state=state,
            native_bank=native, guided_bank=guided, guidance_traces=traces,
        )
        assert decision.selected_index == index
        assert decision.receipt["shadow_critic_and_gradient_computed"] is True
        assert decision.receipt["outcomes_read_for_selection"] == 0
        source = guided if arm == "visual_qgf" else native
        assert torch.equal(decision.selected_actions, source[index:index + 1])


def test_out_of_support_candidate_is_masked():
    native = torch.zeros(4, 32, 7)
    native[:, 0, 0] = torch.tensor([0.1, 2.0, 0.3, 0.2])
    decision = select_online_arm(
        arm="critic_rerank", scene_key="scene", decision_index=1,
        selection_seed=202644504, frozen_q=FakeQ(), state=torch.zeros(1, 2057),
        native_bank=native, guided_bank=native.clone(),
        guidance_traces=tuple({"applied": False} for _ in range(4)),
    )
    assert decision.selected_index == 2


def test_critic_scores_normalized_bank_but_commits_native_bank():
    native = torch.zeros(4, 32, 7)
    native[:, 0, 0] = torch.tensor([0.1, 0.2, 0.3, 0.4])
    normalized = torch.zeros_like(native)
    normalized[:, 0, 0] = torch.tensor([0.1, 0.9, 0.2, 0.3])
    decision = select_online_arm(
        arm="critic_rerank", scene_key="scene", decision_index=2,
        selection_seed=202644505, frozen_q=FakeQ(), state=torch.zeros(1, 2057),
        native_bank=native, guided_bank=native.clone(),
        native_score_bank=normalized, guided_score_bank=normalized.clone(),
        guidance_traces=tuple({"applied": False} for _ in range(4)),
    )
    assert decision.selected_index == 1
    assert torch.equal(decision.selected_actions, native[1:2])
    assert decision.receipt["native_score_bank_sha256"] != decision.receipt["native_bank_sha256"]


def test_baselines_do_not_abort_when_candidate0_is_outside_critic_support():
    native = torch.zeros(4, 32, 7)
    native[0, 0, 0] = 2.0
    traces = tuple({"applied": False} for _ in range(4))
    for arm in ("candidate0", "uniform_random"):
        decision = select_online_arm(
            arm=arm, scene_key="prospective-scene", decision_index=3,
            selection_seed=202644502, frozen_q=FakeQ(),
            state=torch.zeros(1, 2057), native_bank=native,
            guided_bank=native.clone(), guidance_traces=traces,
        )
        assert decision.receipt["native_supported"][0] is False
        assert decision.receipt["support_abstention"] is False


def test_q_arms_fallback_to_candidate0_when_no_candidate_is_supported():
    native = torch.full((4, 32, 7), 2.0)
    guided = torch.full_like(native, 3.0)
    traces = tuple({"applied": True} for _ in range(4))
    for arm in ("critic_rerank", "visual_qgf"):
        decision = select_online_arm(
            arm=arm, scene_key="prospective-scene", decision_index=4,
            selection_seed=202644502, frozen_q=FakeQ(),
            state=torch.zeros(1, 2057), native_bank=native,
            guided_bank=guided, guidance_traces=traces,
        )
        assert decision.selected_index == 0
        assert torch.equal(decision.selected_actions, native[0:1])
        assert decision.receipt["support_abstention"] is True

