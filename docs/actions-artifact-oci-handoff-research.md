# Cross-repository RPM hand-off: Actions artifacts versus GHCR OCI

Research date: 2026-09-05.

## Decision

Use a minimal OCI image on GHCR as the durable hand-off from
`projectbluefin/utah-packages` to `projectbluefin/bluefin` and
`projectbluefin/bluefin-lts`. Put the complete RPM input directory in the
image (currently `/repository`), publish a human-friendly discovery tag, and
make downstream Containerfiles consume an immutable digest:

```dockerfile
ARG UTAH_PACKAGES_IMAGE=ghcr.io/projectbluefin/utah-packages
ARG UTAH_PACKAGES_DIGEST
FROM ${UTAH_PACKAGES_IMAGE}@${UTAH_PACKAGES_DIGEST} AS utah-packages

# Later, in the image build:
COPY --from=utah-packages /repository /tmp/utah-packages
```

The artifact action remains the appropriate mechanism inside the Utah
workflow: it carries matrix/stage outputs into the publishing job. It should
not be the consumer-facing interface. The existing Utah publish job already
constructs exactly this kind of scratch OCI image, pushes it to GHCR, records
the digest, signs the digest, and emits a `FROM ...@digest` / `COPY --from`
example. [Utah publish workflow][utah-oci].

## Actions artifacts

### Normal scope and retention

GitHub describes workflow artifacts as a way to share data between jobs in a
workflow and retain it after that workflow completes. The documented
same-workflow pattern is an upload in one job and a download in a later job.
[GitHub artifact concept][artifact-concept] [GitHub tutorial][artifact-tutorial]

The default retention is 90 days. It can be configured from 1 to 90 days for
public repositories, and from 1 to 400 days for private/internal
repositories; an organization or enterprise may impose a lower maximum.
Retention changes affect new artifacts only. The official upload action
enforces a one-day minimum and treats `0` as the repository default.
[GitHub retention policy][artifact-retention] [upload-artifact action][upload-action]

The current action documents a limit of 500 artifacts created by an individual
job. The service exposes each artifact's `size_in_bytes` in the REST API and
accounts artifact storage against the repository owner's Actions/Packages
allowance. GitHub's currently published documentation does **not** state a
separate per-artifact byte ceiling in the maintained action README or Actions
limits reference; therefore, capacity planning should use the storage quota
and the 500-artifacts-per-job limit, not rely on an unverified historical
per-file limit. [upload-artifact limitations][upload-limits] [artifact REST
schema][artifact-rest] [GitHub Actions billing][actions-billing]

### Cross-workflow and cross-repository access

**Yes: a Bluefin workflow can download an artifact from Utah.** It is not
limited to the producer workflow run, but it is an authenticated, explicit
lookup rather than a cross-repository transport automatically provided by
`upload-artifact`.

`actions/download-artifact@v4` documents these inputs:

* Without `github-token`, it downloads from the current repository and current
  workflow run.
* With `github-token`, `repository` selects `OWNER/REPO` and `run-id` selects
  the source workflow run. Its v4 README explicitly says a PAT with
  `actions:read` access to the target repository is needed for the
  cross-workflow/cross-repository example.

[download-artifact v4 metadata][download-v4-action]
[download-artifact v4 README][download-v4-readme]

For example, the consumer needs an authorized credential and the producer run
ID:

```yaml
- uses: actions/download-artifact@v4
  with:
    name: rpm-set
    github-token: ${{ secrets.UTAH_ARTIFACT_READ_TOKEN }}
    repository: projectbluefin/utah-packages
    run-id: ${{ inputs.utah_run_id }}
    path: /tmp/rpms
```

The REST API is also explicitly repository-addressed:
`GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts` lists artifacts
from a specific run, and
`GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip` returns a
one-minute redirect to its archive. Both require repository read access; for a
private repository, classic PATs need `repo` scope. `gh run download RUN_ID
--repo OWNER/REPO` is the GitHub CLI wrapper with the same explicit repository
selection. [Artifact REST API][artifact-rest] [GitHub CLI manual][gh-run-download]

The third-party `dawidd6/action-download-artifact` is a viable convenience
wrapper if the producer run ID is not known: it can search runs by workflow,
commit, branch, tag, or PR. It also documents that a token is required for a
different repository. That is extra third-party code and API-search behavior,
not capability absent from GitHub's native action: native v4 supports the
cross-repository case when an exact run ID is supplied. [dawidd6 README][dawidd6-readme]
[dawidd6 action metadata][dawidd6-action]

This makes Actions artifacts an operationally weaker dependency contract:
the downstream build needs a credential authorized for Utah, a durable way to
discover and pass the run ID, an artifact name/ID, and a build before the
retention deadline. Artifact upload v4 output is immutable and has an ID and
SHA-256 digest, but the artifact itself expires on the Actions lifecycle.
[upload-artifact README][upload-readme] [GitHub retention policy][artifact-retention]

## Actions cache is not a hand-off channel

`actions/cache` is for reducing repeated work. GitHub specifies cache lookup
and sharing in terms of the current/default/base branch and says that multiple
workflow runs can share a cache only for the **same repository and branch**.
It has no repository or run-ID input analogous to `download-artifact`; caches
are deliberately isolated by branch/tag scope. [GitHub cache restrictions][cache-scope]
[actions/cache README][cache-readme]

GitHub deletes entries not accessed for more than seven days. The default
aggregate cap is 10 GB per repository; when the cap is reached, it evicts by
oldest access. [GitHub cache limits][cache-limits]

Consequently a cache in `utah-packages` is not readable by `bluefin` or
`bluefin-lts` and should not be treated as an RPM publication mechanism. It
can still accelerate each repository's own builds, independently of this
handoff.

## OCI image as the hand-off

GHCR stores both Docker and OCI images. Public container packages can be
pulled anonymously; for a private package, a workflow can use a package grant
for its repository's `GITHUB_TOKEN` or a credential with `read:packages`.
[GHCR support and access][ghcr-docs] [GHCR package workflow access][ghcr-access]

The `COPY --from` pattern is valid with an external registry image:

* Docker's multi-stage documentation states that `COPY --from` accepts a local
  image name, a tag available locally or on a registry, or a tag ID; Docker
  pulls it if needed. Its documented example is
  `COPY --from=nginx:latest ...`. [Docker multi-stage docs][docker-external]
* Buildah builds Containerfiles using Dockerfile syntax. Its `--build-context`
  documentation says a `COPY --from=[name]` source resolves in this order:
  named build context, an earlier `AS` stage, then an image either local or in
  a remote registry. Its `buildah copy --from` manual likewise specifies that
  an image source is used as the root filesystem and can be pulled.
  [Buildah Containerfile source resolution][buildah-external]
  [Buildah copy source][buildah-copy]

Therefore both variants below are valid:

```dockerfile
# Explicit stage gives the source a stable local name.
FROM ghcr.io/projectbluefin/utah-packages@sha256:<digest> AS utah-packages
COPY --from=utah-packages /repository /tmp/utah-packages

# Docker's documented direct external-image form.
COPY --from=ghcr.io/projectbluefin/utah-packages@sha256:<digest> \
  /repository /tmp/utah-packages
```

Use the first form in Bluefin Containerfiles because it is clearer, permits
the digest to be passed as a build argument, and works naturally with
Buildah's named-stage mounts. It does not require `oras`: Utah already has
Podman on the hosted runner and uses `podman build`/`podman push`. `oras` is
useful only if a generic OCI artifact (rather than an image filesystem) is
desired. [Utah OCI publish commands][utah-oci]

### Versioning, integrity, caching, and cost

| Concern | OCI image | Cross-repository Actions artifact |
| --- | --- | --- |
| Immutable build selection | Pin `ghcr.io/projectbluefin/utah-packages@sha256:<digest>`; GHCR documents pull-by-digest specifically as the way to always use the same image. [GHCR digest pulls][ghcr-digest] | Record the producer run ID and immutable artifact ID/digest; the item still expires. [upload-artifact README][upload-readme] |
| Discovery/update flow | Publish a mutable tag such as `latest` or a source-SHA tag, then have a bot/dispatch open a downstream PR replacing the pinned digest. | Find a successful workflow run, then pass its ID and a credential to the downstream workflow. |
| Repeated build transfer | Registry layers are content-addressed and can be reused by the container engine/registry cache; downstream Dockerfile cache keys include the digest. | Each download retrieves and extracts the artifact archive; Actions cache cannot share the result cross-repository. [cache-scope][cache-scope] |
| Access control | Public is anonymous. Private packages can grant a consuming repository Actions access, allowing that workflow's `GITHUB_TOKEN`; otherwise use `read:packages` credentials. [GHCR docs][ghcr-docs] [GHCR access][ghcr-access] | A cross-repo read token/PAT must have access to the Utah repository. [download-artifact v4 README][download-v4-readme] |
| Cost | GitHub says public Packages use is free and Container Registry storage and bandwidth are currently free, subject to notice. [GitHub Packages billing][packages-billing] | Artifacts consume the Actions/Packages storage allowance and expire according to retention. [actions-billing][actions-billing] |
| Tooling | Build/push needs Podman, Buildah, or another OCI client; consuming is ordinary Containerfile syntax. | Uses built-in actions/`gh`, but needs producer-run discovery, a cross-repo credential, and retention management. |

Digest pinning is the important reliability boundary. A mutable tag is
convenient for discovering a new build, but a downstream Containerfile pinned
to the emitted digest reproducibly selects the exact Utah build. Utah already
signs that digest, so downstream policy can additionally verify the signature
before updating a pin. [Utah OCI publication and signing][utah-oci]

## Existing Project Bluefin practice

The requested repositories already use the two mechanisms in their natural
roles; no searched source downloads RPMs from Utah or another external
repository as an Actions artifact.

* `utah-packages` uploads `rpm-s*` artifacts from individual stage builds and
  downloads the `rpm-*` pattern into later jobs, then builds/pushes
  `ghcr.io/<owner>/utah-packages` containing `/repository`. This is
  intra-workflow artifact aggregation followed by OCI publication.
  [Utah artifact upload][utah-artifacts] [Utah artifact aggregation][utah-aggregation]
  [Utah OCI publish][utah-oci]
* Bluefin consumes `common` and `brew` as image stages, with the `common`
  image referred to by an image reference plus digest variables. It uses
  `gh run download ... --repo "${{ github.repository }}"` only to collect
  image-digest artifacts from a triggering workflow in the **same**
  repository, then promotes GHCR digest references to `:testing`.
  [Bluefin Containerfile][bluefin-containerfile]
  [Bluefin same-repository artifacts][bluefin-artifacts]
* Bluefin LTS consumes external `akmods` images, and `common`/`brew` image
  references, as Containerfile stages; Buildah bind-mounts RPM directories
  from the `akmods` stages into the image-building `RUN`. Its NVIDIA manifest
  workflow uses native `download-artifact` with a run ID for sibling
  same-repository workflows. [Bluefin LTS Containerfile][bluefin-lts-containerfile]
  [Bluefin LTS artifact fan-in][bluefin-lts-artifacts]
* `common` uploads one-day architecture digest artifacts and its later
  manifest job downloads them; it publishes and signs the multi-architecture
  image to GHCR. [Common artifact fan-in][common-artifacts]

This aligns the recommended Utah-to-Bluefin interface with the existing
cross-repository dependency pattern: GHCR content selected by immutable
digest, with Actions artifacts retained for short-lived workflow fan-in.

## Sources

[artifact-concept]: https://github.com/github/docs/blob/ec3629a841129ae28189d7bb2274a7b3d40c5095/content/actions/concepts/workflows-and-actions/workflow-artifacts.md#L13-L17
[artifact-tutorial]: https://docs.github.com/en/actions/tutorials/store-and-share-data#passing-data-between-jobs-in-a-workflow
[artifact-retention]: https://github.com/github/docs/blob/ec3629a841129ae28189d7bb2274a7b3d40c5095/data/reusables/actions/about-artifact-log-retention.md#L1-L12
[upload-action]: https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/action.yml#L20-L25
[upload-limits]: https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/README.md#L436-L441
[artifact-rest]: https://docs.github.com/en/rest/actions/artifacts#list-workflow-run-artifacts
[actions-billing]: https://github.com/github/docs/blob/ec3629a841129ae28189d7bb2274a7b3d40c5095/content/billing/concepts/product-billing/github-actions.md#L62-L72
[download-v4-action]: https://github.com/actions/download-artifact/blob/d3f86a106a0bac45b974a628896c90dbdf5c8093/action.yml#L23-L37
[download-v4-readme]: https://github.com/actions/download-artifact/blob/d3f86a106a0bac45b974a628896c90dbdf5c8093/README.md#L248-L260
[gh-run-download]: https://cli.github.com/manual/gh_run_download
[dawidd6-readme]: https://github.com/dawidd6/action-download-artifact/blob/7cb16e2f14150d35e4ba4c101c11a31a4c84f8a2/README.md#L1-L68
[dawidd6-action]: https://github.com/dawidd6/action-download-artifact/blob/7cb16e2f14150d35e4ba4c101c11a31a4c84f8a2/action.yml#L6-L71
[upload-readme]: https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/README.md#L281-L313
[cache-scope]: https://github.com/github/docs/blob/ec3629a841129ae28189d7bb2274a7b3d40c5095/content/actions/reference/workflows-and-actions/dependency-caching.md#L240-L250
[cache-readme]: https://github.com/actions/cache/blob/3edfce9056124e459a23f683a21433670d47daca/README.md#L111-L115
[cache-limits]: https://github.com/github/docs/blob/ec3629a841129ae28189d7bb2274a7b3d40c5095/content/actions/reference/workflows-and-actions/dependency-caching.md#L295-L303
[ghcr-docs]: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
[ghcr-access]: https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#ensuring-workflow-access-to-a-package
[docker-external]: https://github.com/docker/docs/blob/034d46977dac45d2a9493f2465b08108ac3cf87b/content/manuals/build/building/multi-stage.md#L111-L121
[buildah-external]: https://github.com/containers/buildah/blob/a9717254a3bb7e0bc5dc8096d9ab7228fad592d0/docs/buildah-build.1.md#L99-L121
[buildah-copy]: https://github.com/containers/buildah/blob/a9717254a3bb7e0bc5dc8096d9ab7228fad592d0/docs/buildah-copy.1.md#L68-L74
[ghcr-digest]: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#pull-by-digest
[packages-billing]: https://github.com/github/docs/blob/ec3629a841129ae28189d7bb2274a7b3d40c5095/content/billing/concepts/product-billing/github-packages.md#L22-L24
[utah-artifacts]: https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/rebuild-rpms.yml#L1259-L1277
[utah-aggregation]: https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/rebuild-rpms.yml#L1288-L1299
[utah-oci]: https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/rebuild-rpms.yml#L1478-L1540
[bluefin-containerfile]: https://github.com/projectbluefin/bluefin/blob/c442e5c46f6d3a0e95dda5b1d6794dc7f56906ae/Containerfile#L1-L43
[bluefin-artifacts]: https://github.com/projectbluefin/bluefin/blob/c442e5c46f6d3a0e95dda5b1d6794dc7f56906ae/.github/workflows/post-testing-e2e.yml#L21-L55
[bluefin-lts-containerfile]: https://github.com/projectbluefin/bluefin-lts/blob/42953700e63d4d8d4cf3be616328b3a2a00e7ae2/Containerfile#L1-L42
[bluefin-lts-artifacts]: https://github.com/projectbluefin/bluefin-lts/blob/42953700e63d4d8d4cf3be616328b3a2a00e7ae2/.github/workflows/build-nvidia-manifest.yml#L42-L100
[common-artifacts]: https://github.com/projectbluefin/common/blob/bb90f65aecbd4cdd0212f980b66d807a5d63d368/.github/workflows/build.yml#L109-L150
