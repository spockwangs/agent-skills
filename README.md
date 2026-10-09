# agent-skills

A shared collection of agent **skills** that work across [Claude Code](https://code.claude.com/docs/en/skills), [Cursor](https://cursor.com/docs/skills), [CodeBuddy](https://www.codebuddy.ai/docs/cli/skills), [Codex](https://developers.openai.com/codex/skills), and [WorkBuddy](https://www.workbuddy.ai/docs/cli/skills).

## Why this layout

All five tools share the **same skill format** — a directory containing a `SKILL.md` file with YAML frontmatter (`name`, `description`) plus optional `scripts/`, `references/`, and `assets/` folders. The only thing that differs is *which directory* each tool scans:

| Tool          | Project discovery path     |
| ------------- | -------------------------- |
| Claude Code   | `.claude/skills/`          |
| Cursor        | `.agents/skills/` *(shared with Codex; also auto-loads `.claude/skills/`)* |
| CodeBuddy     | `.codebuddy/skills/`       |
| Codex         | `.agents/skills/`          |
| WorkBuddy     | `.workbuddy/skills/`       |

Instead of duplicating skills into five places, this repo keeps a single canonical source and exposes it to every tool via symlinks:

```
agent-skills/
├── skills/                 # canonical source of truth (universal SKILL.md format)
│   └── obsidian/
│       └── SKILL.md
├── .claude/skills      -> ../skills   # Claude Code
├── .codebuddy/skills   -> ../skills   # CodeBuddy
├── .agents/skills      -> ../skills   # Codex + Cursor
├── .workbuddy/skills   -> ../skills   # WorkBuddy
└── README.md
```

Cursor auto-loads `.agents/skills/` (and `.claude/skills/`), so it is covered by the symlinks above — no separate `.cursor/skills/` entry is needed.

## Skills

| Skill      | Description |
| ---------- | ----------- |
| `analysis` | Requirements-analysis stage: sharpen a vague requirement into a shared spec (problem statement / requirements analysis / user stories) through relentless interviewing, while producing a domain model: `CONTEXT.md` glossary and ADRs. Stops at the spec — solution design is the next stage. |
| `code-review` | Two-axis review of the diff between HEAD and a fixed point you name (commit / branch / tag / merge-base). Standards: does the code follow this repo's documented coding standards (plus a built-in Fowler smell baseline)? Spec: does it faithfully implement the originating issue / spec? Each axis runs in its own parallel sub-agent; the two reports are presented side by side, never merged or re-ranked. Read-only; does not fix anything. |
| `daily-news` | Aggregate daily news from multiple sources (RSS / HN / Reddit / Twitter), dedupe, score, and push a report. |
| `design` | Solution-design stage: reads propose's settled understanding, `.agents/GLOSSARY.md`, and `.agents/adr/`, then writes one design plus a test plan in that vocabulary. |
| `download-audio` | Download audio from video sources (e.g. Bilibili) via a shell script. |
| `implement` | Builds the current spec, issue, or conversation with test-driven development and commits it on the current branch. Then a code-reviewer subagent runs `code-review`, and an implementer subagent fixes the findings. Does not reopen the design. |
| `elementary-math` | Design first-principles, visual elementary mathematics lessons and print-quality Chinese PDF worksheets. |
| `grill` | Interview primitive: grill a plan, decision, or idea in rounds until nothing is silently assumed. Model-invoked, so other skills call it. |
| `propose` | User-invoked interview that calls `grill`, and writes resolved terms to `.agents/GLOSSARY.md` and hard decisions to `.agents/adr/` as they crystallise. |
| `elementary-math-quiz` | Generate a printable primary-school math quiz for a specified knowledge point (trigger: 出试卷). |
| `obsidian` | Write and edit Obsidian markdown notes for technical / research topics. |
| `research` | Delegate noisy investigation (many files, long logs, large diffs, wide surveys) to one or more local sub-agents so the orchestrator's context stays clean; work from a distilled answer plus evidence traced to primary sources (chase secondary write-ups to the source that owns the fact). Use before reading a pile of files inline. Open-web multi-source research is `deep-search`. |
| `triage-issue` | Diagnose one issue from a link or number: whether it is a real problem, where it is stuck, and the next step. Verdicts are needs-triage, needs-info, ready, denied, or resolved. Shows the conclusion and waits for confirmation before commenting, relabeling, or closing. |

Invoke a skill from your agent with `/obsidian` (or let the agent auto-trigger it based on the `description`).

### 需求流水线：`propose` → `design` → `implement`

`propose` 把计划访谈到共识，并把术语和关键决策写进 `.agents/`。`design` 只消费这份已经定下来的理解，写出**一份**设计。`implement` 把设计落成代码。

| 阶段 | 技能 | 输入 | 产出 |
| --- | --- | --- | --- |
| 提案 | `propose` | 模糊的计划 | 共识；`.agents/GLOSSARY.md` 与 `.agents/adr/` |
| 方案设计 | `design` | propose 的共识、术语表、ADR | 一份设计方案（领域与物理模型、模块变更、交互时序、接口契约）+ 测试方案 |
| 实现 | `implement` | 当前 spec、issue，或对话里已经定下来的内容 | 当前分支上的提交。写完后由 code-reviewer 子 Agent 跑 `code-review`，再由 implementer 子 Agent 修审查指出的问题 |

三个技能都有明确边界：`propose` 负责把问题和术语问清楚，`design` 写出怎么实现的那一份方案，`implement` 把已经定下来的内容落成代码。`design` 不重新访谈，也不并列多份方案。没有 propose 的产出就跑 `/design` 时，它会先建议跑 `/propose`。

`implement` 在提交后自己拉起一次 `code-review`：审查交给一个不写代码的子 Agent，修复交给另一个子 Agent，只走一轮。`code-review` 也可以单独指向任意分支 / PR。

## Adding a skill

1. Create `skills/<my-skill>/SKILL.md`.
2. Add YAML frontmatter — `name` must match the directory name (lowercase, numbers, hyphens):

   ```markdown
   ---
   name: my-skill
   description: What this skill does and when the agent should use it.
   ---

   # Instructions
   Step-by-step guidance for the agent.
   ```

3. Optionally add `scripts/`, `references/`, and `assets/` next to `SKILL.md`.
4. Keep `SKILL.md` under ~500 lines; move deep material into `references/`.

Because every tool points at the same `skills/` folder, the new skill is immediately available to Claude Code, Cursor, CodeBuddy, Codex, and WorkBuddy — no per-tool copying.

## Installing skills into your agents

Use the bundled `install.sh` to link (or copy) every skill under `skills/` into each agent's expected directory. It is idempotent, backs up anything it didn't create, and refuses to touch the source tree.

```bash
# default: symlink, user scope (skills + AGENTS.md), all agents
./install.sh

# project scope: writes ./.claude/skills, ./.codebuddy/skills, ./.agents/skills, ./.workbuddy/skills (commit to share)
./install.sh --scope project

# pick agents
./install.sh --agents claude,codex

# copy instead of symlink (for filesystems without symlink support)
./install.sh --copy --scope project

# remove what the script installed
./install.sh --uninstall
```

Run `./install.sh --help` for the full reference. Each skill is installed per-skill (e.g. `~/.claude/skills/obsidian -> <repo>/skills/obsidian`); Codex and Cursor share `~/.agents/skills`, so it coexists with any other skills you already have in those directories.

**Windows note:** symlinks may need Developer Mode enabled; otherwise use `--copy`.

## Installing AGENTS.md (agent memory / instructions)

`install.sh` also propagates the repo's `AGENTS.md` to each tool's instructions file, so all five agents share one source of truth. Use `--no-skills` / `--no-agents-md` to opt out of either part.

| Tool | Project scope | User scope |
| --- | --- | --- |
| Claude Code | `./CLAUDE.md` bridge → `AGENTS.md` (Claude reads CLAUDE.md, not AGENTS.md) | `~/.claude/CLAUDE.md` |
| Cursor | reads `./AGENTS.md` natively (nothing to do) | `~/.cursor/rules/agents.mdc` (wrapped with frontmatter) |
| CodeBuddy | reads `./AGENTS.md` natively (fallback to `CODEBUDDY.md`) | `~/.codebuddy/CODEBUDDY.md` |
| Codex | reads `./AGENTS.md` natively | `~/.codex/AGENTS.md` (note: `~/.codex`, not `~/.agents`) |
| WorkBuddy | reads `./AGENTS.md` natively | `~/.workbuddy/SOUL.md` |

```bash
./install.sh --no-skills                 # user scope: global memory for all agents
./install.sh --no-skills --scope project # project scope: just the CLAUDE.md bridge
./install.sh --no-skills --copy          # copy content instead of symlinking
./install.sh --uninstall --no-skills     # remove installed memory files
```

Notes:
- **Project scope** only creates the `CLAUDE.md` bridge for Claude Code; Cursor, CodeBuddy, Codex, and WorkBuddy already read `./AGENTS.md` natively.
- **User scope** replaces each tool's *global* memory file — existing files are backed up to `<name>.bak.<timestamp>` (the installer warns before replacing). Cursor's global rules need a `.mdc` wrapper (frontmatter is required), so that file is always generated rather than symlinked, even in symlink mode.
- In `--copy` mode, Claude Code's project bridge uses an `@AGENTS.md` import (single source of truth); user-scope copies embed the content directly (with a marker comment so the installer can recognize its own files).

## Using this repo in your projects

**Option A — clone and run the installer (recommended).**

```bash
git clone <this-repo> ~/agent-skills
cd ~/agent-skills
./install.sh                 # user scope, all agents, skills + AGENTS.md
# or: ./install.sh --scope project   # from within a project to vendor into it
```

**Option B — vendor the repo.** Copy or subtree-merge it into your project, then run `./install.sh --scope project` (and commit the resulting links/bridges). On filesystems without symlink support, use `./install.sh --copy --scope project`.

## Notes

- Symlinks are committed to git and preserved on macOS/Linux.
- The directory name **must** match the `name` field in `SKILL.md` for Claude Code, Cursor, and Codex; CodeBuddy falls back to the directory name when `name` is omitted.
