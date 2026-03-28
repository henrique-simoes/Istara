"""Hardware detection and model recommendation engine."""

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass

from app.config import settings


@dataclass
class GpuInfo:
    """GPU information."""

    vendor: str
    name: str
    vram_mb: int
    compute_capability: str | None = None


@dataclass
class HardwareProfile:
    """Complete hardware profile of the system."""

    total_ram_gb: float
    available_ram_gb: float
    cpu_cores: int
    cpu_arch: str
    gpu: GpuInfo | None
    os_name: str
    os_version: str

    @property
    def reclaw_ram_budget_gb(self) -> float:
        """RAM available for ReClaw after reserving for OS/apps.

        The reserve is proportional: on machines with <=8GB, we reserve
        only 2GB instead of the default 4GB to avoid zero-budget situations.
        """
        reserve = settings.resource_reserve_ram_gb
        if self.total_ram_gb <= 8:
            reserve = min(reserve, 2.0)
        elif self.total_ram_gb <= 16:
            reserve = min(reserve, 3.0)
        return max(0, self.available_ram_gb - reserve)

    @property
    def reclaw_cpu_budget_cores(self) -> int:
        """CPU cores available for ReClaw."""
        reserved = int(self.cpu_cores * settings.resource_reserve_cpu_percent / 100)
        return max(1, self.cpu_cores - reserved)


@dataclass
class ModelRecommendation:
    """Recommended model configuration based on hardware."""

    model_name: str
    quantization: str
    context_length: int
    gpu_layers: int
    reason: str


def _detect_nvidia_gpu() -> GpuInfo | None:
    """Detect NVIDIA GPU using nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                return GpuInfo(
                    vendor="NVIDIA",
                    name=parts[0],
                    vram_mb=int(float(parts[1])),
                )
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    return None


def _detect_amd_gpu() -> GpuInfo | None:
    """Detect AMD GPU using rocm-smi."""
    if not shutil.which("rocm-smi"):
        return None
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--csv"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    vram_mb = int(float(parts[1]) / (1024 * 1024))
                    return GpuInfo(vendor="AMD", name="AMD GPU", vram_mb=vram_mb)
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    return None


def _detect_apple_gpu() -> GpuInfo | None:
    """Detect Apple Silicon GPU (unified memory)."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return None
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            total_bytes = int(result.stdout.strip())
            # Apple Silicon shares RAM with GPU — report ~75% as available for GPU
            vram_mb = int((total_bytes / (1024 * 1024)) * 0.75)
            # Detect chip name
            chip_result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            chip_name = chip_result.stdout.strip() if chip_result.returncode == 0 else "Apple Silicon"
            return GpuInfo(vendor="Apple", name=chip_name, vram_mb=vram_mb)
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def detect_hardware() -> HardwareProfile:
    """Detect system hardware capabilities."""
    import psutil  # noqa: delayed import — psutil may not be in all envs

    mem = psutil.virtual_memory()
    total_ram_gb = round(mem.total / (1024**3), 1)
    available_ram_gb = round(mem.available / (1024**3), 1)

    gpu = _detect_nvidia_gpu() or _detect_amd_gpu() or _detect_apple_gpu()

    return HardwareProfile(
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        cpu_cores=os.cpu_count() or 1,
        cpu_arch=platform.machine(),
        gpu=gpu,
        os_name=platform.system(),
        os_version=platform.release(),
    )


def recommend_model(profile: HardwareProfile) -> ModelRecommendation:
    """Recommend the best model configuration based on hardware profile."""
    ram = profile.reclaw_ram_budget_gb
    gpu_vram_gb = (profile.gpu.vram_mb / 1024) if profile.gpu else 0
    is_apple = profile.gpu and profile.gpu.vendor == "Apple"

    # Apple Silicon gets special treatment — unified memory means GPU acceleration is free
    if is_apple:
        if ram >= 12:
            return ModelRecommendation(
                model_name="qwen3:14b",
                quantization="Q5_K_M",
                context_length=8192,
                gpu_layers=-1,
                reason=f"Apple Silicon with {profile.total_ram_gb}GB unified memory — full GPU offload",
            )
        if ram >= 6:
            return ModelRecommendation(
                model_name="qwen3:7b",
                quantization="Q5_K_M",
                context_length=8192,
                gpu_layers=-1,
                reason=f"Apple Silicon with {profile.total_ram_gb}GB — good performance with Q5",
            )
        return ModelRecommendation(
            model_name="qwen3:3b",
            quantization="Q4_K_M",
            context_length=4096,
            gpu_layers=-1,
            reason=f"Apple Silicon with limited RAM ({profile.total_ram_gb}GB) — smaller model for comfort",
        )

    # Discrete GPU path
    if gpu_vram_gb >= 8:
        if ram >= 8:
            return ModelRecommendation(
                model_name="qwen3:14b",
                quantization="Q5_K_M",
                context_length=8192,
                gpu_layers=-1,
                reason=f"Strong GPU ({gpu_vram_gb:.0f}GB VRAM) + {ram:.0f}GB RAM — full offload",
            )
        return ModelRecommendation(
            model_name="qwen3:7b",
            quantization="Q6_K",
            context_length=8192,
            gpu_layers=-1,
            reason=f"Good GPU ({gpu_vram_gb:.0f}GB VRAM) — high quality quantization",
        )

    if gpu_vram_gb >= 4:
        return ModelRecommendation(
            model_name="qwen3:7b",
            quantization="Q4_K_M",
            context_length=8192,
            gpu_layers=20,
            reason=f"Mid GPU ({gpu_vram_gb:.0f}GB VRAM) — partial offload for speed",
        )

    # CPU-only path
    if ram >= 8:
        return ModelRecommendation(
            model_name="qwen3:7b",
            quantization="Q5_K_M",
            context_length=8192,
            gpu_layers=0,
            reason=f"No GPU, but {ram:.0f}GB RAM available — CPU inference",
        )
    if ram >= 4:
        return ModelRecommendation(
            model_name="qwen3:3b",
            quantization="Q4_K_M",
            context_length=4096,
            gpu_layers=0,
            reason=f"Limited RAM ({ram:.0f}GB budget) — compact model",
        )

    return ModelRecommendation(
        model_name="qwen3:1.5b",
        quantization="Q4_K_M",
        context_length=2048,
        gpu_layers=0,
        reason=f"Very limited resources ({ram:.0f}GB budget) — smallest viable model",
    )
