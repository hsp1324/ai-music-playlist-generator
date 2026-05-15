# Tmux Auto Session Setup For New Instances

This document is written so another Codex instance can reproduce the SSH-to-tmux
behavior from this VM without copying unrelated shell secrets.

## Goal

When the `ubuntu` user connects over SSH, an interactive tmux session chooser
should appear automatically unless the shell is already inside tmux or the user
sets `NO_AUTO_TMUX=1`.

The chooser supports:

- choose an existing tmux session
- start a new Codex tmux session
- delete a tmux session
- open a normal shell without tmux

## Prerequisites

On the target instance:

```bash
sudo apt update
sudo apt install -y tmux
command -v codex
```

The current setup assumes:

- user: `ubuntu`
- shell: `bash`
- project directory: `/opt/ai-music-playlist-generator`
- Codex launch command: `codex --dangerously-bypass-approvals-and-sandbox`

If the target instance uses a different project path, update
`__ai_music_repo` in the `.bashrc` block below.

## Copy Tmux Config

Create or replace `/home/ubuntu/.tmux.conf` with:

```tmux
set -g history-limit 50000
set -g mouse on
set -g set-clipboard on
setw -g mode-keys vi

# Make the wheel scroll tmux history, even inside mouse-aware TUI apps.
bind-key -n WheelUpPane if-shell -F "#{pane_in_mode}" "send-keys -M" "copy-mode -e; send-keys -M"
bind-key -n WheelDownPane if-shell -F "#{pane_in_mode}" "send-keys -M" "send-keys -M"

# Toggle mouse mode when native terminal drag selection is needed.
bind-key m if-shell -F "#{mouse}" \
  "set -g mouse off; display-message 'tmux mouse: off - native drag/Ctrl+C'" \
  "set -g mouse on; display-message 'tmux mouse: on - wheel scrolls tmux history'"

bind-key -T copy-mode-vi C-c send-keys -X copy-selection-and-cancel
bind-key -T copy-mode C-c send-keys -X copy-selection-and-cancel
```

Equivalent one-liner from this instance:

```bash
scp ~/.tmux.conf ubuntu@TARGET_INSTANCE_IP:~/.tmux.conf
```

## Append Bashrc Block

Append only this block to `/home/ubuntu/.bashrc` on the target instance.
Do not copy this VM's whole `.bashrc`, because it may contain unrelated tokens
or machine-specific exports.

```bash
if [[ $- == *i* ]] && [[ -z "$TMUX" ]] && [[ -z "$NO_AUTO_TMUX" ]] && [[ -t 0 ]] && [[ -t 1 ]]; then
  __ai_music_repo="/opt/ai-music-playlist-generator"
  __ai_music_default_session="ai-music-codex"
  __ai_music_color_prompt=""
  __ai_music_color_cursor=""
  __ai_music_color_selected=""
  __ai_music_color_option=""
  __ai_music_color_hint=""
  __ai_music_color_reset=""

  if command -v tput >/dev/null 2>&1 && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
    __ai_music_color_prompt="$(tput bold)$(tput setaf 6)"
    __ai_music_color_cursor="$(tput bold)$(tput setaf 2)"
    __ai_music_color_selected="$(tput bold)$(tput setaf 3)"
    __ai_music_color_option="$(tput setaf 7)"
    __ai_music_color_hint="$(tput dim)"
    __ai_music_color_reset="$(tput sgr0)"
  fi

  __ai_music_select_menu() {
    local __ai_music_prompt="$1"
    local __ai_music_default_index="$2"
    shift 2
    local __ai_music_options=("$@")
    local __ai_music_count="${#__ai_music_options[@]}"
    local __ai_music_selected_index="$((__ai_music_default_index - 1))"
    local __ai_music_i __ai_music_key __ai_music_sequence

    if (( __ai_music_selected_index < 0 || __ai_music_selected_index >= __ai_music_count )); then
      __ai_music_selected_index=0
    fi

    while true; do
      printf "%b%s%b\n" "$__ai_music_color_prompt" "$__ai_music_prompt" "$__ai_music_color_reset"
      for __ai_music_i in "${!__ai_music_options[@]}"; do
        if (( __ai_music_i == __ai_music_selected_index )); then
          printf " %b>%b %b%s%b\n" \
            "$__ai_music_color_cursor" "$__ai_music_color_reset" \
            "$__ai_music_color_selected" "${__ai_music_options[$__ai_music_i]}" "$__ai_music_color_reset"
        else
          printf "   %b%s%b\n" \
            "$__ai_music_color_option" "${__ai_music_options[$__ai_music_i]}" "$__ai_music_color_reset"
        fi
      done
      printf "%b%s%b\n" "$__ai_music_color_hint" "Use Up/Down and Enter. Number keys also work." "$__ai_music_color_reset"

      IFS= read -rsn1 __ai_music_key
      case "$__ai_music_key" in
        $'\x1b')
          IFS= read -rsn2 -t 0.2 __ai_music_sequence
          case "$__ai_music_sequence" in
            "[A"|"OA")
              (( __ai_music_selected_index = (__ai_music_selected_index - 1 + __ai_music_count) % __ai_music_count ))
              ;;
            "[B"|"OB")
              (( __ai_music_selected_index = (__ai_music_selected_index + 1) % __ai_music_count ))
              ;;
          esac
          ;;
        "")
          echo
          __ai_music_selected="$((__ai_music_selected_index + 1))"
          return 0
          ;;
        [1-9])
          if (( __ai_music_key >= 1 && __ai_music_key <= __ai_music_count )); then
            echo
            __ai_music_selected="$__ai_music_key"
            return 0
          fi
          ;;
      esac

      printf '\033[%sA' "$((__ai_music_count + 2))"
      printf '\033[J'
    done
  }

  while true; do
    echo
    echo "tmux session chooser"
    echo "Existing sessions:"
    tmux list-sessions -F '  #{session_name} (windows: #{session_windows}, attached: #{session_attached})' 2>/dev/null || echo "  none"
    echo
    __ai_music_select_menu "Choose an action:" 1 \
      "Choose an existing tmux session" \
      "Start a new Codex tmux session" \
      "Delete a tmux session" \
      "Open a normal shell without tmux"
    __ai_music_choice="$__ai_music_selected"

    case "${__ai_music_choice:-1}" in
      2)
        __ai_music_session="ai-music-codex-$(date +%Y%m%d-%H%M%S)"
        exec tmux new-session -s "$__ai_music_session" \
          "cd \"$__ai_music_repo\" || exec bash -l; codex --dangerously-bypass-approvals-and-sandbox; exec bash -l"
        ;;
      3)
        while true; do
          mapfile -t __ai_music_sessions < <(tmux list-sessions -F '#{session_name}' 2>/dev/null)

          echo
          if [[ ${#__ai_music_sessions[@]} -eq 0 ]]; then
            __ai_music_select_menu "No existing tmux sessions." 1 "Back"
            break
          fi

          __ai_music_options=("${__ai_music_sessions[@]}" "Back")
          __ai_music_back_number=$((${#__ai_music_sessions[@]} + 1))
          __ai_music_select_menu "Delete a tmux session:" "$__ai_music_back_number" "${__ai_music_options[@]}"
          __ai_music_session_number="$__ai_music_selected"

          if (( __ai_music_session_number == __ai_music_back_number )); then
            break
          fi

          __ai_music_session="${__ai_music_sessions[$((__ai_music_session_number - 1))]}"
          read -r -p "Really delete tmux session '${__ai_music_session}'? [y/N]: " __ai_music_confirm
          case "$__ai_music_confirm" in
            y|Y|yes|YES)
              tmux kill-session -t "$__ai_music_session"
              echo "Deleted tmux session '${__ai_music_session}'."
              ;;
            *)
              echo "Delete canceled."
              ;;
          esac
        done
        ;;
      4)
        cd "$__ai_music_repo" 2>/dev/null || true
        break
        ;;
      *)
        while true; do
          mapfile -t __ai_music_sessions < <(tmux list-sessions -F '#{session_name}' 2>/dev/null)

          echo
          if [[ ${#__ai_music_sessions[@]} -eq 0 ]]; then
            __ai_music_select_menu "No existing tmux sessions." 1 "Back"
            break
          fi

          __ai_music_options=("${__ai_music_sessions[@]}" "Back")
          __ai_music_back_number=$((${#__ai_music_sessions[@]} + 1))
          __ai_music_select_menu "Choose a tmux session:" 1 "${__ai_music_options[@]}"
          __ai_music_session_number="$__ai_music_selected"

          if (( __ai_music_session_number == __ai_music_back_number )); then
            break
          fi

          __ai_music_session="${__ai_music_sessions[$((__ai_music_session_number - 1))]}"
          exec tmux attach-session -t "$__ai_music_session"
        done
        ;;
    esac
  done

  unset __ai_music_back_number __ai_music_choice __ai_music_confirm
  unset __ai_music_color_cursor __ai_music_color_hint __ai_music_color_option
  unset __ai_music_color_prompt __ai_music_color_reset __ai_music_color_selected
  unset __ai_music_default_session __ai_music_i __ai_music_repo
  unset __ai_music_options __ai_music_selected __ai_music_session
  unset __ai_music_session_number __ai_music_sessions
  unset -f __ai_music_select_menu
fi
```

## Ensure Login Shell Loads Bashrc

Ubuntu's default `/home/ubuntu/.profile` usually includes:

```bash
if [ -n "$BASH_VERSION" ]; then
    if [ -f "$HOME/.bashrc" ]; then
        . "$HOME/.bashrc"
    fi
fi
```

If the target instance does not have that block, add it to `.profile`.

## Validation

Open a new SSH connection:

```bash
ssh ubuntu@TARGET_INSTANCE_IP
```

Expected result: the terminal prints `tmux session chooser`.

To bypass the chooser temporarily:

```bash
NO_AUTO_TMUX=1 ssh ubuntu@TARGET_INSTANCE_IP
```

To confirm tmux config loaded inside tmux:

```bash
tmux show -g history-limit
tmux show -g mouse
```

Expected:

```text
history-limit 50000
mouse on
```

## Rollback

If SSH login gets stuck or the menu is unwanted:

```bash
NO_AUTO_TMUX=1 ssh ubuntu@TARGET_INSTANCE_IP
```

Then edit `/home/ubuntu/.bashrc` and remove the block starting with:

```bash
if [[ $- == *i* ]] && [[ -z "$TMUX" ]] && [[ -z "$NO_AUTO_TMUX" ]]
```

and ending at the matching `fi`.

