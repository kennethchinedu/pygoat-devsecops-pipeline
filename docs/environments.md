# Environments and approvals — pygoat

`.github/workflows/deploy.yml` deploys in two stages. Every push to `master` runs:

```
deploy-staging    (environment: staging)     runs straight away
      │ needs
deploy-production (environment: production)  pauses until a reviewer approves
```

The deploy itself is an `echo`; what this file documents is the gates around it.

## Configuration (Settings → Environments)

| Environment | Deployment branches | Required reviewers | Secret |
|---|---|---|---|
| `staging` | `master` only | none | `DEPLOY_TOKEN` (staging value) |
| `production` | `master` only | `kennethchinedu` | `DEPLOY_TOKEN` (production value) |

## What each setting stops

| Setting | What it does | What it stops | Evidence (Actions run) |
|---|---|---|---|
| **Deployment branches** (`master` only) | A job may use the environment only when the run is on an allowed branch. Checked before the job starts, so the secret is never handed over. | A feature branch, or a workflow edited on one, deploying or reading deploy secrets, even when someone triggers it by hand with **Run workflow**. | **Rejected:** run 38127928920 (`workflow_dispatch` on `j01-deploy-from-branch`): *"not allowed to deploy to staging due to environment protection rules"*; production skipped. |
| **Required reviewers** (production) | The job pauses until a named reviewer approves. The approval is recorded on the run. | A merge going live with nobody looking; a compromised workflow or token deploying on its own. | **Paused → approved:** run 38127515343, staging ran, production waited, *"kennethchinedu approved production"*, then ran. |
| **Environment secrets** | A secret is available only to jobs that use that environment, and only after its rules pass. | Staging, test or any other job reading production credentials. | Run 38127515343: same secret name, staging job got `staging…`, production job got `prod…`. |

## Known limits

- **Self-review is allowed.** "Prevent self-review" is off because this repo has one maintainer; with it on, nobody could ever approve. In a team it should be on, so the person who merged cannot also approve the release.
- **Repository admins can still change these settings.** The rules protect the pipeline, not the settings page; changes to environments are not reviewed like code.
- **Log masking only hides the exact secret value.** The workflow prints a prefix (`${DEPLOY_TOKEN%%-*}`) to prove which secret arrived; that is safe only because the values are dummies. Never print any part of a real secret.
- **Next step:** replace long-lived `DEPLOY_TOKEN` secrets with OIDC (J02): the cloud trusts this repo + branch + environment, and issues a short-lived credential per run.
