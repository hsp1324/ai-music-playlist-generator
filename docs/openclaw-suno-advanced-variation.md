# OpenClaw Suno Advanced Variation Policy

Use this policy for every new Suno generation on every channel. The goal is to
keep a playlist coherent without producing the same arrangement, singer, or
mix profile repeatedly.

For every lyric/vocal generation, first read and obey
[openclaw-vocal-arrangement-policy.md](openclaw-vocal-arrangement-policy.md).
That standing direction limits new vocal music to one release-level family:
themed large-scale orchestra, piano-only accompaniment, or acoustic-guitar-only
accompaniment. It overrides older beat-led vocal lane examples unless the
human explicitly requests a one-off exception.

Suno defines `50%` Weirdness as the normal expected result. Style Influence
runs from Loose to Strong. The ranges below are this project's operating
heuristics, not universal Suno quality claims.

## Required pre-generation plan

Before pressing Create, record these choices for each track:

- `weirdness_percent`
- `style_influence_percent`
- genre/subgenre and BPM or tempo feel
- rhythmic feel and two or three defining instruments
- arrangement role, such as anchor, contrast, peak, or closer
- for vocal songs: `vocal_arrangement_family`, the orchestral theme when
  applicable, the hard allowed/forbidden instrument palette, vocal gender
  control, and a distinct singer identity

Do not leave every track at `50 / 50`. Do not reuse the same slider pair for
every track in a release. For three or more newly generated tracks, use at least
two of the operating bands below and differ by at least five percentage points
on one slider between adjacent tracks.

## Operating bands

Choose values from the band that fits the track instead of rotating blindly:

| Track intent | Weirdness | Style Influence | Use |
| --- | ---: | ---: | --- |
| Faithful anchor | 35-45 | 72-85 | Genre-defining opener, lyric-dense song, strict channel lane |
| Balanced variation | 46-58 | 60-72 | Most mainstream vocal or instrumental tracks |
| Exploratory contrast | 59-70 | 45-60 | Hybrid genre, unusual groove, contrasting instrumental color |

For lyric-heavy vocal songs, normally keep Weirdness between `38-60` so
novelty does not overwhelm diction and song structure. Instrumental and
experimental tracks may reach `70`. Do not use Weirdness above `75` or Style
Influence below `40` in normal automation unless the human explicitly requests
an experimental result. Avoid values below `30` because they can reinforce the
same safe output pattern.

Slider changes are only one source of variation. Also change meaningful musical
inputs: tempo, drum pocket, bass movement, key/mode, instrumentation, harmonic
color, section order, intro texture, breakdown/drop design, vocal register, and
delivery. Keep the release inside its selected genre lane and arrangement
family. For piano-only and guitar-only vocal work, do not add drums, bass,
synths, strings, or other instruments merely to create variation. For
orchestral vocal work, vary within the one selected release theme instead of
switching eras or replacing the orchestra with a pop rhythm section.

## Adaptive correction

After reviewing the generated pair:

- If it sounds too similar to recent tracks, raise Weirdness by `8-12` points
  and/or lower Style Influence by `5-10` points on the next attempt, staying
  inside the safe bands. Also change at least two musical inputs.
- If it drifts out of genre, becomes incoherent, or ignores the style prompt,
  lower Weirdness by `8-12` and raise Style Influence by `8-12`.
- If only the singer is repetitive, keep the genre controls sensible and
  rewrite the singer identity. Do not try to solve vocal sameness with extreme
  Weirdness alone.
- A retry for the same track keeps its intended lead gender unless the vocal
  concept itself is deliberately changed.

## Vocal gender and singer identity

For every lyric/vocal song:

1. Decide the lead configuration before Create.
2. In Suno `More options` / `Vocal gender`, select `Female` for a female lead or
   `Male` for a male lead. Leave it unselected for a true male/female duet,
   alternating mixed leads, group vocal, or intentionally unspecified lead.
3. Put a concrete singer identity in the Style field **and** a short bracketed
   cue near the top of the custom Lyrics field. Gender alone is insufficient.

The singer identity must combine at least three traits from register, timbre,
delivery, mic distance, articulation/accent, and emotional attitude. Examples:

- `low female mezzo, smoky grain, dry close-mic phrasing, restrained confidence`
- `bright male tenor, slight nasal indie color, agile syncopation, intimate mic`
- `warm female alto, rounded soul tone, soft vibrato, measured Korean diction`
- `rough low male baritone rap, crisp consonants, off-axis close delivery`
- `airy female head voice hook with calm male baritone verses`

Use a matching lyrics cue such as:

```text
[Lead vocal: low female mezzo, smoky grain, dry close-mic, restrained confidence]
```

Within one release, do not repeat the same gender + register + timbre
combination on adjacent new tracks. Rotate voice families deliberately across
the release. Do not select a reusable Suno Voice or Persona by default because
that can make separate songs converge on one singer; use one only when the
human explicitly wants a consistent vocalist and has the right to use it.

For instrumental/no-vocal tracks, leave Vocal gender unselected, enable
Instrumental, keep the lyrics field bracket-only, and retain the normal vocal
exclusion list.

## UI and API values

- Suno UI sliders use percentages from `0-100`.
- The app API fields `style_weight`, `weirdness_constraint`, and `audio_weight`
  use normalized values from `0.00-1.00`; UI `58%` becomes API `0.58`.
- The app API uses `vocal_gender: "f"` or `"m"`; `female` and `male` are accepted
  aliases and normalized before the provider call.
- Save the chosen advanced values and vocal identity in generation metadata so
  later OpenClaw runs can avoid repeating them.

## Final check before Create

- Advanced Options is open and the intended values are visible.
- Weirdness and Style Influence were chosen for this track, not copied from the
  previous track or left at `50 / 50` without a reason.
- Vocal gender matches the intended lead, or is intentionally unselected.
- Every vocal track stays inside the release's selected orchestral,
  piano-only, or acoustic-guitar-only family; orchestral tracks also match the
  one declared theme.
- Every vocal track has a distinct detailed singer identity in Style and Lyrics.
- The exact values and singer identity are recorded with the track plan.
