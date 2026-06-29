# Lingtai (零台)

> Turn scattered notes into a searchable, self-growing knowledge base.
> You just drop notes in — AI organizes, connects, and finds the gaps.

---

## What is Lingtai?

Lingtai is an **open-source, AI-powered knowledge management system** built on top of an Obsidian vault. It turns raw notes (clippings, thoughts, articles) into a structured wiki with cross-references, quality grading, and automated maintenance.

The core philosophy: **AI prepares the ammo, you pull the trigger.**

---

## Quick Start (3 steps)

### 1. Get the repo

`ash
git clone https://github.com/edrc-shawn/lingtai.git
cd lingtai
`

### 2. Init

`ash
python3 scripts/lingtai.py init
`

> On Windows, use \python\ instead of \python3\.

### 3. Drop notes + call AI

**Drop notes**: Put your markdown files into the \原料/\ folder.

**Call AI**: Open your AI assistant with this repo as the working directory, then say:

> refine

The AI will read the rules and start refining your notes into structured knowledge pages in \丹房/\.

---

## Lingtai MCP (optional but powerful)

Lingtai includes a built-in Model Context Protocol (MCP) server — **29 tools** for knowledge retrieval, graph analysis, observation learning, and more.

**Setup**: Configure your AI client to run:

`ash
python3 .tool/lingshi/mcp_server.py
`

With the environment variable:

`ash
export LINGTAI_VAULT=/path/to/lingtai
`

---

## Directory Structure

`
lingtai/
├── CLAUDE.md          ← Rulebook (single source of truth)
├── AGENTS.md          ← AI entry point
├── 索引.md            ← Full knowledge index
├── 原料/              ← Raw materials (notes, clippings, articles)
├── 丹房/              ← Refined wiki pages (auto-generated)
├── 体检/              ← Health check reports
├── 入门/              ← User guide + profile
├── 巡更/              ← Automation workflows
├── 输出/              ← Output skills (writing, publishing)
├── scripts/           ← Helper scripts
└── .tool/lingshi/     ← Lingtai MCP (29 tools)
`

---

## Requirements

| Dependency | Required? | Notes |
|---|---|---|
| Python 3.10+ | ✅ | For init script and health checks |
| AI assistant | ✅ | Lingtai itself has no built-in AI |
| Obsidian | 🔶 Recommended | Not required, but great for visualization |
| Git | ❌ | You can download the ZIP instead |

**Recommended AI assistants**: Claude, WorkBuddy, ChatGPT — any of them work.

---

## macOS Support

Set the environment variable and use \python3\:

`ash
export LINGTAI_VAULT=/path/to/lingtai
python3 scripts/lingtai.py init
`

See \AGENTS.md\ for full AI startup protocol.

---

## License

MIT — free to use, modify, and distribute.
