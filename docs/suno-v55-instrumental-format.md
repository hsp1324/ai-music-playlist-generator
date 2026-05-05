# Suno V5.5 Instrumental Format

Use this whenever OpenClaw creates Soft Hour Radio, BGM, cafe, study, sleep, lofi, ambient, or any other instrumental/no-vocal Suno track.

## Why This Exists

Suno Custom Mode has a lyrics field. If OpenClaw puts normal prose in that field, Suno can treat those words as lyrics and sing them.

Suno's official help describes Custom Mode as adding a lyrics field, and says to use the Instrumental toggle when not using lyrics. Current Suno v5.5 prompting practice also uses bracketed metatags in the Lyrics field for structure and section control.

References:

- Suno Help: `Can I use my own lyrics?` https://help.suno.com/en/articles/2415873
- Suno Help: `iOS Create: Custom Mode` https://help.suno.com/en/articles/3197377
- Metatag practice guide covering v5.5: https://learnstemlab.com/suno-ai-song-control-metatags-guide

## Mandatory Rule

For instrumental/no-vocal Suno generation, the Suno lyrics/custom-lyrics field must be bracket-only.

Every non-empty line must start with `[` and end with `]`.

Do not put normal sentences, paragraphs, bullet points, Korean prose, English prose, or unbracketed arrangement notes in the lyrics/custom-lyrics field.

## Suno UI / API Settings

- In the Suno UI, enable `Instrumental` when that control is available.
- In an API flow, set the instrumental flag when available, such as `make_instrumental=true`.
- Put global genre/mood/style in the Suno style field.
- Put section flow only in the bracket-only lyrics/custom-lyrics field.
- In Suno Advanced Options, fill the excluded styles / negative style field for instrumental playlists. Use a direct comma-separated list such as:

```text
vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline
```

- Do not put this excluded-style list in the lyrics/custom-lyrics field.

## Duration Rule

For playlist releases, each generated Suno song should usually stay near 2:30 to 3:45, but 4:20 is acceptable.

- Target roughly 2:30 to 3:45 per track.
- If Suno returns a track longer than 4:20, regenerate or replace it before publishing.
- `scripts/openclaw-release auto-publish-playlist` rejects playlist tracks over 260 seconds by default.
- Only use `--allow-long-track` when the human explicitly approves a longer track.

## Good Lyrics Field Shape

```text
[Instrumental only: no sung words, no humming, no spoken words]
[Intro: 8 bars, felt piano motif alone, wide room, soft rain ambience]
[Main Theme: brushed drums enter, upright bass plays long roots, nylon guitar answers the piano]
[Development: warm Rhodes pad opens, piano melody becomes slightly brighter, percussion stays soft]
[Instrumental Break: harp harmonics and soft cymbal swells, melody carried by piano and guitar]
[Bridge: drums drop to rim clicks, bass holds long notes, strings widen gradually]
[Final Theme: piano motif returns, guitar answers every 4 bars, gentle lift without a vocal hook]
[Outro: solo piano and rain ambience, slow fade]
[End]
```

This file can be saved and uploaded to the app with `--lyrics-file`. The app stores it as track context, but the same bracketed text must also be what OpenClaw used in Suno.

## Bad Lyrics Field Shape

```text
Instrumental only, no vocals.
The song starts with felt piano and rain.
Then brushed drums enter.
Avoid singing, humming, spoken words, choirs, and vocal chops.
```

Suno can read those bare lines as singable text. Do not use this format.

## Tag Choices

Prefer instrumental/section tags:

- `[Instrumental only: ...]`
- `[Intro: ...]`
- `[Main Theme: ...]`
- `[Development: ...]`
- `[Instrumental Break: ...]`
- `[Bridge: ...]`
- `[Final Theme: ...]`
- `[Outro: ...]`
- `[End]`

Avoid vocal-oriented tags for Soft Hour Radio instrumental work unless the human explicitly asked for vocals:

- `[Verse]`
- `[Chorus]`
- `[Pre-Chorus]`
- `[Singer]`
- `[Male Vocal]`
- `[Female Vocal]`
- `[Choir]`
- `[Humming]`
- `[Vocalizing]`
- `[Spoken]`
- `[Narration]`

## OpenClaw Checklist

Before pressing Create in Suno:

- Confirm the release is actually instrumental/BGM/no-vocal.
- Enable Suno's Instrumental control if available.
- Confirm the lyrics/custom-lyrics box contains only bracketed lines.
- Confirm there are no unbracketed words anywhere in the lyrics/custom-lyrics box.
- Save the exact same bracketed text to a `.txt` file.
- Upload that exact file to the app with `--lyrics-file`.

If OpenClaw accidentally generated a track from unbracketed prose in the lyrics field, treat that track as suspect. Do not publish it until it has been reviewed for accidental sung words.
