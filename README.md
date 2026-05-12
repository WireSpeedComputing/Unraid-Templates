# WireSpeed Computing -- Unraid Templates

Community Applications templates for self-hosted AI infrastructure on Unraid.

## What's here

| App | Image | Purpose | Variants |
| --- | --- | --- | --- |
| [mcp-memory](mcp-memory/) | `doobidoo/mcp-memory-service:10.49.3-slim` | Persistent AI memory with semantic search | Bridge, Tailscale sidecar |
| [filesystem-mcp](filesystem-mcp/) | `mekayelanik/filesystem-mcp:stable` | MCP filesystem server with Streamable HTTP | Tailscale sidecar |
| [tailscale-sidecar](tailscale-sidecar/) | `tailscale/tailscale:stable` | Generic Tailscale overlay sidecar for MCP services | -- |

Per-app install and configuration instructions live in each app's README.

## Quick start

1. Install via Unraid Community Applications, or add the raw XML URLs manually.
2. **For Tailscale sidecar deployments:** deploy and **RENAME** the sidecar first (see warning below), then deploy the service container.
3. **For bridge deployments:** the service publishes a port to your host LAN.

## Pick your access pattern

| Use bridge if... | Use Tailscale sidecar if... | Use Cloudflare Tunnel if... |
| --- | --- | --- |
| Single-user on a trusted LAN | You want overlay access from multiple devices or locations | You need a public HTTPS URL or SSO-gated access |
| You don't have a Tailscale account | You already use Tailscale, or are willing to | You want third-party-provider SSO (Google, Okta, etc.) |
| Lowest operational complexity | Identity-gated, no open ports, no DNS | Most flexible, most operational surface |
| Examples: home lab, single workstation | Examples: laptop + phone + desktop across cellular/wifi | Examples: share with a contractor, public webhook |

For sidecar: [docs/TAILSCALE_SIDECAR_GUIDE.md](docs/TAILSCALE_SIDECAR_GUIDE.md)

For Cloudflare Tunnel: [docs/CLOUDFLARE_TUNNEL_GUIDE.md](docs/CLOUDFLARE_TUNNEL_GUIDE.md) (documented for completeness; not the WireSpeed reference deployment)

## Critical: rename the Tailscale sidecar per service

The `tailscale-sidecar` template ships with generic defaults: container name `tailscale-sidecar` and state path `/mnt/user/appdata/tailscale-sidecar/`. **Deploying two services with these defaults will collide** -- both sidecars will claim the same Tailscale node identity and overwrite each other's state directory.

For each service, rename to `tailscale-<service-short-name>` and rename the state path to match. Full procedure in [docs/TAILSCALE_SIDECAR_GUIDE.md](docs/TAILSCALE_SIDECAR_GUIDE.md).

## Image-pin policy

Service images are pinned to specific minor versions, not rolling tags. A specific version is auditable and reproducible. Upgrades are deliberate: you edit the template to point at a new tag when you are ready.

History: an earlier template used `doobidoo/mcp-memory-service:quality-cpu`, which was deprecated upstream and stopped resolving. Specific-version pinning prevents that class of failure.

## Documentation

- [docs/CLIENT_SETUP.md](docs/CLIENT_SETUP.md) -- Claude Desktop and Claude Code configuration (including the Windows `cmd /C` and `node.exe` path bugs).
- [docs/TAILSCALE_SIDECAR_GUIDE.md](docs/TAILSCALE_SIDECAR_GUIDE.md) -- The sidecar deployment pattern, key expiry handling, troubleshooting.
- [docs/CLOUDFLARE_TUNNEL_GUIDE.md](docs/CLOUDFLARE_TUNNEL_GUIDE.md) -- Public HTTPS access with Cloudflare Access SSO.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) -- Failure modes catalog.
- [docs/ADDING_NEW_TEMPLATES.md](docs/ADDING_NEW_TEMPLATES.md) -- Conventions and procedure for adding apps to this repo.

## Adding a new template

See [docs/ADDING_NEW_TEMPLATES.md](docs/ADDING_NEW_TEMPLATES.md) and the [_scaffold/](_scaffold/) directory.

## Support

- Template issues: <https://github.com/WireSpeedComputing/Unraid-Templates/issues>
- Upstream bugs: file against the upstream project (linked in each template's `<Project>` field)
- Security: see [SECURITY.md](SECURITY.md). Use private security advisories at <https://github.com/WireSpeedComputing/Unraid-Templates/security/advisories/new>; do not open public issues for security reports.

## License

Apache 2.0. See [LICENSE](LICENSE).

## About WireSpeed Computing

WireSpeed Computing publishes reference architectures and templates for self-hosted AI infrastructure. These templates are generic-first and designed to work on any Unraid server. Maintained as part of the [WireSpeed platform](https://github.com/WireSpeedComputing).
