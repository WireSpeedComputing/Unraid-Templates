# filesystem-mcp

MCP filesystem server with Streamable HTTP (SHTTP) transport. Exposes mounted host directories to AI clients (Claude Desktop, Claude Code, and any other MCP client) as file-system tools: read, write, list, move, search.

Image: `mekayelanik/filesystem-mcp:stable`

Upstream image: <https://github.com/mekayelanik/filesystem-mcp-docker>

Upstream MCP filesystem server (the underlying implementation): <https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem>

---

## Why this image instead of the "official" filesystem server

The official `modelcontextprotocol/servers/filesystem` MCP server speaks **stdio only**. It cannot serve HTTP. That makes it incompatible with the Tailscale sidecar pattern this repo standardizes on (the sidecar shares a network namespace; there is no stdio across containers).

`mekayelanik/filesystem-mcp` is a community Docker wrapper that runs the upstream server and exposes it over Streamable HTTP (SHTTP), Server-Sent Events (SSE), or WebSocket (WS). SHTTP is the recommended transport.

Trade-off: a community wrapper is a smaller maintenance surface than the official MCP organization. If that matters for your deployment, vendor the image into your own registry and rebuild from source.

---

## Deployment variant

Tailscale sidecar only. There is no bridge variant for filesystem-mcp because:

- A filesystem server exposed to your LAN with read/write access to host directories is a meaningful security exposure.
- The Tailscale overlay keeps the service device-identity-gated by default.

If you need filesystem-mcp without Tailscale, deploy with `--network=bridge`, publish a port, and put an authenticating reverse proxy in front. That deployment is not templated here.

---

## Prerequisites

1. **A Tailscale tailnet** and a one-time auth key from <https://login.tailscale.com/admin/settings/keys>.
2. **The `tailscale-sidecar` template deployed and RENAMED** to `tailscale-filesystem-mcp`. See [docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md) for the rename procedure.
3. **At least one host directory** you want to expose via MCP. Common choices: a docs/wiki directory, a project workspace, a shared notes folder.

---

## Setup

### 1. Deploy the sidecar

Follow [docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md). Use these names:

- Container name: `tailscale-filesystem-mcp`
- State path: `/mnt/user/appdata/tailscale-filesystem-mcp/`
- `TS_HOSTNAME`: `filesystem-mcp` (or another descriptive name; this is what shows in your Tailscale admin console)

Apply the sidecar template. Wait until the new device appears in your Tailscale admin console. **Disable key expiry** on it.

### 2. Deploy filesystem-mcp

1. In Unraid, Apps -> search "filesystem-mcp" -> Install.
2. The Network field is pre-set to `Container:tailscale-filesystem-mcp`. Do not change it unless your sidecar has a different name.
3. Set the `Data Directory` path mapping. Default is `/mnt/user/appdata/filesystem-mcp/data` -> `/projects/data`. Change the host side to the directory you want to expose.
4. (Optional) Add more `Path` entries via the template UI to expose additional directories. Each must mount under `/projects/<something>` inside the container.
5. Apply.

**The container exits immediately if `/projects/` is empty.** Mount at least one directory.

### 3. Verify

From any device on your tailnet:

```bash
curl http://<sidecar-tailscale-ip>:8001/
```

You should see an MCP handshake response or an HTTP 200. The exact body depends on the upstream wrapper version.

To get `<sidecar-tailscale-ip>`: Tailscale admin console -> Machines -> find the hostname you set as `TS_HOSTNAME` -> copy the 100.x.y.z address.

---

## Client setup

In your MCP client config (Claude Desktop, Claude Code), add a server entry pointing at the sidecar IP and port. See [docs/CLIENT_SETUP.md](../docs/CLIENT_SETUP.md) for the full configuration including:

- Required `--allow-http` flag for non-HTTPS Tailscale URLs.
- The Windows `cmd /C` path bug workaround.
- The Claude Code on Windows `node.exe` absolute-path pattern.

The endpoint URL is:

```
http://<sidecar-tailscale-ip>:8001/
```

(Default port 8001. Change in the template if you have a conflict.)

---

## Configuration reference

| Template field | Env var | Default | Notes |
| --- | --- | --- | --- |
| HTTP Port | `PORT` | 8001 | Listening port. |
| Protocol | `PROTOCOL` | `SHTTP` | Recommended. Also supports `SSE`, `WS`. |
| Data Directory | (path mount) | `/projects/data` | Mount at least one host directory under `/projects/`. |
| CORS Origins | `CORS` | `*` | Restrict in production. |

PUID=99, PGID=100 are Unraid defaults for `nobody:users`.

---

## Security considerations

- **Filesystem-mcp grants read and write access** to whatever you mount. Be deliberate about which directories you expose.
- **No authentication is enforced inside the container.** Access control comes from Tailscale device identity. Anyone on your tailnet can reach the service. If your tailnet has third-party users (vendors, contractors), restrict their access with Tailscale ACLs.
- **Symlinks inside mounted directories** are followed by the upstream server. If a mounted directory contains a symlink pointing outside `/projects/`, the server may follow it. Audit your mounts.
- **No audit log.** The wrapper does not log individual filesystem operations. If you need an audit trail, run the service behind a logging proxy.

---

## Troubleshooting

**Container exits immediately.** `/projects/` is empty. Mount at least one host directory under `/projects/<something>`.

**Client connects but cannot list files.** Check that the mounted host directory is readable by UID 99 (`nobody`). `chown -R 99:100 <host-path>` if needed.

**Sidecar deployed but `Container:tailscale-filesystem-mcp` not found.** The sidecar exists with a different name. Either rename the sidecar, or edit this template's Network field to match.

**Permission denied writing files.** Container is running as PUID/PGID but the host directory is owned by a different user. `chown -R 99:100 <host-path>` to fix.

**`*` CORS too permissive.** Restrict the `CORS` env var to your client origins explicitly.

For more general MCP client failure modes (HTTPS, Windows path bugs, etc.), see [docs/CLIENT_SETUP.md](../docs/CLIENT_SETUP.md) and [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md).
