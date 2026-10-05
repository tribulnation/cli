# Releases

Merging a pull request from `release` or `release/*` into `main` publishes the
version in `pyproject.toml`. The branch must belong to this repository. Closing
without merging, ordinary feature merges, and direct pushes do not publish.

## One-time trusted publisher setup

For the initial release, add a pending publisher on
[PyPI's publishing page](https://pypi.org/manage/account/publishing/):

| Field | Value |
| --- | --- |
| PyPI project name | `tribulnation-cli` |
| Owner | `tribulnation` |
| Repository | `cli` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

The workflow uses the GitHub environment `pypi` and requests an OIDC identity
only in its publishing job. No PyPI token or password is required. Configure
the pending publisher before merging the first release PR.

## Cut a release

1. Branch from current `main` as `release` or `release/<version>`.
2. Set a new normalized version in `pyproject.toml` and update `CHANGELOG.md`.
   The first release uses the existing `0.1.0`; subsequent releases bump it.
3. Open a PR into `main` and wait for checks to pass.
4. Merge the PR. The workflow checks out its exact merge commit, runs tests
   and lint, builds the sdist and wheel, validates their metadata, and tests
   the installed wheel in a clean environment.
5. The publishing job uploads those artifacts through PyPI trusted publishing.
   After successful publication, it creates `v<version>` and a GitHub release
   pointing at that same merge commit.

Only the build job executes package code. It has no publishing or repository-write
permission; the publish job only downloads and uploads its artifacts.

## Recover a failed release

Fix the cause before retrying. If trusted publishing was not configured correctly,
correct it and rerun the failed jobs. If PyPI publication succeeded but GitHub
release creation failed, rerun only the failed GitHub release job. PyPI versions
are immutable: do not delete tags or reuse a published version for changed code.
For a partial upload, inspect which files PyPI accepted before attempting recovery.

GitHub Actions serializes release workflows and never cancels a release to start
a newer one. Existing version tags fail validation rather than being overwritten.
