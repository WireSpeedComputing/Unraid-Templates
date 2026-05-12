# Adding a new template

Conventions and procedure for adding a new app to this repo.

---

## Folder layout

Each app gets its own top-level folder. The folder name is lowercase and hyphenated.

```
<app-name>/
  <app-name>.xml                 # main template (Tailscale sidecar or bridge)
  <app-name>-tailscale.xml       # optional: sidecar variant if the main is bridge
  README.md                      # app-specific install + config + troubleshooting
```

If the app uses Tailscale, you do NOT add a per-app sidecar XML. Use the generic `tailscale-sidecar/tailscale-sidecar.xml`, and document in the app's README how to rename it for this service.

---

## Naming conventions

| Thing | Convention | Example |
| --- | --- | --- |
| Folder | lowercase-hyphenated | `unraid-mcp` |
| XML filename | matches folder name | `unraid-mcp.xml` |
| Sidecar variant filename | append `-tailscale` | `unraid-mcp-tailscale.xml` |
| Container `<Name>` in XML | **generic, matches folder name** -- NOT a deployment-specific name | `unraid-mcp` |
| Tailscale sidecar container name to reference | `tailscale-<service-short-name>` | `tailscale-unraidmcp` |
| Default host appdata path | `/mnt/user/appdata/<app-name>/` | `/mnt/user/appdata/unraid-mcp/` |

**Do not bake deployment-specific names into the public template.** A user who copies the template should not end up with a container named `mcp-filesystem-wiki` if their use case has nothing to do with a wiki. The container name is generic in the public template; users rename per their deployment.

---

## Template XML conventions

Required structure:

- `<Container version="2">`
- `<Name>` matches folder
- `<Repository>` pinned to a specific version tag, not a rolling tag (`:stable`, `:latest`, `:main`). Specific versions are auditable and reproducible.
- `<Support>` = `https://github.com/WireSpeedComputing/Unraid-Templates/issues`
- `<Project>` = the upstream project URL (not this repo)
- `<TemplateURL>` = raw GitHub URL to this XML file
- `<Icon>` = raw GitHub URL to `icons/<app-name>.png`
- `<ExtraParams>` includes `--restart=unless-stopped` and any healthcheck flags

For Tailscale sidecar variants:

- `<Network>Container:tailscale-<service-short-name></Network>`
- No port mappings on this container -- only the sidecar publishes ports
- `<Requires>` block explicitly warns the user to deploy the sidecar first with the matching name
- Description includes the "RENAME BEFORE DEPLOYMENT" warning block

For secrets:

- `Mask="true"` on any API key, auth key, or token field

For advanced/rarely-changed fields:

- `Display="advanced"` so they collapse in the default Unraid view

---

## Procedure

1. **Copy the scaffold:**
   ```bash
   cp _scaffold/APP_TEMPLATE.xml <app-name>/<app-name>.xml
   cp _scaffold/APP_README.md <app-name>/README.md
   ```
2. **Edit the XML.** Replace every `TODO-*` value. Verify:
   - `<Name>` matches folder name
   - `<Repository>` is pinned to a specific tag
   - `<TemplateURL>` is the correct raw GitHub URL
   - All ports, volumes, env vars are documented in the Description and have `<Config>` entries
   - Secrets have `Mask="true"`
3. **Edit the README.** Cover:
   - What the app does
   - Prerequisites (Tailscale sidecar deployment if applicable)
   - Setup steps
   - Configuration reference
   - Security considerations (especially if the app exposes filesystem or network access)
   - Troubleshooting (link to `docs/TROUBLESHOOTING.md` for cross-cutting issues)
4. **Add an icon.** Drop a PNG at `icons/<app-name>.png`. Placeholder colored squares are fine for v0.1; replace with proper icons later.
5. **Update the root README.** Add a row to the "What's here" table.
6. **Audit before pushing.** From the repo root:
   ```bash
   # No em dashes
   grep -rP '\xe2\x80\x93|\xe2\x80\x94' . --include='*.md' --include='*.xml'
   # No smart quotes
   grep -rP '[\xe2\x80\x98\xe2\x80\x99\xe2\x80\x9c\xe2\x80\x9d]' . --include='*.md' --include='*.xml'
   # No stale repo URLs (the org is WireSpeedComputing CamelCase; lowercase
   # was the old single-app repo. The icon filename wirespeed-computing.png is
   # fine and excluded here.)
   grep -r 'github.com/wirespeed-computing' . --include='*.md' --include='*.xml'   # should be empty
   grep -r 'mcp-memory-unraid' . --include='*.md' --include='*.xml'                # should be empty
   # No rolling tags in actual <Repository> fields (mentions in prose are OK)
   grep -rn '<Repository>.*:quality-cpu\|<Repository>.*:latest\|<Repository>.*:main\b' . --include='*.xml'  # should be empty
   ```
7. **Commit, push, verify raw URL resolves:**
   ```bash
   curl -sI https://raw.githubusercontent.com/WireSpeedComputing/Unraid-Templates/main/<app-name>/<app-name>.xml
   ```

---

## Encoding policy

UTF-8, ASCII characters only in code-like content.

- **No em dashes.** Use `--` (double hyphen) instead.
- **No smart quotes.** Use ASCII straight quotes only (`'` and `"`).
- **No non-ASCII whitespace** (no en spaces, non-breaking spaces, etc.).

Reason: PowerShell scripts on Windows misread `.ps1` files containing non-BOM UTF-8 with multi-byte characters, parsing them as Windows-1252. Maintaining ASCII-only discipline across all files in the repo keeps the rule simple and the build reliable.

The audit greps above catch the common offenders.

---

## What does NOT belong in a public template

- Operator-specific paths (e.g., `/mnt/user/wirespeed/...` -- use `/mnt/user/appdata/...` instead).
- Operator-specific container names (e.g., `mcp-filesystem-wiki` for an instance happens-to-host a wiki -- use `filesystem-mcp` generically).
- Tenant IDs, customer names, real domains.
- API keys, auth keys, tokens, SSH keys, certificates of any kind.
- Internal architecture docs or build logs.
- Anything referencing the operator's actual hostnames or Tailscale node names.

The repo is public. Generic-first, placeholder-based.

---

## Upgrading an existing template

When the upstream image releases a new version:

1. Read the upstream release notes carefully. Tag changes between minor versions can include schema migrations or new required env vars.
2. Update `<Repository>` to the new tag.
3. If env vars changed, update the `<Config>` entries and the README.
4. If the breaking change affects existing users, note it in a `## Upgrading` section in the app's README and reference the upstream migration guide.
5. Commit with a descriptive message: "mcp-memory: bump to 10.50.0 (handles schema migration)".

Do not roll up multiple unrelated upgrades into one commit.

---

## Submitting to Community Applications

After the repo has at least one fully functional app:

1. The repo URL is submitted to Community Applications via the CA submission form (see CA documentation; the form changes occasionally).
2. CA scans the repo for XML templates and surfaces them in the Unraid Docker app catalog.
3. The `ca_profile.xml` at the repo root provides the maintainer entry shown in CA.

CA submission is a separate manual step performed by a repo maintainer. Contributors do not need to do this.
