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

## Continuous Next Release Planning

When the app asks OpenClaw to create the next release after a publish completes, first use [openclaw-next-release-planner.md](openclaw-next-release-planner.md). That planner chooses the next channel and fresh concept, then hands off to this document's automatic private playlist publisher.

## Channel-First Workflow

Before generating cover art, YouTube thumbnails, or Dreamina/Seedance loop videos, OpenClaw must choose the target channel first and read that channel's profile.

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --prompt "PROMPT_OR_STYLE" \
  --tags "comma,separated,tags"
```

If the human explicitly named a channel, pass it:

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --youtube-channel-title "Soft Hour Radio"
```

Then read the returned `profile_doc` from [openclaw-channel-profiles](openclaw-channel-profiles/README.md). Do not mix visual signatures across profiles.

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
- When uploading audio, include lyrics or song-content notes with `--lyrics` or `--lyrics-file` whenever available. For instrumental work, save and upload the exact bracket-only Suno instrumental metatag file so later metadata/visual work can understand the track.
- BGM/background/lofi/study/sleep/cafe music defaults to instrumental/no vocals unless the human explicitly asks for vocals. For Soft Hour Radio or other instrumental BGM, follow [suno-v55-instrumental-format.md](suno-v55-instrumental-format.md) before pressing Create in Suno.
- For Soft Hour Radio instrumental work, do not put plain prose in Suno's lyrics/custom-lyrics field. Every non-empty line in that field must start with `[` and end with `]`. Bare arrangement sentences can be interpreted as sung lyrics.
- For Soft Hour Radio instrumental work, open Suno Advanced Options and fill the excluded styles/negative style field with vocal-related exclusions: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- Instrumental metatags must be concrete enough to steer Suno toward the intended arrangement. Include an instrumental guardrail, tempo/feel, instrument palette, section-by-section musical flow, dynamics, and transitions inside bracketed lines. Do not write singable lyric lines. Example shape:
  `[Instrumental only: no sung words, no humming, no spoken words]`
  `[Intro: 8 bars, felt piano motif alone, wide room, soft rain ambience]`
  `[Main Theme: brushed drums enter, upright bass plays long roots, nylon guitar answers the piano]`
  `[Development: warm Rhodes pad opens, piano melody becomes slightly brighter, percussion stays soft]`
  `[Instrumental Break: harp harmonics and soft cymbal swells, melody carried by piano and guitar]`
  `[Bridge: drums drop to rim clicks, bass holds long notes, strings widen gradually]`
  `[Final Theme: piano motif returns, guitar answers every 4 bars, gentle lift without a vocal hook]`
  `[Outro: solo piano and rain ambience, slow fade]`
  `[End]`
- J-pop/K-pop/pop/Japanese pop/anime-pop releases default to vocal songs with lyrics. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, and the requested language or natural English/Korean lyrics for generic pop. Do not make these instrumental, no-vocal, lyricless, or hum-only unless the human explicitly asks for instrumental/BGM/lofi/no vocals. For every pop-family track, create or capture the final lyrics and upload them with `--lyrics` or `--lyrics-file`. The helper rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- When uploading audio, include the Suno style/settings with `--style` whenever available. This is stored with the track for future cover, thumbnail, loop-video, metadata, and remake work.
- Within one release, intentionally vary every generated track. Do not reuse the exact same Suno prompt, lyrics theme, chorus hook, title pattern, or style string across multiple tracks unless the human explicitly asks for a uniform album. Keep the release coherent by genre/mood, but vary tempo, energy, instruments, rhythm feel, vocal tone, season/time/place imagery, lyrical story, and hook.
- For playlist releases, prefer one `--style` per `--audio` and one `--lyrics-file` per vocal track. Shared style is allowed only for a narrow BGM/instrumental set where the human wants consistency; even then, vary titles and prompts.
- Playlist track generation should target roughly 3:00 to 3:30 per Suno output, with 3:45 still in the preferred range. Outputs up to 4:20 are acceptable if Suno returns them, but do not intentionally ask for 4-minute tracks. Regenerate or replace outputs over 4:20 before publishing. `auto-publish-playlist` rejects tracks over 260 seconds unless `--allow-long-track` is used with explicit human approval.
- For J-pop/K-pop/pop playlists, each song needs its own original lyrics and chorus concept. Do not create multiple songs with near-identical verse/pre-chorus/chorus wording, repeated phrases, or only swapped nouns.
- Always return the final JSON result and mention `release.id` plus uploaded `track.id` values.
- If a command fails, stop and report the exact error. Do not retry blindly more than once.
- For YouTube title/description/tag writing, use [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
- Every YouTube description, including `ko`, `ja`, `en`, and `es` localized descriptions, must end with a visible public hashtag line. The `--tags` option is separate API metadata and does not create visible hashtags in the description.
- For playlist publishing, choose the YouTube channel by release concept:
- Default background/cafe/sleep/study/chill playlists go to `Soft Hour Radio`.
- Mainstream J-pop/Japanese pop releases go to `Tokyo Daydream Radio`. Treat these as Tokyo Daydream candidates when the title, prompt, tags, or concept includes Tokyo, Shibuya, Shinjuku, J-pop, Japanese pop, city pop, Japanese dance-pop, Japanese synth-pop, Japanese pop-rock, anime-pop, vaporwave, 도쿄, 시티팝, 제이팝, 東京, 渋谷, 新宿, Jポップ, or シティポップ. Anime/OST-like music is allowed inside the channel, but the channel is broader mainstream J-pop/pop, not anime OST-only.
- If the human explicitly names a target channel, that explicit channel overrides automatic channel inference and also controls the visual skill. Example: `Soft Hour Radio에 올려줘` means use the Soft Hour channel profile even if the music has light Japan/city-pop influence.
- Do not use `MusicSun` unless the human explicitly requests it.
- `scripts/openclaw-release auto-publish-playlist` can infer the channel when `--youtube-channel-title` is omitted, but OpenClaw should pass `--youtube-channel-title "Tokyo Daydream Radio"` when the Japan routing intent is clear.
- YouTube visibility must stay private. The app uses `AIMP_YOUTUBE_PRIVACY_STATUS=private`; do not make a public upload from OpenClaw.
- Do not upload videos directly through `youtube.com` or YouTube Studio. Use `scripts/openclaw-release auto-publish-single`, `scripts/openclaw-release auto-publish-playlist`, or the app's local `/approve-publish` API only. The app uploads through the YouTube Data API and stores the resulting `youtube_video_id`/channel metadata.
- Do not run `auto-publish-playlist` or `auto-publish-single` against a release that already has `youtube_video_id` unless the human explicitly asks for a re-upload. Create a fresh release for a new video. The helper rejects accidental re-uploads unless `--allow-reupload` is passed.
- YouTube Studio is only for human final checks after the private API upload, such as watching the private video, changing visibility to Public, reviewing automatic captions, or manual cleanup.
- Do not try to enable automatic captions through browser automation. The app does not upload caption files or toggle caption settings. For vocal releases, the API upload infers and sends `snippet.defaultAudioLanguage` when possible so YouTube knows the likely spoken/sung language; YouTube may generate automatic captions later. For BGM/instrumental/no-vocal releases, do not set captions or audio language unless the human explicitly requests manual captions.
- YouTube metadata supports localized title/description for `ko`, `ja`, `en`, and `es`. For `Tokyo Daydream Radio` or any Japan/J-pop release, OpenClaw must write all four versions: Korean, Japanese, English, and Spanish. Use Korean as the default metadata (`--title`, `--description-file`) and also pass `--ko-title`, `--ko-description-file`, `--ja-title`, `--ja-description-file`, `--en-title`, `--en-description-file`, `--es-title`, and `--es-description-file` to `scripts/openclaw-release approve-metadata`.
- For Playlist Releases on every channel, start the main YouTube title and every localized title exactly with `[playlist]`. Do not add this prefix to Single Releases.
- After `[playlist]`, do not repeat playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`; use music/mix/radio wording instead.
- Playlist/BGM YouTube titles must include listening use cases in the title itself, such as study, work, walk, drive, sleep, reading, or rest. Do not write only a mood/genre title.
- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, `Tokyo`, city-pop, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. If language matters, mention it naturally in the description instead; the thumbnail/channel branding can carry `J-POP`.
- In Korean YouTube titles/descriptions/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Prefer `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- In Japan/J-pop localized descriptions, timestamped tracklists must use Japanese titles in the Korean/default description with Korean translations in parentheses, Japanese titles only in the Japanese description, English translated titles only in the English description, and Spanish translated titles only in the Spanish description. Keep the same timestamps and order in all languages.
- For releases one hour or longer, use `HH:MM:SS` timestamps for the whole tracklist, starting at `00:00:00`; this avoids one-hour-plus YouTube timestamp links failing to activate.
- After audio render, metadata timestamps come from the release's saved `rendered_timeline` snapshot, which uses actual ffprobe source-file durations. Always call `scripts/openclaw-release metadata-context` after render and use its returned timeline; do not manually add rounded track durations.
- If a one-hour playlist contains consecutive Suno pair outputs that may feel repetitive, use randomized render order before audio render. In the API this is `random: true`; in `scripts/openclaw-release auto-publish-playlist` this is `--randomize-order`. The app saves the shuffled order before rendering, so final order and metadata timestamps remain consistent.
- Do not leave trailing `A` / `B`, `1` / `2`, `Morning` / `Evening`, or similar pair labels in uploaded playlist track titles.
- Treat every playlist track as its own song title. If Suno returns two outputs from one prompt, rename both as independent editorial titles, not as variants of the same title.
- Full playlist publishing needs two 16:9 images:
- `cover`: video visual shown during playback. It should look good for the full video duration and must include only the selected channel name as a large, readable lower-left brand label used as the Dreamina/Seedance first-frame text reference. Match the visual scale of the channel-brand line used on the YouTube thumbnail; target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- `thumbnail`: YouTube click thumbnail. It should include short readable text such as `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `TOKYO NIGHT`, `CITY POP`, or `J-POP`, plus the selected channel name as a smaller brand line. Do not add duration text such as `1 HOUR`, `60 MIN`, `1時間`, or time badges.
- For cover, thumbnail, and loop-video visual creation, follow [openclaw-visual-assets.md](openclaw-visual-assets.md).
- Channel-specific cover, thumbnail, and loop-video rules are split into [openclaw-channel-profiles](openclaw-channel-profiles/README.md). Use `scripts/openclaw-release channel-profile` first, then read the returned `profile_doc`.
- Asset generation order is mandatory: create the final cover first with only the large lower-left channel brand label, then create the YouTube thumbnail as an image-to-image edit/reference derivative of that exact final cover. Do not create the thumbnail as a fresh unrelated image.
- When generating the thumbnail from the cover reference, preserve the exact channel/requested subject, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add click text, channel branding, crop/contrast/readability adjustments, and small layout refinements. Example: if the right subject has a red cloak in the cover, the thumbnail must keep that cloak red.
- If the generated thumbnail changes character identity, clothing color, subject count, subject placement, or core background compared with the cover, reject it and regenerate before uploading.
- Preferred thumbnail format: full-bleed image background, no card or panel, large bottom-left genre/mood text, and a smaller channel-brand line directly below. For Japan/J-pop releases, follow the approved Tokyo Daydream Radio treatment: large `J-POP` text and smaller `TOKYO DAYDREAM RADIO` directly beneath it. Keep this exact two-line brand system for Tokyo city, forest/nature, and beach versions so the channel stays visually consistent.
- Channel visual signatures are separate:
- Tokyo Daydream Radio/Japan/J-pop uses exactly three people walking forward away from the viewer by default. The camera/viewer sees their backs and backs of heads; no front-facing faces as the main composition.
- Soft Hour Radio/default BGM uses its own channel profile: calm, restrained, long-listening visuals without a fixed recurring mascot, character count, scene list, or camera composition.
- Explicit channel requests override genre-based visual routing. If the requested channel is `Soft Hour Radio`, use the Soft Hour profile returned by `scripts/openclaw-release channel-profile`.
- Human visual requests override the selected channel visual skill. If the human asks for a specific scene, subject, action, camera angle, object, animal, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video.
- When a channel/default signature is used, the main subject must stay centered in thumbnails. Text must not push it to the side, crop it, cover it, or make it feel secondary. Place text in safe negative space, usually lower-left or lower area.
- When a human visual request overrides the default, keep the requested subject/action/composition centered and visually important in thumbnails; text must fit around the requested composition rather than replacing it.
- The background should come from the selected channel profile and the release concept, not from a hard-coded scene list.
- All static images and Dreamina/Seedance loop clips must look animated, anime, illustrated, or stylized. Do not make photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- Generate static images with OpenAI GPT Image models, not Dreamina. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the OpenAI/Image tool environment. Do not use Dreamina for static image generation. Do not assume the OpenAI API is free; use the available Codex/ChatGPT image tool if that is the operator-approved path, or use API billing/credentials when explicitly configured.
- Use Dreamina/Seedance only for the moving visual clip. If Dreamina/Seedance can create a visual motion clip, OpenClaw should generate exactly one 8 second MP4 and pass it with `--loop-video`. The clip should end close to its opening composition so it can be reused across the full release. OpenClaw should not render a one-hour MP4 itself.
- Keep these assets separate: `--thumbnail` is the click image with large text and channel branding, `--cover` is the playback visual with only the large lower-left channel brand label, and `--loop-video` is the 8 second moving visual used inside the rendered video. Do not use the text thumbnail as the video visual.
- The 8 second loop video must visually match the thumbnail's scene and brand, but it should start from the cover or a separate first-frame image that contains only the large lower-left channel brand label. Do not use the final text thumbnail as the Dreamina/Seedance first-frame reference, because generated video often makes large thumbnail text flicker, disappear, or reappear during the loop.
- The lower-left channel label is mandatory inside the rendered video. Let the GPT Image model design the font/lettering to match the scene, channel, and genre, but keep the exact requested spelling large and readable on mobile playback. Then ask Dreamina/Seedance to preserve that baked-in text exactly for the full 8 second clip and never shrink it.
- Do not add extra title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover/first-frame or loop video. The lower-left channel label is the only allowed text inside the moving visual unless the human explicitly asks for more.
- After Dreamina/Seedance generation with baked-in text, visually inspect the downloaded MP4 before upload. Reject and regenerate if the channel label flickers, disappears, morphs, changes spelling, changes font/position drastically, or becomes unreadable.
- For browser-based Dreamina generation, OpenClaw should use `https://dreamina.capcut.com/ai-tool/home/`. Select Seedance/Dreamina `2.0 Fast`, first/last-frame mode if the UI asks, provide the first frame only, leave the last frame empty, set ratio to `16:9` when selectable, quality to `720p`, duration to exactly `8 seconds`, then create/download the MP4, save it locally, and pass the downloaded file path as `--loop-video`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set duration, ratio, and quality only through Dreamina controls. Use the selected channel profile for camera behavior. For `Soft Hour Radio`, keep the camera locked and animate calm but clearly visible environmental motion across several layers throughout the full clip; do not ask for zoom, dolly, camera breathing, or camera drift.
- If Dreamina/Seedance blocks generation for inappropriate content, copyright, moderation, or policy reasons, retry up to 10 total attempts. Do not retry the same prompt. Before every retry, post Slack progress with `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`.
- For every Dreamina retry, sanitize the prompt: remove named artists, studios, franchises, copyrighted characters, brands, logos, celebrity names, exact song/video titles, `in the style of` phrases, real-person likenesses, sexualized wording, minors, weapons, gore, and other moderation-risk terms. Replace them with original generic descriptors while preserving mood, channel label, first-frame continuity, and motion intent.
- If the uploaded first frame appears to be the moderation trigger, regenerate a safer cover/first-frame image first. If all 10 Dreamina attempts fail, post `scripts/openclaw-release slack-notify --text "영상 생성이 10회 실패해서 중단했습니다. RELEASE_TITLE: ERROR_SUMMARY"` and stop before render/publish unless the human explicitly approves a still-image fallback.

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
- If candidate lyrics or instrumental metatag files exist, upload them with the audio candidates using `--lyrics` or `--lyrics-file`. For instrumental/BGM candidates, use the exact bracket-only Suno metatag file from `docs/suno-v55-instrumental-format.md` rather than an empty field when possible. For J-pop/K-pop/pop/Japanese pop/anime-pop candidates, lyrics are expected by default unless the human explicitly asked for instrumental/no-vocal.
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

If no cover image is ready, omit every `--cover` argument. If one shared cover should be used for both candidates, provide one `--cover`; if each candidate has a different cover, provide one `--cover` per `--audio` in the same order. If lyrics/content are truly unavailable, omit `--lyrics`/`--lyrics-file`; the app stores an empty lyrics field. For instrumental/BGM candidates, prefer the exact bracket-only Suno metatag file instead of omitting lyrics. For J-pop/K-pop/pop/Japanese pop/anime-pop candidates, do not treat missing lyrics as normal; generate or capture original lyrics unless the human explicitly requested instrumental/no-vocal. If style/settings are not available, omit `--style`; otherwise always provide it.

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

For mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar Japan-themed vocal pop singles, publish to `Tokyo Daydream Radio`.

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
- Preserve lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available. For BGM/background/instrumental tracks, write and upload the exact bracket-only Suno instrumental metatag file when possible; J-pop/K-pop/pop/Japanese pop/anime-pop songs should not have empty lyrics unless the human explicitly requested an instrumental/no-vocal track.
- If this is a J-pop/K-pop/pop/anime-pop single and there is no final lyric text, stop and generate/capture original lyrics before calling `auto-publish-single`.
- Preserve Suno style/settings during upload. Pass `--style "SUNO_STYLE_OR_SETTINGS"` for each song.
- A final 16:9 cover image is required. For moving-video releases, this cover also acts as the Dreamina/Seedance first-frame reference. It must include only the selected channel name as a large lower-left brand label readable on mobile.
- A separate YouTube thumbnail image with readable text is required. For J-pop/Japan singles, use the approved Tokyo Daydream Radio pattern: large `J-POP` with smaller `TOKYO DAYDREAM RADIO` beneath it. Use the same brand system for Tokyo/city, forest/nature, and beach variants. Do not add duration text or badges such as `1 HOUR`, `60 MIN`, or `1時間`.
- Apply the selected channel profile to both static images. For J-pop/Japan/Tokyo Daydream Radio singles, use the Tokyo profile. For Soft Hour/default BGM singles, use the Soft Hour profile. The cover should contain only the large lower-left channel brand label; the thumbnail must be generated from that final cover as a reference/edit derivative, using the same composition plus readable click text and channel branding. In the thumbnail, keep the main channel/requested subject centered; text must fit around the composition rather than moving the subject sideways.
- Before uploading the thumbnail, compare it against the cover. Character count, subject positions, silhouette, outfit colors, lighting, palette, and core background must remain visually continuous. Regenerate the thumbnail if it looks like a different scene or changes details such as cloak/shirt colors.
- Keep the visual style animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- Generate both static images with OpenAI GPT Image models, not Dreamina. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model. Dreamina is only for the moving 8 second MP4. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- Generate exactly one 8 second Dreamina/Seedance MP4 before publish when moving visuals are requested.
- Use the cover or a separate first-frame image as the first-frame/start-frame reference for Dreamina/Seedance so the video opening matches the thumbnail scene. This first frame must contain only the large lower-left channel label and preserve it exactly. Use the selected channel profile for the first-frame concept. If the human requested a different visual concept, the first frame and motion prompt must follow that requested concept instead. Do not use the text thumbnail, Omni Reference, or a last-frame reference.
- The thumbnail, cover, and loop video are three different assets. The thumbnail has readable click text plus channel branding. The cover/loop video contain only the large lower-left channel label as baked-in text. The loop video must still remain free of subtitles, lyrics, UI, logos, title text, duration text, and unrelated words.
- If using browser automation, open `https://dreamina.capcut.com/ai-tool/home/`, select `2.0 Fast`, use first/last-frame mode with only the first frame provided, do not use Omni Reference, leave the last frame empty, set `16:9`, `720p`, and `8 seconds` when selectable, create/download the MP4, confirm the local file exists, and pass that absolute path as `--loop-video`.
- Do not include duration, ratio, or quality words in the Dreamina prompt. Do not write `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. Those are either UI settings or app-render responsibilities.
- Use the Dreamina prompt shape from the selected channel profile returned by `scripts/openclaw-release channel-profile`.
- If the human provided a specific visual/video request, replace the selected channel default prompt details with the requested subject/action/composition while keeping the safety/quality constraints: one continuous shot, no repeated segment, no ping-pong, preserve first-frame composition/style, preserve the large lower-left channel label, stable composition, no other text/subtitles/logos/UI, no extra unwanted subjects.
- Always include this Dreamina prompt constraint: `The uploaded first frame contains the exact large, readable lower-left channel brand label "{CHANNEL_NAME}" (for example, "Tokyo Daydream Radio"). The label should match the visual scale of the YouTube thumbnail's channel-brand line, roughly 18-24% of image width or 5-6% of image height for text cap height. Preserve this text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, shrink, or change the text. Keep the text area stable; animate the surrounding scene naturally.` Keep all other constraints.
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
- Do not publish without a final cover with the large lower-left channel brand label, a separate text thumbnail, and the correct YouTube channel selection.
- For Japanese/J-pop/Tokyo singles, pass `--youtube-channel-title "Tokyo Daydream Radio"` explicitly.

## Skill 3: Automatic Private Playlist Publisher

Use this skill when the user asks for a playlist, mix, compilation, or approximately one-hour release and expects OpenClaw to finish the private YouTube upload.

### Goal

Create one Playlist Release, generate enough tracks, upload them as approved tracks, render audio/video, generate and approve metadata, and upload the result privately to YouTube on the correct channel.

Use `Soft Hour Radio` for normal background/cafe/sleep/study/chill releases. Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar Japan-themed vocal pop releases.

The human does not review every playlist track before rendering. The human reviews the final private YouTube upload later and only intervenes if something sounds wrong.

### Important Duration Rule

Playlist uploads are auto-approved, so `workspace.actual_duration_seconds` becomes the source of truth after upload.
After audio render, `rendered_timeline` becomes the source of truth for YouTube description timestamps.
Use randomized audio render when Suno two-output pairs are adjacent and the human did not manually arrange a deliberate final order.

Generate enough material before publishing:

- Target at least `3600` seconds for a one-hour playlist.
- A practical buffer of `3900` seconds is acceptable.
- Do not publish under target unless the human explicitly says a shorter playlist is acceptable.
- Every helper audio upload retries up to 3 times. If a track still fails, the helper posts a Slack warning, continues uploading the rest of the batch, and stops before render/publish. Re-download or re-export only the failed source files, upload them again, then render/publish after the full intended track set is present.
- After every successful upload, use the returned JSON as the receipt: confirm `track.id`, `track.status`, and `duration_seconds`. The duration must be close to the actual local audio length.

### OpenClaw Skill Prompt

```text
You are creating and privately publishing a one-hour Playlist Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use scripts/openclaw-release only.

Goal:
- Create or select one Playlist Release workspace before opening Suno or generating audio.
- Generate songs in batches until the usable duration is at least 3600 seconds, preferably around 3900 seconds.
- For BGM/background/lofi/study/sleep/cafe playlist requests, generate instrumental/no-vocal tracks by default unless the human explicitly asks for vocals. For Soft Hour Radio instrumental work, Suno's lyrics/custom-lyrics field must use the bracket-only format from `docs/suno-v55-instrumental-format.md`; never paste unbracketed arrangement prose into that field.
- For BGM/background/lofi/study/sleep/cafe playlist requests, use Suno Advanced Options excluded styles to suppress vocals: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- Ask Suno for roughly 3:00-3:30 per playlist track. 3:45 is still fine. Tracks up to 4:20 are acceptable if Suno returns them, so a 4:04 Suno result can be used. If Suno produces a track longer than 4:20, regenerate or replace it instead of uploading it for final publish unless the human explicitly approves the longer track.
- For J-pop/K-pop/pop/Japanese pop/anime-pop playlist requests, generate vocal songs by default with original lyrics for each track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, and the requested language or natural English/Korean lyrics for generic pop. Do not make the batch instrumental/no-vocal unless the human explicitly asks for instrumental/BGM/lofi/no vocals.
- For every new Suno request in a playlist run, write a distinct prompt/style/lyrics plan before generating. Keep the channel/release mood consistent, but vary one or more of: tempo, drum pattern, bass movement, synth/guitar/piano texture, vocal energy, emotional angle, scene imagery, lyrical storyline, chorus hook, and song structure.
- If Suno returns two outputs from one request, use both outputs as separate playlist tracks when both are usable.
- Before upload, replace awkward trailing A/B, 1/2, or pair-style labels with independent song titles.
- Preserve each track's lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available, because good playlist tracks may later be republished as standalone singles and OpenClaw needs this context for thumbnail/loop-video generation. For J-pop/K-pop/pop/Japanese pop/anime-pop playlist tracks, lyrics are expected and should be uploaded for every track. For BGM/background/instrumental tracks, upload the exact bracket-only Suno instrumental metatag file used for generation instead of leaving the content blank whenever possible.
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
- Generate or obtain the final cover image before running the full publish command, then pass it with `--cover`. Use OpenAI GPT Image models for static image creation, not Dreamina. For moving-video releases, the cover must contain only the large lower-left selected-channel-name brand label because it is the Dreamina/Seedance first-frame reference.
- Generate or obtain a separate text thumbnail before running the full publish command, then pass it with `--thumbnail`. Use OpenAI GPT Image models for static image creation, not Dreamina. The thumbnail must be created from the final cover as an image reference/edit, not as a new independent scene. For J-pop/Japan releases, use the approved Tokyo Daydream Radio layout: large `J-POP` plus smaller `TOKYO DAYDREAM RADIO`, including forest/nature and beach variants. Do not add duration text or badges such as `1 HOUR`, `60 MIN`, or `1時間`.
- Apply the selected channel profile to both images. Use only the large lower-left channel brand label for `--cover`; use the same centered channel/requested composition plus readable click text and the selected channel brand line for `--thumbnail`. In thumbnails, keep the main subject centered and place text around it in negative space; never move the main subject to one side just to make room for text.
- The cover and thumbnail should look like the same release art package. Preserve the same characters, poses, clothing colors, background, lighting, palette, and camera angle. If the thumbnail changes those details, regenerate it before uploading.
- Keep every generated visual animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- Optionally generate an 8 second Dreamina/Seedance 2.0 motion clip before running the full publish command, then pass it with `--loop-video`.
- The thumbnail, cover, and loop video are three different assets. The thumbnail must contain readable click text plus channel branding; the cover and loop video must contain only the large lower-left channel label as baked-in text. Verify that Dreamina/Seedance preserves it in the 8 second clip.
- Use the cover or a separate first-frame image as the visual starting reference for Dreamina/Seedance image-to-video generation. This reference must include only the large lower-left channel label. Use the selected channel profile for the first shot and motion direction. If the human requested a different video concept, use that requested subject/action/composition for the cover, thumbnail, and loop video. Do not use the text thumbnail as the video first frame.
- For Dreamina motion clips, set duration/ratio/quality in Dreamina controls, not in the prompt. Use the prompt shape from the selected channel profile. For `Soft Hour Radio`, the final moment should keep the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ. The motion should be calm but clearly visible throughout the full clip.
- Do not include `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. These terms cause Seedance/Dreamina to sometimes generate a shorter repeated segment inside the clip.
- If using browser automation instead of an API, open `https://dreamina.capcut.com/ai-tool/home/`, choose Seedance/Dreamina `2.0 Fast`, choose the first/last-frame workflow if the UI requires a mode, upload only the first-frame image, leave the last frame empty, do not use Omni Reference, set ratio `16:9`, quality `720p`, duration exactly `8 seconds`, create the video, download the MP4, confirm the local file exists, and use that absolute path for `--loop-video`.
- If Dreamina rejects the prompt/image for inappropriate content, copyright, moderation, or policy reasons, retry up to 10 total attempts before giving up. Send Slack on every failed attempt before retrying:
  `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`
- On each retry, make the prompt safer and more original: remove named artists, studios, franchises, copyrighted characters, brands, logos, celebrity names, exact song/video titles, `in the style of` phrases, real-person likenesses, sexualized wording, minors, weapons, gore, and other moderation-risk terms. Keep the same broad mood, channel label, first-frame continuity, and motion direction.
- If the first-frame image itself appears to be blocked, regenerate a safer first-frame/cover image and then retry Dreamina. If all 10 attempts fail, send `scripts/openclaw-release slack-notify --text "영상 생성이 10회 실패해서 중단했습니다. RELEASE_TITLE: ERROR_SUMMARY"` and stop before render/publish unless the human explicitly accepts a still-image fallback.
- If Dreamina login, CAPTCHA, payment, or human approval blocks browser automation, stop and report the exact blocked step instead of skipping the loop video.
- Do not let the app's local draft cover stand in for final cover art.
- Render playlist audio.
- Approve the cover.
- Render video.
- Generate and approve YouTube metadata.
- Publish privately to the selected YouTube channel. Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop/Tokyo pop releases; otherwise use `Soft Hour Radio`.
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
  --youtube-channel-title "SELECTED_CHANNEL_TITLE" \
  --randomize-order
```

Do not omit `--cover` or `--thumbnail` for a full private publish run. If either asset is not ready, stop after audio upload/render and report the missing asset. The app's local draft cover is only a placeholder for manual review, not acceptable for automatic YouTube upload.

`--loop-video` is optional but preferred when the human wants moving visuals. If it is omitted, the app renders a still-image visual from `--cover`. If it is provided, the generated clip should end close to its opening composition so it can be reused across the full audio duration.
Use `--randomize-order` when the uploaded playlist contains similar Suno two-output pairs next to each other. Omit it when the human already arranged a deliberate final order.

If the release is mainstream J-pop/Japanese pop/Tokyo pop, set `--youtube-channel-title "Tokyo Daydream Radio"`. Otherwise set `--youtube-channel-title "Soft Hour Radio"` or omit the flag and let the helper infer the default.

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
- Do not publish if the selected YouTube channel is not connected. Current intended routing is `Soft Hour Radio` for general BGM releases and `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop releases.
- Do not publish if final cover art was not uploaded. `auto-publish-playlist` requires `--cover` unless a final uploaded cover already exists on the release.
- Do not publish if final YouTube thumbnail art was not uploaded. `auto-publish-playlist` requires `--thumbnail` unless a final uploaded thumbnail already exists on the release.
- Do not use Dreamina to create static cover or thumbnail images. Use OpenAI GPT Image models for static images, then use Dreamina only to animate the cover or first-frame image into an 8 second loop video. This image must include only the large lower-left selected-channel-name brand label.
- Static cover and thumbnail images must follow the selected channel profile returned by `scripts/openclaw-release channel-profile`.
- In thumbnails, keep the main channel/requested subject centered; text must not push it sideways.
- Do not use `--allow-generated-draft-cover` unless the human explicitly says a placeholder cover is acceptable for this upload.
- Do not use `--allow-cover-as-thumbnail` unless the human explicitly says one image is acceptable for both the video visual and YouTube thumbnail.
- Do not create a long one-hour MP4 in OpenClaw. Upload only the 8 second loop clip with `--loop-video`; the app handles the long render.
- Do not add subtitles, lyric overlays, UI elements, title text, genre text, duration text, or unrelated words inside the loop video. The selected channel profile controls the default visual action. An explicit human visual/video request overrides that channel default. If the first-frame reference has baked-in text other than the large lower-left channel label, regenerate a no-extra-text first frame before using Dreamina/Seedance.
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
- The release needs a final cover with a large lower-left channel brand label, separate text thumbnail, optional 8 second Dreamina/Seedance loop video, metadata approval, and private upload.

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
