---
name: yt-tts
description: >-
  Generate YouTube voiceovers with free Edge-TTS after a story/script exists.
  Default TTS for yt-agent and yt-script: save script.txt then produce
  voiceover.mp3 automatically. Use for narration, story audio, script-to-speech,
  Edge TTS. Prefer over Gemini Chrome TTS unless user asks for Gemini/Aoede.
---

# yt-tts (Edge-TTS) — automatic after story/script

**Default TTS for YouTube agent.** Whenever a spoken story/script is finished,
run this skill and deliver `voiceover.mp3` — do not stop at text.

Requires: `pip install edge-tts`

## Defaults

| Setting | Value |
|---------|--------|
| Voice | `en-US-AndrewNeural` |
| Rate / pitch | `+0%` / `+0Hz` |
| Format | MP3 |
| Save root | `%USERPROFILE%\Downloads\yt-tts\<yyyyMMdd-HHmmss>\` |
| Directions | `[ON SCREEN: …]` stripped by default (`--spoken-only`) |

## Required flow (called by yt-agent / yt-script)

1. Take the final spoken story/script (do not invent narration).
2. `$run` = `Downloads\yt-tts\<timestamp>\`
3. Save `$run\script.txt`
4. Generate:

```powershell
python "$env:USERPROFILE\.claude\skills\yt-tts\scripts\generate.py" --file "$run\script.txt" --out $run --name voiceover --voice en-US-AndrewNeural
```

5. Verify `voiceover.mp3`, `script_spoken.txt`, `voiceover.json`; report paths.
6. Skip only if user said text-only / بدون صدا.

## Checklist

```
yt-tts:
- [ ] script.txt written from real story/script
- [ ] generate.py OK
- [ ] voiceover.mp3 on disk
- [ ] path returned to user
```

## Failure rules

- Throttle/403 → retries built-in; if still failing, report and keep `script.txt`
- Never invent audio; Gemini only if user asks by name
