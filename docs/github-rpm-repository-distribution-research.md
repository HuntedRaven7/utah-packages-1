# GitHub-only RPM repository distribution research

Research date: 2026-09-05. This examines a Copr-free way to distribute RPMs
to ordinary DNF/YUM clients using GitHub Actions, Releases, Pages, and GHCR.
The sources linked below are GitHub, upstream projects, or the projects using
the pattern.

## Recommendation

Use a static, signed RPM-MD repository on GitHub Pages: build and sign RPMs in
Actions, run `createrepo_c` only after signing, publish the RPMs and
`repodata/` under a stable architecture path, sign `repomd.xml`, and publish a
`.repo` file and public key alongside them. This is directly consumable by
DNF/YUM because it is the normal `baseurl` model, and it is a deployed pattern
rather than a theoretical one. The following two real examples demonstrate
the required pieces:

* [`ancwrd1/snx-rs` Pages workflow][snx-workflow] downloads release RPMs,
  lays them out per architecture, runs `createrepo_c`, signs `repomd.xml`,
  generates a `.repo` file, then publishes `site/` to its `gh-pages` branch.
  Its generated configuration uses
  `baseurl=https://ancwrd1.github.io/snx-rs/rpm/$basearch` and publishes the
  key through Pages. [Workflow: RPM layout and metadata][snx-metadata]
  [Workflow: client configuration][snx-repo-config]
  [Workflow: `gh-pages` deployment][snx-deploy]
* [`ocicl/ocicl`][ocicl-repo] puts package payloads in GitHub Release assets
  and puts only generated, signed RPM-MD metadata in Pages. Its workflow
  rewrites `primary.xml.gz` package locations to release-asset URLs, regenerates
  and signs `repomd.xml`, then deploys `docs/` with the official Pages artifact
  and deploy actions. [Release assets and metadata construction][ocicl-metadata]
  [Pages deployment][ocicl-deploy] Its checked-in client file has
  `baseurl=https://ocicl.github.io/ocicl/rpm-repo`. [OCICL `.repo` file][ocicl-repo-file]
* [`BlitterStudio/amiberry`][amiberry-repo] installs `createrepo-c`, extracts
  RPMs, runs `createrepo_c` per architecture, signs `repomd.xml`, and makes an
  orphan `gh-pages` branch before force-pushing it to the dedicated
  `BlitterStudio/amiberry-packages` repository. [Metadata build][amiberry-build]
  [Branch publication][amiberry-deploy] Its client configuration uses the
  standard RPM-MD `baseurl`, `gpgcheck`, `repo_gpgcheck`, and `gpgkey` fields.
  [Amiberry `.repo` file][amiberry-repo-file]

The first model is simplest. The Releases-plus-Pages-metadata model is useful
when RPM payloads would approach Pages' published-site limit. GitHub documents
both branch publishing and Actions-based Pages deployments; it notes that
external CI often commits output to `gh-pages`. [GitHub Pages publishing source][pages-source]
`raw.githubusercontent.com` can serve static files but is not GitHub's
documented website-distribution surface; use Pages for a public client
repository URL.

Minimal client configuration follows the verified `snx-rs` pattern:

```ini
[example]
name=Example RPM repository
baseurl=https://ORG.github.io/REPOSITORY/rpm/$basearch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://ORG.github.io/REPOSITORY/RPM-GPG-KEY-example
```

DNF5 documents `baseurl` as a list of repository URLs and recognizes RPM-MD
and YUM repository types. [DNF5 configuration][dnf-baseurl]
[DNF5 supported types][dnf-repo-types]

## GHCR and ORAS

ORAS is appropriate for storing an RPM as an OCI artifact. Its `push` command
accepts one or more files and a caller-selected media type, and its `pull`
command extracts files from a tagged or digest-pinned registry artifact.
[ORAS push implementation][oras-push] [ORAS pull implementation][oras-pull]
For example:

```sh
oras push ghcr.io/ORG/rpm-artifacts:PACKAGE-VERSION \
  package.rpm:application/vnd.example.rpm
oras pull ghcr.io/ORG/rpm-artifacts:PACKAGE-VERSION
```

GHCR supports OCI specifications, so it is registry-protocol compatible with
ORAS. [GitHub Container Registry documentation][ghcr-docs] It is not,
however, an RPM-MD HTTP repository. Upstream DNF5's build list includes
standard plugins such as `config-manager`, `copr`, `reposync`, and
`repomanage`, but no OCI registry repository plugin. [DNF5 plugin build list][dnf-plugins]
The DNF5 configuration and source found in this review document RPM-MD/YUM URL
repositories, not an `oci://` transport. [DNF5 configuration][dnf-baseurl]
[DNF5 supported types][dnf-repo-types]

Accordingly, there is no confirmed native DNF/libdnf5 support for installing
from `ghcr.io` as an OCI RPM artifact source. Treat GHCR/ORAS as an artifact
or image-layer channel; to serve DNF clients, materialize the artifacts into
RPMs plus `repodata/` (for example, an Actions job performs `oras pull`,
`createrepo_c`, and a Pages deployment). This absence is a source-based
assessment, not a claim that no third-party experimental plugin exists.

## Project Bluefin / Universal Blue

This repository, `projectbluefin/utah-packages`, currently publishes its
generated repository as a scratch OCI image at
`ghcr.io/<owner>/utah-packages`, with `/repository` copied into the image. Its
workflow tells container-image consumers to use the image as a build stage and
copy that directory, rather than giving DNF clients a public HTTP `baseurl`.
[Utah OCI publication][utah-oci]

`ublue-os/akmods` publishes OCI images to GHCR, not a Pages DNF repository.
Its image definitions identify `ghcr.io` using the `docker://` transport and
describe image families as caches of pre-built akmod RPMs. [Akmods image
definitions][akmods-images] Its reusable workflow grants `packages: write`,
builds, logs in, and pushes; the `Justfile` implementation pushes the OCI
image. [Build workflow][akmods-workflow] [Push implementation][akmods-push]

`ublue-os/main` consumes those akmod images as Containerfile build stages,
bind-mounting RPM directories before its image install process; it then logs
in and pushes resulting container/bootc images to GHCR. [Containerfile
consumption][main-containerfile] [Workflow publishing][main-workflow]
[Registry implementation][main-push] Thus, the exact repositories examined
are <https://github.com/ublue-os/akmods> and
<https://github.com/ublue-os/main>; their RPMs are build inputs embedded in
OCI image workflows, not a general DNF endpoint advertised through
`repodata/`.

## Hummingbird Pulp comparison

Hummingbird publicly consumes architecture-specific RPM repositories served
from Red Hat Pulp-content URLs. [Hummingbird repository configuration][hummingbird-repo]
Its container repository explains that those definitions are used to generate
RPM lockfiles that drive image builds. [Hummingbird lockfile documentation][hummingbird-lockfiles]
This establishes the public distribution/consumption endpoint; the public
source reviewed here does not establish the implementation of Red Hat's
deployment that publishes into that service.

A static Pages RPM-MD tree and a Pulp RPM Distribution URL can both serve
ordinary DNF/YUM clients. Pulp has materially broader repository-management
features: repository-version retention, automatic publication, distribution
objects, remote definitions, on-demand downloading, and additive or mirror
sync policies. [Pulp repository and remote][pulp-repository]
[Pulp sync policies][pulp-sync] [Pulp publication and distribution][pulp-publication]
Pulp OSS can provide those lifecycle and synchronization APIs, but it needs
hosting and operations outside GitHub. A Pages repository achieves the
client-facing distribution part with GitHub alone; its metadata refresh,
retention, rollback policy, and mirroring must be implemented in Actions and
Git history rather than supplied by a Pulp service.

## Capacity and rate implications

GitHub states that a published Pages site may not exceed 1 GB, with a soft
100 GB/month bandwidth limit; it also recommends keeping the source repository
under 1 GB. [GitHub Pages limits][pages-limits] GitHub Releases permit up to
1,000 assets per release, with each asset under 2 GiB; the release
documentation does not state a total release-size or release-bandwidth limit.
[GitHub Releases documentation][release-limits] GitHub says public Packages
use is free, and says Container Registry storage and bandwidth are currently
free (with advance notice before a change). [GitHub Packages billing][packages-billing]

Use Pages for a small or moderate complete repository. At higher package volume
or download volume, use Release assets for RPM payloads and Pages for metadata,
as OCICL does, or operate Pulp/object storage/CDN if non-GitHub infrastructure
becomes acceptable.

## Existing actions and tools

`createrepo_c` itself is the upstream implementation of `createrepo`.
[Upstream README][createrepo-readme] The reviewed production workflows invoke
it directly rather than relying on a dedicated RPM-repository action. Generic
Pages publishers are available: `peaceiris/actions-gh-pages` supports a
configurable target branch (default `gh-pages`), source directory, and
external repository; `actions/upload-pages-artifact` packages static assets
for Pages deployment. [Pages action definition][pages-action]
[Official upload action][upload-pages-action]

The GitHub Marketplace search for `createrepo` returned no results at the
time of this review. [Marketplace search][marketplace-createrepo] No
maintained, primary-source-verified action was found that implements the full
RPM lifecycle (collect RPMs, generate/sign RPM-MD, and serve it from Pages).
Compose the auditable primitives instead: `createrepo_c`, RPM/GPG signing,
and a generic Pages deploy action.

[snx-workflow]: https://github.com/ancwrd1/snx-rs/blob/282e809b7ac6e114fedbf180d7e6ac734e7798cf/.github/workflows/pages.yml#L76-L88
[snx-metadata]: https://github.com/ancwrd1/snx-rs/blob/282e809b7ac6e114fedbf180d7e6ac734e7798cf/.github/workflows/pages.yml#L134-L153
[snx-repo-config]: https://github.com/ancwrd1/snx-rs/blob/282e809b7ac6e114fedbf180d7e6ac734e7798cf/.github/workflows/pages.yml#L155-L173
[snx-deploy]: https://github.com/ancwrd1/snx-rs/blob/282e809b7ac6e114fedbf180d7e6ac734e7798cf/.github/workflows/pages.yml#L234-L241
[ocicl-repo]: https://github.com/ocicl/ocicl
[ocicl-metadata]: https://github.com/ocicl/ocicl/blob/53b2cd4fdcc8d7ccea175034f65089b587d9b2fe/.github/workflows/release.yaml#L655-L740
[ocicl-deploy]: https://github.com/ocicl/ocicl/blob/53b2cd4fdcc8d7ccea175034f65089b587d9b2fe/.github/workflows/release.yaml#L862-L911
[ocicl-repo-file]: https://github.com/ocicl/ocicl/blob/53b2cd4fdcc8d7ccea175034f65089b587d9b2fe/docs/rpm-repo/ocicl.repo#L1-L7
[amiberry-repo]: https://github.com/BlitterStudio/amiberry
[amiberry-build]: https://github.com/BlitterStudio/amiberry/blob/cf3654469f360d95da84cfbb7d6f92eb5ced9f40/.github/workflows/update-repos.yml#L118-L229
[amiberry-deploy]: https://github.com/BlitterStudio/amiberry/blob/cf3654469f360d95da84cfbb7d6f92eb5ced9f40/.github/workflows/update-repos.yml#L258-L298
[amiberry-repo-file]: https://github.com/BlitterStudio/amiberry/blob/cf3654469f360d95da84cfbb7d6f92eb5ced9f40/packaging/repo/amiberry.repo#L1-L8
[pages-source]: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
[dnf-baseurl]: https://github.com/rpm-software-management/dnf5/blob/main/doc/dnf5.conf.5.rst#L815-L822
[dnf-repo-types]: https://github.com/rpm-software-management/dnf5/blob/main/libdnf5/repo/repo.cpp#L155-L161
[oras-push]: https://github.com/oras-project/oras/blob/749d9c1e453c271b6894e82698c4e9e1f41b621c/cmd/oras/root/push.go#L61-L131
[oras-pull]: https://github.com/oras-project/oras/blob/749d9c1e453c271b6894e82698c4e9e1f41b621c/cmd/oras/root/pull.go#L59-L103
[ghcr-docs]: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
[dnf-plugins]: https://github.com/rpm-software-management/dnf5/blob/3c44b6252bd3f25a5d3dcc26c353ff2e086e7a1f/dnf5-plugins/CMakeLists.txt#L13-L24
[utah-oci]: https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L1478-L1535
[akmods-images]: https://github.com/ublue-os/akmods/blob/9a4db4eb1442c6f2e79f2ca8ba076e42f760759e/images.yaml#L25-L49
[akmods-workflow]: https://github.com/ublue-os/akmods/blob/9a4db4eb1442c6f2e79f2ca8ba076e42f760759e/.github/workflows/reusable-build.yml#L60-L70
[akmods-push]: https://github.com/ublue-os/akmods/blob/9a4db4eb1442c6f2e79f2ca8ba076e42f760759e/Justfile#L415-L438
[main-containerfile]: https://github.com/ublue-os/main/blob/main/Containerfile#L17-L42
[main-workflow]: https://github.com/ublue-os/main/blob/main/.github/workflows/reusable-build.yml#L141-L146
[main-push]: https://github.com/ublue-os/main/blob/main/Justfile#L479-L509
[hummingbird-repo]: https://gitlab.com/redhat/hummingbird/containers/-/blob/fa9f9f14198d38eb9d659f86f7bec791976b4982/yum-repos/hummingbird.repo#L5-34
[hummingbird-lockfiles]: https://gitlab.com/redhat/hummingbird/containers/-/blob/fa9f9f14198d38eb9d659f86f7bec791976b4982/yum-repos/README.md#L1-17
[pulp-repository]: https://github.com/pulp/pulp_rpm/blob/480ab51923b9a913a1f64a03d5f191e79040bf00/docs/user/tutorials/create_sync_publish.md#L30-L58
[pulp-sync]: https://github.com/pulp/pulp_rpm/blob/480ab51923b9a913a1f64a03d5f191e79040bf00/docs/user/tutorials/create_sync_publish.md#L149-L170
[pulp-publication]: https://github.com/pulp/pulp_rpm/blob/480ab51923b9a913a1f64a03d5f191e79040bf00/docs/user/tutorials/create_sync_publish.md#L247-L348
[pages-limits]: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
[release-limits]: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
[packages-billing]: https://docs.github.com/en/billing/concepts/product-billing/github-packages
[createrepo-readme]: https://github.com/rpm-software-management/createrepo_c/blob/332fad59231de20262f4d9f967cf59c12b234716/README.md#L1-L5
[pages-action]: https://github.com/peaceiris/actions-gh-pages/blob/main/action.yml#L1-L45
[upload-pages-action]: https://github.com/actions/upload-pages-artifact/blob/main/action.yml#L1-L27
[marketplace-createrepo]: https://github.com/marketplace?query=createrepo
