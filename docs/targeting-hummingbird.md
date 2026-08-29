# Targeting Hummingbird

This page exists because the same questions kept being re-derived from
repository metadata instead of read. It records what "build targeting
Hummingbird" means concretely, and what is verified fact versus still open.

## What this factory forks

We fork **Fedora Rawhide's RPM recipes**, not Fedora's binary packages.

| input | source | role |
| --- | --- | --- |
| spec + patches | Fedora dist-git `rawhide` branch | bootstrap recipe, pinned by commit and tree in `.hummingbird-upstream.json` |
| source archive | the project's own upstream release | the only payload allowed into a build, SHA-512 locked |
| build root | see below | supplies compiler, macros, BuildRequires |

Rawhide is never a source of package payloads and never a repository a
consumer image enables. It is a recipe donor and a bootstrap build root.

We track **the latest upstream release**, not whatever Fedora happens to have
tagged. That is the point of the direct-source pipeline: Fedora can lag
upstream, and a spec is a build recipe, not a release feed.

## What "targeting Hummingbird" means

Hummingbird is not a Fedora release. It is an overlay of rebuilt packages on
top of a Fedora release, with its own disttag and ABI.

Verified against `packages.redhat.com/api/pulp-content/public-hummingbird/x86_64/`
and the `bootc-os` image on 2026-08-29:

- **Disttag `hum1`** — uniform across all 18,458 published subpackages.
- **Release convention `.N` immediately before `%{?dist}`**, so a Hummingbird
  rebuild sorts above the Fedora build it derives from and below the next
  upstream version. `Release: 3%{?dist}` becomes `Release: 3.1%{?dist}`.
  Seen in practice: `openssl-libs-3.5.6-0.1.hum1`, `glibc-2.42-11.1.hum1`,
  `bootupd-0.2.36-3.hum1`.
- **3,510 packages, base OS only.** It carries openssl, glibc, python3, bootc.
  It carries **no desktop stack at all** — no gnome-shell, mutter, gtk4,
  libadwaita, not even pipewire. Every desktop package is a gap by definition.
- **Paired with Fedora 44.** `images/variables.yml` in
  `redhat/hummingbird/containers` maps `default_variant_repos.rawhide` to
  `fedora-44.repo`. Hummingbird's "rawhide" distro variant is pinned to
  Fedora 44; it does not follow the rolling Rawhide.
- **Builder image** `quay.io/hummingbird-ci/hummingbird-builder:latest`.

### The ABI that matters

| | Hummingbird | Fedora 44 | Rawhide (46) |
| --- | --- | --- | --- |
| openssl | 3.5.6 (`libcrypto.so.3`) | 3.5.5 (`libcrypto.so.3`) | **4.0.1 (`libcrypto.so.4`)** |
| glibc | 2.42 | 2.43 | 2.44.9000 |
| python3 | 3.14 | 3.14 | **3.15** |

This is not academic. An RPM built in a Rawhide root can acquire dependencies
that Hummingbird cannot satisfy. A worked example: `gnome-shell` built on
Rawhide pulls in `pipewire-libs`, which there requires `libcrypto.so.4`.
Hummingbird provides `libcrypto.so.3`. The package installs nowhere.

**A package is ported only when its whole dependency closure resolves on
Hummingbird** — not when it merely compiles.

## The build root, per Hummingbird's own documentation

Hummingbird builds in **mock hermetic mode** (network-isolated, dependencies
pre-fetched). Its `mock/mock.cfg` composes the root from the `[fedora]` and
`[fedora-updates]` repositories of a pinned Fedora release, with Hummingbird's
own Pulp repositories shadowing them by priority. Their rebase runbook warns
that if "Hummingbird's own Pulp repos still serve the _old_ toolchain at a
higher priority than the new Fedora repos during the transition window, this
becomes a real chicken-and-egg problem" -- priority ordering is load-bearing.

A rebase rebuilds the core toolchain in strict order: glibc, gcc, llvm,
annobin, libtool.

This factory mirrors that composition: Fedora 44 plus `public-hummingbird` at
higher priority. Measured in the build itself, that root reports

```
buildroot openssl: 3.5.7-2.fc44          -> libcrypto.so.3, matching Hummingbird
177 packages from public-hummingbird-x86_64-rpms
python3-3.14.7-1.hum1                    -> not Rawhide's 3.15
gio-2.0 2.89.3, graphene 1.10.8, pixman 0.46.2
```

Each build prints its root's `openssl-libs`, so the ABI a package compiled
against is visible in the log rather than assumed. That check is what caught
the Rawhide root producing packages needing `libcrypto.so.4`.

## Build order is part of the port

Several ported packages BuildRequire each other, so a flat parallel matrix
cannot build them:

```
mutter       needs gsettings-desktop-schemas >= 51.alpha   (found 50.1)
gnome-shell  needs mutter-devel >= 51~alpha                (no match)
gtk4, mutter needs wayland-protocols >= 1.48
libadwaita, gnome-control-center  need gtk4 >= 4.23.x
```

Builds therefore run in stages, each stage publishing its RPMs into a local
repository the next stage resolves against:

| stage | packages |
| --- | --- |
| 0 | everything with no in-set dependency, plus `wayland-protocols`, `accountsservice`, `gsettings-desktop-schemas` |
| 1 | `gtk4` |
| 2 | `libadwaita`, `mutter` |
| 3 | `gnome-shell`, `gnome-control-center`, `gnome-session`, `gnome-settings-daemon`, `xdg-desktop-portal-gnome` |

This is the same shape as Hummingbird's toolchain ordering, one layer up.

## The bootstrap ladder

Restating it here because the ordering is what keeps getting lost:

1. A new gap is introduced using the **Rawhide build root** — its compiler,
   macros, and BuildRequires establish the first RPM.
2. That RPM is published to the factory's own repository.
3. **Subsequent builds use the factory repository** as the gap-filler for
   cross-package dependencies, so Rawhide supplies progressively less.
4. Consumer images enable the factory repository and Hummingbird. Never
   Rawhide.

Step 3 is what makes the Rawhide root safe: it is a scaffold that is meant to
be designed out, not a permanent dependency source. Bootstrapping in Rawhide
without ever doing step 3 leaves Rawhide's ABI baked into the output, which is
exactly the failure described above.

## Worked example: GNOME 51

Minimums were read from the GNOME 51 release tarballs' `meson.build`, not
inferred from what Rawhide happens to ship.

Already satisfied by Fedora 44 plus Hummingbird:

```
glib2 2.88.0 >= 2.86.0     gjs 1.88.0 >= 1.87.1     pipewire 1.6.2 >= 1.6.0
libei 1.5.0 >= 1.3.901     wayland 1.24.0 >= 1.24   libdrm 2.4.131 >= 2.4.118
graphene 1.10.8 >= 1.10.2  libinput 1.31.0          harfbuzz 12.3.2 >= 8.4.0
cairo 1.18.4 >= 1.18.2     meson 1.10.2 >= 1.8.0    libnm 1.56.0 >= 1.52.0
upower 1.91.1 >= 1.90.6    libdisplay-info 0.3.0    g-i 1.86.0 >= 1.84
```

Genuine gaps, which must themselves be built:

| package | available | GNOME 51 needs | required by |
| --- | --- | --- | --- |
| `gsettings-desktop-schemas` | 50.1 | >= 51.alpha | mutter |
| `accountsservice` | 23.13.9 | >= 26.27.3 | gnome-control-center |
| `pango` | 1.57.1 | >= 1.58.0 | gtk4 |

`wayland-protocols` was previously listed here as a gap at 1.47. That is no
longer true: Fedora 44 carries 1.49, the same version we fork, so gtk4's
`>= 1.48` resolves without us. We still build it, which costs nothing and
keeps it under this factory's control, but it is not what is blocking anything.

The `pango` row was not predicted from the meson files; it was found by the
stage-1 build failing on `No match for argument: pkgconfig(pango) >= 1.58.0`.
That is the expensive way to learn it. The `preflight` job in
`rebuild-rpms.yml` now resolves every recipe's BuildRequires in the real build
root on each run, so the whole gap list arrives at once rather than one entry
per half-hour round. Its output is a worklist, not a gate: a later-stage
package requiring something an earlier stage has not built yet shows up there
too, and is not a gap.

Note that `glib2` is **not** a blocker. GNOME 51 asks for 2.86, not the 2.89
that Rawhide ships; assuming otherwise sent an earlier attempt down a dead end.

## Open, and deliberately not asserted

- **Step 3 of the ladder is implemented but only partly proven.**
  `rebuild-rpms.yml` now builds in a Fedora 44 container with Hummingbird's
  Pulp repository layered over it, and the job prints `buildroot openssl` as
  its own check: run 33243934353 reported `3.5.7-2.fc44`, which is
  `libcrypto.so.3` — Hummingbird's ABI, not Rawhide's `libcrypto.so.4`. What
  is not proven is that output linked against that root installs cleanly on a
  Hummingbird image; nothing has tested that yet.
- **Nothing sets a Hummingbird-style disttag or `.N` release bump.** Built
  RPMs carry Fedora's `.fc44`, so they neither identify as this factory's nor
  sort against Fedora as Hummingbird's own rebuilds do.
- **GNOME 51 has not yet compiled end to end.** The Fedora 44 plus
  Hummingbird root is confirmed correct. Run 33243934353 built
  `gnome-session`, `gnome-settings-daemon` and `xdg-desktop-portal-gnome`,
  but that does not demonstrate staging: those three resolve entirely against
  Fedora 44. Staging was broken twice over, by the same kind of mistake in two
  places. The guard deciding whether to build the local `[stages]` repository
  used a non-recursive glob against a directory where `download-artifact` had
  nested the RPMs one level down, so it silently found nothing. Fixing that
  exposed the second: `rpmbuild --define "_rpmdir /work/result"` writes to
  `/work/result/<arch>/`, but the upload declared `work/result/*.rpm`, also
  non-recursive. Every artifact this workflow ever produced held only its JSON
  report -- pango built five RPMs and its artifact was 397 bytes.
  `if-no-files-found: error` could not catch it, because the artifact also
  carries `work/reports/*.json`, so one file always matched and the upload
  reported success while shipping nothing. Both globs now recurse and the build
  fails outright if it produced no RPM. The mechanism is still unproven until a
  later-stage package is observed consuming an earlier stage's output.
- **TunaOS Hummingbird (`repo.tunaos.org`) is a different, abandoned project.**
  It is not Red Hat Hummingbird and must not be used. Any leftover reference
  to it is a bug.
