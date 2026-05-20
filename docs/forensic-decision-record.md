# Forensic Decision Record

Care Compass should not rely on the model to explain why it behaved a
certain way. The forensic record is produced outside the model path by the
policy gate and verifier.

The compliance question is:

> Given a user request and a model response, can we prove which signed rules
> were active, which rule triggered, whether the model was allowed to run, and
> which exact model output was produced?

The answer is a per-decision NDJSON record with stable hashes and bounded
reason codes.

## Record Shape

Each line uses schema `care_compass.forensic_decision.v1` and includes:

- `decision_id`: unique ID for the decision event.
- `created_at`: UTC timestamp.
- `request_evidence.sha256`: request fingerprint.
- `aion_evidence.registry_sha256`: registry fingerprint.
- `aion_evidence.artifacts[]`: one entry per signed `.aion` file, including
  file ID, version count, `.aion` file hash, payload hash, and verification
  booleans.
- `gate_evidence.selected_rule`: the rule that controlled the outcome.
- `gate_evidence.candidate_matches`: lower-priority or competing matches.
- `model_evidence.called`: whether the model was allowed to run.
- `model_evidence.request_payload_sha256`: fingerprint of the Ollama request
  payload, including the verified policy context.
- `model_evidence.policy_context_sha256`: fingerprint of the policy excerpts
  shown to the model.
- `model_evidence.output_sha256`: fingerprint of the exact model output.
- `final_decision`: decision, reason, selected rule ID, selected policy
  artifact, and whether the model was allowed.

Raw user text and raw model output are not logged by default.

## Example: Escalated Before Model

An unsafe request can trigger multiple rules. The selected rule is the highest
priority match, while other matches remain visible for audit:

```json
{
  "final_decision": {
    "decision": "escalate",
    "reason": "emergency_medical_signal",
    "selected_rule_id": "immediate_medical_emergency",
    "selected_policy_artifact": "escalation_policy.aion",
    "model_allowed": false
  },
  "gate_evidence": {
    "candidate_matches": [
      {
        "rule_id": "immediate_medical_emergency",
        "policy_artifact": "escalation_policy.aion",
        "reason": "emergency_medical_signal",
        "priority": 100,
        "matched_signals": ["chest pain"]
      },
      {
        "rule_id": "possible_poisoning",
        "policy_artifact": "escalation_policy.aion",
        "reason": "poisoning_signal",
        "priority": 95,
        "matched_signals": ["extra pills"]
      },
      {
        "rule_id": "medication_instruction",
        "policy_artifact": "scope_of_practice.aion",
        "reason": "medication_instruction_blocked",
        "priority": 80,
        "matched_signals": ["change my medication", "dose"]
      }
    ]
  },
  "model_evidence": {
    "called": false
  }
}
```

This is the key compliance property: the model cannot invent a softer
explanation because it was never invoked.

## Example: Allowed Navigation

For an allowed navigation request, the record proves:

- all required `.aion` policies verified,
- `navigation_rules.aion` selected the allowed rule path,
- the model request payload was fingerprinted,
- the model output was fingerprinted,
- the model output parsed as JSON.

The model can still include a user-facing `policy_basis` field, but that field
is not the source of truth. Compliance should treat `gate_evidence` and
`aion_evidence` as authoritative.

## Run

```bash
python3 scripts/validate_aion_ollama.py \
  --model gemma4:e4b \
  --decision-log /tmp/care-compass-forensic.ndjson
```

Optional debugging flags:

```bash
# Prints full records to stdout.
python3 scripts/validate_aion_ollama.py --print-forensic-records

# Adds redacted previews to the forensic log.
python3 scripts/validate_aion_ollama.py --include-redacted-preview

# For local demo only. Do not use with real users or PHI.
python3 scripts/validate_aion_ollama.py --include-raw-in-log
```

## Compliance Story

The record separates three authorities:

- Aion proves which policy bytes were signed and verified.
- The deterministic gate proves which rule path controlled the decision.
- Ollama/Gemma produces helpful language only after the gate allows it.

That gives a reviewer a reproducible forensic fingerprint without trusting the
model to explain itself.

