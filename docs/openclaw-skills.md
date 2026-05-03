# OpenClaw Skills For AI Music Releases

Use this document as the instruction source when asking OpenClaw to create or run release-production skills for this repo.

OpenClaw must run commands on the Oracle VM from:

```bash
cd /opt/ai-music-playlist-generator
```

Use the local API or the helper script. Do not use the public `https://ai-music...sslip.io` URL because it is protected by Google login.

```bash
export AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api
```

## Shared Rules

- Never approve, reject, render, publish, or upload to YouTube unless the human explicitly asks.
- Before opening Suno or generating audio, create or select the target app workspace/release. Use one Single Release workspace for one standalone song candidate set, and one Playlist Release workspace for one playlist/mix. Do not scatter one Suno request or one playlist run across multiple workspaces.
- If continuing existing work, run `scripts/openclaw-release list-releases` and use the existing `release.id` with `--release-id`. If starting fresh, first run `scripts/openclaw-release create-release` and keep the returned `release.id`; then generate Suno audio and upload everything into that same `release.id`.
- Do not wait until after Suno generation to create the app workspace. The release id should exist before the first Suno prompt is submitted so all later audio, lyrics, style, cover, thumbnail, and video assets have one clear destination.
- OpenClaw creates audio candidates and uploads them to the app review queue.
- If cover art is ready with the audio, upload the cover in the same command with `--cover`.
- Human review happens in Slack or the web UI.
- Single Release means one final song, but it may contain up to two review candidates from Suno.
- If two Suno candidates from one prompt are both good, publish them as two separate Single Releases. Do not combine them into one song.
- Playlist Release normally means automatic private publishing. If the human asks for a playlist production run, upload generated tracks as already approved, render everything, generate/approve metadata, and upload privately to YouTube.
- When uploading audio, include lyrics or song-content notes with `--lyrics` or `--lyrics-file` whenever available. For instrumental work, prefer non-sung arrangement notes over an empty lyrics field so later metadata/visual work can understand the track.
- BGM/background/lofi/study/sleep/cafe music defaults to instrumental/no vocals unless the human explicitly asks for vocals. For Soft Hour Radio or other instrumental BGM, do not leave the Suno lyrics/custom-lyrics field completely blank. Write detailed non-sung instrumental arrangement notes, then save and upload the same notes with `--lyrics` or `--lyrics-file`.
- Instrumental arrangement notes must be concrete enough to steer Suno away from accidental vocals. Include: a no-vocal guardrail, tempo/feel, instrument palette, section-by-section musical flow, dynamics/transitions, and negative vocal constraints. Do not write singable lyric lines. Example shape:
  `[Instrumental only - no vocals, no humming, no spoken words]`
  `[Tempo/feel] 76 BPM, relaxed swing, warm late-night cafe mood`
  `[Palette] felt piano lead, nylon guitar answers, soft Rhodes pads, brushed drums, upright bass, subtle rain ambience`
  `[Intro] piano motif alone, wide space, no percussion`
  `[Main A] brushed drums enter, guitar answers piano every 4 bars, bass stays simple`
  `[Main B] Rhodes pad opens, piano melody becomes slightly brighter, no choir or vocal pad`
  `[Bridge] drums drop to rim clicks, guitar harmonics, gentle tension then release`
  `[Outro] return to solo piano and rain ambience, slow fade`
  `[Avoid] vocals, humming, spoken words, choirs, vocal chops, lyric-like phrases`
- J-pop/K-pop/pop/Japanese pop/anime-pop releases default to vocal songs with lyrics. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, and the requested language or natural English/Korean lyrics for generic pop. Do not make these instrumental, no-vocal, lyricless, or hum-only unless the human explicitly asks for instrumental/BGM/lofi/no vocals. For every pop-family track, create or capture the final lyrics and upload them with `--lyrics` or `--lyrics-file`. The helper rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- When uploading audio, include the Suno style/settings with `--style` whenever available. This is stored with the track for future cover, thumbnail, loop-video, metadata, and remake work.
- Within one release, intentionally vary every generated track. Do not reuse the exact same Suno prompt, lyrics theme, chorus hook, title pattern, or style string across multiple tracks unless the human explicitly asks for a uniform album. Keep the release coherent by genre/mood, but vary tempo, energy, instruments, rhythm feel, vocal tone, season/time/place imagery, lyrical story, and hook.
- For playlist releases, prefer one `--style` per `--audio` and one `--lyrics-file` per vocal track. Shared style is allowed only for a narrow BGM/instrumental set where the human wants consistency; even then, vary titles and prompts.
- For J-pop/K-pop/pop playlists, each song needs its own original lyrics and chorus concept. Do not create multiple songs with near-identical verse/pre-chorus/chorus wording, repeated phrases, or only swapped nouns.
- Always return the final JSON result and mention `release.id` plus uploaded `track.id` values.
- If a command fails, stop and report the exact error. Do not retry blindly more than once.
- For YouTube title/description/tag writing, use [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
- Every YouTube description, including `ko`, `ja`, and `en` localized descriptions, must end with a visible public hashtag line. The `--tags` option is separate API metadata and does not create visible hashtags in the description.
- For playlist publishing, choose the YouTube channel by release concept:
- Default background/cafe/sleep/study/chill playlists go to `Soft Hour Radio`.
- Japan-related releases go to `Tokyo Daydream Radio`. Treat these as Japan-related when the title, prompt, tags, or concept includes Japan, Tokyo, Shibuya, Shinjuku, Japanese lofi, city pop, J-pop, anime, vaporwave, 일본, 도쿄, 시티팝, 애니, 제이팝, 日本, 東京, 渋谷, 新宿, アニメ, or シティポップ.
- Do not use `MusicSun` unless the human explicitly requests it.
- `scripts/openclaw-release auto-publish-playlist` can infer the channel when `--youtube-channel-title` is omitted, but OpenClaw should pass `--youtube-channel-title "Tokyo Daydream Radio"` when the Japan routing intent is clear.
- YouTube visibility must stay private. The app uses `AIMP_YOUTUBE_PRIVACY_STATUS=private`; do not make a public upload from OpenClaw.
- YouTube metadata supports localized title/description for `ko`, `ja`, and `en`. For `Tokyo Daydream Radio` or any Japan/J-pop release, OpenClaw must write all three versions: Korean, Japanese, and English. Use Korean as the default metadata (`--title`, `--description-file`) and also pass `--ko-title`, `--ko-description-file`, `--ja-title`, `--ja-description-file`, `--en-title`, and `--en-description-file` to `scripts/openclaw-release approve-metadata`.
- Playlist/BGM YouTube titles must include listening use cases in the title itself, such as study, work, walk, drive, sleep, reading, or rest. Do not write only a mood/genre title.
- In Korean YouTube titles/descriptions/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Prefer `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- In Japan/J-pop localized descriptions, timestamped tracklists must use Japanese titles in the Korean/default description with Korean translations in parentheses, Japanese titles only in the Japanese description, and English translated titles only in the English description. Keep the same timestamps and order in all languages.
- For releases one hour or longer, use `HH:MM:SS` timestamps for the whole tracklist, starting at `00:00:00`; this avoids one-hour-plus YouTube timestamp links failing to activate.
- Do not leave trailing `A` / `B`, `1` / `2`, `Morning` / `Evening`, or similar pair labels in uploaded playlist track titles.
- Treat every playlist track as its own song title. If Suno returns two outputs from one prompt, rename both as independent editorial titles, not as variants of the same title.
- Full playlist publishing needs two 16:9 images:
- `cover`: clean video visual shown during playback. It should look good for the full video duration and must be text-free for releases that use a moving loop video.
- `thumbnail`: YouTube click thumbnail. It should include short readable text such as `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `TOKYO NIGHT`, `CITY POP`, or `J-POP`, plus a small brand mark for the selected channel. Do not add duration text such as `1 HOUR`, `60 MIN`, `1時間`, or time badges.
- Asset generation order is mandatory: create the final clean cover first, then create the YouTube thumbnail as an image-to-image edit/reference derivative of that exact final cover. Do not create the thumbnail as a fresh unrelated image.
- When generating the thumbnail from the cover reference, preserve the exact three subjects, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add click text, channel branding, crop/contrast/readability adjustments, and small layout refinements. Example: if the right subject has a red cloak in the cover, the thumbnail must keep that cloak red.
- If the generated thumbnail changes character identity, clothing color, subject count, subject placement, or core background compared with the cover, reject it and regenerate before uploading.
- Preferred thumbnail format: full-bleed image background, no card or panel, large bottom-left genre/mood text, and a smaller channel-brand line directly below. For Japan/J-pop releases, follow the approved Tokyo Daydream Radio treatment: large `J-POP` text and smaller `TOKYO DAYDREAM RADIO` directly beneath it. Keep this exact two-line brand system for Tokyo city, forest/nature, and beach versions so the channel stays visually consistent.
- Default channel visual signature: every cover, YouTube thumbnail, and loop-video first frame should show exactly three people walking forward away from the viewer. The camera/viewer sees their backs and backs of heads as they walk into the scene. Do not show front-facing faces as the main composition.
- Human visual requests override the default signature. If the human asks for a specific scene, subject, action, camera angle, object, animal, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video instead of forcing the three-people-walking default.
- When the default signature is used, the three people must stay centered in thumbnails. Text must not push them to the side, crop them, cover them, or make them feel secondary. Place text in safe negative space, usually lower-left or lower area, while preserving the central three-person walking silhouette.
- When a human visual request overrides the default, keep the requested subject/action/composition centered and visually important in thumbnails; text must fit around the requested composition rather than replacing it.
- The background can change by genre and channel mood: Tokyo street, cafe alley, forest path, beach, moonlit road, rainy city, abstract dreamscape, etc. The default signature is three backs walking forward into the world, unless the human requests a different visual concept.
- All static images and Dreamina/Seedance loop clips must look animated, anime, illustrated, or stylized. Do not make photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- Generate static images with OpenAI GPT Image models, not Dreamina. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the OpenAI/Image tool environment. Do not use Dreamina for static image generation. Do not assume the OpenAI API is free; use the available Codex/ChatGPT image tool if that is the operator-approved path, or use API billing/credentials when explicitly configured.
- Use Dreamina/Seedance only for the moving visual clip. If Dreamina/Seedance can create a visual motion clip, OpenClaw should generate exactly one 8 second MP4 and pass it with `--loop-video`. The app will repeat it smoothly during final video render. OpenClaw should not render a one-hour video itself.
- Keep these assets separate: `--thumbnail` is the click image with text, `--cover` is the clean text-free playback visual, and `--loop-video` is the 8 second moving visual used inside the rendered video. Do not use the text thumbnail as the video visual.
- The 8 second loop video must visually match the thumbnail's scene and brand, but it must start from the clean text-free cover or a separate clean text-free first-frame image. Do not use the final text thumbnail as the Dreamina/Seedance first-frame reference, because generated video often makes text flicker, disappear, or reappear during the loop. If the only available first-frame image has text, regenerate a clean no-text version before Dreamina/Seedance.
- For browser-based Dreamina generation, OpenClaw should use `https://dreamina.capcut.com/ai-tool/home/`. Select Seedance/Dreamina `2.0 Fast`, first/last-frame mode if the UI asks, provide the first frame only, leave the last frame empty, set ratio to `16:9` when selectable, quality to `720p`, duration to exactly `8 seconds`, then create/download the MP4, save it locally, and pass the downloaded file path as `--loop-video`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set duration, ratio, and quality only through Dreamina controls. The default prompt should ask for one continuous forward-moving shot with no repeated segment; if the human requested a different motion/camera concept, use that requested motion instead while still avoiding repeated segments. The app handles the final loop/crossfade.

## Skill 1: Single Release Candidate Set

Use this skill when the user asks for one standalone song/single.

### Goal

Generate one Single Release candidate set. Suno normally returns two candidate songs for one prompt. Upload both candidates into the same Single Release so the human can listen and choose. If both are good, the human may approve both; the app splits the second approved candidate into its own Single Release instead of combining the songs. If both are bad, the human rejects both; the app archives that release automatically and it can be restored later.

### OpenClaw Skill Prompt

```text
You are creating one Single Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use the local app API only through scripts/openclaw-release.

Goal:
- Create or select one Single Release workspace before opening Suno or generating audio.
- Generate one standalone song/single.
- If Suno returns two candidates, upload both candidates to the precreated Single Release.
- If only one usable candidate exists, upload one candidate to the precreated Single Release.
- If two candidates come from one Suno prompt, they can share the original prompt/style, but give them independent editorial titles and preserve any candidate-specific lyrics, style notes, or differences.
- If candidate cover images exist, upload them with the audio candidates.
- If candidate lyrics or instrumental arrangement notes exist, upload them with the audio candidates using `--lyrics` or `--lyrics-file`. For instrumental/BGM candidates, use non-sung arrangement notes rather than an empty field when possible. For J-pop/K-pop/pop/Japanese pop/anime-pop candidates, lyrics are expected by default unless the human explicitly asked for instrumental/no-vocal.
- If the Suno style/settings are known, upload them with `--style`. Use one shared `--style` or one per candidate.
- Clean awkward trailing A/B or 1/2 labels from uploaded candidate titles. If titles become duplicated, make them naturally unique without using pair labels.
- When the human approves one candidate, its uploaded cover is automatically registered as the release cover. If the human approves both candidates, the second approved candidate becomes a separate Single Release.
- The human still reviews/approves the cover before video rendering.
- Do not approve, reject, render, publish, or upload to YouTube.
- Return release.id, release.title, and all uploaded track ids.

Before opening Suno, run this first:

scripts/openclaw-release create-release \
  --workspace-mode single \
  --release-title "RELEASE_TITLE" \
  --description "Short concept for this single candidate set"

Keep the returned `release.id`. All Suno outputs from this prompt must be uploaded to that same release.

After audio generation, run one of these:

For two Suno candidates:
scripts/openclaw-release upload-single-candidates \
  --release-id RELEASE_ID \
  --audio ABSOLUTE_AUDIO_PATH_A \
  --audio ABSOLUTE_AUDIO_PATH_B \
  --cover ABSOLUTE_COVER_PATH_A \
  --cover ABSOLUTE_COVER_PATH_B \
  --lyrics-file ABSOLUTE_LYRICS_PATH_A \
  --lyrics-file ABSOLUTE_LYRICS_PATH_B \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

For one candidate:
scripts/openclaw-release upload-single-candidates \
  --release-id RELEASE_ID \
  --audio ABSOLUTE_AUDIO_PATH \
  --cover ABSOLUTE_COVER_PATH \
  --lyrics-file ABSOLUTE_LYRICS_PATH \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

If no cover image is ready, omit every `--cover` argument. If one shared cover should be used for both candidates, provide one `--cover`; if each candidate has a different cover, provide one `--cover` per `--audio` in the same order. If lyrics/content are truly unavailable, omit `--lyrics`/`--lyrics-file`; the app stores an empty lyrics field. For instrumental/BGM candidates, prefer a non-sung arrangement note file instead of omitting lyrics. For J-pop/K-pop/pop/Japanese pop/anime-pop candidates, do not treat missing lyrics as normal; generate or capture original lyrics unless the human explicitly requested instrumental/no-vocal. If style/settings are not available, omit `--style`; otherwise always provide it.

Report the command output JSON. The human will approve one candidate, approve both candidates as separate singles, or reject both in Slack or the web UI.
```

### Required Output

OpenClaw should finish with a concise report:

```text
Single release candidates uploaded.
release.id: ...
release.title: ...
tracks:
- ...
- ...
Next: human should approve one candidate, approve both candidates as separate Single Releases, or reject both.
```

### Safety Checks

- Do not create two separate Single Releases before human review. Both candidates from one Suno request should start in one review release.
- Do not upload more than two candidates to a Single Release.
- Do not upload cover images separately after this command if they were already uploaded with the candidate audio.
- A Single Release can publish only one selected track. If another candidate is approved later, the app creates a separate Single Release for it.
- If both candidates are rejected later, the app archives the release automatically. Do not manually delete it.

## Skill 2: Automatic Private Single Publisher

Use this skill when the user explicitly asks OpenClaw to create one standalone song/single and publish it privately to YouTube.

### Goal

Create one Single Release for one final song, generate the needed audio, auto-approve exactly one usable candidate, render the final single video, approve metadata, and upload privately to YouTube on the correct channel.

This is different from `Single Release Candidate Set`: that skill stops for human candidate review. Use this automatic publisher only when the human says to publish/upload the single.

For Japan, Tokyo, city pop, J-pop, anime, Japanese lofi, or similar Japan-themed singles, publish to `Tokyo Daydream Radio`.

### OpenClaw Skill Prompt

```text
You are creating and privately publishing one Single Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use scripts/openclaw-release only.

Goal:
- Create or select one Single Release workspace before opening Suno or generating audio.
- Generate an original standalone song/single.
- If the human references an existing artist such as YOASOBI, treat it only as mood/style guidance. Do not copy melodies, lyrics, titles, or a specific song.
- For J-pop/K-pop/pop/Japanese pop/anime-pop singles, generate a vocal song by default with original lyrics and a clear verse/pre-chorus/chorus structure. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, and the requested language or natural English/Korean lyrics for generic pop. Do not set instrumental/no-vocal unless the human explicitly asks for it.
- If Suno returns two usable candidates and the human asked for full automation, publish each good candidate as a separate Single Release by running this skill once per song.
- If publishing two good candidates from the same Suno request, treat them as separate releases after selection: give each one a distinct title, description angle, thumbnail wording, and preserved lyric/style context.
- Before upload, replace awkward trailing A/B, 1/2, or pair-style labels with independent song titles.
- Preserve lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available. For BGM/background/instrumental tracks, write and upload non-sung instrumental arrangement notes when possible; J-pop/K-pop/pop/Japanese pop/anime-pop songs should not have empty lyrics unless the human explicitly requested an instrumental/no-vocal track.
- If this is a J-pop/K-pop/pop/anime-pop single and there is no final lyric text, stop and generate/capture original lyrics before calling `auto-publish-single`.
- Preserve Suno style/settings during upload. Pass `--style "SUNO_STYLE_OR_SETTINGS"` for each song.
- A final clean 16:9 cover image is required. For moving-video releases, this cover also acts as the clean Dreamina/Seedance first-frame reference and must not contain text.
- A separate YouTube thumbnail image with readable text is required. For J-pop/Japan singles, use the approved Tokyo Daydream Radio pattern: large `J-POP` with smaller `TOKYO DAYDREAM RADIO` beneath it. Use the same brand system for Tokyo/city, forest/nature, and beach variants. Do not add duration text or badges such as `1 HOUR`, `60 MIN`, or `1時間`.
- Apply the default channel visual signature to both static images unless the human requested a different visual concept: exactly three people seen from behind, walking away from camera into the scene. The cover should be the clean version; the thumbnail must be generated from that final cover as a reference/edit derivative, using the same composition plus readable click text and channel branding. In the thumbnail, keep the main requested/default subject centered; text must fit around the composition rather than moving the subject sideways.
- Before uploading the thumbnail, compare it against the cover. Character count, subject positions, silhouette, outfit colors, lighting, palette, and core background must remain visually continuous. Regenerate the thumbnail if it looks like a different scene or changes details such as cloak/shirt colors.
- Keep the visual style animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- Generate both static images with OpenAI GPT Image models, not Dreamina. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model. Dreamina is only for the moving 8 second MP4. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- Generate exactly one 8 second Dreamina/Seedance MP4 before publish when moving visuals are requested.
- Use the clean text-free cover or a separate clean text-free visual signature image as the first-frame/start-frame reference for Dreamina/Seedance so the video opening matches the thumbnail scene without animating any text. By default the frame should show the three people from behind walking into the scene; if the human requested a different visual concept, the first frame and motion prompt must follow that requested concept instead. Do not use the text thumbnail, Omni Reference, or a last-frame reference.
- The thumbnail, cover, and loop video are three different assets. The thumbnail has readable text; the cover is clean; the loop video must remain clean with no subtitles, lyrics, UI, logos, brand text, title text, or other baked-in text.
- If using browser automation, open `https://dreamina.capcut.com/ai-tool/home/`, select `2.0 Fast`, use first/last-frame mode with only the first frame provided, do not use Omni Reference, leave the last frame empty, set `16:9`, `720p`, and `8 seconds` when selectable, create/download the MP4, confirm the local file exists, and pass that absolute path as `--loop-video`.
- Do not include duration, ratio, or quality words in the Dreamina prompt. Do not write `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. Those are either UI settings or app-render responsibilities.
- Default Dreamina prompt shape: `Use the uploaded clean text-free first-frame image as the exact starting frame. Create one continuous forward-moving animated music visualizer shot. Keep the channel signature: exactly three people seen from behind, walking away from the camera into the scene. The viewer should see backs and backs of heads, not front-facing faces. The motion must progress forward naturally for the full clip. Do not repeat any segment. Do not ping-pong or restart motion. Preserve the opening composition, lighting, palette, and illustrated/anime style. Adapt the background and atmosphere to the release concept. Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion. Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no text, no subtitles, no logos, no UI, no extra people or characters.`
- If the human provided a specific visual/video request, replace the default three-people-walking prompt details with the requested subject/action/composition while keeping the safety/quality constraints: one continuous shot, no repeated segment, no ping-pong, preserve first-frame composition/style, stable composition, no text/subtitles/logos/UI, no extra unwanted subjects.
- Render audio/video, generate and approve YouTube metadata, and upload privately.
- Publish Japanese/J-pop/Tokyo content to `Tokyo Daydream Radio`.
- Return the command output JSON, including release.id, uploaded track ids, YouTube video id, and output paths.

First, before opening Suno, create the destination release:

scripts/openclaw-release create-release \
  --workspace-mode single \
  --release-title "SINGLE_RELEASE_TITLE" \
  --description "Short concept description for metadata generation."
```

### Run The Full Automation

After one generated audio file, final cover, text thumbnail, and optional 8 second loop video are ready, run one command:

```bash
scripts/openclaw-release auto-publish-single \
  --release-id RELEASE_ID \
  --description "Short concept description for metadata generation." \
  --audio ABSOLUTE_AUDIO_PATH \
  --title "INDEPENDENT_TRACK_TITLE" \
  --lyrics-file ABSOLUTE_LYRICS_PATH \
  --cover ABSOLUTE_FINAL_CLEAN_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_TEXT_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_DREAMINA_SEEDANCE_8_SECOND_MP4 \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --tags "comma, separated, tags" \
  --youtube-channel-title "Tokyo Daydream Radio"
```

Pass exactly one `--audio`, one `--title`, one optional `--lyrics-file`, and one `--style`. If Suno produced two good songs, prepare separate cover/thumbnail/loop-video assets and run `auto-publish-single` twice with different release titles.

Do not omit `--cover` or `--thumbnail` for a full private single publish run. If either asset is not ready, stop after audio creation and report the missing asset. The app's local draft cover is only a placeholder for manual review, not acceptable for automatic YouTube upload.

`--loop-video` is optional but preferred when the human wants moving visuals. If provided, it should be exactly 8 seconds. The app uses the actual uploaded clip length and repeats it smoothly during final video rendering.

### Required Output

OpenClaw should finish with:

```text
Private single upload completed.
release.id: ...
release.title: ...
uploaded tracks:
- ...
youtube_video_id: ...
youtube_channel: SELECTED_CHANNEL_TITLE
privacy: private
Next: human should listen to the private YouTube upload and change visibility to Public only if it is good.
```

### Safety Checks

- Use `auto-publish-single` only when the human explicitly asks for publishing/uploading the single.
- Do not upload public. The final upload must be private.
- Do not pass two audio files to one `auto-publish-single` command. One command equals one YouTube single.
- If two Suno candidates are both good, create and publish two separate Single Releases with separate assets.
- Do not use pair labels like A/B or 1/2 in final titles.
- Do not publish without a final clean cover, a separate text thumbnail, and the correct YouTube channel selection.
- For Japanese/J-pop/Tokyo singles, pass `--youtube-channel-title "Tokyo Daydream Radio"` explicitly.

## Skill 3: Automatic Private Playlist Publisher

Use this skill when the user asks for a playlist, mix, compilation, or approximately one-hour release and expects OpenClaw to finish the private YouTube upload.

### Goal

Create one Playlist Release, generate enough tracks, upload them as approved tracks, render audio/video, generate and approve metadata, and upload the result privately to YouTube on the correct channel.

Use `Soft Hour Radio` for normal background/cafe/sleep/study/chill releases. Use `Tokyo Daydream Radio` for Japan, Tokyo, city pop, J-pop, anime, Japanese lofi, or similar Japan-themed releases.

The human does not review every playlist track before rendering. The human reviews the final private YouTube upload later and only intervenes if something sounds wrong.

### Important Duration Rule

Playlist uploads are auto-approved, so `workspace.actual_duration_seconds` becomes the source of truth after upload.

Generate enough material before publishing:

- Target at least `3600` seconds for a one-hour playlist.
- A practical buffer of `3900` seconds is acceptable.
- Do not publish under target unless the human explicitly says a shorter playlist is acceptable.

### OpenClaw Skill Prompt

```text
You are creating and privately publishing a one-hour Playlist Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use scripts/openclaw-release only.

Goal:
- Create or select one Playlist Release workspace before opening Suno or generating audio.
- Generate songs in batches until the usable duration is at least 3600 seconds, preferably around 3900 seconds.
- For BGM/background/lofi/study/sleep/cafe playlist requests, generate instrumental/no-vocal tracks by default unless the human explicitly asks for vocals. Do not leave the Suno lyrics/custom-lyrics field blank for Soft Hour Radio instrumental work; write detailed non-sung arrangement notes with the no-vocal guardrail, tempo/feel, instrument palette, sections, dynamics, transitions, and avoid-list described in the shared rules.
- For J-pop/K-pop/pop/Japanese pop/anime-pop playlist requests, generate vocal songs by default with original lyrics for each track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, and the requested language or natural English/Korean lyrics for generic pop. Do not make the batch instrumental/no-vocal unless the human explicitly asks for instrumental/BGM/lofi/no vocals.
- For every new Suno request in a playlist run, write a distinct prompt/style/lyrics plan before generating. Keep the channel/release mood consistent, but vary one or more of: tempo, drum pattern, bass movement, synth/guitar/piano texture, vocal energy, emotional angle, scene imagery, lyrical storyline, chorus hook, and song structure.
- If Suno returns two outputs from one request, use both outputs as separate playlist tracks when both are usable.
- Before upload, replace awkward trailing A/B, 1/2, or pair-style labels with independent song titles.
- Preserve each track's lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available, because good playlist tracks may later be republished as standalone singles and OpenClaw needs this context for thumbnail/loop-video generation. For J-pop/K-pop/pop/Japanese pop/anime-pop playlist tracks, lyrics are expected and should be uploaded for every track. For BGM/background/instrumental tracks, upload non-sung instrumental arrangement notes instead of leaving the content blank whenever possible.
- If this is a J-pop/K-pop/pop/anime-pop playlist and any track lacks final lyric text, stop and generate/capture original lyrics before calling `auto-publish-playlist`. Do not publish a lyricless pop-family playlist unless the human explicitly says it is BGM/instrumental/no-vocal.
- Preserve the Suno style/settings for each track. Pass one shared `--style` if the whole batch used the same style, or one `--style` per `--audio` when styles differ.
- Prefer track-specific `--style` values for playlist tracks. If a shared style is used, add track-specific prompt/title/lyrics variation so the playlist does not sound like one song repeated with minor edits.
- If Suno gives two outputs from the same prompt, do not name them like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`.
- Give each output a standalone title that fits the mood, for example `Saffron Motion` and `Open Road Cadence` instead of `Highway Saffron A` and `Highway Saffron B`.
- Upload all usable tracks to one Playlist Release.
- Upload tracks as auto-approved, not pending human review.
- If using `scripts/openclaw-release upload-audio` for individual playlist tracks, do not pass `--pending-review`; playlist uploads auto-approve by default.
- A final 16:9 cover image is required before YouTube upload.
- A separate YouTube thumbnail image with readable text is required before YouTube upload.
- Generate or obtain the final cover image before running the full publish command, then pass it with `--cover`. Use OpenAI GPT Image models for static image creation, not Dreamina. For moving-video releases, the cover must be clean and text-free because it is the Dreamina/Seedance first-frame reference.
- Generate or obtain a separate text thumbnail before running the full publish command, then pass it with `--thumbnail`. Use OpenAI GPT Image models for static image creation, not Dreamina. The thumbnail must be created from the final clean cover as an image reference/edit, not as a new independent scene. For J-pop/Japan releases, use the approved Tokyo Daydream Radio layout: large `J-POP` plus smaller `TOKYO DAYDREAM RADIO`, including forest/nature and beach variants. Do not add duration text or badges such as `1 HOUR`, `60 MIN`, or `1時間`.
- Apply the default channel visual signature to both images unless the human requested a different visual concept: exactly three people seen from behind walking away from the camera into the scene. Use a clean text-free version for `--cover`; use the same centered default/requested composition plus readable title/channel text for `--thumbnail`. In thumbnails, keep the main subject centered and place text around it in negative space; never move the main subject to one side just to make room for text.
- The cover and thumbnail should look like the same release art package. Preserve the same characters, poses, clothing colors, background, lighting, palette, and camera angle. If the thumbnail changes those details, regenerate it before uploading.
- Keep every generated visual animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- Optionally generate an 8 second Dreamina/Seedance 2.0 motion clip before running the full publish command, then pass it with `--loop-video`.
- The thumbnail, cover, and loop video are three different assets. The thumbnail must contain readable click text; the cover and loop video must stay clean and text-free. This prevents Dreamina/Seedance from making letters disappear, reappear, or flicker during the 8 second clip.
- Use the clean text-free cover or a separate clean text-free signature image as the visual starting reference for Dreamina/Seedance image-to-video generation. By default, the first shot of the 8 second loop video should show the same three-person back-view walking composition as the thumbnail/cover, and the video motion should keep them walking forward away from the viewer. If the human requested a different video concept, use that requested subject/action/composition for the cover, thumbnail, and loop video. Do not use the text thumbnail as the video first frame.
- For Dreamina motion clips, set duration/ratio/quality in Dreamina controls, not in the prompt. The default prompt should request `animated/anime/illustrated style`, `exactly three people seen from behind walking away from camera`, `one continuous forward-moving video shot`, `smooth gentle motion`, `subtle camera-follow movement from behind`, `stable composition`, `no repeated segment`, `no text`, `no subtitles`, `no logos`, `no photorealism`, and `no hard cuts`. If the human requested a different visual/video concept, replace only the subject/action/camera details with that request and keep the remaining continuity/no-text/no-repeat/no-hard-cut constraints. Do not ask for a matching last frame; the app handles smooth repeat with forward crossfade rendering.
- Do not include `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. These terms cause Seedance/Dreamina to sometimes generate a shorter repeated segment inside the clip.
- If using browser automation instead of an API, open `https://dreamina.capcut.com/ai-tool/home/`, choose Seedance/Dreamina `2.0 Fast`, choose the first/last-frame workflow if the UI requires a mode, upload only the first-frame image, leave the last frame empty, do not use Omni Reference, set ratio `16:9`, quality `720p`, duration exactly `8 seconds`, create the video, download the MP4, confirm the local file exists, and use that absolute path for `--loop-video`.
- If Dreamina login, CAPTCHA, payment, or human approval blocks browser automation, stop and report the exact blocked step instead of skipping the loop video.
- Do not let the app's local draft cover stand in for final cover art.
- Render playlist audio.
- Approve the cover.
- Render video.
- Generate and approve YouTube metadata.
- Publish privately to the selected YouTube channel. Use `Tokyo Daydream Radio` for Japan-related releases; otherwise use `Soft Hour Radio`.
- Return the command output JSON, including release.id, uploaded track ids, YouTube video id, and output paths.

First, before opening Suno or submitting the first playlist prompt, create the destination release:

scripts/openclaw-release create-release \
  --workspace-mode playlist \
  --release-title "PLAYLIST_TITLE" \
  --target-seconds 3600 \
  --description "Short mood/use-case description for metadata generation."
```

### Slack Command Example

If the human gives this instruction through Slack, interpret it as approval to run the full private playlist automation:

```text
카페 피아노 1시간 플레이리스트 만들어서 Soft Hour Radio에 private으로 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
마지막 private 업로드가 끝나면 YouTube video id만 알려줘.
```

Japan routing example:

```text
도쿄 시티팝 1시간 플레이리스트 만들어서 Tokyo Daydream Radio에 private으로 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
썸네일에는 큰 J-POP과 작은 TOKYO DAYDREAM RADIO를 같은 위치/스타일로 넣어줘.
```

### Run The Full Automation

After all generated audio files are ready, run one command:

```bash
scripts/openclaw-release auto-publish-playlist \
  --release-id RELEASE_ID \
  --description "Short mood/use-case description for metadata generation." \
  --audio ABSOLUTE_AUDIO_PATH_01 \
  --title "INDEPENDENT_TRACK_TITLE_01" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_01 \
  --style "SUNO_STYLE_OR_SETTINGS_01" \
  --audio ABSOLUTE_AUDIO_PATH_02 \
  --title "INDEPENDENT_TRACK_TITLE_02" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_02 \
  --style "SUNO_STYLE_OR_SETTINGS_02" \
  --audio ABSOLUTE_AUDIO_PATH_03 \
  --title "INDEPENDENT_TRACK_TITLE_03" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_03 \
  --style "SUNO_STYLE_OR_SETTINGS_03" \
  --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_DREAMINA_SEEDANCE_LOOP_MP4 \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags" \
  --youtube-channel-title "SELECTED_CHANNEL_TITLE"
```

Do not omit `--cover` or `--thumbnail` for a full private publish run. If either asset is not ready, stop after audio upload/render and report the missing asset. The app's local draft cover is only a placeholder for manual review, not acceptable for automatic YouTube upload.

`--loop-video` is optional but preferred when the human wants moving visuals. If it is omitted, the app renders a still-image visual from `--cover`. If it is provided, the app uses the actual uploaded clip length, normally 8 seconds, creates a smooth 2 second forward crossfade loop, and repeats it to match the full audio duration. The loop transition should dissolve from one forward pass into the next instead of hard-cutting.

If the release is Japan-related, set `--youtube-channel-title "Tokyo Daydream Radio"`. Otherwise set `--youtube-channel-title "Soft Hour Radio"` or omit the flag and let the helper infer the default.

If the run is continuing an existing release, use `--release-id RELEASE_ID` instead of creating a new title.

Only use `--force-under-target` if the human explicitly accepted a shorter playlist.

### Required Output

OpenClaw should finish with:

```text
Private playlist upload completed.
release.id: ...
release.title: ...
uploaded tracks:
- ...
- ...
youtube_video_id: ...
youtube_channel: SELECTED_CHANNEL_TITLE
privacy: private
Next: human should listen to the private YouTube upload and change visibility to Public only if it is good.
```

### Safety Checks

- Keep all generated tracks for the same playlist in one Playlist Release.
- Do not create a Single Release for playlist candidates.
- Do not use the `MusicSun` channel for playlist publishing unless the human explicitly overrides the channel.
- Do not upload public. The final upload must be private.
- Do not publish if the selected YouTube channel is not connected. Current intended routing is `Soft Hour Radio` for general releases and `Tokyo Daydream Radio` for Japan-related releases.
- Do not publish if final cover art was not uploaded. `auto-publish-playlist` requires `--cover` unless a final uploaded cover already exists on the release.
- Do not publish if final YouTube thumbnail art was not uploaded. `auto-publish-playlist` requires `--thumbnail` unless a final uploaded thumbnail already exists on the release.
- Do not use Dreamina to create static cover or thumbnail images. Use OpenAI GPT Image models for static images, then use Dreamina only to animate the clean text-free cover or clean first-frame image into an 8 second loop video.
- Do not use `--allow-generated-draft-cover` unless the human explicitly says a placeholder cover is acceptable for this upload.
- Do not use `--allow-cover-as-thumbnail` unless the human explicitly says one image is acceptable for both the video visual and YouTube thumbnail.
- Do not create a long one-hour MP4 in OpenClaw. Upload only the 8 second loop clip with `--loop-video`; the app handles the long render.
- Do not add text, subtitles, lyric overlays, logos, brand marks, or UI elements inside the loop video. The default visual action is three people walking forward away from the viewer, but an explicit human visual/video request overrides that default. If the first-frame reference has baked-in text, regenerate a clean no-text first frame before using Dreamina/Seedance.
- Do not use Dreamina Omni Reference for loop-video generation. Use first-frame/start-frame input only and leave last-frame input empty.
- Do not keep A/B, 1/2, or artificial pair suffixes in uploaded track titles.
- Do not use titles that read like numbered alternatives. Playlist tracks should look like a real album/playlist tracklist.
- Do not create a Slack review message for every playlist track during automatic playlist publishing.
- If the automation times out while waiting for render/upload, report the exact stage and current release state. Do not start a duplicate publish blindly.

## Quick Selection Guide

Use `Single Release Candidate Set` when:

- The user asks for one song, one single, one YouTube single, or one standalone track.
- Suno returns two alternatives for the same prompt.
- The human needs to choose A or B.

Use `Automatic Private Single Publisher` when:

- The user asks for one song, one single, or one standalone track and explicitly says to publish/upload it.
- The goal is a private YouTube upload without stopping for candidate review.
- The release needs a final clean cover, separate text thumbnail, optional 8 second Dreamina/Seedance loop video, metadata approval, and private upload.

Use `Automatic Private Playlist Publisher` when:

- The user asks for a playlist, mix, compilation, batch, or one-hour release.
- The goal is many tracks.
- The human expects OpenClaw to upload privately to YouTube and review only the final result.

Use `OpenClaw YouTube Metadata Skill` when:

- The release already has rendered video.
- The human asks OpenClaw to write YouTube title, description, and tags.
- The human wants OpenClaw to approve metadata but not publish.
- The human can alternatively use the web `Generate Metadata` / `Regenerate Metadata Draft` button, which may call the VM's local Codex CLI when enabled.
- OpenClaw must first run `scripts/openclaw-release metadata-context --release-id RELEASE_ID` and use `display_timestamp_lines` when available.
- Follow [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
