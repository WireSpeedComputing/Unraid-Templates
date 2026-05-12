# tailscale-sidecar

Generic, reusable Tailscale sidecar template. Joins your Tailscale network and provides an overlay-network attach point for any paired service container.

This is **not a service** -- it does not do anything by itself. It exists so other service containers can share its network namespace via `--network=container:<this-container-name>`.

Image: `tailscale/tailscale:stable`

Upstream: <https://tailscale.com>

---

## When to use this template

Anytime you want to make an Unraid Docker service reachable over your Tailscale tailnet without publishing a port to the host LAN. Used by:

- `mcp-memory-tailscale.xml` (variant of mcp-memory)
- `filesystem-mcp.xml`
- Any future service in this repo with a `-tailscale` variant or a Tailscale-only deployment

---

## CRITICAL: rename before deploying

The template ships with these GENERIC defaults:

- Container name: `tailscale-sidecar`
- State path: `/mnt/user/appdata/tailscale-sidecar/`

If you deploy two sidecars without renaming, BOTH will:

- Claim the same Tailscale node identity (the second auth attempt overwrites the first).
- Write to the same state directory (one corrupts the other).

Per service, RENAME to a service-specific name (e.g., `tailscale-mcpmemory`, `tailscale-filesystem-mcp`) AND rename the state path to match.

The full procedure is in [../docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md).

---

## Quick start

1. Generate a Tailscale auth key: <https://login.tailscale.com/admin/settings/keys>
   - Reusable: NO
   - Ephemeral: NO
   - Expiration: 90 days (key is consumed on first boot; expiration applies only if not used)
2. In Unraid, Apps -> install `tailscale-sidecar`.
3. **Rename the container** to `tailscale-<your-service-name>`.
4. **Rename the state path** to match: `/mnt/user/appdata/tailscale-<your-service-name>/`.
5. Set `TS_HOSTNAME` to the name you want in your Tailscale admin console.
6. Paste the auth key into `TS_AUTHKEY`.
7. Apply.
8. **In Tailscale admin console: disable key expiry** on the new device. Without this, the device disconnects ~180 days after first auth.

Now deploy your service container with `--network=container:tailscale-<your-service-name>`.

---

## Configuration

| Field | Env var | Default | Notes |
| --- | --- | --- | --- |
| Tailscale State | (volume) | `/mnt/user/appdata/tailscale-sidecar/` | RENAME per service. |
| Tailscale Auth Key | `TS_AUTHKEY` | (empty) | One-time. Consumed on first boot. |
| Tailscale Hostname | `TS_HOSTNAME` | `tailscale-sidecar` | Shown in admin console. |
| Userspace Mode | `TS_USERSPACE` | true | Required for Docker without `--cap-add NET_ADMIN`. |
| Auth Once | `TS_AUTH_ONCE` | true | Auth once, persist via state dir. |
| State Directory | `TS_STATE_DIR` | `/state` | Internal path. Matches volume mount. |
| Extra Args | `TS_EXTRA_ARGS` | (empty) | Additional `tailscale` CLI args if you need them. |
| Timezone | `TZ` | `America/New_York` | Container TZ. |

---

## After first boot

The auth key is consumed and the node persists via the state directory. You can clear `TS_AUTHKEY` from the template if you prefer not to leave the spent value in config.

The state directory contains the node's private key. Treat it as sensitive. Back it up to a private location.

---

## Troubleshooting

See [../docs/TAILSCALE_SIDECAR_GUIDE.md](../docs/TAILSCALE_SIDECAR_GUIDE.md) for the full troubleshooting section.

Common quick checks:

- Sidecar starts but does not show up in admin console -> wrong auth key, expired key, or tailnet device quota exceeded.
- Sidecar shows up but service container can't bind -> service container is using `Container:<wrong-name>`. Match the actual sidecar name.
- Was working, now disconnected -> Tailscale key expiry. Disable it on the device, generate a fresh auth key, re-authenticate.

---

## Why not a single shared sidecar for multiple services

The pattern is one sidecar per service:

- Each sidecar is one Tailscale device, with one IP, one identity, and one ACL row.
- Sharing one sidecar across multiple services routes all of them under the same identity. Audit logs become harder to read. ACL policies cannot scope per service.
- Restarting one service does not affect another's sidecar.

If you have a strong reason (device-count constraints, simplicity preference) you can run multiple services through one sidecar by exposing multiple ports on the sidecar's namespace. It works but is harder to reason about.
