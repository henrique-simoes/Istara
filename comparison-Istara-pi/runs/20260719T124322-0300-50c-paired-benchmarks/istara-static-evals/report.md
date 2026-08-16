# Istara AI Eval Report

- Status: pass
- Run id: istara-static-evals
- Git: 6e3f7e33 dirty=True
- Compass: CF-SPEC-26 / CF-295
- Model: google/gemma-4-e4b
- Live profile configured: True

## Totals

{
  "total": 8,
  "passed": 8,
  "failed": 0,
  "blocked": 0,
  "pass_rate": 1.0
}

## Suites

### llmlingua
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### memento_skills
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### memory_reasoning_bank
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### meta_hyperagent
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### prompt_rag
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### rag
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### thinking_output
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1
### voice_transcription
- pass_rate: 1.000; passed=1 failed=0 blocked=0 total=1

## Case Results

- rag/rag_keyword_gold: passed score=1.0 duration_ms=4.16
- prompt_rag/prompt_rag_identity_and_relevance: passed score=1.0 duration_ms=0.87
- llmlingua/llmlingua_protected_context: passed score=1.0 duration_ms=1.44
- memory_reasoning_bank/reasoning_bank_distillation_redaction: passed score=1.0 duration_ms=0.13
- memento_skills/memento_skill_definition_coverage: passed score=1.0 duration_ms=10.78
- meta_hyperagent/meta_hyperagent_bounds: passed score=1.0 duration_ms=0.27
- thinking_output/thinking_marker_sanitization: passed score=1.0 duration_ms=0.04
- voice_transcription/voice_transcription_contract: passed score=1.0 duration_ms=1.36
