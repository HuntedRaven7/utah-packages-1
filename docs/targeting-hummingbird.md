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

## The bootstrap ladder

`README.md` states the policy and `docs/architecture.md` draws it. Restating
it here because the ordering is what keeps getting lost:

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
| `wayland-protocols` | 1.47 | >= 1.48 | gtk4, mutter |
| `accountsservice` | 23.13.9 | >= 26.27.3 | gnome-control-center |

Note that `glib2` is **not** a blocker. GNOME 51 asks for 2.86, not the 2.89
that Rawhide ships; assuming otherwise sent an earlier attempt down a dead end.

## Open, and deliberately not asserted

- **Step 3 of the ladder is not implemented.** `rebuild-rpms.yml` builds in a
  Rawhide container and enables nothing else — not the factory repository,
  not Hummingbird. Until it does, output carries Rawhide's ABI regardless of
  intent.
- **Nothing sets a Hummingbird-style disttag or `.N` release bump.** Built
  RPMs carry Fedora's `.fc46`, so they neither identify as this factory's nor
  sort against Fedora as Hummingbird's own rebuilds do.
- **Whether GNOME 51 compiles against Fedora 44 is untested.** Every declared
  minimum is met, but meson enforces more than a spec pins.
- **TunaOS Hummingbird (`repo.tunaos.org`) is a different, abandoned project.**
  It is not Red Hat Hummingbird and must not be used. Any leftover reference
  to it is a bug.
