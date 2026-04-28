# Verify

## 验证范围
- 覆盖什么：
  - 侧边栏导航是否已扩展为更接近工作台的分区结构
  - 新增“本地 Dify / 知识库”工作区是否已落到前端
  - 新增工作区状态接口与知识命中抽查接口是否可用
  - 既有首页与知识检索接口是否仍正常返回
  - 是否已针对首次进入体验、移动端可用性和关键操作反馈做一轮前端微调
  - 是否已将“事故复盘”页从长表单收敛为更轻量的分组 / 时间线式布局
- 不覆盖什么：
  - 纯本机 Dify 完整部署
  - 浏览器级完整点击回归
  - 知识库内容质量优化效果

## 验证方法
- 命令：
  - `python -m compileall web_demo/app.py`
  - 使用 `FastAPI TestClient` 直接调用 `/api/workspace/status`、`/api/search`、`/`
- 手工/脚本步骤：
  - 检查首页 HTML 是否包含 `data-view-target="workspace"`、`data-view-panel="workspace"`、`workspaceStatusList`、`workspaceSearchBtn`
  - 检查 `/api/workspace/status` 是否返回 Dify 状态、知识库条数、低置信积压、分类与危险源摘要
  - 检查 `/api/search?q=乙醇储存&top_k=3` 是否返回命中条目
  - 检查事故复盘页 HTML 是否包含 `incident-shell`、`incident-highlight-card`、`incident-timeline-item`、`incident-filter-card` 等新结构
  - 检查事故复盘相关 DOM id 是否仍唯一存在，以确保现有 JS 提交逻辑不被破坏
  - 检查本地 `http://127.0.0.1:8088` 首页是否仍返回 `200`
- 场景：
  - 本地代码级验证，不依赖当前桌面浏览器 profile

## 预期结果
- 预期 1：
  - 页面从“仅分区”进一步收敛成“有本地状态承接能力的工作台”
- 预期 2：
  - 新增工作区能展示本地 Dify 是否已配置、知识库条数与待补强项
- 预期 3：
  - 知识命中抽查可直接返回当前问题的候选条目
- 预期 4：
  - 事故复盘页在不改接口语义的前提下，视觉上更像“分组工作台”而不是“连续长表单”
- 预期 5：
  - “知识命中抽查”页不仅返回候选条目，还能解释“为什么命中、相关性如何、下一步怎么补强”
- 预期 6：
  - 管理端看板首屏应先给一句话结论，而不是先让老师阅读明细指标和列表

## 实际结果
- 实际 1：
  - `web_demo/templates/index.html` 已新增侧边栏导航项 `本地 Dify / 知识库`，并新增 `data-view-panel="workspace"` 工作区分区
- 实际 2：
  - `web_demo/app.py` 已新增 `/api/workspace/status`，返回 `dify_enabled`、`dify_connection_status`、`kb_rows`、`low_confidence_queue_count`、`top_categories`、`top_hazards` 等字段
- 实际 3：
  - 代码级验证中，`/api/workspace/status` 返回 `200`，并显示当前本地 Dify `unconfigured`、本地知识条目 `96`、低置信积压 `1`
- 实际 4：
  - 代码级验证中，`/api/search?q=乙醇储存&top_k=3` 返回 `200`，命中条目包含 `KB-1002`、`KB-1039`、`KB-1036`
- 实际 5：
  - 代码级验证中，首页 `/` 返回 `200`，且 HTML 已包含 `data-view-target="workspace"`、`data-view-panel="workspace"`、`workspaceStatusList`、`workspaceSearchBtn`
- 实际 6：
  - `python -m compileall web_demo/app.py` 通过，说明新增接口与模型定义没有语法错误
- 实际 7：
  - 已新增 Windows 本地运行入口文件：仓库根 `.env.web_demo.example`、`scripts/start_web_demo_local.ps1`、`scripts/stop_web_demo_local.ps1`、`scripts/status_web_demo_local.ps1`，用于统一当前仓库版本的本地启动方式
- 实际 8：
  - 已停掉旧的 8090 遗留实例，并确认 8088 当前实例已切换到仓库最新版本；`/health`、`/api/meta`、`/api/workspace/status` 均返回 200
- 实际 9：
  - 当前新实例已能通过标准本地状态脚本读取 runtime，说明本地标准启动入口已形成闭环
- 实际 10：
  - `POST /api/chat` with `mode=agent` 在本地 8088 返回 `200`，且 `model = gpt-5.3-codex`、`decision = llm_answer`
- 实际 11：
  - 修复 OpenAI 兼容 SSE UTF-8 解码后，中文问题（如“实验室发生乙醇泄漏后第一步怎么做”）返回内容不再乱码
- 实际 12：
  - `artifacts/local-web-demo/runtime.json` 已记录 `app_version`、`acceptance_status`、`chat_lane_agent`、`lab_lane_state`、`runtime_model`
- 实际 13：
  - `scripts/status_web_demo_local.ps1` 已能直接显示 `runtime_model`、`agent_lane`、`lab_mode`、`launch_file`、`err_file`
- 实际 14：
  - 已完成一轮用户体验向前端微调：
    - 移动端加入侧边栏折叠按钮，默认可先收起导航
    - 主内容区新增“当前工作场景 / 推荐下一步”上下文卡片
    - 关键按钮统一加入 loading / busy 文案反馈
    - 关键交互元素加入 `focus-visible` 样式
    - 小屏幕下自动弱化侧边栏说明文字，减少视觉噪音
- 实际 15：
  - 浏览器移动端快照已确认：
    - 默认进入总览页时能先看到“展开导航”按钮，而不是整块导航占满首屏
    - 顶部已出现“当前工作场景 / 推荐下一步”上下文区
    - 页面主信息区的首次进入路径更明确
- 实际 16：
  - 已继续完成“培训与看板”信息层级优化：
    - 页面结构已拆成“培训动作区 + 管理结果区”
    - 管理端筛选项已改成带标签的过滤卡片
    - 低置信问题、最近高风险场景、事故复盘摘要已改成更明确的洞察卡片承载
  - 当前更适合答辩展示时按“培训能做什么 -> 管理能看到什么”来讲解
- 实际 17：
  - 已完成“事故复盘”页轻量重构：页面已新增 `incident-shell` 双栏布局、顶部亮点卡、三段式录入区和右侧状态说明区
- 实际 18：
  - 代码级检查确认：`incidentReporter`、`incidentTitle`、`incidentSeverity`、`incidentScenario`、`incidentCorrectiveActions`、`incidentDueDate`、`createIncidentBtn`、`incidentList` 等相关 DOM id 均只存在 1 次，说明原有创建 / 刷新逻辑仍可复用
- 实际 19：
  - 本地 `http://127.0.0.1:8088` 请求返回 `200`，说明当前模板改造后页面仍可访问
- 实际 20：
  - 已完成 Playwright 浏览器级真实回归：桌面端切入“事故复盘”页后，`incident-shell` 布局、3 张亮点卡、2 段时间线、右侧说明区和状态筛选区均正常显示
- 实际 21：
  - 桌面端已成功创建复盘记录，页面返回 `已创建复盘记录：INC-20260416-0d015c50`，且复盘列表中可看到新建标题“乙醇回流实验前发现审批未闭环”
- 实际 22：
  - 移动端浏览器级回归已确认：默认首屏可见导航折叠按钮，导航初始收起；展开后可进入“事故复盘”页，首屏可见标题、亮点卡和创建按钮
- 实际 23：
  - 已完成“知识命中解释层”前端收敛：workspace 页新增 `workspaceSearchSummary` 总结区、补强建议区，以及每条知识的“命中原因 / 相关性判断 / 下一步怎么用”解释块
- 实际 24：
  - `GET /api/search` 针对“夜间准备进行乙醇回流实验，审批未闭环而且现场只有我一个人，这种情况能开工吗？”返回 `200`，命中 `5` 条候选知识，首条标题为“高风险实验可以一个人单独做吗”，score=`15.25`
- 实际 25：
  - Playwright 浏览器级回归已确认：桌面端解释层总结卡、补强建议卡、5 条命中项与 15 个解释块均正常显示；移动端也能正常显示总结区和知识条目
- 实际 26：
  - 已完成“看板一句话结论层”前端收敛：training 页管理端看板顶部新增 3 张总结卡，分别输出“总体结论 / 当前最需要关注 / 答辩时怎么说”
- 实际 27：
  - `GET /api/admin/dashboard?days=30` 返回 `200`，当前指标包括：清单阻断率 `89%`、培训通过率 `0%`、未闭环复盘 `1`、逾期整改 `0`，低置信问题积压 `5` 条
- 实际 28：
  - Playwright 浏览器级回归已确认：桌面端和移动端均可正常显示 3 张总结卡；当前主结论为“高风险场景阻断占比为 89%，系统更偏先拦住风险，再允许开工”


- 实际 29：
  - 已完成“低置信标签文案收口”：training 页 `adminLowConfidence` 不再直接显示 `top_score_below_threshold:0.1<3.5`，而是展示“当前问题与知识库场景匹配度偏弱”等自然语言说明
- 实际 30：
  - Playwright 浏览器级回归已确认：本地 `http://127.0.0.1:8088` 的“培训与看板”页中，低置信问题 TOP 区域显示为自然语言文案，且浏览器读取结果 `containsRawReason=false`

## 证据
- 路径：
  - `web_demo/templates/index.html`
  - `docs/ops/frontend_benchmark_reference_cn.md`
  - `artifacts/browser-regression-20260416/incident_desktop.png`
  - `artifacts/browser-regression-20260416/incident_mobile.png`
  - `artifacts/browser-regression-20260416/incident_regression_report.json`
  - `artifacts/browser-regression-20260416-workspace/workspace_explain_desktop.png`
  - `artifacts/browser-regression-20260416-workspace/workspace_explain_mobile.png`
  - `artifacts/browser-regression-20260416-workspace/workspace_explain_report.json`
  - `artifacts/browser-regression-20260416-dashboard/dashboard_summary_desktop.png`
  - `artifacts/browser-regression-20260416-dashboard/dashboard_summary_mobile.png`
  - `artifacts/browser-regression-20260416-dashboard/dashboard_summary_report.json`
  - `artifacts/browser-regression-20260416-low-confidence/dashboard_low_confidence_desktop.png`
  - `artifacts/browser-regression-20260416-low-confidence/low_confidence_text.json`
  - `artifacts/browser-regression-20260416-low-confidence/low_confidence_report.json`
  - 当前 change 的 `tasks.md` / `status.md`
- 关键接口证据：
  - `/api/workspace/status` -> 200
  - `/api/search?q=乙醇储存&top_k=3` -> 200
  - `/` -> 200 且包含工作区标记
  - `/api/chat` with `mode=agent` -> 200
  - `/api/meta` -> `runtime_model = gpt-5.3-codex`

## 未通过项
- 未通过项 1：
  - 当前本机 `127.0.0.1:8080` 仍无本地 Dify，`/api/meta` 显示仍处于“结构化回退模式”
- 未通过项 2：
  - 当前已补“事故复盘”页浏览器级真实回归，但整站所有页面的完整浏览器级回归仍未全部覆盖

## 结论
- partial
