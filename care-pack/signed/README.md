# Signed Draft Rule Artifacts

These `.aion` files are signed draft artifacts for the Care Compass MVP.
They prove the current YAML payloads have not been changed since signing.
They do not imply clinical, legal, compliance, or production approval.

## Registry

- Registry: `registry.json`
- Author ID: `81001`
- Key ID used for draft signing: `81001`

## Verification

Verify one file:

```bash
aion verify scope_of_practice.aion --registry registry.json
```

Verify the whole directory from the project root:

```bash
aion verify care-pack/signed/scope_of_practice.aion --registry care-pack/signed/registry.json
aion verify care-pack/signed/privacy_policy.aion --registry care-pack/signed/registry.json
aion verify care-pack/signed/escalation_policy.aion --registry care-pack/signed/registry.json
aion verify care-pack/signed/navigation_rules.aion --registry care-pack/signed/registry.json
aion verify care-pack/signed/trusted_health_sources.aion --registry care-pack/signed/registry.json
aion verify care-pack/signed/resource_directory_seed.aion --registry care-pack/signed/registry.json
```

## Current File IDs

- `scope_of_practice.aion`: `0x258ab3c36b615667`, version 2
- `privacy_policy.aion`: `0xc233703f1bb3fca2`, version 1
- `escalation_policy.aion`: `0x79d77556bc29d605`, version 1
- `navigation_rules.aion`: `0x3b030c30ccf9f718`, version 1
- `trusted_health_sources.aion`: `0x81440d91185c901a`, version 1
- `resource_directory_seed.aion`: `0x680d0cabe33c1503`, version 1
