# OpenClaw Channel Concept Planner: Tokyo Daydream Radio

Use this after the selected channel is `Tokyo Daydream Radio`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/tokyo-daydream-radio.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

Tokyo Daydream Radio is a mainstream J-pop/Japanese pop channel. It can include anime-pop, but it is not an anime OST-only channel. The channel name contains Tokyo, but release titles do not need to contain `Tokyo` unless the selected concept is actually Tokyo-specific.

The audience should immediately understand: hook-driven Japanese vocal pop for Japan lifestyle listening, with Tokyo as one possible setting rather than the default title word.

Titles should be mainstream J-pop packaging first. Use the specific visual scene or city setting as atmosphere unless it is the strongest public hook; do not make narrow scene names the main title by default.

Before finalizing metadata, check the main title and every localized title in its own language. Reject titles that sound like language labels or keyword piles, such as `Japanese vocal`, `Tokyo walk energy`, or an arcade/night/friends list that does not read like a real J-pop playlist in that language. Use `J-POP`, mood, pop substyle, and one or two natural listening situations, rewritten naturally per language.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Tokyo Daydream Radio` releases and avoid repeating:

- The same city/season/weather setting, such as rainy Tokyo, Osaka night out, Kyoto evening, forest walk, beach walk, night park, fantasy forest, or commute.
- The same pop substyle, such as city-pop, dance-pop, synth-pop, guitar pop, pop-rock, anime-pop, or ballad.
- The same lyric premise, such as first love, walking home, new start, night escape, seaside memory, or weekend freedom.
- The same title pattern or thumbnail phrase.
- The same visual scene if it was used recently.

If a setting appeared in the latest 3 Tokyo releases, do not use it again unless the human explicitly asks.

## Concept Lanes

Use one lane, then vary substyle and lyric premise:

- Tokyo night drive, neon train lines, city lights, late commute, rooftop skyline.
- Osaka weekend neon, Kyoto evening streets, Yokohama bay lights, seaside train, summer festival, station road, school-after-hours, shopping street, karaoke night, or Japan travel/lifestyle scenes that are not Tokyo.
- Rainy Shibuya or Shinjuku, umbrellas, station road, after-work walk.
- Summer beach walk, seaside train, coastal evening, festival night.
- Weekend shopping street, cafe date, spring afternoon, sunny crosswalk.
- Arcade or game-center night, neon rhythm games, friends meeting up, karaoke, weekend night out.
- School-after-hours youth pop, band-room guitar pop, graduation season.
- Bright dance-pop, synth-pop, city-pop, pop-rock, emotional ballad, light band pop.

## Music Direction

- Always create original Japanese lyrics by default.
- Every track needs a distinct lyric concept, chorus hook, title, and Suno style/settings.
- Keep choruses memorable and playlist-friendly.
- Treat the playlist title/use case as packaging and energy direction, not as the required lyric topic. If the playlist is for a train ride, arcade night, beach walk, commute, or city lights, the melody/beat/energy should fit that listening context, but the lyrics do not need to literally describe riding trains, playing games, walking, commuting, or looking at city lights.
- Write each song like a real standalone J-pop track: natural Japanese phrasing, memorable hook, believable emotion, youth, longing, first love, distance, courage, new start, night-out, or bittersweet pop story. Avoid over-literal lyrics that repeat the YouTube title/use case.
- Match lyrics to the melody, beat, vocal tone, and hook first. Song quality is the first priority. A song can fit a walk/drive/night playlist because of its rhythm and atmosphere while the lyrics tell an independent pop story unrelated to the playlist title.
- Do not put duration caps such as `less than 4 minutes` or `under 4 minutes` into Suno fields unless the human explicitly asks for that cap. Prompt for a complete J-pop song with a natural intro, verse/pre-chorus/chorus flow, bridge or final chorus lift where useful, and resolved ending; regenerate or explicitly report tracks shorter than 2:00.
- Do not make lyricless, BGM-only, hum-only, or instrumental tracks unless the human explicitly requested it.
- Do not over-emphasize `Japanese language` in titles. Use `J-POP`, the actual Japan scene, mood, and listening use case instead.
- Do not put `Tokyo` / `도쿄` in every title. Use it only when the chosen concept is specifically Tokyo, Shibuya, Shinjuku, Tokyo commute, Tokyo skyline, or a clearly Tokyo-coded scene. For generic J-pop, beach, forest, festival, school, karaoke, or Japan lifestyle concepts, omit Tokyo from the title.
- Do not default every Tokyo title to `walk` / `산책`. Use walking only for street, commute, crosswalk, beach, forest, or similar movement concepts. For arcade/game-center/friends/night-out concepts, use arcade, gaming, friends, night out, driving, getting ready, weekend energy, or party warmup instead.

## Visual Direction

- Default visual signature is exactly three people walking toward the viewer in a front-view composition.
- The setting should match the selected concept, not a generic Tokyo scene.
- Keep the three people centered and visually important.
- For moving clips, keep the camera moving backward at the same pace as the people so the subjects stay the same size; let the side/background motion carry the loop instead of zooming into the people.
- Thumbnail text can use large `J-POP` or a short scene/style phrase, but never `TOKYO DAYDREAM RADIO` or any channel-name brand label.

## Good Fresh Concept Shapes

- `[playlist] Rooftop Dance Pop J-POP | City Lights, Night Out and Weekend Energy`
- `[playlist] Arcade Night J-POP | Neon Games, Friends and Weekend Energy`
- `[playlist] Weekend Train Ride J-POP | Spring Streets and Feel-Good Japanese Pop`
- `[playlist] Summer Coast J-POP | Beach Walk, Seaside Train and Bright Pop`
- `[playlist] Shibuya Rain Synth-Pop | Night Commute and Japanese Vocal Pop`
- `[playlist] Kyoto Evening J-POP | Lantern Streets, New Love and Soft Pop`
- `[playlist] Osaka Weekend J-POP | Neon Friends, Karaoke and Night Out`

## Bad Directions

- Repeating anime opening, OST, or fantasy anime every time.
- Making Japan-themed BGM without vocals and calling it J-pop.
- Lyrics that literally describe the playlist setting instead of working as a standalone song.
- Forcing title/use-case words such as train ride, arcade, beach walk, commute, city lights, or walking into lyrics unless they naturally belong in the song.
- Using `일본어 J-pop`, `Japanese vocal`, or language-first titles unless the human explicitly asks.
- Reusing the same rainy Tokyo/night walk/beach/forest concept too soon.
- Adding `Tokyo` to titles when the concept is not Tokyo-specific.
- Forcing `walk` / `산책` into indoor arcade, game-center, karaoke, party, or friend-hangout concepts.
- Titles that translate into awkward keyword lists instead of natural J-pop discovery copy.
