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
| `daily-news` | Aggregate daily news from multiple sources (RSS / HN / Reddit / Twitter), dedupe, score, and push a report. |
| `download-audio` | Download audio from video sources (e.g. Bilibili) via a shell script. |
| `elementary-math` | Design first-principles, visual elementary mathematics lessons and print-quality Chinese PDF worksheets. |
| `obsidian` | Write and edit Obsidian markdown notes for technical / research topics. |
| `stock-emotion` | Analyze stock market sentiment with a Python script. |

Invoke a skill from your agent with `/obsidian` (or let the agent auto-trigger it based on the `description`).

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
