# Security policy

## Reporting a vulnerability

If you find a security issue in these templates, the install docs, or the sidecar pattern, please report it privately. **Do not open a public issue.**

**Report path:** open a private security advisory at
<https://github.com/WireSpeedComputing/Unraid-Templates/security/advisories/new>

GitHub's private security advisories let you describe the issue, attach proofs of concept, and discuss disclosure timing with the maintainers in a private thread. You do not need a separate mailbox.

When reporting, include:

- A description of the issue and what it allows an attacker to do.
- Minimal reproduction steps on a clean Unraid deployment.
- The commit SHA or release tag of the template you tested against.
- Whether you have already disclosed the issue elsewhere.

## What we ask

- Do not publicly disclose until we have had a chance to investigate and respond.
- Do not test against deployments you do not own.
- Do not exfiltrate data, retain it, or use it for any purpose beyond confirming the issue.

## What you can expect

- Acknowledgment of your report within 5 business days.
- Initial assessment within 10 business days.
- Status updates at least every 2 weeks until resolution.
- Public disclosure coordinated with you after a fix is available.

## Security scope

**This repo covers:**

- Default values shipped in the Unraid Docker template XML files (env vars, port mappings, volume permissions).
- The recommended sidecar deployment pattern as documented in `docs/TAILSCALE_SIDECAR_GUIDE.md`.
- The recommended client setup as documented in `docs/CLIENT_SETUP.md`.

**This repo does NOT cover:**

- Vulnerabilities in the upstream container images. Report those to the upstream maintainer:
  - mcp-memory-service: <https://github.com/doobidoo/mcp-memory-service>
  - filesystem-mcp (community wrapper): <https://github.com/mekayelanik/filesystem-mcp-docker>
  - The underlying MCP filesystem server: <https://github.com/modelcontextprotocol/servers>
  - Tailscale: <https://tailscale.com/security>
- Vulnerabilities in Unraid, Docker, Cloudflare, or any third-party identity provider. Report to that vendor.
- Misconfigurations introduced by an operator deviating from the documented setup. We can advise but cannot patch operator policy.

---

## Threat model (default sidecar deployment)

The default deployment with the Tailscale sidecar pattern protects against:

- **Casual network discovery.** No ports are published to the host. The service is only reachable from devices on the operator's Tailscale tailnet.
- **Unauthenticated reads or writes** (mcp-memory). A shared bearer token is required on every request.
- **Data loss from container restarts.** State is on persistent host volumes; the SQLite database is checkpointed via WAL.
- **Transport eavesdropping.** WireGuard encryption between tailnet devices.

The default deployment does NOT protect against:

- **A compromised client device.** If an attacker steals the API key from your laptop or your Claude Desktop config, they have full read/write access to your memory. Treat the key like a password.
- **Plaintext-at-rest.** The SQLite database (mcp-memory) and the mounted directories (filesystem-mcp) are not encrypted. If you need encryption at rest, encrypt the host volume (LUKS, Unraid encrypted array, ZFS encryption, etc.).
- **Concurrent writers** to the SQLite database. The service is designed for one instance per database. Do not point two containers at the same data directory.
- **Tailnet-level lateral movement.** Anyone on your tailnet can reach the service. If your tailnet includes third-party users (vendors, contractors), restrict their access with Tailscale ACLs.
- **Filesystem traversal via symlinks** (filesystem-mcp). If a mounted directory contains a symlink pointing outside `/projects/`, the wrapper may follow it. Audit your mounts.

If your report describes a way to circumvent two or more of the protections in the first list, treat it as high severity and include reproduction notes.

---

## Credential handling

These templates rely on secrets (`MCP_API_KEY`, `TS_AUTHKEY`, OAuth secrets if enabled). General hygiene:

- **Generate locally**, paste directly into the Unraid template field via the web UI. Mask=true is set on every secret field so the value will not appear in plaintext in the rendered template.
- **Never paste secrets into AI assistant chats.** AI providers' policies on chat retention vary; the safe default is to assume any value pasted into a chat is logged. Generate the secret yourself, paste into the destination form, and refer to the secret by name (e.g., "the API key in MCP_API_KEY") in conversation.
- **Rotate on suspicion of compromise.** Generate a new key, update the template, restart the container, update all clients. There is no in-place key rotation API.
- **Auth keys are single-use.** A Tailscale auth key is consumed on the sidecar's first successful join. After that, the spent value in the template has no power; you can clear it if you prefer.

---

## Defense in depth options

If your deployment requires stronger guarantees:

- **Cloudflare Access** in front of mcp-memory provides identity-aware access control with SSO. See `docs/CLOUDFLARE_TUNNEL_GUIDE.md` for the tunnel setup; the Access layer sits between the tunnel and the service.
- **Encrypted host volumes** protect against host compromise where the attacker has read access to disk but not running memory.
- **Tailscale ACLs** scope access to specific users or tags within a tailnet.
- **A reverse proxy with rate limiting** (Nginx, Caddy, Traefik) added in front of the service can absorb credential-stuffing attempts.

These are not the default because the default is "one user on a private tailnet" -- the simplest deployment that works. Each defense-in-depth layer adds operational surface area; add them when the threat model requires it.
