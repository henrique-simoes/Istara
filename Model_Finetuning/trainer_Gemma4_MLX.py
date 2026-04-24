#!/usr/bin/env python3
"""Fine-tune Gemma-4-E2B-it on Mac Studio M4 Max (36GB unified memory)."""

import torch
from datasets import load_dataset, concatenate_datasets
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer
from peft import LoraConfig, TaskType

MODEL_ID = "google/gemma-4-E2B-it"
HUB_MODEL_ID = "henrique-simoes/gemma-4-e2b-istara-ux"
REPO_ID = "henrique-simoes/ux-research-strategy-dataset"

# Mac Studio M4 Max settings — conservative to avoid OOM
BATCH_SIZE = 1        # Keep at 1 for 36GB
GRAD_ACCUM = 32       # Effective batch = 32
MAX_LENGTH = 1024     # Shorter than ideal but fits memory

# 1. Load & merge datasets
print("[1/4] Loading datasets...")
ux_raw = load_dataset(REPO_ID, data_files="data.parquet", split="train")
def to_messages(ex):
    return {"messages": [
        {"role": "user", "content": ex["instruction"]},
        {"role": "assistant", "content": ex["response"]}
    ]}
ux = ux_raw.map(to_messages, remove_columns=ux_raw.column_names)

istara = load_dataset(REPO_ID, data_files="istara_sft/istara_sft_messages.jsonl", split="train")

dataset = concatenate_datasets([ux, istara]).shuffle(seed=42)
print(f"  Combined: {len(dataset)} examples")

# 2. Load model for Apple Silicon
print("[2/4] Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,    # MPS works better with float16 than bf16
    # NO flash_attention_2 — not supported on MPS
    # NO device_map="auto" — we handle device manually
)
model = model.to("mps")
print(f"  {sum(p.numel() for p in model.parameters())/1e9:.1f}B params on MPS")

# 3. LoRA — aggressive rank reduction to save memory
print("[3/4] LoRA setup...")
peft_config = LoraConfig(
    r=8,              # Lower rank than cloud (16→8) to save memory
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.0,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

# 4. Train
print("[4/4] Training...")
trainer = SFTTrainer(
    model=model,
    args=SFTConfig(
        output_dir="gemma-4-istara-ux",
        num_train_epochs=3,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=2e-5,
        max_length=MAX_LENGTH,
        packing=True,
        fp16=True,                    # NOT bf16 — MPS doesn't handle bf16 well
        gradient_checkpointing=True,  # Critical for 36GB
        logging_steps=10,
        logging_first_step=True,
        disable_tqdm=True,
        save_strategy="epoch",
        save_total_limit=2,
        push_to_hub=True,
        hub_model_id=HUB_MODEL_ID,
        seed=42,
        dataloader_num_workers=0,     # MPS doesn't support multiprocess dataloading well
    ),
    train_dataset=dataset,
    processing_class=tokenizer,
    peft_config=peft_config,
)

trainer.train()
trainer.push_to_hub()
print(f"\nDone! https://huggingface.co/{HUB_MODEL_ID}")