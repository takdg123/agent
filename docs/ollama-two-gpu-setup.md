# Let Ollama use both A6000s

## The problem

The packaged unit pins Ollama to one GPU:

```
$ systemctl cat ollama | grep CUDA
Environment="CUDA_VISIBLE_DEVICES=0"
```

AstroSage-70B (42.5 GB) and Qwen2.5-32B (21.7 GB) total 64 GB, which cannot
coexist in one 48 GB card. So Ollama evicts one to load the other, and the daily
pipeline pays that cost on **every paper**. GPU 1 sits idle the whole time:

```
$ nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
0, 40783 MiB
1, 18 MiB          <-- unused
2, 259 MiB         <-- T400, not used for inference
```

Measured cost: the first AstroSage call in a run takes ~71 s, the second on the
warm model ~38 s. The ~33 s difference is the load. Two loads per paper is roughly
7 minutes of a 40 minute run.

## The fix

A systemd drop-in, so the packaged unit is not edited directly. Drop-ins are
applied after the main unit, so these values win.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d

sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null <<'EOF'
[Service]
# Both A6000s: AstroSage (42.5GB) lands on one card, Qwen (21.7GB) on the other.
Environment="CUDA_VISIBLE_DEVICES=0,1"
# Keep both resident instead of evicting one to load the other.
Environment="OLLAMA_MAX_LOADED_MODELS=2"
# The default 5m can evict a model during a PDF fetch between papers.
Environment="OLLAMA_KEEP_ALIVE=30m"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Restarting aborts any in-flight generation, so do it when no run is active. The
9am cron is the only scheduled user.

## Verify

Confirm the override took effect:

```bash
systemctl show ollama --property=Environment | tr ' ' '\n' | grep -i -E 'cuda|ollama'
```

Expect `CUDA_VISIBLE_DEVICES=0,1`, `OLLAMA_MAX_LOADED_MODELS=2`,
`OLLAMA_KEEP_ALIVE=30m`.

Then load both models and check they stay resident together:

```bash
curl -s localhost:11434/api/generate -d \
  '{"model":"hf.co/mradermacher/AstroSage-70B-i1-GGUF:Q4_K_M","prompt":"hi","stream":false}' >/dev/null
curl -s localhost:11434/api/generate -d \
  '{"model":"qwen2.5:32b","prompt":"hi","stream":false}' >/dev/null

curl -s localhost:11434/api/ps | python3 -c \
  'import sys,json; [print(m["name"], round(m["size"]/1e9,1),"GB") for m in json.load(sys.stdin)["models"]]'
```

Success looks like **both** models listed. If only one appears, the override did
not apply or Ollama chose to spread a single model across both cards; check
`nvidia-smi` to see the placement.

```bash
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
```

Expect roughly 42 GB on one card and 22 GB on the other.

## If it does not help

Ollama may place both models on the same card and still evict. In that case add:

```
Environment="OLLAMA_SCHED_SPREAD=0"
```

which tells the scheduler to keep each model on a single GPU rather than
splitting one across both.

## Rolling back

```bash
sudo rm /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

## Note on the code path

None of this is required for correctness. The pipeline works on one GPU; it just
reloads models more often. The code changes in `map_bounded` and the coordinator's
per-model locking already assume that two *different* models may be resident, and
degrade safely to serialised execution when they are not.
