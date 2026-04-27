# Tasks

## 当前目标
- 建立本地 / 服务器目录规划与同步规范，明确差异、边界与推荐同步流程，并完成 1 次服务器同步 / 收口演练。

## 任务清单
- [x] T1: 读取项目结构、部署和同步相关文档
- [x] T2: 核对本地仓库实际目录结构
- [x] T3: 只读核对服务器 repo 目录与实际运行目录
- [x] T4: 建立 change 并切换 active
- [x] T5: 落地正式规范文档 `docs/ops/local_server_sync_plan_cn.md`
- [x] T6: 同步 `docs/PROJECT_STRUCTURE.md` 反映当前实际标准结构
- [x] T7: 同步 `docs/README.md` / `docs/roadmap.md` / `docs/changes/INDEX.md` 口径
- [x] T8: 补 verify 证据并完成最小校验
- [x] T9: 按规范执行 1 次服务器同步 / 收口演练
- [x] T10: 修复 deploy shell 脚本换行并归档旧 release 目录

## 依赖关系
- T2 依赖 T1
- T3 依赖 T1
- T4 依赖 T1~T3
- T5 依赖 T4
- T6、T7 依赖 T5
- T8 依赖 T6、T7
- T9 依赖 T8
- T10 依赖 T9

## 当前执行项
- 当前执行项已完成；本 change 已收口。

## 阻塞项
- 当前无硬阻塞

## 完成定义
- [x] proposal 已确认
- [x] design 已确认
- [x] 执行完成
- [x] verify 已补证据
- [x] docs/README 已同步（如需要）
- [x] roadmap 已同步（如需要）
