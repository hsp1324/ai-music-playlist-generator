# OpenClaw Vocal Arrangement Policy

## Publishing schedule — effective 2026-10-19

Each automated channel publishes at most once weekly at 07:00 Asia/Seoul on its assigned day: Monday HaruHaru and 불송; Tuesday Solwave Radio and BibliaCanto; Wednesday Tokyo Daydream Radio; Thursday Soft Hour Radio; Friday sundaze; Saturday Cinematic Pulse; Sunday Club Bloom. Storylight OST and MusicSun remain manual-only. The app calculates the slot; do not override it with a manual timestamp.
Cinematic Pulse shares one Saturday slot, alternating orchestra and cute_game each week. The orchestra parity anchor is 2026-10-24, and cute_game is 2026-10-31. Each lane publishes every 14 days at 07:00. Set the exact lane and follow `docs/openclaw-weekly-publishing.md`.

## Current human direction — 2026-10-27

For HaruHaru, sundaze, Solwave Radio, Tokyo Daydream Radio, BibliaCanto,
불송 and any other channel making songs with lyrics, vary both the actual
music genre and the balance of singing, singing rap and rap. This replaces
the 2026-08-24 restriction to three accompaniment families and its mandatory
orchestra/piano/guitar rotation. Modern beats, bass, synths, bands and hybrid
arrangements are allowed when they fit the selected channel and genre.

Do not keep choosing piano ballads as the safe default. Piano and acoustic
songs remain useful parts of the rotation. Preserve existing songs, lyrics,
assets and releases; apply this direction to new prompts and genuine missing
material, rather than regenerating finished work to satisfy a quota.

Instrumental/no-vocal channels and explicit instrumental requests retain their
own rules. Do not add rap, humming or sung hooks to Soft Hour Radio,
Cinematic Pulse or Club Bloom instrumental work under this vocal policy.

## Plan genre and vocal delivery separately

Choose a coherent genre/groove and emotional arc for each playlist, then vary
vocal configurations within it. Rotate genres across releases; related
hybrids may share a playlist when tempo, groove and emotional context connect.
Avoid an unrelated genre sampler or repeated near-identical piano ballads.
Use recent release plans and the app's existing history for rotation; do not
start a historical Suno Library sweep.

| Channel | Examples to rotate, subject to its current channel brief |
| --- | --- |
| HaruHaru | Korean hip-hop, rap-pop, boom bap, trap-soul, R&B/neo-soul, indie-acoustic, pop-rock, piano vocal |
| Tokyo Daydream Radio | Japanese hip-hop/R&B, melodic J-rap, pop-rock, synth-pop, city-pop, anime-pop, acoustic pop |
| sundaze | pop hip-hop, R&B/soul, funk/disco pop, synth-pop, indie/alt pop, pop-rock, country/folk, acoustic or piano songs |
| Solwave Radio | urbano/reggaeton pop, Latin R&B/soul, bachata, salsa/cumbia pop, Latin pop-rock, Spanish acoustic or piano songs |
| BibliaCanto | passage-faithful scripture hip-hop, rap-pop, R&B, neo-soul, pop-rock, Afropop, synth-pop, acoustic or orchestral songs |
| 불송 | source-faithful Korean rap, boom bap, trap-soul, R&B/soul, indie-acoustic, pop-rock, piano or cinematic hybrids |

Keep each channel's lyric language, source requirements and public packaging.
BibliaCanto stays passage-based and outside gospel/worship/CCM; 불송 keeps its
verified source-to-lyric mapping and mainstream public language. Retain the
existing public-title restrictions and channel-specific routing.

## Include singing rap without putting rap in every song

A normal new multi-song vocal playlist must include at least one distinct
**singing-rap** prompt and at least one primarily sung song. Do not count a
label in the title as delivery, or two outputs of one prompt as two different
vocal plans. A single-song request can use whichever configuration fits; do
not add a rap bridge to every single or to every track.

Rotate these patterns rather than copying one verse/chorus template:

| Configuration | Concrete section plan |
| --- | --- |
| Singing only | sung verses, sung chorus, melodic bridge; no required rap |
| Singing rap | pitched rhythmic speech with melodic contour in a verse or hook, contrasted with fully sung sections |
| Rap verse + sung hook | rhythm-led rap verses, recognizably melodic chorus, optional sung bridge |
| Singing-led + occasional rap | mostly sung song with one short rap verse or bridge, then return to the melody |
| Rap-led + sung chorus | rap carries most verses and development; singing provides the chorus or a brief refrain |
| Rap only | developed rap verses and rhythmic/spoken refrain without a forced sung chorus; use when the lane supports it |
| Alternating voices | distinct rapper and singer exchange sections, or a duet changes delivery while retaining one coherent song |

For an eight-song plan, one possible mix is two singing-led songs, two singing
rap songs, two rap-verse/sung-hook songs, one sung song with a rap bridge and
one rap-led or rap-only song. This is an example, not a fixed order or a
requirement to force every pattern into every playlist. Change the mix and
section placement across releases. Pure rap is welcome where it fits; a
piano-ballad collection need not contain a pure-rap track.

## Piano songs can contain a rap section

For some piano vocal songs, plan a restrained 8- or 16-bar rap/half-sung bridge
between developed sung sections. Others should remain fully sung. Rap changes
the vocal delivery, not the instrumentation: if the chosen lane is genuinely
piano-only, keep piano as the only accompaniment, without adding drums, 808s,
bass, pads or orchestra just because the voice raps. The same principle applies
to an explicitly acoustic-guitar-only song. Broader R&B/hip-hop or band lanes
may use the rhythm section and instruments that define that genre.

Example Style direction:

```text
Korean intimate piano vocal song, one acoustic upright piano only,
clear close-mic expressive lead, sung verse and chorus, one restrained
8-bar rhythmic rap bridge in the middle, return to a fully sung final chorus,
no drums, no bass, no synths, distinct natural singer identity
```

Write actual original lyrics under concise section cues, for example:

```text
[Verse 1: sung, close and conversational]
[full original verse lyrics]
[Chorus: fully sung, clear melodic hook]
[full original chorus lyrics]
[Verse 2: sung, new scene and developed story]
[full original second verse lyrics]
[Bridge: 8 bars of restrained rap, piano accompaniment only]
[original rhythmically phrased rap lyrics]
[Final Chorus: fully sung, emotional lift]
[full original final chorus lyrics]
```

Replace every placeholder before Create. Do not ask Suno to sing instructions.
For singing rap, specify melodic rhythmic delivery explicitly rather than only
adding `rap` to a generic ballad prompt. For rap-only, do not simultaneously
request an obligatory fully sung chorus. Keep all exclusion lists consistent:
remove `rap`/`spoken vocals` blockers for planned rap sections, while retaining
clarity, noise and genuinely forbidden-instrument exclusions.

## Record the plan before Create

In the local production plan, record each track's genre/subgenre, tempo and
groove, instrument palette, vocal configuration, section map, singer identity,
lead gender and lyric language/source. These are planning notes, not invented
API or CLI flags. Use existing backend fields only when they truly describe
the track; do not label a full-band rap-pop song `piano_only` to fit an old
three-family plan.

Vary at least two meaningful musical choices between adjacent new prompts:
groove/tempo, harmony, instrument palette, singer identity, delivery balance,
section order or emotional angle. A low-energy piano song should not dictate
the next track's genre, voice and structure by default. Follow the existing
intro quota and write enough developed lyrics for a full song.

Before Create, check the playlist plan contains singing rap and singing-led
material, the style and section cues agree, lyrics fit their source and
language, and the exclusions do not forbid the requested delivery. Record
intended configuration honestly; do not invent evidence about unheard audio
or introduce a new listening-QC or per-song approval gate. Standing audio
pre-approval and existing real-file integrity checks continue to apply.

Reuse must fit the same channel, intended genre/groove, emotional arc and
verified standard-v6 eligibility. Explicit piano-only/guitar-only releases
retain their literal palette; an orchestral concept retains a compatible
ensemble/theme. For broader lanes, compatible rap/sung combinations need not
fit the retired three-family taxonomy. BibliaCanto's passage/no-reuse rules
and HaruHaru's current freshness rules still apply. Generate only a genuine
shortfall and reach the existing one-hour target before render. Finish
already audio-full releases rather than generating extra songs for a quota.
