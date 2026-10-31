"""Current-observation-only WAM features, with training-fold-only scaling."""

import numpy as np
import torch
from torch.nn import functional as F

from data_contract import capture_rng, observation_payload, restore_rng


def pool_features(latents, context, context_mask, proprio, remaining_steps):
    if latents.ndim != 5 or latents.shape[0] != 1 or latents.shape[2] != 1:
        raise ValueError('Feature encoder must contain only one current frame')
    if context.ndim != 3 or context.shape[0] != 1 or context_mask.shape != context.shape[:2]:
        raise ValueError('Invalid official prompt context/mask')
    if proprio.shape != (1, 8) or not 0 <= remaining_steps <= 700:
        raise ValueError('Invalid current proprio/known remaining horizon')
    if not context_mask.any():
        raise ValueError('Empty official prompt mask')
    vision = F.adaptive_avg_pool2d(latents[:, :, 0].float(), (4, 8)).flatten(1)
    weights = context_mask.float().unsqueeze(-1)
    text = (context.float() * weights).sum(1) / weights.sum(1)
    value = torch.cat((vision, text, proprio.float(),
                       proprio.new_tensor([[remaining_steps / 700.]], dtype=torch.float32)), 1)
    if not torch.isfinite(value).all():
        raise ValueError('Nonfinite current-only feature')
    return value.detach().cpu().numpy()[0].astype(np.float32)


class CurrentWamFeatures:
    def __init__(self, model, processor, cfg):
        self.model, self.processor, self.cfg = model, processor, cfg
        self.prompt_cache = {}
        self.spec = None

    def __call__(self, observation, description, remaining_steps):
        from experiments.libero.eval_libero_single import _obs_to_model_input, DEFAULT_PROMPT

        obs = observation_payload(observation)
        before = capture_rng()
        try:
            with torch.no_grad():
                image, proprio, _, _ = _obs_to_model_input(
                    obs, cfg=self.cfg, processor=self.processor, width=448, height=224,
                    device=self.model.device, dtype=self.model.torch_dtype)
                # This exact method is called for the current image in official infer_action.
                latents = self.model._encode_input_image_latents_tensor(input_image=image, tiled=False)
                prompt = DEFAULT_PROMPT.format(task=description)
                if prompt not in self.prompt_cache:
                    self.prompt_cache[prompt] = self.model.encode_prompt(prompt, text_encoder_offload=True)
                context, context_mask = self.prompt_cache[prompt]
                value = pool_features(latents, context, context_mask, proprio, remaining_steps)
            spec = {'latent_shape': list(latents.shape), 'latent_pool': [4, 8],
                    'context_dimension': int(context.shape[-1]), 'proprio_dimension': 8,
                    'remaining_horizon_dimension': 1, 'feature_dimension': int(value.size),
                    'time_normalization': 'known remaining model steps divided by700',
                    'prompt_pool': 'official returned context_mask weighted mean, including its visible zero padding',
                    'future_frames': 0, 'feature_dtype': 'float32'}
            if self.spec is None:
                self.spec = spec
            elif self.spec != spec:
                raise ValueError('Feature shape/contract changed')
            return value
        finally:
            restore_rng(before)


class FoldScaler:
    """Fit only on supplied training observation rows, never validation rows."""

    def __init__(self):
        self.mean = None
        self.scale = None

    def fit(self, values):
        values = np.asarray(values, dtype=np.float64)
        if values.ndim != 2 or not len(values) or not np.isfinite(values).all():
            raise ValueError('Invalid training feature matrix')
        self.mean = values.mean(0).astype(np.float32)
        self.scale = np.maximum(values.std(0), 1e-5).astype(np.float32)
        return self

    def transform(self, values):
        if self.mean is None:
            raise RuntimeError('Training scaler has not been fitted')
        values = np.asarray(values, dtype=np.float32)
        if values.shape[-1] != len(self.mean) or not np.isfinite(values).all():
            raise ValueError('Invalid feature input to frozen scaler')
        return (values - self.mean) / self.scale

    def state(self):
        if self.mean is None:
            raise RuntimeError('Unfitted scaler')
        return {'mean': self.mean.copy(), 'scale': self.scale.copy()}
