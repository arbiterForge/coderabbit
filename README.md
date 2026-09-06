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

## Validating changes locally

The validator lock supports Linux x86_64 with CPython 3.13 or 3.14. Install it into a temporary
directory so it does not alter a project environment, then run the same checks as CI:

```sh
validator_dir="$(mktemp -d)"
python3 -m pip install --require-hashes --only-binary=:all: \
  --target "$validator_dir" -r .github/requirements/coderabbit-validator.txt
PYTHONPATH="$validator_dir" python3 -m unittest discover -s tests -v
PYTHONPATH="$validator_dir" python3 scripts/validate_coderabbit.py .coderabbit.yaml
```

The editor annotation uses CodeRabbit's canonical schema URL. The guard downloads the same bytes
from CodeRabbit's original public asset at
`https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json`, avoiding the canonical
redirect's browser-oriented WAF. It accepts only bytes with SHA-256
`8c34e033182463bd4f2a823b144077cb21cc327927fb82ce49791bdae2b9da13`. Retrieval failure or schema
drift fails validation without a fallback. To adopt a vendor schema revision, review the complete
new schema, update the digest in the validator and regression test, and rerun all checks.
