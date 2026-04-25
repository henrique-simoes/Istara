#!/usr/bin/env python3
"""Build and publish Istara fine-tuned model releases.

The script can run the whole local release path:

1. optionally regenerate Istara SFT data
2. optionally fine-tune a base model with LoRA on Apple MPS
3. merge the adapter into a full Hugging Face safetensors model
4. build GGUF F16 plus Q4_K_M
5. build MLX F16 plus MLX 4-bit
6. upload all publishable artifacts to Hugging Face

It is intentionally conservative and resumable. Pass existing paths to skip
expensive stages that already completed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FT_DIR = Path(__file__).resolve().parent
LLM_DIR = ROOT / "LLMs"
DEFAULT_DATASET_REPO = "henrique-simoes/ux-research-strategy-dataset"
DEFAULT_LOCAL_SFT = FT_DIR / "generated_datasets" / "istara_sft_messages.jsonl"
DEFAULT_LLAMA_CPP = Path("/tmp/llama.cpp")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    raise SystemExit(f"Missing required value: {prompt}")


def yes_no(prompt: str, default: bool) -> bool:
    marker = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{marker}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "true", "1"}


def run(cmd: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("\n+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def require_python_module(module: str, package_hint: str | None = None) -> None:
    try:
        __import__(module)
    except Exception as exc:
        hint = package_hint or module
        raise SystemExit(f"Missing Python module {module!r}. Install with: python -m pip install {hint}") from exc


def safe_repo_id(namespace: str, name: str) -> str:
    return f"{namespace.rstrip('/')}/{name.strip('/')}"


def default_slug(model_id: str) -> str:
    return model_id.split("/")[-1].lower().replace("_", "-") + "-istara-ux-research"


def regenerate_dataset() -> None:
    for script in [
        "adapter_qualitative.py",
        "adapter_quantitative.py",
        "adapter_rtf.py",
        "merge_datasets.py",
        "dataset-json-generator.py",
    ]:
        run([sys.executable, script], cwd=FT_DIR)


def load_training_dataset(local_sft: Path, dataset_repo: str, use_hub_sft: bool, smoke: bool):
    require_python_module("datasets")
    from datasets import concatenate_datasets, load_dataset

    hub_sft = f"hf://datasets/{dataset_repo}/istara_sft/istara_sft_messages.jsonl"

    def to_messages(ex):
        return {
            "messages": [
                {"role": "user", "content": ex["instruction"]},
                {"role": "assistant", "content": ex["response"]},
            ]
        }

    def only_messages(ex):
        return {"messages": ex["messages"]}

    ux_raw = load_dataset(dataset_repo, data_files="data.parquet", split="train")
    ux = ux_raw.map(to_messages, remove_columns=ux_raw.column_names)

    if use_hub_sft:
        istara_raw = load_dataset("json", data_files=hub_sft, split="train")
    else:
        if not local_sft.exists():
            raise FileNotFoundError(f"Local SFT dataset not found: {local_sft}")
        istara_raw = load_dataset("json", data_files=str(local_sft), split="train")

    istara = istara_raw.map(only_messages, remove_columns=istara_raw.column_names)
    dataset = concatenate_datasets([ux, istara]).shuffle(seed=42)
    if smoke:
        dataset = dataset.select(range(min(16, len(dataset))))

    print(f"Base UXR examples: {len(ux)}")
    print(f"Istara SFT examples: {len(istara)}")
    print(f"Training examples: {len(dataset)}")
    return dataset


def train_adapter(args: argparse.Namespace) -> Path:
    require_python_module("torch")
    require_python_module("transformers")
    require_python_module("trl")
    require_python_module("peft")

    import torch
    from peft import LoraConfig, TaskType
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    if not torch.backends.mps.is_available():
        raise RuntimeError("PyTorch MPS is not available on this machine.")

    dataset = load_training_dataset(args.local_sft, args.dataset_repo, args.use_hub_sft, args.smoke)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        dtype=torch.float16,
        trust_remote_code=True,
    ).to("mps")
    model.config.use_cache = False

    target_modules: str | tuple[str, ...]
    if args.target_modules == "gemma4":
        target_modules = (
            r"model\.language_model\.layers\.\d+\."
            r"(self_attn\.(q_proj|k_proj|v_proj|o_proj)|mlp\.(gate_proj|up_proj|down_proj))$"
        )
    elif args.target_modules == "all-linear":
        target_modules = "all-linear"
    else:
        target_modules = tuple(x.strip() for x in args.target_modules.split(",") if x.strip())

    peft_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        target_modules=target_modules,
        lora_dropout=0.0,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    trainer = SFTTrainer(
        model=model,
        args=SFTConfig(
            output_dir=str(args.adapter_dir),
            num_train_epochs=args.epochs,
            max_steps=2 if args.smoke else -1,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=args.learning_rate,
            max_length=args.max_length,
            packing=False,
            fp16=False,
            bf16=False,
            gradient_checkpointing=True,
            logging_steps=1 if args.smoke else 10,
            logging_first_step=True,
            save_strategy="no" if args.smoke else "epoch",
            save_total_limit=2,
            seed=42,
            dataloader_num_workers=0,
            dataloader_pin_memory=False,
            report_to=[],
        ),
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(str(args.adapter_dir))
    return args.adapter_dir


def find_adapter_checkpoint(adapter_dir: Path) -> Path:
    if (adapter_dir / "adapter_config.json").exists():
        return adapter_dir
    checkpoints = sorted(
        [p for p in adapter_dir.glob("checkpoint-*") if (p / "adapter_config.json").exists()],
        key=lambda p: int(p.name.split("-")[-1]),
    )
    if not checkpoints:
        raise FileNotFoundError(f"No PEFT adapter checkpoint found under {adapter_dir}")
    return checkpoints[-1]


def merge_adapter(base_model: str, adapter_dir: Path, merged_dir: Path, release_name: str) -> Path:
    require_python_module("torch")
    require_python_module("transformers")
    require_python_module("peft")

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    checkpoint = find_adapter_checkpoint(adapter_dir)
    merged_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        dtype=torch.float16,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(model, checkpoint)
    model = model.merge_and_unload()
    model.save_pretrained(merged_dir, safe_serialization=True, max_shard_size="4GB")
    tokenizer.save_pretrained(merged_dir)
    copy_hf_file_if_exists(base_model, "processor_config.json", merged_dir / "processor_config.json")
    write_readme(
        merged_dir / "README.md",
        title=release_name,
        body=(
            f"Merged Hugging Face safetensors release for `{release_name}`.\n\n"
            f"Base model: `{base_model}`\n\n"
            f"Adapter source: `{checkpoint}`\n"
        ),
    )
    return merged_dir


def copy_hf_file_if_exists(repo_id: str, filename: str, destination: Path) -> bool:
    try:
        from huggingface_hub import hf_hub_download

        source = Path(hf_hub_download(repo_id, filename))
    except Exception:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def ensure_llama_cpp(path: Path) -> tuple[Path, Path]:
    if not (path / ".git").exists():
        run(["git", "clone", "https://github.com/ggerganov/llama.cpp", str(path)], cwd=ROOT)
    else:
        run(["git", "-C", str(path), "pull", "--ff-only"], cwd=ROOT)

    quantize = path / "build" / "bin" / "llama-quantize"
    converter = path / "convert_hf_to_gguf.py"
    if not quantize.exists():
        run(["cmake", "-S", str(path), "-B", str(path / "build"), "-DGGML_METAL=ON", "-DCMAKE_BUILD_TYPE=Release"], cwd=ROOT)
        jobs = str(os.cpu_count() or 4)
        run(["cmake", "--build", str(path / "build"), "--config", "Release", "-j", jobs], cwd=ROOT)
    return converter, quantize


def build_gguf(
    merged_dir: Path,
    output_dir: Path,
    release_name: str,
    llama_cpp: Path,
    qtype: str,
    mmproj_repo: str | None = None,
) -> tuple[Path, Path]:
    converter, quantize = ensure_llama_cpp(llama_cpp)
    output_dir.mkdir(parents=True, exist_ok=True)
    f16 = output_dir / f"{release_name}-f16.gguf"
    q4 = output_dir / f"{release_name}-{qtype}.gguf"
    run([sys.executable, str(converter), str(merged_dir), "--outfile", str(f16), "--outtype", "f16", "--model-name", release_name])
    run([str(quantize), str(f16), str(q4), qtype])
    mmproj_line = ""
    if mmproj_repo:
        mmproj_file = copy_first_mmproj(mmproj_repo, output_dir)
        if mmproj_file:
            mmproj_line = f"- `{mmproj_file.name}`: base multimodal projector copied from `{mmproj_repo}`.\n"
    write_readme(
        output_dir / "README.md",
        title=f"{release_name} GGUF",
        body=(
            f"GGUF artifacts for `{release_name}`.\n\n"
            f"- `{q4.name}`: {qtype} quantized build.\n"
            f"- `{f16.name}`: F16 build.\n"
            f"{mmproj_line}"
        ),
    )
    return f16, q4


def infer_mmproj_repo(base_model: str) -> str | None:
    if not base_model.startswith("google/gemma-4-"):
        return None
    return f"lmstudio-community/{base_model.split('/')[-1]}-GGUF"


def copy_first_mmproj(repo_id: str, output_dir: Path) -> Path | None:
    require_python_module("huggingface_hub")
    from huggingface_hub import HfApi, hf_hub_download

    try:
        info = HfApi().model_info(repo_id)
    except Exception as exc:
        print(f"[WARN] Could not inspect mmproj repo {repo_id}: {exc}")
        return None

    candidates = sorted(
        sibling.rfilename
        for sibling in info.siblings
        if sibling.rfilename.startswith("mmproj-") and sibling.rfilename.endswith(".gguf")
    )
    if not candidates:
        print(f"[WARN] No mmproj GGUF found in {repo_id}")
        return None

    # Prefer BF16/F16 projectors, then fall back to the first projector.
    selected = next((c for c in candidates if "BF16" in c.upper() or "F16" in c.upper()), candidates[0])
    source = Path(hf_hub_download(repo_id, selected))
    destination = output_dir / Path(selected).name
    shutil.copy2(source, destination)
    return destination


def build_mlx(merged_dir: Path, mlx_root: Path, release_name: str) -> tuple[Path, Path]:
    require_python_module("mlx_lm", "mlx-lm>=0.31.3")
    f16_dir = mlx_root / f"{release_name}-MLX-F16"
    q4_dir = mlx_root / f"{release_name}-MLX-4bit"
    if f16_dir.exists():
        shutil.rmtree(f16_dir)
    if q4_dir.exists():
        shutil.rmtree(q4_dir)
    run(["mlx_lm.convert", "--hf-path", str(merged_dir), "--mlx-path", str(f16_dir), "--dtype", "float16", "--trust-remote-code"])
    run([
        "mlx_lm.convert",
        "--hf-path",
        str(merged_dir),
        "--mlx-path",
        str(q4_dir),
        "--quantize",
        "--q-bits",
        "4",
        "--q-group-size",
        "64",
        "--dtype",
        "float16",
        "--trust-remote-code",
    ])
    write_readme(
        f16_dir / "README.md",
        title=f"{release_name} MLX F16",
        body=f"Apple MLX F16 conversion of `{release_name}`.\n",
        library="mlx",
    )
    write_readme(
        q4_dir / "README.md",
        title=f"{release_name} MLX 4-bit",
        body=f"Apple MLX 4-bit conversion of `{release_name}`.\n",
        library="mlx",
    )
    materialize_gemma4_mlx_shared_kv(f16_dir)
    materialize_gemma4_mlx_shared_kv(q4_dir)
    return f16_dir, q4_dir


def materialize_gemma4_mlx_shared_kv(model_dir: Path) -> None:
    """Backfill Gemma 4 shared K/V tensors for stricter MLX loaders.

    MLX-LM 0.31.3 can load Gemma 4 models whose shared-KV layers omit
    duplicate K/V tensors. Some downstream apps bundle stricter MLX loaders and
    still expect those tensors to exist. Public mlx-community Gemma 4 releases
    materialize them, so we do the same for portability.
    """

    config_path = model_dir / "config.json"
    if not config_path.exists():
        return

    config = json.loads(config_path.read_text(encoding="utf-8"))
    text_config = config.get("text_config") or {}
    if config.get("model_type") != "gemma4" or not text_config.get("num_kv_shared_layers"):
        return

    require_python_module("torch")
    require_python_module("safetensors")
    from huggingface_hub.serialization import save_torch_state_dict
    from safetensors.torch import load_file, save_file

    weight_files = sorted(model_dir.glob("model*.safetensors"))
    if not weight_files:
        return

    state = {}
    for weight_file in weight_files:
        state.update(load_file(str(weight_file)))

    layer_types = text_config["layer_types"]
    first_shared = text_config["num_hidden_layers"] - text_config["num_kv_shared_layers"]
    kvs_by_type: dict[str, int] = {}
    for layer_idx in range(first_shared):
        kvs_by_type[layer_types[layer_idx]] = layer_idx

    suffixes = (
        "self_attn.k_norm.weight",
        "self_attn.k_proj.weight",
        "self_attn.k_proj.scales",
        "self_attn.k_proj.biases",
        "self_attn.v_proj.weight",
        "self_attn.v_proj.scales",
        "self_attn.v_proj.biases",
    )

    added = 0
    for target_idx in range(first_shared, text_config["num_hidden_layers"]):
        source_idx = kvs_by_type[layer_types[target_idx]]
        for suffix in suffixes:
            source_key = f"language_model.model.layers.{source_idx}.{suffix}"
            target_key = f"language_model.model.layers.{target_idx}.{suffix}"
            if target_key not in state and source_key in state:
                state[target_key] = state[source_key].clone()
                added += 1

    if not added:
        return

    def clear_existing_weights() -> None:
        for weight_file in model_dir.glob("model*.safetensors"):
            weight_file.unlink()
        index_file = model_dir / "model.safetensors.index.json"
        if index_file.exists():
            index_file.unlink()

    has_uint32 = any(str(t.dtype).endswith("uint32") for t in state.values())
    clear_existing_weights()
    if has_uint32:
        # huggingface_hub's torch sharder does not currently know uint32 tensor
        # sizes, but safetensors itself can store them. Quantized MLX models use
        # uint32 packed weights, so write a single safetensors file plus a small
        # index for strict loaders.
        model_file = model_dir / "model.safetensors"
        save_file(state, str(model_file))
        total_size = sum(t.numel() * t.element_size() for t in state.values())
        index = {
            "metadata": {"total_size": total_size},
            "weight_map": {key: model_file.name for key in sorted(state)},
        }
        (model_dir / "model.safetensors.index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        save_torch_state_dict(
            state,
            model_dir,
            max_shard_size="4GB",
            safe_serialization=True,
            filename_pattern="model{suffix}.safetensors",
        )
    print(f"[INFO] Materialized {added} Gemma 4 shared-KV MLX tensors in {model_dir}")


def write_readme(path: Path, title: str, body: str, library: str | None = None) -> None:
    library_line = f"library_name: {library}\n" if library else ""
    path.write_text(
        "---\n"
        "language: en\n"
        "license: gemma\n"
        "pipeline_tag: text-generation\n"
        f"{library_line}"
        "tags:\n"
        "  - ux-research\n"
        "  - istara\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


def upload_folder(repo_id: str, folder: Path, message: str) -> None:
    require_python_module("huggingface_hub")
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=False)
    api.upload_folder(repo_id=repo_id, repo_type="model", folder_path=str(folder), commit_message=message)
    print(f"Uploaded https://huggingface.co/{repo_id}")


def upload_file(repo_id: str, file_path: Path, path_in_repo: str, message: str) -> None:
    require_python_module("huggingface_hub")
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=False)
    api.upload_file(
        repo_id=repo_id,
        repo_type="model",
        path_or_fileobj=str(file_path),
        path_in_repo=path_in_repo,
        commit_message=message,
    )
    print(f"Uploaded {path_in_repo} to https://huggingface.co/{repo_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model")
    parser.add_argument("--release-name")
    parser.add_argument("--namespace", default="henrique-simoes")
    parser.add_argument("--dataset-repo", default=DEFAULT_DATASET_REPO)
    parser.add_argument("--local-sft", type=Path, default=DEFAULT_LOCAL_SFT)
    parser.add_argument("--use-hub-sft", action="store_true")
    parser.add_argument("--adapter-dir", type=Path)
    parser.add_argument("--merged-dir", type=Path)
    parser.add_argument("--gguf-dir", type=Path)
    parser.add_argument("--mlx-dir", type=Path, default=LLM_DIR / "mlx_models")
    parser.add_argument("--llama-cpp", type=Path, default=DEFAULT_LLAMA_CPP)
    parser.add_argument(
        "--mmproj-repo",
        default=None,
        help="Optional Hugging Face GGUF repo containing a compatible mmproj-*.gguf. Defaults to lmstudio-community/<Gemma-4-base>-GGUF for google/gemma-4-* bases.",
    )
    parser.add_argument("--target-modules", default="gemma4", help="'gemma4', 'all-linear', or a comma-separated PEFT target module list.")
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--qtype", default="Q4_K_M")
    parser.add_argument("--skip-data", action="store_true")
    parser.add_argument("--skip-training", action="store_true")
    parser.add_argument("--skip-gguf", action="store_true")
    parser.add_argument("--skip-mlx", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Do not prompt; require/derive all values.")
    return parser.parse_args()


def complete_args(args: argparse.Namespace) -> argparse.Namespace:
    if not args.yes:
        args.base_model = args.base_model or ask("Base model to fine-tune", "google/gemma-4-E2B-it")
        args.release_name = args.release_name or ask("Release name", default_slug(args.base_model))
        args.namespace = ask("Hugging Face namespace", args.namespace)
        args.skip_data = not yes_no("Regenerate local Istara SFT datasets first", not args.skip_data)
        args.skip_training = not yes_no("Run fine-tuning now", not args.skip_training)
        args.skip_gguf = not yes_no("Build GGUF F16 and Q4", not args.skip_gguf)
        args.skip_mlx = not yes_no("Build MLX F16 and 4-bit", not args.skip_mlx)
        args.skip_upload = not yes_no("Upload publishable artifacts to Hugging Face", not args.skip_upload)

    if not args.base_model:
        raise SystemExit("--base-model is required when --yes is used")
    if not args.release_name:
        args.release_name = default_slug(args.base_model)
    if args.mmproj_repo is None:
        args.mmproj_repo = infer_mmproj_repo(args.base_model)

    args.adapter_dir = args.adapter_dir or LLM_DIR / f"{args.release_name}-adapter"
    args.merged_dir = args.merged_dir or LLM_DIR / "merged_models" / args.release_name
    args.gguf_dir = args.gguf_dir or LLM_DIR / "quantized_models" / args.release_name
    return args


def main() -> int:
    args = complete_args(parse_args())

    if not args.skip_data:
        regenerate_dataset()

    if args.skip_training:
        print(f"Skipping training; using adapter dir: {args.adapter_dir}")
    else:
        train_adapter(args)

    merge_adapter(args.base_model, args.adapter_dir, args.merged_dir, args.release_name)

    gguf_q4 = None
    if not args.skip_gguf:
        _gguf_f16, gguf_q4 = build_gguf(
            args.merged_dir,
            args.gguf_dir,
            args.release_name,
            args.llama_cpp,
            args.qtype,
            args.mmproj_repo,
        )

    mlx_f16 = mlx_q4 = None
    if not args.skip_mlx:
        mlx_f16, mlx_q4 = build_mlx(args.merged_dir, args.mlx_dir, args.release_name)

    if not args.skip_upload:
        upload_folder(safe_repo_id(args.namespace, args.release_name), args.merged_dir, "Upload merged safetensors model")
        if gguf_q4 is not None:
            upload_folder(safe_repo_id(args.namespace, f"{args.release_name}-GGUF"), args.gguf_dir, "Upload GGUF model artifacts")
        if mlx_f16 is not None:
            upload_folder(safe_repo_id(args.namespace, f"{args.release_name}-MLX-F16"), mlx_f16, "Upload MLX F16 model")
        if mlx_q4 is not None:
            upload_folder(safe_repo_id(args.namespace, f"{args.release_name}-MLX-4bit"), mlx_q4, "Upload MLX 4-bit model")

    print("\nDone.")
    print(f"Merged model: {args.merged_dir}")
    if gguf_q4 is not None:
        print(f"GGUF Q4: {gguf_q4}")
    if mlx_f16 is not None:
        print(f"MLX F16: {mlx_f16}")
    if mlx_q4 is not None:
        print(f"MLX 4-bit: {mlx_q4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
