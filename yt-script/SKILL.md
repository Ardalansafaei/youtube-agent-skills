---
name: yt-script
description: >-
  Write a YouTube video script/story from a raw idea - hook options off 21
  formulas, scored, then the full spoken script with retention beats. After the
  spoken script is ready, always synthesize voiceover via yt-tts (Edge-TTS)
  unless the user asks for text-only. Use for video script, story, hook,
  "what should I say", "write my next video", or narration audio.
---

# yt-script

One idea into a script somebody finishes.

Two tools live in this folder and both actually run. Use them. Do not eyeball the hook.

```bash
python3 hookscore.py hooks.txt              # rank your hook options
python3 hookscore.py --hook "one line"      # score a single one
```

## Before you write

1. Read `~/.claude/youtube/voice.md` if it exists. That is the user's voice profile: how they talk
   on camera, the words they never use, who they are talking to, what they will not claim. If it
   does not exist, ask for **three of their own videos**, read or transcribe them, infer the voice,
   and write the file. A script in the wrong voice is worse than no script, because they have to
   read it out loud.
2. Never invent a number, a result or a source. If a figure would strengthen it and you do not have
   one, ask for it or write the line without it.
3. **Stills timeline:** after the script, run `yt-image` —
   `build_still_prompts.py --every 6` then `generate_batch.py` (one prompt per 6 seconds of
   runtime at 150 WPM). Put useful `[ON SCREEN: …]` cues on beats so stills match the story.
4. **After the spoken story/script is written → always run `yt-tts`** (Edge-TTS) and save
   `voiceover.mp3`, unless the user said text-only / بدون صدا. Do not end on script alone.

## Runtime (mandatory)

Long-form scripts are **6–12 minutes** at 150 words per minute.

- Count **spoken words only**. Strip `[ON SCREEN]` and other stage directions before counting.
- **900 words = 6:00. 1800 words = 12:00.** Target about **1200–1500 words** (8–10 min).
- If the draft is short, add teaching beats. If it is long, cut repetition. Do not pad with intros or stretch one idea with filler.
- Report the word count and the minute estimate with the script. Do not start TTS until the count is inside 6–12 minutes, unless the user explicitly asked for a Short or another length.

## The shape

**The first 15 seconds is the whole job.** It does three things or the video leaks: confirm the
click the title promised, open a question the viewer cannot close, and prove the payoff exists.

1. **Hook.** Write FIVE against [the 21 formulas](hooks.json), run them through `hookscore.py`,
   keep the top two, and show the user both with their scores. Never hand over one hook.
2. **The turn** (0:15-0:45). Say what the video is going to do, in one sentence, and start doing it.
   No channel intro, no "before we get started", no subscribe pitch. Those are the single most
   common cause of the 0:30 cliff.
3. **The body.** One idea per beat. Mark each beat with `[ON SCREEN: …]` — aim for a usable visual
   cue about **every 6 seconds** of spoken time (yt-image builds one still prompt per 6s from
   these cues). A talking head with nothing to look at is a podcast.
4. **The payoff.** Deliver the thing the hook promised, explicitly, and say that you are delivering
   it: "that is the prompt, it is in the description".
5. **The close.** One ask. Not three.

## What to hand back

- the two best hooks with their scored panels
- the script, beat by beat, with `[ON SCREEN: ...]` on every beat
- the runtime estimate at 150 words per minute, with spoken word count, inside **6–12 minutes**
- one line naming which formula the winning hook used and why it fits this idea
- **`voiceover.mp3` path** from `yt-tts` (required unless text-only)
- **stills** from `yt-image` — one per 6s (`prompts.txt` + rendered files, unless no-stills)

## After the script (required audio + stills every 6s)

```powershell
$run = Join-Path $env:USERPROFILE ("Downloads\yt-tts\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $run | Out-Null
# write full spoken script to $run\script.txt then:
python "$env:USERPROFILE\.claude\skills\yt-tts\scripts\generate.py" --file "$run\script.txt" --out $run --name voiceover --voice en-US-AndrewNeural
```

```powershell
$img = Join-Path $env:USERPROFILE ("Downloads\yt-images\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $img | Out-Null
Copy-Item "$run\script.txt" "$img\script.txt"
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\build_still_prompts.py" --file "$img\script.txt" --out $img --every 6
python "$env:USERPROFILE\.claude\skills\yt-image\scripts\generate_batch.py" "$img\prompts.txt" --out $img --width 1920 --height 1080
```

Stills must be **1920×1080** (YouTube 16:9 video). Thumbnails separately **1280×720**.


## The gate

Nothing here publishes. Every output ends with asset paths (script + MP3 + stills) and: **ship it, or change it?**
