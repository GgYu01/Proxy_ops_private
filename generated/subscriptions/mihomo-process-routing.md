# Clash Verge Rev / mihomo process routing notes

Generated for the GG proxy subscription service.

## Scope

- Published profile: `mihomo-universal.yaml`
- Node source: current enabled `Proxy_ops_private` inventory
- Published VLESS Reality nodes: GG-US-SEA-BGP-01, GG-Vmrack1
- Ruleset source: `DustinWin/ruleset_geodata` release asset `mihomo-ruleset`
- TUN mode: enabled with `auto-route`, `auto-redirect`, `strict-route`, and DNS hijack for `any:53`

## Evidence and assumptions

- Local Windows evidence on this workstation showed multiple `Codex.exe` desktop processes and multiple `codex.exe` CLI helper processes under the OpenAI Codex app package and user-local Codex bin directory.
- Browser fingerprint traffic (Chrome / Edge / Firefox / Brave / Safari / Simprint / ChatGPT desktop) is process-routed to the `ChatGPT` group **after** CN/domestic DIRECT rules, so sites like goofish/qwen stay DIRECT while non-CN browser traffic (including WebRTC/STUN) still shares the QQPW residential exit.
- Official OpenAI / ChatGPT / Codex domains are high-priority `ChatGPT` group rules: `openai.com`, `chatgpt.com`, `oaistatic.com`, `oaiusercontent.com`, `oaistatsig.com`, `auth.openai.com`, `auth0.openai.com`, `cdn.openaimerge.com`. The ChatGPT group defaults to `QQPW-Residential-Reality` (WG residential VLESS). `QQPW-Residential-Hysteria2` is optional. Other nodes remain selectable in that group.
- General non-browser traffic uses the `PROXY` group (default `Auto` over non-QQPW nodes). QQPW exits remain selectable there too.
- Codex CLI/desktop install paths remain `DIRECT` fallbacks for non-OpenAI destinations after official domain rules.
- Antigravity install paths remain process-level `PROXY` overrides (developer tooling, not browser fingerprint).
- `codexsdk`, `antigravitysdk`, and `cursorsdk` are SDK/library usage patterns, not stable standalone processes. Generic host processes such as `node` and `python` are not process-proxied by default; destination rules decide whether traffic is direct or proxied.
- `mihomo-universal.yaml` merges the Windows, macOS, and Linux process rules into one file. Rules for executables or paths that do not exist on the current OS are expected to miss, not to run or launch anything.
- Cursor domain rules are the highest-priority DIRECT rules and are evaluated before process rules, so Cursor destinations stay direct no matter which app opens them. The first rule is fuzzy `DOMAIN-KEYWORD,cursor,DIRECT`, followed by explicit suffixes: `cursor.sh`, `cursor.com`, `cursorapi.com`, `cursor-cdn.com`, `anysphere.co`, and `anysphere.inc`.
- Cursor is also protected by DIRECT process rules in this profile.
- WPS / Kingsoft domain rules are evaluated after Cursor and before process rules. The first rule is `DOMAIN-KEYWORD,kingsoft,DIRECT`, followed by suffixes: `kingsoft.com`, `kingsoft-office-service.com`, `wps.cn`, `wpscdn.cn`, `wpscdn.com`, `kdocs.cn`, `kdocs.com`, `ksosoft.com`, `ksord.com`, `wpsplus.com`.
- WPS Office, cloud sync (`wpscloudsvr.exe`), and update helpers are also protected by DIRECT process/path rules on Windows.
- Domestic APT and container registry mirrors are DIRECT and exempt from fake-ip so WSL apt/podman and local package workflows resolve real addresses. Covered suffixes: `mirrors.tuna.tsinghua.edu.cn`, `deb.debian.org`, `security.debian.org`, `ftp.debian.org`, `mirrors.aliyun.com`, `mirrors.ustc.edu.cn`, `mirrors.huaweicloud.com`, `mirrors.cloud.tencent.com`, `mirror.nju.edu.cn`, `mirrors.163.com`, `docker.m.daocloud.io`, `daocloud.io`.
- Domestic platform domains are DIRECT and exempt from fake-ip so SSH/Git to self-hosted services resolve real addresses. Covered suffixes: `gglohh.top`, `ringzle.com`.
- `ssh` / `git` processes are DIRECT on all platforms so Git-over-SSH and shell access do not break on fake-ip destinations.

## Domestic platform DIRECT rules

- `DOMAIN-SUFFIX,gglohh.top,DIRECT`
- `DOMAIN-SUFFIX,ringzle.com,DIRECT`

## Domestic mirror DIRECT rules

- `DOMAIN-SUFFIX,mirrors.tuna.tsinghua.edu.cn,DIRECT`
- `DOMAIN-SUFFIX,deb.debian.org,DIRECT`
- `DOMAIN-SUFFIX,security.debian.org,DIRECT`
- `DOMAIN-SUFFIX,ftp.debian.org,DIRECT`
- `DOMAIN-SUFFIX,mirrors.aliyun.com,DIRECT`
- `DOMAIN-SUFFIX,mirrors.ustc.edu.cn,DIRECT`
- `DOMAIN-SUFFIX,mirrors.huaweicloud.com,DIRECT`
- `DOMAIN-SUFFIX,mirrors.cloud.tencent.com,DIRECT`
- `DOMAIN-SUFFIX,mirror.nju.edu.cn,DIRECT`
- `DOMAIN-SUFFIX,mirrors.163.com,DIRECT`
- `DOMAIN-SUFFIX,docker.m.daocloud.io,DIRECT`
- `DOMAIN-SUFFIX,daocloud.io,DIRECT`

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

Private and mainland China direct guardrails are evaluated before proxy rules. That is intentional for TUN rule mode: domestic CDN traffic, local China apps, Cursor, WPS, and generic runtimes should stay `DIRECT` when they hit China/private rule providers. Browsers are process-routed to `ChatGPT`. The final fallback is `MATCH,PROXY`, so non-mainland non-browser destinations are proxied for mainland China users.

## windows

### ChatGPT process names (browser fingerprint)

- `chrome.exe`
- `msedge.exe`
- `firefox.exe`
- `brave.exe`
- `opera.exe`
- `vivaldi.exe`
- `chromium.exe`
- `ChatGPT.exe`
- `ChatGPT Atlas.exe`
- `ChatGPTAtlas.exe`

### ChatGPT process paths (browser fingerprint)

- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
- `C:\Users\*\AppData\Local\Google\Chrome\Application\chrome.exe`
- `C:\Program Files\Microsoft\Edge\Application\msedge.exe`
- `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
- `C:\Users\*\AppData\Local\Microsoft\Edge\Application\msedge.exe`
- `C:\Program Files\Microsoft\Edge Beta\Application\msedge.exe`
- `C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe`
- `C:\Users\*\AppData\Local\Microsoft\Edge Beta\Application\msedge.exe`
- `C:\Program Files\Mozilla Firefox\firefox.exe`
- `C:\Program Files (x86)\Mozilla Firefox\firefox.exe`
- `C:\Users\*\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe`
- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\chrome_proxy.exe`
- `C:\Users\*\AppData\Local\Simprint\data\profiles\Chrome *\simprint.exe`
- `C:\Users\*\Simprint\webview-fixed\*\msedgewebview2.exe`
- `C:\Users\*\AppData\Local\Simprint\*\msedgewebview2.exe`
- `C:\Users\*\AppData\Local\Simprint\*\*\msedgewebview2.exe`
- `C:\Users\*\AppData\Local\Simprint\*\*\*\msedgewebview2.exe`
- `C:\Program Files\OpenAI\ChatGPT\*`
- `C:\Users\*\AppData\Local\Programs\ChatGPT\*`
- `C:\Program Files\OpenAI\ChatGPT Atlas\*`
- `C:\Users\*\AppData\Local\Programs\ChatGPT Atlas\*`

### DIRECT process names

- `ssh.exe`
- `git.exe`
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

- `C:\Users\*\AppData\Local\Programs\Cursor\*`
- `C:\Users\*\AppData\Local\Kingsoft\WPS Office\*`
- `C:\Users\*\AppData\Local\OpenAI\Codex\bin\*\codex.exe`
- `C:\Program Files\WindowsApps\OpenAI.Codex_*\app\*`

### Default process-level PROXY overrides

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

### ChatGPT process names (browser fingerprint)

- `Google Chrome`
- `Google Chrome Helper`
- `Chromium`
- `Microsoft Edge`
- `Microsoft Edge Helper`
- `Firefox`
- `Brave Browser`
- `Opera`
- `Vivaldi`
- `Safari`
- `ChatGPT`
- `ChatGPT Helper`
- `ChatGPT Atlas`
- `ChatGPT Atlas Helper`
- `ChatGPTAtlas`
- `ChatGPTAtlas Helper`

### ChatGPT process paths (browser fingerprint)

- `/Applications/Google Chrome.app/Contents/*`
- `/Applications/Chromium.app/Contents/*`
- `/Applications/Microsoft Edge.app/Contents/*`
- `/Applications/Firefox.app/Contents/*`
- `/Applications/Brave Browser.app/Contents/*`
- `/Applications/Opera.app/Contents/*`
- `/Applications/Vivaldi.app/Contents/*`
- `/Applications/Safari.app/Contents/*`
- `/System/Applications/Safari.app/Contents/*`
- `/Users/*/Applications/Google Chrome.app/Contents/*`
- `/Users/*/Applications/Microsoft Edge.app/Contents/*`
- `/Applications/ChatGPT.app/Contents/*`
- `/Applications/ChatGPT Atlas.app/Contents/*`
- `/Users/*/Applications/ChatGPT.app/Contents/*`
- `/Users/*/Applications/ChatGPT Atlas.app/Contents/*`

### DIRECT process names

- `ssh`
- `git`
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
- `/Applications/Codex.app/Contents/*`
- `/Users/*/Applications/Codex.app/Contents/*`

### Default process-level PROXY overrides

- `/Applications/Antigravity.app/Contents/*`
- `/Users/*/Applications/Antigravity.app/Contents/*`

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

### ChatGPT process names (browser fingerprint)

- `google-chrome`
- `chrome`
- `chromium`
- `chromium-browser`
- `microsoft-edge`
- `msedge`
- `firefox`
- `brave`
- `brave-browser`
- `opera`
- `vivaldi`
- `chatgpt`
- `chatgpt-atlas`
- `chatgptatlas`

### ChatGPT process paths (browser fingerprint)

- `/opt/google/chrome/*`
- `/usr/bin/google-chrome*`
- `/usr/bin/chromium*`
- `/opt/microsoft/msedge/*`
- `/usr/bin/microsoft-edge*`
- `/usr/bin/firefox*`
- `/opt/brave.com/brave/*`
- `/usr/bin/brave*`
- `/opt/chatgpt/*`
- `/usr/bin/chatgpt*`
- `/opt/chatgpt-atlas/*`
- `/usr/bin/chatgpt-atlas*`
- `/usr/bin/chatgptatlas*`

### DIRECT process names

- `ssh`
- `git`
- `qq`
- `cursor`
- `cursor-agent`
- `wechat`
- `weixin`
- `wxwork`

### DIRECT process paths

- `/usr/bin/cursor*`
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
