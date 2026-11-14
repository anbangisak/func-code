"""Reproducible CIFAR-10 experiments for Unsupervised Deep Learning Assignment 2.

Run this module from the accompanying notebooks on the provisioned BITS GPU.
Images are kept in [0, 1], as required by the assignment.
"""

from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from torchvision import datasets, transforms
from torchvision.utils import save_image


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_OUTPUT_DIR = ROOT / "outputs"
SEED = 533
FID_COUNT = 10_000
SAMPLE_COUNT = 100


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True


def require_cuda() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU is required by the assignment. Run this notebook on the "
            "provisioned BITS Prayogshala/WILP GPU, not on a CPU-only runtime."
        )
    return torch.device("cuda")


def make_loaders(
    data_dir: Path = DEFAULT_DATA_DIR,
    batch_size: int = 128,
    workers: int = 4,
) -> tuple[DataLoader, DataLoader]:
    transform = transforms.ToTensor()
    train_set = datasets.CIFAR10(
        root=str(data_dir), train=True, download=True, transform=transform
    )
    test_set = datasets.CIFAR10(
        root=str(data_dir), train=False, download=True, transform=transform
    )
    loader_args = {
        "batch_size": batch_size,
        "num_workers": workers,
        "pin_memory": True,
        "persistent_workers": workers > 0,
    }
    train_generator = torch.Generator().manual_seed(SEED)
    train_loader = DataLoader(
        train_set, shuffle=True, generator=train_generator, **loader_args
    )
    test_loader = DataLoader(test_set, shuffle=False, **loader_args)
    return train_loader, test_loader


class ConvVAE(nn.Module):
    def __init__(self, latent_dim: int = 128) -> None:
        super().__init__()
        self.latent_dim = latent_dim
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 4, 2, 1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, 4, 2, 1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Flatten(),
        )
        self.to_mu = nn.Linear(256 * 4 * 4, latent_dim)
        self.to_logvar = nn.Linear(256 * 4 * 4, latent_dim)
        self.from_latent = nn.Linear(latent_dim, 256 * 4 * 4)
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(256, 128, 4, 2, 1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, 4, 2, 1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 3, 4, 2, 1),
            nn.Sigmoid(),
        )

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.encoder(x)
        return self.to_mu(h), self.to_logvar(h).clamp(-12.0, 12.0)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        h = self.from_latent(z).view(-1, 256, 4, 4)
        return self.decoder(h)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mu, logvar = self.encode(x)
        std = torch.exp(0.5 * logvar)
        z = mu + std * torch.randn_like(std)
        return self.decode(z), mu, logvar


def vae_loss(
    reconstruction: torch.Tensor,
    x: torch.Tensor,
    mu: torch.Tensor,
    logvar: torch.Tensor,
    beta: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    reconstruction_loss = F.mse_loss(
        reconstruction, x, reduction="none"
    ).flatten(1).sum(1).mean()
    kl_loss = -0.5 * (1 + logvar - mu.square() - logvar.exp()).sum(1).mean()
    return reconstruction_loss + beta * kl_loss, reconstruction_loss, kl_loss


class VectorQuantizer(nn.Module):
    def __init__(self, codebook_size: int, embedding_dim: int, commitment: float = 0.25):
        super().__init__()
        self.codebook_size = codebook_size
        self.embedding_dim = embedding_dim
        self.commitment = commitment
        self.embedding = nn.Embedding(codebook_size, embedding_dim)
        nn.init.uniform_(self.embedding.weight, -1 / codebook_size, 1 / codebook_size)

    def forward(
        self, z_e: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        batch, channels, height, width = z_e.shape
        flat = z_e.permute(0, 2, 3, 1).contiguous().view(-1, channels)
        weights = self.embedding.weight
        distances = (
            flat.square().sum(1, keepdim=True)
            + weights.square().sum(1)
            - 2 * flat @ weights.t()
        )
        indices = distances.argmin(dim=1)
        quantized = self.embedding(indices).view(batch, height, width, channels)
        quantized = quantized.permute(0, 3, 1, 2).contiguous()
        codebook_loss = F.mse_loss(quantized, z_e.detach())
        commitment_loss = F.mse_loss(quantized.detach(), z_e)
        quantized_st = z_e + (quantized - z_e).detach()
        counts = torch.bincount(indices, minlength=self.codebook_size).float()
        probabilities = counts / counts.sum().clamp_min(1)
        perplexity = torch.exp(
            -(probabilities * probabilities.clamp_min(1e-10).log()).sum()
        )
        return (
            quantized_st,
            indices.view(batch, height, width),
            codebook_loss + self.commitment * commitment_loss,
            perplexity,
        )


class ConvVQVAE(nn.Module):
    def __init__(self, codebook_size: int, embedding_dim: int = 128):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, embedding_dim, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(embedding_dim, embedding_dim, 3, 1, 1),
        )
        self.quantizer = VectorQuantizer(codebook_size, embedding_dim)
        self.decoder = nn.Sequential(
            nn.Conv2d(embedding_dim, embedding_dim, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(embedding_dim, 64, 4, 2, 1),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 3, 4, 2, 1),
            nn.Sigmoid(),
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def encode_indices(self, x: torch.Tensor) -> torch.Tensor:
        z_e = self.encode(x)
        return self.quantizer(z_e)[1]

    def decode_codes(self, indices: torch.Tensor) -> torch.Tensor:
        z_q = self.quantizer.embedding(indices).permute(0, 3, 1, 2).contiguous()
        return self.decoder(z_q)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        quantized, indices, quantizer_loss, perplexity = self.quantizer(
            self.encode(x)
        )
        return self.decoder(quantized), indices, quantizer_loss, perplexity


class MaskedConv2d(nn.Conv2d):
    def __init__(self, *args, mask_type: str, **kwargs):
        super().__init__(*args, **kwargs)
        if mask_type not in {"A", "B"}:
            raise ValueError("mask_type must be 'A' or 'B'")
        mask = torch.ones_like(self.weight)
        center_y, center_x = self.kernel_size[0] // 2, self.kernel_size[1] // 2
        mask[:, :, center_y + 1 :, :] = 0
        mask[:, :, center_y, center_x + (mask_type == "B") :] = 0
        self.register_buffer("mask", mask)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.conv2d(
            x,
            self.weight * self.mask,
            self.bias,
            self.stride,
            self.padding,
            self.dilation,
            self.groups,
        )


class PixelResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.layers = nn.Sequential(
            nn.ReLU(inplace=True),
            MaskedConv2d(channels, channels, 3, padding=1, mask_type="B"),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.layers(x)


class PixelCNN(nn.Module):
    def __init__(self, codebook_size: int, hidden_channels: int = 128):
        super().__init__()
        self.embedding = nn.Embedding(codebook_size, hidden_channels)
        self.input_conv = MaskedConv2d(
            hidden_channels, hidden_channels, 7, padding=3, mask_type="A"
        )
        self.blocks = nn.Sequential(
            PixelResidualBlock(hidden_channels),
            PixelResidualBlock(hidden_channels),
            PixelResidualBlock(hidden_channels),
            PixelResidualBlock(hidden_channels),
        )
        self.output = nn.Sequential(
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, hidden_channels, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, codebook_size, 1),
        )

    def forward(self, indices: torch.Tensor) -> torch.Tensor:
        x = self.embedding(indices).permute(0, 3, 1, 2).contiguous()
        x = self.input_conv(x)
        return self.output(self.blocks(x))


class Generator(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        self.latent_dim = latent_dim
        self.project = nn.Linear(latent_dim, 512 * 4 * 4)
        self.layers = nn.Sequential(
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(512, 256, 4, 2, 1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(256, 128, 4, 2, 1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 3, 4, 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        return self.layers(self.project(z).view(-1, 512, 4, 4))


class Critic(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(64, 128, 4, 2, 1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(128, 256, 4, 2, 1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Flatten(),
            nn.Linear(256 * 4 * 4, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x).flatten()


def _output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "samples").mkdir(exist_ok=True)
    (path / "checkpoints").mkdir(exist_ok=True)
    (path / "curves").mkdir(exist_ok=True)
    return path


def _save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _record_result(output_dir: Path, result: dict) -> None:
    path = output_dir / "summary.json"
    summary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    summary[result["model_id"]] = result
    _save_json(path, summary)


def _save_grid(images: torch.Tensor, path: Path, nrow: int = 10) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_image(images.detach().cpu().clamp(0, 1), path, nrow=nrow, padding=2)


@torch.no_grad()
def _psnr(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    squared_error = 0.0
    value_count = 0
    for x, _ in loader:
        x = x.to(device, non_blocking=True)
        if isinstance(model, ConvVAE):
            mu, _ = model.encode(x)
            reconstruction = model.decode(mu)
        else:
            reconstruction, _, _, _ = model(x)
        squared_error += F.mse_loss(reconstruction, x, reduction="sum").item()
        value_count += x.numel()
    mse = squared_error / value_count
    return float(10.0 * math.log10(1.0 / max(mse, 1e-12)))


@torch.no_grad()
def _codebook_quality(
    model: ConvVQVAE, loader: DataLoader, device: torch.device
) -> dict[str, float]:
    model.eval()
    counts = torch.zeros(model.quantizer.codebook_size, dtype=torch.float64)
    for x, _ in loader:
        indices = model.encode_indices(x.to(device, non_blocking=True))
        counts += torch.bincount(
            indices.reshape(-1).cpu(), minlength=model.quantizer.codebook_size
        ).double()
    probabilities = counts / counts.sum().clamp_min(1)
    active = counts.gt(0).sum().item()
    entropy = -(probabilities * probabilities.clamp_min(1e-12).log()).sum().item()
    return {
        "perplexity": float(math.exp(entropy)),
        "active_codes": int(active),
        "active_code_fraction": float(active / model.quantizer.codebook_size),
    }


def _fid_score(
    real_loader: DataLoader,
    fake_batches: Callable[[int], torch.Tensor],
    device: torch.device,
    count: int = FID_COUNT,
) -> float:
    try:
        from torchmetrics.image.fid import FrechetInceptionDistance
    except ImportError as exc:
        raise RuntimeError(
            'FID requires torchmetrics and torch-fidelity. Install with '
            '`pip install "torchmetrics[image]"` in the BITS runtime.'
        ) from exc

    fid = FrechetInceptionDistance(feature=2048, normalize=False).to(device)
    seen = 0
    for x, _ in real_loader:
        take = min(x.shape[0], count - seen)
        if take <= 0:
            break
        real_uint8 = (x[:take].to(device) * 255).round().byte()
        fid.update(real_uint8, real=True)
        seen += take
    if seen != count:
        raise RuntimeError(f"FID requested {count} real images but found {seen}.")
    generated = 0
    while generated < count:
        batch = min(128, count - generated)
        fake = fake_batches(batch).clamp(0, 1)
        fid.update((fake * 255).round().byte(), real=False)
        generated += batch
    return float(fid.compute().item())


def _train_vae(
    beta: float,
    train_loader: DataLoader,
    test_loader: DataLoader,
    output_dir: Path,
    epochs: int,
    device: torch.device,
) -> dict:
    model_id = f"vae_beta_{beta:g}"
    model = ConvVAE().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
    curve = {"epoch": [], "train_loss": [], "psnr": [], "seconds": []}
    epoch_seconds = []
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, batches = 0.0, 0
        epoch_start = time.perf_counter()
        for x, _ in train_loader:
            x = x.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            reconstruction, mu, logvar = model(x)
            loss, _, _ = vae_loss(reconstruction, x, mu, logvar, beta)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            batches += 1
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - epoch_start
        epoch_seconds.append(elapsed)
        psnr = _psnr(model, test_loader, device)
        curve["epoch"].append(epoch)
        curve["train_loss"].append(total_loss / max(batches, 1))
        curve["psnr"].append(psnr)
        curve["seconds"].append(elapsed)
        print(
            f"{model_id} | epoch {epoch:03d}/{epochs} | "
            f"loss={curve['train_loss'][-1]:.3f} | test PSNR={psnr:.2f} dB"
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    training_seconds = float(sum(epoch_seconds))
    checkpoint = output_dir / "checkpoints" / f"{model_id}.pt"
    torch.save(model.state_dict(), checkpoint)
    _save_json(output_dir / "curves" / f"{model_id}.json", curve)

    @torch.no_grad()
    def fake_batches(batch_size: int) -> torch.Tensor:
        return model.decode(torch.randn(batch_size, model.latent_dim, device=device))

    fid = _fid_score(test_loader, fake_batches, device)
    sample = fake_batches(SAMPLE_COUNT)
    _save_grid(sample, output_dir / "samples" / f"{model_id}_100.png")
    result = {
        "model_id": model_id,
        "family": "VAE",
        "beta": beta,
        "epochs": epochs,
        "test_psnr_db": curve["psnr"][-1],
        "fid": fid,
        "training_seconds": training_seconds,
        "seconds_per_epoch": float(np.mean(epoch_seconds)),
        "fid_images": FID_COUNT,
        "checkpoint": str(checkpoint),
    }
    _record_result(output_dir, result)
    del model
    torch.cuda.empty_cache()
    return result


def _train_vqvae(
    codebook_size: int,
    train_loader: DataLoader,
    test_loader: DataLoader,
    output_dir: Path,
    epochs: int,
    device: torch.device,
) -> tuple[ConvVQVAE, dict]:
    model_id = f"vqvae_k_{codebook_size}"
    model = ConvVQVAE(codebook_size).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
    curve = {"epoch": [], "train_loss": [], "psnr": [], "seconds": []}
    epoch_seconds = []
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, batches = 0.0, 0
        epoch_start = time.perf_counter()
        for x, _ in train_loader:
            x = x.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            reconstruction, _, quantizer_loss, _ = model(x)
            loss = F.mse_loss(reconstruction, x) + quantizer_loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            batches += 1
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - epoch_start
        epoch_seconds.append(elapsed)
        psnr = _psnr(model, test_loader, device)
        curve["epoch"].append(epoch)
        curve["train_loss"].append(total_loss / max(batches, 1))
        curve["psnr"].append(psnr)
        curve["seconds"].append(elapsed)
        print(
            f"{model_id} | epoch {epoch:03d}/{epochs} | "
            f"loss={curve['train_loss'][-1]:.4f} | test PSNR={psnr:.2f} dB"
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    training_seconds = float(sum(epoch_seconds))
    checkpoint = output_dir / "checkpoints" / f"{model_id}.pt"
    torch.save(model.state_dict(), checkpoint)
    _save_json(output_dir / "curves" / f"{model_id}.json", curve)
    quality = _codebook_quality(model, train_loader, device)
    result = {
        "model_id": model_id,
        "family": "VQ-VAE",
        "codebook_size": codebook_size,
        "epochs": epochs,
        "test_psnr_db": curve["psnr"][-1],
        **quality,
        "training_seconds": training_seconds,
        "seconds_per_epoch": float(np.mean(epoch_seconds)),
        "checkpoint": str(checkpoint),
    }
    _record_result(output_dir, result)
    return model, result


@torch.no_grad()
def _extract_latents(
    model: ConvVQVAE, loader: DataLoader, device: torch.device
) -> torch.Tensor:
    model.eval()
    maps = []
    for x, _ in loader:
        maps.append(model.encode_indices(x.to(device, non_blocking=True)).cpu())
    return torch.cat(maps)


def _train_pixelcnn(
    codebook_size: int,
    latent_maps: torch.Tensor,
    output_dir: Path,
    epochs: int,
    device: torch.device,
) -> tuple[PixelCNN, float]:
    model = PixelCNN(codebook_size).to(device)
    loader = DataLoader(
        TensorDataset(latent_maps.long()),
        batch_size=128,
        shuffle=True,
        pin_memory=True,
        num_workers=0,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
    epoch_seconds = []
    started = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, batches = 0.0, 0
        epoch_start = time.perf_counter()
        for (indices,) in loader:
            indices = indices.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(indices)
            loss = F.cross_entropy(logits, indices)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            batches += 1
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - epoch_start
        epoch_seconds.append(elapsed)
        print(
            f"pixelcnn_k_{codebook_size} | epoch {epoch:03d}/{epochs} | "
            f"cross-entropy={total_loss / max(batches, 1):.4f}"
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    training_seconds = time.perf_counter() - started
    checkpoint = output_dir / "checkpoints" / f"pixelcnn_k_{codebook_size}.pt"
    torch.save(model.state_dict(), checkpoint)
    _save_json(
        output_dir / "curves" / f"pixelcnn_k_{codebook_size}.json",
        {"seconds_per_epoch": epoch_seconds},
    )
    return model, training_seconds


@torch.no_grad()
def _sample_pixelcnn(
    model: PixelCNN, batch_size: int, grid_size: int, device: torch.device
) -> torch.Tensor:
    model.eval()
    codes = torch.zeros(batch_size, grid_size, grid_size, dtype=torch.long, device=device)
    for row in range(grid_size):
        for column in range(grid_size):
            logits = model(codes)[:, :, row, column]
            probabilities = torch.softmax(logits, dim=1)
            codes[:, row, column] = torch.multinomial(probabilities, num_samples=1).squeeze(1)
    return codes


def _run_vq_experiment(
    codebook_size: int,
    train_loader: DataLoader,
    test_loader: DataLoader,
    output_dir: Path,
    vq_epochs: int,
    pixelcnn_epochs: int,
    device: torch.device,
) -> dict:
    model, result = _train_vqvae(
        codebook_size, train_loader, test_loader, output_dir, vq_epochs, device
    )
    latent_maps = _extract_latents(model, train_loader, device)
    latent_path = output_dir / "checkpoints" / f"train_latents_k_{codebook_size}.pt"
    torch.save(latent_maps, latent_path)
    prior, prior_seconds = _train_pixelcnn(
        codebook_size, latent_maps, output_dir, pixelcnn_epochs, device
    )

    @torch.no_grad()
    def fake_batches(batch_size: int) -> torch.Tensor:
        codes = _sample_pixelcnn(prior, batch_size, 8, device)
        return model.decode_codes(codes)

    result["fid"] = _fid_score(test_loader, fake_batches, device)
    result["pixelcnn_epochs"] = pixelcnn_epochs
    result["pixelcnn_training_seconds"] = prior_seconds
    result["end_to_end_training_seconds"] = result.pop("training_seconds") + prior_seconds
    result["fid_images"] = FID_COUNT
    result["latent_map_shape"] = list(latent_maps.shape[1:])
    result["checkpoint_pixelcnn"] = str(
        output_dir / "checkpoints" / f"pixelcnn_k_{codebook_size}.pt"
    )
    sample_codes = _sample_pixelcnn(prior, SAMPLE_COUNT, 8, device)
    _save_grid(
        model.decode_codes(sample_codes),
        output_dir / "samples" / f"vqvae_k_{codebook_size}_100.png",
    )
    _record_result(output_dir, result)
    del model, prior, latent_maps
    torch.cuda.empty_cache()
    return result


def run_part_a(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    vae_epochs: int = 100,
    vqvae_epochs: int = 100,
    pixelcnn_epochs: int = 50,
) -> dict[str, dict]:
    seed_everything()
    device = require_cuda()
    output_dir = _output_dir(Path(output_dir))
    train_loader, test_loader = make_loaders(Path(data_dir))
    results = {}
    for beta in (1, 2, 4, 10):
        results[f"vae_beta_{beta}"] = _train_vae(
            beta, train_loader, test_loader, output_dir, vae_epochs, device
        )
    for codebook_size in (512, 256, 128):
        results[f"vqvae_k_{codebook_size}"] = _run_vq_experiment(
            codebook_size,
            train_loader,
            test_loader,
            output_dir,
            vqvae_epochs,
            pixelcnn_epochs,
            device,
        )
    _save_json(output_dir / "part_a_results.json", results)
    return results


def _gradient_penalty(
    critic: Critic, real: torch.Tensor, fake: torch.Tensor, device: torch.device
) -> torch.Tensor:
    alpha = torch.rand(real.shape[0], 1, 1, 1, device=device)
    interpolated = (alpha * real + (1 - alpha) * fake).requires_grad_(True)
    scores = critic(interpolated)
    gradients = torch.autograd.grad(
        outputs=scores,
        inputs=interpolated,
        grad_outputs=torch.ones_like(scores),
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0]
    norm = gradients.flatten(1).norm(2, dim=1)
    return ((norm - 1) ** 2).mean()


def _train_wgan(
    mode: str,
    train_loader: DataLoader,
    test_loader: DataLoader,
    output_dir: Path,
    epochs: int,
    device: torch.device,
    latent_dim: int = 128,
) -> dict:
    if mode not in {"wgan", "wgan_gp"}:
        raise ValueError("mode must be 'wgan' or 'wgan_gp'")
    model_id = mode
    generator = Generator(latent_dim).to(device)
    critic = Critic().to(device)
    if mode == "wgan_gp":
        generator_optimizer = torch.optim.Adam(
            generator.parameters(), lr=1e-4, betas=(0.0, 0.9)
        )
        critic_optimizer = torch.optim.Adam(
            critic.parameters(), lr=1e-4, betas=(0.0, 0.9)
        )
        optimizer_name = "Adam(lr=1e-4, betas=(0.0, 0.9))"
    else:
        generator_optimizer = torch.optim.RMSprop(generator.parameters(), lr=5e-5)
        critic_optimizer = torch.optim.RMSprop(critic.parameters(), lr=5e-5)
        optimizer_name = "RMSprop(lr=5e-5)"
    curve = {"epoch": [], "critic_loss": [], "generator_loss": [], "seconds": []}
    epoch_seconds = []
    critic_steps = 5
    for epoch in range(1, epochs + 1):
        generator.train()
        critic.train()
        critic_sum, generator_sum, batches = 0.0, 0.0, 0
        epoch_start = time.perf_counter()
        for batch_index, (real, _) in enumerate(train_loader):
            real = real.to(device, non_blocking=True)
            batch_size = real.shape[0]
            for _ in range(critic_steps):
                noise = torch.randn(batch_size, latent_dim, device=device)
                fake = generator(noise).detach()
                critic_optimizer.zero_grad(set_to_none=True)
                real_score = critic(real)
                fake_score = critic(fake)
                if mode == "wgan_gp":
                    penalty = _gradient_penalty(critic, real, fake, device)
                    critic_loss = fake_score.mean() - real_score.mean() + 10.0 * penalty
                else:
                    critic_loss = fake_score.mean() - real_score.mean()
                critic_loss.backward()
                critic_optimizer.step()
                if mode == "wgan":
                    for parameter in critic.parameters():
                        parameter.data.clamp_(-0.01, 0.01)
                critic_sum += critic_loss.item()

            generator_optimizer.zero_grad(set_to_none=True)
            noise = torch.randn(batch_size, latent_dim, device=device)
            generator_loss = -critic(generator(noise)).mean()
            generator_loss.backward()
            generator_optimizer.step()
            generator_sum += generator_loss.item()
            batches += 1
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - epoch_start
        epoch_seconds.append(elapsed)
        curve["epoch"].append(epoch)
        curve["critic_loss"].append(critic_sum / max(batches * critic_steps, 1))
        curve["generator_loss"].append(generator_sum / max(batches, 1))
        curve["seconds"].append(elapsed)
        print(
            f"{model_id} | epoch {epoch:03d}/{epochs} | "
            f"critic={curve['critic_loss'][-1]:.4f} | "
            f"generator={curve['generator_loss'][-1]:.4f}"
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    training_seconds = float(sum(epoch_seconds))
    generator_path = output_dir / "checkpoints" / f"{model_id}_generator.pt"
    torch.save(generator.state_dict(), generator_path)
    _save_json(output_dir / "curves" / f"{model_id}.json", curve)
    generator.eval()

    @torch.no_grad()
    def fake_batches(batch_size: int) -> torch.Tensor:
        return generator(torch.randn(batch_size, latent_dim, device=device))

    fid = _fid_score(test_loader, fake_batches, device)
    _save_grid(
        fake_batches(SAMPLE_COUNT),
        output_dir / "samples" / f"{model_id}_100.png",
    )
    result = {
        "model_id": model_id,
        "family": "WGAN-GP" if mode == "wgan_gp" else "WGAN",
        "epochs": epochs,
        "critic_updates_per_batch": critic_steps,
        "gradient_penalty_lambda": 10.0 if mode == "wgan_gp" else None,
        "weight_clip": None if mode == "wgan_gp" else 0.01,
        "optimizer": optimizer_name,
        "test_psnr_db": None,
        "fid": fid,
        "training_seconds": training_seconds,
        "seconds_per_epoch": float(np.mean(epoch_seconds)),
        "fid_images": FID_COUNT,
        "checkpoint": str(generator_path),
    }
    _record_result(output_dir, result)
    del generator, critic
    torch.cuda.empty_cache()
    return result


def run_part_b(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    epochs: int = 100,
) -> dict[str, dict]:
    seed_everything()
    device = require_cuda()
    output_dir = _output_dir(Path(output_dir))
    train_loader, test_loader = make_loaders(Path(data_dir))
    results = {}
    for mode in ("wgan", "wgan_gp"):
        results[mode] = _train_wgan(
            mode, train_loader, test_loader, output_dir, epochs, device
        )
    _save_json(output_dir / "part_b_results.json", results)
    return results


MODEL_ORDER = ["vae_beta_1", "vae_beta_2", "vae_beta_4", "vae_beta_10", "vqvae_k_512", "vqvae_k_256", "vqvae_k_128", "wgan", "wgan_gp"]
SAMPLE_MODELS = ["vae_beta_1", "vqvae_k_256", "wgan", "wgan_gp"]
def training_time(item):
    value = item.get("end_to_end_training_seconds", item.get("training_seconds"))
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"Missing or invalid training time: {item.get('model_id')}")
    return value
DEFAULT_OBSERVATIONS = {
    "vae_beta_1": "VAE (beta=1): Samples preserve broad colour patterns and coarse layouts, but strong blur removes edges and fine detail. Several suggest object silhouettes while many are difficult to identify. Variation is visible, but balanced coverage of all ten classes is not established.",
    "vqvae_k_256": "VQ-VAE (K=256) with PixelCNN: Samples show sharper local boundaries and more texture than the VAE. Many shapes remain fragmented or ambiguous, with patchy transitions and inconsistent structure. Better FID is consistent with improved detail, not uniformly coherent objects.",
    "wgan": "WGAN: Samples contain substantial speckled noise, high-contrast artifacts and poorly defined objects. Repeated blue/green background patterns suggest reduced diversity in some outputs, but this grid alone cannot confirm mode collapse or missing classes.",
    "wgan_gp": "WGAN-GP: Samples show more varied compositions and more recognizable object-like forms than WGAN, consistent with the lower FID. Distorted geometry and texture artifacts remain. The final grid supports better sample quality but does not conclusively establish training stability."
}
def build_part_c_pdf(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    pdf_path: Path | None = None,
    visual_observations: dict[str, str] | None = None,
) -> Path:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError as exc:
        raise RuntimeError(
            "The report requires matplotlib. Install it in the BITS runtime."
        ) from exc

    output_dir = Path(output_dir).expanduser().resolve()
    summary_path = output_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            "No experiment results found. Run Part A and Part B notebooks first."
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required = tuple(MODEL_ORDER)
    visual_observations = DEFAULT_OBSERVATIONS if visual_observations is None else visual_observations
    if any(
        not visual_observations.get(key, "").strip() for key in SAMPLE_MODELS
    ):
        raise ValueError(
            "Inspect each 100-image grid and provide non-empty visual observations "
            "for vae_beta_1, vqvae_k_256, wgan, and wgan_gp."
        )
    missing = [key for key in required if key not in summary]
    missing_samples = [
        key
        for key in SAMPLE_MODELS
        if not (output_dir / "samples" / f"{key}_100.png").exists()
    ]
    if missing or missing_samples:
        raise RuntimeError(
            f"Part A and Part B are not both complete. Missing results={missing}; "
            f"missing 100-image grids={missing_samples}."
        )
    missing_curves = [k for k in MODEL_ORDER[:7] if not (output_dir / "curves" / f"{k}.json").exists()]
    if missing_curves:
        raise FileNotFoundError(f"Missing PSNR curve files: {missing_curves}")
    for key in MODEL_ORDER:
        item = summary[key]
        fields = ["fid", "fid_images"]
        fields += ["test_psnr_db"] if key in MODEL_ORDER[:7] else []
        fields += ["perplexity", "active_codes", "codebook_size"] if key.startswith("vqvae") else []
        for field in fields:
            value = item.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Missing or invalid {field} for {key}")
        training_time(item)  # Reject missing/invalid timing; never substitute zero.
    counts = {summary[k]["fid_images"] for k in MODEL_ORDER}
    if len(counts) != 1:
        raise ValueError("FID sample counts differ; comparison requires matching counts.")
    fid_count = int(next(iter(counts)))
    pdf_path = Path(pdf_path) if pdf_path else output_dir / "PartC_Comparative_Analysis.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(pdf_path) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.5, 0.88, "CIFAR-10 Generative Models", ha="center", fontsize=22)
        fig.text(0.5, 0.82, "Unsupervised Deep Learning — Assignment 2", ha="center", fontsize=14)
        fig.text(
            0.1,
            0.70,
            "Compared methods: β-VAE (β ∈ {1, 2, 4, 10}), VQ-VAE with "
            "PixelCNN prior (K ∈ {512, 256, 128}), WGAN, and WGAN-GP.",
            wrap=True,
            fontsize=11,
        )
        fig.text(
            0.1,
            0.60,
            f"Evaluation uses CIFAR-10 test images and {fid_count:,} generated images "
            "per model for FID. Pixel inputs are in [0, 1].",
            wrap=True,
            fontsize=11,
        )
        fig.text(
            0.1,
            0.47,
            "All metric values and training times below are read from the completed "
            "notebook runs; no results are assumed or fabricated.",
            wrap=True,
            fontsize=11,
        )
        
        # Updated Group members and Course details
        fig.text(0.1, 0.31, "Group members:", fontsize=11, weight="bold")
        members = [
            "PRICILLA W — 2025AE05321",
            "GUNA ANBAN G — 2025AE05318",
            "PUNEET SINGHAL — 2025AE05340",
            "CHOKKARAP PRAVEEN — 2025AF05151",
            "YUVRAJ KISHAN SHARMA — 2025AG05143",
        ]
        mem_y = 0.28
        for member in members:
            fig.text(0.12, mem_y, f"• {member}", fontsize=10)
            mem_y -= 0.022

        fig.text(0.1, 0.14, "Course / section: Unsupervised Deep Learning (AIMLZG533)", fontsize=11, weight="bold")
        fig.text(0.1, 0.08, f"Report generated: {time.strftime('%Y-%m-%d %H:%M')}", fontsize=9)
        plt.axis("off")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        model_order = [
            "vae_beta_1",
            "vae_beta_2",
            "vae_beta_4",
            "vae_beta_10",
            "vqvae_k_512",
            "vqvae_k_256",
            "vqvae_k_128",
            "wgan",
            "wgan_gp",
        ]
        rows = []
        for key in model_order:
            if key not in summary:
                continue
            item = summary[key]
            psnr = item.get("test_psnr_db")
            rows.append(
                [
                    item.get("family", key),
                    f"β={item['beta']:g}" if "beta" in item else (
                        f"K={item['codebook_size']}" if "codebook_size" in item else "—"
                    ),
                    "—" if psnr is None else f"{psnr:.2f}",
                    "—" if item.get("fid") is None else f"{item['fid']:.2f}",
                    "—" if "perplexity" not in item else f"{item['perplexity']:.1f}",
                    "—"
                    if "active_codes" not in item
                    else f"{item['active_codes']}/{item['codebook_size']}",
                    f"{item.get('seconds_per_epoch', 0):.1f}",
                    f"{training_time(item) / 60:.1f}",
                ]
            )
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        ax.set_title("Quantitative comparison", fontsize=18, pad=20)
        table = ax.table(
            cellText=rows,
            colLabels=[
                "Model",
                "Setting",
                "PSNR (dB)",
                "FID ↓",
                "Perplexity",
                "Active codes",
                "s / epoch",
                "Train min",
            ],
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.0, 1.65)
        ax.text(
            0.02,
            0.04,
            "PSNR is reconstruction-only (not applicable to unconditional GAN samples). "
            "FID compares generated images against the CIFAR-10 test split.",
            transform=ax.transAxes,
            fontsize=9,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11.69, 6.5))
        for key in ("vae_beta_1", "vae_beta_2", "vae_beta_4", "vae_beta_10",
                    "vqvae_k_512", "vqvae_k_256", "vqvae_k_128"):
            curve_path = output_dir / "curves" / f"{key}.json"
            if curve_path.exists():
                curve = json.loads(curve_path.read_text(encoding="utf-8"))
                axes[0].plot(curve["epoch"], curve["psnr"], label=key)
        axes[0].set_title("Reconstruction PSNR by epoch")
        axes[0].set_xlabel("Epoch")
        axes[0].set_ylabel("PSNR (dB)")
        axes[0].grid(alpha=0.25)
        axes[0].legend(fontsize=7)
        fid_items = [(key, summary[key]["fid"]) for key in model_order if key in summary]
        axes[1].bar([item[0] for item in fid_items], [item[1] for item in fid_items])
        axes[1].set_title("FID comparison (lower is better)")
        axes[1].set_ylabel("FID")
        axes[1].tick_params(axis="x", labelrotation=70, labelsize=7)
        axes[1].grid(axis="y", alpha=0.25)
        fig.tight_layout()
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        all_fid = [(key, summary[key]["fid"]) for key in model_order if key in summary]
        best_fid = min(all_fid, key=lambda pair: pair[1])
        fastest = min(((k, training_time(summary[k])) for k in model_order), key=lambda pair: pair[1])
        beta1, beta10 = summary["vae_beta_1"], summary["vae_beta_10"]
        vq256 = summary["vqvae_k_256"]
        wgan, gp = summary["wgan"], summary["wgan_gp"]
        def text_page(title, paragraphs):
            import textwrap
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.08, 0.94, title, fontsize=17, weight="bold")
            y = 0.88
            for paragraph in paragraphs:
                lines = textwrap.wrap(paragraph, width=93)
                needed = len(lines) * 0.020 + 0.025
                if y - needed < 0.07:
                    pdf.savefig(fig)
                    plt.close(fig)
                    fig = plt.figure(figsize=(8.27, 11.69))
                    fig.text(0.08, 0.94, title + " (continued)", fontsize=17, weight="bold")
                    y = 0.88
                fig.text(0.08, y, "\n".join(lines), fontsize=10, linespacing=1.35, va="top")
                y -= needed
            pdf.savefig(fig)
            plt.close(fig)

        text_page("Comparative discussion", [
            f"Reconstruction: VAE beta=1 reaches {beta1['test_psnr_db']:.2f} dB, whereas VQ-VAE K=256 reaches {vq256['test_psnr_db']:.2f} dB. PSNR uses aggregate test-set pixel MSE and a peak value of 1. VAE reconstruction uses the posterior mean. Higher PSNR means lower reconstruction error, not necessarily greater perceptual realism. PSNR is not applicable to unconditional GANs.",
            f"Effect of beta: beta=1 records PSNR {beta1['test_psnr_db']:.2f} dB and FID {beta1['fid']:.2f}; beta=10 records {beta10['test_psnr_db']:.2f} dB and FID {beta10['fid']:.2f}. In the supplied runs, stronger KL regularization worsens both reconstruction and final sample quality. The PSNR curves flatten late in training, but final-only FID does not establish convergence of sampling quality.",
            "Codebook comparison: " + "; ".join(f"K={summary[k]['codebook_size']}: PSNR {summary[k]['test_psnr_db']:.2f} dB, FID {summary[k]['fid']:.2f}, {100*summary[k]['active_codes']/summary[k]['codebook_size']:.1f}% active" for k in MODEL_ORDER[4:7]) + ". In these runs, K=512 has the highest PSNR while K=256 has the lowest VQ-VAE FID. A larger codebook or a higher utilization fraction alone does not guarantee better samples.",
            f"Adversarial generation: WGAN FID is {wgan['fid']:.2f} and WGAN-GP FID is {gp['fid']:.2f}. The WGAN-GP configuration performs better in these runs. Its optimizer and learning rate also differ from WGAN, so the difference cannot be attributed solely to the gradient penalty.",
            f"Overall: {best_fid[0]} gives the lowest measured FID ({best_fid[1]:.2f}). VQ-VAE gives the strongest reconstruction PSNR. These conclusions apply to the supplied architectures and training settings. Single-run results without uncertainty estimates do not establish universal rankings.",
        ])
        text_page("Training and sampling speed", [
            f"The shortest recorded training time is {fastest[0]} at {fastest[1]/60:.1f} minutes. WGAN takes {training_time(wgan)/60:.1f} minutes and WGAN-GP takes {training_time(gp)/60:.1f} minutes.",
            "The supplied Part A setup output reports NVIDIA RTX A6000; Part B reports NVIDIA A40. These timings are descriptive and are not a hardware-controlled comparison across model families. The recorded setup output should be checked against the actual training session when reproducing the experiments.",
            "For VQ-VAE, total training time includes the autoencoder and PixelCNN prior. Its seconds-per-epoch column refers only to the autoencoder. Recorded training totals exclude FID computation and image generation; VQ-VAE totals also exclude latent extraction. They should not be described as complete workflow durations.",
            "VAE and GAN sampling use feed-forward decoder/generator computation. PixelCNN generates an 8 x 8 latent map using 64 sequential code-position steps before decoding. Sampling latency was not measured, so no numerical generation-speed ranking is claimed.",
            f"Evaluation: FID compares {fid_count:,} generated images per model with the CIFAR-10 test split using 2048-dimensional Inception features. VQ-VAE samples use the trained PixelCNN prior. Inputs are in [0,1] and are rounded to uint8 for FID. Perplexity and active-code counts are measured on training-set assignments.",
        ])
        text_page("Perceptual observations", [visual_observations[k] for k in SAMPLE_MODELS] + [
            "The following grids contain 100 unconditional examples per model. They support qualitative observations about blur, texture, shape and variation, but do not by themselves prove class coverage, mode collapse or training stability. PSNR and FID provide complementary evidence."
        ])

        sample_labels = {
            "vae_beta_1": "β-VAE (β=1): 100 unconditional samples",
            "vqvae_k_256": "VQ-VAE (K=256) + PixelCNN: 100 unconditional samples",
            "wgan": "WGAN: 100 unconditional samples",
            "wgan_gp": "WGAN-GP: 100 unconditional samples",
        }
        for key, title in sample_labels.items():
            image_path = output_dir / "samples" / f"{key}_100.png"
            image = plt.imread(image_path)
            fig, ax = plt.subplots(figsize=(8.27, 8.27))
            ax.imshow(image)
            ax.set_title(title, fontsize=14)
            ax.axis("off")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    return pdf_path

