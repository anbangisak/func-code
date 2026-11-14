import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def markdown(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def write_notebook(name: str, cells: list[dict]) -> None:
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (ROOT / name).write_text(json.dumps(notebook, indent=1), encoding="utf-8")


write_notebook(
    "Part_A.ipynb",
    [
        markdown(
            """# Part A — β-VAE and VQ-VAE + PixelCNN (CIFAR-10)

This notebook covers every Part A task: train β-VAE for β={1,2,4,10}; track test-set reconstruction PSNR by epoch; measure FID; train VQ-VAE for K={512,256,128}; extract discrete latent maps; train a masked PixelCNN prior; sample new latent maps and decode images; compare PSNR, FID, and codebook utilization.

**Run on the provisioned BITS Prayogshala/WILP CUDA GPU.** The assignment requires that infrastructure. Pixel values are converted to `[0,1]` by `ToTensor()`. The VAE loss is summed pixel MSE plus β times summed KL; PSNR uses deterministic posterior-mean reconstructions. FID uses the CIFAR-10 test split and 10,000 generated samples per model. Keep `assignment2_solution.py` beside this notebook.

If FID dependencies are missing in the lab environment, install them in a notebook cell with `%pip install "torchmetrics[image]"` and restart the kernel. Do not report unrun/default metrics as experimental results.
"""
        ),
        code(
            """from pathlib import Path
import sys
import torch
import matplotlib.pyplot as plt
from IPython.display import display, Image

candidates = [Path.cwd(), *Path.cwd().parents]
ROOT = next((p for p in candidates if (p / "assignment2_solution.py").is_file()), None)
if ROOT is None:
    raise FileNotFoundError("Place this notebook and assignment2_solution.py in the same folder.")
sys.path.insert(0, str(ROOT))
from assignment2_solution import run_part_a

if not torch.cuda.is_available():
    raise RuntimeError("Use the BITS-provisioned CUDA GPU runtime for this assignment.")
print("GPU:", torch.cuda.get_device_name(0))
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
"""
        ),
        markdown(
            """## Train and evaluate all Part A variants

Default training uses 100 epochs per VAE/VQ-VAE and 50 epochs per PixelCNN. Keep these settings identical across the compared variants. If lab time forces a change, state the actual epoch counts and rerun all compared models consistently. FID relies on the Inception feature extractor supplied by TorchMetrics/torch-fidelity; the first run may download its pretrained weights.
"""
        ),
        code(
            """results_a = run_part_a(
    data_dir=DATA_DIR,
    output_dir=OUTPUT_DIR,
    vae_epochs=100,
    vqvae_epochs=100,
    pixelcnn_epochs=50,
)
display(list(results_a.values()))
"""
        ),
        markdown("## PSNR curves and generated examples"),
        code(
            """import json

for name in (
    "vae_beta_1", "vae_beta_2", "vae_beta_4", "vae_beta_10",
    "vqvae_k_512", "vqvae_k_256", "vqvae_k_128",
):
    with (OUTPUT_DIR / "curves" / f"{name}.json").open() as f:
        curve = json.load(f)
    plt.plot(curve["epoch"], curve["psnr"], label=name)
plt.xlabel("Epoch")
plt.ylabel("Test reconstruction PSNR (dB)")
plt.title("Part A — PSNR versus epochs")
plt.grid(alpha=0.25)
plt.legend()
plt.show()

for name in ("vae_beta_1", "vqvae_k_512", "vqvae_k_256", "vqvae_k_128"):
    print(name, "— 100 samples")
    display(Image(filename=str(OUTPUT_DIR / "samples" / f"{name}_100.png")))
"""
        ),
        markdown(
            """## Interpretation checklist

- Report PSNR against epochs for each β and K; state that higher PSNR indicates lower pixel reconstruction error.
- Compare FID (lower is better) using the common 10,000-image protocol.
- For β-VAE, discuss the reconstruction–regularization trade-off as β increases.
- For VQ-VAE, report codebook perplexity, active-code count/fraction, and relate code usage to PSNR/FID.
- Confirm that PixelCNN is trained on encoded **training-set** latent maps and that generated maps are decoded by the matching VQ-VAE.
- Capture a genuine screenshot of the active BITS lab GPU runtime for submission; this notebook cannot create that evidence.

After executing all cells and saving the notebook with outputs, export the HTML without rerunning training: `jupyter nbconvert --to html Part_A.ipynb`. Include `assignment2_solution.py` with the notebook when moving it to the lab.
"""
        ),
    ],
)

write_notebook(
    "Part_B.ipynb",
    [
        markdown(
            """# Part B — WGAN and WGAN-GP (CIFAR-10)

This notebook trains a weight-clipped WGAN and WGAN-GP, generates random samples, and computes FID for each. Both models use the same generator/critic architecture, CIFAR-10 `[0,1]` inputs, latent dimension, batch size, and epoch count. The critic is updated five times per generator update. WGAN uses RMSprop and weight clipping at 0.01; WGAN-GP uses Adam and a gradient penalty with λ=10. The optimizer difference is recorded and should be noted when interpreting the comparison.

**Run on the provisioned BITS Prayogshala/WILP CUDA GPU.** FID compares 10,000 generated images with the CIFAR-10 test split. Unconditional GANs do not reconstruct an input, so PSNR is not applicable; do not report an invented PSNR.
"""
        ),
        code(
            """from pathlib import Path
import sys
import torch
import matplotlib.pyplot as plt
from IPython.display import display, Image

candidates = [Path.cwd(), *Path.cwd().parents]
ROOT = next((p for p in candidates if (p / "assignment2_solution.py").is_file()), None)
if ROOT is None:
    raise FileNotFoundError("Place this notebook and assignment2_solution.py in the same folder.")
sys.path.insert(0, str(ROOT))
from assignment2_solution import run_part_b

if not torch.cuda.is_available():
    raise RuntimeError("Use the BITS-provisioned CUDA GPU runtime for this assignment.")
print("GPU:", torch.cuda.get_device_name(0))
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
"""
        ),
        markdown(
            """## Train, sample, and evaluate

The default is 100 epochs for each GAN. WGAN-GP is computationally expensive because the gradient penalty differentiates through the critic. Use the same epoch count for both models and report the actual count and GPU model. FID dependencies: `%pip install "torchmetrics[image]"` if not already available (then restart the kernel).
"""
        ),
        code(
            """results_b = run_part_b(data_dir=DATA_DIR, output_dir=OUTPUT_DIR, epochs=100)
display(list(results_b.values()))
"""
        ),
        markdown("## Loss histories and 100 generated samples per model"),
        code(
            """import json

for name in ("wgan", "wgan_gp"):
    with (OUTPUT_DIR / "curves" / f"{name}.json").open() as f:
        curve = json.load(f)
    plt.plot(curve["epoch"], curve["generator_loss"], label=f"{name} generator")
plt.xlabel("Epoch")
plt.ylabel("Generator loss (critic-score convention)")
plt.title("Part B — training curves")
plt.grid(alpha=0.25)
plt.legend()
plt.show()

for name in ("wgan", "wgan_gp"):
    print(name, "— 100 samples")
    display(Image(filename=str(OUTPUT_DIR / "samples" / f"{name}_100.png")))
"""
        ),
        markdown(
            """## Interpretation checklist

- Compare WGAN and WGAN-GP FID under the same test split, sample count, architecture, and epoch count.
- Explain weight clipping versus the WGAN-GP gradient penalty (λ=10), and relate observed stability to the loss curves.
- Inspect sharpness, diversity, object coherence, artifacts, and repeated/missing modes in the 100-image grids.
- State clearly that reconstruction PSNR is not defined for these unconditional generators.
- Capture and submit a genuine screenshot showing GPU use in the BITS lab environment.

After executing all cells and saving the notebook with outputs, export HTML without rerunning training: `jupyter nbconvert --to html Part_B.ipynb`. Include `assignment2_solution.py` with the notebook when moving it to the lab.
"""
        ),
    ],
)

write_notebook(
    "Part_C_Report.ipynb",
    [
        markdown(
            """# Part C — Comparative analysis and PDF

Run Part A and Part B first. This notebook reads the **measured** scores, curves, timings, and 100-image grids from `outputs/`, then generates `PartC_Comparative_Analysis.pdf`. It includes all requested models, reconstruction PSNR and FID comparisons, codebook quality, measured runtime, and 100 sample images each for β-VAE (β=1), VQ-VAE (K=256), WGAN, and WGAN-GP.

Inspect the four 100-image grids before filling in the observations below. These notes are deliberately required rather than auto-invented; summarize what you actually see (sharpness, coherence, diversity, artifacts, repetitions/mode collapse).
"""
        ),
        code(
            """from pathlib import Path
import sys
from IPython.display import display, IFrame

candidates = [Path.cwd(), *Path.cwd().parents]
ROOT = next((p for p in candidates if (p / "assignment2_solution.py").is_file()), None)
if ROOT is None:
    raise FileNotFoundError("Place this notebook and assignment2_solution.py in the same folder.")
sys.path.insert(0, str(ROOT))
from assignment2_solution import build_part_c_pdf

OUTPUT_DIR = ROOT / "outputs"
"""
        ),
        markdown("## Your visual observations — complete from the generated sample grids"),
        code(
            """visual_observations = {
    "vae_beta_1": "",   # Describe the 100 β=1 VAE samples.
    "vqvae_k_256": "",  # Describe the 100 K=256 VQ-VAE + PixelCNN samples.
    "wgan": "",         # Describe the 100 WGAN samples.
    "wgan_gp": "",      # Describe the 100 WGAN-GP samples.
}
"""
        ),
        code(
            """pdf_path = build_part_c_pdf(
    output_dir=OUTPUT_DIR,
    visual_observations=visual_observations,
)
print("Created:", pdf_path)
display(IFrame(src=str(pdf_path), width="100%", height=700))
"""
        ),
        markdown(
            """## Submission checks

- Confirm the PDF contains measured values and the actual sample grids; do not alter reported metrics manually.
- Add group member names and course/section on the cover.
- Submit `PartC_Comparative_Analysis.pdf`, the two executed notebooks with outputs, their HTML exports, the support module, and a genuine JPG screenshot from the BITS GPU infrastructure.
- The report includes a model-level comparison and an observation page; edit and regenerate if the PDF does not reflect your own visual inspection.
"""
        ),
    ],
)

print("Created Part_A.ipynb, Part_B.ipynb, and Part_C_Report.ipynb")
