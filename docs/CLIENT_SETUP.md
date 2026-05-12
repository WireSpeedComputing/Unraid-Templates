# Client setup

How to connect AI clients (Claude Desktop, Claude Code) to MCP services from this repo. The patterns here apply to any MCP-over-HTTP service; the examples are mcp-memory and filesystem-mcp.

This guide focuses on **first-time-setup failure modes** that are not obvious from upstream docs. Every entry below describes a failure encountered firsthand during the WireSpeed deployment.

---

## Prerequisites

- The MCP service is running and reachable. Verify with:
  ```
  curl http://<service-ip>:<port>/api/health
  ```
  (mcp-memory) or
  ```
  curl http://<service-ip>:<port>/
  ```
  (filesystem-mcp).

- For Tailscale sidecar variants: the service IP is the **sidecar's Tailscale IP**, not the Unraid host IP. Find it in the Tailscale admin console.

- `node` and `npm` installed locally (clients spawn `npx mcp-remote` to bridge HTTP/SSE to stdio).

---

## Claude Desktop -- mcp-memory over Tailscale sidecar

`claude_desktop_config.json` location:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Working config:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx.cmd",
      "args": [
        "mcp-remote",
        "http://<sidecar-tailscale-ip>:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer <your-mcp-api-key>"
      ]
    }
  }
}
```

On macOS/Linux replace `npx.cmd` with `npx`.

### Why `--allow-http` is required

`mcp-remote` refuses non-HTTPS URLs by default. If you omit the flag, the Claude Desktop log shows:

```
Error: Non-HTTPS URLs are only allowed for localhost or when --allow-http flag is provided
```

The transport closes immediately after the initial handshake. Adding `--allow-http` explicitly opts in. This is safe over Tailscale because WireGuard provides transport encryption on every packet between tailnet devices.

If you ever expose the service publicly (Cloudflare Tunnel with TLS termination), the URL becomes `https://...` and you can drop `--allow-http`.

### Why `npx.cmd` instead of `npx` on Windows

Claude Desktop on Windows wraps `mcpServers.command` in `cmd.exe /C <command>` **without quoting**. If `command` resolves to an absolute path with spaces (e.g., `C:\Program Files\nodejs\npx.cmd`), Windows splits on the space and tries to execute `C:\Program` with `Files\nodejs\npx.cmd` as an argument. The log shows:

```
'C:\Program' is not recognized as an internal or external command
```

Workaround: use the bare command (`npx.cmd`) and let `PATH` resolve it.

Alternative workaround: install Node in a path without spaces (e.g., `C:\nodejs\`). Then absolute paths work.

### Verifying the connection

After saving the config and restarting Claude Desktop:

1. Open the developer log:
   - Windows: `%APPDATA%\Claude\logs\mcp.log` (or `mcp-server-memory.log`)
   - macOS: `~/Library/Logs/Claude/mcp.log`
2. Confirm you see the MCP initialize handshake succeed and no `Error:` lines.
3. In a chat, ask: "What memories do you have access to?" The model should describe the memory tool.
4. **Ignore stale sidebar warnings.** If you see "Could not attach to MCP server memory" in the sidebar even after a successful connect, dismiss it manually or restart Claude Desktop. The status indicator does not always refresh after a recovered connection. Verify actual state via the log file or a tool call.

---

## Claude Code on Windows -- the node.exe absolute-path pattern

This is the single trickiest setup. Claude Code spawns MCP server subprocesses with a stripped `PATH`. If you point it at a `.cmd` shim (`npx.cmd`, `mcp-remote.cmd`), the shim invokes bare `node` internally, which then fails with:

```
'node' is not recognized as an internal or external command
```

The working pattern is to point at `node.exe` directly and pass the proxy.js absolute path as the first argument.

### Find your absolute paths

```powershell
# Where is node.exe
where.exe node
# Typical: C:\Program Files\nodejs\node.exe

# Where is mcp-remote installed
npm root -g
# Typical: C:\Users\<user>\AppData\Roaming\npm\node_modules
# So proxy.js is at: C:\Users\<user>\AppData\Roaming\npm\node_modules\mcp-remote\dist\proxy.js
```

If you do not have `mcp-remote` installed globally:

```powershell
npm install -g mcp-remote
```

### Config

`%USERPROFILE%\.claude\settings.json` (or whichever Claude Code config the docs point at):

```json
{
  "mcpServers": {
    "memory": {
      "command": "C:\\Program Files\\nodejs\\node.exe",
      "args": [
        "C:\\Users\\<your-user>\\AppData\\Roaming\\npm\\node_modules\\mcp-remote\\dist\\proxy.js",
        "http://<sidecar-tailscale-ip>:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer <your-mcp-api-key>"
      ]
    }
  }
}
```

Notes:

- Both backslashes in JSON paths must be doubled.
- The `command` value here HAS spaces, but Claude Code does not wrap it in `cmd /C`, so spaces are tolerated.
- If you upgrade Node or change install paths, you must update this config.

### Why this pattern

1. `npx.cmd` is a Batch file. It eventually calls `node`. When spawned by Claude Code with a stripped PATH, `node` is not resolvable, and the shim fails.
2. Pointing directly at `node.exe` bypasses the shim and executes the proxy directly.
3. `proxy.js` is the entry point shipped with `mcp-remote`. It is a small wrapper around the SDK.

This pattern also works for Claude Code on macOS and Linux, but it is rarely needed there because PATH propagation is more reliable. On those platforms, the simple `"command": "npx"` form usually works.

---

## macOS prerequisites

If you just installed Homebrew on Apple Silicon, the installer prints three commands you need to run before `brew` is on your PATH:

```bash
echo >> /Users/<user>/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/<user>/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Run them. Restart the shell. Then `brew install node` and proceed.

---

## Linux prerequisites

Use your distro's Node (or nvm). The standard `npm install -g mcp-remote` flow works without the Windows pitfalls described above.

---

## Verifying any MCP-over-HTTP connection

Independent of the client, you can test the service directly:

```bash
# mcp-memory health
curl -H "Authorization: Bearer <key>" http://<service-ip>:8000/api/health

# mcp-memory MCP initialize (basic JSON-RPC handshake)
curl -X POST -H "Authorization: Bearer <key>" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}' \
  http://<service-ip>:8000/mcp
```

If both succeed and your client still cannot connect, the failure is in the client, not the service. Check the client log, then re-read the failure modes above.

---

## Reference: which fixes are required for which client

| Failure | Affects | Fix |
| --- | --- | --- |
| Non-HTTPS URL rejected | All clients using `mcp-remote` over HTTP | `--allow-http` |
| `'C:\Program' is not recognized` | Claude Desktop on Windows | Bare `npx.cmd`, let PATH resolve |
| `'node' is not recognized` from spawned subprocess | Claude Code on Windows | Point at `node.exe` + absolute proxy.js path |
| Stale "Could not attach" warning | Claude Desktop | Restart, or verify via log file |
| Homebrew not on PATH | macOS, fresh install | Run the three `echo`+`eval` commands |

Each of these was hit during the WireSpeed reference deployment. They are documented here so you do not hit them in that order yourself.
