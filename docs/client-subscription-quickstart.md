# 当前订阅接入速查

## 适用范围

这份文档描述当前这套已发布订阅的真实使用方式，适用于：

- `Ubuntu.online` 上已经发布的订阅入口
- 三节点池：`Lisahost`、`Akilecloud`、`Dedirock`
- Windows / Linux / Android 客户端直接导入

如果你看到公开仓库里还有 `show_info.sh`、单节点 VLESS 分享链接之类的描述，那是 standalone 基线文档，不是这套现网订阅方案的主入口。

## 当前权威入口

- 主订阅 URL：
  - `https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt`
- Hiddify 一键导入：
  - `hiddify://import/https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt#GG%20Proxy%20Nodes`
- sing-box 辅助清单：
  - `https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/singbox-client-profile.json`

## 推荐客户端

- Windows：`Hiddify` 优先，`v2rayN` 备用
- Linux：`Hiddify` 优先，`v2rayN` 备用
- Android：`Hiddify` 优先，`v2rayNG` 备用

## Windows

### 推荐方式

优先使用 `Hiddify`。

### 最短步骤

1. 安装 Hiddify。
2. 直接打开这条导入链接：

```text
hiddify://import/https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt#GG%20Proxy%20Nodes
```

3. 在客户端里更新订阅。
4. 选择你要使用的节点。

### 备用方式

如果你使用 `v2rayN`，把下面这条作为订阅 URL 导入：

```text
https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt
```

## Linux

### 推荐方式

优先使用 `Hiddify` Desktop。

### 最短步骤

1. 安装 Hiddify。
2. 导入同一条 Hiddify 链接，或者直接导入订阅 URL。
3. 更新订阅并选择节点。

### 备用方式

如果你使用 `v2rayN` Linux 版本，同样导入：

```text
https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt
```

## Android

### 推荐方式

优先使用 `Hiddify`。

### 最短步骤

1. 安装 Hiddify Android。
2. 直接打开这条导入链接：

```text
hiddify://import/https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt#GG%20Proxy%20Nodes
```

3. 更新订阅并选择节点。

### 备用方式

如果你使用 `v2rayNG`，把下面这条作为订阅 URL 导入：

```text
https://proxy-subscriptions.svc.prod.lab.gglohh.top:27111/subscriptions/v2ray_nodes.txt
```

## 如何理解和选择节点

- 当前优先级策略是：
  - `Lisahost`
  - `Akilecloud`
  - `Dedirock`
- `infra-core` 自己的 sidecar 会按这个顺序做主备切换。
- 客户端订阅看到的是多个节点；客户端侧是否自动切换，取决于客户端自身能力和你选择的模式。

## 一个容易误判的点

`infra-core` 当前是规则分流，不是“所有流量都强制走远端代理”。

所以：

- 命中规则的流量会按当前主备节点出口
- 不命中规则的流量仍可能直接走宿主默认出口

如果你要验证“代理是否真的生效”，不要只看普通查 IP 网站。运维侧应优先用：

```bash
bash /workspaces/proxy_own/proxy_ops_private/scripts/check_infra_core_egress_ip.sh
```
