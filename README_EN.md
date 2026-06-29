# LingTai (零台) — AI Content Production System for Solopreneurs

> **Raw notes → Structured knowledge. 29 MCP tools, MIT open source, zero API dependencies.**
> 
> _One human + AI production system. Not a chatbot — your knowledge assembly line._

[Gitee Main Repo](https://gitee.com/erdong-risheng/lingtai) | [GitHub Mirror](https://github.com/erdong-risheng/lingtai) | MIT License

***

## The Story Behind the Name

**零台** comes from Zhuangzi:

> *"工倕旋而盖规矩，指与物化而不以心稽，故其灵台一而不桎."*
> — Zhuangzi, *Dasheng*

The craftsman drew circles truer than a compass — not because of skill, but because **his hand and the object became one, his mind unblocked, his spirit focused without constraint.**

"LingTai" first appeared as a Daoist concept. Guo Xiang's commentary says it best: **"LingTai is the heart-mind."** It is the dwelling place of the spirit, the source of clear insight.

> _A clear mind lets the hand become one with the work. A mirror that does not lie. A production system that does not deceive itself._

***

## Architecture

`
                          ┌──────────────────────────────┐
                          │    Obsidian (Knowledge UI)    │
┌─────────────────────────┴──────────────────────────────┘
│  LingShi (灵识) — Cognitive Engine
│  ├── 29 MCP Tools (knowledge retrieval, graph, memory)
│  ├── Observation Engine + Hebbian Weights
│  └── User Profile Learning
│
│  LingTai (灵台) — Knowledge Pipeline
│  ├── Raw Material -> Distillation -> DanFang (Wiki)
│  ├── Grade Assessment -> Health Check
│  └── 166+ pages, 12 domains
│
│  SkillOpt — Self-Evolution Engine
│  ├── Test-case gated improvement
│  └── Refinement workflow optimization
└────────────────────────────────────────────────────────
`

***

## Key Capabilities

- **29 MCP tools**: knowledge retrieval, graph analysis, observation learning, perception reasoning, model routing
- **6 automated tasks**: Daily Briefing, Inspection, Introspection, Weekly Review, Monthly Query, Auto Distillation
- **3-tier quality grading**: Top (上品) / Mid (中品) / Raw (下品)
- **Self-evolving rulebook**: SkillOpt methodology — change with test-case validation
- **Pluggable MCP**: delete .tool/lingshi/ and core pipeline still works
- **Zero external API dependency**: all tools work offline with local knowledge base

***

## Quick Start

### 1. Get the repo

`ash
git clone https://github.com/edrc-shawn/lingtai.git
cd lingtai
`

### 2. Init

`ash
# macOS / Linux
python3 scripts/lingtai.py init

# Windows
python scripts/lingtai.py init
`

### 3. Drop notes and call AI

Put markdown files into **原料/** (raw materials). Then tell your AI assistant:

> refine

The AI reads the rules, refines your notes into structured wiki pages in **丹房/**.

### 4. Enable MCP (optional)

Add the MCP server to your AI client config:

`json
{
  "mcpServers": {
    "lingtai-kb": {
      "command": "python3",
      "args": [".tool/lingshi/mcp_server.py"],
      "env": {
        "LINGTAI_VAULT": "/path/to/lingtai"
      }
    }
  }
}
`

***

## Why Open Source?

> _"Open source the skeleton to set the standard. Keep the flesh as a moat."_

LingTai is fully open (MIT) because sharing the paradigm matters more than hiding the code. What stays private: personal notes, user profiles, API credentials, and operational history from the author's own pipeline — your 365 days of data is your real moat.

***

Built by [耳东日成](https://gitee.com/erdong-risheng)

_One human CEO + one AI army. Daily production since 2025._
