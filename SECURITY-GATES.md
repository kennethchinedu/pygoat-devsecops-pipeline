# Security Gates — pygoat

## 1. Purpose

This document is for developers whose PR is blocked by a security gate. It explains why the gate failed, what must be fixed or accepted, and how to get unblocked safely.

Security gates prioritize real risk using confidence, and blast radius rather than treating every scanner finding equally.

## 2. Gates per stage

| Stage      | Scanner                  | FAIL when                                                                                                                                                                                        | WARN when                                                                                                           | INFO                                                                                    | Why this split                                                                    |
| ---------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Pre-commit | Secret scan              | Secret detected, because credentials must not enter commits.                                                                                                                                     | —                                                                                                                   | —                                                                                       | Stop secrets as early as possible.                                                |
| PR         | Secret scan              | Secret detected, because pre-commit can be bypassed with `--no-verify`.                                                                                                                          | —                                                                                                                   | —                                                                                       | The PR gate prevents bypassing local protection.                                  |
| PR         | SCA                      | **New** high/critical vulnerability with a fix available, because an actionable dependency vulnerability should block. **KEV always fails**, because active exploitation increases blast radius. | Existing finding or high/critical with no fix, because it was not introduced by the PR or cannot yet be remediated. | Low-severity findings, because their immediate impact is limited.                       | Fail actionable new risk; manage legacy/no-fix risk through ownership and expiry. |
| PR         | SAST                     | **New** finding from an ERROR-severity Semgrep rule, because attacker-controlled input reaching a dangerous sink (SQL, `eval`, shell, deserialisation) can be exploited directly. | WARNING-severity findings, or ERROR findings that already exist on master, because they need manual validation or were not introduced by the PR. | Informational/code-quality findings, because they have no demonstrated security impact. | Fail on new high-severity defects; manage existing ones through Code Scanning and the allowlist. |
| PR         | IaC                      | Security-critical misconfiguration such as missing Dockerfile `USER`, because the container runs as root and increases compromise impact.                                                        | Lower-risk configuration issues, because they have lower immediate impact.                                          | Informational hardening recommendations.                                                | Privilege and blast radius determine whether configuration should block.          |
| Post-merge | Image scan               | **New** high/critical vulnerability with a fix available, because the vulnerable artifact is about to be deployed.                                                                               | Existing or high/critical with no fix, because it was not introduced by the change or cannot yet be remediated.     | Informational package/hardening findings.                                               | Scan the actual artifact; fail new actionable vulnerabilities.                    |
| Nightly    | Full-history secret scan | Alert security + rotate the key, because a live secret such as the planted `AKIA…` key may remain exposed in Git history.                                                                        | —                                                                                                                   | Historical/non-live matches requiring investigation.                                    | Full-history scanning catches secrets that were committed and later deleted.      |
| Staging    | DAST                     | Confirmed high-impact vulnerability, because the running application can be attacked before production.                                                                                          | Lower-confidence or lower-impact finding, because it needs validation before blocking release.                      | Informational observations.                                                             | DAST requires a running application and therefore blocks promotion, not the PR.   |

**SCA "new only"** means the PR fails only for vulnerabilities introduced by the change; existing findings do not suddenly turn an otherwise unrelated PR red. A vulnerability in CISA's **KEV** catalog overrides this rule and fails because it is known to be actively exploited.

**SAST known gap:** the `introduction/views.py:157` SQL injection is not matched by any `p/python` rule, because the query is built on one line and executed five lines later. A green SAST check does not mean no SQL injection. A custom Semgrep rule for it is planned in J04.

## 3. Rollout

1. **Warn:** run the new gate and publish findings without blocking.
2. **Fail new:** block newly introduced high-risk findings once the gate is trusted and tuned.
3. **Expand:** progressively enforce the remaining gates.
4. **Baseline:** existing findings remain tracked but do not block unrelated PRs.
5. **KEV override:** KEV vulnerabilities fail regardless of the normal threshold unless security approves an explicit exception.

**Current status:** SAST is at step 1 (warn) since 2026-10-10: Semgrep runs on every PR and push to master, all findings go to Code Scanning, nothing blocks. Step 2 starts when the gate compares against the PR's base commit (`--baseline-commit`).

## 4. Allowlist (risk acceptance)

The allowlist is version-controlled in the repository and changes require a PR.

Each entry contains five fields:

```yaml
- id: CVE-2023-32681
  location: "requirements.txt"
  reason: "no proxy in use, upgrade breaks a test"
  owner: "ken"
  expires: "2026-12-31"
```

**Approved by security (CODEOWNERS).**

**Require review from Code Owners** must be enabled so allowlist changes cannot merge without the designated owner.

**Expired → gate fails.**

**Never allowlisted: live secrets.**

## 5. Blocked? Unblocked in under 1 hour

1. Read the gate result and identify the exact finding.
2. Fix the finding and rerun the gate.
3. If it is an accepted risk or false positive, submit a time-bound allowlist PR.
4. **Security responds within 1 h.**
5. For an urgent release, use break-glass: `gh pr merge --admin`. The bypass must be **logged in the PR**, justified, and followed by remediation or an allowlist PR.

## 6. Where findings go

Scanner results are uploaded as **SARIF** to GitHub **Code Scanning**.

* **FAIL** → blocks the relevant gate or promotion.
* **WARN** → visible to developers for review but does not block.
* **INFO** → recorded for visibility and investigation.
