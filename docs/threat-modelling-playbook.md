# Threat-modelling playbook

How we find security problems in a design before the code exists. Example used throughout: the
PyGoat model in [`docs/threat-model/`](threat-model/).

## 1. When we threat model
A threat model is required when a change does any of these:
- adds a new **way in** (a new public endpoint, a webhook, a file upload, a new API client);
- moves data across a **trust boundary** it did not cross before (to a new third party, another
  account, or the internet);
- handles a **new kind of sensitive data** (personal data, payment details, credentials);
- changes **who can do what** (new roles, admin features, support "act as" tools);
- adds or changes **infrastructure that holds secrets or runs code** (CI/CD, IAM roles, KMS keys).

Not needed for: copy changes, styling, refactors with no new data flow. When unsure, the team asks
in the security channel; the answer takes minutes, a missed review can take months.

Two sizes:
| Size | When | Time |
|---|---|---|
| **Light** | small feature, one new flow | 20–30 min at design time, written in the PR or design doc |
| **Full** | new service, new boundary, sensitive data | 60–90 min session + a model committed to the repo |

## 2. Who is in the room
- **The engineers building it.** They own the model and the fixes; they know how it really works.
- **A facilitator.** A security engineer or a trained security champion. They ask questions and
  keep the four questions moving; they do not write the answers for the team.
- **Optional:** the product owner (to accept risks), an SRE (for infrastructure and failure modes).

Five people at most. More people means less talking.

## 3. The session: four questions
1. **What are we building?** Draw the DFD together: actors, processes, stores, flows, trust
   boundaries. Use OWASP Threat Dragon so the result is a file. Stop when every flow that crosses a
   boundary is drawn and labelled.
2. **What can go wrong?** Walk the diagram one element at a time; for each, go down STRIDE and ask
   "could this happen here?" Start with **flows that cross a boundary**. Write each threat as
   *who, how, what is harmed*.
3. **What will we do about it?** For each threat: prevent, detect, respond, or **accept** in writing
   with a named owner. Rank with **likelihood × impact (1–3 each)**:
   likelihood 3 = anyone, no login · 2 = needs an account · 1 = needs an insider;
   impact 3 = all users, takeover or cloud credentials · 2 = one user, partial secret, outage · 1 = minor.
   Break ties by blast radius and by what cannot be undone.
4. **Did we do a good job?** Before closing: did every boundary crossing get looked at? Is every
   High threat either fixed in the design or ticketed? Later: when a test, pen test or incident finds
   something the model missed, add it, and note why it was missed.

Facilitator rules: questions, not lectures ("what checks that this tenant ID is really theirs?");
the team writes the threats in its own words; finish on time even if the model is incomplete, and
book a follow-up.

## 4. What comes out
- **The model file**, committed next to the code (`docs/threat-model/*.json`) and updated in the same
  PR that changes the design. A model that is not in the repo goes stale within a month.
- **A ranked list** (top 10), each item marked *control today* or *ticket* (example:
  [`ranking.md`](threat-model/ranking.md)).
- **Tickets** for every Open threat ranked 6 or above.

## 5. How findings become tickets
Each ticket contains: the threat (who, how, harmed), the L × I score, the element on the diagram, the
fix, and a **done-when** that can be checked, for example "`curl -I http://host` returns 301 to
https" or "a request with another tenant's ID returns 403".

Service levels by score:
| Score | Fix before |
|---|---|
| 9 | launch: the feature does not ship |
| 6 | 30 days after launch |
| 3–4 | next quarter, or accepted in writing |
| 1–2 | accepted, reviewed yearly |

An accepted risk has an owner and an expiry date. On expiry it is re-reviewed, not silently renewed.

## 6. Scaling it beyond the security team
One security engineer cannot attend every design meeting. So:
- **Security champions.** One engineer per team, trained to facilitate a light session. They pull in
  security for full sessions.
- **Self-serve templates.** A design-doc template with a "Threat model" section that asks the four
  questions, plus Threat Dragon starter diagrams for common shapes (web app + database, CI/CD
  pipeline, file upload, multi-tenant service).
- **Pattern library.** Threats that recur get a standard fix written once: SSRF (allowlist, block
  internal ranges, no redirects), public storage (block public access, presigned GET), cross-tenant
  access (tenant from the session, never the client), secrets in CI (OIDC, no printing, CODEOWNERS on
  workflows).
- **Measure it.** Share of new services with a model in the repo; Highs found at design time versus
  found later by testing or incidents. The second number should rise over time.

## 7. Example: what a 30-minute light session found
The PyGoat pipeline session found that `deploy.yml` printed part of a deploy token into public logs,
and that the branch ruleset needed 0 approvals with an admin bypass. Both were invisible in the
scanners' results, and both took one line to describe once someone looked at the diagram.
