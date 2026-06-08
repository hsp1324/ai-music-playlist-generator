# Suno V5.5 Instrumental Format

Use this whenever OpenClaw creates Soft Hour Radio solo-piano tracks, BGM, cafe, study, sleep, lofi, ambient, or any other instrumental/no-vocal Suno track. New Soft Hour Radio audio should be solo piano/felt piano/quiet piano; existing similar Soft Hour tracks may temporarily fill the back half when there are not enough piano tracks to approach one hour.

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

## Producer Tag / Artist Reference Safety

Suno can block lyrics/custom-lyrics, metatags, style, prompts, tags, or excluded styles when a word looks like a producer tag or a specific artist reference.

- Do not use producer names, artist names, label names, artist-like aliases, `type beat` credit text, or exact imitation phrases.
- Known blocked example: `lowlight` can trigger `Your lyrics contain producer tag lowlight - we don't reference specific artists on Suno, please change your lyrics and try again.`
- If Suno flags a term, replace it with generic descriptive wording before retrying. For `lowlight`, use alternatives like `low-lit`, `dim`, `shadowy`, `muted night`, `soft ambient`, or `dark warm room tone`.
- This rule applies even inside bracketed instrumental metatags. Write `[Intro: dim felt piano in a quiet room]`, not `[Intro: lowlight felt piano]`.

## Suno UI / API Settings

- Select Suno v5.5 for new generations whenever it is available. The AI Music app API default is `V5_5`. If Suno's UI or API shows v5.5 costing more credits than v5 for the same request, stop before batch generation and report the exact credit difference to the human.
- In the Suno UI, enable `Instrumental` when that control is available.
- In an API flow, set the instrumental flag when available, such as `make_instrumental=true`.
- Put global genre/mood/style in the Suno style field.
- Put section flow only in the bracket-only lyrics/custom-lyrics field.
- In Suno Advanced Options, fill the excluded styles / negative style field for instrumental playlists. Use a direct comma-separated list such as:

```text
vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline, white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss
```

- Do not put this excluded-style list in the lyrics/custom-lyrics field.

## Duration Rule

Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno prompts, style strings, lyrics, or bracketed metatags unless the human explicitly asks for that wording. Those phrases can cause Suno to end too early or behave unpredictably. Prompt structurally instead: a credit-efficient full instrumental cue that naturally lands around 4 minutes or longer, with natural intro, first main theme, second developed theme, variation/breakdown where useful, final theme lift, and a resolved outro. The bracket-only lyrics/custom-lyrics field should contain enough section flow to steer a full cue, not only a few short arrangement notes. Suno has no guaranteed minimum-duration field, so verify the downloaded duration. Tracks shorter than 4:00 are still valid uploads when they fit. Playlist tracks from 1:00 to 1:59 should be uploaded/used and recorded for later analysis; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute cues are acceptable.
- If Suno repeatedly returns tracks over the allowed helper max for a non-exempt channel, stop and report the issue instead of adding duration caps to every prompt.
- Do not use short-loop, jingle, intro, bumper, sting, teaser, or snippet wording for full playlist tracks.

## Good Lyrics Field Shape

```text
[Instrumental only: no sung words, no humming, no spoken words]
[Intro: 8 bars, felt piano motif alone, wide room, soft rain ambience]
[Main Theme: brushed drums enter, upright bass plays long roots, nylon guitar answers the piano]
[Second Theme: piano melody opens into a longer answering phrase, bass movement becomes warmer, percussion stays soft]
[Development: warm Rhodes pad opens, piano melody becomes slightly brighter, dynamics rise gently]
[Instrumental Break: harp harmonics and soft cymbal swells, melody carried by piano and guitar]
[Bridge: drums drop to rim clicks, bass holds long notes, strings widen gradually]
[Final Theme: piano motif returns with a slightly higher register, guitar answers every 4 bars, gentle lift without a vocal hook]
[Resolved Outro: motif slows down, rain ambience remains, final chord rings naturally]
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
