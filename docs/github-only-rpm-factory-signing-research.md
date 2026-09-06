# Copr-free, GitHub-only RPM factory: signing and provenance research

*Research date: 2026-09-05. Scope is deliberately limited to first-party
documentation and source: GitHub and GitHub Actions, Sigstore/Cosign, RPM/DNF,
and Project Bluefin/ublue-os workflow source. “GitHub-only” below means that
GitHub Actions is the build service and GitHub Pages/GHCR are distribution
surfaces; it does **not** mean that every verification mechanism is understood
by DNF.*

## Decision in one paragraph

Use three complementary layers, with the native RPM layer as the install-time
authority:

1. Sign every released RPM with an RPM-native OpenPGP signature and publish its
   public key. This is the required layer for ordinary `dnf gpgcheck=1`
   consumers, because RPM package signatures are OpenPGP entries in the RPM
   signature/header format and DNF's `gpgcheck` checks package GPG signatures.
   [RPM signature format, `rpm-software-management/rpm:docs/manual/signatures_digests.md:7-37`](https://github.com/rpm-software-management/rpm/blob/master/docs/manual/signatures_digests.md#L7-L37)
   [DNF `gpgcheck`, `rpm-software-management/dnf:doc/conf_ref.rst:985-995`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L985-L995)
2. Generate GitHub SLSA provenance for each final, *already RPM-signed* `.rpm`
   and retain the resulting GitHub attestation/bundle. This ties the exact
   signed file digest to the GitHub Actions build identity, but it is a
   separate in-toto/Sigstore artifact-verification mechanism.
   [GitHub action overview, `actions/attest-build-provenance:README.md:3-20`](https://github.com/actions/attest-build-provenance/blob/main/README.md#L3-L20)
3. Optionally use keyless `cosign sign-blob` for independently verifiable RPM
   or repository-metadata sidecar bundles. It is useful to people and
   automation that run Cosign, but must not replace the RPM OpenPGP signature
   when normal DNF compatibility is a requirement.
   [Cosign blob verification material, `sigstore/cosign:doc/cosign_verify-blob.md:7-13`](https://github.com/sigstore/cosign/blob/main/doc/cosign_verify-blob.md#L7-L13)

That is compatible with a Copr-free factory. It is not necessary to run a Copr
build service to produce a repository; `createrepo_c` can create the metadata
from the built RPMs and GitHub can publish the resulting directory or OCI image.
The present Utah workflow does exactly the build/repository-metadata portion,
but intentionally sets `gpgcheck=0` in both its staged build repo and its
consumer test repo. [Utah staged-repo configuration, `projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:304-308`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L304-L308)
[Utah consumer test configuration, `projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:1421-1438`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L1421-L1438)
[Utah OCI repository publication, `projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:1478-1519`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L1478-L1519)

## 1. Native RPM OpenPGP signing: the DNF-compatible mechanism

`rpmsign --addsign` generates and inserts an OpenPGP signature in the package;
`--resign` replaces prior signatures. RPM 6 permits an arbitrary number of V6
signatures, while RPM V4 compatibility has only one V4 signature and depends on
a V4-known algorithm. [RPM `rpmsign` operations and compatibility,
`rpm-software-management/rpm:docs/man/rpmsign.1.scd:13-29`](https://github.com/rpm-software-management/rpm/blob/master/docs/man/rpmsign.1.scd#L13-L29)
[RPM V4/V6 compatibility details, `rpm-software-management/rpm:docs/man/rpmsign.1.scd:72-93`](https://github.com/rpm-software-management/rpm/blob/master/docs/man/rpmsign.1.scd#L72-L93)

RPM requires a signer identity: configure `%_openpgp_sign_id` to the signing
key fingerprint or key ID, or pass `--key-id`; GnuPG is the default OpenPGP
implementation and `%_gpg_path` selects a non-default keyring. The RPM manual
also gives `rpmsign --addsign PACKAGE` as the basic operation.
[RPM signing configuration and example,
`rpm-software-management/rpm:docs/man/rpmsign.1.scd:114-157`](https://github.com/rpm-software-management/rpm/blob/master/docs/man/rpmsign.1.scd#L114-L157)

The RPM verifier enumerates the relevant RPM tags (`OPENPGP`, legacy `PGP` and
`GPG`, RSA/DSA header signatures) as signature items and describes them as
OpenPGP signatures. This is the format boundary that a DNF/RPM consumer
recognizes. [RPM verifier signature tags,
`rpm-software-management/rpm:lib/rpmvs.cc:29-86`](https://github.com/rpm-software-management/rpm/blob/master/lib/rpmvs.cc#L29-L86)
[RPM verifier OpenPGP classification,
`rpm-software-management/rpm:lib/rpmvs.cc:320-346`](https://github.com/rpm-software-management/rpm/blob/master/lib/rpmvs.cc#L320-L346)

### Evidence from a production CI signing flow

Serial Studio provides a concrete GitHub Actions example: its workflow maps
`GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`, and `GPG_KEY_ID` from GitHub Actions
secrets, creates a locked-down GnuPG home, imports the private key with
`gpg --batch --import`, prepares non-interactive loopback signing macros, then
calls `rpmsign --addsign` and checks the signature with `rpm -Kv`.
[Secret import and RPM macro setup, `Serial-Studio/Serial-Studio:.github/workflows/ci.yml:582-611`](https://github.com/Serial-Studio/Serial-Studio/blob/f75236b097fc405087eb77bc12c6ad1a0b908b03/.github/workflows/ci.yml#L582-L611)
[RPM signing and verification, `Serial-Studio/Serial-Studio:.github/workflows/ci.yml:1060-1065`](https://github.com/Serial-Studio/Serial-Studio/blob/f75236b097fc405087eb77bc12c6ad1a0b908b03/.github/workflows/ci.yml#L1060-L1065)

Store an ASCII-armored private-key export in a protected GitHub Actions
environment/repository secret (and its passphrase, if any, separately), expose
each only through the release job's `env`, and never echo them. The Serial
Studio example is a usable baseline, but a factory should set and later remove
a job-local `GNUPGHOME` rather than using the runner's default home directory.
[GitHub repository/environment secret creation, `github/docs:content/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets.md:28-95`](https://github.com/github/docs/blob/main/content/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets.md#L28-L95)
[GitHub secret environment-variable guidance, `github/docs:content/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets.md:195-214`](https://github.com/github/docs/blob/main/content/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets.md#L195-L214)

For GitHub Actions, adapt that *sequence*, not any key value: make the private
OpenPGP export a protected GitHub Actions environment/repository secret; create
a job-local `GNUPGHOME`; import it non-interactively; set the immutable
fingerprint as `%_openpgp_sign_id`; run `rpmsign --addsign` over the final RPMs;
then destroy the job-local keyring. RPM's own command source rejects signing
when no `%_openpgp_sign_id` is configured. [RPM signer identity enforcement,
`rpm-software-management/rpm:tools/rpmsign.cc:132-192`](https://github.com/rpm-software-management/rpm/blob/master/tools/rpmsign.cc#L132-L192)

### Reference protected release-job shape

Put `RPM_GPG_PRIVATE_KEY` (an ASCII-armored secret-key export) and, if used,
`RPM_GPG_PASSPHRASE` in a protected `rpm-production` GitHub environment.
Keep the full `RPM_GPG_FINGERPRINT` in a non-secret repository variable or
workflow configuration; do not select a key by a mutable user ID. For the
Fedora/RPM 4 GnuPG backend, a signing job can use the following shape after
the final RPMs have been built:

```yaml
environment: rpm-production
env:
  GNUPGHOME: ${{ runner.temp }}/rpm-signing-gnupg
  RPM_GPG_PRIVATE_KEY: ${{ secrets.RPM_GPG_PRIVATE_KEY }}
  RPM_GPG_PASSPHRASE: ${{ secrets.RPM_GPG_PASSPHRASE }}
  RPM_GPG_FINGERPRINT: ${{ vars.RPM_GPG_FINGERPRINT }}
run: |
  set -euo pipefail
  install -d -m 700 "$GNUPGHOME"
  printf '%s' "$RPM_GPG_PRIVATE_KEY" | gpg --batch --import
  passphrase_file="$RUNNER_TEMP/rpm-gpg-passphrase"
  umask 077
  printf '%s' "$RPM_GPG_PASSPHRASE" > "$passphrase_file"
  rpmsign --addsign \
    --define "_gpg_path $GNUPGHOME" \
    --define "_gpg_name $RPM_GPG_FINGERPRINT" \
    --define "_gpg_sign_cmd_extra_args --batch --pinentry-mode loopback --passphrase-file $passphrase_file" \
    repository/**/*.rpm
  rm -f "$passphrase_file"
  rm -rf "$GNUPGHOME"
```

Use a `find`/array rather than the illustrative glob where the runner shell
does not enable recursive globbing. Check every package with `rpm --checksig`
against the separately published public key before releasing it. For RPM 6,
prefer its implementation-independent `%_openpgp_sign_id` configuration to
the legacy GnuPG `%_gpg_name` macro. [RPM configuration guidance,
`rpm-software-management/rpm:docs/man/rpmsign.1.scd:114-157`](https://github.com/rpm-software-management/rpm/blob/master/docs/man/rpmsign.1.scd#L114-L157)

Do not put private-key material, a passphrase, or a derived key dump in logs,
artifacts, workflow YAML, or this repository. Publish only the public key and
its out-of-band verified fingerprint. If repository metadata signing is also
enabled, treat it as a second OpenPGP trust configuration: DNF states that
`repo_gpgcheck` verifies metadata and stores metadata-verification keys
separately from package-signature keys. [DNF metadata-key separation,
`rpm-software-management/dnf:doc/conf_ref.rst:1133-1144`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L1133-L1144)

## 2. GitHub artifact provenance for arbitrary RPM files

`actions/attest-build-provenance@v4` is now a compatibility wrapper around
`actions/attest`; GitHub recommends new integrations use `actions/attest`.
[Wrapper status, `actions/attest-build-provenance:README.md:35-42`](https://github.com/actions/attest-build-provenance/blob/main/README.md#L35-L42)

GitHub states that artifact attestations by themselves provide **SLSA v1.0
Build Level 2**. Building and attesting in a known, vetted reusable workflow
can meet **SLSA v1.0 Build Level 3**; this is a property of the complete
workflow design and verification policy, not a switch in the action.
[GitHub SLSA levels, `github/docs:content/actions/concepts/security/artifact-attestations.md:16-20`](https://github.com/github/docs/blob/main/content/actions/concepts/security/artifact-attestations.md#L16-L20)
[GitHub reusable-workflow requirements, `github/docs:content/actions/how-tos/secure-your-work/use-artifact-attestations/increase-security-rating.md:24-70`](https://github.com/github/docs/blob/main/content/actions/how-tos/secure-your-work/use-artifact-attestations/increase-security-rating.md#L24-L70)

For a binary file, GitHub documents `id-token: write`, `contents: read`, and
`attestations: write`, then `actions/attest@v4` with `subject-path` after the
build. [GitHub binary-attestation workflow,
`github/docs:content/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations.md:33-53`](https://github.com/github/docs/blob/main/content/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations.md#L33-L53)
The action additionally documents `artifact-metadata: write` as the permission
to create the artifact storage record. [Action permission mechanics,
`actions/attest:README.md:61-88`](https://github.com/actions/attest/blob/main/README.md#L61-L88)

This supports RPMs without an RPM-specific adapter: `subject-path` accepts a
path/glob/list, the implementation filters selected paths only by “is a file,”
then computes the configured digest; it has no filename-extension test. Thus
`dist/*.rpm` is an ordinary binary-file subject (up to the documented
1,024-subject cap), rather than a special package type.
[Subject inputs and limit, `actions/attest-build-provenance:action.yml:8-30`](https://github.com/actions/attest-build-provenance/blob/main/action.yml#L8-L30)
[Generic file handling, `actions/attest:src/subject.ts:108-154`](https://github.com/actions/attest/blob/main/src/subject.ts#L108-L154)

With no SBOM or custom predicate inputs, `actions/attest` selects provenance
mode and auto-generates a SLSA build-provenance predicate. Its signed
attestations bind named subjects and digests to predicates in in-toto format;
the attestation uses a short-lived Sigstore certificate and is associated with
the initiating repository through GitHub's attestation API.
[Action modes, `actions/attest:README.md:44-55`](https://github.com/actions/attest/blob/main/README.md#L44-L55)
[In-toto/Sigstore/API mechanics, `actions/attest:README.md:6-28`](https://github.com/actions/attest/blob/main/README.md#L6-L28)

For end users or CI, the documented binary command is:

```console
gh attestation verify path/to/package.rpm \
  --repo projectbluefin/utah-packages \
  --signer-workflow projectbluefin/utah-packages/.github/workflows/rebuild-rpms.yml
```

The first form is GitHub’s documented binary verification pattern; binding to
the known signer workflow is the stronger policy. [GitHub CLI binary command,
`github/docs:content/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations.md:155-167`](https://github.com/github/docs/blob/main/content/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations.md#L155-L167)
[GitHub CLI policy guidance, `cli/cli:pkg/cmd/attestation/verify/verify.go:46-70`](https://github.com/cli/cli/blob/trunk/pkg/cmd/attestation/verify/verify.go#L46-L70)

The CLI first digests the supplied file, then fetches matching attestations and
verifies them against its enforcement criteria. For a reusable workflow, the
reusable workflow is the signer, so use `--signer-workflow` or
`--signer-repo` for the shared-workflow identity instead of naming only the
caller repository. [CLI artifact loading and verification,
`cli/cli:pkg/cmd/attestation/verify/verify.go:264-307`](https://github.com/cli/cli/blob/trunk/pkg/cmd/attestation/verify/verify.go#L264-L307)
[CLI reusable-workflow rule, `cli/cli:pkg/cmd/attestation/verify/verify.go:64-70`](https://github.com/cli/cli/blob/trunk/pkg/cmd/attestation/verify/verify.go#L64-L70)

The generated attestation is a separate JSON Sigstore bundle, with an
attestation URL/ID and local bundle path exposed as action outputs. It does not
add an RPM header signature. [Attestation outputs,
`actions/attest:README.md:162-178`](https://github.com/actions/attest/blob/main/README.md#L162-L178)
[RPM’s recognized signature format,
`rpm-software-management/rpm:docs/manual/signatures_digests.md:10-20`](https://github.com/rpm-software-management/rpm/blob/master/docs/manual/signatures_digests.md#L10-L20)

## 3. Cosign keyless blob signatures for RPMs

Cosign’s `sign-blob` takes one arbitrary blob/file; its command source calls
the argument a supplied blob and requires exactly one argument. The documented
`--bundle` output contains what is needed to verify the blob.
[Cosign command definition, `sigstore/cosign:cmd/cosign/cli/signblob.go:32-67`](https://github.com/sigstore/cosign/blob/main/cmd/cosign/cli/signblob.go#L32-L67)
[Cosign `--bundle` option, `sigstore/cosign:doc/cosign_sign-blob.md:33-57`](https://github.com/sigstore/cosign/blob/main/doc/cosign_sign-blob.md#L33-L57)

For an RPM, keyless mode is the no-`--key` form, executed in a job granted
`id-token: write`. The upstream Cosign README gives the applicable GitHub
Actions identity-bound pair:

```console
cosign sign-blob package.rpm --bundle package.rpm.sigstore.json --yes
cosign verify-blob package.rpm \
  --bundle package.rpm.sigstore.json \
  --certificate-identity \
  "https://github.com/ORG/REPO/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

[Cosign’s keyless blob example, `sigstore/cosign:README.md:185-195`](https://github.com/sigstore/cosign/blob/main/README.md#L185-L195)

Distribute the matching `.sigstore.json` bundle beside the RPM (and preserve
both immutable files), and require the expected certificate identity *and* OIDC
issuer on verification. Cosign documents that the preferred bundle contains the
signature, certificate, and transparency-log proof; it also requires an
identity/identity-regexp and issuer/issuer-regexp for keyless flows.
[Cosign bundle contents, `sigstore/cosign:doc/cosign_verify-blob.md:7-13`](https://github.com/sigstore/cosign/blob/main/doc/cosign_verify-blob.md#L7-L13)
[Cosign keyless verification constraints,
`sigstore/cosign:doc/cosign_verify-blob.md:56-70`](https://github.com/sigstore/cosign/blob/main/doc/cosign_verify-blob.md#L56-L70)

The current Utah factory is a real example of this sidecar pattern for
repository metadata: after `createrepo_c`, it keylessly signs
`repodata/repomd.xml` and writes `repomd.xml.bundle`. This is valuable
provenance/integrity evidence for a Cosign-aware client, but it remains a
separate bundle and the same workflow uses `gpgcheck=0`; it is not evidence
that DNF consumed the bundle. [Utah metadata Cosign step,
`projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:1426-1438`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L1426-L1438)
[Utah DNF test uses `gpgcheck=0`,
`projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:1450-1466`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L1450-L1466)

There is no supported RPM/DNF consumer path for a Cosign keyless blob bundle
in the reviewed upstreams. Sigstore's open Cosign/RPM integration meta-issue
specifically lists blob signing and `cosign verify` as the currently supported
case, and lists the lack of RPM/DNF support for Cosign keyless signatures and
transparency logs as gaps. Consequently, the published end-user instruction is
the explicit `cosign verify-blob` command above—not a `dnf` plugin or a
`gpgcheck` equivalent. [Sigstore Cosign/RPM integration status,
`sigstore/cosign#3523`](https://github.com/sigstore/cosign/issues/3523)

### Why keyless Cosign and GitHub attestations cannot satisfy `dnf gpgcheck`

This is a format-and-verifier conclusion, not an assertion that either project
tries to modify RPM metadata: RPM recognizes OpenPGP values placed in the RPM
signature/header tags, whereas Cosign `verify-blob` consumes an input file plus
a detached bundle. Therefore neither a GitHub attestation nor a Cosign bundle
causes RPM’s OpenPGP-header verifier to regard an unsigned RPM as package
signed. [RPM signature/header locations,
`rpm-software-management/rpm:docs/manual/signatures_digests.md:10-34`](https://github.com/rpm-software-management/rpm/blob/master/docs/manual/signatures_digests.md#L10-L34)
[Cosign detached verification inputs,
`sigstore/cosign:doc/cosign_verify-blob.md:7-31`](https://github.com/sigstore/cosign/blob/main/doc/cosign_verify-blob.md#L7-L31)
[DNF package-signature check definition,
`rpm-software-management/dnf:doc/conf_ref.rst:985-995`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L985-L995)

Accordingly, a keyless-only release is viable only where the consumer
explicitly performs `cosign verify-blob` or `gh attestation verify` before
installation, or where `gpgcheck` is disabled. It is **not** a drop-in
substitute for a standard repository configured with `gpgcheck=1`. Enabling
`repo_gpgcheck` is also not a substitute: it verifies repository metadata, not
the RPM package signature, and uses a separate key store.
[DNF `repo_gpgcheck` scope,
`rpm-software-management/dnf:doc/conf_ref.rst:1133-1144`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L1133-L1144)

## 4. Exact Bluefin/ublue container-signing model (and why it differs)

### Current Project Bluefin

Bluefin’s caller workflow delegates to
`projectbluefin/actions` and grants `id-token: write` and
`attestations: write`. [Bluefin reusable-build caller,
`projectbluefin/bluefin:.github/workflows/build-image-testing.yml:38-67`](https://github.com/projectbluefin/bluefin/blob/main/.github/workflows/build-image-testing.yml#L38-L67)
The shared build workflow pushes the image, then invokes the
`sign-and-publish` composite action with `signing-mode: keyless`.
[Shared build publication and signing call,
`projectbluefin/actions:.github/workflows/reusable-build.yml:449-457`](https://github.com/projectbluefin/actions/blob/main/.github/workflows/reusable-build.yml#L449-L457)
[Keyless call inputs, `projectbluefin/actions:.github/workflows/reusable-build.yml:558-573`](https://github.com/projectbluefin/actions/blob/main/.github/workflows/reusable-build.yml#L558-L573)

That action checks for the Actions OIDC request URL in keyless mode, signs the
immutable OCI image digest without a key argument, and verifies using both a
Project Bluefin workflow-identity regular expression and the GitHub Actions
OIDC issuer. [OIDC precondition,
`projectbluefin/actions:bootc-build/sign-and-publish/action.yml:64-74`](https://github.com/projectbluefin/actions/blob/main/bootc-build/sign-and-publish/action.yml#L64-L74)
[Keyless sign and verify commands,
`projectbluefin/actions:bootc-build/sign-and-publish/action.yml:88-134`](https://github.com/projectbluefin/actions/blob/main/bootc-build/sign-and-publish/action.yml#L88-L134)
It also creates GitHub SBOM and build-provenance attestations for the OCI
subject. [SBOM and provenance attestations,
`projectbluefin/actions:bootc-build/sign-and-publish/action.yml:187-194`](https://github.com/projectbluefin/actions/blob/main/bootc-build/sign-and-publish/action.yml#L187-L194)
[Build provenance invocation,
`projectbluefin/actions:bootc-build/sign-and-publish/action.yml:262-268`](https://github.com/projectbluefin/actions/blob/main/bootc-build/sign-and-publish/action.yml#L262-L268)

The action deliberately requests the legacy Cosign `.sig` layout
(`--new-bundle-format=false`) because its source says the
containers/image-based Podman, Skopeo, and `bootc switch` consumers discover
that layout; it checks that the legacy signature tag exists. This is an
OCI-container compatibility choice, not an RPM signature format.
[Legacy OCI signature rationale,
`projectbluefin/actions:bootc-build/sign-and-publish/action.yml:33-48`](https://github.com/projectbluefin/actions/blob/main/bootc-build/sign-and-publish/action.yml#L33-L48)
[Legacy OCI signature assertion,
`projectbluefin/actions:bootc-build/sign-and-publish/action.yml:136-159`](https://github.com/projectbluefin/actions/blob/main/bootc-build/sign-and-publish/action.yml#L136-L159)

Before stable promotion, the shared release workflow resolves immutable
digests, verifies their Cosign certificate identity/issuer, and copies them
with `--preserve-digests`; the comments correctly note that signatures follow
the digest. [Pre-promotion verification,
`projectbluefin/actions:.github/workflows/reusable-execute-release.yml:162-184`](https://github.com/projectbluefin/actions/blob/main/.github/workflows/reusable-execute-release.yml#L162-L184)
[Digest-preserving promotion,
`projectbluefin/actions:.github/workflows/reusable-execute-release.yml:202-217`](https://github.com/projectbluefin/actions/blob/main/.github/workflows/reusable-execute-release.yml#L202-L217)

### Historical/current ublue-os contrast

The current `ublue-os/bluefin` reusable workflow uses **key-based**, rather
than keyless, Cosign signing: it supplies `--key env://COSIGN_PRIVATE_KEY` and
sets that variable from the `SIGNING_SECRET` secret. It separately requests
`id-token: write`/attestation permissions and creates a GitHub image
attestation. [ublue-os/bluefin permissions,
`ublue-os/bluefin:.github/workflows/reusable-build.yml:31-41`](https://github.com/ublue-os/bluefin/blob/main/.github/workflows/reusable-build.yml#L31-L41)
[ublue-os/bluefin secret-backed image signing,
`ublue-os/bluefin:.github/workflows/reusable-build.yml:250-261`](https://github.com/ublue-os/bluefin/blob/main/.github/workflows/reusable-build.yml#L250-L261)
[ublue-os/bluefin GitHub attestation,
`ublue-os/bluefin:.github/workflows/reusable-build.yml:304-310`](https://github.com/ublue-os/bluefin/blob/main/.github/workflows/reusable-build.yml#L304-L310)

This distinction matters: Project Bluefin’s current OCI release policy is an
identity-bound keyless signature over an OCI digest; older ublue-os Bluefin
uses a stored Cosign private key; neither model writes an OpenPGP signature
inside an RPM. The last point follows from the RPM signature format and Cosign
blob/OCI mechanisms cited above, not from an unstated assumption.

## 5. Recommended release policy and order of operations

1. **Build untrusted/PR candidates without release credentials.** Produce RPM
   artifacts and run tests. The existing Utah workflow already uploads built
   RPMs as artifacts after asserting that at least one RPM exists.
   [Utah RPM build and artifact upload,
   `projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:423-441`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L423-L441)
2. **In a protected, main/tag-only release job, import the secret OpenPGP key
   into a job-local keyring and RPM-sign the final RPMs.** Configure the
   fingerprint with `%_openpgp_sign_id`, use `rpmsign --addsign`, and verify
   signatures before publication. This is the only recommendation here that
   supplies DNF’s package-signature mechanism.
   [RPM configuration/operation,
   `rpm-software-management/rpm:docs/man/rpmsign.1.scd:114-157`](https://github.com/rpm-software-management/rpm/blob/master/docs/man/rpmsign.1.scd#L114-L157)
3. **Create repository metadata only from those final signed RPMs, and
   OpenPGP-sign its metadata if enabling `repo_gpgcheck=1`.** Publish the
   public RPM key at a stable URL and configure consumers for `gpgcheck=1`;
   configure metadata verification separately when desired because DNF keeps
   the trust stores separate.
   [DNF package verification,
   `rpm-software-management/dnf:doc/conf_ref.rst:985-995`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L985-L995)
   [DNF metadata verification/key separation,
   `rpm-software-management/dnf:doc/conf_ref.rst:1133-1144`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L1133-L1144)
4. **Attest the final signed RPM bytes** with `actions/attest@v4`
   `subject-path: 'repository/**/*.rpm'`. Record/export the bundle if offline
   or independently hosted verification is needed. Verify with a repository
   plus exact signer-workflow constraint; if signing is moved into a reusable
   workflow, constrain to that reusable workflow/repository.
   [GitHub action invocation,
   `github/docs:content/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations.md:33-53`](https://github.com/github/docs/blob/main/content/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations.md#L33-L53)
   [GitHub CLI reusable-workflow verifier rule,
   `cli/cli:pkg/cmd/attestation/verify/verify.go:64-70`](https://github.com/cli/cli/blob/trunk/pkg/cmd/attestation/verify/verify.go#L64-L70)
5. **Optionally generate a keyless Cosign bundle for each RPM and/or
   `repomd.xml`.** Distribute it adjacent to its subject and document the
   expected GitHub workflow identity and issuer. This adds an OIDC/transparency
   path comparable in spirit to the Bluefin container model, but remains an
   explicit pre-install verification step—not a DNF policy input.
   [Cosign keyless blob example,
   `sigstore/cosign:README.md:185-195`](https://github.com/sigstore/cosign/blob/main/README.md#L185-L195)
   [DNF’s OpenPGP package check,
   `rpm-software-management/dnf:doc/conf_ref.rst:985-995`](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst#L985-L995)

## Gaps and precise conclusions

- The reviewed Project Bluefin/ublue-os workflows show strong container
  signing/provenance patterns and Utah’s current keyless `repomd.xml` bundle,
  but no reviewed workflow inserts native OpenPGP signatures into Utah’s built
  RPMs. The explicit `gpgcheck=0` settings make that limitation observable in
  the current source. [Utah staged configuration,
  `projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:304-308`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L304-L308)
  [Utah consumer configuration,
  `projectbluefin/utah-packages:.github/workflows/rebuild-rpms.yml:1450-1466`](https://github.com/projectbluefin/utah-packages/blob/main/.github/workflows/rebuild-rpms.yml#L1450-L1466)
- There is no safe “keyless RPM-header signature” substitution established by
  the reviewed sources. Native RPM signing is OpenPGP; keyless Cosign and
  GitHub attestations use separate Sigstore/in-toto bundle mechanisms.
  [RPM OpenPGP manipulation,
  `rpm-software-management/rpm:docs/man/rpmsign.1.scd:13-29`](https://github.com/rpm-software-management/rpm/blob/master/docs/man/rpmsign.1.scd#L13-L29)
  [GitHub attestation representation,
  `actions/attest:README.md:175-178`](https://github.com/actions/attest/blob/main/README.md#L175-L178)
- A factory can therefore be Copr-free and GitHub-hosted while retaining
  standard DNF security, but only by accepting an OpenPGP release-signing key
  (preferably protected and short-exposure in the release job) **in addition
  to**, not instead of, keyless provenance/signature evidence.
