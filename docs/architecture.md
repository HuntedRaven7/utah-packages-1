# Architecture

```mermaid
flowchart TD
  Fedora["Fedora spec + patches (bootstrap)"] --> Spec["RPM recipe"]
  Upstream["Direct upstream release / tag"] --> Verify["Checksum, signature and policy gate"]
  Verify --> Lock["Exact source lock"]
  Spec --> Mock["Mock rebuild matrix"]
  Lock --> Mock
  Mock --> Repo["RPM overlay + repodata"]
  Repo --> Pages["GitHub Pages repository"]
  Repo --> Bootc["Minimal bootc composition"]
  Bootc --> GHCR["Signed GHCR image"]
```

Fedora Rawhide supplies a temporary compatibility build root and initial RPM
recipes, never an update source or runtime package repository for consumer
images. Every RPM source payload is fetched from its configured upstream and
must pass the verification gate before it can reach Mock. The factory builds a
manifest-defined closure in shards on GitHub-hosted runners.
