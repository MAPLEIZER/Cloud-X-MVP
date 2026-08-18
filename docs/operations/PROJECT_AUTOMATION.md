# Label-driven GitHub Projects automation

Cloud-X treats repository labels as the machine-readable source of truth for issue and pull-request planning metadata. GitHub Projects are a projection of that metadata, not a second source that must be maintained manually.

## Why this model

The repository already uses a compact taxonomy:

- `status:*` — workflow state such as `planned`, `in-progress`, `acceptance`, `blocked`, `done`;
- `phase:*` — canonical roadmap phase;
- `priority:*` — `p0` through `p3`;
- `pipeline:*` — `current`, `next`, `later`, `done`;
- `type:*` — feature, infra, security, test, tracking, hygiene, and similar work types;
- `area:*` — one or more technical/product areas.

Keeping those values in GitHub labels has several advantages: the metadata remains visible outside Projects, survives Project replacement, can be applied by issues/API/automation, and is easy for repository governance tests and agents to reason about.

## What the workflow does

`.github/workflows/project-sync.yml` reacts to issue and pull-request lifecycle/label changes. When `PROJECTS_TOKEN` is configured it:

1. discovers every writable GitHub Project V2 linked to `MAPLEIZER/Cloud-X-MVP`;
2. adds the issue or pull request to each linked open Project if it is not already present;
3. reads `.missionkit/project-sync.json`;
4. maps the label dimensions into compatible Project fields;
5. clears the corresponding Project field when its source label is removed;
6. treats a closed issue/PR as `status:done` + `pipeline:done` for Project presentation;
7. writes a human-readable run summary listing missing fields/options instead of inventing Project schema.

No Project IDs, item IDs, field IDs, or option IDs are stored in this repository. New Projects can therefore be introduced simply by linking them to the repository and running a backfill.

## Supported Project field shapes

The sync accepts the following field contracts:

| Label dimension | Preferred Project field | Supported field type |
|---|---|---|
| `status:*` | `Status` | single select (preferred), text |
| `phase:*` | `Phase` | single select, text |
| `priority:*` | `Priority` | single select, text |
| `pipeline:*` | `Pipeline` | single select, text |
| `type:*` | `Type` or `Work Type` | single select, text |
| `area:*` | `Areas` or `Area` | multi select (preferred), single select, text |

Option matching is case/punctuation insensitive and supports aliases declared in `.missionkit/project-sync.json`. For example, `status:planned` can populate a built-in `Status` option named `Todo`, while `phase:2` matches `Phase 2`.

The workflow deliberately does **not** create or rename Project fields/options automatically. Schema mutation is a higher-risk administrative operation than item synchronization. If a linked Project lacks a matching field or option, the action summary reports it and continues with the other fields/Projects.

## One-time authentication bootstrap

GitHub's normal repository `GITHUB_TOKEN` does not have the permissions required to write Projects V2. Configure one repository Actions secret:

`PROJECTS_TOKEN`

For a personal Project, GitHub documents a classic personal access token with `project` plus repository access as a supported bootstrap mechanism. A dedicated GitHub App with Projects write permission is preferable once Cloud-X has its bot/service identities because it can be narrowly scoped and rotated independently of a user account.

Security rules:

- never commit the token;
- do not switch this workflow to `pull_request_target` merely to expose secrets to forked PRs;
- fork/Dependabot PRs that do not receive the secret safely skip Project writes;
- grant only the repository/Project permissions actually needed;
- rotate the bootstrap PAT when a GitHub App replaces it.

## Linking a new Project

1. Create the GitHub Project under the intended user/organization.
2. Link `MAPLEIZER/Cloud-X-MVP` to that Project in the Project/repository settings.
3. Add any desired fields from the field contract above.
4. Ensure single/multi-select options use recognizable names (or add an alias to `.missionkit/project-sync.json`).
5. Run **Project Metadata Sync** manually with `scope=open` to populate active work. Use `scope=all` only when historical closed items are also wanted.

After that initial backfill, issue/PR lifecycle and label changes synchronize automatically.

## Recommended Project views

Because the same fields are populated in every linked Project, views can be made consistent without additional workflows:

### Delivery board

Group by `Status`; filter `Pipeline = Current`; sort by `Priority`.

### Roadmap

Group or slice by `Phase`; filter out `Pipeline = Done`; use GitHub's roadmap/date fields separately when an actual target date exists. Do not invent dates merely to place work on a timeline.

### Next-up queue

Filter `Pipeline = Next`; group by `Phase`; sort by `Priority`.

### Security / release readiness

Filter `Type = Security` or `Areas` contains `Dependencies`, `Release`, `Deployment`; group by `Status`.

### Completed evidence

Filter `Pipeline = Done`; group by `Phase` or `Areas` for release/pilot evidence reviews.

## Backfill behavior

Manual dispatch supports:

- `open` — every currently open issue and pull request;
- `all` — open and closed issues/pull requests.

The backfill uses the same mapping logic as event-driven sync. It is safe to rerun because adding an existing issue/PR is avoided and field updates are deterministic.

## Configuration changes

Edit `.missionkit/project-sync.json` when:

- a taxonomy prefix is added;
- a Project field is renamed and should have another accepted alias;
- a Project select option uses a different human-readable name;
- a future phase/pipeline value is introduced.

Run `python3 -m unittest tests/test_project_sync.py` locally before merging mapping changes. Branch Policy runs these governance tests in CI.

## Failure behavior

| Condition | Behavior |
|---|---|
| `PROJECTS_TOKEN` absent | workflow succeeds with a clear skip notice; labels remain authoritative |
| no linked writable Projects | succeeds and reports that nothing was linked |
| Project field missing | skips that field and reports it |
| select option missing | skips that value and reports it |
| conflicting single-value labels such as two `status:*` labels | fails so the metadata conflict is corrected |
| GraphQL/permission failure with a configured token | fails visibly rather than pretending the board is synchronized |
| more than 50 linked Projects/items | fails explicitly; pagination should be added before silently dropping data |

## Future bot integration

When Cloud-X introduces its planned GitHub bot/service identities, replace the bootstrap PAT with a GitHub App token. The label schema and `sync_projects.py` do not need to change; only credential issuance changes.
