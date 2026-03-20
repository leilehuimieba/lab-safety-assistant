# 知识库溯源规范

## 1. 溯源字段定义

| 字段 | 必填 | 说明 | 示例 |
|------|------|------|------|
| source_type | 是 | 来源类型 | SOP/MSDS/制度/应急预案/网页/经验 |
| source_title | 是 | 来源标题 | MSDS-乙醇、实验室安全管理制度 |
| source_org | 是 | 来源机构 | 实验室管理处、南京林业大学 |
| source_version | 否 | 版本号 | v1.0、2023版 |
| source_date | 是 | 发布/更新日期 | 2024-01-15 |
| source_url | 条件必填 | 来源URL | https://example.com/sop |

## 2. 来源类型分级

| 级别 | 类型 | 权威度 |
|------|------|--------|
| 1 | 国家法规/标准 | 最高 |
| 2 | 制度/SOP/MSDS | 高 |
| 3 | 高校/机构官方文档 | 中 |
| 4 | 公开网页资料 | 中低 |
| 5 | 人工经验/推断 | 低 |

## 3. 填写规范

### 3.1 制度/SOP 类
- source_type: 制度/SOP
- source_title: 制度/ SOP 名称
- source_org: 制定机构名称
- source_date: 发布或实施日期
- source_url: 如有官方发布链接则填写

### 3.2 MSDS 类
- source_type: MSDS
- source_title: MSDS-化学品名称
- source_org: 供应商或编制机构
- source_version: 依据的 MSDS 版本
- source_date: MSDS 版本日期
- source_url: 供应商官网或数据库链接

### 3.3 应急预案类
- source_type: 应急预案
- source_title: 预案名称
- source_org: 编制单位
- source_date: 预案发布日期
- source_url: 预案发布链接

### 3.4 网页来源
- source_type: 网页
- source_title: 页面标题
- source_org: 网站主办单位
- source_date: 页面内容日期或抓取日期
- source_url: 页面 URL

### 3.5 人工经验
- source_type: 经验
- source_title: 经验总结
- source_org: 内部知识
- source_date: 创建日期
- status: draft（需审核）

## 4. 状态流转

```
draft -> pending_review -> approved -> active -> deprecated
                            |
                            v
                       rejected
```

- draft: 待完善溯源信息
- pending_review: 等待审核
- approved: 已审核，待生效
- active: 生效中
- deprecated: 已废弃
- rejected: 审核未通过
