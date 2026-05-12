# Tailscale sidecar guide

Pattern: a small `tailscale/tailscale:stable` container ("the sidecar") joins your Tailscale network. A second container ("the service") shares the sidecar's network namespace and is reachable only over the Tailscale overlay. No ports are published to the host.

This guide is the reference for every service in this repo that uses the sidecar pattern (mcp-memory-tailscale, filesystem-mcp).

---

## What you get

- **Identity-gated access.** Only devices on your Tailscale network can reach the service. ACLs let you scope per user.
- **No open ports on your firewall.** The sidecar dials out to Tailscale; nothing inbound.
- **No TLS termination on your side.** WireGuard provides transport encryption end-to-end.
- **Mobile and remote access.** Connect from a laptop in a cafe or a phone on cellular without changing anything.

## What you give up

- Slight latency overhead vs. LAN-local bridge.
- A Tailscale account dependency. (Free tier supports 100 devices.)
- Each service needs its own sidecar container -- the pattern does not multiplex multiple services through one sidecar (you would have to share the namespace **and** publish multiple internal ports, which works but is harder to reason about).

---

## Sidecar architecture

```
[Tailscale tailnet]
        |
        |  WireGuard
        v
+---------------------------+
| tailscale-<service>       |  <-- container in bridge mode, joins tailnet
|   network namespace       |
| +-----------------------+ |
| | <service>             | |  <-- container with --network=container:tailscale-<service>
| |   listens on :PORT    | |       inherits the sidecar's network namespace
| +-----------------------+ |
+---------------------------+
```

Why this works: the inner container "sees" only the sidecar's network. It binds its socket to `0.0.0.0:PORT`, which is the sidecar's network interface. Traffic arriving on the sidecar's tailscale-ip:PORT lands directly in the inner container's socket. No NAT, no userland forwarder.

Why the inner container must NOT publish a port: in `--network=container:X` mode, only the outer container can publish. Adding `-p 8000:8000` to the inner container is a Docker config error and the container will refuse to start.

---

## Per-service deployment procedure

The generic `tailscale-sidecar` template ships with the **generic default name** `tailscale-sidecar` and the **generic default state path** `/mnt/user/appdata/tailscale-sidecar/`. You MUST rename per service before deploying. If you don't, two services will collide on the same Tailscale node identity and the same state directory.

For each service:

### 1. Decide on names

| Service | Sidecar container name | Sidecar state path | TS_HOSTNAME |
| --- | --- | --- | --- |
| mcp-memory | `tailscale-mcpmemory` | `/mnt/user/appdata/tailscale-mcpmemory/` | `mcp-memory` (or your preferred name) |
| filesystem-mcp | `tailscale-filesystem-mcp` | `/mnt/user/appdata/tailscale-filesystem-mcp/` | `filesystem-mcp` (or your preferred name) |

For other services, follow the same pattern: container name `tailscale-<service-short-name>`, state path matching, `TS_HOSTNAME` is what appears in your Tailscale admin console.

### 2. Generate a Tailscale auth key

1. Open <https://login.tailscale.com/admin/settings/keys>.
2. Click "Generate auth key."
3. Settings:
   - **Reusable: NO.** One service per key.
   - **Ephemeral: NO.** This is a persistent service.
   - **Expiration: 90 days** (or your preferred policy; the key is consumed on first boot regardless).
   - **Tags:** add `tag:server` or similar if you use ACL tagging.
4. Copy the key. It is shown once.

### 3. Deploy the sidecar

1. In Unraid, Apps -> install `tailscale-sidecar`.
2. **Rename the container** to your chosen sidecar name (e.g., `tailscale-mcpmemory`).
3. **Edit the Tailscale State path** to match (e.g., `/mnt/user/appdata/tailscale-mcpmemory/`).
4. Set `TS_HOSTNAME` to the name you want in your Tailscale admin console.
5. Paste the auth key into `TS_AUTHKEY`.
6. Apply.

The container should start and report success to Tailscale within ~30 seconds. Check the container log:

```
docker logs <sidecar-name>
```

You should see lines like `tailscale up: success` and the node's tailnet IP.

### 4. Disable key expiry on the new device

In the Tailscale admin console (<https://login.tailscale.com/admin/machines>):

1. Find the new device by its `TS_HOSTNAME`.
2. Open the device's settings (three-dot menu).
3. **Disable key expiry.** Service accounts that never re-authenticate will disconnect at the 180-day mark if key expiry remains on, and the service silently becomes unreachable.

This is one of the most important non-obvious steps. It is the difference between a deployment that works for years and one that mysteriously goes down after six months.

### 5. Deploy the service

Now deploy the service template (e.g., `mcp-memory-tailscale.xml`). It is preconfigured with the matching `Container:tailscale-<service>` reference. As long as your sidecar exists with that exact name, the service will start.

### 6. Reach the service

From any device on your tailnet:

```bash
# Find the sidecar's tailnet IP
# Tailscale admin console -> Machines -> <your TS_HOSTNAME> -> copy 100.x.y.z

# Verify the service responds
curl http://<sidecar-tailscale-ip>:<service-port>/
```

For mcp-memory the dashboard is at `http://<sidecar-tailscale-ip>:8000`. For filesystem-mcp the SHTTP endpoint is at `http://<sidecar-tailscale-ip>:8001/`.

---

## Operational notes

### Auth key behavior

The auth key is consumed on **first successful join**. After that, the node's identity persists via the state directory, and `TS_AUTHKEY` is no longer required. You can safely clear the variable in the template after first boot if you prefer not to keep the (now-spent) key in the template config.

If the state directory is lost (volume deleted), the node loses its identity. You will need a new auth key to re-join.

### State directory

The state directory contains the node's private key and tailnet metadata. It is sensitive. Back it up to a private location (not a public mirror).

Path is `/mnt/user/appdata/<sidecar-name>/` on the host, mounted as `/state` inside the container. The default volume is named accordingly.

### Free tier

The Tailscale free tier supports up to 100 devices and 3 users. If you exceed that, you need a paid plan. Critically: **Tailscale does not auto-downgrade.** If you start a paid trial and then stop using it, you will get billed when the trial ends. Downgrade explicitly in the admin console before or shortly after trial end.

### Health and monitoring

The sidecar does not include a healthcheck out of the box. If you want one, the simplest approach is host-level monitoring (Beszel, Uptime Kuma) querying the service through the sidecar's tailnet IP.

A future version of this template may include a sidecar healthcheck that runs `tailscale status` and exits nonzero if not connected.

### Restarting the service container

The service container can be restarted freely. The sidecar container keeps the tailnet identity warm. If you restart the SIDECAR, the service container loses its network for the duration of the restart and will need to be restarted afterward (Docker does not auto-reconnect across sidecar restarts in `--network=container:X` mode).

### Restarting the sidecar

Restart works, but the service container will be unreachable until you also restart it. The order matters:

```
docker restart tailscale-<service>
docker restart <service>
```

### Updating Tailscale

Updating the sidecar image (`tailscale/tailscale:stable`) is safe. The state directory persists across updates and the node identity is preserved.

### Renaming a deployed sidecar

If you deployed with the generic default `tailscale-sidecar` name and want to rename:

1. Stop the service container.
2. Stop the sidecar.
3. Rename the host state directory (move, don't copy: `mv /mnt/user/appdata/tailscale-sidecar /mnt/user/appdata/tailscale-mcpmemory`).
4. Update the sidecar template's container name and state path. Apply.
5. Update the service template's Network field to `Container:tailscale-mcpmemory`. Apply.

The node identity is preserved because it lives in the state directory.

---

## Troubleshooting

### Service container fails to start: "container tailscale-mcpmemory not found"

The sidecar with that exact name does not exist. Either:

- The sidecar was deployed under a different name. Either rename it (procedure above) or change the service template's Network field to match.
- The sidecar was deployed but is currently stopped. Start it.
- A typo. Check both names with `docker ps -a`.

### Sidecar starts but does not appear in Tailscale admin console

- Wrong or expired auth key. Generate a fresh one and re-deploy.
- Tailscale account quota exceeded (free tier limit). Check the admin console.
- Network egress blocked. The sidecar needs outbound UDP and TCP to Tailscale's edge. Check Unraid firewall and any upstream firewall.

Container log will usually show the cause:

```
docker logs <sidecar-name>
```

### Service is reachable from the LAN but not from a remote tailnet device

- Subnet routing or exit-node settings on a different device are intercepting the request. Check that device's Tailscale state.
- The service is binding to `127.0.0.1` instead of `0.0.0.0`. Check the service container's bind address in its config.

### Service was working, suddenly unreachable

Most common cause: **Tailscale key expiry kicked in** on the sidecar. The default 180-day expiry will silently disconnect the device.

Check the admin console -> the sidecar's device entry -> look for "Expired" status. If expired:

1. Generate a fresh auth key.
2. Either re-deploy the sidecar with the new key in `TS_AUTHKEY`, or run `tailscale login --authkey=<key>` inside the running container to re-auth in place.
3. **This time, disable key expiry on the device** so it does not happen again.

### Two services accidentally sharing one sidecar's network namespace

Don't do this. The pattern is one sidecar per service. Mixing services means a single Tailscale device identity routes for multiple ports, which is fine technically but confuses ACL policies and audit logs. Worth being explicit.

### State path collision (two sidecars writing to one directory)

If you deployed two sidecars with the same `/state` host mount, one will overwrite the other's identity on next boot. Symptom: the "lost" sidecar disappears from the admin console.

Recovery:

1. Stop both sidecars.
2. Pick which one should keep the existing state. Leave its state path alone.
3. For the other, give it a fresh empty state path AND a fresh auth key.
4. Start it. It will register as a new device.

---

## Sources

This guide is consolidated from the WireSpeed deployment of mcp-memory + Tailscale sidecar on Unraid (2026-05). The patterns documented here were validated on a live deployment, not theoretical.
