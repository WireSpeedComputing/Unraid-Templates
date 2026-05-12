# mcp-memory

Persistent AI memory service with semantic search. Two deployment variants:

- `mcp-memory.xml` -- bridge mode, port published to host LAN.
- `mcp-memory-tailscale.xml` -- shares network namespace with a Tailscale sidecar, no published ports.

Image: `doobidoo/mcp-memory-service:10.49.3-slim` (pinned, not a rolling tag).

Upstream project: <https://github.com/doobidoo/mcp-memory-service>

---

## Which variant should I use?

| Use bridge mode (`mcp-memory.xml`) if... | Use Tailscale sidecar (`mcp-memory-tailscale.xml`) if... |
| --- | --- |
| Single user on a trusted LAN | Multiple devices or multiple physical locations |
| You do not have a Tailscale tailnet | You already run Tailscale or want overlay access |
| You want the simplest possible setup | You need to reach the service from outside your LAN without opening a port |

Both variants run the same image, the same backend, and the same data layout. You can migrate between them later by changing only the network configuration.

For full sidecar setup, see [docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md).

---

## Image tag policy

The template pins to a specific minor version (`:10.49.3-slim`), not a rolling tag.

History: the previous template used `:quality-cpu`, which was deprecated upstream and stopped resolving (`docker pull` returns "manifest unknown"). Pinning to a specific version is auditable and reproducible. You upgrade on your schedule by editing the template, not when an upstream tag silently moves.

---

## Prerequisites

1. **Unraid 6.12 or newer** with Community Applications installed.
2. **An API key.** Generate one before first launch:
   ```
   openssl rand -base64 48
   ```
   Paste it into the `MCP API Key` field of the template. The key is stored masked in the template XML.
3. **(Tailscale variant only)** A Tailscale tailnet and a one-time auth key generated at <https://login.tailscale.com/admin/settings/keys>. See [docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md) for the full walkthrough.

---

## Bridge mode setup

1. In Unraid, Apps -> search "mcp-memory" -> Install the bridge template.
2. Fill in `MCP API Key` (paste the value from `openssl rand -base64 48`).
3. Leave the default paths (`/mnt/user/appdata/mcp-memory/data`, `/mnt/user/appdata/mcp-memory/backups`) unless you have a reason to change them.
4. Apply. First boot will download a ~90MB ONNX embedding model. The container can appear to hang for a few minutes. Watch the log via Docker UI; you will see download progress.
5. Verify the service is up:
   ```
   curl -H "Authorization: Bearer <your-api-key>" http://<unraid-ip>:8000/api/health
   ```
6. Open the dashboard in a browser: `http://<unraid-ip>:8000`

The Unraid container will show "healthy" in the Docker tab once the healthcheck succeeds (about 30 seconds after the HTTP service starts).

---

## Tailscale sidecar setup (summary)

The full walkthrough is in [docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md). The summary:

1. Deploy `tailscale-sidecar` first. **Rename it to `tailscale-mcpmemory`** before applying. Rename the state path from `/mnt/user/appdata/tailscale-sidecar/` to `/mnt/user/appdata/tailscale-mcpmemory/`. Paste a one-time Tailscale auth key.
2. Wait for the sidecar to authenticate. Check the Tailscale admin console -- the new device should appear.
3. **Disable key expiry** on the new device in the Tailscale admin console. Service accounts that never re-auth will disconnect 180 days after first boot if key expiry remains on.
4. Deploy `mcp-memory-tailscale.xml`. The template's Network field is already set to `Container:tailscale-mcpmemory`, so as long as the sidecar exists with that exact name, this container will start.
5. Reach the dashboard from any tailnet device at `http://<sidecar-tailscale-ip>:8000`. Find the IP in the Tailscale admin console under the hostname you set as `TS_HOSTNAME`.

**Why no published port on this variant:** in `--network=container:<sidecar>` mode, only the outer (sidecar) container can publish ports. The inner (mcp-memory) container must not have port mappings, or Docker will reject the configuration. The bind address inside mcp-memory remains `0.0.0.0`.

---

## Client setup (Claude Desktop, Claude Code)

See [docs/CLIENT_SETUP.md](../docs/CLIENT_SETUP.md) for the full client configuration, including:

- The `--allow-http` flag required for non-HTTPS Tailscale URLs.
- The Windows `cmd /C` path-with-spaces bug and how to work around it.
- The Claude Code on Windows node.exe absolute-path pattern.
- Verifying the connection.

---

## API key generation and rotation

```bash
# Generate
openssl rand -base64 48

# Rotate: change the value in the template, restart the container, update all clients.
# There is no in-place key rotation API; the key is read on startup.
```

The key is a single shared bearer token. The service does not currently support per-user or per-client keys. If you need multi-user access control, put the service behind Cloudflare Access or a similar identity-aware proxy.

---

## Backups

The container writes nightly SQLite dumps to `/app/backups` (host: `/mnt/user/appdata/mcp-memory/backups`). Point your host-level backup tool (rclone, Duplicati, restic, Unraid's CA Backup, etc.) at that directory.

**Critical: do NOT use plain `cp` on `memory.db`.** SQLite in WAL mode keeps recent transactions in a separate `memory.db-wal` file. A naive copy of just the main database file loses recent writes. The nightly dump uses SQLite's `backup()` API and is the correct way to snapshot the database. See [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) for the failure mode.

To trigger a manual backup, restart the container or use the upstream dump command (see upstream README).

---

## Migrating from local mcp-memory-service

If you ran `mcp-memory-service` locally (Python venv, not containerized) and want to move that data into this container:

1. **Stop the local service.** Live SQLite writes during migration corrupt the export.
2. **Use the SQLite backup API**, not `cp`, to produce a clean snapshot of `memory.db`:
   ```python
   import sqlite3
   src = sqlite3.connect("memory.db")
   dst = sqlite3.connect("memory-export.db")
   src.backup(dst)
   src.close(); dst.close()
   ```
3. Copy the resulting `memory-export.db` to `/mnt/user/appdata/mcp-memory/data/memory.db` on the Unraid host.
4. `chown -R 99:100 /mnt/user/appdata/mcp-memory` so the container can read and write.
5. Start the container. On first boot it will run schema migrations.
6. **Expect content-hash deduplication.** Schema migrations between v10.27 and v10.49 include content-hash dedupe. If your import had duplicates (same content stored twice), the live count will be lower than the import count. Diff source vs live by `content_hash` to verify dropped records were genuine dupes.

---

## Configuration reference

All template fields map to environment variables documented at the upstream project README. The most commonly adjusted:

| Template field | Env var | Default | Notes |
| --- | --- | --- | --- |
| HTTP Port | (port mapping) | 8000 | Bridge variant only |
| MCP API Key | `MCP_API_KEY` | (empty) | Required. Generate with `openssl rand -base64 48`. |
| HTTP Enabled | `MCP_HTTP_ENABLED` | true | Must be true. |
| Storage Backend | `MCP_MEMORY_STORAGE_BACKEND` | `sqlite_vec` | sqlite_vec is recommended. chroma and hybrid also supported. |
| SQLite Path | `MCP_MEMORY_SQLITE_PATH` | `/app/data/memory.db` | Must be inside the data volume. |
| OAuth Enabled | `MCP_OAUTH_ENABLED` | false | Enable only if you want native OAuth 2.1 (independent of edge auth like Cloudflare Access). |
| Log Level | `LOG_LEVEL` | INFO | Set to DEBUG for troubleshooting. |

PUID=99, PGID=100 are the Unraid defaults for `nobody:users` and should not be changed unless you know why.

---

## Healthcheck

Both variants include a Docker healthcheck:
```
curl -sf http://localhost:8000/api/health || exit 1
```
Interval 30s, timeout 5s, retries 3, start period 30s.

If the HTTP service crashes inside the container, Unraid will show the container as `unhealthy` in the Docker tab. The `localhost` form works in both variants because:

- Bridge: the container's own loopback.
- Sidecar: the container shares the sidecar's network namespace, so `localhost` resolves to the same stack.

---

## Security model

Default deployment protects against:

- Casual network discovery (LAN-only on bridge, tailnet-only on sidecar).
- Unauthenticated reads or writes (the API key gates every endpoint).
- Data loss from container restarts (state on persistent volumes).

Default deployment does NOT protect against:

- A compromised client device. If an attacker steals your API key, they have full read/write access to your memory. Treat the key like a password.
- Plaintext-at-rest. The SQLite database is not encrypted. If you need encryption, encrypt the host volume (LUKS, Unraid encrypted array, etc.).
- Concurrent writers. The service is designed for one server instance per database. Do not point two containers at the same SQLite file.

For a fuller threat model, see [SECURITY.md](../SECURITY.md) at the repo root.

---

## Troubleshooting

Common issues are catalogued in [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md). Highlights:

- **First boot hangs for several minutes** -- ~90MB ONNX embedding model is downloading. Watch the log.
- **Container can't read its volumes** -- run `chown -R 99:100 /mnt/user/appdata/mcp-memory/`.
- **Client returns 401** -- API key mismatch. Check the Authorization header is `Bearer <key>`, not the key alone.
- **Tailscale variant container won't start with "container tailscale-mcpmemory not found"** -- the sidecar isn't deployed, or it has a different name. See [docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md).

---

## Upgrading

The image is pinned to `:10.49.3-slim`. To upgrade:

1. Read the upstream release notes at <https://github.com/doobidoo/mcp-memory-service/releases>.
2. Edit this template to point at the new tag.
3. Apply. The container will pull the new image and run schema migrations on first start (if any).
4. Check the log for migration output. Verify the record count after migration.

The previous image is not deleted automatically. If you want to roll back, edit the template to point at the older tag.
