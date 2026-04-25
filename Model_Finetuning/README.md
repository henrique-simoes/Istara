# Model Fine-Tuning Pipeline

This directory contains the data pipeline and training scripts for fine-tuning local models (Gemma 4, Qwen, etc.) on UX Research (UXR) tasks.

## Pipeline Overview

1. **Source Adapters** — Parse raw external datasets into normalized nuggets.
2. **Merge** — Deduplicate and compile all nuggets into a single bank.
3. **Dataset Generator** — Sample from the bank and skill definitions to produce SFT JSONL.
4. **Trainer** — Fine-tune the model using Apple MPS or CUDA.

## Files

| File | Purpose |
|------|---------|
| `adapter_qualitative.py` | Ingests `Qualitative-Text-Datasets-for-UX-Research-main/` (JSON/CSV/TXT) |
| `adapter_quantitative.py` | Ingests `UX_datasets-main/` (CSV) |
| `adapter_rtf.py` | Extracts text blocks from `Quant_UX_Research_Examples.rtf` |
| `merge_datasets.py` | Combines legacy + new nuggets, deduplicates, writes `consolidated_bank.py` |
| `consolidated_bank.py` | Unified nugget bank imported by the generator |
| `dataset-json-generator.py` | Generates `istara_sft_*.jsonl` from skills + nuggets |
| `trainer_Gemma4_MPS.py` | PyTorch MPS fine-tuning script for Apple Silicon |
| `trainer_Gemma4_CUDA.py` | CUDA fine-tuning script for NVIDIA GPUs |
| `release_builder.py` | End-to-end Apple Silicon release builder: optional data regeneration, MPS LoRA fine-tuning, adapter merge, GGUF F16/Q4, MLX F16/4-bit, and Hugging Face upload |
| `cleaned_nuggets.py` | Legacy nugget bank (retained for reference) |

## Adding a New Data Source

1. Write a new `adapter_<source>.py` that reads the raw format and yields tuples of `(text, source, [tags])`.
2. Run the adapter to produce a JSONL or Python list file.
3. Update `merge_datasets.py` to include the new adapter output.
4. Run `python merge_datasets.py` to regenerate `consolidated_bank.py`.
5. Regenerate the dataset with `python dataset-json-generator.py`.

## Building a Model Release

For a guided run:

```bash
python Model_Finetuning/release_builder.py
```

For a non-interactive run that resumes from an existing adapter:

```bash
python Model_Finetuning/release_builder.py \
  --base-model google/gemma-4-E2B-it \
  --release-name gemma-4-e2b-it-istara-ux-research \
  --adapter-dir LLMs/gemma-4-istara-ux/checkpoint-399 \
  --skip-data \
  --skip-training \
  --yes
```

The release builder publishes four user-facing model formats when all stages are enabled:

- merged Hugging Face safetensors
- GGUF with Q4_K_M quantization
- MLX F16 for Apple Silicon
- MLX 4-bit for Apple Silicon

For Gemma 4 bases, the builder also copies `processor_config.json` into the merged model and attempts to include a compatible `mmproj-*.gguf` projector in the GGUF folder. You can override this with `--mmproj-repo`. MLX Gemma 4 exports also materialize shared K/V tensors so stricter downstream loaders, including LM Studio's bundled MLX loader, can load the model without missing-parameter errors. Gemma 4 runtime support is still version-sensitive, so use current LM Studio, llama.cpp, Ollama, MLX, vLLM, and SGLang builds when testing released artifacts.

For non-Gemma architectures, use `--target-modules all-linear` unless the model needs a specific PEFT target list.

Local training and release artifacts are written under `LLMs/`, which is intentionally ignored by git. Keep source scripts, Compass docs, planner files, and dataset-generation code outside `LLMs/` so they remain tracked and merge-safe.
