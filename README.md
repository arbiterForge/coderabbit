# coderabbit

Org-wide [CodeRabbit](https://coderabbit.ai) configuration for the **arbiterForge** organization.

CodeRabbit reads `.coderabbit.yaml` from a repository named exactly `coderabbit` as the
organization's **central configuration**, and applies it to every repo in the org.

## Precedence

Highest first:

| # | Source |
|---|--------|
| 0 | Workspace global overrides *(Enterprise only)* |
| 1 | Organization global overrides *(dashboard UI)* |
| 2 | A repository's own `.coderabbit.yaml` |
| 3 | **This repo's `.coderabbit.yaml`** |
| 4 | Repository UI settings |
| 5 | Organization UI settings |
| 6 | Workspace UI settings *(Enterprise only)* |
| 7 | CodeRabbit schema defaults |

Global overrides (0 and 1) apply as the final layer after the inheritance chain resolves, so
they are never affected by what any repository sets.

## The footgun this creates

A repository that adds its own `.coderabbit.yaml` **replaces this file entirely** unless that
file sets `inheritance: true`. There is no warning. Any new repo config in this org must set
it, or it silently drops every default here.

With inheritance on: objects deep-merge, arrays take the child's items first then unique parent
items, and scalars take the child's value.

## Scope

Deliberately no `path_filters` and no `path_instructions`. Merge semantics would allow them,
but paths are repo-specific — a pattern that is precise in one repo is noise in the next.
Per-repo path rules belong in the repo. See `codeArbiter/.coderabbit.yaml` for an example that
excludes vendored trees.

## Verifying it took effect

Comment `@coderabbitai configuration` on any pull request. CodeRabbit replies with the fully
resolved config and the **source of each setting**, which is the only reliable way to confirm a
change here actually reached a repo. The file existing is not evidence that it applied.
