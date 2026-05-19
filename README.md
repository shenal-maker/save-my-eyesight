# save-my-eyesight

I started building this when my eyesight got worse. Claude Code is great, but its default responses are decorated for eyes — long code blocks, headers, bullet preambles — and that's brutal to listen to.

This wraps Claude Code so:

- It speaks every reply aloud (macOS `say`).
- It writes for the ear: short answers, no code dumps in the spoken stream, no decorative markdown.
- Voice input you already get for free from Claude Code's built-in voice mode.

Small on purpose. One hook script, one prompt file, one installer.

## Install

Requires macOS (uses the built-in `say` command) and Python 3.

```bash
git clone https://github.com/shenal-maker/save-my-eyesight.git
cd save-my-eyesight
./install.sh
```

The installer does two things:

1. Adds a Stop hook to `~/.claude/settings.json` pointing at `hooks/tts.py`.
2. Appends the "respond for the ear" rules to `~/.claude/CLAUDE.md`.

Your `settings.json` is backed up to `settings.json.bak.<timestamp>` first. The Stop hook is appended to the existing array, not replaced — other hooks (`claudio`, sound packs, etc.) keep working.

### Don't want it global?

If you'd rather keep your global `CLAUDE.md` untouched and apply the ear-shaped rules only to specific projects:

```bash
./install.sh --no-prompt
```

That wires the TTS hook only. Then drop `prompts/ear-shaped.md` into any project's own `CLAUDE.md` (or `.claude/CLAUDE.md`) when you want listenable replies there.

The hook strips markdown on its own, so even without the prompt rules, what you hear is tolerable — just longer than it could be.

Start a new Claude Code session and the next reply will speak.

## Voice input

You don't need this repo for voice input. Claude Code has it built in. Add to `~/.claude/settings.json`:

```json
"voice": { "enabled": true, "mode": "hold" },
"voiceEnabled": true
```

Then hold the voice key to dictate.

## Customize

Set env vars before launching Claude Code:

| Var | Default | Effect |
| --- | --- | --- |
| `SME_VOICE` | system voice | macOS voice name. `say -v ?` lists them. Try `Samantha`, `Daniel`, `Karen`, or one of the new Siri voices. |
| `SME_RATE` | `220` | Words per minute. Most people land between 250 and 320 once their ear adjusts. |

## How it works

When Claude finishes a reply, the Stop hook runs. It reads the session transcript JSONL at the path Claude Code passes in, walks backward to the last assistant message, strips markdown that doesn't translate to speech, kills any in-flight `say` so the new reply takes over, and pipes the cleaned text to `say` non-blocking.

The stripping rules:

- Code blocks → "code block omitted." Claude is told not to paste them anyway; this is a safety net.
- Headers, bullets, bold, italic, link URLs → markers dropped, text kept.
- Blank lines → collapsed so `say` doesn't pause forever.

The ear-shaped prompt lives in `prompts/ear-shaped.md` and gets appended to your global `CLAUDE.md` so it applies to every project.

## Known gaps

- macOS only. Linux or Windows would swap `say` for `espeak`, Edge TTS, OpenAI TTS, ElevenLabs, etc.
- Built-in `say` voices are mediocre. The hook is a single subprocess call, so swap in OpenAI TTS or ElevenLabs if you want better quality and don't mind the API cost.
- Long edits get summarized verbally, not dictated. By design.

## Uninstall

Restore the most recent backup:

```bash
ls -t ~/.claude/settings.json.bak.* | head -1 | xargs -I{} cp {} ~/.claude/settings.json
```

Then delete the ear-shaped block from `~/.claude/CLAUDE.md` (look for the `<!-- save-my-eyesight: ear-shaped rules -->` marker).

## License

MIT.
