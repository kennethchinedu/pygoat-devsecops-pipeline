# Security Gates — pygoat

## 1. Purpose

This document is for developers whose PR is blocked by a security gate. It explains why the gate failed, what must be fixed or accepted, and how to get unblocked safely.

Security gates prioritize real risk using confidence, and blast radius rather than treating every scanner finding equally.

## 2. Gates per stage

| Stage      | Scanner                  | FAIL when                                                                                                                                                                                        | WARN when                                                                                                           | INFO                                                                                    | Why this split                                                                    |
| ---------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Pre-commit | Secret scan              | Secret detected, because credentials must not enter commits.                                                                                                                                     | —                                                                                                                   | —                                                                                       | Stop secrets as early as possible.                                                |
| PR         | Secret scan              | Secret detected in the PR's commits (`base..head`), or the scan could not read any commit (fail closed), because pre-commit can be bypassed with `--no-verify`.                                   | —                                                                                                                   | —                                                                                       | The PR gate prevents bypassing local protection.                                  |
| PR         | SCA                      | **New** high/critical vulnerability with a fix available, because an actionable dependency vulnerability should block. **KEV always fails**, because active exploitation increases blast radius. | Existing finding or high/critical with no fix, because it was not introduced by the PR or cannot yet be remediated. | Low-severity findings, because their immediate impact is limited.                       | Fail actionable new risk; manage legacy/no-fix risk through ownership and expiry. |
| PR         | SAST                     | **New** finding from an ERROR-severity Semgrep rule, because attacker-controlled input reaching a dangerous sink (SQL, `eval`, shell, deserialisation) can be exploited directly. | WARNING-severity findings, or ERROR findings that already exist on master, because they need manual validation or were not introduced by the PR. | Informational/code-quality findings, because they have no demonstrated security impact. | Fail on new high-severity defects; manage existing ones through Code Scanning and the allowlist. |
| PR + weekly | SAST (CodeQL)          | — (rollout step 1: reports, not a required check).                                                                                                                                              | New high/critical alert: the CodeQL PR check goes red and the alert opens in Code Scanning.                        | Lower-severity alerts.                                                                   | Dataflow follows input across functions and files; it found passwords written to logs (`views.py` 159, 861, 875) that no other tool did. Slower, so it informs before it blocks. |
| PR         | IaC                      | Security-critical misconfiguration such as missing Dockerfile `USER`, because the container runs as root and increases compromise impact.                                                        | Lower-risk configuration issues, because they have lower immediate impact.                                          | Informational hardening recommendations.                                                | Privilege and blast radius determine whether configuration should block.          |
| Post-merge | Image scan               | **New** high/critical vulnerability with a fix available, because the vulnerable artifact is about to be deployed.                                                                               | Existing or high/critical with no fix, because it was not introduced by the change or cannot yet be remediated.     | Informational package/hardening findings.                                               | Scan the actual artifact; fail new actionable vulnerabilities.                    |
| Nightly    | Full-history secret scan | Any finding not in `.gitleaksignore`, or no commits read (fail closed). Triage with TruffleHog `--only-verified`: **verified → rotate first** (leak runbook), because a live secret in history is exploitable. | —                                                                                                                   | Reviewed, non-live lab material accepted in `.gitleaksignore`.                           | Full-history scanning catches secrets that were committed and later deleted.      |
| Staging    | DAST                     | Confirmed high-impact vulnerability, because the running application can be attacked before production.                                                                                          | Lower-confidence or lower-impact finding, because it needs validation before blocking release.                      | Informational observations.                                                             | DAST requires a running application and therefore blocks promotion, not the PR.   |

**SCA "new only"** means the PR fails only for vulnerabilities introduced by the change; existing findings do not suddenly turn an otherwise unrelated PR red. A vulnerability in CISA's **KEV** catalog overrides this rule and fails because it is known to be actively exploited.

**SAST gap closed (J04, 2026-10-25):** `p/python` and `p/django` miss the two `.raw()` SQL injections in `introduction/views.py` (162, 878), because the query is built in one statement and executed in another. The custom taint rule `django-raw-sql-from-request` (`semgrep-rule/`, tested, part of the gate) catches both and not the parameterised fix; CodeQL confirms them. Still not found by any tool: logic flaws such as `secret()` trusting a client-sent header. A green SAST check does not replace review.

**Secrets scans fail closed:** each scan first counts the commits it will read with `git rev-list`; if git cannot read the repository or the range is empty, the job fails instead of reporting "no leaks found" on zero commits.

## 3. Rollout

1. **Warn:** run the new gate and publish findings without blocking.
2. **Fail new:** block newly introduced high-risk findings once the gate is trusted and tuned.
3. **Expand:** progressively enforce the remaining gates.
4. **Baseline:** existing findings remain tracked but do not block unrelated PRs.
5. **KEV override:** KEV vulnerabilities fail regardless of the normal threshold unless security approves an explicit exception.

**Current status:** SAST is at step 2 (fail new) since 2026-10-11: every finding goes to Code Scanning; a PR fails only on ERROR-severity findings it introduces (`--baseline-commit` = PR base). Proven on PR #8: plant red, removal green.

Secrets: pre-commit hook, PR scan and nightly full-history scan are at step 2 (fail) since 2026-10-25; the PR scan was proven red on a planted key (`test-leak`) and green on clean commits. CodeQL is at step 1 (report).

## 4. Allowlist (risk acceptance)

The allowlist is version-controlled in the repository and changes require a PR.

SAST allowlist: `.github/security/semgrep-allowlist.json`. It is JSON because the gate reads it with `jq` inside the Semgrep image. It lives under `.github/`, so CODEOWNERS applies to every change. Each entry contains five fields:

```json
[
  {
    "id": "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
    "location": "challenge/views.py",
    "reason": "false positive: command is built from an app-set container ID, list args, no user input",
    "owner": "ken",
    "expires": "2026-12-31"
  }
]
```

An entry excuses **one rule (`id`) in one file (`location`)**. A line that fires two rules needs two entries; the same rule in another file still fails. `expires` is `YYYY-MM-DD` so it compares correctly as text. The SCA allowlist is `.snyk` (Snyk's own policy format): each ignore has the Snyk ID, a reason, the owner and an `expires` date, e.g. the Pillow findings kept for A9 lab 2.

Secrets allowlist: `.gitleaksignore`, one **fingerprint** per line (`commit:file:rule:line`), with the review date and reason in the header comment. It stores locations, never the secrets. A finding is added only after review shows it is not a real credential (today: lab passwords, sample JWTs, captured CSRF tokens) **and** TruffleHog `--only-verified` reports it is not live.

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

Scanner results are uploaded as **SARIF** to GitHub **Code Scanning** (Security tab), one category per tool:

* `Semgrep OSS`: community rules + `semgrep-rule/` custom rules
* `CodeQL`: default setup, every PR and weekly
* `Snyk Container`: image and Python dependencies
* `gitleaks-pr` / `gitleaks-history`: secrets in a PR's commits / in all history (secrets redacted, location only)

The upload runs even when the scan fails, so the finding that blocked a PR is always recorded.

* **FAIL** → blocks the relevant gate or promotion.
* **WARN** → visible to developers for review but does not block.
* **INFO** → recorded for visibility and investigation.
