#!/usr/bin/env bash
# install.sh — install this repo's skills into AI coding agents.
#
# Supported agents: claude (Claude Code), cursor (Cursor),
#                   codebuddy (Tencent CodeBuddy), codex (OpenAI Codex),
#                   workbuddy (WorkBuddy).
#
# What it installs:
#   Skills: each ./skills/<name>/  ->  <agent>/skills/<name>   (universal SKILL.md format)
#   AGENTS.md is not installed. --uninstall still removes rule files
#   created by older versions of this script.
#
# Usage:
#   ./install.sh                         # symlink, user scope, all agents
#   ./install.sh --project               # install into ./<agent>/... (commit to share)
#   ./install.sh --agents claude,codex   # pick agents
#   ./install.sh --copy                  # copy files instead of symlinking
#   ./install.sh --uninstall             # remove what this script installed
#   ./install.sh --help
#
set -eu

# --- Config ------------------------------------------------------------------
# agent id -> skills dir name. Codex and Cursor share ~/.agents/skills.
agent_dir() {
  case "$1" in
    claude)    printf '.claude' ;;
    cursor)    printf '.agents' ;;
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
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_ROOT/skills"
AGENTS_MD="$REPO_ROOT/AGENTS.md"
MARKER='<!-- installed by agent-skills/install.sh -->'
HAD_FAILURE=0
PROCESSED_SKILL_ROOTS=""   # real skills paths already installed this run (agents sharing a dir)

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

check_existing_skill() {
  local path="$1" src="$2"
  [[ -e "$path" || -L "$path" ]] || return 0
  if [[ -L "$path" ]]; then
    local tgt; tgt="$(readlink "$path")"
    [[ "$tgt" == "$src" ]] && return 0
  fi
  warn "target exists and is not ours, overwriting: $path"
  rm -rf "$path"
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
  check_existing_skill "$dest" "$src"
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

  # Several agents may share one skills dir (codex + cursor both use
  # ~/.agents/skills). Install to a given real path only once per run, so a
  # second pass doesn't re-copy or back up the first pass's work (copy mode).
  case " $PROCESSED_SKILL_ROOTS " in
    *" $real_target "*) log "  skills: target already handled for a sibling agent, skipping."; return 0 ;;
  esac
  PROCESSED_SKILL_ROOTS="$PROCESSED_SKILL_ROOTS $real_target"

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

# --- AGENTS.md legacy cleanup ------------------------------------------------
# Target file path written by older versions of this script.
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
  local target
  target="$(agents_md_target "$agent")"
  if [[ -z "$target" ]]; then
    log "  agents.md: $agent reads AGENTS.md natively here, nothing to do."
    return 0
  fi
  uninstall_agents_md_one "$agent" "$target"
}

# --- Per-agent driver --------------------------------------------------------
run_for_agent() {
  local agent="$1" rc=0
  is_valid_agent "$agent" || die "unknown agent: $agent"
  log "agent=$agent scope=$SCOPE"
  run_skills_for_agent "$agent" || rc=1
  if [[ "$ACTION" == "uninstall" ]]; then
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
install.sh — install this repo's skills into AI coding agents.

Usage: install.sh [options]

Options:
  --scope user|project   Where to install (default: user).
                         user    -> ~/<agent-dir>/skills/
                         project -> ./.<agent-dir>/skills/
  --agents LIST          Comma-separated subset of: claude,cursor,codebuddy,codex,workbuddy
                         (default: all five)
  --copy                 Copy files instead of symlinking (for FS without symlink
                         support, e.g. some Windows setups).
  --uninstall            Remove what this script previously installed.
  --help, -h             Show this help.

Agents map to these skills locations:
  claude     .claude/skills
  cursor     .agents/skills
  codebuddy  .codebuddy/skills
  codex      .agents/skills
  workbuddy  .workbuddy/skills

Notes:
  - AGENTS.md is not installed. --uninstall still removes rule files created by
    older versions of this script.

Examples:
  install.sh                                  # user scope, all agents
  install.sh --project                        # vendor into current repo (commit to share)
  install.sh --project --agents claude,codex
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
    --help|-h)      usage; exit 0 ;;
    *)              die "unknown option: $1 (try --help)" ;;
  esac
done

[[ "$SCOPE" == "user" || "$SCOPE" == "project" ]] || die "--scope must be user or project"
[[ "$MODE" == "symlink" || "$MODE" == "copy" ]] || die "invalid mode"
AGENTS="${AGENTS# }"; AGENTS="${AGENTS% }"
[[ -n "$AGENTS" ]] || AGENTS="$ALL_AGENTS"

# --- Main --------------------------------------------------------------------
log "repo: $REPO_ROOT"
log "action=$ACTION scope=$SCOPE mode=$MODE agents=$AGENTS"
log "install: skills"
echo

# Configure git hooks
git config core.hooksPath .githooks

[[ -d "$SRC_DIR" ]] || die "skills directory not found at $SRC_DIR"

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
  printf "${c_dim}Tip: symlinks are committed to git; commit them so teammates get the same setup.${c_reset}\n"
fi
