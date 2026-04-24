# Model Fine-Tuning Pipeline

This directory contains the data pipeline and training scripts for fine-tuning local models (Gemma 4, Qwen, etc.) on UX Research (UXR) tasks.

## Pipeline Overview

1. **Source Adapters** — Parse raw external datasets into normalized nuggets.
2. **Merge** — Deduplicate and compile all nuggets into a single bank.
3. **Dataset Generator** — Sample from the bank and skill definitions to produce SFT JSONL.
4. **Trainer** — Fine-tune the model using MLX or CUDA.

## Files

| File | Purpose |
|------|---------|
| `adapter_qualitative.py` | Ingests `Qualitative-Text-Datasets-for-UX-Research-main/` (JSON/CSV/TXT) |
| `adapter_quantitative.py` | Ingests `UX_datasets-main/` (CSV) |
| `adapter_rtf.py` | Extracts text blocks from `Quant_UX_Research_Examples.rtf` |
| `merge_datasets.py` | Combines legacy + new nuggets, deduplicates, writes `consolidated_bank.py` |
| `consolidated_bank.py` | Unified nugget bank imported by the generator |
| `dataset-json-generator.py` | Generates `istara_sft_*.jsonl` from skills + nuggets |
| `trainer_Gemma4_MLX.py` | MLX fine-tuning script for Apple Silicon |
| `trainer_Gemma4_CUDA.py` | CUDA fine-tuning script for NVIDIA GPUs |
| `cleaned_nuggets.py` | Legacy nugget bank (retained for reference) |

## Adding a New Data Source

1. Write a new `adapter_<source>.py` that reads the raw format and yields tuples of `(text, source, [tags])`.
2. Run the adapter to produce a JSONL or Python list file.
3. Update `merge_datasets.py` to include the new adapter output.
4. Run `python merge_datasets.py` to regenerate `consolidated_bank.py`.
5. Regenerate the dataset with `python dataset-json-generator.py`.
