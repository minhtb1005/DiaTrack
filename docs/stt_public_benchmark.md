# Public STT benchmark — VietMed pilot

## Snapshot

- Dataset: `leduckhai/VietMed`, test split, revision `f302146de79c5cbd6a7d14400fefa2c8cfda7738`.
- Sampling: 15 rows, exactly 5 North, 5 Central and 5 South using VietMed accent labels; all compared models use the same reference and speaker hashes.
- Runtime: CPU, local Transformers pipeline; results are a model-screening pilot, not a DiaTrack safety gate.
- Reproduce after `pip install -e ".[local,evaluation]"`:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_stt_public.py --model vinai/PhoWhisper-tiny --per-region 5 --output test-results\stt-public-phowhisper-tiny.json
```

## Results

| Model | WER | CER | Mean latency | North WER | Central WER | South WER |
|---|---:|---:|---:|---:|---:|---:|
| `openai/whisper-tiny` | 432.31% | 445.06% | 13.53s | 493.63% | 690.34% | 112.96% |
| `vinai/PhoWhisper-tiny` | 18.63% | 14.00% | 4.64s | 12.78% | 32.32% | 10.80% |
| `vinai/PhoWhisper-small` | 14.00% | 11.05% | 18.13s | 7.90% | 24.65% | 9.45% |

WER above 100% is possible when hallucinated output contains more inserted words than the reference. PhoWhisper Small improves mean WER by 4.63 percentage points over PhoWhisper Tiny but is about 3.9× slower on this CPU. Central remains the weakest region for both.

## DiaTrack synthetic safety probe

On the existing 45 Piper samples (30 clean + 15 at 15 dB noise), PhoWhisper Tiny reached WER 28.94%, CER 16.48%, utterance task accuracy 40.0% and individual semantic-check accuracy 53.62%; mean latency 2.84s, p95 4.63s. Under the confirmation guardrail, it still missed 23 of 33 expected emergency cases in this synthetic probe. Piper emitted missing-phoneme warnings for some letter/number strings, so this probe cannot replace human gold audio.

## Decision

- Reject `openai/whisper-tiny` for Vietnamese runtime.
- Keep `vinai/PhoWhisper-tiny` as the current candidate for human-gold evaluation: materially faster than Small and much better than the baseline.
- Do not enable it in runtime yet. PhoWhisper Small's modest public-WER improvement does not justify its CPU latency before a target safety benchmark shows a decisive recall benefit.
- Next gate remains the consented human DiaTrack corpus in `docs/stt_gold_collection.md`; evaluate exact numeric accuracy, red-flag recall and false alerts there before any default switch.
