# Testing Farm, tmt/fmf, and RPM/image CI research

**Scope.** This report separates directly verified implementations from
similarly named patterns. GitHub references are immutable commit URLs so their
line ranges remain auditable. “Workflow” below means either a GitHub Actions
workflow or, where explicitly labelled, an Argo `WorkflowTemplate`; it does
not imply that all examples run on GitHub-hosted runners.

## Findings at a glance

* Testing Farm is a test-execution backend (“Testing System as a Service”) with
  an HTTP API; it uses test metadata to decouple tests from the underlying
  infrastructure. [Testing Farm documentation — Testing System as a Service](https://docs.testing-farm.io/Testing%20Farm/0.1/index.html#testing-system-as-a-service)
* tmt stores test-execution metadata in a Git repository and uses FMF, a
  YAML-based, source-adjacent metadata format. An FMF tree is rooted by
  `.fmf`, with metadata read from `*.fmf` files. [tmt overview, lines 19–28](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/docs/overview.rst#L19-L28)
  [tmt guide, lines 115–136](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/docs/guide.rst#L115-L136)
* The official tmt implementation documents all four requested guest choices:
  `local`, Podman-backed `container`, testcloud/libvirt-backed `virtual`, and
  SSH `connect` to an existing host. The distinctions matter: `local` and
  `connect` do **not** provision a machine. [local plugin, lines 256–292](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/local.py#L256-L292)
  [container plugin, lines 693–719](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/podman.py#L693-L719)
  [virtual plugin, lines 1401–1443](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/testcloud.py#L1401-L1443)
  [connect plugin, lines 228–274](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/connect.py#L228-L274)
* A public Actions example runs `tmt run ... provision --how container`; its
  FMF plan asks tmt to install an RPM-named package and its smoke test checks
  that package with `rpm -q`. The Actions bootstrap itself installs Podman via
  APT and tmt via pip, rather than directly installing an RPM. [CoreOS Actions workflow, lines 34–48](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/.github/workflows/tmt-tests.yml#L34-L48)
  [CoreOS plan, lines 1–4](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/tests/tmt/plans/main.fmf#L1-L4)
  [CoreOS smoke test, lines 1–6](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/tests/tmt/tests/core/core.fmf#L1-L6)

## 1. Testing Farm and tmt/fmf format

Testing Farm describes itself as a reliable, scalable Testing System as a
Service for Red Hat internal and Hybrid Cloud services and related open-source
projects. Its documentation says it is commonly used as a test-execution
backend for services or CI systems, exposes an HTTP API, and abstracts tests
from infrastructure so tests can express hardware requirements independently
of the provider. [Testing Farm documentation — Testing System as a Service](https://docs.testing-farm.io/Testing%20Farm/0.1/index.html#testing-system-as-a-service)

tmt’s specification defines L1 **test** metadata (for example `test`,
`framework`, `path`, `duration`, and required packages) and L2 **plan**
metadata. Plans group tests and specify the discover, provision, prepare,
execute, and report stages. [tmt overview, lines 34–53](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/docs/overview.rst#L34-L53)
The guide further says a plan is recognized by an `execute` key in any
`*.fmf` file, and shows a plan choosing a container, installing `wget`, then
executing a test. [tmt guide, lines 142–156](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/docs/guide.rst#L142-L156)
[tmt guide, lines 168–199](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/docs/guide.rst#L168-L199)

### Official provisioning evidence

The published tmt guide explicitly shows local, container, and virtual
invocations, including `tmt run -a provision -h container`; its Provision
Plugins reference lists `virtual.testcloud`, `container`, `connect`, and
`local` as supported provisioning plugins. [tmt guide — run locally, in a
container, or in a VM](https://tmt.readthedocs.io/en/stable/guide.html)
[guide source, lines 59–95](https://github.com/teemtee/tmt/blob/main/docs/guide.rst#L59-L95)
[tmt Provision Plugins reference](https://tmt.readthedocs.io/en/stable/plugins/provision.html#provision-plugins)

| Method | What the official source proves | Minimal configuration / operational qualification |
|---|---|---|
| `local` | The plugin uses localhost and does not provision a system; tests execute on localhost. | `provision: { how: local }`. It requires explicit unsafe-behaviour consent. [local plugin, lines 265–292](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/local.py#L265-L292) |
| `container` | The plugin is registered as `container`, requires Podman, and creates a new container using Podman. | The documented example is `how: container` with `image: fedora:latest`. [container plugin, lines 693–719](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/podman.py#L693-L719) |
| `virtual` | `virtual.testcloud` requires testcloud and libvirt for VM-backed guests, and describes a local VM provided by testcloud. | `how: virtual` selects the latest Fedora image in the minimal example; the full example accepts a QCOW2 image, user, elevation, memory, and disk. [virtual plugin, lines 1401–1443](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/testcloud.py#L1401-L1443) |
| `connect` | The plugin connects to an already provisioned guest using SSH and does not provision a system itself. | Minimal metadata contains `how: connect` and `guest`; the documented example supports a user, sudo elevation, and a private key. [connect plugin, lines 228–274](https://github.com/teemtee/tmt/blob/2b972c9c9ad507a3d9cfbbe543441745b21da414/tmt/steps/provision/connect.py#L228-L274) |

## 2. Public RPM-oriented CI examples

### tmt with a container and an RPM verification

`coreos/console-login-helper-messages` runs on `ubuntu-latest`, installs
Podman, installs `tmt[provision]`, and invokes the following container
provisioner command:

```sh
tmt run --all --debug -vvvv provision --how container "${PLAN_FILTER[@]}"
```

[CoreOS Actions workflow, lines 23–48](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/.github/workflows/tmt-tests.yml#L23-L48)
Its plan declares the tmt `install` preparation method for
`console-login-helper-messages`, and its core smoke test runs
`rpm -q console-login-helper-messages`. This is direct evidence of an
RPM-oriented test plan, but **not** evidence that the YAML’s outer Actions
shell executes `dnf install` or `rpm -i`. [CoreOS plan, lines 1–4](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/tests/tmt/plans/main.fmf#L1-L4)
[CoreOS smoke test, lines 1–6](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/tests/tmt/tests/core/core.fmf#L1-L6)

### `rpmlint`

`ErikReider/SwayNotificationCenter` has an Actions `rpmlint` job using a
Fedora-minimal job container. It installs `rpmlint` and `rpkg` using
`microdnf`, generates the spec with `rpkg spec`, and runs
`rpmlint ./specs/swaync.rpkg.spec`. [SwayNotificationCenter lint workflow, lines 48–77](https://github.com/ErikReider/SwayNotificationCenter/blob/b8017a4d1a53debdf0e8766628fb80357eae31e7/.github/workflows/linting.yml#L48-L77)

### `rpmdeplint`

The public `fedora-ci/rpmdeplint-pipeline` provides a genuine tmt/FMF Fedora
CI pipeline: its `/plan` provisions a Fedora container, installs the
`@osci/rpmdeplint` COPR, and its `/check` test requires and invokes
`rpmdeplint`. [rpmdeplint FMF plan, lines 1–34](https://github.com/fedora-ci/rpmdeplint-pipeline/blob/637161dc45bbcff65d7d366e0173fb2ae26b160b/rpmdeplint.fmf#L1-L34)
[rpmdeplint FMF check, lines 55–68](https://github.com/fedora-ci/rpmdeplint-pipeline/blob/637161dc45bbcff65d7d366e0173fb2ae26b160b/rpmdeplint.fmf#L55-L68)

**Important limit:** this is not an Actions job that runs `rpmdeplint`.
At the pinned revision, the repository’s sole GitHub Actions workflow is a
Jenkinsfile syntax check. [rpmdeplint-pipeline Actions workflow, lines 1–15](https://github.com/fedora-ci/rpmdeplint-pipeline/blob/637161dc45bbcff65d7d366e0173fb2ae26b160b/.github/workflows/pipeline_linter.yml#L1-L15)
Accordingly, no exact public **GitHub Actions** `rpmdeplint` execution example
was found and included here; the cited FMF pipeline is the closest verified
primary-source example, and must not be represented as an Actions execution.

### `dnf5 repoquery`

`sirredbeard/azurelinux-desktop` has a GitHub Actions workflow that launches
its toolchain container and runs `dnf5 repoquery` with an explicitly supplied
Azure Linux base repository, `--available`, `--latest-limit=1`, and a NEVRA
query format to obtain the latest kernel. [Azure Linux desktop kmod workflow, lines 56–93](https://github.com/sirredbeard/azurelinux-desktop/blob/a5c42f72cca4d9ba280a467a11aec7b5efc9e39e/.github/workflows/publish-desktop-kmods.yml#L56-L93)
This is an exact `dnf5 repoquery` check in a public Actions workflow, rather
than an inference from the presence of DNF packages.

## 3. Project Bluefin / ublue OS-image testing patterns

### A GitHub Actions image candidate that is handed to E2E

`projectbluefin/common` builds a candidate layer with Buildah, writes a
Containerfile based on `ghcr.io/projectbluefin/bluefin:testing`, copies the
candidate’s `system_files` into it, then builds and (for permitted events)
pushes the composed test image. [common PR E2E workflow, lines 21–115](https://github.com/projectbluefin/common/blob/bb90f65aecbd4cdd0212f980b66d807a5d63d368/.github/workflows/pr-e2e.yml#L21-L115)
The same workflow passes that resulting image to its reusable testsuite
wrapper. [common PR E2E workflow, lines 117–127](https://github.com/projectbluefin/common/blob/bb90f65aecbd4cdd0212f980b66d807a5d63d368/.github/workflows/pr-e2e.yml#L117-L127)
The wrapper in turn calls the `projectbluefin/testsuite` E2E workflow with the
image and suite inputs. [common testsuite wrapper, lines 1–30](https://github.com/projectbluefin/common/blob/bb90f65aecbd4cdd0212f980b66d807a5d63d368/.github/workflows/run-testsuite.yml#L1-L30)

### GitHub Actions: bootc OCI image installed and booted in QEMU/KVM

`projectbluefin/testsuite`’s reusable E2E workflow enables KVM, pulls both
the target OCI image and runner container with Podman, and installs
`qemu-system-x86`. [testsuite E2E workflow, lines 301–326](https://github.com/projectbluefin/testsuite/blob/ee82d53a4f86617d807df831a60ad1deaa0d5366/.github/workflows/e2e.yml#L301-L326)
It then starts the OCI image under privileged Podman and executes
`bootc install to-disk --via-loopback /data/disk.raw`. [testsuite E2E workflow, lines 333–370](https://github.com/projectbluefin/testsuite/blob/ee82d53a4f86617d807df831a60ad1deaa0d5366/.github/workflows/e2e.yml#L333-L370)
Finally, it boots that disk with `qemu-system-x86_64 -machine q35,accel=kvm`
and waits for SSH to the VM. [testsuite E2E workflow, lines 675–720](https://github.com/projectbluefin/testsuite/blob/ee82d53a4f86617d807df831a60ad1deaa0d5366/.github/workflows/e2e.yml#L675-L720)
This is direct evidence of a GitHub Actions OS-image test path using an OCI
image, Podman, bootc installation, and a KVM-accelerated VM.

The same workflow has a fallback that attempts `rpm-ostree install
--apply-live` and then `dnf install` for missing shell tools in the booted
VM. This is a runtime fallback, not a proof that RPM landing is always
validated by a transaction. [testsuite E2E workflow, lines 859–942](https://github.com/projectbluefin/testsuite/blob/ee82d53a4f86617d807df831a60ad1deaa0d5366/.github/workflows/e2e.yml#L859-L942)

### Argo workflow: nested Podman systemd target

`projectbluefin/lab` is an Argo-based workflow source, not GitHub Actions.
Its `run-container-tests` template explicitly describes a nested,
systemd-booted target OCI container whose privileged Podman host is
Kubernetes-native. [lab container test template, lines 1–11](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/run-container-tests.yaml#L1-L11)
The runner is privileged because Podman needs a writable cgroup hierarchy,
mounts dedicated container storage/runroot volumes, and obtains the target
image parameters. [lab container test template, lines 91–147](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/run-container-tests.yaml#L91-L147)
It pulls the specified image and runs it with `--systemd=always`,
`--privileged`, and `/sbin/init`, then probes systemd, D-Bus, logind, and
graphical-seat readiness using `podman exec`. [lab container test template, lines 352–435](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/run-container-tests.yaml#L352-L435)

This is strong evidence for **Podman running inside a privileged Kubernetes
Pod to test a nested target container**. It is not labelled
“Podman-in-Podman” by the source, so that exact term should not be used as if
it had been verified.

### Argo workflow: KubeVirt container-disk VM

The lab’s `provision-containerdisk-vm` template says it provisions a KubeVirt
test VM from a containerDisk image in its local Zot registry. [lab VM template, lines 1–10](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/provision-containerdisk-vm.yaml#L1-L10)
Its manifest is a `kubevirt.io/v1` `VirtualMachine`, injects an SSH key through
the QEMU guest agent, and attaches the target as a `containerDisk` volume.
[lab VM template, lines 85–151](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/provision-containerdisk-vm.yaml#L85-L151)

## 4. Existing `utah-packages` evidence

The repository’s Hummingbird-gap workflow pulls the target bootc image and
uses its `rpm` entrypoint to enumerate installed package names. It then runs a
Fedora container, installs `dnf-plugins-core`, and performs `dnf repoquery`
against the Hummingbird repository before calculating parity gaps.
[utah-packages gap workflow, lines 19–45](https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/recalculate-hummingbird-gaps.yml#L19-L45)
That is an image-installed-RPM inventory plus repository inventory comparison;
it is not `dnf5 repoquery`, and it does not attempt an RPM installation
transaction. [utah-packages gap workflow, lines 26–45](https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/recalculate-hummingbird-gaps.yml#L26-L45)

The RPM rebuild workflow separately resolves package build requirements inside
a Fedora container using `dnf ... --assumeno builddep`, records missing
providers and version conflicts, and uploads the preflight report.
[utah-packages rebuild workflow, lines 150–225](https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/rebuild-rpms.yml#L150-L225)
Later in that workflow, the runtime contract chooses `dnf5` when present and
otherwise `dnf`, then performs an `--assumeno` install-resolution check against
the factory and Hummingbird repositories. [utah-packages rebuild workflow, lines 1455–1467](https://github.com/projectbluefin/utah-packages/blob/66fa022c04809c1ac0d4bffcd33163047eb782fb/.github/workflows/rebuild-rpms.yml#L1455-L1467)

## 5. What static checks prove, and a GitHub-only minimum gate

`rpmlint` checks common RPM-package errors and accepts binary RPMs, source
RPMs, and plain spec files. Its own documentation recommends source RPMs for
the broadest check coverage, so it is a spec/package-quality check rather than
an installability proof. [rpmlint README, lines 11–17](https://github.com/rpm-software-management/rpmlint/blob/main/README.md#L11-L17)
`rpmdeplint` is specifically a tool to find RPM-package errors in the context
of the dependency graph and depends on `rpm`, `librepo`, and `libsolv`; that
makes it suitable for solver/dependency-graph validation, not a substitute for
executing a package after installation. [rpmdeplint README, lines 1–13](https://github.com/fedora-ci/rpmdeplint/blob/main/README.md#L1-L13)
DNF5's `repoquery` queries packages from configured repositories; `--whatprovides`
finds capability providers, `--whatrequires` finds packages requiring a
capability, and `--providers-of=requires --recursive` repeatedly resolves
providers for package requirements. It can therefore inspect availability and
the repository dependency graph, but it does not run a transaction or execute
the installed software. [DNF5 repoquery documentation — description](https://dnf5.readthedocs.io/en/latest/commands/repoquery.8.html#description)
[DNF5 repoquery documentation — dependency options](https://dnf5.readthedocs.io/en/latest/commands/repoquery.8.html#whatprovides)
[DNF5 repoquery documentation — recursive providers](https://dnf5.readthedocs.io/en/latest/commands/repoquery.8.html#recursive)

For a Copr-free GitHub-only factory, the low-complexity gate is a Fedora or EL
Actions `container:` job that first exposes the just-built RPM(s) through a
file-backed repository, then runs a real `dnf install` transaction and
package-specific smoke commands in that same matching base image. Run
`rpmlint` on the SRPM/binary RPM alongside it, and use `dnf5 repoquery` only
as a fast diagnostic/preflight complement. This splits the evidence cleanly:
lint detects common packaging mistakes, repoquery explains the available
dependency graph, while the actual transaction and smoke command demonstrate
installability and basic functionality. The SwayNotificationCenter Actions
job is a real containerized `rpmlint` precedent, and the Azure Linux job is a
real Actions `dnf5 repoquery` precedent. [SwayNotificationCenter lint workflow, lines 48–77](https://github.com/ErikReider/SwayNotificationCenter/blob/b8017a4d1a53debdf0e8766628fb80357eae31e7/.github/workflows/linting.yml#L48-L77)
[Azure Linux desktop kmod workflow, lines 56–93](https://github.com/sirredbeard/azurelinux-desktop/blob/a5c42f72cca4d9ba280a467a11aec7b5efc9e39e/.github/workflows/publish-desktop-kmods.yml#L56-L93)

The public sources support using these checks in the same CI system, but they
do **not** establish a common one-workflow convention that chains `rpmlint`,
`rpmdeplint`, and `dnf5 repoquery` together: the verified `rpmlint` and
`dnf5 repoquery` examples are different Actions repositories, while the
verified `rpmdeplint` invocation is an FMF/Fedora-CI plan rather than Actions.
[SwayNotificationCenter lint workflow, lines 48–77](https://github.com/ErikReider/SwayNotificationCenter/blob/b8017a4d1a53debdf0e8766628fb80357eae31e7/.github/workflows/linting.yml#L48-L77)
[Azure Linux desktop kmod workflow, lines 56–93](https://github.com/sirredbeard/azurelinux-desktop/blob/a5c42f72cca4d9ba280a467a11aec7b5efc9e39e/.github/workflows/publish-desktop-kmods.yml#L56-L93)
[rpmdeplint FMF plan, lines 17–34](https://github.com/fedora-ci/rpmdeplint-pipeline/blob/637161dc45bbcff65d7d366e0173fb2ae26b160b/rpmdeplint.fmf#L17-L34)

## 6. Explicit gaps and non-claims

* No source cited above demonstrates a GitHub Actions workflow whose outer
  shell both calls `tmt run --how container` **and** directly invokes
  `dnf`, `yum`, or `rpm -i` to install the test RPM. The CoreOS example instead
  delegates installation to the tmt plan and verifies the result with
  `rpm -q`. [CoreOS Actions workflow, lines 34–48](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/.github/workflows/tmt-tests.yml#L34-L48)
  [CoreOS plan and test, lines 1–4](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/tests/tmt/plans/main.fmf#L1-L4)
  [CoreOS smoke test, lines 1–6](https://github.com/coreos/console-login-helper-messages/blob/94c615bc1b25c57f7302588e3ab83652c80bce85/tests/tmt/tests/core/core.fmf#L1-L6)
* No exact GitHub Actions `rpmdeplint` runner execution was verified. The
  primary-source rpmdeplint example is an FMF plan for Fedora CI, while its
  checked-in Actions workflow only lints a Jenkinsfile. [rpmdeplint FMF plan, lines 17–34](https://github.com/fedora-ci/rpmdeplint-pipeline/blob/637161dc45bbcff65d7d366e0173fb2ae26b160b/rpmdeplint.fmf#L17-L34)
  [rpmdeplint-pipeline Actions workflow, lines 7–15](https://github.com/fedora-ci/rpmdeplint-pipeline/blob/637161dc45bbcff65d7d366e0173fb2ae26b160b/.github/workflows/pipeline_linter.yml#L7-L15)
* No exact `systemd-nspawn` workflow example was verified in the public
  ublue-os/projectbluefin sources examined. The closest verified
  projectbluefin implementation uses a nested systemd target started by
  Podman, not `systemd-nspawn`. [lab container test template, lines 400–435](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/run-container-tests.yaml#L400-L435)
* The Bluefin lab examples are Argo `WorkflowTemplate` definitions deployed
  from a GitHub repository. They demonstrate image-testing mechanics, but
  should not be cited as GitHub Actions evidence. [lab container test template, lines 1–17](https://github.com/projectbluefin/lab/blob/22d40cd2f7069e0352bee8b2cec6cd5539ca7e9b/argo/workflow-templates/run-container-tests.yaml#L1-L17)
