# 实验室安全助手平台（Lab Safety Assistant）

面向高校实验室的轻量安全工作台，覆盖：

1. 安全问答
2. 风险评估
3. 开工检查
4. 培训记录
5. 老师工作台
6. 管理员验收看板
7. 事故复盘

当前版本重点是：**能运行、能展示、能留痕、能导出材料**。

## 快速运行

```powershell
cd web_demo
python -m uvicorn app:app --host 127.0.0.1 --port 8101
```

打开：

```text
http://127.0.0.1:8101/
```

健康检查：

```text
http://127.0.0.1:8101/health
```

## 主要角色

### 学生

- 提安全问题
- 做风险评估
- 生成开工检查
- 完成安全培训

### 老师

- 查看待审核开工
- 查看高风险提醒
- 上传培训名单
- 查看/复制未完成培训名单
- 导出老师处理清单

### 管理员

- 查看知识库数量
- 检查证据链接
- 查看测试结果
- 导出验收包

## 老师名单功能

模板路径：

```text
data_sources/training_roster_template.csv
```

CSV 字段：

```csv
student_id,name,class_name,lab_group,required_training
2026001,张三,化学工程1班,A组,true
```

老师可在页面中：

1. 下载名单模板
2. 填写学生名单
3. 上传 CSV
4. 点击“未完成培训”卡片查看名单
5. 一键复制未完成名单发班群

## 测试

```powershell
python -m pytest -q
```

## 当前产品化说明

详见：

```text
docs/product/product_delivery_note_20260427.md
```
