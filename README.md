# jev-games

[I had Jev play a bunch of games](https://arsh.zip/posts/jev-games/)



## What's in the post, and where it lives here

| Game in the post | Generator / cases |
|---|---|
| Encoding games: plain, Base64, ROT13, reversed, Morse (color + sentiment ×12 records) | `run_experiments.py` → `enc-*` |
| Contradictory info (Base64 slot 11: “violet and blue”) | `run_experiments.py` → `enc-base64-11` |
| Belief tracking (8 stories × 2 questions) | `belief-*` |
| Python tracing (12 snippets) | `code-*` |
| Counting ones (12 strings) | `parity-*` |
| Ignoring untrusted notes (24 requests) | `injection-*` |
| Recognizing missing information (6 cases, **no prompt mentions unknown**) | `missing-*` |

## Run it

Python 3.10+, standard library only.

```sh
export TYPESAFE_API_KEY=...   # your key; API calls incur usage
python3 run_experiments.py    # resumes by case id; move results.jsonl and manifest.json aside for a fresh run
python3 validate_truth.py     # audit the answer keys locally
```

`cases.json` holds the exact API requests plus local-only expected answers and decoded references; `results.jsonl` holds the unmodified parsed responses; `manifest.json` pins model, counts, protocol, and the suite hash.
