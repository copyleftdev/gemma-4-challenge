# Care Compass

[![Tip my tokens](https://tokentip.to/badge/copyleftdev.svg?logo=1)](https://tokentip.to/@copyleftdev)

Care Compass is a local-first community health navigation prototype for the
Gemma 4 Challenge. Gemma 4 handles language-heavy assistance; Aion Context
holds the signed source of truth for policy, resource, privacy, escalation,
and navigation rules.

The competition story is the synergy: Gemma 4 makes the system useful for real
community-care language work, while Aion Context makes the decision path
defensible for healthcare compliance review. See
[docs/competition-positioning.md](docs/competition-positioning.md),
[docs/architecture-diagrams.md](docs/architecture-diagrams.md), and
[docs/demo-script.md](docs/demo-script.md). PNG article embeds are collected in
[docs/devto-assets.md](docs/devto-assets.md), and the DEV submission draft is
in [docs/devto-submission.md](docs/devto-submission.md).

## Exposure Boundary

These files are safe and useful to expose in the project repository:

- `care-pack/normalized/*.yaml`: human-reviewable draft rules.
- `care-pack/signed/*.aion`: signed runtime policy artifacts.
- `care-pack/signed/registry.json`: public verifying-key registry for the
  draft artifacts.
- `care-pack/raw/README.md`: intake rules for future raw data.
- `care_compass/`: audited runtime code for Aion verification, rule gating,
  Ollama calls, and decision records.
- `scripts/validate_aion_ollama.py`: local validation CLI.

Do not expose:

- Aion private signing keys.
- Real patient data, PHI, intake transcripts, referral drafts, or logs.
- Raw local datasets that contain private, restricted, or unreviewed data.
- Secrets, API keys, model-provider tokens, or analytics identifiers.

Runtime trust should come from the signed `.aion` files, not from the model
and not from unsigned YAML. The YAML files are for review and regeneration;
the app should verify the `.aion` files before answering.

## Code Structure

The Python runtime is organized around single-purpose modules:

- `care_compass/aion.py`: verifies signed `.aion` artifacts and extracts their
  payloads.
- `care_compass/rules.py`: deterministic pre-model policy gate.
- `care_compass/model.py`: local Ollama/Gemma integration.
- `care_compass/records.py`: redaction, hashes, and forensic decision records.
- `care_compass/service.py`: orchestration used by the HTTP API.
- `app/server.py`: thin standard-library HTTP wrapper.
- `scripts/*.py`: CLI entry points for validation, red-team, and tamper checks.

This keeps the competition demo inspectable: policy trust, model execution, and
evidence generation are separate code paths instead of one monolithic script.

## Local Validation

Default Ollama model:

```bash
ollama pull gemma4:e4b
```

`gemma4:e4b` is the default because it gives the demo more headroom for
policy-grounded answers. For the lowest-footprint challenge profile, use
`gemma4:e2b` instead:

```bash
ollama pull gemma4:e2b
CARE_COMPASS_MODEL=gemma4:e2b python3 app/server.py
```

Run the Aion + Ollama smoke test:

```bash
python3 scripts/validate_aion_ollama.py --model gemma4:e4b
```

## Interactive Console

Prerequisites:

- Docker Engine or Docker Desktop with Docker Compose v2.
- `curl` and `awk` on the host for readiness and port checks.
- At least 20 GB free disk space for first-run image/model downloads.
- At least 16 GB system RAM recommended.
- NVIDIA GPU, current NVIDIA driver, and NVIDIA Container Toolkit recommended
  for fast local inference. CPU fallback works but is slower.

Run the preflight:

```bash
make doctor
```

One-command Docker demo:

```bash
make demo
```

This runs the same preflight, starts the demo with Docker Compose, pulls the
configured Gemma model, waits for the API to become ready, and opens the browser at
`http://127.0.0.1:8080`. If that port is busy, the launcher automatically uses
the next available port and prints the URL. The default demo model is
`gemma4:e2b` for a smaller local footprint. Use a larger model when you want
the quality profile:

```bash
make demo CARE_COMPASS_MODEL=gemma4:e4b
```

The default launcher starts Ollama through Docker so the demo is self-contained.
On NVIDIA hosts, it also requests GPU access for the Ollama container. Disable
that explicitly with:

```bash
make demo OLLAMA_GPU=0
```

Skip preflight only when automating a known-good environment:

```bash
make demo DEMO_PREFLIGHT=0
```

If you already run an externally reachable Ollama daemon and want to use it
instead, run:

```bash
make demo OLLAMA_MODE=host
```

Run the local forensic console:

```bash
python3 app/server.py
```

Then open:

```text
http://127.0.0.1:8080
```

The console exposes the Aion verification ledger, selected rule path,
candidate matches, Gemma output, and the full forensic decision record.

Docker build and run:

```bash
docker compose up -d ollama
docker compose exec -T ollama ollama pull gemma4:e2b
docker compose up --build care-compass
```

`make demo` wraps these steps, waits for readiness, handles port conflicts, and
opens the browser.

The validation harness:

1. Verifies every signed `.aion` rule file against
   `care-pack/signed/registry.json`.
2. Extracts the current signed rule payloads from the `.aion` files.
3. Applies a deterministic pre-model gate for unsafe requests.
4. Sends an allowed community-navigation request to local Ollama.
5. Confirms Gemma 4 can generate a response grounded in verified policy
   excerpts.

Write forensic decision records:

```bash
python3 scripts/validate_aion_ollama.py \
  --model gemma4:e4b \
  --decision-log /tmp/care-compass-forensic.ndjson
```

The forensic log records signed policy fingerprints, selected rule IDs,
candidate rule matches, model-call status, prompt/context hashes, and model
output hashes. It does not store raw user text or raw model output by default.
See [docs/forensic-decision-record.md](docs/forensic-decision-record.md).

## Red-Team Harness

Fast gate-only run, no GPU:

```bash
python3 scripts/red_team_harness.py \
  --mode gate \
  --report /tmp/care-compass-red-team-gate.json \
  --decision-log /tmp/care-compass-red-team-gate.ndjson
```

Budgeted sampled model run, serial, capped at 6 Gemma calls:

```bash
python3 scripts/red_team_harness.py \
  --mode sampled-model \
  --model gemma4:e4b \
  --max-model-cases 6 \
  --model-delay-seconds 1 \
  --report /tmp/care-compass-red-team-sampled.json \
  --decision-log /tmp/care-compass-red-team-sampled.ndjson
```

The sampled report includes model latency and Ollama token-throughput metrics
so small-model runs can be compared without changing the safety gate.

Tamper-detection run, no GPU:

```bash
python3 scripts/tamper_check.py
```

The adversarial corpus lives at
[tests/adversarial_cases.jsonl](tests/adversarial_cases.jsonl). It covers
emergency escalation, self-harm, harm to others, poisoning, personal safety,
medication advice, diagnosis, lab/imaging interpretation, eligibility,
privacy-sensitive identifiers, unverified resources, jailbreak attempts,
multi-intent priority, and allowed navigation.

## Current Safety Scope

Allowed:

- Community health resource navigation.
- Patient education linkouts.
- Appointment-preparation questions.
- Plain-language and translation support.

Blocked:

- Diagnosis.
- Treatment recommendations.
- Medication start, stop, change, or dosing instructions.
- Benefits eligibility determinations.
- Unverified resource invention.
- Sensitive identifier collection.

Escalated before normal navigation:

- Emergency medical signals.
- Suicide or self-harm signals.
- Harm-to-others signals.
- Possible poisoning.
- Immediate personal safety concerns.
