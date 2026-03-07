Overview
Tools
OpenClaw exposes first-class agent tools for browser, canvas, nodes, and cron. These replace the old openclaw-\* skills: the tools are typed, no shelling, and the agent should rely on them directly.
​
Disabling tools
You can globally allow/deny tools via tools.allow / tools.deny in openclaw.json (deny wins). This prevents disallowed tools from being sent to model providers.
{
tools: { deny: ["browser"] },
}
Notes:
Matching is case-insensitive.

- wildcards are supported ("_" means all tools).
  If tools.allow only references unknown or unloaded plugin tool names, OpenClaw logs a warning and ignores the allowlist so core tools stay available.
  ​
  Tool profiles (base allowlist)
  tools.profile sets a base tool allowlist before tools.allow/tools.deny. Per-agent override: agents.list[].tools.profile.
  Profiles:
  minimal: session_status only
  coding: group:fs, group:runtime, group:sessions, group:memory, image
  messaging: group:messaging, sessions_list, sessions_history, sessions_send, session_status
  full: no restriction (same as unset)
  Example (messaging-only by default, allow Slack + Discord tools too):
  {
  tools: {
  profile: "messaging",
  allow: ["slack", "discord"],
  },
  }
  Example (coding profile, but deny exec/process everywhere):
  {
  tools: {
  profile: "coding",
  deny: ["group:runtime"],
  },
  }
  Example (global coding profile, messaging-only support agent):
  {
  tools: { profile: "coding" },
  agents: {
  list: [
  {
  id: "support",
  tools: { profile: "messaging", allow: ["slack"] },
  },
  ],
  },
  }
  ​
  Provider-specific tool policy
  Use tools.byProvider to further restrict tools for specific providers (or a single provider/model) without changing your global defaults. Per-agent override: agents.list[].tools.byProvider.
  This is applied after the base tool profile and before allow/deny lists, so it can only narrow the tool set. Provider keys accept either provider (e.g. google-antigravity) or provider/model (e.g. openai/gpt-5.2).
  Example (keep global coding profile, but minimal tools for Google Antigravity):
  {
  tools: {
  profile: "coding",
  byProvider: {
  "google-antigravity": { profile: "minimal" },
  },
  },
  }
  Example (provider/model-specific allowlist for a flaky endpoint):
  {
  tools: {
  allow: ["group:fs", "group:runtime", "sessions_list"],
  byProvider: {
  "openai/gpt-5.2": { allow: ["group:fs", "sessions_list"] },
  },
  },
  }
  Example (agent-specific override for a single provider):
  {
  agents: {
  list: [
  {
  id: "support",
  tools: {
  byProvider: {
  "google-antigravity": { allow: ["message", "sessions_list"] },
  },
  },
  },
  ],
  },
  }
  ​
  Tool groups (shorthands)
  Tool policies (global, agent, sandbox) support group:_ entries that expand to multiple tools. Use these in tools.allow / tools.deny.
  Available groups:
  group:runtime: exec, bash, process
  group:fs: read, write, edit, apply*patch
  group:sessions: sessions_list, sessions_history, sessions_send, sessions_spawn, session_status
  group:memory: memory_search, memory_get
  group:web: web_search, web_fetch
  group:ui: browser, canvas
  group:automation: cron, gateway
  group:messaging: message
  group:nodes: nodes
  group:openclaw: all built-in OpenClaw tools (excludes provider plugins)
  Example (allow only file tools + browser):
  {
  tools: {
  allow: ["group:fs", "browser"],
  },
  }
  ​
  Plugins + tools
  Plugins can register additional tools (and CLI commands) beyond the core set. See Plugins for install + config, and Skills for how tool usage guidance is injected into prompts. Some plugins ship their own skills alongside tools (for example, the voice-call plugin).
  Optional plugin tools:
  Lobster: typed workflow runtime with resumable approvals (requires the Lobster CLI on the gateway host).
  LLM Task: JSON-only LLM step for structured workflow output (optional schema validation).
  Diffs: read-only diff viewer and PNG or PDF file renderer for before/after text or unified patches.
  ​
  Tool inventory
  ​
  apply_patch
  Apply structured patches across one or more files. Use for multi-hunk edits. Experimental: enable via tools.exec.applyPatch.enabled (OpenAI models only). tools.exec.applyPatch.workspaceOnly defaults to true (workspace-contained). Set it to false only if you intentionally want apply_patch to write/delete outside the workspace directory.
  ​
  exec
  Run shell commands in the workspace.
  Core parameters:
  command (required)
  yieldMs (auto-background after timeout, default 10000)
  background (immediate background)
  timeout (seconds; kills the process if exceeded, default 1800)
  elevated (bool; run on host if elevated mode is enabled/allowed; only changes behavior when the agent is sandboxed)
  host (sandbox | gateway | node)
  security (deny | allowlist | full)
  ask (off | on-miss | always)
  node (node id/name for host=node)
  Need a real TTY? Set pty: true.
  Notes:
  Returns status: "running" with a sessionId when backgrounded.
  Use process to poll/log/write/kill/clear background sessions.
  If process is disallowed, exec runs synchronously and ignores yieldMs/background.
  elevated is gated by tools.elevated plus any agents.list[].tools.elevated override (both must allow) and is an alias for host=gateway + security=full.
  elevated only changes behavior when the agent is sandboxed (otherwise it’s a no-op).
  host=node can target a macOS companion app or a headless node host (openclaw node run).
  gateway/node approvals and allowlists: Exec approvals.
  ​
  process
  Manage background exec sessions.
  Core actions:
  list, poll, log, write, kill, clear, remove
  Notes:
  poll returns new output and exit status when complete.
  log supports line-based offset/limit (omit offset to grab the last N lines).
  process is scoped per agent; sessions from other agents are not visible.
  ​
  loop-detection (tool-call loop guardrails)
  OpenClaw tracks recent tool-call history and blocks or warns when it detects repetitive no-progress loops. Enable with tools.loopDetection.enabled: true (default is false).
  {
  tools: {
  loopDetection: {
  enabled: true,
  warningThreshold: 10,
  criticalThreshold: 20,
  globalCircuitBreakerThreshold: 30,
  historySize: 30,
  detectors: {
  genericRepeat: true,
  knownPollNoProgress: true,
  pingPong: true,
  },
  },
  },
  }
  genericRepeat: repeated same tool + same params call pattern.
  knownPollNoProgress: repeating poll-like tools with identical outputs.
  pingPong: alternating A/B/A/B no-progress patterns.
  Per-agent override: agents.list[].tools.loopDetection.
  ​
  web_search
  Search the web using Perplexity, Brave, Gemini, Grok, or Kimi.
  Core parameters:
  query (required)
  count (1–10; default from tools.web.search.maxResults)
  Notes:
  Requires an API key for the chosen provider (recommended: openclaw configure --section web).
  Enable via tools.web.search.enabled.
  Responses are cached (default 15 min).
  See Web tools for setup.
  ​
  web_fetch
  Fetch and extract readable content from a URL (HTML → markdown/text).
  Core parameters:
  url (required)
  extractMode (markdown | text)
  maxChars (truncate long pages)
  Notes:
  Enable via tools.web.fetch.enabled.
  maxChars is clamped by tools.web.fetch.maxCharsCap (default 50000).
  Responses are cached (default 15 min).
  For JS-heavy sites, prefer the browser tool.
  See Web tools for setup.
  See Firecrawl for the optional anti-bot fallback.
  ​
  browser
  Control the dedicated OpenClaw-managed browser.
  Core actions:
  status, start, stop, tabs, open, focus, close
  snapshot (aria/ai)
  screenshot (returns image block + MEDIA:<path>)
  act (UI actions: click/type/press/hover/drag/select/fill/resize/wait/evaluate)
  navigate, console, pdf, upload, dialog
  Profile management:
  profiles — list all browser profiles with status
  create-profile — create new profile with auto-allocated port (or cdpUrl)
  delete-profile — stop browser, delete user data, remove from config (local only)
  reset-profile — kill orphan process on profile’s port (local only)
  Common parameters:
  profile (optional; defaults to browser.defaultProfile)
  target (sandbox | host | node)
  node (optional; picks a specific node id/name) Notes:
  Requires browser.enabled=true (default is true; set false to disable).
  All actions accept optional profile parameter for multi-instance support.
  When profile is omitted, uses browser.defaultProfile (defaults to “chrome”).
  Profile names: lowercase alphanumeric + hyphens only (max 64 chars).
  Port range: 18800-18899 (~100 profiles max).
  Remote profiles are attach-only (no start/stop/reset).
  If a browser-capable node is connected, the tool may auto-route to it (unless you pin target).
  snapshot defaults to ai when Playwright is installed; use aria for the accessibility tree.
  snapshot also supports role-snapshot options (interactive, compact, depth, selector) which return refs like e12.
  act requires ref from snapshot (numeric 12 from AI snapshots, or e12 from role snapshots); use evaluate for rare CSS selector needs.
  Avoid act → wait by default; use it only in exceptional cases (no reliable UI state to wait on).
  upload can optionally pass a ref to auto-click after arming.
  upload also supports inputRef (aria ref) or element (CSS selector) to set <input type="file"> directly.
  ​
  canvas
  Drive the node Canvas (present, eval, snapshot, A2UI).
  Core actions:
  present, hide, navigate, eval
  snapshot (returns image block + MEDIA:<path>)
  a2ui_push, a2ui_reset
  Notes:
  Uses gateway node.invoke under the hood.
  If no node is provided, the tool picks a default (single connected node or local mac node).
  A2UI is v0.8 only (no createSurface); the CLI rejects v0.9 JSONL with line errors.
  Quick smoke: openclaw nodes canvas a2ui push --node <id> --text "Hello from A2UI".
  ​
  nodes
  Discover and target paired nodes; send notifications; capture camera/screen.
  Core actions:
  status, describe
  pending, approve, reject (pairing)
  notify (macOS system.notify)
  run (macOS system.run)
  camera_list, camera_snap, camera_clip, screen_record
  location_get, notifications_list, notifications_action
  device_status, device_info, device_permissions, device_health
  Notes:
  Camera/screen commands require the node app to be foregrounded.
  Images return image blocks + MEDIA:<path>.
  Videos return FILE:<path> (mp4).
  Location returns a JSON payload (lat/lon/accuracy/timestamp).
  run params: command argv array; optional cwd, env (KEY=VAL), commandTimeoutMs, invokeTimeoutMs, needsScreenRecording.
  Example (run):
  {
  "action": "run",
  "node": "office-mac",
  "command": ["echo", "Hello"],
  "env": ["FOO=bar"],
  "commandTimeoutMs": 12000,
  "invokeTimeoutMs": 45000,
  "needsScreenRecording": false
  }
  ​
  image
  Analyze an image with the configured image model.
  Core parameters:
  image (required path or URL)
  prompt (optional; defaults to “Describe the image.”)
  model (optional override)
  maxBytesMb (optional size cap)
  Notes:
  Only available when agents.defaults.imageModel is configured (primary or fallbacks), or when an implicit image model can be inferred from your default model + configured auth (best-effort pairing).
  Uses the image model directly (independent of the main chat model).
  ​
  pdf
  Analyze one or more PDF documents.
  For full behavior, limits, config, and examples, see PDF tool.
  ​
  message
  Send messages and channel actions across Discord/Google Chat/Slack/Telegram/WhatsApp/Signal/iMessage/MS Teams.
  Core actions:
  send (text + optional media; MS Teams also supports card for Adaptive Cards)
  poll (WhatsApp/Discord/MS Teams polls)
  react / reactions / read / edit / delete
  pin / unpin / list-pins
  permissions
  thread-create / thread-list / thread-reply
  search
  sticker
  member-info / role-info
  emoji-list / emoji-upload / sticker-upload
  role-add / role-remove
  channel-info / channel-list
  voice-status
  event-list / event-create
  timeout / kick / ban
  Notes:
  send routes WhatsApp via the Gateway; other channels go direct.
  poll uses the Gateway for WhatsApp and MS Teams; Discord polls go direct.
  When a message tool call is bound to an active chat session, sends are constrained to that session’s target to avoid cross-context leaks.
  ​
  cron
  Manage Gateway cron jobs and wakeups.
  Core actions:
  status, list
  add, update, remove, run, runs
  wake (enqueue system event + optional immediate heartbeat)
  Notes:
  add expects a full cron job object (same schema as cron.add RPC).
  update uses { jobId, patch } (id accepted for compatibility).
  ​
  gateway
  Restart or apply updates to the running Gateway process (in-place).
  Core actions:
  restart (authorizes + sends SIGUSR1 for in-process restart; openclaw gateway restart in-place)
  config.schema.lookup (inspect one config path at a time without loading the full schema into prompt context)
  config.get
  config.apply (validate + write config + restart + wake)
  config.patch (merge partial update + restart + wake)
  update.run (run update + restart + wake)
  Notes:
  config.schema.lookup expects a targeted config path such as gateway.auth or agents.list.*.heartbeat.
  Paths may include slash-delimited plugin ids when addressing plugins.entries.<id>, for example plugins.entries.pack/one.config.
  Use delayMs (defaults to 2000) to avoid interrupting an in-flight reply.
  config.schema remains available to internal Control UI flows and is not exposed through the agent gateway tool.
  restart is enabled by default; set commands.restart: false to disable it.
  ​
  sessions*list / sessions_history / sessions_send / sessions_spawn / session_status
  List sessions, inspect transcript history, or send to another session.
  Core parameters:
  sessions_list: kinds?, limit?, activeMinutes?, messageLimit? (0 = none)
  sessions_history: sessionKey (or sessionId), limit?, includeTools?
  sessions_send: sessionKey (or sessionId), message, timeoutSeconds? (0 = fire-and-forget)
  sessions_spawn: task, label?, runtime?, agentId?, model?, thinking?, cwd?, runTimeoutSeconds?, thread?, mode?, cleanup?, sandbox?, streamTo?, attachments?, attachAs?
  session_status: sessionKey? (default current; accepts sessionId), model? (default clears override)
  Notes:
  main is the canonical direct-chat key; global/unknown are hidden.
  messageLimit > 0 fetches last N messages per session (tool messages filtered).
  Session targeting is controlled by tools.sessions.visibility (default tree: current session + spawned subagent sessions). If you run a shared agent for multiple users, consider setting tools.sessions.visibility: "self" to prevent cross-session browsing.
  sessions_send waits for final completion when timeoutSeconds > 0.
  Delivery/announce happens after completion and is best-effort; status: "ok" confirms the agent run finished, not that the announce was delivered.
  sessions_spawn supports runtime: "subagent" | "acp" (subagent default). For ACP runtime behavior, see ACP Agents.
  For ACP runtime, streamTo: "parent" routes initial-run progress summaries back to the requester session as system events instead of direct child delivery.
  sessions_spawn starts a sub-agent run and posts an announce reply back to the requester chat.
  Supports one-shot mode (mode: "run") and persistent thread-bound mode (mode: "session" with thread: true).
  If thread: true and mode is omitted, mode defaults to session.
  mode: "session" requires thread: true.
  If runTimeoutSeconds is omitted, OpenClaw uses agents.defaults.subagents.runTimeoutSeconds when set; otherwise timeout defaults to 0 (no timeout).
  Discord thread-bound flows depend on session.threadBindings.* and channels.discord.threadBindings._.
  Reply format includes Status, Result, and compact stats.
  Result is the assistant completion text; if missing, the latest toolResult is used as fallback.
  Manual completion-mode spawns send directly first, with queue fallback and retry on transient failures (status: "ok" means run finished, not that announce delivered).
  sessions_spawn supports inline file attachments for subagent runtime only (ACP rejects them). Each attachment has name, content, and optional encoding (utf8 or base64) and mimeType. Files are materialized into the child workspace at .openclaw/attachments/<uuid>/ with a .manifest.json metadata file. The tool returns a receipt with count, totalBytes, per file sha256, and relDir. Attachment content is automatically redacted from transcript persistence.
  Configure limits via tools.sessions_spawn.attachments (enabled, maxTotalBytes, maxFiles, maxFileBytes, retainOnSessionKeep).
  attachAs.mountPath is a reserved hint for future mount implementations.
  sessions_spawn is non-blocking and returns status: "accepted" immediately.
  ACP streamTo: "parent" responses may include streamLogPath (session-scoped _.acp-stream.jsonl) for tailing progress history.
  sessions_send runs a reply‑back ping‑pong (reply REPLY_SKIP to stop; max turns via session.agentToAgent.maxPingPongTurns, 0–5).
  After the ping‑pong, the target agent runs an announce step; reply ANNOUNCE_SKIP to suppress the announcement.
  Sandbox clamp: when the current session is sandboxed and agents.defaults.sandbox.sessionToolsVisibility: "spawned", OpenClaw clamps tools.sessions.visibility to tree.
  ​
  agents_list
  List agent ids that the current session may target with sessions_spawn.
  Notes:
  Result is restricted to per-agent allowlists (agents.list[].subagents.allowAgents).
  When ["*"] is configured, the tool includes all configured agents and marks allowAny: true.
  ​
  Parameters (common)
  Gateway-backed tools (canvas, nodes, cron):
  gatewayUrl (default ws://127.0.0.1:18789)
  gatewayToken (if auth enabled)
  timeoutMs
  Note: when gatewayUrl is set, include gatewayToken explicitly. Tools do not inherit config or environment credentials for overrides, and missing explicit credentials is an error.
  Browser tool:
  profile (optional; defaults to browser.defaultProfile)
  target (sandbox | host | node)
  node (optional; pin a specific node id/name)
  ​
  Recommended agent flows
  Browser automation:
  browser → status / start
  snapshot (ai or aria)
  act (click/type/press)
  screenshot if you need visual confirmation
  Canvas render:
  canvas → present
  a2ui_push (optional)
  snapshot
  Node targeting:
  nodes → status
  describe on the chosen node
  notify / run / camera_snap / screen_record
  ​
  Safety
  Avoid direct system.run; use nodes → run only with explicit user consent.
  Respect user consent for camera/screen capture.
  Use status/describe to ensure permissions before invoking media commands.
  ​
  How tools are presented to the agent
  Tools are exposed in two parallel channels:
  System prompt text: a human-readable list + guidance.
  Tool schema: the structured function definitions sent to the model API.
  That means the agent sees both “what tools exist” and “how to call them.” If a tool doesn’t appear in the system prompt or the schema, the model cannot call it.

Built-in tools
apply\*patch Tool
Apply file changes using a structured patch format. This is ideal for multi-file or multi-hunk edits where a single edit call would be brittle.
The tool accepts a single input string that wraps one or more file operations:
\*\*\* Begin Patch
**_ Add File: path/to/file.txt
+line 1
+line 2
_** Update File: src/app.ts
@@
-old line
+new line
**_ Delete File: obsolete.txt
_** End Patch
​
Parameters
input (required): Full patch contents including **_ Begin Patch and _** End Patch.
​
Notes
Patch paths support relative paths (from the workspace directory) and absolute paths.
tools.exec.applyPatch.workspaceOnly defaults to true (workspace-contained). Set it to false only if you intentionally want apply\*patch to write/delete outside the workspace directory.
Use **\* Move to: within an **_ Update File: hunk to rename files.
_** End of File marks an EOF-only insert when needed.
Experimental and disabled by default. Enable with tools.exec.applyPatch.enabled.
OpenAI-only (including OpenAI Codex). Optionally gate by model via tools.exec.applyPatch.allowModels.
Config is only under tools.exec.
​
Example
{
"tool": "apply_patch",
"input": "**_ Begin Patch\n_\*\* Update File: src/index.ts\n@@\n-const foo = 1\n+const foo = 2\n\*\*\* End Patch"
}

Built-in tools
Perplexity Sonar
OpenClaw can use Perplexity Sonar for the web_search tool. You can connect through Perplexity’s direct API or via OpenRouter.
​
API options
​
Perplexity (direct)
Base URL: https://api.perplexity.ai
Environment variable: PERPLEXITY_API_KEY
​
OpenRouter (alternative)
Base URL: https://openrouter.ai/api/v1
Environment variable: OPENROUTER_API_KEY
Supports prepaid/crypto credits.
​
Config example
{
tools: {
web: {
search: {
provider: "perplexity",
perplexity: {
apiKey: "pplx-...",
baseUrl: "https://api.perplexity.ai",
model: "perplexity/sonar-pro",
},
},
},
},
}
​
Switching from Brave
{
tools: {
web: {
search: {
provider: "perplexity",
perplexity: {
apiKey: "pplx-...",
baseUrl: "https://api.perplexity.ai",
},
},
},
},
}
If both PERPLEXITY_API_KEY and OPENROUTER_API_KEY are set, set tools.web.search.perplexity.baseUrl (or tools.web.search.perplexity.apiKey) to disambiguate.
If no base URL is set, OpenClaw chooses a default based on the API key source:
PERPLEXITY_API_KEY or pplx-... → direct Perplexity (https://api.perplexity.ai)
OPENROUTER_API_KEY or sk-or-... → OpenRouter (https://openrouter.ai/api/v1)
Unknown key formats → OpenRouter (safe fallback)
​
Models
perplexity/sonar — fast Q&A with web search
perplexity/sonar-pro (default) — multi-step reasoning + web search
perplexity/sonar-reasoning-pro — deep research
See Web tools for the full web_search configuration.

Built-in tools
Diffs
Use the optional Diffs plugin to render before and after text or unified patches as a gateway-hosted diff view, a file (PNG or PDF), or both.

diffs is an optional plugin tool with short built-in system guidance and a companion skill that turns change content into a read-only diff artifact for agents.
It accepts either:
before and after text
a unified patch
It can return:
a gateway viewer URL for canvas presentation
a rendered file path (PNG or PDF) for message delivery
both outputs in one call
When enabled, the plugin prepends concise usage guidance into system-prompt space and also exposes a detailed skill for cases where the agent needs fuller instructions.
​
Quick start
Enable the plugin.
Call diffs with mode: "view" for canvas-first flows.
Call diffs with mode: "file" for chat file delivery flows.
Call diffs with mode: "both" when you need both artifacts.
​
Enable the plugin
{
plugins: {
entries: {
diffs: {
enabled: true,
},
},
},
}
​
Disable built-in system guidance
If you want to keep the diffs tool enabled but disable its built-in system-prompt guidance, set plugins.entries.diffs.hooks.allowPromptInjection to false:
{
plugins: {
entries: {
diffs: {
enabled: true,
hooks: {
allowPromptInjection: false,
},
},
},
},
}
This blocks the diffs plugin’s before_prompt_build hook while keeping the plugin, tool, and companion skill available.
If you want to disable both the guidance and the tool, disable the plugin instead.
​
Typical agent workflow
Agent calls diffs.
Agent reads details fields.
Agent either:
opens details.viewerUrl with canvas present
sends details.filePath with message using path or filePath
does both
​
Input examples
Before and after:
{
"before": "# Hello\n\nOne",
"after": "# Hello\n\nTwo",
"path": "docs/example.md",
"mode": "view"
}
Patch:
{
"patch": "diff --git a/src/example.ts b/src/example.ts\n--- a/src/example.ts\n+++ b/src/example.ts\n@@ -1 +1 @@\n-const x = 1;\n+const x = 2;\n",
"mode": "both"
}
​
Tool input reference
All fields are optional unless noted:
before (string): original text. Required with after when patch is omitted.
after (string): updated text. Required with before when patch is omitted.
patch (string): unified diff text. Mutually exclusive with before and after.
path (string): display filename for before and after mode.
lang (string): language override hint for before and after mode.
title (string): viewer title override.
mode ("view" | "file" | "both"): output mode. Defaults to plugin default defaults.mode.
theme ("light" | "dark"): viewer theme. Defaults to plugin default defaults.theme.
layout ("unified" | "split"): diff layout. Defaults to plugin default defaults.layout.
expandUnchanged (boolean): expand unchanged sections when full context is available. Per-call option only (not a plugin default key).
fileFormat ("png" | "pdf"): rendered file format. Defaults to plugin default defaults.fileFormat.
fileQuality ("standard" | "hq" | "print"): quality preset for PNG or PDF rendering.
fileScale (number): device scale override (1-4).
fileMaxWidth (number): max render width in CSS pixels (640-2400).
ttlSeconds (number): viewer artifact TTL in seconds. Default 1800, max 21600.
baseUrl (string): viewer URL origin override. Must be http or https, no query/hash.
Validation and limits:
before and after each max 512 KiB.
patch max 2 MiB.
path max 2048 bytes.
lang max 128 bytes.
title max 1024 bytes.
Patch complexity cap: max 128 files and 120000 total lines.
patch and before or after together are rejected.
Rendered file safety limits (apply to PNG and PDF):
fileQuality: "standard": max 8 MP (8,000,000 rendered pixels).
fileQuality: "hq": max 14 MP (14,000,000 rendered pixels).
fileQuality: "print": max 24 MP (24,000,000 rendered pixels).
PDF also has a max of 50 pages.
​
Output details contract
The tool returns structured metadata under details.
Shared fields for modes that create a viewer:
artifactId
viewerUrl
viewerPath
title
expiresAt
inputKind
fileCount
mode
File fields when PNG or PDF is rendered:
filePath
path (same value as filePath, for message tool compatibility)
fileBytes
fileFormat
fileQuality
fileScale
fileMaxWidth
Mode behavior summary:
mode: "view": viewer fields only.
mode: "file": file fields only, no viewer artifact.
mode: "both": viewer fields plus file fields. If file rendering fails, viewer still returns with fileError.
​
Collapsed unchanged sections
The viewer can show rows like N unmodified lines.
Expand controls on those rows are conditional and not guaranteed for every input kind.
Expand controls appear when the rendered diff has expandable context data, which is typical for before and after input.
For many unified patch inputs, omitted context bodies are not available in the parsed patch hunks, so the row can appear without expand controls. This is expected behavior.
expandUnchanged applies only when expandable context exists.
​
Plugin defaults
Set plugin-wide defaults in ~/.openclaw/openclaw.json:
{
plugins: {
entries: {
diffs: {
enabled: true,
config: {
defaults: {
fontFamily: "Fira Code",
fontSize: 15,
lineSpacing: 1.6,
layout: "unified",
showLineNumbers: true,
diffIndicators: "bars",
wordWrap: true,
background: true,
theme: "dark",
fileFormat: "png",
fileQuality: "standard",
fileScale: 2,
fileMaxWidth: 960,
mode: "both",
},
},
},
},
},
}
Supported defaults:
fontFamily
fontSize
lineSpacing
layout
showLineNumbers
diffIndicators
wordWrap
background
theme
fileFormat
fileQuality
fileScale
fileMaxWidth
mode
Explicit tool parameters override these defaults.
​
Security config
security.allowRemoteViewer (boolean, default false)
false: non-loopback requests to viewer routes are denied.
true: remote viewers are allowed if tokenized path is valid.
Example:
{
plugins: {
entries: {
diffs: {
enabled: true,
config: {
security: {
allowRemoteViewer: false,
},
},
},
},
},
}
​
Artifact lifecycle and storage
Artifacts are stored under the temp subfolder: $TMPDIR/openclaw-diffs.
Viewer artifact metadata contains:
random artifact ID (20 hex chars)
random token (48 hex chars)
createdAt and expiresAt
stored viewer.html path
Default viewer TTL is 30 minutes when not specified.
Maximum accepted viewer TTL is 6 hours.
Cleanup runs opportunistically after artifact creation.
Expired artifacts are deleted.
Fallback cleanup removes stale folders older than 24 hours when metadata is missing.
​
Viewer URL and network behavior
Viewer route:
/plugins/diffs/view/{artifactId}/{token}
Viewer assets:
/plugins/diffs/assets/viewer.js
/plugins/diffs/assets/viewer-runtime.js
URL construction behavior:
If baseUrl is provided, it is used after strict validation.
Without baseUrl, viewer URL defaults to loopback 127.0.0.1.
If gateway bind mode is custom and gateway.customBindHost is set, that host is used.
baseUrl rules:
Must be http:// or https://.
Query and hash are rejected.
Origin plus optional base path is allowed.
​
Security model
Viewer hardening:
Loopback-only by default.
Tokenized viewer paths with strict ID and token validation.
Viewer response CSP:
default-src 'none'
scripts and assets only from self
no outbound connect-src
Remote miss throttling when remote access is enabled:
40 failures per 60 seconds
60 second lockout (429 Too Many Requests)
File rendering hardening:
Screenshot browser request routing is deny-by-default.
Only local viewer assets from http://127.0.0.1/plugins/diffs/assets/* are allowed.
External network requests are blocked.
​
Browser requirements for file mode
mode: "file" and mode: "both" need a Chromium-compatible browser.
Resolution order:
browser.executablePath in OpenClaw config.
Environment variables:
OPENCLAW_BROWSER_EXECUTABLE_PATH
BROWSER_EXECUTABLE_PATH
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
Platform command/path discovery fallback.
Common failure text:
Diff PNG/PDF rendering requires a Chromium-compatible browser...
Fix by installing Chrome, Chromium, Edge, or Brave, or setting one of the executable path options above.
​
Troubleshooting
Input validation errors:
Provide patch or both before and after text.
Include both before and after, or provide patch.
Provide either patch or before/after input, not both.
Do not mix input modes.
Invalid baseUrl: ...
Use http(s) origin with optional path, no query/hash.
{field} exceeds maximum size (...)
Reduce payload size.
Large patch rejection
Reduce patch file count or total lines.
Viewer accessibility issues:
Viewer URL resolves to 127.0.0.1 by default.
For remote access scenarios, either:
pass baseUrl per tool call, or
use gateway.bind=custom and gateway.customBindHost
Enable security.allowRemoteViewer only when you intend external viewer access.
Unmodified-lines row has no expand button:
This can happen for patch input when the patch does not carry expandable context.
This is expected and does not indicate a viewer failure.
Artifact not found:
Artifact expired due TTL.
Token or path changed.
Cleanup removed stale data.
​
Operational guidance
Prefer mode: "view" for local interactive reviews in canvas.
Prefer mode: "file" for outbound chat channels that need an attachment.
Keep allowRemoteViewer disabled unless your deployment requires remote viewer URLs.
Set explicit short ttlSeconds for sensitive diffs.
Avoid sending secrets in diff input when not required.
If your channel compresses images aggressively (for example Telegram or WhatsApp), prefer PDF output (fileFormat: "pdf").
Diff rendering engine:
Powered by Diffs.
Built-in tools
PDF Tool
pdf analyzes one or more PDF documents and returns text.
Quick behavior:
Native provider mode for Anthropic and Google model providers.
Extraction fallback mode for other providers (extract text first, then page images when needed).
Supports single (pdf) or multi (pdfs) input, max 10 PDFs per call.
​
Availability
The tool is only registered when OpenClaw can resolve a PDF-capable model config for the agent:
agents.defaults.pdfModel
fallback to agents.defaults.imageModel
fallback to best effort provider defaults based on available auth
If no usable model can be resolved, the pdf tool is not exposed.
​
Input reference
pdf (string): one PDF path or URL
pdfs (string[]): multiple PDF paths or URLs, up to 10 total
prompt (string): analysis prompt, default Analyze this PDF document.
pages (string): page filter like 1-5 or 1,3,7-9
model (string): optional model override (provider/model)
maxBytesMb (number): per-PDF size cap in MB
Input notes:
pdf and pdfs are merged and deduplicated before loading.
If no PDF input is provided, the tool errors.
pages is parsed as 1-based page numbers, deduped, sorted, and clamped to the configured max pages.
maxBytesMb defaults to agents.defaults.pdfMaxBytesMb or 10.
​
Supported PDF references
local file path (including ~ expansion)
file:// URL
http:// and https:// URL
Reference notes:
Other URI schemes (for example ftp://) are rejected with unsupported_pdf_reference.
In sandbox mode, remote http(s) URLs are rejected.
With workspace-only file policy enabled, local file paths outside allowed roots are rejected.
​
Execution modes
​
Native provider mode
Native mode is used for provider anthropic and google. The tool sends raw PDF bytes directly to provider APIs.
Native mode limits:
pages is not supported. If set, the tool returns an error.
​
Extraction fallback mode
Fallback mode is used for non-native providers.
Flow:
Extract text from selected pages (up to agents.defaults.pdfMaxPages, default 20).
If extracted text length is below 200 chars, render selected pages to PNG images and include them.
Send extracted content plus prompt to the selected model.
Fallback details:
Page image extraction uses a pixel budget of 4,000,000.
If the target model does not support image input and there is no extractable text, the tool errors.
Extraction fallback requires pdfjs-dist (and @napi-rs/canvas for image rendering).
​
Config
{
agents: {
defaults: {
pdfModel: {
primary: "anthropic/claude-opus-4-6",
fallbacks: ["openai/gpt-5-mini"],
},
pdfMaxBytesMb: 10,
pdfMaxPages: 20,
},
},
}
See Configuration Reference for full field details.
​
Output details
The tool returns text in content[0].text and structured metadata in details.
Common details fields:
model: resolved model ref (provider/model)
native: true for native provider mode, false for fallback
attempts: fallback attempts that failed before success
Path fields:
single PDF input: details.pdf
multiple PDF inputs: details.pdfs[] with pdf entries
sandbox path rewrite metadata (when applicable): rewrittenFrom
​
Error behavior
Missing PDF input: throws pdf required: provide a path or URL to a PDF document
Too many PDFs: returns structured error in details.error = "too_many_pdfs"
Unsupported reference scheme: returns details.error = "unsupported_pdf_reference"
Native mode with pages: throws clear pages is not supported with native PDF providers error
​
Examples
Single PDF:
{
"pdf": "/tmp/report.pdf",
"prompt": "Summarize this report in 5 bullets"
}
Multiple PDFs:
{
"pdfs": ["/tmp/q1.pdf", "/tmp/q2.pdf"],
"prompt": "Compare risks and timeline changes across both documents"
}
Page-filtered fallback model:
{
"pdf": "https://example.com/report.pdf",
"pages": "1-3,7",
"model": "openai/gpt-5-mini",
"prompt": "Extract only customer-impacting incidents"
}

Built-in tools
Elevated Mode
​
What it does
/elevated on runs on the gateway host and keeps exec approvals (same as /elevated ask).
/elevated full runs on the gateway host and auto-approves exec (skips exec approvals).
/elevated ask runs on the gateway host but keeps exec approvals (same as /elevated on).
on/ask do not force exec.security=full; configured security/ask policy still applies.
Only changes behavior when the agent is sandboxed (otherwise exec already runs on the host).
Directive forms: /elevated on|off|ask|full, /elev on|off|ask|full.
Only on|off|ask|full are accepted; anything else returns a hint and does not change state.
​
What it controls (and what it doesn’t)
Availability gates: tools.elevated is the global baseline. agents.list[].tools.elevated can further restrict elevated per agent (both must allow).
Per-session state: /elevated on|off|ask|full sets the elevated level for the current session key.
Inline directive: /elevated on|ask|full inside a message applies to that message only.
Groups: In group chats, elevated directives are only honored when the agent is mentioned. Command-only messages that bypass mention requirements are treated as mentioned.
Host execution: elevated forces exec onto the gateway host; full also sets security=full.
Approvals: full skips exec approvals; on/ask honor them when allowlist/ask rules require.
Unsandboxed agents: no-op for location; only affects gating, logging, and status.
Tool policy still applies: if exec is denied by tool policy, elevated cannot be used.
Separate from /exec: /exec adjusts per-session defaults for authorized senders and does not require elevated.
​
Resolution order
Inline directive on the message (applies only to that message).
Session override (set by sending a directive-only message).
Global default (agents.defaults.elevatedDefault in config).
​
Setting a session default
Send a message that is only the directive (whitespace allowed), e.g. /elevated full.
Confirmation reply is sent (Elevated mode set to full... / Elevated mode disabled.).
If elevated access is disabled or the sender is not on the approved allowlist, the directive replies with an actionable error and does not change session state.
Send /elevated (or /elevated:) with no argument to see the current elevated level.
​
Availability + allowlists
Feature gate: tools.elevated.enabled (default can be off via config even if the code supports it).
Sender allowlist: tools.elevated.allowFrom with per-provider allowlists (e.g. discord, whatsapp).
Unprefixed allowlist entries match sender-scoped identity values only (SenderId, SenderE164, From); recipient routing fields are never used for elevated authorization.
Mutable sender metadata requires explicit prefixes:
name:<value> matches SenderName
username:<value> matches SenderUsername
tag:<value> matches SenderTag
id:<value>, from:<value>, e164:<value> are available for explicit identity targeting
Per-agent gate: agents.list[].tools.elevated.enabled (optional; can only further restrict).
Per-agent allowlist: agents.list[].tools.elevated.allowFrom (optional; when set, the sender must match both global + per-agent allowlists).
Discord fallback: if tools.elevated.allowFrom.discord is omitted, the channels.discord.allowFrom list is used as a fallback (legacy: channels.discord.dm.allowFrom). Set tools.elevated.allowFrom.discord (even []) to override. Per-agent allowlists do not use the fallback.
All gates must pass; otherwise elevated is treated as unavailable.
​
Logging + status
Elevated exec calls are logged at info level.
Session status includes elevated mode (e.g. elevated=ask, elevated=full).

Built-in tools
Exec Tool
Run shell commands in the workspace. Supports foreground + background execution via process. If process is disallowed, exec runs synchronously and ignores yieldMs/background. Background sessions are scoped per agent; process only sees sessions from the same agent.
​
Parameters
command (required)
workdir (defaults to cwd)
env (key/value overrides)
yieldMs (default 10000): auto-background after delay
background (bool): background immediately
timeout (seconds, default 1800): kill on expiry
pty (bool): run in a pseudo-terminal when available (TTY-only CLIs, coding agents, terminal UIs)
host (sandbox | gateway | node): where to execute
security (deny | allowlist | full): enforcement mode for gateway/node
ask (off | on-miss | always): approval prompts for gateway/node
node (string): node id/name for host=node
elevated (bool): request elevated mode (gateway host); security=full is only forced when elevated resolves to full
Notes:
host defaults to sandbox.
elevated is ignored when sandboxing is off (exec already runs on the host).
gateway/node approvals are controlled by ~/.openclaw/exec-approvals.json.
node requires a paired node (companion app or headless node host).
If multiple nodes are available, set exec.node or tools.exec.node to select one.
On non-Windows hosts, exec uses SHELL when set; if SHELL is fish, it prefers bash (or sh) from PATH to avoid fish-incompatible scripts, then falls back to SHELL if neither exists.
On Windows hosts, exec prefers PowerShell 7 (pwsh) discovery (Program Files, ProgramW6432, then PATH), then falls back to Windows PowerShell 5.1.
Host execution (gateway/node) rejects env.PATH and loader overrides (LD*\*/DYLD*\*) to prevent binary hijacking or injected code.
OpenClaw sets OPENCLAW_SHELL=exec in the spawned command environment (including PTY and sandbox execution) so shell/profile rules can detect exec-tool context.
Important: sandboxing is off by default. If sandboxing is off and host=sandbox is explicitly configured/requested, exec now fails closed instead of silently running on the gateway host. Enable sandboxing or use host=gateway with approvals.
Script preflight checks (for common Python/Node shell-syntax mistakes) only inspect files inside the effective workdir boundary. If a script path resolves outside workdir, preflight is skipped for that file.
​
Config
tools.exec.notifyOnExit (default: true): when true, backgrounded exec sessions enqueue a system event and request a heartbeat on exit.
tools.exec.approvalRunningNoticeMs (default: 10000): emit a single “running” notice when an approval-gated exec runs longer than this (0 disables).
tools.exec.host (default: sandbox)
tools.exec.security (default: deny for sandbox, allowlist for gateway + node when unset)
tools.exec.ask (default: on-miss)
tools.exec.node (default: unset)
tools.exec.pathPrepend: list of directories to prepend to PATH for exec runs (gateway + sandbox only).
tools.exec.safeBins: stdin-only safe binaries that can run without explicit allowlist entries. For behavior details, see Safe bins.
tools.exec.safeBinTrustedDirs: additional explicit directories trusted for safeBins path checks. PATH entries are never auto-trusted. Built-in defaults are /bin and /usr/bin.
tools.exec.safeBinProfiles: optional custom argv policy per safe bin (minPositional, maxPositional, allowedValueFlags, deniedFlags).
Example:
{
tools: {
exec: {
pathPrepend: ["~/bin", "/opt/oss/bin"],
},
},
}
​
PATH handling
host=gateway: merges your login-shell PATH into the exec environment. env.PATH overrides are rejected for host execution. The daemon itself still runs with a minimal PATH:
macOS: /opt/homebrew/bin, /usr/local/bin, /usr/bin, /bin
Linux: /usr/local/bin, /usr/bin, /bin
host=sandbox: runs sh -lc (login shell) inside the container, so /etc/profile may reset PATH. OpenClaw prepends env.PATH after profile sourcing via an internal env var (no shell interpolation); tools.exec.pathPrepend applies here too.
host=node: only non-blocked env overrides you pass are sent to the node. env.PATH overrides are rejected for host execution and ignored by node hosts. If you need additional PATH entries on a node, configure the node host service environment (systemd/launchd) or install tools in standard locations.
Per-agent node binding (use the agent list index in config):
openclaw config get agents.list
openclaw config set agents.list[0].tools.exec.node "node-id-or-name"
Control UI: the Nodes tab includes a small “Exec node binding” panel for the same settings.
​
Session overrides (/exec)
Use /exec to set per-session defaults for host, security, ask, and node. Send /exec with no arguments to show the current values.
Example:
/exec host=gateway security=allowlist ask=on-miss node=mac-1
​
Authorization model
/exec is only honored for authorized senders (channel allowlists/pairing plus commands.useAccessGroups). It updates session state only and does not write config. To hard-disable exec, deny it via tool policy (tools.deny: ["exec"] or per-agent). Host approvals still apply unless you explicitly set security=full and ask=off.
​
Exec approvals (companion app / node host)
Sandboxed agents can require per-request approval before exec runs on the gateway or node host. See Exec approvals for the policy, allowlist, and UI flow.
When approvals are required, the exec tool returns immediately with status: "approval-pending" and an approval id. Once approved (or denied / timed out), the Gateway emits system events (Exec finished / Exec denied). If the command is still running after tools.exec.approvalRunningNoticeMs, a single Exec running notice is emitted.
​
Allowlist + safe bins
Manual allowlist enforcement matches resolved binary paths only (no basename matches). When security=allowlist, shell commands are auto-allowed only if every pipeline segment is allowlisted or a safe bin. Chaining (;, &&, ||) and redirections are rejected in allowlist mode unless every top-level segment satisfies the allowlist (including safe bins). Redirections remain unsupported.
autoAllowSkills is a separate convenience path in exec approvals. It is not the same as manual path allowlist entries. For strict explicit trust, keep autoAllowSkills disabled.
Use the two controls for different jobs:
tools.exec.safeBins: small, stdin-only stream filters.
tools.exec.safeBinTrustedDirs: explicit extra trusted directories for safe-bin executable paths.
tools.exec.safeBinProfiles: explicit argv policy for custom safe bins.
allowlist: explicit trust for executable paths.
Do not treat safeBins as a generic allowlist, and do not add interpreter/runtime binaries (for example python3, node, ruby, bash). If you need those, use explicit allowlist entries and keep approval prompts enabled. openclaw security audit warns when interpreter/runtime safeBins entries are missing explicit profiles, and openclaw doctor --fix can scaffold missing custom safeBinProfiles entries.
For full policy details and examples, see Exec approvals and Safe bins versus allowlist.
​
Examples
Foreground:
{ "tool": "exec", "command": "ls -la" }
Background + poll:
{"tool":"exec","command":"npm run build","yieldMs":1000}
{"tool":"process","action":"poll","sessionId":"<id>"}
Send keys (tmux-style):
{"tool":"process","action":"send-keys","sessionId":"<id>","keys":["Enter"]}
{"tool":"process","action":"send-keys","sessionId":"<id>","keys":["C-c"]}
{"tool":"process","action":"send-keys","sessionId":"<id>","keys":["Up","Up","Enter"]}
Submit (send CR only):
{ "tool": "process", "action": "submit", "sessionId": "<id>" }
Paste (bracketed by default):
{ "tool": "process", "action": "paste", "sessionId": "<id>", "text": "line1\nline2\n" }
​
apply_patch (experimental)
apply_patch is a subtool of exec for structured multi-file edits. Enable it explicitly:
{
tools: {
exec: {
applyPatch: { enabled: true, workspaceOnly: true, allowModels: ["gpt-5.2"] },
},
},
}
Notes:
Only available for OpenAI/OpenAI Codex models.
Tool policy still applies; allow: ["exec"] implicitly allows apply_patch.
Config lives under tools.exec.applyPatch.
tools.exec.applyPatch.workspaceOnly defaults to true (workspace-contained). Set it to false only if you intentionally want apply_patch to write/delete outside the workspace directory.

Built-in tools
Exec Approvals
Exec approvals are the companion app / node host guardrail for letting a sandboxed agent run commands on a real host (gateway or node). Think of it like a safety interlock: commands are allowed only when policy + allowlist + (optional) user approval all agree. Exec approvals are in addition to tool policy and elevated gating (unless elevated is set to full, which skips approvals). Effective policy is the stricter of tools.exec._ and approvals defaults; if an approvals field is omitted, the tools.exec value is used.
If the companion app UI is not available, any request that requires a prompt is resolved by the ask fallback (default: deny).
​
Where it applies
Exec approvals are enforced locally on the execution host:
gateway host → openclaw process on the gateway machine
node host → node runner (macOS companion app or headless node host)
macOS split:
node host service forwards system.run to the macOS app over local IPC.
macOS app enforces approvals + executes the command in UI context.
​
Settings and storage
Approvals live in a local JSON file on the execution host:
~/.openclaw/exec-approvals.json
Example schema:
{
"version": 1,
"socket": {
"path": "~/.openclaw/exec-approvals.sock",
"token": "base64url-token"
},
"defaults": {
"security": "deny",
"ask": "on-miss",
"askFallback": "deny",
"autoAllowSkills": false
},
"agents": {
"main": {
"security": "allowlist",
"ask": "on-miss",
"askFallback": "deny",
"autoAllowSkills": true,
"allowlist": [
{
"id": "B0C8C0B3-2C2D-4F8A-9A3C-5A4B3C2D1E0F",
"pattern": "~/Projects/**/bin/rg",
"lastUsedAt": 1737150000000,
"lastUsedCommand": "rg -n TODO",
"lastResolvedPath": "/Users/user/Projects/.../bin/rg"
}
]
}
}
}
​
Policy knobs
​
Security (exec.security)
deny: block all host exec requests.
allowlist: allow only allowlisted commands.
full: allow everything (equivalent to elevated).
​
Ask (exec.ask)
off: never prompt.
on-miss: prompt only when allowlist does not match.
always: prompt on every command.
​
Ask fallback (askFallback)
If a prompt is required but no UI is reachable, fallback decides:
deny: block.
allowlist: allow only if allowlist matches.
full: allow.
​
Allowlist (per agent)
Allowlists are per agent. If multiple agents exist, switch which agent you’re editing in the macOS app. Patterns are case-insensitive glob matches. Patterns should resolve to binary paths (basename-only entries are ignored). Legacy agents.default entries are migrated to agents.main on load.
Examples:
~/Projects/\*\*/bin/peekaboo
~/.local/bin/_
/opt/homebrew/bin/rg
Each allowlist entry tracks:
id stable UUID used for UI identity (optional)
last used timestamp
last used command
last resolved path
​
Auto-allow skill CLIs
When Auto-allow skill CLIs is enabled, executables referenced by known skills are treated as allowlisted on nodes (macOS node or headless node host). This uses skills.bins over the Gateway RPC to fetch the skill bin list. Disable this if you want strict manual allowlists.
​
Safe bins (stdin-only)
tools.exec.safeBins defines a small list of stdin-only binaries (for example jq) that can run in allowlist mode without explicit allowlist entries. Safe bins reject positional file args and path-like tokens, so they can only operate on the incoming stream. Validation is deterministic from argv shape only (no host filesystem existence checks), which prevents file-existence oracle behavior from allow/deny differences. File-oriented options are denied for default safe bins (for example sort -o, sort --output, sort --files0-from, sort --compress-program, wc --files0-from, jq -f/--from-file, grep -f/--file). Safe bins also enforce explicit per-binary flag policy for options that break stdin-only behavior (for example sort -o/--output/--compress-program and grep recursive flags). Safe bins also force argv tokens to be treated as literal text at execution time (no globbing and no $VARS expansion) for stdin-only segments, so patterns like * or $HOME/... cannot be used to smuggle file reads. Safe bins must also resolve from trusted binary directories (system defaults plus the gateway process PATH at startup). This blocks request-scoped PATH hijacking attempts. Shell chaining and redirections are not auto-allowed in allowlist mode.
Shell chaining (&&, ||, ;) is allowed when every top-level segment satisfies the allowlist (including safe bins or skill auto-allow). Redirections remain unsupported in allowlist mode. Command substitution ($() / backticks) is rejected during allowlist parsing, including inside double quotes; use single quotes if you need literal $() text. On macOS companion-app approvals, raw shell text containing shell control or expansion syntax (&&, ||, ;, |, `, $, <, >, (, )) is treated as an allowlist miss unless the shell binary itself is allowlisted.
Default safe bins: jq, cut, uniq, head, tail, tr, wc.
grep and sort are not in the default list. If you opt in, keep explicit allowlist entries for their non-stdin workflows. For grep in safe-bin mode, provide the pattern with -e/--regexp; positional pattern form is rejected so file operands cannot be smuggled as ambiguous positionals.
​
Control UI editing
Use the Control UI → Nodes → Exec approvals card to edit defaults, per‑agent overrides, and allowlists. Pick a scope (Defaults or an agent), tweak the policy, add/remove allowlist patterns, then Save. The UI shows last used metadata per pattern so you can keep the list tidy.
The target selector chooses Gateway (local approvals) or a Node. Nodes must advertise system.execApprovals.get/set (macOS app or headless node host). If a node does not advertise exec approvals yet, edit its local ~/.openclaw/exec-approvals.json directly.
CLI: openclaw approvals supports gateway or node editing (see Approvals CLI).
​
Approval flow
When a prompt is required, the gateway broadcasts exec.approval.requested to operator clients. The Control UI and macOS app resolve it via exec.approval.resolve, then the gateway forwards the approved request to the node host.
When approvals are required, the exec tool returns immediately with an approval id. Use that id to correlate later system events (Exec finished / Exec denied). If no decision arrives before the timeout, the request is treated as an approval timeout and surfaced as a denial reason.
The confirmation dialog includes:
command + args
cwd
agent id
resolved executable path
host + policy metadata
Actions:
Allow once → run now
Always allow → add to allowlist + run
Deny → block
​
Approval forwarding to chat channels
You can forward exec approval prompts to any chat channel (including plugin channels) and approve them with /approve. This uses the normal outbound delivery pipeline.
Config:
{
approvals: {
exec: {
enabled: true,
mode: "session", // "session" | "targets" | "both"
agentFilter: ["main"],
sessionFilter: ["discord"], // substring or regex
targets: [
{ channel: "slack", to: "U12345678" },
{ channel: "telegram", to: "123456789" },
],
},
},
}
Reply in chat:
/approve <id> allow-once
/approve <id> allow-always
/approve <id> deny
​
macOS IPC flow
Gateway -> Node Service (WS)
| IPC (UDS + token + HMAC + TTL)
v
Mac App (UI + approvals + system.run)
Security notes:
Unix socket mode 0600, token stored in exec-approvals.json.
Same-UID peer check.
Challenge/response (nonce + HMAC token + request hash) + short TTL.
​
System events
Exec lifecycle is surfaced as system messages:
Exec running (only if the command exceeds the running notice threshold)
Exec finished
Exec denied
These are posted to the agent’s session after the node reports the event. Gateway-host exec approvals emit the same lifecycle events when the command finishes (and optionally when running longer than the threshold). Approval-gated execs reuse the approval id as the runId in these messages for easy correlation.
​
Implications
full is powerful; prefer allowlists when possible.
ask keeps you in the loop while still allowing fast approvals.
Per-agent allowlists prevent one agent’s approvals from leaking into others.
Approvals only apply to host exec requests from authorized senders. Unauthorized senders cannot issue /exec.
/exec security=full is a session-level convenience for authorized operators and skips approvals by design. To hard-block host exec, set approvals security to deny or deny the exec tool via tool policy.

Built-in tools
LLM Task
llm-task is an optional plugin tool that runs a JSON-only LLM task and returns structured output (optionally validated against JSON Schema).
This is ideal for workflow engines like Lobster: you can add a single LLM step without writing custom OpenClaw code for each workflow.
​
Enable the plugin
Enable the plugin:
{
"plugins": {
"entries": {
"llm-task": { "enabled": true }
}
}
}
Allowlist the tool (it is registered with optional: true):
{
"agents": {
"list": [
{
"id": "main",
"tools": { "allow": ["llm-task"] }
}
]
}
}
​
Config (optional)
{
"plugins": {
"entries": {
"llm-task": {
"enabled": true,
"config": {
"defaultProvider": "openai-codex",
"defaultModel": "gpt-5.2",
"defaultAuthProfileId": "main",
"allowedModels": ["openai-codex/gpt-5.3-codex"],
"maxTokens": 800,
"timeoutMs": 30000
}
}
}
}
}
allowedModels is an allowlist of provider/model strings. If set, any request outside the list is rejected.
​
Tool parameters
prompt (string, required)
input (any, optional)
schema (object, optional JSON Schema)
provider (string, optional)
model (string, optional)
authProfileId (string, optional)
temperature (number, optional)
maxTokens (number, optional)
timeoutMs (number, optional)
​
Output
Returns details.json containing the parsed JSON (and validates against schema when provided).
​
Example: Lobster workflow step
openclaw.invoke --tool llm-task --action json --args-json '{
"prompt": "Given the input email, return intent and draft.",
"input": {
"subject": "Hello",
"body": "Can you help?"
},
"schema": {
"type": "object",
"properties": {
"intent": { "type": "string" },
"draft": { "type": "string" }
},
"required": ["intent", "draft"],
"additionalProperties": false
}
}'
​
Safety notes
The tool is JSON-only and instructs the model to output only JSON (no code fences, no commentary).
No tools are exposed to the model for this run.
Treat output as untrusted unless you validate with schema.
Put approvals before any side-effecting step (send, post, exec).

Built-in tools
Lobster
Typed workflow runtime for OpenClaw — composable pipelines with approval gates.

Lobster is a workflow shell that lets OpenClaw run multi-step tool sequences as a single, deterministic operation with explicit approval checkpoints.
​
Hook
Your assistant can build the tools that manage itself. Ask for a workflow, and 30 minutes later you have a CLI plus pipelines that run as one call. Lobster is the missing piece: deterministic pipelines, explicit approvals, and resumable state.
​
Why
Today, complex workflows require many back-and-forth tool calls. Each call costs tokens, and the LLM has to orchestrate every step. Lobster moves that orchestration into a typed runtime:
One call instead of many: OpenClaw runs one Lobster tool call and gets a structured result.
Approvals built in: Side effects (send email, post comment) halt the workflow until explicitly approved.
Resumable: Halted workflows return a token; approve and resume without re-running everything.
​
Why a DSL instead of plain programs?
Lobster is intentionally small. The goal is not “a new language,” it’s a predictable, AI-friendly pipeline spec with first-class approvals and resume tokens.
Approve/resume is built in: A normal program can prompt a human, but it can’t pause and resume with a durable token without you inventing that runtime yourself.
Determinism + auditability: Pipelines are data, so they’re easy to log, diff, replay, and review.
Constrained surface for AI: A tiny grammar + JSON piping reduces “creative” code paths and makes validation realistic.
Safety policy baked in: Timeouts, output caps, sandbox checks, and allowlists are enforced by the runtime, not each script.
Still programmable: Each step can call any CLI or script. If you want JS/TS, generate .lobster files from code.
​
How it works
OpenClaw launches the local lobster CLI in tool mode and parses a JSON envelope from stdout. If the pipeline pauses for approval, the tool returns a resumeToken so you can continue later.
​
Pattern: small CLI + JSON pipes + approvals
Build tiny commands that speak JSON, then chain them into a single Lobster call. (Example command names below — swap in your own.)
inbox list --json
inbox categorize --json
inbox apply --json
{
"action": "run",
"pipeline": "exec --json --shell 'inbox list --json' | exec --stdin json --shell 'inbox categorize --json' | exec --stdin json --shell 'inbox apply --json' | approve --preview-from-stdin --limit 5 --prompt 'Apply changes?'",
"timeoutMs": 30000
}
If the pipeline requests approval, resume with the token:
{
"action": "resume",
"token": "<resumeToken>",
"approve": true
}
AI triggers the workflow; Lobster executes the steps. Approval gates keep side effects explicit and auditable.
Example: map input items into tool calls:
gog.gmail.search --query 'newer_than:1d' \
 | openclaw.invoke --tool message --action send --each --item-key message --args-json '{"provider":"telegram","to":"..."}'
​
JSON-only LLM steps (llm-task)
For workflows that need a structured LLM step, enable the optional llm-task plugin tool and call it from Lobster. This keeps the workflow deterministic while still letting you classify/summarize/draft with a model.
Enable the tool:
{
"plugins": {
"entries": {
"llm-task": { "enabled": true }
}
},
"agents": {
"list": [
{
"id": "main",
"tools": { "allow": ["llm-task"] }
}
]
}
}
Use it in a pipeline:
openclaw.invoke --tool llm-task --action json --args-json '{
"prompt": "Given the input email, return intent and draft.",
"input": { "subject": "Hello", "body": "Can you help?" },
"schema": {
"type": "object",
"properties": {
"intent": { "type": "string" },
"draft": { "type": "string" }
},
"required": ["intent", "draft"],
"additionalProperties": false
}
}'
See LLM Task for details and configuration options.
​
Workflow files (.lobster)
Lobster can run YAML/JSON workflow files with name, args, steps, env, condition, and approval fields. In OpenClaw tool calls, set pipeline to the file path.
name: inbox-triage
args:
tag:
default: "family"
steps:

- id: collect
  command: inbox list --json
- id: categorize
  command: inbox categorize --json
  stdin: $collect.stdout
- id: approve
  command: inbox apply --approve
  stdin: $categorize.stdout
  approval: required
- id: execute
  command: inbox apply --execute
  stdin: $categorize.stdout
  condition: $approve.approved
  Notes:
  stdin: $step.stdout and stdin: $step.json pass a prior step’s output.
  condition (or when) can gate steps on $step.approved.
  ​
  Install Lobster
  Install the Lobster CLI on the same host that runs the OpenClaw Gateway (see the Lobster repo), and ensure lobster is on PATH.
  ​
  Enable the tool
  Lobster is an optional plugin tool (not enabled by default).
  Recommended (additive, safe):
  {
  "tools": {
  "alsoAllow": ["lobster"]
  }
  }
  Or per-agent:
  {
  "agents": {
  "list": [
  {
  "id": "main",
  "tools": {
  "alsoAllow": ["lobster"]
  }
  }
  ]
  }
  }
  Avoid using tools.allow: ["lobster"] unless you intend to run in restrictive allowlist mode.
  Note: allowlists are opt-in for optional plugins. If your allowlist only names plugin tools (like lobster), OpenClaw keeps core tools enabled. To restrict core tools, include the core tools or groups you want in the allowlist too.
  ​
  Example: Email triage
  Without Lobster:
  User: "Check my email and draft replies"
  → openclaw calls gmail.list
  → LLM summarizes
  → User: "draft replies to #2 and #5"
  → LLM drafts
  → User: "send #2"
  → openclaw calls gmail.send
  (repeat daily, no memory of what was triaged)
  With Lobster:
  {
  "action": "run",
  "pipeline": "email.triage --limit 20",
  "timeoutMs": 30000
  }
  Returns a JSON envelope (truncated):
  {
  "ok": true,
  "status": "needs_approval",
  "output": [{ "summary": "5 need replies, 2 need action" }],
  "requiresApproval": {
  "type": "approval_request",
  "prompt": "Send 2 draft replies?",
  "items": [],
  "resumeToken": "..."
  }
  }
  User approves → resume:
  {
  "action": "resume",
  "token": "<resumeToken>",
  "approve": true
  }
  One workflow. Deterministic. Safe.
  ​
  Tool parameters
  ​
  run
  Run a pipeline in tool mode.
  {
  "action": "run",
  "pipeline": "gog.gmail.search --query 'newer_than:1d' | email.triage",
  "cwd": "workspace",
  "timeoutMs": 30000,
  "maxStdoutBytes": 512000
  }
  Run a workflow file with args:
  {
  "action": "run",
  "pipeline": "/path/to/inbox-triage.lobster",
  "argsJson": "{\"tag\":\"family\"}"
  }
  ​
  resume
  Continue a halted workflow after approval.
  {
  "action": "resume",
  "token": "<resumeToken>",
  "approve": true
  }
  ​
  Optional inputs
  cwd: Relative working directory for the pipeline (must stay within the current process working directory).
  timeoutMs: Kill the subprocess if it exceeds this duration (default: 20000).
  maxStdoutBytes: Kill the subprocess if stdout exceeds this size (default: 512000).
  argsJson: JSON string passed to lobster run --args-json (workflow files only).
  ​
  Output envelope
  Lobster returns a JSON envelope with one of three statuses:
  ok → finished successfully
  needs_approval → paused; requiresApproval.resumeToken is required to resume
  cancelled → explicitly denied or cancelled
  The tool surfaces the envelope in both content (pretty JSON) and details (raw object).
  ​
  Approvals
  If requiresApproval is present, inspect the prompt and decide:
  approve: true → resume and continue side effects
  approve: false → cancel and finalize the workflow
  Use approve --preview-from-stdin --limit N to attach a JSON preview to approval requests without custom jq/heredoc glue. Resume tokens are now compact: Lobster stores workflow resume state under its state dir and hands back a small token key.
  ​
  OpenProse
  OpenProse pairs well with Lobster: use /prose to orchestrate multi-agent prep, then run a Lobster pipeline for deterministic approvals. If a Prose program needs Lobster, allow the lobster tool for sub-agents via tools.subagents.tools. See OpenProse.
  ​
  Safety
  Local subprocess only — no network calls from the plugin itself.
  No secrets — Lobster doesn’t manage OAuth; it calls OpenClaw tools that do.
  Sandbox-aware — disabled when the tool context is sandboxed.
  Hardened — fixed executable name (lobster) on PATH; timeouts and output caps enforced.
  ​
  Troubleshooting
  lobster subprocess timed out → increase timeoutMs, or split a long pipeline.
  lobster output exceeded maxStdoutBytes → raise maxStdoutBytes or reduce output size.
  lobster returned invalid JSON → ensure the pipeline runs in tool mode and prints only JSON.
  lobster failed (code …) → run the same pipeline in a terminal to inspect stderr.
  ​
  Learn more
  Plugins
  Plugin tool authoring
  ​
  Case study: community workflows
  One public example: a “second brain” CLI + Lobster pipelines that manage three Markdown vaults (personal, partner, shared). The CLI emits JSON for stats, inbox listings, and stale scans; Lobster chains those commands into workflows like weekly-review, inbox-triage, memory-consolidation, and shared-task-sync, each with approval gates. AI handles judgment (categorization) when available and falls back to deterministic rules when not.
  Thread: https://x.com/plattenschieber/status/2014508656335770033
  Repo: https://github.com/bloomedai/brain-cli

Built-in tools
Tool-loop detection
Configure optional guardrails for preventing repetitive or stalled tool-call loops

OpenClaw can keep agents from getting stuck in repeated tool-call patterns. The guard is disabled by default.
Enable it only where needed, because it can block legitimate repeated calls with strict settings.
​
Why this exists
Detect repetitive sequences that do not make progress.
Detect high-frequency no-result loops (same tool, same inputs, repeated errors).
Detect specific repeated-call patterns for known polling tools.
​
Configuration block
Global defaults:
{
tools: {
loopDetection: {
enabled: false,
historySize: 30,
warningThreshold: 10,
criticalThreshold: 20,
globalCircuitBreakerThreshold: 30,
detectors: {
genericRepeat: true,
knownPollNoProgress: true,
pingPong: true,
},
},
},
}
Per-agent override (optional):
{
agents: {
list: [
{
id: "safe-runner",
tools: {
loopDetection: {
enabled: true,
warningThreshold: 8,
criticalThreshold: 16,
},
},
},
],
},
}
​
Field behavior
enabled: Master switch. false means no loop detection is performed.
historySize: number of recent tool calls kept for analysis.
warningThreshold: threshold before classifying a pattern as warning-only.
criticalThreshold: threshold for blocking repetitive loop patterns.
globalCircuitBreakerThreshold: global no-progress breaker threshold.
detectors.genericRepeat: detects repeated same-tool + same-params patterns.
detectors.knownPollNoProgress: detects known polling-like patterns with no state change.
detectors.pingPong: detects alternating ping-pong patterns.
​
Recommended setup
Start with enabled: true, defaults unchanged.
Keep thresholds ordered as warningThreshold < criticalThreshold < globalCircuitBreakerThreshold.
If false positives occur:
raise warningThreshold and/or criticalThreshold
(optionally) raise globalCircuitBreakerThreshold
disable only the detector causing issues
reduce historySize for less strict historical context
​
Logs and expected behavior
When a loop is detected, OpenClaw reports a loop event and blocks or dampens the next tool-cycle depending on severity. This protects users from runaway token spend and lockups while preserving normal tool access.
Prefer warning and temporary suppression first.
Escalate only when repeated evidence accumulates.
​
Notes
tools.loopDetection is merged with agent-level overrides.
Per-agent config fully overrides or extends global values.
If no config exists, guardrails stay off.

Built-in tools
Reactions
Shared reaction semantics across channels:
emoji is required when adding a reaction.
emoji="" removes the bot’s reaction(s) when supported.
remove: true removes the specified emoji when supported (requires emoji).
Channel notes:
Discord/Slack: empty emoji removes all of the bot’s reactions on the message; remove: true removes just that emoji.
Google Chat: empty emoji removes the app’s reactions on the message; remove: true removes just that emoji.
Telegram: empty emoji removes the bot’s reactions; remove: true also removes reactions but still requires a non-empty emoji for tool validation.
WhatsApp: empty emoji removes the bot reaction; remove: true maps to empty emoji (still requires emoji).
Zalo Personal (zalouser): requires non-empty emoji; remove: true removes that specific emoji reaction.
Signal: inbound reaction notifications emit system events when channels.signal.reactionNotifications is enabled.

Built-in tools
Thinking Levels
​
What it does
Inline directive in any inbound body: /t <level>, /think:<level>, or /thinking <level>.
Levels (aliases): off | minimal | low | medium | high | xhigh | adaptive
minimal → “think”
low → “think hard”
medium → “think harder”
high → “ultrathink” (max budget)
xhigh → “ultrathink+” (GPT-5.2 + Codex models only)
adaptive → provider-managed adaptive reasoning budget (supported for Anthropic Claude 4.6 model family)
x-high, x*high, extra-high, extra high, and extra_high map to xhigh.
highest, max map to high.
Provider notes:
Anthropic Claude 4.6 models default to adaptive when no explicit thinking level is set.
Z.AI (zai/*) only supports binary thinking (on/off). Any non-off level is treated as on (mapped to low).
Moonshot (moonshot/\_) maps /think off to thinking: { type: "disabled" } and any non-off level to thinking: { type: "enabled" }. When thinking is enabled, Moonshot only accepts tool_choice auto|none; OpenClaw normalizes incompatible values to auto.
​
Resolution order
Inline directive on the message (applies only to that message).
Session override (set by sending a directive-only message).
Global default (agents.defaults.thinkingDefault in config).
Fallback: adaptive for Anthropic Claude 4.6 models, low for other reasoning-capable models, off otherwise.
​
Setting a session default
Send a message that is only the directive (whitespace allowed), e.g. /think:medium or /t high.
That sticks for the current session (per-sender by default); cleared by /think:off or session idle reset.
Confirmation reply is sent (Thinking level set to high. / Thinking disabled.). If the level is invalid (e.g. /thinking big), the command is rejected with a hint and the session state is left unchanged.
Send /think (or /think:) with no argument to see the current thinking level.
​
Application by agent
Embedded Pi: the resolved level is passed to the in-process Pi agent runtime.
​
Verbose directives (/verbose or /v)
Levels: on (minimal) | full | off (default).
Directive-only message toggles session verbose and replies Verbose logging enabled. / Verbose logging disabled.; invalid levels return a hint without changing state.
/verbose off stores an explicit session override; clear it via the Sessions UI by choosing inherit.
Inline directive affects only that message; session/global defaults apply otherwise.
Send /verbose (or /verbose:) with no argument to see the current verbose level.
When verbose is on, agents that emit structured tool results (Pi, other JSON agents) send each tool call back as its own metadata-only message, prefixed with <emoji> <tool-name>: <arg> when available (path/command). These tool summaries are sent as soon as each tool starts (separate bubbles), not as streaming deltas.
Tool failure summaries remain visible in normal mode, but raw error detail suffixes are hidden unless verbose is on or full.
When verbose is full, tool outputs are also forwarded after completion (separate bubble, truncated to a safe length). If you toggle /verbose on|full|off while a run is in-flight, subsequent tool bubbles honor the new setting.
​
Reasoning visibility (/reasoning)
Levels: on|off|stream.
Directive-only message toggles whether thinking blocks are shown in replies.
When enabled, reasoning is sent as a separate message prefixed with Reasoning:.
stream (Telegram only): streams reasoning into the Telegram draft bubble while the reply is generating, then sends the final answer without reasoning.
Alias: /reason.
Send /reasoning (or /reasoning:) with no argument to see the current reasoning level.
​
Related
Elevated mode docs live in Elevated mode.
​
Heartbeats
Heartbeat probe body is the configured heartbeat prompt (default: Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.). Inline directives in a heartbeat message apply as usual (but avoid changing session defaults from heartbeats).
Heartbeat delivery defaults to the final payload only. To also send the separate Reasoning: message (when available), set agents.defaults.heartbeat.includeReasoning: true or per-agent agents.list[].heartbeat.includeReasoning: true.
​
Web chat UI
The web chat thinking selector mirrors the session’s stored level from the inbound session store/config when the page loads.
Picking another level applies only to the next message (thinkingOnce); after sending, the selector snaps back to the stored session level.
To change the session default, send a /think:<level> directive (as before); the selector will reflect it after the next reload.

Agent coordination
Agent Send
openclaw agent runs a single agent turn without needing an inbound chat message. By default it goes through the Gateway; add --local to force the embedded runtime on the current machine.
​
Behavior
Required: --message <text>
Session selection:
--to <dest> derives the session key (group/channel targets preserve isolation; direct chats collapse to main), or
--session-id <id> reuses an existing session by id, or
--agent <id> targets a configured agent directly (uses that agent’s main session key)
Runs the same embedded agent runtime as normal inbound replies.
Thinking/verbose flags persist into the session store.
Output:
default: prints reply text (plus MEDIA:<url> lines)
--json: prints structured payload + metadata
Optional delivery back to a channel with --deliver + --channel (target formats match openclaw message --target).
Use --reply-channel/--reply-to/--reply-account to override delivery without changing the session.
If the Gateway is unreachable, the CLI falls back to the embedded local run.
​
Examples
openclaw agent --to +15555550123 --message "status update"
openclaw agent --agent ops --message "Summarize logs"
openclaw agent --session-id 1234 --message "Summarize inbox" --thinking medium
openclaw agent --to +15555550123 --message "Trace logs" --verbose on --json
openclaw agent --to +15555550123 --message "Summon reply" --deliver
openclaw agent --agent ops --message "Generate report" --deliver --reply-channel slack --reply-to "#reports"
​
Flags
--local: run locally (requires model provider API keys in your shell)
--deliver: send the reply to the chosen channel
--channel: delivery channel (whatsapp|telegram|discord|googlechat|slack|signal|imessage, default: whatsapp)
--reply-to: delivery target override
--reply-channel: delivery channel override
--reply-account: delivery account id override
--thinking <off|minimal|low|medium|high|xhigh>: persist thinking level (GPT-5.2 + Codex models only)
--verbose <on|full|off>: persist verbose level
--timeout <seconds>: override agent timeout
--json: output structured JSON

Agent coordination
Sub-Agents
Sub-agents are background agent runs spawned from an existing agent run. They run in their own session (agent:<agentId>:subagent:<uuid>) and, when finished, announce their result back to the requester chat channel.
​
Slash command
Use /subagents to inspect or control sub-agent runs for the current session:
/subagents list
/subagents kill <id|#|all>
/subagents log <id|#> [limit] [tools]
/subagents info <id|#>
/subagents send <id|#> <message>
/subagents steer <id|#> <message>
/subagents spawn <agentId> <task> [--model <model>] [--thinking <level>]
Thread binding controls:
These commands work on channels that support persistent thread bindings. See Thread supporting channels below.
/focus <subagent-label|session-key|session-id|session-label>
/unfocus
/agents
/session idle <duration|off>
/session max-age <duration|off>
/subagents info shows run metadata (status, timestamps, session id, transcript path, cleanup).
​
Spawn behavior
/subagents spawn starts a background sub-agent as a user command, not an internal relay, and it sends one final completion update back to the requester chat when the run finishes.
The spawn command is non-blocking; it returns a run id immediately.
On completion, the sub-agent announces a summary/result message back to the requester chat channel.
For manual spawns, delivery is resilient:
OpenClaw tries direct agent delivery first with a stable idempotency key.
If direct delivery fails, it falls back to queue routing.
If queue routing is still not available, the announce is retried with a short exponential backoff before final give-up.
The completion handoff to the requester session is runtime-generated internal context (not user-authored text) and includes:
Result (assistant reply text, or latest toolResult if the assistant reply is empty)
Status (completed successfully / failed / timed out / unknown)
compact runtime/token stats
a delivery instruction telling the requester agent to rewrite in normal assistant voice (not forward raw internal metadata)
--model and --thinking override defaults for that specific run.
Use info/log to inspect details and output after completion.
/subagents spawn is one-shot mode (mode: "run"). For persistent thread-bound sessions, use sessions*spawn with thread: true and mode: "session".
For ACP harness sessions (Codex, Claude Code, Gemini CLI), use sessions_spawn with runtime: "acp" and see ACP Agents.
Primary goals:
Parallelize “research / long task / slow tool” work without blocking the main run.
Keep sub-agents isolated by default (session separation + optional sandboxing).
Keep the tool surface hard to misuse: sub-agents do not get session tools by default.
Support configurable nesting depth for orchestrator patterns.
Cost note: each sub-agent has its own context and token usage. For heavy or repetitive tasks, set a cheaper model for sub-agents and keep your main agent on a higher-quality model. You can configure this via agents.defaults.subagents.model or per-agent overrides.
​
Tool
Use sessions_spawn:
Starts a sub-agent run (deliver: false, global lane: subagent)
Then runs an announce step and posts the announce reply to the requester chat channel
Default model: inherits the caller unless you set agents.defaults.subagents.model (or per-agent agents.list[].subagents.model); an explicit sessions_spawn.model still wins.
Default thinking: inherits the caller unless you set agents.defaults.subagents.thinking (or per-agent agents.list[].subagents.thinking); an explicit sessions_spawn.thinking still wins.
Default run timeout: if sessions_spawn.runTimeoutSeconds is omitted, OpenClaw uses agents.defaults.subagents.runTimeoutSeconds when set; otherwise it falls back to 0 (no timeout).
Tool params:
task (required)
label? (optional)
agentId? (optional; spawn under another agent id if allowed)
model? (optional; overrides the sub-agent model; invalid values are skipped and the sub-agent runs on the default model with a warning in the tool result)
thinking? (optional; overrides thinking level for the sub-agent run)
runTimeoutSeconds? (defaults to agents.defaults.subagents.runTimeoutSeconds when set, otherwise 0; when set, the sub-agent run is aborted after N seconds)
thread? (default false; when true, requests channel thread binding for this sub-agent session)
mode? (run|session)
default is run
if thread: true and mode omitted, default becomes session
mode: "session" requires thread: true
cleanup? (delete|keep, default keep)
sandbox? (inherit|require, default inherit; require rejects spawn unless target child runtime is sandboxed)
sessions_spawn does not accept channel-delivery params (target, channel, to, threadId, replyTo, transport). For delivery, use message/sessions_send from the spawned run.
​
Thread-bound sessions
When thread bindings are enabled for a channel, a sub-agent can stay bound to a thread so follow-up user messages in that thread keep routing to the same sub-agent session.
​
Thread supporting channels
Discord (currently the only supported channel): supports persistent thread-bound subagent sessions (sessions_spawn with thread: true), manual thread controls (/focus, /unfocus, /agents, /session idle, /session max-age), and adapter keys channels.discord.threadBindings.enabled, channels.discord.threadBindings.idleHours, channels.discord.threadBindings.maxAgeHours, and channels.discord.threadBindings.spawnSubagentSessions.
Quick flow:
Spawn with sessions_spawn using thread: true (and optionally mode: "session").
OpenClaw creates or binds a thread to that session target in the active channel.
Replies and follow-up messages in that thread route to the bound session.
Use /session idle to inspect/update inactivity auto-unfocus and /session max-age to control the hard cap.
Use /unfocus to detach manually.
Manual controls:
/focus <target> binds the current thread (or creates one) to a sub-agent/session target.
/unfocus removes the binding for the current bound thread.
/agents lists active runs and binding state (thread:<id> or unbound).
/session idle and /session max-age only work for focused bound threads.
Config switches:
Global default: session.threadBindings.enabled, session.threadBindings.idleHours, session.threadBindings.maxAgeHours
Channel override and spawn auto-bind keys are adapter-specific. See Thread supporting channels above.
See Configuration Reference and Slash commands for current adapter details.
Allowlist:
agents.list[].subagents.allowAgents: list of agent ids that can be targeted via agentId (["*"] to allow any). Default: only the requester agent.
Sandbox inheritance guard: if the requester session is sandboxed, sessions_spawn rejects targets that would run unsandboxed.
Discovery:
Use agents_list to see which agent ids are currently allowed for sessions_spawn.
Auto-archive:
Sub-agent sessions are automatically archived after agents.defaults.subagents.archiveAfterMinutes (default: 60).
Archive uses sessions.delete and renames the transcript to *.deleted.<timestamp> (same folder).
cleanup: "delete" archives immediately after announce (still keeps the transcript via rename).
Auto-archive is best-effort; pending timers are lost if the gateway restarts.
runTimeoutSeconds does not auto-archive; it only stops the run. The session remains until auto-archive.
Auto-archive applies equally to depth-1 and depth-2 sessions.
​
Nested Sub-Agents
By default, sub-agents cannot spawn their own sub-agents (maxSpawnDepth: 1). You can enable one level of nesting by setting maxSpawnDepth: 2, which allows the orchestrator pattern: main → orchestrator sub-agent → worker sub-sub-agents.
​
How to enable
{
agents: {
defaults: {
subagents: {
maxSpawnDepth: 2, // allow sub-agents to spawn children (default: 1)
maxChildrenPerAgent: 5, // max active children per agent session (default: 5)
maxConcurrent: 8, // global concurrency lane cap (default: 8)
runTimeoutSeconds: 900, // default timeout for sessions*spawn when omitted (0 = no timeout)
},
},
},
}
​
Depth levels
Depth Session key shape Role Can spawn?
0 agent:<id>:main Main agent Always
1 agent:<id>:subagent:<uuid> Sub-agent (orchestrator when depth 2 allowed) Only if maxSpawnDepth >= 2
2 agent:<id>:subagent:<uuid>:subagent:<uuid> Sub-sub-agent (leaf worker) Never
​
Announce chain
Results flow back up the chain:
Depth-2 worker finishes → announces to its parent (depth-1 orchestrator)
Depth-1 orchestrator receives the announce, synthesizes results, finishes → announces to main
Main agent receives the announce and delivers to the user
Each level only sees announces from its direct children.
​
Tool policy by depth
Depth 1 (orchestrator, when maxSpawnDepth >= 2): Gets sessions_spawn, subagents, sessions_list, sessions_history so it can manage its children. Other session/system tools remain denied.
Depth 1 (leaf, when maxSpawnDepth == 1): No session tools (current default behavior).
Depth 2 (leaf worker): No session tools — sessions_spawn is always denied at depth 2. Cannot spawn further children.
​
Per-agent spawn limit
Each agent session (at any depth) can have at most maxChildrenPerAgent (default: 5) active children at a time. This prevents runaway fan-out from a single orchestrator.
​
Cascade stop
Stopping a depth-1 orchestrator automatically stops all its depth-2 children:
/stop in the main chat stops all depth-1 agents and cascades to their depth-2 children.
/subagents kill <id> stops a specific sub-agent and cascades to its children.
/subagents kill all stops all sub-agents for the requester and cascades.
​
Authentication
Sub-agent auth is resolved by agent id, not by session type:
The sub-agent session key is agent:<agentId>:subagent:<uuid>.
The auth store is loaded from that agent’s agentDir.
The main agent’s auth profiles are merged in as a fallback; agent profiles override main profiles on conflicts.
Note: the merge is additive, so main profiles are always available as fallbacks. Fully isolated auth per agent is not supported yet.
​
Announce
Sub-agents report back via an announce step:
The announce step runs inside the sub-agent session (not the requester session).
If the sub-agent replies exactly ANNOUNCE_SKIP, nothing is posted.
Otherwise delivery depends on requester depth:
top-level requester sessions use a follow-up agent call with external delivery (deliver=true)
nested requester subagent sessions receive an internal follow-up injection (deliver=false) so the orchestrator can synthesize child results in-session
if a nested requester subagent session is gone, OpenClaw falls back to that session’s requester when available
Child completion aggregation is scoped to the current requester run when building nested completion findings, preventing stale prior-run child outputs from leaking into the current announce.
Announce replies preserve thread/topic routing when available on channel adapters.
Announce context is normalized to a stable internal event block:
source (subagent or cron)
child session key/id
announce type + task label
status line derived from runtime outcome (success, error, timeout, or unknown)
result content from the announce step (or (no output) if missing)
a follow-up instruction describing when to reply vs. stay silent
Status is not inferred from model output; it comes from runtime outcome signals.
Announce payloads include a stats line at the end (even when wrapped):
Runtime (e.g., runtime 5m12s)
Token usage (input/output/total)
Estimated cost when model pricing is configured (models.providers.\*.models[].cost)
sessionKey, sessionId, and transcript path (so the main agent can fetch history via sessions_history or inspect the file on disk)
Internal metadata is meant for orchestration only; user-facing replies should be rewritten in normal assistant voice.
​
Tool Policy (sub-agent tools)
By default, sub-agents get all tools except session tools and system tools:
sessions_list
sessions_history
sessions_send
sessions_spawn
When maxSpawnDepth >= 2, depth-1 orchestrator sub-agents additionally receive sessions_spawn, subagents, sessions_list, and sessions_history so they can manage their children.
Override via config:
{
agents: {
defaults: {
subagents: {
maxConcurrent: 1,
},
},
},
tools: {
subagents: {
tools: {
// deny wins
deny: ["gateway", "cron"],
// if allow is set, it becomes allow-only (deny still wins)
// allow: ["read", "exec", "process"]
},
},
},
}
​
Concurrency
Sub-agents use a dedicated in-process queue lane:
Lane name: subagent
Concurrency: agents.defaults.subagents.maxConcurrent (default 8)
​
Stopping
Sending /stop in the requester chat aborts the requester session and stops any active sub-agent runs spawned from it, cascading to nested children.
/subagents kill <id> stops a specific sub-agent and cascades to its children.
​
Limitations
Sub-agent announce is best-effort. If the gateway restarts, pending “announce back” work is lost.
Sub-agents still share the same gateway process resources; treat maxConcurrent as a safety valve.
sessions_spawn is always non-blocking: it returns { status: "accepted", runId, childSessionKey } immediately.
Sub-agent context only injects AGENTS.md + TOOLS.md (no SOUL.md, IDENTITY.md, USER.md, HEARTBEAT.md, or BOOTSTRAP.md).
Maximum nesting depth is 5 (maxSpawnDepth range: 1–5). Depth 2 is recommended for most use cases.
maxChildrenPerAgent caps active children per session (default: 5, range: 1–20).

Agent coordination
ACP Agents
Agent Client Protocol (ACP) sessions let OpenClaw run external coding harnesses (for example Pi, Claude Code, Codex, OpenCode, and Gemini CLI) through an ACP backend plugin.
If you ask OpenClaw in plain language to “run this in Codex” or “start Claude Code in a thread”, OpenClaw should route that request to the ACP runtime (not the native sub-agent runtime).
​
Fast operator flow
Use this when you want a practical /acp runbook:
Spawn a session:
/acp spawn codex --mode persistent --thread auto
Work in the bound thread (or target that session key explicitly).
Check runtime state:
/acp status
Tune runtime options as needed:
/acp model <provider/model>
/acp permissions <profile>
/acp timeout <seconds>
Nudge an active session without replacing context:
/acp steer tighten logging and continue
Stop work:
/acp cancel (stop current turn), or
/acp close (close session + remove bindings)
​
Quick start for humans
Examples of natural requests:
“Start a persistent Codex session in a thread here and keep it focused.”
“Run this as a one-shot Claude Code ACP session and summarize the result.”
“Use Gemini CLI for this task in a thread, then keep follow-ups in that same thread.”
What OpenClaw should do:
Pick runtime: "acp".
Resolve the requested harness target (agentId, for example codex).
If thread binding is requested and the current channel supports it, bind the ACP session to the thread.
Route follow-up thread messages to that same ACP session until unfocused/closed/expired.
​
ACP versus sub-agents
Use ACP when you want an external harness runtime. Use sub-agents when you want OpenClaw-native delegated runs.
Area ACP session Sub-agent run
Runtime ACP backend plugin (for example acpx) OpenClaw native sub-agent runtime
Session key agent:<agentId>:acp:<uuid> agent:<agentId>:subagent:<uuid>
Main commands /acp ... /subagents ...
Spawn tool sessions*spawn with runtime:"acp" sessions_spawn (default runtime)
See also Sub-agents.
​
Thread-bound sessions (channel-agnostic)
When thread bindings are enabled for a channel adapter, ACP sessions can be bound to threads:
OpenClaw binds a thread to a target ACP session.
Follow-up messages in that thread route to the bound ACP session.
ACP output is delivered back to the same thread.
Unfocus/close/archive/idle-timeout or max-age expiry removes the binding.
Thread binding support is adapter-specific. If the active channel adapter does not support thread bindings, OpenClaw returns a clear unsupported/unavailable message.
Required feature flags for thread-bound ACP:
acp.enabled=true
acp.dispatch.enabled is on by default (set false to pause ACP dispatch)
Channel-adapter ACP thread-spawn flag enabled (adapter-specific)
Discord: channels.discord.threadBindings.spawnAcpSessions=true
Telegram: channels.telegram.threadBindings.spawnAcpSessions=true
​
Thread supporting channels
Any channel adapter that exposes session/thread binding capability.
Current built-in support:
Discord threads/channels
Telegram topics (forum topics in groups/supergroups and DM topics)
Plugin channels can add support through the same binding interface.
​
Channel specific settings
For non-ephemeral workflows, configure persistent ACP bindings in top-level bindings[] entries.
​
Binding model
bindings[].type="acp" marks a persistent ACP conversation binding.
bindings[].match identifies the target conversation:
Discord channel or thread: match.channel="discord" + match.peer.id="<channelOrThreadId>"
Telegram forum topic: match.channel="telegram" + match.peer.id="<chatId>:topic:<topicId>"
bindings[].agentId is the owning OpenClaw agent id.
Optional ACP overrides live under bindings[].acp:
mode (persistent or oneshot)
label
cwd
backend
​
Runtime defaults per agent
Use agents.list[].runtime to define ACP defaults once per agent:
agents.list[].runtime.type="acp"
agents.list[].runtime.acp.agent (harness id, for example codex or claude)
agents.list[].runtime.acp.backend
agents.list[].runtime.acp.mode
agents.list[].runtime.acp.cwd
Override precedence for ACP bound sessions:
bindings[].acp.*
agents.list[].runtime.acp.\_
global ACP defaults (for example acp.backend)
Example:
{
agents: {
list: [
{
id: "codex",
runtime: {
type: "acp",
acp: {
agent: "codex",
backend: "acpx",
mode: "persistent",
cwd: "/workspace/openclaw",
},
},
},
{
id: "claude",
runtime: {
type: "acp",
acp: { agent: "claude", backend: "acpx", mode: "persistent" },
},
},
],
},
bindings: [
{
type: "acp",
agentId: "codex",
match: {
channel: "discord",
accountId: "default",
peer: { kind: "channel", id: "222222222222222222" },
},
acp: { label: "codex-main" },
},
{
type: "acp",
agentId: "claude",
match: {
channel: "telegram",
accountId: "default",
peer: { kind: "group", id: "-1001234567890:topic:42" },
},
acp: { cwd: "/workspace/repo-b" },
},
{
type: "route",
agentId: "main",
match: { channel: "discord", accountId: "default" },
},
{
type: "route",
agentId: "main",
match: { channel: "telegram", accountId: "default" },
},
],
channels: {
discord: {
guilds: {
"111111111111111111": {
channels: {
"222222222222222222": { requireMention: false },
},
},
},
},
telegram: {
groups: {
"-1001234567890": {
topics: { "42": { requireMention: false } },
},
},
},
},
}
Behavior:
OpenClaw ensures the configured ACP session exists before use.
Messages in that channel or topic route to the configured ACP session.
In bound conversations, /new and /reset reset the same ACP session key in place.
Temporary runtime bindings (for example created by thread-focus flows) still apply where present.
​
Start ACP sessions (interfaces)
​
From sessions_spawn
Use runtime: "acp" to start an ACP session from an agent turn or tool call.
{
"task": "Open the repo and summarize failing tests",
"runtime": "acp",
"agentId": "codex",
"thread": true,
"mode": "session"
}
Notes:
runtime defaults to subagent, so set runtime: "acp" explicitly for ACP sessions.
If agentId is omitted, OpenClaw uses acp.defaultAgent when configured.
mode: "session" requires thread: true to keep a persistent bound conversation.
Interface details:
task (required): initial prompt sent to the ACP session.
runtime (required for ACP): must be "acp".
agentId (optional): ACP target harness id. Falls back to acp.defaultAgent if set.
thread (optional, default false): request thread binding flow where supported.
mode (optional): run (one-shot) or session (persistent).
default is run
if thread: true and mode omitted, OpenClaw may default to persistent behavior per runtime path
mode: "session" requires thread: true
cwd (optional): requested runtime working directory (validated by backend/runtime policy).
label (optional): operator-facing label used in session/banner text.
streamTo (optional): "parent" streams initial ACP run progress summaries back to the requester session as system events.
When available, accepted responses include streamLogPath pointing to a session-scoped JSONL log (<sessionId>.acp-stream.jsonl) you can tail for full relay history.
​
Sandbox compatibility
ACP sessions currently run on the host runtime, not inside the OpenClaw sandbox.
Current limitations:
If the requester session is sandboxed, ACP spawns are blocked.
Error: Sandboxed sessions cannot spawn ACP sessions because runtime="acp" runs on the host. Use runtime="subagent" from sandboxed sessions.
sessions_spawn with runtime: "acp" does not support sandbox: "require".
Error: sessions_spawn sandbox="require" is unsupported for runtime="acp" because ACP sessions run outside the sandbox. Use runtime="subagent" or sandbox="inherit".
Use runtime: "subagent" when you need sandbox-enforced execution.
​
From /acp command
Use /acp spawn for explicit operator control from chat when needed.
/acp spawn codex --mode persistent --thread auto
/acp spawn codex --mode oneshot --thread off
/acp spawn codex --thread here
Key flags:
--mode persistent|oneshot
--thread auto|here|off
--cwd <absolute-path>
--label <name>
See Slash Commands.
​
Session target resolution
Most /acp actions accept an optional session target (session-key, session-id, or session-label).
Resolution order:
Explicit target argument (or --session for /acp steer)
tries key
then UUID-shaped session id
then label
Current thread binding (if this conversation/thread is bound to an ACP session)
Current requester session fallback
If no target resolves, OpenClaw returns a clear error (Unable to resolve session target: ...).
​
Spawn thread modes
/acp spawn supports --thread auto|here|off.
Mode Behavior
auto In an active thread: bind that thread. Outside a thread: create/bind a child thread when supported.
here Require current active thread; fail if not in one.
off No binding. Session starts unbound.
Notes:
On non-thread binding surfaces, default behavior is effectively off.
Thread-bound spawn requires channel policy support:
Discord: channels.discord.threadBindings.spawnAcpSessions=true
Telegram: channels.telegram.threadBindings.spawnAcpSessions=true
​
ACP controls
Available command family:
/acp spawn
/acp cancel
/acp steer
/acp close
/acp status
/acp set-mode
/acp set
/acp cwd
/acp permissions
/acp timeout
/acp model
/acp reset-options
/acp sessions
/acp doctor
/acp install
/acp status shows the effective runtime options and, when available, both runtime-level and backend-level session identifiers.
Some controls depend on backend capabilities. If a backend does not support a control, OpenClaw returns a clear unsupported-control error.
​
ACP command cookbook
Command What it does Example
/acp spawn Create ACP session; optional thread bind. /acp spawn codex --mode persistent --thread auto --cwd /repo
/acp cancel Cancel in-flight turn for target session. /acp cancel agent:codex:acp:<uuid>
/acp steer Send steer instruction to running session. /acp steer --session support inbox prioritize failing tests
/acp close Close session and unbind thread targets. /acp close
/acp status Show backend, mode, state, runtime options, capabilities. /acp status
/acp set-mode Set runtime mode for target session. /acp set-mode plan
/acp set Generic runtime config option write. /acp set model openai/gpt-5.2
/acp cwd Set runtime working directory override. /acp cwd /Users/user/Projects/repo
/acp permissions Set approval policy profile. /acp permissions strict
/acp timeout Set runtime timeout (seconds). /acp timeout 120
/acp model Set runtime model override. /acp model anthropic/claude-opus-4-5
/acp reset-options Remove session runtime option overrides. /acp reset-options
/acp sessions List recent ACP sessions from store. /acp sessions
/acp doctor Backend health, capabilities, actionable fixes. /acp doctor
/acp install Print deterministic install and enable steps. /acp install
​
Runtime options mapping
/acp has convenience commands and a generic setter.
Equivalent operations:
/acp model <id> maps to runtime config key model.
/acp permissions <profile> maps to runtime config key approval_policy.
/acp timeout <seconds> maps to runtime config key timeout.
/acp cwd <path> updates runtime cwd override directly.
/acp set <key> <value> is the generic path.
Special case: key=cwd uses the cwd override path.
/acp reset-options clears all runtime overrides for target session.
​
acpx harness support (current)
Current acpx built-in harness aliases:
pi
claude
codex
opencode
gemini
kimi
When OpenClaw uses the acpx backend, prefer these values for agentId unless your acpx config defines custom agent aliases.
Direct acpx CLI usage can also target arbitrary adapters via --agent <command>, but that raw escape hatch is an acpx CLI feature (not the normal OpenClaw agentId path).
​
Required config
Core ACP baseline:
{
acp: {
enabled: true,
// Optional. Default is true; set false to pause ACP dispatch while keeping /acp controls.
dispatch: { enabled: true },
backend: "acpx",
defaultAgent: "codex",
allowedAgents: ["pi", "claude", "codex", "opencode", "gemini", "kimi"],
maxConcurrentSessions: 8,
stream: {
coalesceIdleMs: 300,
maxChunkChars: 1200,
},
runtime: {
ttlMinutes: 120,
},
},
}
Thread binding config is channel-adapter specific. Example for Discord:
{
session: {
threadBindings: {
enabled: true,
idleHours: 24,
maxAgeHours: 0,
},
},
channels: {
discord: {
threadBindings: {
enabled: true,
spawnAcpSessions: true,
},
},
},
}
If thread-bound ACP spawn does not work, verify the adapter feature flag first:
Discord: channels.discord.threadBindings.spawnAcpSessions=true
See Configuration Reference.
​
Plugin setup for acpx backend
Install and enable plugin:
openclaw plugins install acpx
openclaw config set plugins.entries.acpx.enabled true
Local workspace install during development:
openclaw plugins install ./extensions/acpx
Then verify backend health:
/acp doctor
​
acpx command and version configuration
By default, the acpx plugin (published as @openclaw/acpx) uses the plugin-local pinned binary:
Command defaults to extensions/acpx/node_modules/.bin/acpx.
Expected version defaults to the extension pin.
Startup registers ACP backend immediately as not-ready.
A background ensure job verifies acpx --version.
If the plugin-local binary is missing or mismatched, it runs: npm install --omit=dev --no-save acpx@<pinned> and re-verifies.
You can override command/version in plugin config:
{
"plugins": {
"entries": {
"acpx": {
"enabled": true,
"config": {
"command": "../acpx/dist/cli.js",
"expectedVersion": "any"
}
}
}
}
}
Notes:
command accepts an absolute path, relative path, or command name (acpx).
Relative paths resolve from OpenClaw workspace directory.
expectedVersion: "any" disables strict version matching.
When command points to a custom binary/path, plugin-local auto-install is disabled.
OpenClaw startup remains non-blocking while the backend health check runs.
See Plugins.
​
Permission configuration
ACP sessions run non-interactively — there is no TTY to approve or deny file-write and shell-exec permission prompts. The acpx plugin provides two config keys that control how permissions are handled:
​
permissionMode
Controls which operations the harness agent can perform without prompting.
Value Behavior
approve-all Auto-approve all file writes and shell commands.
approve-reads Auto-approve reads only; writes and exec require prompts.
deny-all Deny all permission prompts.
​
nonInteractivePermissions
Controls what happens when a permission prompt would be shown but no interactive TTY is available (which is always the case for ACP sessions).
Value Behavior
fail Abort the session with AcpRuntimeError. (default)
deny Silently deny the permission and continue (graceful degradation).
​
Configuration
Set via plugin config:
openclaw config set plugins.entries.acpx.config.permissionMode approve-all
openclaw config set plugins.entries.acpx.config.nonInteractivePermissions fail
Restart the gateway after changing these values.
Important: OpenClaw currently defaults to permissionMode=approve-reads and nonInteractivePermissions=fail. In non-interactive ACP sessions, any write or exec that triggers a permission prompt can fail with AcpRuntimeError: Permission prompt unavailable in non-interactive mode. If you need to restrict permissions, set nonInteractivePermissions to deny so sessions degrade gracefully instead of crashing.
​
Troubleshooting
Symptom Likely cause Fix
ACP runtime backend is not configured Backend plugin missing or disabled. Install and enable backend plugin, then run /acp doctor.
ACP is disabled by policy (acp.enabled=false) ACP globally disabled. Set acp.enabled=true.
ACP dispatch is disabled by policy (acp.dispatch.enabled=false) Dispatch from normal thread messages disabled. Set acp.dispatch.enabled=true.
ACP agent "<id>" is not allowed by policy Agent not in allowlist. Use allowed agentId or update acp.allowedAgents.
Unable to resolve session target: ... Bad key/id/label token. Run /acp sessions, copy exact key/label, retry.
--thread here requires running /acp spawn inside an active ... thread --thread here used outside a thread context. Move to target thread or use --thread auto/off.
Only <user-id> can rebind this thread. Another user owns thread binding. Rebind as owner or use a different thread.
Thread bindings are unavailable for <channel>. Adapter lacks thread binding capability. Use --thread off or move to supported adapter/channel.
Sandboxed sessions cannot spawn ACP sessions ... ACP runtime is host-side; requester session is sandboxed. Use runtime="subagent" from sandboxed sessions, or run ACP spawn from a non-sandboxed session.
sessions_spawn sandbox="require" is unsupported for runtime="acp" ... sandbox="require" requested for ACP runtime. Use runtime="subagent" for required sandboxing, or use ACP with sandbox="inherit" from a non-sandboxed session.
Missing ACP metadata for bound session Stale/deleted ACP session metadata. Recreate with /acp spawn, then rebind/focus thread.
AcpRuntimeError: Permission prompt unavailable in non-interactive mode permissionMode blocks writes/exec in non-interactive ACP session. Set plugins.entries.acpx.config.permissionMode to approve-all and restart gateway. See Permission configuration.
ACP session fails early with little output Permission prompts are blocked by permissionMode/nonInteractivePermissions. Check gateway logs for AcpRuntimeError. For full permissions, set permissionMode=approve-all; for graceful degradation, set nonInteractivePermissions=deny.
ACP session stalls indefinitely after completing work Harness process finished but ACP session did not report completion. Monitor with ps aux | grep acpx; kill stale processes manually.

Agent coordination
Multi-Agent Sandbox & Tools
​
Overview
Each agent in a multi-agent setup can now have its own:
Sandbox configuration (agents.list[].sandbox overrides agents.defaults.sandbox)
Tool restrictions (tools.allow / tools.deny, plus agents.list[].tools)
This allows you to run multiple agents with different security profiles:
Personal assistant with full access
Family/work agents with restricted tools
Public-facing agents in sandboxes
setupCommand belongs under sandbox.docker (global or per-agent) and runs once when the container is created.
Auth is per-agent: each agent reads from its own agentDir auth store at:
~/.openclaw/agents/<agentId>/agent/auth-profiles.json
Credentials are not shared between agents. Never reuse agentDir across agents. If you want to share creds, copy auth-profiles.json into the other agent’s agentDir.
For how sandboxing behaves at runtime, see Sandboxing. For debugging “why is this blocked?”, see Sandbox vs Tool Policy vs Elevated and openclaw sandbox explain.
​
Configuration Examples
​
Example 1: Personal + Restricted Family Agent
{
"agents": {
"list": [
{
"id": "main",
"default": true,
"name": "Personal Assistant",
"workspace": "~/.openclaw/workspace",
"sandbox": { "mode": "off" }
},
{
"id": "family",
"name": "Family Bot",
"workspace": "~/.openclaw/workspace-family",
"sandbox": {
"mode": "all",
"scope": "agent"
},
"tools": {
"allow": ["read"],
"deny": ["exec", "write", "edit", "apply_patch", "process", "browser"]
}
}
]
},
"bindings": [
{
"agentId": "family",
"match": {
"provider": "whatsapp",
"accountId": "*",
"peer": {
"kind": "group",
"id": "120363424282127706@g.us"
}
}
}
]
}
Result:
main agent: Runs on host, full tool access
family agent: Runs in Docker (one container per agent), only read tool
​
Example 2: Work Agent with Shared Sandbox
{
"agents": {
"list": [
{
"id": "personal",
"workspace": "~/.openclaw/workspace-personal",
"sandbox": { "mode": "off" }
},
{
"id": "work",
"workspace": "~/.openclaw/workspace-work",
"sandbox": {
"mode": "all",
"scope": "shared",
"workspaceRoot": "/tmp/work-sandboxes"
},
"tools": {
"allow": ["read", "write", "apply_patch", "exec"],
"deny": ["browser", "gateway", "discord"]
}
}
]
}
}
​
Example 2b: Global coding profile + messaging-only agent
{
"tools": { "profile": "coding" },
"agents": {
"list": [
{
"id": "support",
"tools": { "profile": "messaging", "allow": ["slack"] }
}
]
}
}
Result:
default agents get coding tools
support agent is messaging-only (+ Slack tool)
​
Example 3: Different Sandbox Modes per Agent
{
"agents": {
"defaults": {
"sandbox": {
"mode": "non-main", // Global default
"scope": "session"
}
},
"list": [
{
"id": "main",
"workspace": "~/.openclaw/workspace",
"sandbox": {
"mode": "off" // Override: main never sandboxed
}
},
{
"id": "public",
"workspace": "~/.openclaw/workspace-public",
"sandbox": {
"mode": "all", // Override: public always sandboxed
"scope": "agent"
},
"tools": {
"allow": ["read"],
"deny": ["exec", "write", "edit", "apply_patch"]
}
}
]
}
}
​
Configuration Precedence
When both global (agents.defaults._) and agent-specific (agents.list[]._) configs exist:
​
Sandbox Config
Agent-specific settings override global:
agents.list[].sandbox.mode > agents.defaults.sandbox.mode
agents.list[].sandbox.scope > agents.defaults.sandbox.scope
agents.list[].sandbox.workspaceRoot > agents.defaults.sandbox.workspaceRoot
agents.list[].sandbox.workspaceAccess > agents.defaults.sandbox.workspaceAccess
agents.list[].sandbox.docker._ > agents.defaults.sandbox.docker._
agents.list[].sandbox.browser._ > agents.defaults.sandbox.browser._
agents.list[].sandbox.prune._ > agents.defaults.sandbox.prune._
Notes:
agents.list[].sandbox.{docker,browser,prune}._ overrides agents.defaults.sandbox.{docker,browser,prune}._ for that agent (ignored when sandbox scope resolves to "shared").
​
Tool Restrictions
The filtering order is:
Tool profile (tools.profile or agents.list[].tools.profile)
Provider tool profile (tools.byProvider[provider].profile or agents.list[].tools.byProvider[provider].profile)
Global tool policy (tools.allow / tools.deny)
Provider tool policy (tools.byProvider[provider].allow/deny)
Agent-specific tool policy (agents.list[].tools.allow/deny)
Agent provider policy (agents.list[].tools.byProvider[provider].allow/deny)
Sandbox tool policy (tools.sandbox.tools or agents.list[].tools.sandbox.tools)
Subagent tool policy (tools.subagents.tools, if applicable)
Each level can further restrict tools, but cannot grant back denied tools from earlier levels. If agents.list[].tools.sandbox.tools is set, it replaces tools.sandbox.tools for that agent. If agents.list[].tools.profile is set, it overrides tools.profile for that agent. Provider tool keys accept either provider (e.g. google-antigravity) or provider/model (e.g. openai/gpt-5.2).
​
Tool groups (shorthands)
Tool policies (global, agent, sandbox) support group:_ entries that expand to multiple concrete tools:
group:runtime: exec, bash, process
group:fs: read, write, edit, apply_patch
group:sessions: sessions_list, sessions_history, sessions_send, sessions_spawn, session_status
group:memory: memory_search, memory_get
group:ui: browser, canvas
group:automation: cron, gateway
group:messaging: message
group:nodes: nodes
group:openclaw: all built-in OpenClaw tools (excludes provider plugins)
​
Elevated Mode
tools.elevated is the global baseline (sender-based allowlist). agents.list[].tools.elevated can further restrict elevated for specific agents (both must allow).
Mitigation patterns:
Deny exec for untrusted agents (agents.list[].tools.deny: ["exec"])
Avoid allowlisting senders that route to restricted agents
Disable elevated globally (tools.elevated.enabled: false) if you only want sandboxed execution
Disable elevated per agent (agents.list[].tools.elevated.enabled: false) for sensitive profiles
​
Migration from Single Agent
Before (single agent):
{
"agents": {
"defaults": {
"workspace": "~/.openclaw/workspace",
"sandbox": {
"mode": "non-main"
}
}
},
"tools": {
"sandbox": {
"tools": {
"allow": ["read", "write", "apply_patch", "exec"],
"deny": []
}
}
}
}
After (multi-agent with different profiles):
{
"agents": {
"list": [
{
"id": "main",
"default": true,
"workspace": "~/.openclaw/workspace",
"sandbox": { "mode": "off" }
}
]
}
}
Legacy agent._ configs are migrated by openclaw doctor; prefer agents.defaults + agents.list going forward.
​
Tool Restriction Examples
​
Read-only Agent
{
"tools": {
"allow": ["read"],
"deny": ["exec", "write", "edit", "apply_patch", "process"]
}
}
​
Safe Execution Agent (no file modifications)
{
"tools": {
"allow": ["read", "exec", "process"],
"deny": ["write", "edit", "apply_patch", "browser", "gateway"]
}
}
​
Communication-only Agent
{
"tools": {
"sessions": { "visibility": "tree" },
"allow": ["sessions_list", "sessions_send", "sessions_history", "session_status"],
"deny": ["exec", "write", "edit", "apply_patch", "read", "browser"]
}
}
​
Common Pitfall: “non-main”
agents.defaults.sandbox.mode: "non-main" is based on session.mainKey (default "main"), not the agent id. Group/channel sessions always get their own keys, so they are treated as non-main and will be sandboxed. If you want an agent to never sandbox, set agents.list[].sandbox.mode: "off".
​
Testing
After configuring multi-agent sandbox and tools:
Check agent resolution:
openclaw agents list --bindings
Verify sandbox containers:
docker ps --filter "name=openclaw-sbx-"
Test tool restrictions:
Send a message requiring restricted tools
Verify the agent cannot use denied tools
Monitor logs:
tail -f "${OPENCLAW_STATE_DIR:-$HOME/.openclaw}/logs/gateway.log" | grep -E "routing|sandbox|tools"
​
Troubleshooting
​
Agent not sandboxed despite mode: "all"
Check if there’s a global agents.defaults.sandbox.mode that overrides it
Agent-specific config takes precedence, so set agents.list[].sandbox.mode: "all"
​
Tools still available despite deny list
Check tool filtering order: global → agent → sandbox → subagent
Each level can only further restrict, not grant back
Verify with logs: [tools] filtering tools for agent:${agentId}
​
Container not isolated per agent
Set scope: "agent" in agent-specific sandbox config
Default is "session" which creates one container per session
