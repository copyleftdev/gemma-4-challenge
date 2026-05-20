# Gemma 4 Challenge Positioning

Care Compass is a Gemma 4 Challenge project, so the submission must make the
Gemma role obvious and meaningful. Aion Context is the differentiator, but it
should not make the entry look like a generic policy-engine demo.

## Submission Thesis

Healthcare AI needs more than helpful answers. It needs defensible answers.

Care Compass uses Gemma 4 for local, privacy-preserving language assistance in
community health navigation, then uses Aion Context as an external signed
policy gate that produces forensic evidence for every decision.

## What Gemma 4 Does

Gemma 4 is responsible for the human-language work:

- understanding messy community-care requests,
- converting needs into plain-language next steps,
- generating non-clinical questions for clinics or case managers,
- adapting output for Spanish/language-access needs,
- producing structured JSON that the UI can inspect and display.

Gemma is intentionally not the source of truth for safety, eligibility,
resource authority, or clinical scope.

## What Aion Context Does

Aion Context is the trust and audit layer:

- verifies signed policy files before each decision,
- selects the governing rule path,
- records policy file IDs, versions, hashes, and verification status,
- blocks or escalates unsafe requests before Gemma is called,
- fingerprints the exact model request and response when Gemma is allowed.

## Why The Pair Matters

The project is not “a chatbot with disclaimers.” It is a governed AI workflow:

1. A user submits a healthcare navigation request.
2. Aion verifies signed policy artifacts.
3. The deterministic gate decides whether Gemma may run.
4. Gemma produces helpful navigation output only for allowed requests.
5. The system emits a forensic decision record for compliance review.

This gives judges a concrete answer to: “How do we know why the AI made this
decision?”

## Demo Story

Show three moments:

1. **Allowed navigation**: uninsured discharge follow-up, Spanish preference,
   low-cost clinic needs. Gemma helps with resource navigation and questions.
2. **Unsafe escalation**: chest pain plus too many pills plus jailbreak
   language. Aion records multiple candidate matches and blocks Gemma.
3. **Tamper proof**: a changed `.aion` policy fails verification, proving the
   model cannot silently operate under altered governance.

## Judging Hooks

- **Use of Gemma 4**: local Gemma 4 E4B powers the language and navigation
  output after the signed gate allows it.
- **Implementation quality**: signed Aion artifacts, forensic records,
  adversarial harness, Docker-ready app, and reproducible local validation.
- **Originality**: external forensic governance for healthcare AI decisions,
  rather than trusting model self-explanations.
- **User experience**: compliance-first console showing signed policy evidence,
  selected rule path, model output, and immutable fingerprints.

