# Project Rules

## Project purpose

This repository develops an early-warning signal for small-business closure risk using open data from the AI·Data Problem Solving Bank. The work is for the analysis-tool track of the 2026 Data+AI Innovation Challenge. The intended outputs are a reproducible problem definition and analysis workflow, a data recipe, validated risk indicators or a scoring model, interpretable visualizations, and the final application package due on 2026-10-22.

## Project scope and completion

- Keep the analysis focused on the Problem Solving Bank analysis-tool track; do not introduce work for the mutually exclusive data-recipe proposal track.
- Treat the Notion project page as the planning source and the Linear project `문제해결은행 소상공인 폐업위험 2026` as the execution source.
- Link implementation work to the relevant Linear issue in the `COD-189` through `COD-207` plan, or let the feature-branch automation create the appropriate mirrored issue pair.
- Consider the project complete only when the data recipe, Work Studio analysis result, application materials, validation notes, and reproducible repository artifacts are ready for submission.
- Do not commit credentials, personal data, restricted competition data, or source data whose license does not permit redistribution. Record provenance and usage conditions for every external dataset.
- Resolve and document the analysis-tool track fit before model implementation; the small-business closure topic must be framed and confirmed as a social-issue use case rather than assumed eligible.
- Disclose the use and scope of generative AI in competition deliverables, as required by the official rules.

## PR & issue policy

Every PR into `develop` is gated by CI (`.github/workflows/pr-policy.yml`) that requires a mirrored Linear/GitHub issue pair. The normal path is automated — do not do the old manual dance of pre-creating a Linear issue, then a GitHub issue, then baking the id into the branch name; that's exactly the flow that used to get skipped or done out of order:

1. Create a branch named `feat/<slug>` (no id prefix needed) and push it to `origin`.
2. `.github/workflows/prepare-feature-pr.yml` finds or creates a Linear issue in team `COD` (project set by the `LINEAR_PROJECT_SLUG`/`LINEAR_PROJECT_NAME` repo variables — see README setup checklist), finds or creates the matching GitHub mirror issue, and opens a Draft PR into `develop` with both closing references already filled in.
3. `.github/workflows/pr-policy.yml` only validates the branch flow and issue pair on every PR event — it never creates or edits anything.
4. `main` only accepts PRs from `develop`. If this project cuts versioned releases, uncomment `validate-release` in `pr-policy.yml` and adapt it (see `codingnanyong/busan-competition-2026` for a working example); otherwise leave `main` PRs release-gate-free.

Automation uses the `LINEAR_API_KEY` and `GH_PAT` repo secrets. `GH_PAT` must be a fine-grained PAT (not the default `GITHUB_TOKEN`) with Contents:read and Issues/Pull requests:write — edits made with `GITHUB_TOKEN` don't retrigger workflow runs (GitHub's anti-recursion rule), so `pr-policy.yml` would never re-check a PR the automation just fixed up. Provisioning is keyed by `repository:branch`, so rerunning `Prepare feature PR` (or pushing again) after a partial failure reuses whatever Linear/GitHub records already exist instead of duplicating them. A branch named `feat/cod-<n>-<slug>` reuses that existing Linear issue if it belongs to the configured team/project.

**Manual fallback** (if `GH_PAT`/`LINEAR_API_KEY` are missing or expired): create the Linear issue yourself, create an open GitHub issue whose title starts with the same `COD-<n>`, then open the PR with both `Closes COD-<n>` and `Closes #<n>` in the body. Don't create a second issue pair for a branch the automation already provisioned.

On merge into `develop`, CI auto-closes the mirrored GitHub issue; Linear's native GitHub integration then auto-transitions the Linear issue to Done. No manual status update needed after merge.

## Editing constraints

- Do not publish, upload, create a pull request, merge branches, or message external services without explicit user authorization (opening a PR as part of the normal Linear/GitHub flow above is fine; merging and any external-facing action still needs a go-ahead).
- Keep unrelated user changes intact.
- At handoff, report the changed files, any generated assets, and remaining review items.

## Documentation conventions

- Write user-facing project documentation in Korean; use English where required by tools, APIs, or source material.
- Distinguish measured facts from assumptions and proposed proxy indicators.
- Record dataset source, reference date, geographic and industry granularity, license, and known limitations.
- Keep dates in `YYYY-MM-DD` format in machine-readable files and include the timezone when time-of-day matters.
