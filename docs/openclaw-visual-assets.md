# OpenClaw Visual Asset Skills

Use this when OpenClaw creates cover images, YouTube thumbnails, or Dreamina/Seedance loop videos for this repo.

The visual rules are channel-specific. Do not apply one channel's visual signature to every release. The source of truth for production work is now [openclaw-channel-profiles](openclaw-channel-profiles/README.md). OpenClaw should run `scripts/openclaw-release channel-profile` first, then read the returned `profile_doc`.

## Shared Asset Contract

- Create static cover and thumbnail images with OpenAI GPT Image models, not Dreamina.
- Prefer `gpt-image-2` when available; otherwise use the best available GPT Image model in the current environment.
- Use Dreamina/Seedance only for the moving loop video.
- Always create a final clean 16:9 cover first.
- Create the YouTube thumbnail from that final cover as an image-to-image edit/reference derivative, not as a fresh unrelated scene.
- Keep cover, thumbnail, and loop video visually continuous: same subject count, subject placement, silhouettes, clothing colors, props, background landmarks, lighting, palette, and camera angle.
- The thumbnail is the click image and should contain short readable text plus channel branding.
- The cover is the playback visual and Dreamina/Seedance first-frame reference. It must include only a small lower-left selected-channel-name watermark.
- Do not use the text thumbnail as the Dreamina first-frame reference.
- The cover/first-frame watermark is mandatory for every channel. Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words.
- The Dreamina/Seedance loop video must preserve the exact lower-left channel label for the full clip. Reject/regenerate if it disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- The thumbnail should use larger click text plus a smaller channel-brand line whose size/style stays consistent with the cover watermark when possible.
- Human visual requests override the channel default. If the human asks for a specific scene, subject, action, camera angle, animal, object, or character type, apply that concept consistently to the cover, thumbnail, and loop video.
- All generated visuals should look animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage unless the human explicitly asks and the YouTube synthetic-media policy is handled.

## Tokyo Daydream Radio Visual Skill

Use this for `Tokyo Daydream Radio`, Japan, Tokyo, city-pop, J-pop, anime-pop, Japanese lofi, or similar Japan-themed releases.

Default visual signature:

- Exactly three people seen from behind, walking forward away from the viewer into the scene.
- The camera/viewer sees backs and backs of heads, not front-facing faces.
- The three people stay centered and visually important.
- Text must fit around the centered three-person silhouette, usually in lower-left or lower negative space. Do not push the people sideways.
- Background can adapt to the release: Tokyo street, forest path, beach, rainy city, night park, station road, fantasy forest, seaside walk, etc.

Thumbnail text:

- Use large `J-POP`.
- Use smaller `TOKYO DAYDREAM RADIO` directly beneath it.
- Keep the same full-bleed two-line treatment for Tokyo/city, forest/nature, and beach variants.
- Do not add `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, or duration badges.

Dreamina/Seedance prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact lower-left channel label "Tokyo Daydream Radio".
Create one continuous forward-moving animated music visualizer shot.
Keep the Tokyo Daydream Radio signature: exactly three people seen from behind, walking away from the camera into the scene.
The viewer should see backs and backs of heads, not front-facing faces.
The motion must progress forward naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Preserve the lower-left "Tokyo Daydream Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, or change it.
Adapt the background and atmosphere to the release concept.
Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI, no extra people or characters.
```

## Soft Hour Radio Visual Skill

Use this for `Soft Hour Radio`, default background music, cafe, piano, sleep, study, work, chill, relaxing, ambient, lofi, and similar non-Japan BGM releases.

Default visual direction:

- Prefer calm, restrained visuals matched to the music use case.
- Let the specific release concept decide the subject. Do not force a fixed recurring mascot, character count, scene list, or camera composition.
- Human presence is optional and should serve the release concept.
- Keep the composition uncluttered, warm, readable, and suitable for long background listening.

Thumbnail text:

- Use 2-4 large use-case or mood words such as `DEEP SLEEP`, `CAFE PIANO`, `FOCUS MUSIC`, `RAINY NIGHT`, `STUDY BGM`, or `CALM READING`.
- Add smaller `SOFT HOUR RADIO` as the channel brand line.
- Do not add duration badges unless the human explicitly asks.

Dreamina/Seedance prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact lower-left channel label "Soft Hour Radio".
Create one continuous calm animated music visualizer shot for a background-music release.
Preserve the opening composition, lighting, palette, and illustrated/stylized visual language.
Preserve the lower-left "Soft Hour Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, or change it.
Animate only natural, subtle details already implied by the first frame and release mood.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## Other Channels Or Explicit Requests

- If the channel is neither `Tokyo Daydream Radio` nor `Soft Hour Radio`, derive a visual system from the channel name, release concept, and human request.
- If the human explicitly names the target channel, that channel's visual skill wins over automatic genre routing.
- Keep the shared asset contract.
- Do not borrow another channel's visual signature unless the human explicitly asks for it.
