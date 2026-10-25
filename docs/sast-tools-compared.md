# SAST tools compared — pygoat

What each static analysis tool found on the same code, what it missed, and where each one
sits in the pipeline. Everything below comes from runs on this repo (2026-10-24/25) unless
marked **(from docs)**.

**Bottom line:** no single tool found every bug. On pygoat, Semgrep's community rules missed
both SQL injections, bandit missed the SSRF, CodeQL missed the hardcoded Django key, and
SonarQube missed the passwords written to logs. Only a custom rule caught the SQL injection
cheaply on every PR, only dataflow (CodeQL) caught passwords in logs, and no tool caught the
logic flaw in `secret()`. The pipeline therefore layers tools: fast and precise on every PR,
deep on a schedule, and human review for logic.

## 1. Tools run on pygoat

| Tool | Version / mode | How it works | Where it runs here |
| ---- | -------------- | ------------ | ------------------ |
| Semgrep (`p/python`, `p/django`) | 1.140.0 | Pattern matching on the syntax tree; taint mode within one function | Every PR (gate on new ERROR findings) |
| Semgrep custom rules (`semgrep-rule/`) | same | Taint rule written for this codebase (`django-raw-sql-from-request`), plus the J01 `SECRET_KEY` rule; tested with `semgrep --test` | Every PR, same gate |
| bandit | 1.8.6 | Python AST checks against a fixed list (B101…B703); no taint | Local only (second opinion) |
| CodeQL | default setup | Builds a database of the whole program; dataflow from modelled sources to sinks across functions and files | Every PR + weekly; reports to Code Scanning |
| SonarQube Cloud | scanner 12.3 | Rules + taint analysis from framework entry points; also bugs, code smells, duplication | Every PR; quality gate is a required check |

## 2. Same code, different findings

Bugs in `introduction/views.py` unless another file is named. ✅ found, ❌ missed.

| Bug | Semgrep community | Custom rules | bandit | CodeQL | SonarQube |
| --- | ----------------- | ------------ | ------ | ------ | --------- |
| SQL injection via `.raw()` (162, 878) | ❌ | ✅ (sink) | ✅ B608 (string build) | ✅ `py/sql-injection` | ✅ S3649 |
| XXE in `xxe_parse` (259–260) | ❌ | — | ✅ B317/B319 | ✅ `py/xxe`, `py/xml-bomb` | ✅ S2755 |
| SSRF (961–963) | ✅ | — | ❌ (only B113: no timeout) | ✅ `py/full-ssrf` | ✅ S5144 |
| Command injection (430–432) | ✅ | — | ✅ B602 | ✅ `py/command-line-injection` | ❌ here (found one in `mitre.py`) |
| Passwords written to logs (159, 861, 875) | ❌ | — | ❌ | ✅ `py/clear-text-logging-sensitive-data` | ❌ |
| MD5 for passwords (1026) | ✅ (reported twice) | — | ✅ B324 | ✅ `py/weak-sensitive-data-hashing` | ✅ S4790 |
| Hardcoded Django `SECRET_KEY` (`pygoat/settings.py:24`, `dockerized_labs/…/settings.py:8`) | ❌ | ✅ (J01 rule) | partly (B105 strings) | ❌ | ✅ S6687 |
| App bound to `0.0.0.0` (`dockerized_labs`) | ❌ | — | ❌ | ❌ | ✅ |
| `secret()` grants access from a client-sent `X-Host` header | ❌ | ❌ | ❌ | ❌ | ❌ |

Volume on the same file or repo: Semgrep `p/python` 12 findings on `views.py`; bandit 27 on
`views.py` (17 LOW); CodeQL 42 alerts repo-wide (Python + JavaScript); SonarQube 407 open
issues repo-wide (security rating E, 187 vulnerabilities, 165 bugs — expected for a
deliberately vulnerable app).

## 3. What each tool is good and bad at

**Semgrep.** Fast (seconds), readable YAML rules, and custom rules take minutes to write, so
it is the PR gate. It only finds shapes a rule describes: the community rules missed the
SQL injection because the query is built in one statement and executed in another. The fix
was a taint rule with `focus-metavariable` on the SQL argument, so the parameterised fix is
not flagged (proven with a red test case). Duplicates are possible (MD5 reported by two
rules).

**bandit.** Python only, no taint: B608 flags any SQL built from variables, wherever the data
comes from, so it catches more but is noisier (17 of 27 findings LOW). Useful as a second
opinion; in CI it would run with `-ll -ii` (medium and above, medium confidence and above).
It missed the SSRF entirely.

**CodeQL.** Dataflow across the whole program with Django modelled, so it found the one bug no
other tool did: passwords flowing into `print()`. Slower (minutes), queries are hard to write
(QL), so it runs on PRs as a report and weekly as a deep scan rather than as a blocking gate.
It does not look for hardcoded secrets in its default suite.

**SonarQube Cloud.** Security plus code quality, with history and PR decoration. Its taint
analysis needs a framework entry point: an unrouted function with a command injection was
not reported; the same code as a routed Django view was (S2076) and failed the quality gate.
Judges new code only, so a legacy app rated E can still have a strict PR gate. Coverage is
excluded until tests exist (see `SECURITY-GATES.md`).

## 4. Commercial tools (from docs, not run)

| Tool | How it works **(from docs)** | Trade-off |
| ---- | ---------------------------- | --------- |
| Checkmarx One SAST | Source-code dataflow analysis without a build; custom queries; IDE and CI integrations; enterprise licence | Deep coverage across many languages; needs tuning to keep false positives down; cost |
| Veracode Static Analysis | SaaS scans of a packaged application (binaries/bytecode for compiled languages); policy-based pass/fail; a faster pipeline scan for CI | Strong policy and reporting for compliance-driven teams; upload model and scan time suit release gates more than every PR |

Both answer the same question as CodeQL and SonarQube — does untrusted input reach a dangerous
sink — with commercial support, central policy and reporting. Whether they would have found
the logic flaw in `secret()` is unknown; no rule-based tool here did.

## 5. Secrets scanning (for comparison)

| Tool | Found on pygoat history | Missed |
| ---- | ----------------------- | ------ |
| gitleaks 8.30.1 | 11 (lab passwords, sample JWTs, captured CSRF tokens) — reviewed and listed in `.gitleaksignore` | Google OAuth tokens inside `db.sqlite3` (binary) |
| TruffleHog 3.99.7 `--only-verified` | 0 verified; 12 unverified candidates in a vendored virtualenv (commit `51e32c5`) | Everything gitleaks found (no provider format) |
| GitHub push protection | 4 Google OAuth tokens in `db.sqlite3` history | — |

Zero overlap between gitleaks and TruffleHog. SonarQube also reported both hardcoded Django
keys (S6687), which gitleaks and CodeQL missed.

## 6. Where each tool sits

| Stage | Tool | Why |
| ----- | ---- | --- |
| Pre-commit | gitleaks | Stop a secret before the commit exists |
| PR (blocking) | Semgrep + custom rules, SonarQube Cloud gate, gitleaks | Fast, precise, judged on new code only |
| PR (report) | CodeQL | Deep dataflow; informs the reviewer |
| Nightly / weekly | gitleaks full history, CodeQL weekly | New rules applied to old code |
| On demand | TruffleHog `--only-verified` | Which leaked secrets are live right now |
| Human | Code review | Logic flaws and missing checks (`secret()`, authorisation) that no tool saw |

## 7. Recommendation

Keep Semgrep with custom rules as the blocking PR gate (speed and precision), SonarQube Cloud
as the second blocking gate (quality plus taint from entry points), and CodeQL as a
non-blocking deep scan until its findings are triaged and trusted. Write a custom Semgrep
rule whenever a deep scan or a review finds a bug pattern the PR gate missed. Treat a green
SAST check as "no known pattern found", not "secure": the `secret()` header check passed
every tool.
