#!/usr/bin/env python3
"""Fine-tune Gemma-4-E2B-it on combined UX + Istara dataset."""

from pathlib import Path

import torch
from datasets import load_dataset, concatenate_datasets
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer
from peft import LoraConfig, TaskType

MODEL_ID = "google/gemma-4-E2B-it"
HUB_MODEL_ID = "henrique-simoes/gemma-4-e2b-istara-ux"
REPO_ID = "henrique-simoes/ux-research-strategy-dataset"
ROOT = Path(__file__).resolve().parent
HUB_SFT_MESSAGES = f"hf://datasets/{REPO_ID}/istara_sft/istara_sft_messages.jsonl"

BATCH_SIZE = 2      # 24GB GPU
GRAD_ACCUM = 16     # effective batch = 32

# 1. Load & merge
print("[1/4] Loading datasets...")
ux_raw = load_dataset(REPO_ID, data_files="data.parquet", split="train")
def to_messages(ex):
    return {"messages": [
        {"role": "user", "content": ex["instruction"]},
        {"role": "assistant", "content": ex["response"]}
    ]}
ux = ux_raw.map(to_messages, remove_columns=ux_raw.column_names)

istara = load_dataset("json", data_files=HUB_SFT_MESSAGES, split="train")

dataset = concatenate_datasets([ux, istara]).shuffle(seed=42)
print(f"  Combined: {len(dataset)} examples")

# 2. Model
print("[2/4] Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
    device_map="auto",
)

# 3. LoRA
print("[3/4] LoRA setup...")
peft_config = LoraConfig(
    r=16, lora_alpha=32,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    lora_dropout=0.0, bias="none", task_type=TaskType.CAUSAL_LM,
)

# 4. Train
print("[4/4] Training...")
trainer = SFTTrainer(
    model=model,
    args=SFTConfig(
        output_dir=str(ROOT.parent / "LLMs" / "gemma-4-istara-ux"),
        num_train_epochs=3,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=2e-5,
        max_length=2048,
        packing=True,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        logging_first_step=True,
        disable_tqdm=True,
        save_strategy="epoch",
        save_total_limit=2,
        push_to_hub=True,
        hub_model_id=HUB_MODEL_ID,
        seed=42,
    ),
    train_dataset=dataset,
    processing_class=tokenizer,
    peft_config=peft_config,
)

trainer.train()
trainer.push_to_hub()
print(f"\nDone! https://huggingface.co/{HUB_MODEL_ID}")
