# 本地接服务器 Dify 的最短落地方案

## 1. 适用场景

适用于当前这类情况：

- 本地 `web_demo` 可以运行
- 但本机没有完整跑起 Dify（`127.0.0.1:8081` 不通）
- 你手头已经有一台可用的腾讯云服务器，服务器上已经配置了 Dify 与 `DIFY_APP_API_KEY`
- 你现在优先需要一版“本地可运行、口径上基于 Dify”的可提交版本

> 这套方案的本质是：  
> **本地运行 `web_demo`，服务器提供 Dify 后端。**

它不是“纯本机单机 Dify 部署”。

---

## 2. 当前默认参数

- 服务器：`175.178.90.193`
- SSH 用户：`root`
- SSH key：`C:\Users\33371\.ssh\labsafe_new.pem`
- 远端 Dify：`127.0.0.1:8081`
- 本地 tunnel 端口：`18080`
- 本地 demo 端口：`8090`

之所以默认用 `8090`，是为了避免和你机器上已经在跑的 `8088` 冲突。

---

## 3. 启动命令

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local_demo_via_server_dify.ps1
```

如果你希望手动指定端口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local_demo_via_server_dify.ps1 `
  -TunnelPort 18080 `
  -DemoPort 8090
```

---

## 4. 启动后应该看到什么

成功时会输出：

- 本地 demo 地址
- health 地址
- tunnel 地址
- 当前 `chat_lane_lab`
- runtime 文件位置

默认访问地址：

- 本地页面：`http://127.0.0.1:8090`
- 健康检查：`http://127.0.0.1:8090/health`

---

## 5. 最小验证步骤

### Step 1：检查 health

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8090/health
```

预期：

- 返回 `200`
- body 含 `{"status":"ok"}`

### Step 2：检查 meta

```powershell
Invoke-RestMethod http://127.0.0.1:8090/api/meta
```

重点看：

- `chat_lane_lab`
- `demo_port`
- `app_version`

### Step 3：检查 chat

```powershell
$body = @{ question = '危险实验开始前最关键的阻断项是什么？'; mode = 'lab' } | ConvertTo-Json
Invoke-RestMethod `
  -Uri http://127.0.0.1:8090/api/chat `
  -Method Post `
  -ContentType 'application/json' `
  -Body $body `
  -TimeoutSec 180
```

注意：

- 即使本地已通过 tunnel 接到服务器 Dify，运行结果**仍可能**因为远端 workflow 状态或知识命中问题回退到 fallback
- 因此“桥接成功”和“Dify 工作流本身完全稳定”是两件事，不要混为一谈

---

## 6. 停止命令

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_local_demo_via_server_dify.ps1
```

该脚本会：

- 停止本地 `web_demo`
- 停止 SSH tunnel
- 清理运行时记录文件

---

## 7. 当前推荐口径

如果老师或评委问“你这版是不是基于 Dify”，当前推荐回答：

> 本项目的实验室安全问答正式链路是基于 Dify 工作流设计的。  
> 当前本地演示入口运行在我电脑上，Dify 后端使用已落地的服务器环境；同时系统保留了 fallback 机制，用于上游异常时的兜底。

这个说法比“我已经完全本机单机部署 Dify”更稳，也更符合当前实际状态。
