# Architecture

```mermaid
flowchart TD
  Rawhide["Fedora Rawhide source RPMs"] --> Lock["Exact source lock"]
  Lock --> Mock["Mock rebuild matrix"]
  Mock --> Repo["RPM overlay + repodata"]
  Repo --> Pages["GitHub Pages repository"]
  Repo --> Bootc["Minimal bootc composition"]
  Bootc --> GHCR["Signed GHCR image"]
```

Fedora Rawhide is an upstream source, never a runtime package repository for
consumer images. The factory builds a manifest-defined closure in shards on
GitHub-hosted runners; expanding to all Rawhide packages is a capacity project,
not a change in the trust model.
