# Contributions to this fork

This is @carmanspb's integration fork of [K2 OpenKlipper](https://github.com/grant0013/K2-OpenKlipper).
Only @carmanspb maintains and changes this repository. External contributions
are not accepted here; pull request creation is restricted to collaborators,
and branch changes are restricted to the owner.

- For K2 OpenKlipper changes, contribute to the [upstream project](https://github.com/grant0013/K2-OpenKlipper/blob/main/CONTRIBUTING.md).
- For the native touchscreen, contribute through a pull request to
  [K2 OpenKlipper Touchscreen](https://github.com/carmanspb/K2-OpenKlipper-Touchscreen/blob/main/CONTRIBUTING.md).

The repository remains public for inspection and use under its existing license.

## Code review

All changes to `main` go through pull requests, including maintainer changes.
Codex review provides additional feedback; review its findings before merging.
Automated review does not replace the repository owner’s merge decision.

## PR package preparation

The integration follows the native touchscreen repository's preparation flow.
`Request PR package validation` reads PR metadata and dispatches the workflow
from `main`; it never checks out PR code. Source changes and advances to `main`
queue validation, while title/body edits do not.

`Prepare and validate PR package` merges the current `main` tip into the PR,
resolves only generated ARM-package conflicts, builds the desktop simulator,
runs firmware and touchscreen tests, and rebuilds stale ARM packages. Source
conflicts stop for manual resolution. It also builds and checks the installable
`k2-openklipper-host.zip`, available as a run artifact.

The build job runs PR code with read-only permissions on `ubuntu-24.04`. A
separate publisher uses tooling from the trusted workflow checkout, verifies the
artifact's checksums, source fingerprints and commit ancestry, recreates the
exact tested merge, and updates only the same repository's PR branch. It refuses
to publish if either the PR head or `main` moved. Bot commits explicitly dispatch
another run. Only a successful run requiring no further source/package update
reports `integration/package` success on that exact head. Fork PRs receive no
write access and must commit their own source/package updates.

During initial installation, the workflow runs a read-only bootstrap build on
this PR. Publication and status-reporting jobs require a dispatch from the
workflow on `main`. After installation, PR-triggered bootstrap builds are skipped
and the trusted dispatcher owns validation.

Repository setup after merging these workflows:

- Require the `integration/package` status on `main` with up-to-date branches.
- Permit the GitHub Actions app to update PR branches under the owner-only branch
  ruleset. Keep `main` protected by its separate PR requirement; do not grant the
  app a bypass of that requirement.
- Retain read-only default Actions permissions and disabled review approval.
  The publisher requests only the write permissions needed for its job.

These workflows do not approve or merge PRs, publish releases, deploy to a printer,
or push directly to `main`. The repository owner's merge decision remains final.
