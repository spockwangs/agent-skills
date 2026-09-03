# agent-skills

A shared collection of agent **skills** that work across [Claude Code](https://code.claude.com/docs/en/skills), [Cursor](https://cursor.com/docs/skills), [CodeBuddy](https://www.codebuddy.ai/docs/cli/skills), [Codex](https://developers.openai.com/codex/skills), and [WorkBuddy](https://www.workbuddy.ai/docs/cli/skills).

## Why this layout

All five tools share the **same skill format** — a directory containing a `SKILL.md` file with YAML frontmatter (`name`, `description`) plus optional `scripts/`, `references/`, and `assets/` folders. The only thing that differs is *which directory* each tool scans:

| Tool          | Project discovery path     |
| ------------- | -------------------------- |
| Claude Code   | `.claude/skills/`          |
| Cursor        | `.cursor/skills/` *(also auto-loads `.claude/skills/` and `.agents/skills/`)* |
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
├── .agents/skills      -> ../skills   # Codex (and Cursor compat)
├── .workbuddy/skills   -> ../skills   # WorkBuddy
└── README.md
```

Cursor reads skills from `.claude/skills/` and `.agents/skills/` automatically, so it is covered by the symlinks above. If you want an explicit `.cursor/skills/` entry too, add it with:

```bash
mkdir -p .cursor && ln -s ../skills .cursor/skills
```

## Skills

| Skill      | Description |
| ---------- | ----------- |
| `analysis` | Requirements-analysis stage: sharpen a vague requirement into a shared spec (problem statement / requirements analysis / user stories) through relentless interviewing, while producing a domain model: `CONTEXT.md` glossary and ADRs. Stops at the spec — solution design is the next stage. |
| `code-review` | Two-axis review of the diff between HEAD and a fixed point you name (commit / branch / tag / merge-base). Standards: does the code follow this repo's documented coding standards (plus a built-in Fowler smell baseline)? Spec: does it faithfully implement the originating issue / spec? Each axis runs in its own parallel sub-agent; the two reports are presented side by side, never merged or re-ranked. Read-only; does not fix anything. |
| `daily-news` | Aggregate daily news from multiple sources (RSS / HN / Reddit / Twitter), dedupe, score, and push a report. |
| `design` | Solution-design stage: takes the analysis spec, spawns 3 parallel sub-agents (minimal change / cleanest architecture / pragmatic middle ground), compares them for the user to choose, then emits a domain-terminology design plus test plan as the basis for implementation. |
| `download-audio` | Download audio from video sources (e.g. Bilibili) via a shell script. |
| `implement` | Implementation stage: takes the design (design + test plan), or a spec, or the plan just agreed in the conversation, and writes code + tests via a TDD red-green loop at pre-agreed seams, typechecking as it goes, running the full suite once at the end, then self-reviewing and committing to the current branch. Trusts the upstream, does not reopen the design; stops at the commit. |
| `elementary-math` | Design first-principles, visual elementary mathematics lessons and print-quality Chinese PDF worksheets. |
| `obsidian` | Write and edit Obsidian markdown notes for technical / research topics. |

Invoke a skill from your agent with `/obsidian` (or let the agent auto-trigger it based on the `description`).

### 需求流水线：`analysis` → `design`

`analysis` 与 `design` 是一对串联技能，覆盖「从模糊需求到可实现 spec」的全过程：

| 阶段 | 技能 | 输入 | 产出 |
| --- | --- | --- | --- |
| 需求分析 | `analysis` | 模糊的需求 | spec：问题陈述 / 需求分析 / 用户故事；另产出 `CONTEXT.md` 领域模型与 ADR |
| 方案设计 | `design` | 分析阶段的 spec | 设计方案（领域与物理模型 Schema、模块变更、交互时序、接口契约）+ 测试方案（测试范围、测试用例、需 mock 的 seam） |
| 实现 | `implement` | 设计方案 + 测试方案（或 spec / 当前上下文中已达成的共识） | 提交到当前分支的、通过测试的代码 |

三个技能都有明确边界：`analysis` 只回答「解决什么问题、为什么解决、范围多大」，`design` 才回答「怎么实现」，`implement` 把设计落成代码——**三者都不越界**。`analysis` 不写方案，`design` 不写代码，`implement` 不重开设计。若没有 spec 就直接跑 `/design`，它会先建议你跑 `/analysis`；若只有 spec 没有设计，`/implement` 会先和你确认 seam 再开始。

`code-review` 是这条链尾部的审查步骤，也可独立指向任意分支 / PR：`analysis → design → implement → code-review`。`implement` 的收尾自审参考它的两轴划分，但真正诚实的版本是从**新会话**里单独跑 `/code-review`——写代码的同一会话审查自己，是带着塑造代码的全部假设在审查。

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
# default: symlink, user scope (~/.claude, ~/.cursor, ~/.codebuddy, ~/.agents, ~/.workbuddy), all agents
./install.sh

# project scope: writes ./.claude/skills, ./.cursor/skills, ... (commit to share)
./install.sh --scope project

# pick agents
./install.sh --agents claude,codex

# copy instead of symlink (for filesystems without symlink support)
./install.sh --copy --scope project

# remove what the script installed
./install.sh --uninstall
```

Run `./install.sh --help` for the full reference. Each skill is installed per-skill (e.g. `~/.claude/skills/obsidian -> <repo>/skills/obsidian`), so it coexists with any other skills you already have in those directories.

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
