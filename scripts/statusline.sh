#!/usr/bin/env bash
# Reads Claude Code statusline JSON from stdin and prints a 2-line formatted status line.

input=$(cat)

# --- Claude fields ---
model=$(echo "$input"        | jq -r '.model.display_name // "unknown"')
tokens_in=$(echo "$input"    | jq -r '.context_window.total_input_tokens // 0')
tokens_out=$(echo "$input"   | jq -r '.context_window.total_output_tokens // 0')
cache_read=$(echo "$input"   | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
cache_create=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
ctx_used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
session_cost=$(echo "$input" | jq -r '.session_cost_usd // 0')

# --- Context bar ---
BAR_WIDTH=15
if [[ -n "$ctx_used_pct" ]]; then
  ctx_pct=$(awk "BEGIN { printf \"%.1f\", $ctx_used_pct }")
  fill=$(awk "BEGIN { printf \"%d\", int($ctx_used_pct / 100 * $BAR_WIDTH + 0.5) }")
  [[ $fill -gt $BAR_WIDTH ]] && fill=$BAR_WIDTH
  pad=$(( BAR_WIDTH - fill ))
  filled=$(printf '█%.0s' $(seq 1 $fill 2>/dev/null) 2>/dev/null || awk "BEGIN { s=\"\"; for(i=0;i<$fill;i++) s=s\"█\"; printf s }")
  empty=$(printf '░%.0s'  $(seq 1 $pad  2>/dev/null) 2>/dev/null || awk "BEGIN { s=\"\"; for(i=0;i<$pad;i++)  s=s\"░\"; printf s }")
  bar="${filled}${empty}"
  pct_display="${ctx_pct}%"
else
  bar=$(printf '░%.0s' $(seq 1 $BAR_WIDTH))
  pct_display="n/a"
fi

# --- Cost ---
cost_display=$(awk "BEGIN { printf \"\$%.2f\", $session_cost }")

# --- Git fields ---
folder=$(basename "$(pwd)")
git_line=""
if git -C "$(pwd)" rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
  branch=$(git -C "$(pwd)" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null \
           || git -C "$(pwd)" --no-optional-locks rev-parse --short HEAD 2>/dev/null \
           || echo "detached")
  ahead_behind=$(git -C "$(pwd)" --no-optional-locks rev-list --count --left-right "@{upstream}...HEAD" 2>/dev/null || true)
  sync=""
  if [[ -n "$ahead_behind" ]]; then
    behind=$(echo "$ahead_behind" | awk '{print $1}')
    ahead=$(echo  "$ahead_behind" | awk '{print $2}')
    [[ "$ahead"  -gt 0 ]] && sync+=" ↑${ahead}"
    [[ "$behind" -gt 0 ]] && sync+=" ↓${behind}"
  fi
  dirty=""
  [[ -n "$(git -C "$(pwd)" --no-optional-locks status --porcelain 2>/dev/null)" ]] && dirty="*"
  git_line=" | 🌿 ${branch}${dirty}${sync}"
fi

# --- Output (exactly 2 lines) ---
printf "[%s]  📁 %s%s\n%s %s | %s | input:%s output:%s | cache_read:%s cache_creation:%s\n" \
  "$model" \
  "$folder" \
  "$git_line" \
  "$bar" \
  "$pct_display" \
  "$cost_display" \
  "$tokens_in" \
  "$tokens_out" \
  "$cache_read" \
  "$cache_create"
