# OpenClaw Next Release Planner Skill

Use this skill when the AI Music web app asks OpenClaw to make the next one-hour playlist after a private YouTube publish completes.

This skill is the first step of the continuous automation loop. It decides which channel and concept should be made next, then hands off to the automatic private playlist publisher in [openclaw-skills.md](openclaw-skills.md).

## Goal

Choose the next channel and a fresh one-hour playlist concept that fits that channel, avoids recent repetition, and can be privately published end-to-end.

The current active channel roster is:

- `Tokyo Daydream Radio`
- `Soft Hour Radio`

Future channels should be added as separate channel profiles before they enter the rotation.

## Channel Concepts

### Tokyo Daydream Radio

Tokyo Daydream Radio is a mainstream J-pop channel, not an anime OST-only channel.

Use it for:

- General popular J-pop, Japanese pop, city-pop, dance-pop, synth-pop, pop-rock, light band pop, emotional pop ballads, summer pop, night-drive pop, and upbeat youth pop.
- Tokyo/Japan lifestyle scenes such as commute, night walk, beach walk, shopping street, train station, rainy city, weekend trip, cafe date, school-after-hours mood, festival night, or neon city drive.
- Anime/OST-like songs only as one possible lane inside broader J-pop. Do not make every Tokyo Daydream release feel like an anime soundtrack.

Music defaults:

- Vocal songs with original Japanese lyrics.
- Catchy hooks, chorus-focused structure, clear pop melodies, and track-to-track variation.
- Each playlist track needs its own lyric concept, hook, title, and Suno style/settings.
- Avoid lyricless, BGM-only, hum-only, or instrumental J-pop unless the human explicitly asks.

Visual defaults:

- Animated/anime/illustrated/stylized visuals are still the visual language.
- The default signature is three people seen from behind walking forward into the scene, but the music concept is mainstream J-pop, not anime-only.
- The thumbnail uses large `J-POP` plus `TOKYO DAYDREAM RADIO`.

Good concept examples:

- `Tokyo Night Drive J-POP`
- `Summer Beach Walk J-POP`
- `Rainy Shibuya Pop`
- `Weekend Train Ride J-POP`
- `City Lights Dance Pop`
- `After School Guitar Pop`
- `Spring Shopping Street J-POP`

Bad concept direction:

- Repeating `anime opening`, `OST`, or `fantasy anime` every time.
- Making Japan-themed BGM without vocals and calling it J-pop.
- Highlighting only the Japanese language instead of the pop concept.

### Soft Hour Radio

Soft Hour Radio is a long-listening BGM channel.

Use it for:

- Study, work, reading, sleep, rest, cafe, focus, rainy night, forest, ocean, fireplace, piano, acoustic, lofi, ambient, and other background-use releases.

Music defaults:

- Instrumental/no-vocal BGM unless the human explicitly asks for vocals.
- Use detailed non-sung arrangement notes instead of empty lyrics.
- Prioritize usefulness, calmness, flow, and low listener fatigue.

Visual defaults:

- Calm illustrated/stylized scenes matched to the release concept.
- No fixed character count or required walking signature.
- Locked/stable camera by default unless the human asks for movement.
- Thumbnail text should describe the use case, such as `CAFE PIANO`, `FOCUS MUSIC`, `DEEP SLEEP`, or `RAINY NIGHT`.

Good concept examples:

- `Cafe Piano for Work`
- `Rainy Night Reading BGM`
- `Deep Sleep Soft Piano`
- `Forest Morning Focus Music`
- `Ocean Window Study BGM`
- `Fireplace Acoustic Rest`

## Rotation Rules

1. Run `scripts/openclaw-release list-releases` and inspect recent playlist releases.
2. Prefer alternating active channels. With the current two-channel roster:
   - If the previous published playlist was `Tokyo Daydream Radio`, choose `Soft Hour Radio` next.
   - If the previous published playlist was `Soft Hour Radio`, choose `Tokyo Daydream Radio` next.
3. If the previous channel is missing or ambiguous, choose the active channel with the oldest recent published playlist. If still tied, choose the channel that best improves variety.
4. Do not pick the same channel twice in a row unless the other channel is blocked, unavailable, or the human explicitly requested it.
5. When future channels are added, rotate across all active channels while respecting each channel's profile and upload readiness.

## Fresh Concept Rules

Before choosing a concept:

1. Review recent release titles, channel names, descriptions, and YouTube ids from `scripts/openclaw-release list-releases`.
2. Avoid repeating the same theme, setting, title pattern, thumbnail phrase, lyric premise, and visual scene used recently.
3. Keep the selected channel identity stable while varying the specific release concept.
4. Prefer concepts that are easy for YouTube viewers to understand quickly from the title and thumbnail.
5. Prefer search/click-friendly phrases, but do not stuff keywords or make titles feel machine-generated.

For `Tokyo Daydream Radio`, vary:

- city/night/day/beach/rain/train/spring/summer/festival/weekend/drive/walk/cafe/street settings
- pop substyle: dance-pop, city-pop, synth-pop, guitar pop, pop-rock, ballad, bright summer pop
- lyric angle: new start, night escape, first love, walking home, city lights, weekend freedom, seaside memory

For `Soft Hour Radio`, vary:

- use case: study, work, reading, sleep, rest, cafe, focus
- setting: rain, forest, ocean, fireplace, window, morning, late night
- instrument palette: piano, guitar, Rhodes, strings, lofi drums, ambient pads, acoustic textures

## Output Plan

After selecting the next channel and concept, immediately continue into the automatic private playlist publisher skill.

The selected plan should include:

- `selected_channel`
- `release_title`
- `release_description`
- `music_direction`
- `visual_direction`
- `thumbnail_text`
- `metadata_language_plan`
- brief reason why this was chosen and how it differs from recent releases

For every Playlist Release plan, the main YouTube title and all localized titles must start exactly with `[playlist]`. Do not use this prefix for Single Releases.

Then execute the one-hour playlist automation from [openclaw-skills.md](openclaw-skills.md), using the selected channel and concept.

## Skill Prompt

```text
You are the Next Release Planner for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use scripts/openclaw-release only.

First, update the repo:
git pull origin main

Then inspect recent releases:
scripts/openclaw-release list-releases

Choose the next one-hour Playlist Release using docs/openclaw-next-release-planner.md:
- Rotate active channels instead of repeating the same channel.
- Current active channels are Tokyo Daydream Radio and Soft Hour Radio.
- Tokyo Daydream Radio is mainstream J-pop/pop with Japanese vocals; anime/OST-like music is allowed but not the whole channel identity.
- Soft Hour Radio is instrumental/no-vocal long-listening BGM for study, work, reading, sleep, rest, cafe, and focus.
- Pick a fresh concept not used recently while keeping the selected channel identity clear.

After choosing the channel and concept, run the Automatic Private Playlist Publisher skill from docs/openclaw-skills.md.
Create enough audio for at least 3600 seconds, generate final cover, separate YouTube thumbnail, 8 second loop video when possible, metadata, and publish privately to the selected YouTube channel.

When done, report:
- selected_channel
- release.id
- release.title
- youtube_video_id
- privacy: private
- short reason for the chosen concept
```
