# Troubleshooting

Catalog of failure modes encountered during the WireSpeed reference deployment of mcp-memory + filesystem-mcp + Tailscale sidecar on Unraid (2026-05). Organized by symptom-first so you can search for the error message you are seeing.

For client-side issues (Claude Desktop, Claude Code config), see [CLIENT_SETUP.md](CLIENT_SETUP.md). For the sidecar pattern, see [TAILSCALE_SIDECAR_GUIDE.md](TAILSCALE_SIDECAR_GUIDE.md).

---

## Container deployment

### `docker pull doobidoo/mcp-memory-service:quality-cpu` returns "manifest unknown"

The `:quality-cpu` tag is deprecated upstream. It was retired between 2026-Q1 and 2026-Q2.

Fix: use `:10.49.3-slim` (or a newer specific minor version tag). All templates in this repo are pinned to the specific version. If you copied an older template from a blog or forum post, update the tag.

### First boot appears to hang for several minutes

`mcp-memory` downloads a ~90MB ONNX embedding model on first boot. The container can appear to do nothing for 2-5 minutes depending on your internet connection.

Fix: wait. Watch the container log (`docker logs -f mcp-memory`). You will see download progress and then the HTTP server start.

### Container starts but can't read or write its data volume

Symptom: log shows `Permission denied` opening `/app/data/memory.db` or writing to `/app/backups`.

Cause: host directory ownership is wrong. Unraid containers run as PUID/PGID (default 99/100 = `nobody:users`).

Fix:
```
chown -R 99:100 /mnt/user/appdata/mcp-memory/
```

Adjust paths per the directory you're using.

### filesystem-mcp container exits immediately

The upstream image checks for at least one mount under `/projects/` and exits if it finds nothing.

Fix: edit the template to mount a host directory under `/projects/<name>`. The default `Data Directory` field does this; if you removed it, add at least one Path back.

### Healthcheck status `unhealthy` but service responds to curl

Likely causes in order:

1. The container shares a sidecar's network namespace and the healthcheck is running with the wrong loopback interpretation. In `--network=container:<sidecar>`, `localhost` inside the container resolves to the sidecar's loopback, which IS where the service is bound. The healthcheck should work as written.
2. The internal port is not 8000. Check `MCP_HTTP_PORT` in the template.
3. `curl` is not in the image. The `:10.49.3-slim` variant includes it. If you switched to a `:bookworm` or other variant without curl, switch the healthcheck command to `wget` or remove the healthcheck.

---

## SQLite migration and backups

### `cp memory.db` loses recent writes

SQLite in WAL (Write-Ahead Logging) mode keeps recent transactions in `memory.db-wal`. A naive copy of just the `.db` file loses everything that hasn't been checkpointed back into the main file yet.

Fix: use the SQLite `backup()` API to produce a clean snapshot:

```python
import sqlite3
src = sqlite3.connect("memory.db")
dst = sqlite3.connect("memory-clean.db")
src.backup(dst)
src.close()
dst.close()
```

Or use the upstream container's nightly dump (written to `/app/backups`).

Or stop the service cleanly first (which checkpoints WAL into the main file), then copy. But running the live service across the copy and using `cp` is a guaranteed data loss footgun.

### Migration import shows fewer records than source

Symptom: imported 172 records, container reports 167 after first start.

Cause: schema migrations between mcp-memory-service v10.27 and v10.49 include content-hash deduplication. If your source had duplicates (same content text stored twice), they collapse on import.

Fix: this is expected. Verify by diffing source vs live by `content_hash`. If the only differences are duplicates, your data is intact.

### Backups directory is empty

Symptom: `/mnt/user/appdata/mcp-memory/backups/` is empty even after the container has been running for days.

Cause: the upstream container does NOT automatically schedule backups in older versions. Check the upstream README for the version you are running.

Fix:

- Verify which version's backup behavior you expect. If the container writes nightly dumps, check `LOG_LEVEL=DEBUG` for backup-cycle messages.
- If your version doesn't auto-backup, schedule a host-side cron that triggers the dump manually (e.g., `docker exec mcp-memory <command>` -- consult upstream README for the correct command).
- Always back up `/mnt/user/appdata/mcp-memory/data/` at the host level via your normal backup tool (rclone, Duplicati, etc.) regardless.

---

## Client setup

(Detailed coverage in [CLIENT_SETUP.md](CLIENT_SETUP.md). The short version below.)

### "Non-HTTPS URLs are only allowed for localhost or when --allow-http flag is provided"

`mcp-remote` refuses plain-HTTP URLs without explicit opt-in.

Fix: add `--allow-http` to the args. Safe over Tailscale; WireGuard provides transport encryption.

### Windows: `'C:\Program' is not recognized as an internal or external command`

Claude Desktop wraps the command in `cmd /C` without quoting. Absolute paths with spaces (`C:\Program Files\nodejs\npx.cmd`) get split.

Fix: use bare `npx.cmd`, let PATH resolve. OR install Node in a path without spaces.

### Windows: `'node' is not recognized` from a spawned subprocess (Claude Code)

`.cmd` shims invoke bare `node`. Claude Code spawns subprocesses with a stripped PATH, so `node` is not resolvable.

Fix: point at `node.exe` absolute path + `proxy.js` absolute path. Full pattern in [CLIENT_SETUP.md](CLIENT_SETUP.md).

### Claude Desktop sidebar shows "Could not attach to MCP server memory" after successful connect

UI state lag. The status indicator does not always refresh after a recovered connection.

Fix: dismiss manually or restart Claude Desktop. Verify actual state via the log file or a tool call.

---

## Tailscale sidecar

### "container tailscale-mcpmemory not found"

The service template references a sidecar by exact name, but the sidecar was deployed under a different name (typically the generic `tailscale-sidecar` because the user didn't rename it).

Fix: rename the sidecar (full procedure in [TAILSCALE_SIDECAR_GUIDE.md](TAILSCALE_SIDECAR_GUIDE.md)), OR edit the service template's Network field to point at your actual sidecar name.

### Sidecar starts, never appears in Tailscale admin console

Order of likelihood:

1. Wrong auth key (typo, or the key was already consumed by a previous deployment attempt).
2. Auth key expired before first use.
3. Tailscale free-tier device quota exceeded.
4. Egress blocked. Sidecar needs outbound UDP/TCP to Tailscale's edge servers.

Check `docker logs <sidecar-name>` for the specific error.

### Service was working, suddenly unreachable after months

Most common cause: Tailscale key expiry. The default 180-day expiry silently disconnects service accounts.

Fix: in admin console, find the device, check Expiration status. Generate a fresh auth key, re-auth, AND disable key expiry on the device so it doesn't recur.

### Free-tier auto-downgrade missing

Tailscale does NOT auto-downgrade from a paid trial. If your trial ends, you'll get billed.

Fix: explicitly downgrade in the admin console before or shortly after trial end.

### Two services accidentally sharing one sidecar's state directory

Symptom: one sidecar mysteriously "disappears" from the admin console after the other one boots.

Cause: both deployed with default `/mnt/user/appdata/tailscale-sidecar/` state path. Each one's first boot overwrites the other's identity.

Fix: see [TAILSCALE_SIDECAR_GUIDE.md](TAILSCALE_SIDECAR_GUIDE.md) "State path collision" section.

### Inner container fails to start with a port-publish error

You added `-p 8000:8000` (or similar) to the service container in sidecar mode. In `--network=container:X`, only the outer container can publish ports.

Fix: remove all port mappings from the inner container. The bind address inside should remain `0.0.0.0:<port>`, but no Docker-level port publishing.

---

## API and access

### Client returns 401 Unauthorized

The API key in the client doesn't match `MCP_API_KEY` in the container.

Fix: verify the header is `Authorization: Bearer <key>` and the key matches exactly (no leading/trailing whitespace, base64 padding intact).

If you rotated the key on the server, restart the container (the key is read on startup) and update all clients.

### Client returns 403 Forbidden

This is uncommon. mcp-memory-service typically returns 401 for unauthenticated and 200 for authenticated. A 403 suggests an authenticating proxy (Cloudflare Access, an OAuth layer) is rejecting the request before it reaches the service.

Fix: check your edge auth configuration, not the service.

### Client connects but the model can't find a tool to call

The MCP handshake succeeded but the tool wasn't registered. Common causes:

1. The MCP server crashed after handshake (check `docker logs`).
2. The client cached an empty tool list. Restart the client.
3. The model isn't aware of the tool's name. Ask explicitly: "What tools do you have access to?"

---

## Container update procedure

1. Read upstream release notes. Tag changes between minor versions can introduce schema migrations or new required env vars.
2. **Take a backup** of `/mnt/user/appdata/mcp-memory/data/` first. Use `sqlite3 ... backup()` or stop the container cleanly before copying.
3. Edit the template to point at the new tag.
4. Apply. The container pulls the new image and starts. Schema migrations (if any) run on first start.
5. Watch the container log for migration progress.
6. Verify the record count matches expectations (allowing for dedupe -- see "Migration import shows fewer records" above).

If anything goes wrong, the old image is still on the host (`docker image ls`). Edit the template back to the previous tag.

---

## Diagnostic info to collect when filing an issue

If you open an issue at <https://github.com/WireSpeedComputing/Unraid-Templates/issues>, please include:

- Unraid version (`uname -a` and Unraid build).
- Container image and tag from your template (`docker inspect <container> | grep Image`).
- Last 50 lines of the container log (`docker logs --tail 50 <container>`).
- Network mode and (for sidecar) the sidecar container name.
- Whether you copied the template from this repo as-is, or modified fields (note which fields).
- For client-side issues: client name and version, OS, and the relevant log file from the client.

Do NOT include API keys, auth keys, or Tailscale node IPs. Redact before pasting.
