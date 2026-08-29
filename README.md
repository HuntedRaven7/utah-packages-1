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

See [architecture](docs/architecture.md) and [contributing](docs/contributing.md).
