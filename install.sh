#!/usr/bin/env bash
# install.sh — install this repo's skills AND AGENTS.md into AI coding agents.
#
# Supported agents: claude (Claude Code), cursor (Cursor),
#                   codebuddy (Tencent CodeBuddy), codex (OpenAI Codex),
#                   workbuddy (WorkBuddy).
#
# What it installs:
#   1. Skills:  each ./skills/<name>/  ->  <agent>/skills/<name>   (universal SKILL.md format)
#   2. AGENTS.md: the repo's ./AGENTS.md propagated to each tool's memory file:
#      - project scope: only Claude Code needs a bridge (CLAUDE.md -> AGENTS.md);
#        Cursor / CodeBuddy / Codex / WorkBuddy read AGENTS.md natively.
#      - user scope: ~/.claude/CLAUDE.md, ~/.cursor/rules/agents.mdc,
#        ~/.codebuddy/CODEBUDDY.md, ~/.codex/AGENTS.md, ~/.workbuddy/SOUL.md
#
# Usage:
#   ./install.sh                         # symlink, user scope, all agents, skills + AGENTS.md
#   ./install.sh --project               # install into ./<agent>/... (commit to share)
#   ./install.sh --agents claude,codex   # pick agents
#   ./install.sh --copy                  # copy files instead of symlinking
#   ./install.sh --no-skills             # only install AGENTS.md
#   ./install.sh --no-agents-md          # only install skills
#   ./install.sh --uninstall             # remove what this script installed
#   ./install.sh --help
#
set -eu

# --- Config ------------------------------------------------------------------
# agent id -> skills dir name. Codex skills live under .agents.
agent_dir() {
  case "$1" in
    claude)    printf '.claude' ;;
    cursor)    printf '.cursor' ;;
    codebuddy) printf '.codebuddy' ;;
    codex)     printf '.agents' ;;
    workbuddy) printf '.workbuddy' ;;
    *)         return 1 ;;
  esac
}
is_valid_agent() { agent_dir "$1" >/dev/null 2>&1; }
ALL_AGENTS="claude cursor codebuddy codex workbuddy"

# --- Defaults ----------------------------------------------------------------
SCOPE="user"            # user | project
AGENTS=""               # space-separated list
MODE="symlink"          # symlink | copy
ACTION="install"        # install | uninstall
DO_SKILLS=1
DO_AGENTS_MD=1
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_ROOT/skills"
AGENTS_MD="$REPO_ROOT/AGENTS.md"
MARKER='<!-- installed by agent-skills/install.sh -->'
HAD_FAILURE=0

# --- Helpers -----------------------------------------------------------------
if [[ -t 1 ]]; then
  c_reset='\033[0m'; c_dim='\033[2m'; c_green='\033[1;32m'
  c_yellow='\033[1;33m'; c_red='\033[1;31m'; c_blue='\033[1;34m'
else
  c_reset=''; c_dim=''; c_green=''; c_yellow=''; c_red=''; c_blue=''
fi
log()  { printf "${c_blue}•${c_reset} %s\n" "$*"; }
ok()   { printf "${c_green}✓${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}!${c_reset} %s\n" "$*" >&2; }
err()  { printf "${c_red}✗${c_reset} %s\n" "$*" >&2; }
die()  { err "$*"; exit 1; }

# Resolve a path to a physical (symlink-free) absolute path. Works even if the
# final component does not yet exist, by resolving its parent.
resolve_path() {
  local p="$1" parent dir rparent
  if [[ -d "$p" ]]; then (cd "$p" && pwd -P); return; fi
  parent="$(dirname "$p")"; dir="$(basename "$p")"
  if rparent="$(cd "$parent" 2>/dev/null && pwd -P)"; then
    printf '%s/%s' "$rparent" "$dir"
  else
    printf '%s' "$p"
  fi
}

# --- Skills helpers ----------------------------------------------------------
target_skills_root() {
  local dir; dir="$(agent_dir "$1")" || die "unknown agent: $1"
  case "$SCOPE" in
    user)    printf '%s/%s/skills' "$HOME" "$dir" ;;
    project) printf '%s/%s/skills' "$REPO_ROOT" "$dir" ;;
  esac
}
src_skill_path() { printf '%s/%s' "$SRC_DIR" "$1"; }

list_skills() {
  [[ -d "$SRC_DIR" ]] || return 0
  local d
  for d in "$SRC_DIR"/*/; do
    [[ -f "${d}SKILL.md" ]] || continue
    basename "$d"
  done
}

maybe_backup_skill() {
  local path="$1" src="$2"
  [[ -e "$path" || -L "$path" ]] || return 0
  if [[ -L "$path" ]]; then
    local tgt; tgt="$(readlink "$path")"
    [[ "$tgt" == "$src" ]] && return 0
  fi
  local bak="${path}.bak.$(date +%s)"
  warn "target exists and is not ours, backing up: $path -> $bak"
  mv "$path" "$bak"
}

install_skill_one() {
  local target_root="$1" skill="$2"
  local src; src="$(src_skill_path "$skill")"
  local dest="$target_root/$skill"
  if [[ "$MODE" == "symlink" && -L "$dest" ]] &&
     [[ "$(resolve_path "$dest")" == "$(resolve_path "$src")" ]]; then
    printf "${c_dim}  - skip    %s (already linked to this repo)${c_reset}\n" "$dest"
    return 0
  fi
  mkdir -p "$target_root" || return 1
  maybe_backup_skill "$dest" "$src"
  if [[ "$MODE" == "copy" ]]; then
    rm -rf "$dest"
    cp -R "$src" "$dest" || return 1
    ok "skill copied  $skill -> $dest"
  else
    ln -sfn "$src" "$dest" || return 1
    ok "skill linked  $skill -> $dest"
  fi
}

uninstall_skill_one() {
  local target_root="$1" skill="$2"
  local dest="$target_root/$skill"
  local src; src="$(src_skill_path "$skill")"
  if [[ ! -e "$dest" && ! -L "$dest" ]]; then
    printf "${c_dim}  - skip    %s (not present)${c_reset}\n" "$dest"
    return 0
  fi
  if [[ -L "$dest" ]]; then
    local tgt; tgt="$(readlink "$dest")"
    [[ "$tgt" == "$src" ]] || { warn "not ours, leaving: $dest"; return 0; }
    rm -f "$dest" || return 1
    ok "skill removed  $skill from $target_root"
  else
    if cmp -s "$dest/SKILL.md" "$src/SKILL.md" 2>/dev/null; then
      rm -rf "$dest" || return 1
      ok "skill removed  $skill from $target_root"
    else
      warn "SKILL.md differs from source, leaving: $dest"
    fi
  fi
}

run_skills_for_agent() {
  local agent="$1"
  local target_root; target_root="$(target_skills_root "$agent")"
  log "skills: agent=$agent target=$target_root mode=$MODE"

  # Safety: never write into our own source tree (happens when the target skills
  # dir is already a whole-dir symlink to ../skills).
  local real_target real_src
  real_target="$(resolve_path "$target_root")"
  real_src="$(resolve_path "$SRC_DIR")"
  if [[ "$real_target" == "$real_src" || "$real_target" == "$real_src"/* ]]; then
    log "  skills: target resolves to the source tree; skills already exposed here, skipping."
    return 0
  fi

  local skills; skills="$(list_skills)"
  [[ -n "$skills" ]] || { warn "no skills found under $SRC_DIR"; return 0; }

  local skill rc=0
  for skill in $skills; do
    if [[ "$ACTION" == "uninstall" ]]; then
      uninstall_skill_one "$target_root" "$skill" || rc=1
    else
      install_skill_one "$target_root" "$skill" || rc=1
    fi
  done
  return $rc
}

# --- AGENTS.md helpers -------------------------------------------------------
# Method to install AGENTS.md for (agent, scope, mode). "skip" = tool reads
# AGENTS.md natively, nothing to do.
agents_md_method() {
  local agent="$1"
  case "$SCOPE" in
    project)
      case "$agent" in
        claude) [[ "$MODE" == "symlink" ]] && echo symlink || echo import ;;
        cursor|codebuddy|codex|workbuddy) echo skip ;;
      esac ;;
    user)
      case "$agent" in
        claude)    [[ "$MODE" == "symlink" ]] && echo symlink || echo copy ;;
        cursor)    echo mdc ;;                       # .mdc needs frontmatter, never a symlink
        codebuddy) [[ "$MODE" == "symlink" ]] && echo symlink || echo copy ;;
        codex)     [[ "$MODE" == "symlink" ]] && echo symlink || echo copy ;;
        workbuddy) [[ "$MODE" == "symlink" ]] && echo symlink || echo copy ;;
      esac ;;
  esac
}

# Target file path for AGENTS.md install (empty when method=skip).
agents_md_target() {
  local agent="$1"
  case "$SCOPE" in
    project)
      case "$agent" in
        claude) echo "$REPO_ROOT/CLAUDE.md" ;;
        *)      echo "" ;;
      esac ;;
    user)
      case "$agent" in
        claude)    echo "$HOME/.claude/CLAUDE.md" ;;
        cursor)    echo "$HOME/.cursor/rules/agents.mdc" ;;
        codebuddy) echo "$HOME/.codebuddy/CODEBUDDY.md" ;;
        codex)     echo "$HOME/.codex/AGENTS.md" ;;
        workbuddy) echo "$HOME/.workbuddy/SOUL.md" ;;
      esac ;;
  esac
}

# Is an existing target file one we previously installed?
is_ours_md() {
  local target="$1" source="$2"
  if [[ -L "$target" ]]; then
    local tgt resolved_tgt
    tgt="$(readlink "$target")"
    [[ "$tgt" == "$source" ]] && return 0
    # Accept equivalent paths (relative vs absolute symlink targets).
    if [[ "$tgt" == /* ]]; then
      resolved_tgt="$(resolve_path "$tgt")"
    else
      resolved_tgt="$(resolve_path "$(dirname "$target")/$tgt")"
    fi
    [[ "$resolved_tgt" == "$(resolve_path "$source")" ]] && return 0
  fi
  [[ -f "$target" ]] && grep -qF "$MARKER" "$target" 2>/dev/null && return 0
  return 1
}

backup_if_needed_md() {
  local target="$1" source="$2"
  [[ -e "$target" || -L "$target" ]] || return 0
  if is_ours_md "$target" "$source"; then return 0; fi
  local bak="${target}.bak.$(date +%s)"
  warn "agents.md: target exists and is not ours, backing up: $target -> $bak"
  mv "$target" "$bak"
}

install_agents_md_one() {
  local agent="$1" method="$2" target="$3"
  local src="$AGENTS_MD"
  # Safety: never overwrite the source file itself.
  local rt rs
  rt="$(resolve_path "$target")"; rs="$(resolve_path "$src")"
  if [[ "$rt" == "$rs" ]]; then
    log "  agents.md: target is the source file, skipping."
    return 0
  fi
  # Already a symlink pointing at this repo — leave it alone.
  if [[ "$method" == "symlink" && -L "$target" ]] && is_ours_md "$target" "$src"; then
    printf "${c_dim}  - skip    %s (already linked to this repo)${c_reset}\n" "$target"
    return 0
  fi
  mkdir -p "$(dirname "$target")" || return 1
  backup_if_needed_md "$target" "$src"
  # Remove any pre-existing target (incl. our own symlink to the source) before
  # writing, so a copy/import never writes *through* a symlink into the source.
  rm -f "$target"
  case "$method" in
    symlink)
      ln -sfn "$src" "$target" || return 1
      ok "agents.md linked  $target -> $src" ;;
    import)
      printf '%s\n\n@AGENTS.md\n' "$MARKER" > "$target" || return 1
      ok "agents.md bridge  $target (@AGENTS.md import)" ;;
    copy)
      { printf '%s\n\n' "$MARKER"; cat "$src"; } > "$target" || return 1
      ok "agents.md copied  $target" ;;
    mdc)
      {
        printf -- '---\ndescription: Project-wide agent guidelines installed from agent-skills\nalwaysApply: true\n---\n'
        printf '%s\n\n' "$MARKER"
        cat "$src"
      } > "$target" || return 1
      ok "agents.md cursor-rule  $target" ;;
  esac
}

uninstall_agents_md_one() {
  local agent="$1" target="$2"
  if [[ -z "$target" ]]; then
    log "  agents.md: $agent reads AGENTS.md natively, nothing to uninstall."
    return 0
  fi
  if [[ ! -e "$target" && ! -L "$target" ]]; then
    printf "${c_dim}  - skip    %s (not present)${c_reset}\n" "$target"
    return 0
  fi
  if is_ours_md "$target" "$AGENTS_MD"; then
    rm -f "$target" || return 1
    ok "agents.md removed  $target"
  else
    warn "agents.md: not ours, leaving: $target"
  fi
}

run_agents_md_for_agent() {
  local agent="$1"
  [[ -f "$AGENTS_MD" ]] || { warn "agents.md: $AGENTS_MD not found, skipping"; return 0; }
  local method target
  method="$(agents_md_method "$agent")"
  target="$(agents_md_target "$agent")"
  if [[ -z "$target" || "$method" == "skip" ]]; then
    log "  agents.md: $agent reads AGENTS.md natively here, nothing to do."
    return 0
  fi
  if [[ "$SCOPE" == "user" && "$ACTION" == "install" ]] &&
     { [[ -e "$target" ]] || [[ -L "$target" ]]; } &&
     ! is_ours_md "$target" "$AGENTS_MD"; then
    warn "agents.md: $ACTION will replace global memory file $target (existing backed up)"
  fi
  if [[ "$ACTION" == "uninstall" ]]; then
    uninstall_agents_md_one "$agent" "$target"
  else
    install_agents_md_one "$agent" "$method" "$target"
  fi
}

# --- Per-agent driver --------------------------------------------------------
run_for_agent() {
  local agent="$1" rc=0
  is_valid_agent "$agent" || die "unknown agent: $agent"
  log "agent=$agent scope=$SCOPE"
  if [[ "$DO_SKILLS" -eq 1 ]]; then
    run_skills_for_agent "$agent" || rc=1
  fi
  if [[ "$DO_AGENTS_MD" -eq 1 ]]; then
    run_agents_md_for_agent "$agent" || rc=1
  fi
  if [[ $rc -ne 0 ]]; then
    warn "some operations failed for agent=$agent"
    HAD_FAILURE=1
  fi
}

# --- Arg parsing -------------------------------------------------------------
usage() {
  cat <<'EOF'
install.sh — install this repo's skills AND AGENTS.md into AI coding agents.

Usage: install.sh [options]

Options:
  --scope user|project   Where to install (default: user).
                         user    -> ~/<agent-dir>/skills/ + global memory files
                         project -> ./.<agent-dir>/skills/ + ./CLAUDE.md bridge
  --agents LIST          Comma-separated subset of: claude,cursor,codebuddy,codex,workbuddy
                         (default: all five)
  --copy                 Copy files instead of symlinking (for FS without symlink
                         support, e.g. some Windows setups).
  --no-skills            Do not install skills (AGENTS.md only).
  --no-agents-md         Do not install AGENTS.md (skills only).
  --uninstall            Remove what this script previously installed.
  --help, -h             Show this help.

Agents map to these skills / memory locations:
  claude     .claude/skills   |  CLAUDE.md (project) / ~/.claude/CLAUDE.md
  cursor     .cursor/skills   |  AGENTS.md (project, native) / ~/.cursor/rules/agents.mdc
  codebuddy  .codebuddy/skills|  AGENTS.md (project, native) / ~/.codebuddy/CODEBUDDY.md
  codex      .agents/skills   |  AGENTS.md (project, native) / ~/.codex/AGENTS.md
  workbuddy  .workbuddy/skills|  AGENTS.md (project, native) / ~/.workbuddy/SOUL.md

Notes:
  - Project-scope AGENTS.md: only Claude Code needs a bridge (CLAUDE.md -> AGENTS.md);
    Cursor, CodeBuddy, Codex, and WorkBuddy read ./AGENTS.md natively.
  - User-scope AGENTS.md replaces each tool's global memory file (existing files
    are backed up to <name>.bak.<timestamp>).

Examples:
  install.sh                                  # user scope, all agents, skills + AGENTS.md
  install.sh --project                        # vendor into current repo (commit to share)
  install.sh --project --agents claude,codex
  install.sh --no-skills --scope user         # just global AGENTS.md memory
  install.sh --uninstall --agents cursor
EOF
}

parse_agents() {
  local saved_IFS="$IFS"
  IFS=','
  set -- $1
  IFS="$saved_IFS"
  local p
  for p in "$@"; do
    p="${p#"${p%%[![:space:]]*}"}"   # ltrim
    p="${p%"${p##*[![:space:]]}"}"   # rtrim
    [[ -n "$p" ]] || continue
    is_valid_agent "$p" || die "unknown agent in --agents: $p"
    AGENTS="$AGENTS $p"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope)        SCOPE="$2"; shift 2 ;;
    --agents)       parse_agents "$2"; shift 2 ;;
    --copy)         MODE="copy"; shift ;;
    --uninstall)    ACTION="uninstall"; shift ;;
    --no-skills)    DO_SKILLS=0; shift ;;
    --no-agents-md) DO_AGENTS_MD=0; shift ;;
    --help|-h)      usage; exit 0 ;;
    *)              die "unknown option: $1 (try --help)" ;;
  esac
done

[[ "$SCOPE" == "user" || "$SCOPE" == "project" ]] || die "--scope must be user or project"
[[ "$MODE" == "symlink" || "$MODE" == "copy" ]] || die "invalid mode"
[[ $DO_SKILLS -eq 1 || $DO_AGENTS_MD -eq 1 ]] || die "nothing to do (--no-skills and --no-agents-md both set)"
AGENTS="${AGENTS# }"; AGENTS="${AGENTS% }"
[[ -n "$AGENTS" ]] || AGENTS="$ALL_AGENTS"

# --- Main --------------------------------------------------------------------
log "repo: $REPO_ROOT"
log "action=$ACTION scope=$SCOPE mode=$MODE agents=$AGENTS"
log "install: $( [[ $DO_SKILLS -eq 1 ]] && echo skills )$( [[ $DO_SKILLS -eq 1 && $DO_AGENTS_MD -eq 1 ]] && echo ' + ' )$( [[ $DO_AGENTS_MD -eq 1 ]] && echo agents-md )"
echo

# Configure git hooks
git config core.hooksPath .githooks

if [[ $DO_SKILLS -eq 1 && ! -d "$SRC_DIR" ]]; then
  warn "skills directory not found at $SRC_DIR; skipping skills"
  DO_SKILLS=0
fi
if [[ $DO_AGENTS_MD -eq 1 && ! -f "$AGENTS_MD" ]]; then
  warn "AGENTS.md not found at $AGENTS_MD; skipping agents-md"
  DO_AGENTS_MD=0
fi
[[ $DO_SKILLS -eq 1 || $DO_AGENTS_MD -eq 1 ]] || die "nothing to install (missing skills/ and AGENTS.md)"

for agent in $AGENTS; do
  run_for_agent "$agent" || HAD_FAILURE=1
done

echo
if [[ $HAD_FAILURE -ne 0 ]]; then
  warn "completed with failures (agents=$AGENTS, scope=$SCOPE)"
  exit 1
fi
ok "done ($ACTION): $AGENTS ($SCOPE scope)"
if [[ "$MODE" == "symlink" && "$SCOPE" == "project" ]]; then
  printf "${c_dim}Tip: symlinks/bridges are committed to git; commit them so teammates get the same setup.${c_reset}\n"
fi
