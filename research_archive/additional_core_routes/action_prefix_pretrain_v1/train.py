"""Fixed masked-action reconstruction pretraining."""

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch


class ActionEncoder(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.input = torch.nn.Linear(7, 128)
        self.mask = torch.nn.Parameter(torch.zeros(128))
        self.position = torch.nn.Parameter(torch.randn(32, 128) * 0.01)
        layer = torch.nn.TransformerEncoderLayer(
            128, 4, 256, dropout=0.0, activation="gelu", batch_first=True, norm_first=True
        )
        self.encoder = torch.nn.TransformerEncoder(layer, 3)
        self.output = torch.nn.Linear(128, 7)

    def forward(self, actions, masked):
        hidden = self.input(actions)
        hidden = torch.where(masked[..., None], self.mask[None, None, :], hidden)
        hidden = self.encoder(hidden + self.position[None, :, :])
        return self.output(hidden)


def state_sha(model):
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--updates", type=int, default=5000)
    args = parser.parse_args()
    if args.seed not in (202642301, 202642302, 202642303) or args.updates != 5000:
        raise RuntimeError("Non-frozen seed or update count")
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite output")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda:0")
    with np.load(args.corpus, allow_pickle=False) as payload:
        actions = torch.from_numpy(payload["actions"])
        train_groups = torch.from_numpy(payload["train"])
    train = actions[train_groups].reshape(-1, 32, 7).to(device)
    validation = actions[~train_groups].reshape(-1, 32, 7).to(device)
    model = ActionEncoder().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    generator = torch.Generator(device=device).manual_seed(args.seed + 17)
    losses = []
    model.train()
    for step in range(args.updates):
        indices = torch.randint(len(train), (64,), generator=generator, device=device)
        batch = train[indices]
        masked = torch.rand((64, 32), generator=generator, device=device) < 0.30
        masked[:, 0] = True
        prediction = model(batch, masked)
        loss = torch.nn.functional.mse_loss(prediction[masked], batch[masked])
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if step % 100 == 0 or step + 1 == args.updates:
            losses.append([step + 1, float(loss.detach())])

    model.eval()
    with torch.no_grad():
        mask = torch.zeros((len(validation), 32), dtype=torch.bool, device=device)
        mask[:, ::3] = True
        val_loss = float(torch.nn.functional.mse_loss(model(validation, mask)[mask], validation[mask]))
    args.output.mkdir(parents=True)
    checkpoint = args.output / "encoder.pt"
    torch.save({"model": model.state_dict(), "seed": args.seed, "updates": args.updates}, checkpoint)
    result = {
        "status": "ACTION_PREFIX_PRETRAIN_COMPLETE",
        "seed": args.seed,
        "updates": args.updates,
        "train_chunks": len(train),
        "validation_chunks": len(validation),
        "validation_masked_mse": val_loss,
        "loss_trace": losses,
        "model_state_sha256": state_sha(model),
        "scientific_outcomes_read": False,
        "qgf_evidence": False,
    }
    (args.output / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

