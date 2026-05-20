# Care Compass Rule Pack

This directory is the source-of-truth pack for the Care Compass demo:
a local-first community health navigation assistant powered by Gemma and
governed by Aion Context.

The model may interpret user needs, rewrite text in plain language, and
draft navigation-oriented next steps. It must not be the source of truth
for policy, safety, eligibility, or resource authority. Those decisions
come from the normalized rule files in `normalized/`, then get signed into
`.aion` files under `signed/`.

## Files

- `normalized/manifest.yaml` describes the pack, sources, and intended
  signing targets.
- `normalized/scope_of_practice.yaml` defines what the assistant may,
  must, and must not do.
- `normalized/privacy_policy.yaml` defines data minimization and logging
  rules.
- `normalized/escalation_policy.yaml` defines emergency and crisis
  routing behavior.
- `normalized/navigation_rules.yaml` defines allowed resource and benefits
  navigation behavior.
- `normalized/trusted_health_sources.yaml` defines allowed health
  education sources and attribution rules.
- `normalized/resource_directory_seed.yaml` contains initial national
  resource entries for the MVP.
- `raw/README.md` records how raw datasets should be staged before
  normalization.

## Signing Intent

Each normalized YAML file should be signed independently with Aion Context:

```bash
aion init signed/scope_of_practice.aion --author <AUTHOR_ID> --key <KEY_ID> --rules normalized/scope_of_practice.yaml --no-encryption
aion init signed/privacy_policy.aion --author <AUTHOR_ID> --key <KEY_ID> --rules normalized/privacy_policy.yaml --no-encryption
aion init signed/escalation_policy.aion --author <AUTHOR_ID> --key <KEY_ID> --rules normalized/escalation_policy.yaml --no-encryption
aion init signed/navigation_rules.aion --author <AUTHOR_ID> --key <KEY_ID> --rules normalized/navigation_rules.yaml --no-encryption
aion init signed/trusted_health_sources.aion --author <AUTHOR_ID> --key <KEY_ID> --rules normalized/trusted_health_sources.yaml --no-encryption
aion init signed/resource_directory_seed.aion --author <AUTHOR_ID> --key <KEY_ID> --rules normalized/resource_directory_seed.yaml --no-encryption
```

The current draft artifacts in `signed/` were signed with local demo
author/key `81001` and verify against `signed/registry.json`.

For the demo gate, the app should verify all required `.aion` files before
answering. If any required file fails verification, the assistant should
refuse normal navigation and surface a bounded refusal reason.

## Safety Position

This pack is for community navigation and education linkout support. It is
not a clinical decision support system, diagnostic tool, treatment planner,
benefits eligibility engine, HIPAA compliance certification, or emergency
service.
