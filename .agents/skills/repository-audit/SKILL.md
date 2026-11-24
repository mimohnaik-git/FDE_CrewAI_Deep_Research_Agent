---
name: repository-audit
description: Perform a read-only audit of repository identity, Git state, conventions, constraints, and validation entry points, then report evidence and gaps.
---

# Repository audit

1. Confirm the current directory, Git root, origin, branch, HEAD, and full working-tree status.
2. If Git reports dubious ownership, use only a per-command `git -c safe.directory=<repo-root>` override; do not write global Git configuration.
3. Inspect tracked guidance, project manifests and lockfiles, docs, workflows, test layout, and ignore rules. Do not read secret files such as `.env`.
4. Compare requested changes with current conventions and record concrete file paths or command output for each finding.
5. When asked for a read-only audit, do not modify files, refs, configuration, or remote state.

## Report

Return PASS or FAIL for each requested criterion, with supporting evidence and any access or discovery limits. Do not infer a clean tree from an abbreviated or failed status command.
