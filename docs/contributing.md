# Contributing

Add source RPM names—not binary RPM names—to `config/bootstrap-packages.txt`.
Keep additions dependency-first. Pull requests validate configuration but cannot
publish packages, pages content, attestations, or image tags.

To bring in an upstream source, use **Actions → Import Rawhide package**. It
imports Fedora dist-git rather than a binary RPM, records the exact Rawhide
commit, and proposes the result through a pull request. Do not modify
`.hummingbird-upstream.json`; re-import when upstream changes.

## Execution environment

Run package builds, generated-source reproduction, and environment-sensitive
validation on the lab's remote Argo cluster. Use the existing
organization-owned FSDK containers for general tooling instead of launching
one-off local Ubuntu or Fedora containers. The digest-pinned Packit image
mirrored into the lab's writable Zot is used only for Packit commands.

Do not install missing tools into a workflow container at runtime. If the
existing FSDK images do not provide a required capability, add that capability
to `projectbluefin/fsdk-containers` so it is signed, scanned, reproducible, and
available to subsequent workflows.
