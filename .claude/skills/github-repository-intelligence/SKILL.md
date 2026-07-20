# GitHub Repository Intelligence

## Role
Map the repository before modification and identify the real production decision path.

## Required workflow
- Inspect the tree, entry points, configuration, tests, workflows, open issues and recent changes.
- Trace data flow from ingestion to final decision and persistence.
- Identify duplicate engines, dead code, compatibility paths and conflicting classifiers.
- Produce a file-specific implementation plan before editing.

## Mandatory output
- Architecture map.
- Active decision path.
- Contradictions and risks.
- Files to change and files to delete or retire.
- Acceptance criteria.

## Prohibitions
- Do not infer architecture from filenames alone.
- Do not patch before tracing the complete call path.
- Do not preserve obsolete logic merely for compatibility when it conflicts with the production design.