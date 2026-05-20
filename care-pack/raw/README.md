# Raw Data Intake

Raw files live here only as staging material. They should not be consumed
directly by the assistant.

## Accepted Raw Source Classes

- Official federal, state, county, or city health and benefits pages.
- Downloadable public datasets from official government sources.
- Public resource directories from 211 providers or local health agencies.
- Human-reviewed community organization lists with clear ownership.
- Trusted patient education APIs or pages, such as MedlinePlus.

## Normalization Rules

Before raw data can become part of a signed `.aion` ruleset:

1. Keep only the minimum fields needed for navigation.
2. Remove private, sensitive, tracking, or analytics fields.
3. Preserve source URL, retrieval date, license or terms note, and reviewer.
4. Mark stale or unverified records as inactive instead of deleting silently.
5. Never create fake resources to fill gaps.
6. For eligibility or benefits content, link users to official application
   or assister channels instead of claiming eligibility.

## Suggested Raw Files

- `hrsa_health_center_sites.csv`
- `samhsa_findtreatment_links.json`
- `local_211_resources.csv`
- `state_medicaid_navigation.md`
- `county_health_department_resources.md`
- `medlineplus_source_policy.md`

