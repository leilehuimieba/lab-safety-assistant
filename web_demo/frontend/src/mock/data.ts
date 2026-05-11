import type {
  AdminDashboardResponse,
  ChatRequest,
  ChatResponse,
  ChecklistItem,
  ChecklistSubmitRequest,
  ChecklistSubmitResponse,
  ChecklistTemplateRequest,
  ChecklistTemplateResponse,
  CreateIncidentRequest,
  DemoMetaResponse,
  EmergencyCard,
  EmergencyMatchResponse,
  IncidentListResponse,
  IncidentRecord,
  RiskAssessRequest,
  RiskAssessResponse,
  SearchResponse,
  TrainingRosterStatusResponse,
  TrainingSessionResponse,
  TrainingStatsResponse,
  TrainingSubmitRequest,
  TrainingSubmitResponse,
  WeeklyReportResponse,
  WorkspaceStatusResponse,
} from "../types";

function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
}

function futureDate(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

const citations = [
  {
    kb_id: "kb-chem-001",
    title: "危化品实验前检查规范",
    source_title: "高校实验室安全手册",
    source_org: "校实验室与设备管理处",
    source_url: "https://demo.local/safety/chem-checklist",
    risk_level: "High",
    snippet: "涉及挥发性溶剂和强腐蚀性试剂时，须在通风橱内操作，并确认 PPE 与废液收集方案。",
    score: 0.96,
  },
  {
    kb_id: "kb-fire-003",
    title: "有机溶剂加热事故应急处置",
    source_title: "实验室事故应急卡片",
    source_org: "实验安全中心",
    source_url: "https://demo.local/emergency/fire-solvent",
    risk_level: "Critical",
    snippet: "起火时优先切断热源与电源，确认人员撤离，再根据火源类型选用灭火介质。",
    score: 0.92,
  },
];

const emergencyCards: EmergencyCard[] = [
  {
    id: "fire-organic",
    title: "有机溶剂起火",
    category: "火灾",
    summary: "适用于乙醇、丙酮、乙醚等易燃溶剂在加热或转移过程中起火。",
    trigger_signs: ["明火", "刺鼻烟雾", "容器局部高温"],
    immediate_actions: [
      "立即停止加热并切断电源/气源",
      "组织周边人员撤离，保持通道畅通",
      "使用二氧化碳或干粉灭火器处置初起火情",
    ],
    forbidden: ["禁止泼水灭火", "禁止徒手转移着火容器"],
    ppe: ["护目镜", "实验服", "防热手套"],
    escalation: ["实验人员", "实验室负责人", "楼层安全员", "校保卫处"],
  },
  {
    id: "chem-leak",
    title: "腐蚀性化学品泄漏",
    category: "化学品泄漏",
    summary: "适用于酸、碱等腐蚀性液体的小范围泄漏处置。",
    trigger_signs: ["容器破裂", "地面液体蔓延", "刺激性气味"],
    immediate_actions: [
      "隔离泄漏区域，限制无关人员进入",
      "佩戴防护手套和护目镜后使用吸附材料围堵",
      "按危废流程收集污染物并做好标识",
    ],
    forbidden: ["禁止直接用手清理", "禁止将残液直接倒入下水道"],
    ppe: ["护目镜", "面屏", "耐化手套"],
    escalation: ["实验人员", "实验室负责人", "危化品管理员"],
  },
  {
    id: "bio-exposure",
    title: "生物样本暴露",
    category: "生物安全",
    summary: "适用于样本飞溅、皮肤接触或操作面污染等情形。",
    trigger_signs: ["样本飞溅", "开放性伤口接触", "操作台面污染"],
    immediate_actions: [
      "停止操作并按流程进行局部冲洗/消毒",
      "封存暴露区域相关器材",
      "第一时间上报指导老师和生物安全员",
    ],
    forbidden: ["禁止带污染 PPE 离开现场", "禁止隐瞒暴露情况"],
    ppe: ["实验服", "一次性手套", "口罩"],
    escalation: ["实验人员", "指导老师", "生物安全员", "校医院"],
  },
];

const defaultChecklistItems: ChecklistItem[] = [
  { id: "c1", label: "已确认实验 SOP 最新版本并完成阅读", critical: true, checked: true, note: "" },
  { id: "c2", label: "已确认 SDS 可获取，危险特性已知", critical: true, checked: true, note: "" },
  { id: "c3", label: "已准备护目镜、实验服、耐化手套", critical: true, checked: true, note: "" },
  { id: "c4", label: "通风橱运行正常，风速检查通过", critical: true, checked: false, note: "答辩演示时可强调需现场确认" },
  { id: "c5", label: "废液桶标签与分类处置方案已确认", critical: false, checked: true, note: "" },
  { id: "c6", label: "指导老师/实验负责人已知晓本次实验安排", critical: false, checked: true, note: "" },
];

let incidentRecords: IncidentRecord[] = [
  {
    incident_id: "INC-2026-001",
    reported_at: isoDaysAgo(12),
    updated_at: isoDaysAgo(10),
    reporter: "张三",
    title: "乙醇加热时局部起火",
    scenario: "有机合成预热阶段",
    severity: "high",
    status: "verified",
    location: "化学楼 A201",
    cause_categories: ["明火使用不规范", "易燃液体靠近热源"],
    immediate_actions: ["切断热源", "使用干粉灭火器处理"],
    corrective_actions: ["调整热源隔离距离", "补做火灾培训"],
    owner: "李老师",
    due_date: futureDate(-2),
    closure_notes: "已复盘并完成培训",
    recurrence_risk: "medium",
    overdue: false,
    overdue_days: 0,
  },
  {
    incident_id: "INC-2026-002",
    reported_at: isoDaysAgo(6),
    updated_at: isoDaysAgo(2),
    reporter: "王五",
    title: "酸液滴落导致台面腐蚀",
    scenario: "酸碱滴定",
    severity: "medium",
    status: "action_in_progress",
    location: "化学楼 B103",
    cause_categories: ["容器转移不规范"],
    immediate_actions: ["围堵清理", "中和残液"],
    corrective_actions: ["更换托盘", "规范倾倒流程"],
    owner: "周老师",
    due_date: futureDate(-1),
    closure_notes: "",
    recurrence_risk: "low",
    overdue: true,
    overdue_days: 1,
  },
  {
    incident_id: "INC-2026-003",
    reported_at: isoDaysAgo(3),
    updated_at: isoDaysAgo(1),
    reporter: "赵六",
    title: "样本飞溅暴露",
    scenario: "离心前取样",
    severity: "high",
    status: "in_review",
    location: "生物楼 C302",
    cause_categories: ["离心管盖未压紧", "操作台防护不足"],
    immediate_actions: ["局部冲洗", "现场消毒", "上报老师"],
    corrective_actions: ["复训 PPE", "更新离心前检查项"],
    owner: "陈老师",
    due_date: futureDate(2),
    closure_notes: "",
    recurrence_risk: "medium",
    overdue: false,
    overdue_days: 0,
  },
];

export const demoWorkspaceStatus: WorkspaceStatusResponse = {
  dify_enabled: false,
  dify_connection_status: "unconfigured",
  kb_rows: 142,
  kb_imported: 398,
  low_confidence_queue_count: 5,
  top_categories: [
    { label: "化学", count: 56 },
    { label: "通用", count: 36 },
    { label: "生物", count: 18 },
    { label: "设备安全", count: 8 },
    { label: "危化品", count: 7 },
    { label: "电气", count: 6 },
  ],
  top_hazards: [
    { label: "危化品", count: 36 },
    { label: "综合安全", count: 29 },
    { label: "综合", count: 16 },
    { label: "生物", count: 15 },
    { label: "储存", count: 12 },
    { label: "高压", count: 12 },
    { label: "生物危废", count: 10 },
    { label: "危废", count: 9 },
  ],
};

export const demoMeta: DemoMetaResponse = {
  app_version: "demo-showcase-20260511",
  chat_lane_lab: "实验前风险判断 + 本地知识检索",
  chat_lane_agent: "结构化演示代理模式",
  acceptance_status: "答辩演示版",
  formal_eval_score: "20/20",
  stability_status: "3/3 PASS",
  knowledge_base_rows: 142,
  knowledge_base_imported: 398,
  demo_port: "8088",
  runtime_model: "mock-demo-mode",
};

export function mockChat(request: ChatRequest): ChatResponse {
  const q = request.question;

  if (q.includes("起火") || q.includes("火灾")) {
    return {
      answer:
        "检测到你提问的是实验室火灾场景。系统建议立即停止操作、切断热源与电源、组织撤离，并根据火源类型使用合适灭火器材，同时通知老师和安全员。",
      mode: request.mode,
      model: "demo-mock",
      decision: "emergency_redirect",
      risk_level: "Critical",
      matched_rule_id: "EMG-FIRE-001",
      matched_rule_action: "redirect_to_emergency",
      low_confidence: false,
      low_confidence_reason: "",
      followup_logged: false,
      citations,
    };
  }

  return {
    answer:
      "根据你当前描述，该实验属于中高风险场景。建议在开工前确认 SOP、SDS、PPE、通风条件和废液处置方案；若涉及强腐蚀或易燃试剂，应提交老师确认后再开工。",
    mode: request.mode,
    model: "demo-mock",
    decision: "llm_answer_guarded",
    risk_level: "High",
    matched_rule_id: "PRECHECK-101",
    matched_rule_action: "teacher_review_recommended",
    low_confidence: false,
    low_confidence_reason: "",
    followup_logged: true,
    citations,
  };
}

export function mockSearch(query: string): SearchResponse {
  return {
    results: citations.filter(
      (c) => c.title.includes(query) || c.snippet.includes(query)
    ),
  };
}

export function mockRiskAssess(request: RiskAssessRequest): RiskAssessResponse {
  return {
    scenario: request.scenario,
    risk_score: 82,
    risk_level: "High",
    key_hazards: ["易燃溶剂", "腐蚀性试剂", "加热操作"],
    ppe: ["护目镜", "实验服", "耐化手套"],
    forbidden: ["在开放明火附近转移有机溶剂", "未确认废液分类前直接排放"],
    emergency_actions: ["立即切断热源", "按火灾卡片处置", "通知老师与安全员"],
    recommended_steps: [
      "在通风橱内完成关键操作",
      "确认 SDS 与 SOP 已阅读",
      "先完成老师审核再启动实验",
    ],
    low_confidence: false,
    low_confidence_reason: "",
    citations,
  };
}

export function mockChecklistTemplate(
  request: ChecklistTemplateRequest
): ChecklistTemplateResponse {
  return {
    scenario: request.scenario,
    risk_score: 82,
    risk_level: "High",
    key_hazards: ["易燃溶剂", "腐蚀性试剂", "通风条件要求高"],
    checklist: defaultChecklistItems.map((item) => ({ ...item })),
    recommended_actions: [
      "关键步骤在通风橱内完成",
      "开工前让老师确认风险点",
      "确认废液桶与灭火器位置",
    ],
    citations,
  };
}

export function mockChecklistSubmit(
  request: ChecklistSubmitRequest
): ChecklistSubmitResponse {
  const blockingReasons = request.checklist
    .filter((i) => i.critical && !i.checked)
    .map((i) => `关键项未确认：${i.label}`);

  const allowStart = blockingReasons.length === 0;

  return {
    record_id: `CHK-${Date.now()}`,
    submitted_at: new Date().toISOString(),
    scenario: request.scenario,
    operator: request.operator,
    risk_score: 82,
    risk_level: "High",
    key_hazards: ["易燃溶剂", "腐蚀性试剂", "加热操作"],
    allow_start: allowStart,
    blocking_reasons: allowStart
      ? []
      : [...blockingReasons, "高风险实验建议老师确认后再开工"],
    next_actions: allowStart
      ? ["保留检查记录", "按照 SOP 进行操作", "注意废液分类"]
      : ["补齐关键检查项", "联系老师审核", "确认应急器材位置"],
  };
}

export function mockEmergencyCards(): EmergencyCard[] {
  return emergencyCards.map((card) => ({ ...card }));
}

export function mockEmergencyMatch(query: string): EmergencyMatchResponse {
  const lower = query.toLowerCase();
  const matched =
    lower.includes("火") || lower.includes("燃")
      ? emergencyCards[0]
      : lower.includes("泄漏") || lower.includes("酸")
        ? emergencyCards[1]
        : emergencyCards[2];

  return {
    query,
    matched_card_id: matched.id,
    confidence: 0.93,
    card: { ...matched },
  };
}

export function mockTrainingSession(): TrainingSessionResponse {
  return {
    session_id: "demo-training-001",
    total_questions: 5,
    pass_threshold: 80,
    questions: [
      {
        id: "q1",
        category: "危化品",
        prompt: "使用易燃有机溶剂加热时，以下哪项是正确做法？",
        options: ["在明火附近快速完成", "在通风橱内并远离点火源", "随手放置废液"],
        multiple: false,
        references: ["危化品实验前检查规范"],
      },
      {
        id: "q2",
        category: "PPE",
        prompt: "以下哪些属于化学实验常见基础 PPE？",
        options: ["护目镜", "实验服", "耐化手套", "凉鞋"],
        multiple: true,
        references: ["实验室 PPE 使用规范"],
      },
      {
        id: "q3",
        category: "火灾",
        prompt: "有机溶剂起火时，优先动作是什么？",
        options: ["围观判断", "切断热源并组织撤离", "直接泼水"],
        multiple: false,
        references: ["有机溶剂起火应急卡片"],
      },
      {
        id: "q4",
        category: "废弃物",
        prompt: "危化废液处置正确的是？",
        options: ["按类别收集并贴标签", "直接倒入下水道", "混装省空间"],
        multiple: false,
        references: ["危废分类管理办法"],
      },
      {
        id: "q5",
        category: "生物安全",
        prompt: "样本暴露后应采取哪些动作？",
        options: ["局部冲洗/消毒", "及时上报", "继续操作避免耽误", "封存污染器材"],
        multiple: true,
        references: ["生物样本暴露处理流程"],
      },
    ],
  };
}

export function mockTrainingSubmit(
  request: TrainingSubmitRequest
): TrainingSubmitResponse {
  return {
    attempt_id: `ATT-${Date.now()}`,
    session_id: request.session_id,
    participant: request.participant,
    submitted_at: new Date().toISOString(),
    score: 4,
    total_questions: 5,
    pass_threshold: 80,
    passed: true,
    weak_categories: ["生物安全"],
    recommended_actions: [
      "复习生物样本暴露处置流程",
      "补做一次实验前 PPE 核查练习",
    ],
    review: [
      {
        question_id: "q5",
        category: "生物安全",
        prompt: "样本暴露后应采取哪些动作？",
        selected_indices: [0, 1],
        correct_indices: [0, 1, 3],
        correct: false,
        explanation: "除冲洗和上报外，还应封存污染器材，避免二次暴露。",
        references: ["生物样本暴露处理流程"],
      },
    ],
  };
}

export function mockTrainingStats(): TrainingStatsResponse {
  return {
    attempt_count: 128,
    pass_rate: 0.91,
    average_score: 4.3,
    latest_submitted_at: new Date().toISOString(),
    category_mistakes: {
      生物安全: 12,
      危化品: 7,
      废弃物: 5,
    },
    recent_scores: [5, 4, 4, 5, 3, 4, 5],
  };
}

export function mockTrainingRoster(): TrainingRosterStatusResponse {
  return {
    roster: [
      {
        student_id: "2023001",
        name: "张三",
        class_name: "化学工程 2201",
        lab_group: "A组",
        completed: true,
        passed: true,
        latest_score: 5,
        latest_submitted_at: isoDaysAgo(1),
      },
      {
        student_id: "2023002",
        name: "李四",
        class_name: "化学工程 2201",
        lab_group: "A组",
        completed: true,
        passed: true,
        latest_score: 4,
        latest_submitted_at: isoDaysAgo(2),
      },
      {
        student_id: "2023003",
        name: "王五",
        class_name: "生物工程 2202",
        lab_group: "B组",
        completed: false,
        passed: false,
        latest_score: 0,
        latest_submitted_at: "",
      },
    ],
  };
}

export function mockAdminDashboard(): AdminDashboardResponse {
  return {
    metrics: [
      { label: "检查提交", value: "128", detail: "近30天" },
      { label: "高风险阻断", value: "17", detail: "需老师确认" },
      { label: "低置信问题", value: "5", detail: "待补知识" },
      { label: "事故记录", value: "3", detail: "近30天" },
      { label: "培训通过率", value: "91%", detail: "学生端" },
    ],
    low_confidence_top: [
      { label: "HF 配置步骤", count: 4 },
      { label: "高压灭菌锅故障处理", count: 3 },
      { label: "生物样本外带要求", count: 2 },
      { label: "危废桶标签规范", count: 2 },
      { label: "有机溶剂混放", count: 1 },
    ],
    recent_high_risk_scenarios: [
      {
        submitted_at: isoDaysAgo(1),
        scenario: "浓硫酸参与的有机合成预热实验",
        risk_level: "High",
        allow_start: false,
        operator: "张三",
      },
      {
        submitted_at: isoDaysAgo(2),
        scenario: "离心前生物样本裂解操作",
        risk_level: "High",
        allow_start: false,
        operator: "王五",
      },
      {
        submitted_at: isoDaysAgo(3),
        scenario: "高压气瓶更换与气路检测",
        risk_level: "Critical",
        allow_start: false,
        operator: "赵六",
      },
    ],
    incident_summary: {
      open: 0,
      in_review: 1,
      action_in_progress: 1,
      verified: 1,
      closed: 0,
    },
    overdue_incidents: ["INC-2026-002"],
  };
}

export function mockWeeklyReport(): WeeklyReportResponse {
  return {
    report: `# 实验室安全周报（演示版）

## 一、本周概况
- 开工检查提交：42
- 高风险阻断：6
- 老师待审核：2
- 低置信问题新增：1

## 二、重点风险
1. 有机溶剂加热场景出现频率较高
2. 生物样本暴露处置知识掌握不足
3. 废液分类与标签填写仍需强化

## 三、建议动作
1. 对高风险实验实行老师预审
2. 对危化品实验补充 SOP 学习
3. 对新成员开展一次专项培训
`,
  };
}

export function mockIncidents(): IncidentListResponse {
  return {
    incidents: incidentRecords.map((item) => ({ ...item })),
    total: incidentRecords.length,
  };
}

export function mockCreateIncident(data: CreateIncidentRequest): IncidentRecord {
  const record: IncidentRecord = {
    incident_id: `INC-2026-${String(incidentRecords.length + 1).padStart(3, "0")}`,
    reported_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    reporter: data.reporter,
    title: data.title,
    scenario: data.scenario,
    severity: data.severity,
    status: "open",
    location: data.location,
    cause_categories: data.cause_categories,
    immediate_actions: data.immediate_actions,
    corrective_actions: [],
    owner: data.owner,
    due_date: data.due_date,
    closure_notes: "",
    recurrence_risk: "medium",
    overdue: false,
    overdue_days: 0,
  };

  incidentRecords = [record, ...incidentRecords];
  return { ...record };
}

export function mockUpdateIncident(
  id: string,
  patch: Partial<IncidentRecord>
): IncidentRecord {
  const index = incidentRecords.findIndex((item) => item.incident_id === id);
  if (index === -1) {
    throw new Error("Incident not found");
  }

  incidentRecords[index] = {
    ...incidentRecords[index],
    ...patch,
    updated_at: new Date().toISOString(),
  };

  return { ...incidentRecords[index] };
}
