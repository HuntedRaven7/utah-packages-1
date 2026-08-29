# Hummingbird GitHub

A GitHub-hosted RPM and bootc image factory inspired by Hummingbird's goals:
fast upstream tracking, minimal images, reproducible build roots, and verifiable
supply-chain metadata.

It does **not** make consumer images install Fedora Rawhide directly. It
rebuilds selected Rawhide source RPMs on GitHub-hosted runners, publishes a
coherent overlay repository, and composes images from that repository.

## Initial scope

`config/bootstrap-packages.txt` is a dependency-first source RPM set covering
the Fedora components that blocked Utah: FUSE, NTFS, device-mapper persistent
data, UDisks, librsvg, glycin, GVFS, GNOME, Firefox, and Distrobox.

The RPM workflow locks source RPM checksums, rebuilds them in Mock, creates
repodata, keylessly signs `repomd.xml` using GitHub OIDC/Cosign, and deploys it
to GitHub Pages. Pull requests never publish RPMs or images.

## Import and fork upstream packages

`Import Rawhide package` imports a Fedora dist-git's `rawhide` branch into
`packages/<name>/`, recording its remote, immutable commit, tree ID, and import
time in `.hummingbird-upstream.json`. The workflow opens a pull request so
downstream patches are explicit and reviewable before the package enters a
rebuild set.

This is an in-factory fork with upstream provenance. Mirroring each source into
an independent GitHub repository is intentionally optional: GitHub Actions'
`GITHUB_TOKEN` cannot create repositories. It can be added later with a
dedicated, narrowly scoped repository-creation credential.

See [architecture](docs/architecture.md) and [contributing](docs/contributing.md).
