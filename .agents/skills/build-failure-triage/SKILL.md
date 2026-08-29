---
name: build-failure-triage
description: >-
  Diagnose a failed package build in this factory's GitHub Actions rebuild
  matrix. Use when a rebuild job fails, when asked why a package did not
  build, or when deciding whether a failure belongs to this repository,
  to Fedora, or to the build environment.
---

# Build Failure Triage

This factory forks Rawhide recipes and builds them against Hummingbird. Most
failures are **not** what the last line of the log suggests. This skill exists
because several wrong conclusions were reached by reading too little of a log
and then acting on them.

## Rule 0: read enough of the log

`get_job_logs` with a short `tail_lines` usually returns only rpm's summary and
the runner's cleanup, which is worthless. **Ask for 40-70 lines minimum.** The
real error is typically 20-60 lines above the summary.

Two wrong calls were made this way: "Fedora 44 cannot satisfy GNOME 51's
BuildRequires" (it was a single missing package we build ourselves), and
"libratbag has no Fedora fix" (its actual failure had moved to a missing
D-Bus session). Both reversed once the full log was read.

## Rule 1: confirm which build root ran

Every job prints this before `builddep`:

```
buildroot openssl: 3.5.7-2.fc44
```

`3.5.x` means `libcrypto.so.3` — the ABI Hummingbird has. If it ever reads
`4.x`, the root has regressed to Rawhide and the resulting RPMs will not
install on Hummingbird, whatever else the log says.

## Rule 2: check the commit is current

Check-run events arrive for superseded commits. Compare the event's
`head_sha` against the PR's current head before spending time on it. A run
whose conclusion is `cancelled` was superseded by a later push, not broken.

## Classifying the failure

| What the log shows | What it means | What to do |
| --- | --- | --- |
| `No match for argument: <pkg>` where `<pkg>` is in `config/upstream-sources.json` | Build ordering. The matrix has not built it yet. | Raise its `stage` in `upstream-sources.json` above the package that needs it |
| `Found X but need: '>= Y'` where the package is one of ours | Same — ordering, not a missing dependency | As above |
| `No match for argument: <pkg>` where `<pkg>` is a Fedora package | Genuine gap: Fedora predates what the source needs | Import and pin it, like `wayland-protocols` and `accountsservice` |
| Error inside `/usr/share/cargo/registry/...` or another Fedora-packaged dependency | Fedora packaging bug | Verify it affects more than one Fedora release before calling it release-specific. Do not work around it in the spec |
| `Bad exit status ... (%check)` needing a bus, display or device | The container lacks a service the test needs | Give the container the service. **Never** skip or disable the test |
| rpmbuild exit **11**, `*.buildreqs.nosrc.rpm` written | Dynamic BuildRequires (`%generate_buildrequires`, all Rust packages) | Install what the generated SRPM declares, then retry, bounded |
| Exit **125**, log under ~1 KB | `docker run` failed before the build; infrastructure | Not the package. Re-run once at most |
| `Signature verification failed` / `wrong key?` | A repo whose key the image does not trust | Disable that repo for the build if its content is not needed |

## Verify against primary sources

Do not infer a version from what Rawhide ships or from a package name.

- **What a source actually requires** — read its `meson.build` from the release
  tarball. GNOME 51 needs glib `2.86`, not the `2.89` Rawhide carries; assuming
  the latter sent one attempt down a dead end.
- **What a repository actually has** — read its `repodata/primary.xml`.
- **Binary versus source names** — `wayland` the source RPM ships as
  `libwayland-server` and `wayland-devel`. A name lookup that misses is not a
  missing package.

## Never

- Skip, disable or quarantine a test to make a build pass.
- Push an empty commit, or close and reopen, to re-trigger CI.
- Report a package as fixed without a green job to point at.
