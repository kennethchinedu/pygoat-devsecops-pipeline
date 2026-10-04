| # | Where (file:line) | What's wrong | Kind | Should be caught by | Status |
|---|---|---|---|---|---|
| 1 | `.github/workflows/flake8.yml:18 - 23` | GitHub Actions are not pinned to immutable commit SHAs | IaC/config | IaC scanner / GitHub Actions security scanner |  fixed (5f45b6b) |
| 2 | `.github/workflows/flake8.yml:21, 25` | Lint ran on Python 3.8 (EOL) while the image runs Python 3.11 | IaC/config | IaC scanner / GitHub Actions security scanner | fixed (5f45b6b)  |
| 3 | `pygoat/settings.py:146` | `django_heroku.settings(locals())` silently sets `ALLOWED_HOSTS` to `['*']` | config | DAST (send Host: evil.com, expect 400) | fixed (467c641, e1a3660) |
| 4 | `Dockerfile:1,9` | Uses an EOL Buster base image and obsolete `deb10`-pinned packages | IaC/config | IaC scanner / container scanner | fixed (fc900ea) |
| 5 | `Dockerfile` (no `USER` line) | Container runs as root; a break-out of the app = root in the container | IaC/config | IaC scanner / container scanner | open |
| 6 | `requirements.txt` (`requests` line) | `requests==2.28.2` has a known vulnerability; fixed in 2.31.0 | SCA | SCA scanner | open |
| 7 | `introduction/views.py:157` | User input joined with `+` into a raw SQL query → SQL injection | SAST | SAST scanner (+ DAST) | open |
| 8 | `introduction/templates/Lab/XSS/xss_lab.html:27` | `{{query\|safe}}` prints user input unescaped → reflected XSS | SAST | SAST scanner (+ DAST) | open |
| 9 | `pygoat/settings.py:24` | `SECRET_KEY` is hardcoded in the public repository | secrets | secrets scanner | open |
| 10 | `pygoat/settings.py:29` | `DEBUG = True` exposes detailed error information | config | SAST (+ DAST: a 404 shows the debug page) | open |
| 11 | `.github/workflows/pr-check.yml` | `pull_request_target` checks out and executes untrusted PR code with access to a repository secret | IaC/config | IaC scanner / GitHub Actions security scanner | ixed (e949c50) |