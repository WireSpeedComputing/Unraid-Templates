# Cloudflare Tunnel guide

How to expose a service from this repo through a Cloudflare Tunnel with optional Cloudflare Access SSO. Use this when:

- You need public HTTPS access (not just tailnet access).
- You want identity-aware access via SSO (Google, GitHub, Okta, etc.).
- You do not want to open inbound ports on your firewall.

---

## Status

**Documented for completeness. The WireSpeed reference deployment uses the Tailscale sidecar pattern exclusively.** This Cloudflare Tunnel path is supported by the upstream `cloudflare/cloudflared` image and has been validated in adjacent deployments, but it has not been operated as the primary access path in production by WireSpeed Computing.

For tailnet-style overlay access, prefer [TAILSCALE_SIDECAR_GUIDE.md](TAILSCALE_SIDECAR_GUIDE.md). For team or public access with SSO, this guide.

---

## When to use Cloudflare Tunnel vs Tailscale sidecar

| Tailscale sidecar | Cloudflare Tunnel + Access |
| --- | --- |
| Internal: only your devices | External: public hostname with identity-gated SSO |
| WireGuard transport encryption | TLS at Cloudflare edge |
| Free tier covers 100 devices | Free tier covers 50 Access users |
| Requires Tailscale client on each device | Works in any browser, no client needed |
| Low operational complexity | Moderate operational complexity (DNS, Access policies) |

Many WireSpeed deployments will run both: Tailscale sidecar as the everyday path, Cloudflare Tunnel + Access as the share-with-a-collaborator path.

---

## Path 1: add a route to an existing tunnel

If you already run `cloudflared` for other services:

1. Open the Cloudflare Zero Trust dashboard.
2. Networks -> Tunnels -> your tunnel -> Public Hostname -> Add a public hostname.
3. Subdomain: `memory`. Domain: your public domain. Path: leave blank.
4. Service: `HTTP`. URL: `mcp-memory:8000`.
5. Save.

This requires the `cloudflared` container and the `mcp-memory` container to share a Docker network so `cloudflared` can resolve `mcp-memory:8000`. The simplest way is to put both on the standard `bridge` network and rely on Docker DNS, or create a user-defined bridge for the pair.

The DNS record is created automatically. Verify the route shows healthy a few minutes after saving.

Trade-off: mixing the memory service with unrelated services on the same tunnel makes audit logs noisier and revocation harder. Path 2 (dedicated tunnel) is cleaner.

---

## Path 2: create a dedicated tunnel

### 1. Create the tunnel

1. Cloudflare Zero Trust dashboard.
2. Networks -> Tunnels -> Create a tunnel.
3. Name: `wirespeed-platform` (or any descriptive name).
4. Save. Cloudflare provides a tunnel token. Copy it. Treat it like a password.

### 2. Run cloudflared on Unraid

In Unraid Docker (no template included in this repo for cloudflared; use the upstream image directly):

- Repository: `cloudflare/cloudflared:latest` (pin to a digest in production).
- Network type: bridge or a user-defined Docker network shared with the service container.
- Extra params: `--restart=unless-stopped`.
- Post args: `tunnel run --token <TOKEN>`.

Apply. The Cloudflare dashboard should show the tunnel as healthy within 30 seconds.

Alternative: set `TUNNEL_TOKEN` as an env var instead of passing on the command line. Either works.

### 3. Add the route

1. Networks -> Tunnels -> your tunnel -> Public Hostname -> Add a public hostname.
2. Subdomain: `memory`. Domain: your public domain. Path: leave blank.
3. Service: `HTTP`. URL: `mcp-memory:8000`.
4. Save.

If the `mcp-memory` container is not running yet, Cloudflare's health check will fail until it is. This is fine; the route configuration itself is valid.

### 4. Verify

After both `cloudflared` and `mcp-memory` are running:

```bash
docker exec cloudflared cloudflared tunnel info <tunnel-id>
```

From a browser, navigate to `https://memory.<your-domain>`. If Access is configured, you should see the SSO flow. If Access is not yet configured, the request reaches the memory service unauthenticated, which is incorrect for production. Configure Access immediately (next section).

---

## Cloudflare Access setup

1. Cloudflare Zero Trust dashboard.
2. Access -> Applications -> Add an application.
3. Type: Self-hosted.
4. Application name: `mcp-memory` (or your preferred label).
5. Session duration: 24 hours is a reasonable default.
6. Application domain: `memory.<your-domain>`.
7. Identity providers: enable the ones you use (Google, GitHub, Okta, OneLogin, etc.).
8. Save.
9. Add a policy:
   - Name: `Allow operators`
   - Action: Allow
   - Include rule: Emails -> add your email(s), OR Email domain -> your company domain, OR specific identity provider groups.
   - Save.

You can also add a service-token rule for programmatic access from CI or scheduled tasks; configure that separately and pass the service token in the `Cf-Access-Client-Id` and `Cf-Access-Client-Secret` headers.

---

## Validating the JWT inside mcp-memory

For defense in depth, mcp-memory-service can validate the Cloudflare Access JWT (`Cf-Access-Jwt-Assertion` header) as a required gate, refusing requests that arrive without a valid JWT from your configured Access application.

Check the upstream README for the current env var names and behavior. If supported, you set:

- The Cloudflare Access certs URL for your team domain.
- The audience (AUD) tag of the Access application (visible in the Access app's settings).

With JWT validation enabled, even if someone discovers the origin URL directly (e.g., via the Cloudflare-tunnel container's network), they cannot reach the service without a JWT from your Access flow.

---

## Notes on tunnel hygiene

- Run one tunnel per logical platform. Avoid mixing unrelated services on one tunnel.
- Pin `cloudflare/cloudflared` to an image digest in production, not the rolling `:latest`.
- Tunnel tokens are sensitive. Rotate the tunnel if the token is exposed.
- The `cloudflared` container reaches origin services by their Docker network hostnames (e.g., `mcp-memory:8000`), not by host IPs. Nothing should be published to the host for this pattern.
- The internal traffic between `cloudflared` and the service is plain HTTP on a Docker bridge. The bridge is isolated from the host network namespace; TLS at the bridge layer adds no security in this topology.

---

## Troubleshooting

**Tunnel shows unhealthy.** Token is wrong, container has no outbound internet, or Cloudflare's edge is rejecting the connection. Container log (`docker logs cloudflared`) shows the cause.

**Public hostname returns 502.** Internal target not reachable from the `cloudflared` container. Confirm both containers share a Docker network and the target name matches the container name exactly.

**SSO redirect goes to a Cloudflare error page.** Access application has no policy that allows the user, or the identity provider integration has an error. Re-check the Access policy.

**Service responds publicly but JWT is not enforced.** Cloudflare Access is not protecting the application. Verify the Access application's domain matches the public hostname exactly, and that at least one policy is configured.

---

## Why this is NOT the default in this repo

The WireSpeed reference deployment is a single-operator setup where every access device runs Tailscale. The Tailscale sidecar pattern is simpler, has fewer moving parts, and does not depend on a third-party SSO provider.

Cloudflare Tunnel + Access is the right answer when:

- You need to share access with people who do not have Tailscale.
- You need a public URL (e.g., for a webhook receiver).
- You want SSO with audit log integration.

If none of those apply, save yourself the operational surface and use the sidecar pattern.
