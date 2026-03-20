# Embedding 模型接入指南 v2

本文说明如何为本地 Dify 部署配置 Embedding 模型，实现语义检索（高质量/混合检索），解决当前"倒排索引噪声多"的问题。

## 背景

当前状态（见 `retrieval_tuning_report.md`）：

- Dify 使用**经济模式**（纯关键词倒排索引）
- 问题：语义相近但措辞不同的问题无法正确召回（如"实验室着火"同时返回3条无关噪声）
- 根因：没有配置 Embedding 模型，无法建立向量索引

接入 Embedding 后可以启用：
- **高质量索引**（每条知识库条目向量化）
- **混合检索**（关键词 + 语义，效果最优）
- 可选：rerank 模型，进一步提升排序

---

## 方案一：Ollama 本地 Embedding（推荐，免费、无需 GPU）

### 1. 安装 Ollama

访问 [ollama.com](https://ollama.com) 下载并安装 Windows/Mac 客户端。

Linux 安装：
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

验证安装：
```bash
ollama --version
```

### 2. 拉取 Embedding 模型

推荐模型（按优先级）：

| 模型 | 参数量 | 特点 | 内存需求 |
|------|--------|------|----------|
| bge-m3 | 567M | 多语言，中文支持好，推荐 | ~1GB |
| nomic-embed-text | 137M | 轻量，英文为主 | ~300MB |
| mxbai-embed-large | 566M | 效果优秀 | ~1.2GB |
| m2-bert-base | 110M | 中文专项 | ~500MB |

```bash
# 推荐：bge-m3，多语言，支持中文效果好
ollama pull bge-m3

# 中文专项（可选）
ollama pull m2-bert-base
```

验证模型可用：
```bash
curl http://localhost:11434/api/embeddings -d '{"model":"bge-m3","prompt":"实验室安全"}'
```

返回包含 `embedding` 数组的 JSON 说明成功。

### 3. Ollama 作为系统级服务（可选）

如果需要在后台运行 Ollama：
```bash
# 创建 systemd 服务文件
sudo nano /etc/systemd/system/ollama.service

# 内容：
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/local/bin/ollama serve
Restart=on-failure

[Install]
WantedBy=default.target

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 4. 在 Dify 中配置 Ollama Embedding

1. 打开 Dify 管理后台 → **设置** → **模型供应商**
2. 找到 **Ollama** 或 **OpenAI-compatible** 供应商（Dify >= 0.6 支持 Ollama）
3. 填写：
   - Base URL：`http://host.docker.internal:11434`
     （Docker 内访问宿主机 Ollama，Windows/Mac 用 `host.docker.internal`；Linux 用宿主机 IP）
   - Model name：`bge-m3`
   - Model type：**Text Embedding**
4. 保存并测试连接

### 5. 在知识库中切换到高质量索引

> **注意：切换索引模式需要重新导入文档，会消耗 embedding 配额（本地免费）**

1. 打开 **知识库** → **实验室安全知识库** → **设置**
2. 将索引模式从 **经济** 改为 **高质量**
3. 选择 Embedding 模型：`bge-m3`
4. 点击保存，等待向量化完成（75 条约 30 秒）

### 6. 配置混合检索

1. 进入应用的 **工作流编辑器**
2. 点击 **知识检索** 节点
3. 将检索方式改为：**混合检索**
4. 参数建议：
   - Top K：`5`
   - Score threshold：`0.5`（低于此相似度的结果不返回）
   - Rerank model：暂时关闭（可选后续再加）

---

## 方案二：使用云端 Embedding API

如果本机配置不足以运行 Ollama，可以使用以下免费/低成本云服务：

| 服务 | 模型 | 特点 | 免费额度 |
|------|------|------|----------|
| 智谱 AI | embedding-3 | 中文效果好，有免费额度 | 100万tokens/月 |
| 硅基流动 | bge-large-zh-v1.5 | 免费，中文专项 | 200万tokens/月 |
| OpenAI | text-embedding-3-small | 效果好，需付费 | $5/1M tokens |
| Cohere | embed-multilingual | 多语言 | $0.1/1M tokens |

### 智谱 AI 配置步骤

1. 注册 [智谱 AI Open API](https://open.bigmodel.cn/)
2. 获取 API Key
3. 在 Dify 中添加 **Zhipu AI** 模型供应商
4. 填入 API Key
5. 选择 embedding-3 模型

### 硅基流动配置步骤

1. 注册 [硅基流动](https://account.siliconflow.cn/)
2. 获取 API Key
3. 在 Dify 中添加 **SiliconFlow** 或 **OpenAI-compatible** 提供商
4. Base URL：`https://api.siliconflow.cn/v1`
5. 选择 bge-large-zh-v1.5 模型

---

## 接入后的效果验证

使用 `eval_set_v1.csv` 中的以下噪声问题重新测试：

```
实验室着火怎么办？      → 应命中 KB-1018（仅1条正确结果，无噪声）
有人触电了怎么办？      → 应命中 KB-1012（仅1条，不再混入 KB-1014）
液氮如何安全使用？      → 应命中 KB-1029 和 WEB-012-002
```

对比 `retrieval_tuning_report.md` 中的旧结果，记录改善情况。

---

## 更新调参记录

接入 Embedding 后，请更新 `retrieval_tuning_report.md`，补充：

- 日期
- 使用的 Embedding 模型名称
- Top K 和 Score threshold 设置
- 5 条召回测试的新结果
- 与旧版对比结论

这份记录是项目答辩时展示"迭代优化过程"的核心证据材料。

---

## 常见问题

**Q：Ollama 运行但 Dify 连接失败？**
A：检查 Docker 网络配置。Dify 运行在 Docker 容器内，访问宿主机需用 `host.docker.internal` 而不是 `localhost`。

**Q：切换高质量索引后知识库变空？**
A：正常现象，Dify 需要重新向量化所有文档。等待进度条完成即可。

**Q：embedding 后回答质量没有提升？**
A：检查 score threshold 是否太低（设 0 则没有过滤效果），或适当调低 Top K 至 3 减少噪声。

**Q：Ollama 模型下载慢？**
A：可以使用镜像加速：
```bash
OLLAMA_HOST=https://your-mirror.com ollama pull bge-m3
```

---

## 下一步优化

1. **Rerank 模型**：启用 rerank 可以进一步提升排序质量
2. **Query 改写**：在检索前对用户问题进行改写，提升召回效果
3. **增量更新**：配置知识库的增量更新机制，而非每次全量重建

---

## 相关文档

- [检索调参记录](./retrieval_tuning_report.md)
- [评测集评估报告](./eval_criteria.md)
