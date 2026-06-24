# Clash Verge Rev / mihomo process routing notes

Generated for the GG proxy subscription service.

## Scope

- Published profile: `mihomo-universal.yaml`
- Node source: current enabled `Proxy_ops_private` inventory
- Published VLESS Reality nodes: GG-US-SEA-BGP-01, GG-Vmrack1, GG-Dedirock
- Ruleset source: `DustinWin/ruleset_geodata` release asset `mihomo-ruleset`
- TUN mode: enabled with `auto-route`, `auto-redirect`, `strict-route`, and DNS hijack for `any:53`

## Evidence and assumptions

- Local Windows evidence on this workstation showed multiple `Codex.exe` desktop processes and multiple `codex.exe` CLI helper processes under the OpenAI Codex app package and user-local Codex bin directory.
- Browser and WebView runtimes such as Edge Beta, `msedge.exe`, and `msedgewebview2.exe` are intentionally not process-proxied by default because that over-routes unrelated browsing. They use `PROXY` only when destination rules require it.
- Official OpenAI / ChatGPT / Codex domains are high-priority `PROXY` rules: `openai.com`, `chatgpt.com`, `oaistatic.com`, `oaiusercontent.com`, `oaistatsig.com`, `auth.openai.com`, `auth0.openai.com`, `cdn.openaimerge.com`. This covers ChatGPT/Codex WebSocket traffic to `chatgpt.com` without broad keyword rules.
- OpenAI-family desktop app paths are `DIRECT` fallbacks after those official domain rules. That prevents Codex Desktop, ChatGPT, or ChatGPT Atlas non-OpenAI destinations such as Google push channels from being dragged into `MATCH,PROXY` by process identity.
- On macOS, Safari app paths are high-priority `DIRECT` process exceptions before official OpenAI domain rules. Use Microsoft Edge when browser-wide `PROXY` behavior is required.
- Antigravity, macOS Microsoft Edge, and Simprint Chrome profile paths are default process-level `PROXY` overrides. Simprint rules target the Chromium browser Simprint launches, not `C:\Users\...\Simprint\simprint.exe`, not `C:\Users\...\Simprint\simprint-runtime.exe`, and not Simprint's fixed WebView2 UI runtime.
- `codexsdk`, `antigravitysdk`, and `cursorsdk` are SDK/library usage patterns, not stable standalone processes. Generic host processes such as `node` and `python` are not process-proxied by default; destination rules decide whether traffic is direct or proxied.
- `mihomo-universal.yaml` merges the Windows, macOS, and Linux process rules into one file. Rules for executables or paths that do not exist on the current OS are expected to miss, not to run or launch anything.
- Antigravity, ChatGPT, ChatGPT Atlas, Codex, Simprint, and stable Microsoft Edge can spawn helper, renderer, GPU, plugin, update, and CLI processes. The default profile uses narrow app install path rules only where process identity is the right control; OpenAI-family apps remain destination-rule based with DIRECT app fallbacks.
- Cursor domain rules are the highest-priority DIRECT rules and are evaluated before process rules, so Cursor destinations stay direct no matter which app opens them. The first rule is fuzzy `DOMAIN-KEYWORD,cursor,DIRECT`, followed by explicit suffixes: `cursor.sh`, `cursor.com`, `cursorapi.com`, `cursor-cdn.com`, `anysphere.co`, and `anysphere.inc`.
- Cursor is also protected by DIRECT process rules in this profile.
- WPS / Kingsoft domain rules are evaluated after Cursor and before process rules. The first rule is `DOMAIN-KEYWORD,kingsoft,DIRECT`, followed by suffixes: `kingsoft.com`, `kingsoft-office-service.com`, `wps.cn`, `wpscdn.cn`, `wpscdn.com`, `kdocs.cn`, `kdocs.com`, `ksosoft.com`, `ksord.com`, `wpsplus.com`.
- WPS Office, cloud sync (`wpscloudsvr.exe`), and update helpers are also protected by DIRECT process/path rules on Windows.

## WPS / Kingsoft domain DIRECT rules

- `DOMAIN-KEYWORD,kingsoft,DIRECT`
- `DOMAIN-SUFFIX,kingsoft.com,DIRECT`
- `DOMAIN-SUFFIX,kingsoft-office-service.com,DIRECT`
- `DOMAIN-SUFFIX,wps.cn,DIRECT`
- `DOMAIN-SUFFIX,wpscdn.cn,DIRECT`
- `DOMAIN-SUFFIX,wpscdn.com,DIRECT`
- `DOMAIN-SUFFIX,kdocs.cn,DIRECT`
- `DOMAIN-SUFFIX,kdocs.com,DIRECT`
- `DOMAIN-SUFFIX,ksosoft.com,DIRECT`
- `DOMAIN-SUFFIX,ksord.com,DIRECT`
- `DOMAIN-SUFFIX,wpsplus.com,DIRECT`

## Direct process protections

Private and mainland China direct guardrails are evaluated before proxy rules. That is intentional for TUN rule mode: domestic CDN traffic, local China apps, Edge Beta, Cursor, WebView2, Safari, and generic runtimes should stay `DIRECT` when they hit China/private rule providers. The final fallback is `MATCH,PROXY`, so non-mainland destinations are proxied for mainland China users.

## windows

### DIRECT process names

- `QQ.exe`
- `QQProtect.exe`
- `TIM.exe`
- `Cursor.exe`
- `cursor.exe`
- `cursor-agent.exe`
- `WeChat.exe`
- `WeChatAppEx.exe`
- `WeChatBrowser.exe`
- `WeChatOCR.exe`
- `Weixin.exe`
- `WXWork.exe`
- `wps.exe`
- `wpp.exe`
- `et.exe`
- `wpspdf.exe`
- `wpscloudsvr.exe`
- `ksolaunch.exe`
- `wpsupdate.exe`
- `ksomisc.exe`

### DIRECT process paths

- `C:\Program Files\Microsoft\Edge Beta\Application\msedge.exe`
- `C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe`
- `C:\Users\*\AppData\Local\Microsoft\Edge Beta\Application\msedge.exe`
- `C:\Users\*\AppData\Local\Programs\Cursor\*`
- `C:\Users\*\AppData\Local\Kingsoft\WPS Office\*`
- `C:\Users\*\AppData\Local\OpenAI\Codex\bin\*\codex.exe`
- `C:\Program Files\WindowsApps\OpenAI.Codex_*\app\*`
- `C:\Program Files\OpenAI\ChatGPT\*`
- `C:\Users\*\AppData\Local\Programs\ChatGPT\*`
- `C:\Program Files\OpenAI\ChatGPT Atlas\*`
- `C:\Users\*\AppData\Local\Programs\ChatGPT Atlas\*`

### Default process-level PROXY overrides

- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe`
- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\simprint.exe`
- `C:\Program Files\Google\Antigravity\*`
- `C:\Program Files\Google\Antigravity*\*`
- `C:\Users\*\AppData\Local\Programs\Antigravity\*`

### Observed app process names, not proxied by default

- `Antigravity.exe`
- `Antigravity IDE.exe`
- `antigravity.exe`
- `antigravity-cli.exe`
- `agy.exe`
- `ChatGPT.exe`
- `ChatGPT Atlas.exe`
- `ChatGPTAtlas.exe`
- `Codex.exe`
- `codex.exe`

### Observed app process paths, not proxied by default

- `C:\Program Files\Google\Antigravity\*`
- `C:\Program Files\Google\Antigravity*\*`
- `C:\Users\*\AppData\Local\Programs\Antigravity\*`
- `C:\Users\*\AppData\Local\OpenAI\Codex\bin\*\codex.exe`
- `C:\Program Files\WindowsApps\OpenAI.Codex_*\app\*`
- `C:\Users\*\Simprint\webview-fixed\*\msedgewebview2.exe`
- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe`
- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\simprint.exe`
- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\*\*`
- `C:\Program Files\Microsoft\Edge\Application\msedge.exe`
- `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
- `C:\Users\*\AppData\Local\Microsoft\Edge\Application\msedge.exe`

## macos

### DIRECT process names

- `QQ`
- `Cursor`
- `Cursor Helper`
- `Cursor Helper (GPU)`
- `Cursor Helper (Plugin)`
- `Cursor Helper (Renderer)`
- `cursor-agent`
- `WeChat`
- `Weixin`
- `WXWork`

### DIRECT process paths

- `/Applications/Cursor.app/Contents/*`
- `/Applications/ChatGPT.app/Contents/*`
- `/Applications/ChatGPT Atlas.app/Contents/*`
- `/Applications/Codex.app/Contents/*`
- `/Users/*/Applications/ChatGPT.app/Contents/*`
- `/Users/*/Applications/ChatGPT Atlas.app/Contents/*`
- `/Users/*/Applications/Codex.app/Contents/*`

### Default process-level PROXY overrides

- `/Applications/Antigravity.app/Contents/*`
- `/Users/*/Applications/Antigravity.app/Contents/*`
- `/Applications/Microsoft Edge.app/Contents/*`
- `/Users/*/Applications/Microsoft Edge.app/Contents/*`

### Observed app process names, not proxied by default

- `Antigravity`
- `Antigravity Helper`
- `Antigravity Helper (GPU)`
- `Antigravity Helper (Plugin)`
- `Antigravity Helper (Renderer)`
- `antigravity`
- `antigravity-cli`
- `agy`
- `ChatGPT`
- `ChatGPT Helper`
- `ChatGPT Atlas`
- `ChatGPT Atlas Helper`
- `ChatGPTAtlas`
- `ChatGPTAtlas Helper`
- `Codex`
- `codex`

### Observed app process paths, not proxied by default

- `/Applications/Antigravity.app/Contents/*`
- `/Applications/ChatGPT.app/Contents/*`
- `/Applications/ChatGPT Atlas.app/Contents/*`
- `/Applications/Codex.app/Contents/*`
- `/Applications/Microsoft Edge.app/Contents/*`

## linux

### DIRECT process names

- `qq`
- `cursor`
- `cursor-agent`
- `wechat`
- `weixin`
- `wxwork`

### DIRECT process paths

- `/usr/bin/cursor*`
- `/opt/chatgpt/*`
- `/usr/bin/chatgpt*`
- `/opt/chatgpt-atlas/*`
- `/usr/bin/chatgpt-atlas*`
- `/usr/bin/chatgptatlas*`
- `/opt/codex/*`
- `/usr/bin/codex`

### Default process-level PROXY overrides

- `/opt/Antigravity/*`
- `/opt/antigravity/*`
- `/usr/bin/antigravity*`

### Observed app process names, not proxied by default

- `antigravity`
- `antigravity-ide`
- `antigravity-cli`
- `agy`
- `chatgpt`
- `chatgpt-atlas`
- `chatgptatlas`
- `codex`

### Observed app process paths, not proxied by default

- `/opt/Antigravity/*`
- `/opt/antigravity/*`
- `/usr/bin/antigravity*`
- `/usr/bin/codex`
- `/opt/microsoft/msedge/*`

## Operational notes

- Import `mihomo-universal.yaml` into Clash Verge Rev as the remote profile for Windows, macOS, and Linux.
- Enable Clash Verge Rev service mode/admin permissions before enabling TUN.
- Keep the subscription host direct so profile updates do not depend on the proxy path.
- If a China app unexpectedly uses the proxy, inspect the destination and add a narrow DIRECT process/path or domain rule. Do not add broad shared-runtime proxy rules.
