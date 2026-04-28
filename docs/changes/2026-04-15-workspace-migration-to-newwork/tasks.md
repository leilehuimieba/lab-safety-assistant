# Tasks

## 当前目标
- 将当前项目工作区迁移到 `D:\newwork`，并把本地 Dify 配置收进项目目录内。

## 任务清单
- [x] T1: 建立迁移 change 并切换 active
- [x] T2: 设计新工作区目录结构与命名
- [x] T3: 复制仓库到 `D:\newwork`
- [x] T4: 将 Dify docker 配置迁入新项目目录
- [x] T5: 更新最小必要脚本 / 文档口径
- [x] T6: 验证新路径下仓库与 Dify 配置可读可用
- [x] T7: 恢复 Docker Desktop 运行层并确认新路径下 compose 可读
- [x] T8: 修复新路径下 nginx 入口缺失模板与端口口径
- [x] T9: 定位并修复新路径下本地 Dify `502 Bad Gateway`
- [x] T10: 确认本地 Dify 现有 setup / app / token 状态，并确认 `web_demo` 配置已可指向本地 Dify
- [x] T11: 在新路径下验证 `web_demo` 直连本地 Dify 的实际问答链路
- [x] T12: 统一展示默认 app token 口径，并补最小运行说明
- [x] T13: 补浏览器级展示回归证据（侧边栏切换 / lab / agent / workspace / gate）
- [x] T14: 完成“新旧路径口径最终清理”，统一新目录为唯一默认执行入口

## 依赖关系
- T2 依赖 T1
- T3 依赖 T2
- T4 依赖 T3
- T5 依赖 T4
- T6 依赖 T5
- T7 依赖 T6
- T8 依赖 T7
- T9 依赖 T8
- T10 依赖 T9
- T11 依赖 T10
- T12 依赖 T11
- T13 依赖 T12

## 当前执行项
- 当前正在推进：旧 `D:\workspace` 历史报告口径标注收尾，保留历史证据，同时避免后续阅读误认为当前默认入口仍在旧路径。

## 阻塞项
- 阻塞 1：迁移 change 自身仍需保留对旧 `D:\workspace` 的上下文说明，无法也不应完全去除。

## 完成定义
- [x] proposal 已确认
- [x] design 已确认
- [x] 执行完成
- [x] verify 已补证据
- [x] docs/README 已同步（如需要）
- [ ] roadmap 已同步（如需要）
