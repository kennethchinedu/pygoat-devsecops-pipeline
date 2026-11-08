# PyGoat threat model: ranked top 10

Date: 2026-11-08 · Ranking by Kenneth Chinedu (scores and order); write-up by the tutor.
Sources: `pygoat.json` (app DFD) and `pipeline.json` (CI/CD DFD), opened in OWASP Threat Dragon.

**Scale.** Likelihood: 3 = anyone, no login or already public · 2 = needs an account or effort ·
1 = needs an insider. Impact: 3 = all users, account takeover or cloud credentials · 2 = one user,
a partial secret or an outage · 1 = minor. Risk = likelihood × impact. Ties broken by blast radius
and by what cannot be undone.

| Rank | Threat | Model | L × I | Control today | Ticket |
|---|---|---|---|---|---|
| 1 | SSRF reaches ECS task metadata → AWS role credentials (`introduction/views.py:963`) | app | 3 × 3 | none | URL allowlist + block internal ranges, disable redirects, least-privilege task role; GuardDuty for credential use outside AWS |
| 2 | `SECRET_KEY` hardcoded in a public repo and not overridden on ECS → forged password resets (`pygoat/settings.py:24`) | app | 3 × 3 | gitleaks finds it (PLANTED #9) | read it from Secrets Manager, rotate, purge from history |
| 3 | OS command injection runs as root in the container (`introduction/views.py:430`, no `USER` in Dockerfile) | app | 3 × 3 | Semgrep / CodeQL / hadolint flag it | argument list without a shell; non-root `USER` |
| 4 | `DEBUG = True` in production leaks stack traces and settings (`pygoat/settings.py:29`) | app | 3 × 2 | Sonar / Semgrep (PLANTED #10) | `DEBUG` from the environment, `False` on ECS |
| 5 | SQL injection, plus plain-text passwords in the lab login table (`introduction/views.py:157`) | app | 3 × 2 | custom Semgrep taint rule (J04), Sonar gate | ORM / parameterised queries; Django's hashed auth |
| 6 | `/admin/` open to the internet with a password only (`pygoat/urls.py:23`) | app | 2 × 3 | none | restrict by IP or keep it off CloudFront; MFA; rate-limit login |
| 7 | Part of `DEPLOY_TOKEN` printed to public Actions logs (`.github/workflows/deploy.yml:24-25`) | pipeline | 3 × 2 | none | delete the echo, rotate the token, move to OIDC |
| 8 | Plain HTTP while CloudFront is not deployed: credentials and session readable in transit | app | 2 × 2 | designed (`edge/main.tf:107`), not running | get the account verified, deploy the edge; `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| 9 | Reflected XSS: `{{query\|safe}}` (`xss_lab.html:27`) | app | 2 × 2 | Semgrep / CodeQL (PLANTED #8) | remove `\|safe`; Content-Security-Policy |
| 10 | ECS runs the image without verifying its cosign signature (`fargate-service/main.tf:137`) | pipeline | 1 × 3 | images are signed; `release.yml` verify job | deploy by digest; verify before deploy (Kyverno `verifyImages` in J08) |

**Why #1 outranks #2** (the student's reasoning): both are easy to exploit and harm many people,
but a leaked `SECRET_KEY` can be contained quickly once found (rotate it and every forged token
dies), while SSRF hands over the app's AWS role credentials. Those reach beyond the app into the
whole AWS account, so the blast radius is larger and the damage is harder to undo.

Also tracked, below the top 10: a 0-approval merge to `master` with admin bypass (1 × 3); scan
tokens exfiltrated through a collaborator's PR (1 × 3).
