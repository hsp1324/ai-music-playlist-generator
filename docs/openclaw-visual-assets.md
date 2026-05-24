# OpenClaw Visual Asset Skills

Use this when OpenClaw creates cover images, YouTube thumbnails, or short loop videos for this repo.

The production source of truth is [openclaw-channel-profiles](openclaw-channel-profiles/README.md). Run `scripts/openclaw-release channel-profile` first, then read the returned `profile_doc`.

## Shared Asset Contract

- Create static cover and thumbnail images with OpenAI GPT Image models, not Dreamina.
- Use Gemini first for moving loop videos, then Dreamina/Seedance when Gemini is unavailable, blocked after retries, or in its 24 hour cooldown after 3 successful video generations.
- Always create the final 16:9 cover/first-frame first, then create the YouTube thumbnail from that image as a reference/edit derivative.
- Keep cover, thumbnail, and loop video visually continuous: same subject count, subject placement, silhouettes, clothing colors, props, background landmarks, lighting, palette, and camera angle.
- Do not put the YouTube channel name, channel logo, or channel-brand line on covers, thumbnails, first-frame images, or loop videos.
- If text is useful, use only a short natural style, genre, use-case, or passage phrase. Examples: `J-POP`, `LOFI`, `TECH HOUSE`, `CINEMATIC ORCHESTRA`, `GAME OST`, `Genesis 1:1-5`, `Matthew 1:18-25`, `팔정도 명상팝`, `자비 트립합`. The phrase should feel integrated into the image, not like a pasted badge.
- Do not add title sentences, lyrics, subtitles, duration text, UI, logos, watermarks, or unrelated words to the cover/first-frame or loop video.
- If Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not regenerate only because that provider logo is present.
- Do not include spectrum bars, waveform graphics, equalizers, or audio meters in generated assets. The app adds the audio-reactive visualizer during final render.
- Available app-rendered visualizer presets are `bars`, `mirror-bars`, `calm-bars`, and `none`. Do not use removed busy presets: small dots/particles, thin waveform, multiwave, radial, pulse, or the spectrum style used on `창세기 창조의 빛`. `BibliaCanto` must use `none`; `불송` must use `calm-bars`.
- Human visual requests override the channel default when they are safe and compatible with the channel.
- All generated visuals should look animated, anime, illustrated, or stylized unless a channel profile says otherwise. `Cinematic Pulse` uses original photorealistic cinematic first-frame art and restrained cinematic motion. `불송` uses photorealistic/premium Buddhist visuals by default, with occasional gentle animation only when the music lane fits.

## Loop Video Rules

- Normal Dreamina/Seedance browser clips use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`.
- If the Seedance/Dreamina duration control is hidden when the screen opens, gently drag/scroll the settings/control row to the right until the duration option is visible, then set it to exactly `7 seconds`. Do not Generate while the duration is hidden, set to 5 seconds, or uncertain.
- `불송` clips use Seedance/Dreamina `2.0 Fast`, first-frame only, `16:9`, `720p`, exactly `6 seconds`.
- HaruHaru photorealistic clips use Seedance `2.0`, first-frame only, `16:9`, `1080p`, exactly `7 seconds`, then final render `--video-render-resolution 1080p`.
- Gemini clips are uploaded as generated after inspection. Do not mention duration in Gemini prompts.
- Do not put `7 seconds`, `6 seconds`, `16:9`, `720p`, `1080p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Set those in provider controls when available.
- Do not use a local pan/zoom, app still-image animation, or other workaround when video generation fails unless the human explicitly approves a still-image fallback.

## Prompt Stability Rules

- Describe the visible state, camera, composition, and environmental motion. Avoid conceptual phrases that imply a staged montage.
- Avoid `playlist`, `music visual`, `visualizer shot`, and scripture-framework words in the video prompt when they are not visually necessary. For example, do not prompt `Four Noble Truths playlist`; prompt `a quiet rain-washed temple path, lotus pond, dawn mist, warm lantern glow`.
- Prefer positive fixed-shot language: `single fixed camera shot`, `locked-off camera`, `one uninterrupted calm environmental take`, `same composition from first to last frame`.
- Keep negative lists short. Too many `do not` clauses can make providers focus on the forbidden action and cause hard cuts, resets, or layout changes.
- Ask for ambient motion that naturally exists in the first frame: light flicker, rain ripple, incense smoke, water shimmer, fabric/hair wind, city lights, DJ LEDs, lantern glow, leaves, clouds, or reflections.
- Reject/regenerate clips that change to a different scene, reset composition mid-clip, introduce extra text, invent channel names, or make the subject noticeably zoom in/out when the profile requires stable scale.

## Channel Visual Notes

- `Tokyo Daydream Radio`: illustrated J-pop visuals; default exactly three people walking toward the viewer while the camera moves backward at the same speed so subject size stays stable. Text, if any, should be a short J-pop/style phrase, not the channel name.
- `Soft Hour Radio`: calm BGM visuals; often best with locked camera, natural environmental motion, and `none` or restrained spectrum for very quiet releases. Use lofi wording when the lane is lofi.
- `sundaze`: English pop visuals; style/use-case text should name the pop lane naturally, such as pop R&B, dance-pop, synth-pop, pop-rock, or feel-good pop.
- `Solwave Radio`: Latin/Spanish pop visuals; use Spanish/Latin lane text such as Pop Latino, Reggaeton Suave, Bachata Pop, Latin R&B, or Verano Latino when useful.
- `HaruHaru`: Korean pop visuals; keep one coherent lane per video. Photorealistic adult-fashion/lifestyle visuals are allowed at a 2:1 photorealistic-to-animation ratio, with stable subject scale and no explicit sexual content.
- `Storylight OST`: playful game/anime BGM visuals; sell happy mood, cozy gaming, arcade/game OST, or light focus instead of narrow mechanic words.
- `Cinematic Pulse`: photorealistic cinematic cover/first-frame art, preferably 2560x1440 or at least 1920x1080. Create a subtle 7 second provider loop video from that first frame, then queue final render with `--video-render-source-mode loop_video --video-render-resolution 720p --video-spectrum-overlay-style bars` unless a human explicitly asks for still-image fallback or higher resolution.
- `Club Bloom`: no-vocal club/EDM visuals; prefer active DJ/performance scenes, rooftop/beach/festival/nightclub energy, bold neon, and style text such as Tech House, Bass House, Trance Mix, EDM Mix, or Club Mix.
- `BibliaCanto`: Bible scripture music; use exact passage range and music lane as visual text when useful, never `Old Verse`, `New Verse`, or channel names. Render with `--video-spectrum-overlay-style none`.
- `불송`: Buddhist scripture-inspired vocal music; cover/thumbnail/first-frame should use a short Korean passage/theme + style phrase such as `팔정도 명상팝`, `자비 트립합`, or `무상 불교 재즈`, never `불송`. Use calm 6 second Seedance/Dreamina `2.0 Fast` motion and final render with `--video-spectrum-overlay-style calm-bars`.

## Bulsong Prompt Shape

```text
Use the uploaded first-frame image as the exact starting frame.
It is a clean Buddhist/dharma music artwork with a short Korean passage/theme + music-style phrase integrated into the image.
Create one uninterrupted calm environmental take from a locked-off camera.
Keep the same composition, crop, camera distance, lighting, palette, subject placement, and typography from first frame to final frame.
Animate only gentle ambient details already present in the image: lantern flicker, incense smoke, rain ripple, moonlight on water, drifting petals, soft wind, candle glow, dust in light, or slow reflections.
Keep the existing short Korean phrase stable and readable if present. Do not invent any channel name.
No new text, no subtitles, no lyrics, no UI, no added logos, no disrespectful religious imagery, no photorealistic Buddha face.
```

## Other Channels Or Explicit Requests

- If the selected channel has no profile, derive a visual system from the channel purpose, release concept, and human request.
- Do not borrow another channel's fixed signature unless the human explicitly asks.
- Keep metadata titles broad, natural, and clickable. Visual scene details can support the description, but the public title should normally lead with genre/lane and listening use case.
