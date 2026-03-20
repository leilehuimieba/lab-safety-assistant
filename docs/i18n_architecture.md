# 多语言支持架构

本文档描述实验室安全小助手的国际化（i18n）和多语言支持架构设计。

## 当前状态

当前系统仅支持中文（`zh-CN`），所有知识库条目、规则、评测集均使用中文编写。

## 多语言支持目标

| 阶段 | 目标 | 优先级 |
|------|------|--------|
| Phase 1 | 英文翻译（面向国际学生） | P1 |
| Phase 2 | 中英双语切换 | P2 |
| Phase 3 | 其他语言扩展框架 | P3 |

## Phase 1: 英文翻译

### 翻译范围

| 类别 | 条目数 | 说明 |
|------|--------|------|
| 知识库（KB） | 92+ | 核心安全知识 |
| 规则库 | 30 | 安全规则 |
| 评测集 | 100 | 测试问题 |
| UI 文本 | - | 界面文案 |

### 翻译流程

1. **导出待翻译文本**
   ```bash
   python scripts/i18n_extract.py --extract
   ```

2. **翻译（人工或机翻）**
   - 优先使用 ChatGPT/Claude 等工具辅助翻译
   - 保持术语一致性（参考术语表）

3. **导入翻译**
   ```bash
   python scripts/i18n_import.py --apply
   ```

4. **验证**
   ```bash
   python scripts/quality_gate.py
   ```

### 术语表

| 中文 | 英文 |
|------|------|
| 实验室安全 | Laboratory Safety |
| 通风柜 | Fume Hood |
| 个人防护用品 (PPE) | Personal Protective Equipment (PPE) |
| 危化品 | Hazardous Chemicals |
| 应急预案 | Emergency Response Plan |
| 废液 | Chemical Waste |
| MSDS/SDS | Material Safety Data Sheet / Safety Data Sheet |
| 生物安全柜 | Biosafety Cabinet |
| 触电 | Electric Shock |
| 灼伤 | Burns |
| 离心机 | Centrifuge |

## Phase 2: 中英双语切换

### 数据结构扩展

在知识库中添加 `language` 字段扩展：

```csv
id,title,title_en,category,question,question_en,answer,answer_en,...
KB-0001,通风柜使用,How to use a fume hood?,...
```

### 实现方案

1. **Dify 工作流**
   - 根据用户语言偏好选择 `question` 或 `question_en`
   - 答案语言与问题语言一致

2. **规则库双语**
   - patterns 保持中英文关键词
   - response 提供中英文版本

### 示例规则（双语）

```yaml
- id: R-001
  category: dangerous_mixing
  patterns: ["漂白水", "次氯酸钠", "bleach", "hydrochloric acid"]
  action: refuse
  response:
    zh: "可能产生有毒气体或剧烈反应，禁止混合。"
    en: "May produce toxic gases or violent reactions. Mixing is prohibited."
```

## Phase 3: 其他语言扩展框架

### 架构设计

```
knowledge_base/
├── zh-CN/
│   └── knowledge_base_curated.csv
├── en-US/
│   └── knowledge_base_curated.csv
├── ja-JP/
│   └── knowledge_base_curated.csv
└── _shared/
    └── terminology.json    # 共享术语表
```

### 扩展语言优先级

| 语言 | 使用场景 | 优先级 |
|------|----------|--------|
| English | 国际学生、联合实验室 | P1 |
| Japanese | 合作高校 | P2 |
| Korean | 合作高校 | P3 |

## 翻译脚本

### i18n_extract.py

提取需要翻译的文本：

```bash
python scripts/i18n_extract.py --extract --output translations/
```

### i18n_import.py

导入翻译后的文本：

```bash
python scripts/i18n_import.py --apply --input translations/
```

### 翻译验证

```bash
# 检查翻译完整性
python scripts/i18n_validate.py --check

# 检查术语一致性
python scripts/i18n_validate.py --terminology
```

## 注意事项

1. **安全相关文本**：涉及安全的术语必须准确翻译，不可产生歧义
2. **法规引用**：不同地区法规不同，翻译时需注明适用地区
3. **文化差异**：某些安全概念可能需要本地化解释

## 相关文档

- [知识库结构](./knowledge_base_schema.md)
- [规则库设计](./safety_rules.md)
