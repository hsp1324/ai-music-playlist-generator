# OpenClaw Vocal Arrangement Policy

This is the standing production direction for every **new song with singable
lyrics**, regardless of channel, language, scripture source, public genre
label, or visual concept. It applies to playlists and singles created after
2026-08-24. A direct human request for a different arrangement may override it
for that request only.

The purpose is to separate these channels from ordinary low-cost pop
production. New vocal music should sound as if it would require either a large,
expensive live ensemble or a deliberately exposed one-instrument performance.

Already generated, rendered, scheduled, or published audio is not
automatically discarded or regenerated. Apply this policy to new generation
and to an unstarted workspace. Preserve real existing assets unless the human
explicitly asks for a rebuild.

## The only three vocal arrangement families

Every new vocal release must choose exactly one of these families. Do not mix
families within one playlist.

### 1. Themed orchestral vocal

This is the primary and most frequent family. Put a clear lead vocal and
original lyrics over a genuinely large cinematic orchestra: layered strings,
brass, woodwinds, timpani and other orchestral percussion, with harp, piano,
ethnic acoustic instruments, or restrained choir color only when the selected
theme needs them. The orchestra must be a central musical identity, not a thin
string pad behind a normal pop, trap, EDM, or rock backing track.

Choose exactly one release-level theme before writing or generating tracks.
Valid theme families include:

- epic or heroic journey
- majestic or ceremonial
- lyrical, tender, or emotionally sweeping
- Nordic, fjord, winter, or runic-folk orchestral
- medieval court, castle, bardic, or pilgrimage orchestral
- dark fantasy, gothic, or tragic orchestral
- mythic, legendary, or ancient-world orchestral
- romantic, bittersweet, or tearful film-score orchestral
- celestial, wonder, creation, or starlight orchestral
- adventure, battle-march, victory, or homecoming orchestral

Keep all tracks inside that one theme and a coherent ensemble palette. Vary
tempo, mode, dynamics, vocal identity, melodic contour, solo instrument,
section shape, and emotional viewpoint without turning the playlist into a
sampler of unrelated eras or fantasy worlds. A Nordic playlist must not drift
into medieval court music halfway through; an intimate lyrical-orchestra
playlist must not become trailer battle music.

Useful Suno style shape:

```text
themed cinematic orchestral vocal song, full symphony orchestra, [ONE THEME],
prominent intelligible lead vocal, layered strings, expressive brass and
woodwinds, natural orchestral dynamics, expensive live-ensemble scale,
song-first verse/chorus/bridge structure, [DISTINCT SINGER IDENTITY]
```

Exclude ordinary beat-led production that would replace the orchestra, such
as `generic pop beat, trap drums, 808 bass, EDM drop, synth-pop backing,
lo-fi beat, rock band, small combo`, unless a human explicitly requests a
specific hybrid. Orchestral percussion is allowed when it serves the selected
theme. Do not default to worship, gospel, or church choir styling for
BibliaCanto.

### 2. Piano-only vocal

Use one acoustic grand, upright, or felt piano as the **only accompaniment**
under a clear lead vocal. The exposed voice, lyric, harmony, touch, silence,
and dynamics must carry the song.

Do not add drums, percussion, bass, guitar, strings, pads, synths, orchestra,
choir, Rhodes, organ, or ambient backing layers. A different piano register,
voicing, rhythmic pattern, room intimacy, and singer identity may vary by
track, but the playlist remains piano plus voice only.

Useful Suno style shape:

```text
intimate vocal song, solo acoustic [GRAND|UPRIGHT|FELT] piano accompaniment
only, no other instruments, exposed natural dynamics, clear close lead vocal,
song-first verse/chorus/bridge structure, [DISTINCT SINGER IDENTITY]
```

### 3. Guitar-only acoustic vocal

Use one acoustic guitar as the **only accompaniment** under a clear lead
vocal. Choose a coherent guitar palette for the release: steel-string
fingerstyle, gentle strumming, nylon-string intimacy, or another clearly
acoustic lane.

Do not add drums, percussion, bass, piano, strings, pads, synths, orchestra,
electric-guitar layers, or full-band backing. Vary picking pattern, capo/key,
register, dynamics, lyrical angle, and singer identity while keeping the same
release-level acoustic lane.

Useful Suno style shape:

```text
intimate acoustic vocal song, one [STEEL-STRING|NYLON-STRING] acoustic guitar
accompaniment only, no other instruments, natural fingerstyle or restrained
strumming, clear close lead vocal, [DISTINCT SINGER IDENTITY]
```

## Release rotation and channel identity

- Make orchestral vocal releases the plurality. The normal new-vocal rotation
  is `orchestral -> piano-only -> orchestral with a different theme ->
  guitar-only`, then repeat without reusing a recent orchestral theme.
- Channel and language identity still control lyrics, vocal delivery, public
  metadata, and visuals. They do not permit a fourth accompaniment family.
  Korean, Japanese, English, Spanish, BibliaCanto, and 불송 vocal songs must all
  use one of the same three families.
- Old detailed labels such as trap, R&B, synth-pop, dance-pop, Afropop, or
  neo-soul may classify legacy catalog items, vocal phrasing, or a lyrical
  sensibility, but they must not reintroduce a beat-led fourth arrangement into
  new vocal generation.
- Title and metadata should truthfully surface the audible family when useful:
  orchestral vocal, cinematic orchestra songs, piano vocal, piano ballad,
  acoustic guitar vocal, or natural localized equivalents.

## Reuse and one-hour fill

Reuse is strict for new vocal releases:

- Reuse only vocal tracks from the same channel and the same arrangement
  family.
- For orchestral releases, also require the same or a genuinely compatible
  orchestral theme and ensemble scale.
- Never use an instrumental Cinematic Pulse track as a vocal-song substitute.
  It may guide scale and instrumentation, but the new track must be generated
  as a real vocal song with matching lyrics.
- Do not backfill a new orchestral, piano-only, or guitar-only playlist with
  legacy trap, synth-pop, EDM, full-band, R&B-beat, generic pop, or unrelated
  acoustic tracks merely to reach one hour.
- If compatible reuse is insufficient, render and publish the coherent shorter
  release rather than weakening the identity.

## Required plan before Suno

Record these fields for the release before the first Create:

- `vocal_arrangement_family`: `orchestral`, `piano_only`, or
  `acoustic_guitar_only`
- `orchestral_theme`: required only for `orchestral`
- allowed instrument palette
- forbidden instruments and beat types
- lyric language and release-level emotional arc
- track-by-track singer identity and vocal gender control

For every track, put the chosen family and its hard instrumentation boundary in
the Style field. Also keep the existing distinct singer-identity cue in both
Style and Lyrics. Do not rely on a title or lyric cue alone to make an
orchestral song; the actual Style prompt must demand the full ensemble.

## Approval check

Before accepting, uploading, reusing, or rendering a vocal track:

- It has real singable lyrics and an audible lead vocal.
- Its accompaniment belongs to the selected one of three families.
- Piano-only and guitar-only tracks contain no audible extra backing ensemble.
- Orchestral tracks sound genuinely large-scale and match the one selected
  release theme.
- The lyrics file belongs to that exact audio output; reject a title/lyrics
  mismatch or language mismatch.
- Adjacent new tracks do not repeat the same singer identity, melodic shape,
  or emotional angle.
