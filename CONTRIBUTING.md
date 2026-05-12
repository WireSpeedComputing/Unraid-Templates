# Contributing to Unraid-Templates

Thanks for considering a contribution. Please read this short guide before opening an issue or pull request.

## Repo scope

This repo packages Unraid Community Applications (CA) Docker templates for self-hosted AI infrastructure (mcp-memory, filesystem-mcp, Tailscale sidecar, and more as the catalog grows). Each template is a deployment recipe, not the upstream service itself.

**In scope:**

- Bug fixes in template XML files (wrong env var names, broken paths, missing healthcheck, etc.).
- Improvements to documentation for clarity, correctness, and coverage of common Unraid configurations.
- New app templates following the conventions in [docs/ADDING_NEW_TEMPLATES.md](docs/ADDING_NEW_TEMPLATES.md).
- Compatibility patches when an upstream image releases a breaking change.
- Issue and PR template improvements.

**Out of scope:**

- Bugs in the upstream service images. Report those to the upstream project (linked in each template's `<Project>` field).
- Feature requests for an upstream service. Report upstream.
- Customer-specific or operator-specific deployments. Templates are generic-first by design. If a change only helps one operator's setup, keep it in a private fork.

## How to propose a change

1. Open an issue first for non-trivial changes. A short problem description plus proposed fix saves time on both sides before code is written.
2. For bug reports: use the bug report template (when issue templates are in place).
3. For new app templates: read [docs/ADDING_NEW_TEMPLATES.md](docs/ADDING_NEW_TEMPLATES.md) first. The conventions are not negotiable.
4. Open a PR that references the issue.
5. Keep PRs narrow. One concern per PR. "Fix three unrelated things" PRs will be asked to split.
6. Update relevant docs if your change affects user-visible behavior. Documentation is part of the change.

## Encoding policy

All files in this repo are UTF-8 with ASCII-only content for code-like text.

- No em dashes. Use `--` (double hyphen).
- No smart quotes. ASCII straight quotes only.
- No non-ASCII whitespace.

Reason: PowerShell on Windows misreads non-BOM UTF-8 with multi-byte characters as Windows-1252, breaking any `.ps1` script with em dashes or smart quotes. Maintaining ASCII discipline across the whole repo keeps the rule simple.

Pre-commit audit:

```bash
grep -rP '\xe2\x80\x93|\xe2\x80\x94' . --include='*.md' --include='*.xml'  # em dashes
grep -rP '[\xe2\x80\x98\xe2\x80\x99\xe2\x80\x9c\xe2\x80\x9d]' . --include='*.md' --include='*.xml'  # smart quotes
```

Both should return empty.

## Style notes

- Markdown that renders cleanly in GitHub preview.
- Tables where tables make sense; prose where prose makes sense.
- No customer names, no real tenant IDs, no real domains, no real keys, no SSH keys, no Tailscale node IPs in any committed file.
- Anchored claims. If you assert something about an upstream project, link the source.

## Code of conduct

Be civil. Disagreement is fine; the work has tradeoffs. Personal attacks, harassment, or hostility toward contributors are not.

If you experience or witness behavior that violates this expectation, contact the maintainers privately via the security disclosure path in [SECURITY.md](SECURITY.md).

## License

By contributing, you agree your contributions are licensed under the Apache 2.0 license, the same as the rest of the repo.
