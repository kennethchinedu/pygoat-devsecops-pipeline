# SCA evaluation — pygoat

What was run, what each tool saw, and which one the pipeline trusts and why.
Everything below comes from runs on this repo (2026-10-11/12) unless marked **(from docs)**.

**Bottom line:** all SCA tools do the same job — match installed components against advisory
databases — but they use **different data** and give **different answers** on the same code.
A gate is only as precise as the tool *and* the severity source it trusts. Pygoat's gate uses
**Snyk** (policy fit), **Trivy** for the SBOM (inventory), and **GitHub attestations** to prove
what shipped.

## 1. Tools run on pygoat

| | pip-audit 2.10 | Trivy 0.75 | Snyk CLI 1.1308 |
|---|---|---|---|
| Reads | `requirements.txt` (manifest) or a venv | manifest, filesystem, **image** (OS + language) | **image** (OS + language + any manifests inside it) |
| Data source | PyPI advisory DB / OSV (`PYSEC-…`) | Trivy DB built from NVD, GHSA, distro feeds (`CVE-…`) | Snyk's own DB, researched in-house (`SNYK-…`) |
| Severity per finding | ❌ none | ✅ (NVD/vendor) | ✅ (Snyk's own scoring) |
| Fix version | ✅ per ID | ✅ per CVE | ✅ **per package** ("upgrade X to Y") |
| OS packages | ❌ | ✅ | ✅ |
| Account needed | no | no | **yes** (token) |
| Cost | free | free | free tier; service-account tokens are paid |

### Same code, different numbers
| Scope | pip-audit | Trivy | Snyk |
|---|---|---|---|
| `requirements.txt` (34 packages) | 247 rows → **141 unique** | **137** | **159** (in image) |
| Debian OS packages (slim image) | n/a | **354** | **148** |
| Vulnerable Python packages | 14 | 14 | 14 + 3 extra manifests in the image |

Why they differ:
- **Different databases.** Per package, counts diverged (cryptography 13 vs 11, oauthlib 1 vs 2,
  pillow, pyjwt, werkzeug). No single scanner is "the truth".
- **Counting units.** Trivy counts package × CVE (one glibc CVE on `libc6` and `libc-bin` = 2);
  Snyk groups them into one issue.
- **Duplicates.** pip-audit printed the same ID twice for many packages (247 rows, 141 unique).
  **Deduplicate before reporting a number.**
- **Severity source.** Snyk largely uses Debian's own severities for OS packages (123 of 148
  "low"); Trivy leans on NVD scores.

## 2. Findings that changed the design

1. **"Fail on HIGH" needs to say *whose* HIGH.** `Jinja2==2.10` (CVE-2019-10906, sandbox escape):
   Trivy **HIGH**, Snyk **MEDIUM**. A Snyk gate at `--severity-threshold=high` let it through;
   a Trivy gate would have blocked it. The policy names its severity source.
2. **Remove before you accept.** The image scan showed 2,989 OS findings; 2,474 were
   `linux-libc-dev` (kernel headers) pulled in by `python3-dev`/`libpq-dev`, which nothing
   needed (`psycopg2-binary` ships compiled). Removing two packages → **354 (−88%)**. A
   `.dockerignore` then removed 3 lab `requirements.txt` files that `COPY . .` had shipped →
   **110 → 76** high/critical. Neither needed an allowlist entry.
3. **Old repos are not uniformly vulnerable.** 19 of 33 packages had no known issue; risk sits in
   code that parses untrusted input (web frameworks, HTTP clients, YAML/SQL/image parsers, crypto).
4. **End-of-life changes the fix.** Django 4.2 LTS left support in April 2026; newer advisories
   list fixes only in 5.2/6.0 — the fix is a major upgrade, not a pin bump.
5. **No-fix findings exist** (`pyjwt` PYSEC-2025-183; all 2,989 Debian findings were
   `affected`/`fix_deferred`/`will_not_fix`). Policy: warn, don't fail (`--fail-on=upgradable`).

## 3. The gate (live in `.github/workflows/sca.yml`)

- `snyk container test` on the built image, `--severity-threshold=high --fail-on=upgradable`:
  fail on high/critical **with a fix**; no-fix → not blocking.
- SARIF → GitHub Code Scanning (`if: always()`), `snyk container monitor` on master.
- **Allowlist = `.snyk`**: 76 baseline entries, reason + owner (in the reason text, no owner
  field) + `expires: 2026-12-31`.
- Proven: plant `paramiko==2.4.0` (auth bypass, critical) → red → 7-day ignore → green →
  expired → red (runs 38151901148 → 38152126927 → 38152298388).
- CLI installed with `npm i -g snyk@1.1308.0` (pinned) rather than `snyk/actions`, to keep the
  Actions allow-list at GitHub-owned + hadolint.

### Snyk limitations found
- **Expired ignores are silent.** The finding simply reappears; the log never says "exception
  expired". Add a separate check that lists past-`expires` entries so developers know why.
- **No baseline/diff mode in the CLI** (unlike Semgrep's `--baseline-commit`), so existing issues
  must be baselined in `.snyk` — 76 entries to maintain.
- **Personal token** in CI: the pipeline acts as one person; a service account is a paid feature.
- `snyk test` doesn't show in the web UI; only `monitor` creates projects.

### Automation pitfall found
GitHub's API returns **at most 100 results per page**. Pulling Code Scanning alert IDs without
`--paginate` returned exactly 100 alerts → 66 IDs instead of 76; the baseline would have been
incomplete and the gate still red. Treat a round 100/30/50 as "there is another page".

## 4. Supply chain (live in `.github/workflows/release.yml`)

- Image pushed to GHCR **by digest**, signed with **cosign keyless** (GitHub OIDC → Fulcio,
  Rekor log), cosign binary pinned and **checksum-verified**.
- **CycloneDX SBOM** (Trivy) as a build artifact and as a signed attestation; **SLSA provenance**
  via `actions/attest-build-provenance`. Pipeline level: **SLSA L2**; L3 needs provenance
  generated outside the build's control (isolated reusable workflow).
- **Verify job:** `cosign verify` (identity = this repo's `release.yml`, issuer = GitHub) **and**
  `gh attestation verify` (requires SLSA provenance).
- **Lesson:** with signing and provenance removed but the SBOM attestation left in, **`cosign
  verify` passed** — it accepted the SBOM attestation as a signature from the right identity.
  Only the provenance check failed (run 38183300188). Verify *what* was signed, not only *who*
  (`cosign verify-attestation --type slsaprovenance1`).
- **SBOM limits:** image SBOM = 177 components (121 deb + 55 pypi); Python packages show
  `dependsOn: []` because installed packages don't record who pulled them in — a lockfile-based
  SBOM would.

## 5. Dependency confusion (demo in a private workspace)

Two local sources: "private" `hexpay-utils 1.2.0`, "public" `hexpay-utils 99.0.0` with a
`setup.py` payload. With both sources pip installed **99.0.0** and the payload ran at **install**
time as the developer; with the private source only, 1.2.0 and no payload. A cached wheel hid the
payload on one run — wheels don't execute code at install, source builds do.

Fixes, layered: one index (`--index-url` to a proxy, never `--extra-index-url`); **pinned versions
with hashes** (`--require-hashes`); reserve internal names publicly; proxy rules; `--only-binary
:all:` narrows install-time execution. **Pygoat today:** versions pinned, **no hashes** (pip-audit
warns about this on every run) — to fix.

## 6. Not run

| Tool | Notes |
|---|---|
| **OWASP Dependency-Check** | Skipped by decision: built for Java/.NET; Python analyzers are experimental; first run downloads the full NVD (hours without a free NVD API key). For a Python stack, pip-audit/Trivy/Snyk fit better. |
| **Dependabot** (from docs) | GitHub-native: alerts from GHSA, automatic security-update PRs, version-update PRs. Already on for Actions here. Doesn't gate by itself — pair with `dependency-review-action` on PRs. Free. |
| **Checkmarx SCA** (from docs) | Part of Checkmarx One alongside its SAST; reachability ("is the vulnerable function used?") and licence policy. Commercial. |
| **Veracode SCA** (from docs) | Agent/CLI and upload-based scanning in Veracode's platform; vulnerable-method analysis; licence policy. Commercial. |
| **Black Duck** (from docs) | Strongest on **licence compliance** and open-source governance; scans source and binaries against its own knowledge base. Commercial, common in regulated/enterprise shops. |

## 7. Recommendation

| Need | Use |
|---|---|
| PR gate on vulnerable dependencies | Snyk (policy flags + `.snyk` expiry), or Trivy with `--severity --exit-code` where an account isn't wanted |
| Inventory / SBOM | Trivy → CycloneDX, attested and signed |
| Second opinion on Python | pip-audit (free, PyPA-maintained, fast) |
| Continuous watch after merge | `snyk monitor` + Dependabot alerts |
| Next fixes | hashes in requirements (`pip-compile --generate-hashes`); Django 5.2 upgrade plan; expired-ignore check; `verify-attestation --type slsaprovenance1` |
