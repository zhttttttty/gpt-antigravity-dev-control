# 流程审核与修复 — 2026-11-01

审核基线：GitHub main `0dffa7d364f2ea2c5f175dd611e2a427994a3b1f`；本轮版本：**3.6.0-local**。
范围：CLI、首次安装、日常 run、高级路由及 prepare/launch/verify/collect、进程执行、
PowerShell 探测和调度、回执/恢复文档、测试及 CI。历史任务不因本次维护自动重派或完成。

## 结论

项目已具备有界委派、工作树隔离与证据收集能力，主要问题集中在首次使用和故障路径。
本轮将日常流程固定为 **doctor → run → runs**，自检仅首次使用或排障时执行。
复杂任务保留契约与审批，明确自动生成文件和有效审批复用边界，避免继续堆叠编排层。

## 已修复问题

| 优先级 | 原问题与触发方式 | 修复与验证方式 |
|---|---|---|
| P1 | verify 后提交新代码并改回执 HEAD，collect 可能接受旧检查结论 | 控制器保存验证 HEAD、回执 SHA-256 和独立副本；对抗测试拒绝替换 |
| P1 | agy 超时只终止父进程，子命令可能继续写入 | agy 与检查共用进程组执行及超时清理；真实子进程延迟写入测试 |
| P1 | 普通 init 未预检 `.ai`、`.gitignore` 链接和类型冲突，可能写到项目外或部分初始化 | 所有预期写入路径统一预检；测试外部目录不受影响、冲突前零写入 |
| P2 | 探测运行 agent/agents 等非帮助命令，可能进入会话；PowerShell 探测无限等待 | 只调用 help/version，PowerShell 单项限时 15 秒；保留 login UNKNOWN |
| P2 | print-only CLI 被缺少交互参数误拦截；标志前缀被误识别，未声明的可选参数仍被发送 | 按运行模式验证、精确匹配标志、可选参数按能力发送，help 非零明确失败 |
| P2 | CLI 不支持 stream-json 时，正常文本被判格式错误 | 只在请求 stream-json 时校验 NDJSON，保留权限/认证错误优先级 |
| P2 | Skill 复制到无缓存忽略规则的干净项目，预览产生 pyc 后自报脏源 | 统一入口禁用字节码；真实复制安装后预览及 Git 干净断言 |
| P2 | 后续检查参数有误时，早期检查已执行，verify 目录残留 | 执行前预检完整矩阵和重复命令策略；执行中保存进度，内部错误记为 FAILED |
| P2 | 缺 PyYAML、无 HEAD、脏源缺少统一定位入口 | 标准库启动的 doctor 提供逐项原因和下一步；run 报错给安装命令或脏路径 |
| P2 | 日常 run 不在 status 中，结果只能手动找 Git 元数据 | runs 列表及完整查询；latest 按更新时间，损坏记录明确报错 |
| P3 | 文档暗示规划时手填七份文件，旧状态页仍称未提交 | 首页统一三步路径，说明自动模板、审批复用、验证快照和当前发布状态 |

## 简化后的使用方式

安装依赖，审查并提交目标项目中的 Skill 文件；也可通过已有安装的绝对脚本路径加 `--repo` 调用，
无需重复复制。源仓库必须已有提交且干净，未提交与忽略内容不会复制。

```powershell
$ctl = Join-Path $PWD '.agents/skills/antigravity-delegate/scripts/control.py'
python $ctl doctor
python $ctl run "补充 README 安装说明" --allow README.md --check "git diff --check"
python $ctl runs latest
```

普通任务无需 init、模型角色配置、task.yaml 或手填回执。run 可加 --dry-run 预览。
READY_FOR_REVIEW 后检查完整结果、Diff、新增文件和日志，再明确整合修改。
架构、安全、迁移等任务继续使用高级协议，不用 run 规避已有契约或预算。

## 验证边界与后续工作

本轮使用离线夹具、真实本机子进程及假执行器验证行为，不调用真实 Provider 编码。
本机 doctor 已实际读取 agy 帮助并识别原生可执行文件和参数能力；这不证明登录或真实任务完成率。

- 工作树和 Scope 是 Git 隔离及事后核验，不是系统沙箱；进程树清理为尽力处理。
- 高级验证要求干净、已提交候选。验证后修改或旧 VERIFIED 记录缺少绑定时，须审查并建立新尝试，不能继承旧 PASS。
- 硬退出停在 VERIFYING 时读取 progress.json 并核对实际进程；不自动删锁、重试、改预算或合并。
- 真实效果仍需经授权的小任务测量完成时间、返工与审查成本，不据离线测试承诺节省额度。
- 历史任务、嵌套独立仓库和旧工作树继续保留；生命周期清理应单独核对修改及合并状态。

## 实际验证

- Windows 本地全量 158 项 Python unittest 通过（141.095 秒）。
- PowerShell 多代理协议测试通过，包含只读探测和原有调度、恢复检查。
- 23 个 Python 文件语法、17 个 YAML、18 个 TOML 解析通过。
- 55 份维护范围内 Markdown 的 123 个本地链接检查通过。
- 根项目及配置夹具 check-orchestration 均 PASS；这是离线配置一致性检查。
- 真实子进程模拟执行覆盖改文件、写报告、控制器检查及按 ID 找回结果；源工作区保持不变。
- 持久任务仍为 3 个 REVIEW、1 个 BLOCKED；任务、人工状态和归档资料无 Git 差异。
- 维护文件 Git 空白检查通过。CI 已扩展为 Linux、Windows 两端运行 Python 工作流测试。
