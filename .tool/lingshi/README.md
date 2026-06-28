import os
# 灵台灵识 - 知识管理增强模块

> 灵识 = 灵台管线上的认知层，绑定知识库深度，专用但深。
>
> 基于 index.json 的知识引擎，提供查询、图扩散搜索、链接分析、LLM推理、感知规则、KAR融合等功能。

---

## 快速开始

### 1. MCP Server（推荐）

灵识通过 MCP 协议暴露 **35 个工具**，WorkBuddy / MiMo Code / Cursor 均可直接调用。

**配置文件**：`~/.workbuddy/mcp.json`

```json
{
  "mcpServers": {
    "lingshi": {
      "command": "C:\\Users\\39029\\.workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe",
      "args": ["os.environ.get("LINGTAI_VAULT", "")\\.tool\\lingshi\\mcp_server.py"],
      "enabled": true
    }
  }
}
```

**启用方式**：WorkBuddy → 连接器 → 管理连接器 → 找到 lingshi → 信任

### 2. Python 代码调用

```python
import sys
sys.path.insert(0, r'os.environ.get("LINGTAI_VAULT", "")\.tool\lingshi')

from memory_engine import MemoryEngine
from perception import PerceptionTools
from kar_fusion import KARFusion

# 查询知识
engine = MemoryEngine()
result = engine.query("O与π")

# 注入相关知识
tools = PerceptionTools()
result = tools.inject("O与π")

# KAR统一查询
kar = KARFusion()
result = kar.unified_query("O与π", hops=3)
```

---

## MCP 工具列表（35个）

### 知识库查询

| 工具 | 参数 | 说明 |
|------|------|------|
| `query` | keyword, hops | 查询知识库（含丹房+近期记忆） |
| `search` | keyword, search_content | 搜索页面内容 |
| `analyze` | page_path | 分析页面链接关系 |
| `related` | page_path, max_results | 获取相关页面 |
| `stats` | 无 | 知识库统计概览 |
| `domains` | 无 | 获取域列表 |
| `pages` | domain, limit | 获取页面列表 |
| `graph` | page_path, hops, weighted | 图扩散（默认hops=3，加权） |

### 感知模块

| 工具 | 参数 | 说明 |
|------|------|------|
| `inject` | keyword | 注入相关知识（按品级排序） |
| `save` | content, category, source | 保存新知识（文件名自动过滤引号） |
| `recommend` | current_topic, max_results | 推荐相关页面（按品级排序） |
| `context` | 无 | 生成会话上下文 |
| `profile` | 无 | 获取用户画像（读 WorkBuddy MEMORY.md） |

### Token 与自检

| 工具 | 参数 | 说明 |
|------|------|------|
| `token` | period | Token消耗查询 |

### KAR融合

| 工具 | 参数 | 说明 |
|------|------|------|
| `unified_query` | keyword, hops | 统一查询：知识+关联+推理 |
| `chain_query` | keywords[], hops | 链式查询：多关键词串联 |
| `explore_topic` | topic, depth | 主题探索：从主题出发探索知识网络 |

### LLM推理

| 工具 | 参数 | 说明 |
|------|------|------|
| `analyze_text` | text | LLM文本分析 |
| `summarize_text` | text, max_length | LLM文章总结 |
| `extract_insights` | text | LLM洞察提取 |

### 规则与统计

| 工具 | 参数 | 说明 |
|------|------|------|
| `perception_stats` | period | 感知命中率统计 |
| `rules` | chapter | 台律规则查询（按章节） |

### skillopt（v4.1 睡眠自进化）

| 工具 | 参数 | 说明 |
|------|------|------|
| `skillopt_dryrun` | 无 | 预览进化轮次产出，不暂存不改动 |
| `skillopt_run` | 无 | 手动触发进化轮次 |
| `skillopt_status` | 无 | 查看 staged 规则列表（按自信降序） |
| `skillopt_adopt` | ids(可选) | 采纳 staged 规则，空=全部 🟢 推荐 |
| `skillopt_reject` | id, reason | 拒绝规则 → blacklist |
| `skillopt_log` | days | 进化历史日志 |

### 新层（v4）

| 工具 | 参数 | 说明 |
|------|------|------|
| `observations` | keyword, limit | 查询观察层已归纳模式（规则⑥）|
| `observation_stats` | 无 | 观察层统计信息 |
| `hebbian_stats` | 无 | Hebbian 动态权重统计 |
| `sentinel` | 无 | 感知规则监控报告（健康状态/违规） |

### 其他

| 工具 | 参数 | 说明 |
|------|------|------|
| `tavily_search` | keyword, max_results | 联网搜索（Tavily API，月限1000次）|
| `check_status` | 无 | Git 状态 + 最近操作日志检查 |
| `search_logs` | keyword, days | 搜索日志/体检记录（规则⑤第三步）|

---

## 架构设计

```
灵台完整管线：

原料 → 提炼 → 丹房（index.json）→ 灵识（查询/关联/推理）
                    ↓
              体检 → 内观 → 选题池 → 公众号 → 归档

灵识 = 这条管线上最接近「认知」的那一层
```

### 模块职责

```
灵台/.tool/lingshi/
├── __init__.py              # 模块初始化
├── memory_engine.py         # 记忆引擎（index.json + n-gram回退）
├── auto_edge.py             # 链接分析（linked_from/links_to）
├── reasoning_engine.py      # 推理引擎（LLM增强）
├── llm_reasoning.py         # LLM推理引擎（DeepSeek）
├── token_monitor.py         # Token监测（报告、图表、趋势）
├── perception.py            # 感知模块（规则驱动）
├── kar_fusion.py            # KAR融合（统一查询、链式查询）
├── mcp_server.py            # MCP Server（21个工具）
├── selfcheck.py             # 自检系统（6项检查+6项修复）
├── perception_stats.py      # 感知命中率统计
├── rules.py                 # 台律规则查询
└── README.md                # 本文件
```

---

## 核心功能详解

### 1. 记忆引擎（n-gram回退）

```python
from memory_engine import MemoryEngine

engine = MemoryEngine()

# 查询（自动n-gram回退）
result = engine.query("O与π")
# 返回: {"results": [...], "match_type": "exact/ngram/none", "keyword": "..."}

# 图扩散（hops=3，加权）
results = engine.search_graph("O与π", hops=3, weighted=True)
# 返回按权重排序的页面列表
```

### 2. 感知规则（5条规则）

```markdown
规则1：知识注入 → 用户提问时调用 inject
规则2：自动学习 → 用户提供事实时调用 save
规则3：关联推荐 → 讨论话题时调用 recommend
规则4：会话上下文 → 新会话开始时调用 context
规则5：检索纪律 → 信息类问题时执行三步检索管线
```

### 3. 检索管线（三步不可跳过）

```
第一步：灵台全库检索（query + search）
第二步：图扩散3跳（graph）
第三步：日志/体检回溯
```

### 4. KAR融合

```python
from kar_fusion import KARFusion

kar = KARFusion()

# 统一查询：知识+关联+推理
result = kar.unified_query("O与π", hops=3)

# 链式查询：多关键词串联
result = kar.chain_query(["O与π", "含人量"])

# 主题探索：从主题出发探索知识网络
result = kar.explore_topic("追问", depth=2)
```

### 5. LLM推理（DeepSeek）

```python
from reasoning_engine import ReasoningEngine

engine = ReasoningEngine()

# 分析文本
result = engine.analyze("待分析的文本")

# 总结文本
summary = engine.summarize("待总结的文本")

# 提取洞察
insights = engine.extract_insights("待分析的文本")
```

### 6. 台律规则查询

```python
from rules import LingtaiRules

rules = LingtaiRules()

# 获取所有章节
all_rules = rules.get_rules("all")

# 获取特定章节
field_rules = rules.get_rules("字段")

# 获取文件名规则
filename_rules = rules.get_filename_rules()

# 获取链接规范
link_rules = rules.get_link_rules()
```

---

## 台律约束内化

灵识的工具默认遵守台律规则，AI 无需主动读台律.md：

| 工具 | 台律约束 |
|------|----------|
| `save` | 文件名自动过滤弯/直引号（保留角引号「」） |
| `inject` | 返回结果按品级降序（上品优先），附带品级标签 |
| `recommend` | 返回结果按品级降序，附带品级标签 |
| `rules` | 按章节返回台律核心规则 |

---

## 感知规则配置

规则文件：`灵台/.tool/lingshi/感知规则.md`

AI 在回复用户前，按以下规则调用灵识工具：

- 规则1：用户提问 → 调用 `inject`
- 规则2：用户提供事实 → 调用 `save`
- 规则3：讨论话题 → 调用 `recommend`
- 规则4：新会话开始 → 调用 `context`
- 规则5：信息类问题 → 执行三步检索管线（强制）

---

## 自检系统

运行自检：

```bash
python 灵台/.tool/lingshi/selfcheck.py        # 仅检查
python 灵台/.tool/lingshi/selfcheck.py --fix  # 检查并自动修复
```

检查项：
1. MCP配置
2. MCP服务器
3. 数据源
4. LLM配置
5. 依赖库
6. Token数据库

---

## Token监测

```bash
# 每日报告
python 灵台/.tool/scripts/token_daily_report.py

# 查看统计
python 灵台/.tool/lingshi/token_monitor.py stats

# 查看图表
python 灵台/.tool/lingshi/token_monitor.py chart --days 7
```

---

## 文件结构

```
灵台/.tool/lingshi/
├── __init__.py              # 模块初始化（v2.0.0）
├── memory_engine.py         # 记忆引擎
├── auto_edge.py             # 链接分析
├── reasoning_engine.py      # 推理引擎
├── llm_reasoning.py         # LLM推理（DeepSeek）
├── token_monitor.py         # Token监测
├── perception.py            # 感知模块
├── kar_fusion.py            # KAR融合
├── mcp_server.py            # MCP Server（21个工具）
├── selfcheck.py             # 自检系统
├── perception_stats.py      # 感知统计
├── rules.py                 # 台律规则
├── 感知规则.md               # AI执行规则
├── README.md                # 本文件
└── .cache/                  # LLM缓存
```

---

## 注意事项

1. **数据源**：lingshi/ 读取丹房/.meta/index.json，不维护独立数据库
2. **刷新数据**：修改.md文件后需运行 `build_index.py` 重建索引
3. **编码格式**：所有文件使用UTF-8编码
4. **Token监测**：独立模块，记录查询操作的Token消耗
5. **LLM配置**：需要在 `~/.workbuddy/models.json` 中配置API密钥

---

*灵识 v2.0.0 · 2026-06-27*

---

## 设计规范

> 借鉴 IMA Skill 的安全设计，结合灵台实际场景。

### 1. 安全门（Gate）

所有写入操作必须过安全门，失败立即停止：

| Gate | 检查项 | 失败处理 |
|------|--------|---------|
| GATE 1 | 类型检查（原料/丹房/产出） | 拒绝，告知用户 |
| GATE 2 | 文件名规范（过滤引号、长度限制） | 自动修正 |
| GATE 3 | 重名检查（同名文件是否覆盖） | 询问用户 |
| GATE 4 | 内容校验（FM完整性、正文长度） | 回滚 |

**应用于**：
- `save` 工具：GATE 2（文件名过滤）
- `ll_finish_with_brain.py`：GATE 4（验证门控）
- 原料预处理：GATE 1（类型检查）

### 2. 敏感操作确认

以下操作不可撤销，必须用户明确指定目标后再执行：

| 操作 | 确认要求 |
|------|---------|
| `append_doc`（追加到已有笔记） | 必须指定目标笔记，不确定时先问 |
| 补角（修改已有丹房页） | 必须指定目标页 |
| 删除文件 | 必须确认 |
| Git提交 | 必须用户请求 |

**原则**：不确定时，先问。宁可多问一句，也不要误改用户已有内容。

### 3. 隐藏内部ID

MCP工具返回值和用户展示中，永远不暴露内部标识：

| 不展示 | 展示为 |
|--------|--------|
| `丹房/00-思考与认知/含人量.md` | 含人量 |
| `index.json` 中的路径 | 页面标题 |
| `note_id` / `media_id` | 笔记/文件标题 |

**原因**：内部ID会随重构变化，用户不应依赖。灵识MCP工具返回值应始终包含 `title` 字段。

### 4. 灵台 API

灵台提供两种API访问方式：

**MCP协议（推荐）**：
- 22个工具，通过 stdin/stdout 通信
- 配置：`~/.workbuddy/mcp.json`

**Python直调**：
```python
from memory_engine import MemoryEngine
from perception import PerceptionTools
from kar_fusion import KARFusion
```

**Obsidian CLI封装**：
```python
from obsidian_cli import ObsidianCLI
# 读写FM、搜索、查入链等
```

**Defuddle封装**：
```python
from web_extractor import WebExtractor
# 网页内容提取为原料
```
