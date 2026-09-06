# Packit reuse in a GitHub-native RPM factory

*Research date: 2026-09-05.  Scope: primary Packit sources (the upstream
GitHub repositories and Packit's official documentation) plus third-party
GitHub Actions workflow source used as integration evidence.  All Packit
source links below are immutable commit permalinks.*

## Decision summary

**Use neither Packit Service nor Packit's downstream-sync workflows for this
factory.**  The Packit CLI's `srpm`, `prepare-sources`, and local build paths
are technically usable without Copr, Koji, Bodhi, or Testing Farm: their
documented input is an upstream Git checkout and Packit config, and the local
RPM path ultimately executes `rpmbuild`.  This is a real, demonstrated
GitHub-Actions use case, not a hypothetical one.
[Packit CLI package/entry point and dependency set,
`packit/packit:pyproject.toml:1-61`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/pyproject.toml#L1-L61)
[local RPM implementation, `packit/packit:packit/upstream.py:1142-1234`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/upstream.py#L1142-L1234)

That technical possibility is not the recommended architectural choice for a
small project-owned factory.  Packit packages a broad Fedora/CentOS,
dist-git, remote-build, forge, and service abstraction layer—even when only
the source-archive/spec-rewrite fragment is wanted.  Prefer a
project-owned, reviewed roughly-200-line script that explicitly bumps the
spec, creates the archive, invokes `rpmbuild -bs`, and passes the result to
the existing Mock job.  Treat Packit as a reference implementation (and,
only if its configurable source preparation removes substantial package
specific complexity, a pinned execution dependency), rather than vendoring
or adopting its service/synchronization model.
[CLI dependency inventory including `copr`, `koji`, `bodhi-client`, `rpkg`,
`ogr`, and Fedora/openSUSE alias packages,
`packit/packit:pyproject.toml:25-55`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/pyproject.toml#L25-L55)
[hard-coded default dist-git instances,
`packit/packit:packit/constants.py:37-60`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/constants.py#L37-L60)

## 1. Licensing and distribution boundaries

### License result

`packit/packit` is MIT licensed: its license grants copying, modification,
distribution, sublicensing, and sale, subject to preserving the copyright and
permission notice in copies/substantial portions.  Therefore vendoring a
selected implementation is legally permitted, but must retain that notice;
the no-warranty language remains applicable.
[Packit MIT grant and notice condition,
`packit/packit:LICENSE:1-21`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/LICENSE#L1-L21)

`packit/ogr` is also MIT under the same notice-preservation condition.
[OGR MIT grant and notice condition,
`packit/ogr:LICENSE:1-21`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/LICENSE#L1-L21)

`packit/packit-service` is MIT, and its metadata independently labels the
distribution MIT.  The Service is nevertheless a separate web/worker product,
not a required component of the CLI.
[Packit Service MIT grant,
`packit/packit-service:LICENSE:1-21`](https://github.com/packit/packit-service/blob/cc8356cc839974ccc569a203a178388670e476c7/LICENSE#L1-L21)
[Service package metadata,
`packit/packit-service:setup.cfg:1-43`](https://github.com/packit/packit-service/blob/cc8356cc839974ccc569a203a178388670e476c7/setup.cfg#L1-L43)
[Service describes its purpose as GitHub-to-Fedora integration,
`packit/packit-service:README.md:1-17`](https://github.com/packit/packit-service/blob/cc8356cc839974ccc569a203a178388670e476c7/README.md#L1-L17)

### Installability and dependency weight

The CLI's Python distribution is named **`packitos`**, builds with Hatchling,
requires Python 3.9+, and exports the `packit` console command.  Its required
dependencies include remote Fedora services (`copr`, `koji`, `bodhi-client`,
`rpkg`), OGR and forge clients, Kerberos support, Bugzilla, and distribution
alias libraries; installing the CLI does not make those dependencies
architecturally disappear merely because a particular command avoids their
network paths.
[Packit build metadata, console script, and requirements,
`packit/packit:pyproject.toml:1-61`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/pyproject.toml#L1-L61)

OGR is independently packaged as `ogr`, declares Python 3.12+, and explicitly
supports installation from PyPI (`pip3 install --user ogr`).  Its direct
dependency set is much narrower but still includes GitPython, PyGithub,
python-gitlab, pyforgejo, requests/httpx, and cryptography.
[OGR project metadata and dependencies,
`packit/ogr:pyproject.toml:1-52`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/pyproject.toml#L1-L52)
[OGR installation options including PyPI,
`packit/ogr:README.md:53-94`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/README.md#L53-L94)

The Service has a `setup.py`/`setup.cfg` package definition but deliberately
leaves `install_requires` commented because its web-service and Celery-worker
images use separate dependency files.  Its service install manifest includes
FastAPI, Gunicorn, database drivers, Redis, Celery, Bodhi, and a Copr setup
step that installs OGR/specfile/Packit.  This is decisive evidence against
repurposing it for a Copr-free GitHub Actions factory.
[Service package setup boundary,
`packit/packit-service:setup.py:1-7`](https://github.com/packit/packit-service/blob/cc8356cc839974ccc569a203a178388670e476c7/setup.py#L1-L7)
[separate-component/dependency statement,
`packit/packit-service:setup.cfg:30-43`](https://github.com/packit/packit-service/blob/cc8356cc839974ccc569a203a178388670e476c7/setup.cfg#L30-L43)
[Service image dependencies and Copr installation,
`packit/packit-service:files/install-deps.yaml:11-51`](https://github.com/packit/packit-service/blob/cc8356cc839974ccc569a203a178388670e476c7/files/install-deps.yaml#L11-L51)

## 2. CLI commands: local paths and prerequisites

### `packit srpm`

The official command documentation says `packit srpm` creates an SRPM from
the current upstream content.  By default it uses `git describe --tags
--match '*.*'` for a snapshot version and `git archive` for the source
tarball; the documented minimum requirements are a Git-based upstream project
and a Packit config in that repository.
[official SRPM behavior and defaults,
`packit/packit.dev:docs/cli/srpm.md:7-25`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/srpm.md#L7-L25)

The CLI accepts a local directory or upstream Git URL (defaulting to the
current directory), creates a `PackitAPI`, resolves the release suffix, and
calls `create_srpm`; the command source contains no Copr/Koji/Bodhi/Testing
Farm submission on that path.
[SRPM command arguments and call path,
`packit/packit:packit/cli/srpm.py:18-104`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/srpm.py#L18-L104)
[API SRPM path prepares sources, creates the SRPM, and cleans up,
`packit/packit:packit/api.py:2049-2101`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/api.py#L2049-L2101)

`--update-release` defaults from configuration (normally enabled), while
`--preserve-spec` prevents spec modification and implies no release update.
This is important for reproducibility: choose one policy explicitly rather
than accept Packit's snapshot timestamp/release defaults.
[official SRPM options,
`packit/packit.dev:docs/cli/srpm.md:72-103`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/srpm.md#L72-L103)

### `packit prepare-sources`

`prepare-sources` is the same source-preparation pipeline without the final
SRPM: it determines the version, creates/downloads source material and
source-git patches, fixes/updates the spec, downloads remote sources, then
places the prepared spec-directory content in `--result-dir` (or a default
directory).  It has the same Git-project and in-repository-config
requirements as `srpm`.
[official prepare-sources purpose/requirements,
`packit/packit.dev:docs/cli/prepare-sources.md:7-18`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/prepare-sources.md#L7-L18)
[result directory and action options,
`packit/packit.dev:docs/cli/prepare-sources.md:19-69`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/prepare-sources.md#L19-L69)
[CLI invokes only API source preparation,
`packit/packit:packit/cli/prepare_sources.py:20-167`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/prepare_sources.py#L20-L167)
[API prepares then copies the spec directory,
`packit/packit:packit/api.py:1973-2047`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/api.py#L1973-L2047)

It is *locally executable*, but it is not a generic archive helper: its
default `fix-spec-file` behavior changes the configured `Source`, first
`%setup`/`%autosetup` directory, Version and Release.  Custom
`get-current-version`, `create-archive`, `create-patches`, and
`fix-spec-file` actions replace those defaults and are the supported
extension seam.
[SRPM action matrix and supported hooks,
`packit/packit.dev:docs/configuration/actions.md:86-101`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/configuration/actions.md#L86-L101)
[default `fix-spec-file` transformations,
`packit/packit.dev:docs/configuration/actions.md:137-169`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/configuration/actions.md#L137-L169)

### `packit build locally` and Mock

`packit build locally` is not a Mock client and does not call Copr.  The CLI
selects either an existing SRPM or `PackitAPI.create_rpms`; the latter prepares
the sources and the upstream implementation executes `rpmbuild -bb` with
explicit RPM directory macros.  Consequently its runner must have local RPM
build dependencies available; it is not an isolated chroot build.
[local-build CLI dispatch,
`packit/packit:packit/cli/builds/local_build.py:20-103`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/builds/local_build.py#L20-L103)
[local `rpmbuild` invocation,
`packit/packit:packit/upstream.py:1142-1212`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/upstream.py#L1142-L1212)
[official local-build command interface,
`packit/packit.dev:docs/cli/build/locally.md:7-37`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/build/locally.md#L7-L37)

In the reviewed current CLI, the public subcommand is **`packit build
locally`**, not `packit local-build`: Click registers this implementation
under the literal name `locally` beneath the `build` command group.  Treat
“local-build” as a descriptive/internal spelling (the source filename is
`local_build.py`), not as a command to put in a workflow.
[command registration, `packit/packit:packit/cli/builds/local_build.py:1-49`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/builds/local_build.py#L1-L49)

Packit instead exposes a distinct `packit build in-mock` command.  It creates
an SRPM unless one was supplied through configuration and calls
`mock --root ROOT [--resultdir DIR] SRPM`; its documented root may name a
Mock configuration or an explicit `.cfg` file.  Thus “Packit SRPM then
Mock” is feasible, and Packit's supported single-command version is
`build in-mock`; a project may also make the SRPM and invoke its own pinned
Mock command.
[Mock CLI implementation,
`packit/packit:packit/cli/builds/mock_build.py:18-119`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/builds/mock_build.py#L18-L119)
[Mock subprocess construction,
`packit/packit:packit/api.py:2701-2735`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/api.py#L2701-L2735)
[official Mock arguments,
`packit/packit.dev:docs/cli/build/in-mock.md:7-45`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/build/in-mock.md#L7-L45)

### Input/configuration caveats

All four local-facing commands use the `LocalProjectParameter`: it accepts a
directory (including a spec file's parent) or a Git URL.  The CLI package
iterator loads `packit.yaml` from the local project, and the API rejects a
non-Git local project for the normal path.  A factory must therefore provide
a real checkout (including tags if relying on default version discovery), a
Packit config, an explicit `specfile_path` or discoverable `.spec`, archive
sources, and the RPM tools/build dependencies.
[directory/URL parameter conversion,
`packit/packit:packit/cli/types.py:17-113`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/types.py#L17-L113)
[config loading per local project,
`packit/packit:packit/cli/utils.py:96-153`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/utils.py#L96-L153)
[normal-path Git-repository check,
`packit/packit:packit/cli/utils.py:257-327`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/utils.py#L257-L327)
[official `specfile_path` semantics,
`packit/packit.dev:docs/configuration/index.md:88-108`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/configuration/index.md#L88-L108)

## 3. `packit/actions`: complete-tree result

At commit
`936ee51c3b1c39f375a44232c7202f986e173516`, the recursive upstream Git tree
contains exactly five entries: `.pre-commit-config.yaml`, `LICENSE`, the
`srpm/` tree, `srpm/Dockerfile`, and `srpm/action.yml`.
[recursive Git tree, `packit/actions` at immutable commit](https://api.github.com/repos/packit/actions/git/trees/936ee51c3b1c39f375a44232c7202f986e173516?recursive=1)

The complete listing is:

```text
blob  .pre-commit-config.yaml
blob  LICENSE
tree  srpm
blob  srpm/Dockerfile
blob  srpm/action.yml
```

There is no root `README` or any other README in that tree, so the action
manifest and Dockerfile are the complete implementation/documentation surface.
[recursive Git tree, `packit/actions` at immutable commit](https://api.github.com/repos/packit/actions/git/trees/936ee51c3b1c39f375a44232c7202f986e173516?recursive=1)

The only shipped action is therefore the Docker `Packit SRPM build` action:
its manifest names one Docker action, its Dockerfile derives from
`quay.io/packit/packit`, marks `/github/workspace` safe for Git, and makes
`packit srpm` the entry point.  There is **no** local-build, Mock, Copr,
Testing Farm, or generic multi-action implementation in this repository at
that revision; consumers needing any of those must run the CLI themselves or
write an action.
[the sole action manifest,
`packit/actions:srpm/action.yml:1-6`](https://github.com/packit/actions/blob/936ee51c3b1c39f375a44232c7202f986e173516/srpm/action.yml#L1-L6)
[the SRPM-only image entrypoint,
`packit/actions:srpm/Dockerfile:1-5`](https://github.com/packit/actions/blob/936ee51c3b1c39f375a44232c7202f986e173516/srpm/Dockerfile#L1-L5)

## 4. GitHub Actions feasibility evidence

This is supported/sane for **build artifact production**.  NVIDIA/OpenShell's
reusable workflow installs `packit` and `rpm-build` in a pinned Fedora
container, checks out with full history, fetches tags, passes RPM/version and
prebuilt-binary context as environment variables, invokes `packit build
locally`, and uploads only the resulting RPM artifacts.  It has no Copr,
Koji, Bodhi, or Testing Farm step.
[OpenShell environment and checkout context,
`NVIDIA/OpenShell:.github/workflows/build-rpm.yml:44-102`](https://github.com/NVIDIA/OpenShell/blob/592df3e01489b3fd2af5573e1feb043108596aed/.github/workflows/build-rpm.yml#L44-L102)
[OpenShell artifact collection/upload,
`NVIDIA/OpenShell:.github/workflows/build-rpm.yml:104-123`](https://github.com/NVIDIA/OpenShell/blob/592df3e01489b3fd2af5573e1feb043108596aed/.github/workflows/build-rpm.yml#L104-L123)

A second public workflow, `saariuslystoned/OpenShell-grok`, has the same
pattern across x86_64 and aarch64 runners: install Packit/RPM tools in
Fedora, full-depth checkout and tag fetch, environment-selected inputs,
`packit build locally`, then artifact upload.
[OpenShell-grok matrix/tooling/checkout,
`saariuslystoned/OpenShell-grok:.github/workflows/rpm-package.yml:32-100`](https://github.com/saariuslystoned/OpenShell-grok/blob/c4b500a7de64d0b66e3ee8098f58d14299092162/.github/workflows/rpm-package.yml#L32-L100)
[OpenShell-grok artifact handling,
`saariuslystoned/OpenShell-grok:.github/workflows/rpm-package.yml:102-121`](https://github.com/saariuslystoned/OpenShell-grok/blob/c4b500a7de64d0b66e3ee8098f58d14299092162/.github/workflows/rpm-package.yml#L102-L121)

For the prebuilt `packit/actions/srpm` form, `emtee40/openSC` uses a
full-depth checkout, invokes that action, and uploads the `.src.rpm`;
the adjacent RPM job delegates to that repository's own local action.
[openSC SRPM Action integration,
`emtee40/openSC:.github/workflows/packit.yaml:14-42`](https://github.com/emtee40/openSC/blob/b9529d944537f8c1e40b798909b71517a609c870/.github/workflows/packit.yaml#L14-L42)

**Operational judgment:** this proves a conventional GitHub-native local
build is viable.  Pin all Actions and Packit/container versions rather than
use the mutable `@main` used by the older openSC example; fetch tags or pass
an explicit version because the default archive/version logic is Git-history
dependent.  Do not infer that this makes downstream synchronization a sane
fit—the two areas have materially different dependencies.
[default archive/version dependence,
`packit/packit.dev:docs/cli/srpm.md:9-17`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/srpm.md#L9-L17)

## 5. Downstream synchronization is not a generic two-checkout API

`sync-from-downstream` documents a Fedora dist-git repository, upstream
Packit config, Fedora Pagure token, and GitHub token as requirements; its
stated result is an upstream pull request from Fedora dist-git.  Its CLI has
only `PATH_OR_URL` for the upstream checkout—not a second arbitrary local
checkout/manifest parameter—and its default branch is obtained through
`api.dg`.
[official sync requirements and flow,
`packit/packit.dev:docs/cli/sync-from-downstream.md:7-43`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/sync-from-downstream.md#L7-L43)
[sync CLI options and API call,
`packit/packit:packit/cli/sync_from_downstream.py:17-101`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/sync_from_downstream.py#L17-L101)

The implementation reinforces that design: it updates/switches the
`DistGit` branch, resolves `files_to_sync` with dist-git as source and
upstream as destination, then creates a branch/commit and, unless `--no-pr`,
pushes to a fork and creates a PR.  That is remote-forge synchronization,
not a local manifest copier.
[sync implementation,
`packit/packit:packit/api.py:1628-1710`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/api.py#L1628-L1710)
[DistGit describes Pagure-over-dist-git responsibility,
`packit/packit:packit/distgit.py:45-57`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/distgit.py#L45-L57)

`propose-downstream` does expose `--dist-git-path`, but the official
requirements still require a Fedora/CentOS dist-git repository, service
tokens, Kerberos, a release tag/spec/config, and lookaside upload.  Its
implementation calls `sync_release`, which uses a `DistGit` object, requires
clean upstream and dist-git repositories, derives an upstream version/tag,
and expects a downstream project/default branch.
[official propose-downstream prerequisites and lookaside behavior,
`packit/packit.dev:docs/cli/propose-downstream.md:7-60`](https://github.com/packit/packit.dev/blob/c545d8d0b804ec4cfe70bfdd4bbcc880535687b9/docs/cli/propose-downstream.md#L7-L60)
[CLI `--dist-git-path` model,
`packit/packit:packit/cli/propose_downstream.py:33-202`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/cli/propose_downstream.py#L33-L202)
[sync-release version, clean-tree and DistGit assumptions,
`packit/packit:packit/api.py:996-1100`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/api.py#L996-L1100)

There is a narrow configuration escape hatch: `dist_git_base_url` and
`dist_git_namespace` can construct a `DistGitInstance` from a custom URL
instead of the default Fedora `fedpkg` instance.  This makes a GitHub-hosted
“downstream” experimentally conceivable, but it remains Packit's
dist-git-shaped object (package-name-derived URL, namespace/remote detection,
source cache and PR behaviors), not documented support for arbitrary local
checkouts or a factory manifest.  The API also initializes a `DistGit`
instance lazily and its local-project path clones to a temporary directory
when no clone path is supplied.
[custom/default dist-git construction,
`packit/packit:packit/config/common_package_config.py:39-74`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/config/common_package_config.py#L39-L74)
[downstream URL is package-name-derived,
`packit/packit:packit/config/common_package_config.py:480-493`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/config/common_package_config.py#L480-L493)
[DistGit local-clone behavior,
`packit/packit:packit/distgit.py:100-165`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/distgit.py#L100-L165)
[Fedora/openSUSE aliases and dist-git-branch transformation,
`packit/packit:packit/config/aliases.py:35-151`](https://github.com/packit/packit/blob/868f8f6b5f04b0dfc5f4e42aa466721ffc0e4b15/packit/config/aliases.py#L35-L151)

**Conclusion for this scope:** no, Packit does not provide a supported direct
interface for “two arbitrary local Git checkouts plus a manifest” release
synchronization.  Configuring a custom downstream URL would mean adapting an
unsupported dist-git workflow and retaining its remote PR/lookaside/alias
assumptions; it is fighting the model, not reusing a small neutral sync
primitive.

## 6. OGR is the independently reusable component

OGR is intentionally a library offering one API across GitHub, GitLab,
Pagure, and Forgejo, with an explicit GitHub example that gets a project and
lists releases.  Unlike Packit synchronization, it does not encode an RPM or
Fedora release model in this public surface.
[OGR supported-forge statement and GitHub example,
`packit/ogr:README.md:10-51`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/README.md#L10-L51)

Its public module exports `GithubService`, `GitlabService`, `PagureService`,
`ForgejoService`, `get_project`, and authentication/configuration helpers.
The URL-based factory selects a registered service implementation, supports
custom service instances, and returns a forge-neutral `GitProject`.  The
abstract project interface includes practical cross-forge operations such as
branches, releases, forks, pull requests, statuses, and file contents.
[public OGR exports,
`packit/ogr:ogr/__init__.py:1-30`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/ogr/__init__.py#L1-L30)
[URL/service factory,
`packit/ogr:ogr/factory.py:11-130`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/ogr/factory.py#L11-L130)
[forge-neutral project/release/PR interface,
`packit/ogr:ogr/abstract/git_project.py:15-104`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/ogr/abstract/git_project.py#L15-L104)
[release/PR/file operations,
`packit/ogr:ogr/abstract/git_project.py:300-494`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/ogr/abstract/git_project.py#L300-L494)

`GithubService` is a usable independent GitHub wrapper: it accepts a token
or GitHub-App-style credentials and can construct a `GithubProject` or create
a repository.  OGR also has GitLab service code that accepts a configurable
instance URL/token, underscoring that the abstraction is forge-oriented rather
than Packit-workflow-oriented.
[GitHub service initialization/project API,
`packit/ogr:ogr/services/github/service.py:28-170`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/ogr/services/github/service.py#L28-L170)
[GitLab service configurable instance/token,
`packit/ogr:ogr/services/gitlab/service.py:18-104`](https://github.com/packit/ogr/blob/1d91993bf4c52e46d4a9b562b443a230a8c0736e/ogr/services/gitlab/service.py#L18-L104)

For a fully GitHub-native factory, OGR is legally and technically reusable,
but GitHub Actions already has first-party API mechanisms and this project
need not acquire OGR's multi-forge dependency surface unless it actually needs
portable forge support.  It is the only Packit-adjacent component in this
investigation that is a plausible standalone automation library.

## 7. Recommended adoption boundary

1. **Keep the existing GitHub workflow/Mock/RPM repository architecture.**
   Implement version/spec/archive/SRPM policy in project-owned code with
   inputs and outputs visible in the workflow.
2. **If evaluating Packit pragmatically, pin the CLI image/version and use
   only `srpm` or `build in-mock`.**  Add a minimal `packit.yaml`, full
   checkout/tags, explicit `specfile_path`, and tests which assert the
   resulting SRPM's source and spec contents.  Do not use mutable
   `packit/actions/srpm@main`.
3. **Do not vendor Packit wholesale.**  MIT permits it, but its 20+
   mandatory Python dependencies and Fedora/remote-service abstractions turn a
   small packaging policy into an upstream maintenance fork.
4. **Do not adopt `propose-downstream` or `sync-from-downstream`.**  They are
   explicitly dist-git release workflows, including branches, remote forge
   API, lookaside, Fedora credentials, aliases, and sometimes Kerberos—not a
   Copr-free local synchronization primitive.
