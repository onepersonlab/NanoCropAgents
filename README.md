# NanoCropAgents 🌱

**面向豆科作物纳米处理方案设计的多智能体协同系统**

---

## 项目定位

NanoCropAgents 采用制度化的多智能体协作架构，实现从用户目标到纳米处理方案推荐的自动化流程。

**核心目标：**
- 根据用户给定目标（如提高萌发率）
- 在纳米材料和处理参数空间中生成候选方案
- 调用代理模型预测 6 个指标
- 结合文献证据做支持与风险判断
- 进行筛选、审核和迭代
- 最终由协调者统一把结果返回给用户

---

## 九大智能体架构

### 入口层

| 智能体 | ID | 职责 |
|--------|-----|------|
| 协调智能体 | coordinator | 唯一对外窗口，接旨、建任务、回传结果 |

### 决策层

| 智能体 | ID | 职责 |
|--------|-----|------|
| 规划智能体 | planner | 将用户目标转为可执行计划 |
| 审议智能体 | reviewer | 审议任务草案，可封驳 |
| 派发智能体 | dispatcher | 拆分子任务，派发给执行层 |

### 执行层

| 智能体 | ID | 职责 | 执行顺序 |
|--------|-----|------|----------|
| 方案生成智能体 | generator | 生成候选纳米处理方案 | 第1步 |
| 审核智能体 | auditor | 检查合法性、约束、OOD风险 | 第2步 |
| 评估智能体 | evaluator | 调用代理模型预测6指标 | 第3步 |
| 文献检索智能体 | retriever | 检索文献证据 | 第4步 |
| 报告智能体 | reporter | 整理输出结果，回奏协调智能体 | 第5步 |

---

## 通信架构

### 完整通信流程

```
用户
 ↓
协调智能体 ←─────────────────────┐
 ↓ 分拣                          │ 回奏结果
规划智能体                        │
 ↓ 规划                          │
审议智能体                        │
 ↓ 准奏/封驳                     │
派发智能体                        │
 ↓ 派发任务                      │
 ├→ 方案生成 → 审核 → 评估 → 文献检索 → 报告智能体
                              ↓ 回奏
                        协调智能体 → 用户
```

### allowAgents 配置

| 智能体 | 允许调用 | 通信目的 |
|--------|----------|----------|
| coordinator | planner, reviewer, dispatcher, reporter | 调用决策层 + 接收回奏 |
| planner | reviewer, dispatcher | 方案送审/直接派发 |
| reviewer | planner, dispatcher | 封驳/准奏 |
| dispatcher | 5个执行层 | 派发子任务 |
| generator | auditor | 结果传递 |
| auditor | evaluator | 结果传递 |
| evaluator | retriever | 结果传递 |
| retriever | reporter | 结果传递 |
| reporter | coordinator | **回奏结果** |

---

## 6个预测指标

| 指标 | 单位 | 说明 |
|------|------|------|
| 萌发率提升 | % | 种子萌发率提升百分比 |
| 出苗率提升 | % | 出苗率提升百分比 |
| 生物量增长 | % | 植株生物量增长 |
| 抗逆指数 | 0-1 | 抗逆能力综合评分 |
| 安全指数 | 0-1 | 环境安全性评分 |
| 成本效益比 | - | 投入产出比 |

---

## 纳米材料库

| 材料 | 类型 | 适用场景 |
|------|------|----------|
| TiO2 | 金属氧化物 | 光合增强、抗逆 |
| SiO2 | 金属氧化物 | 保水、缓释 |
| ZnO | 金属氧化物 | 抗菌、促生长 |
| 碳纳米管 | 碳基 | 养分传输 |
| AgNPs | 金属纳米 | 抗菌 |
| Fe3O4 | 磁性纳米 | 靶向递送 |

---

## 目录结构

```
NanoCropAgents/
├── agents/              # 九大智能体定义
│   ├── coordinator/     # 协调智能体
│   ├── planner/         # 规划智能体
│   ├── reviewer/        # 审议智能体
│   ├── dispatcher/      # 派发智能体
│   ├── generator/       # 方案生成智能体
│   ├── auditor/         # 审核智能体
│   ├── evaluator/       # 评估智能体
│   ├── retriever/       # 文献检索智能体
│   └── reporter/        # 报告智能体
├── agents.json          # 智能体通信配置
├── install.sh           # 一键安装脚本
├── dashboard/           # 看板前端
├── scripts/             # 工具脚本
└── docs/                # 文档
```

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/onepersonlab/NanoCropAgents.git
cd NanoCropAgents

# 一键安装
bash install.sh
```

### 启动看板

```bash
# 启动看板服务器
python3 dashboard/server.py

# 访问看板
# http://127.0.0.1:7999

# 或指定其他端口
python3 dashboard/server.py --port 8888
```

### 使用示例

```
用户: 帮我设计大豆纳米包衣方案，目标是提高萌发率

协调智能体: 已收到您的请求，正在为您创建任务。
任务ID: NCA-20260403-001
目标: 设计大豆纳米包衣方案，提高萌发率
正在转交规划智能体设计方案...

[流程执行中...]

协调智能体: 任务 NCA-20260403-001 已完成

📋 推荐方案 Top-3:
1. TiO2纳米包衣 (综合评分: 85/100)
   - 浓度: 0.1 mg/mL
   - 处理时间: 4小时
   - 预测萌发率提升: 15.2% ± 2.3%

📊 预测指标:
- 萌发率提升: 15.2% ± 2.3%
- 出苗率提升: 12.8% ± 1.9%
- 安全指数: 0.91

📚 文献支持:
- [B级证据] TiO2纳米颗粒处理大豆种子可显著提高萌发率

⚠️ 风险提示:
- 长期使用可能在土壤中积累，建议轮作
```

---

## 技术栈

- **前端**: React + TypeScript + ECharts
- **后端**: Python + FastAPI
- **代理模型**: 机器学习预测模型
- **文献检索**: PubMed/CNKI/WoS API
- **多智能体框架**: OpenClaw

---

## 相关项目

- [OPMALab](https://github.com/onepersonlab/OPMALab) - 实验室主项目
- [GeneClaw](https://github.com/onepersonlab/GeneClaw) - 基因分析多智能体系统

---

## Acknowledgements

- **[Edict](https://github.com/cft0808/edict)** - 三省六部制多智能体协作框架，提供了核心架构设计
- **[OpenClaw](https://github.com/openclaw/openclaw)** - 多智能体运行时框架，提供了 Agent 通信和调度能力

---

## License

MIT