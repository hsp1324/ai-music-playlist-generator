# Suno v6 Generation and Reuse Policy

Standing human direction, 2026-10-02 (Asia/Seoul). Applies to **all new song generation**, playlists, singles, comment requests, and channel lanes. Read before Suno Create, catalog reuse, order selection, or new-playlist render.

## Preserve the work already made

- Existing songs, images, releases, approved track lists, in-flight jobs, schedules, and published videos remain intact. Continue already-started releases; do not delete, regenerate, detach, reorder, or relabel their existing tracks just to migrate models.
- An existing v5.5-based release is grandfathered for its already attached material. Any **additional song newly generated** for it must still use v6. Preserve its existing order/brief; do not retroactively force its legacy opener to the tail.
- For a **new release** planned from this direction onward, use the eligibility and ordering rules below. This is not permission to discard the old catalog or remove a human's Good rating.

## Generate with the exact v6 model

1. Select the mandated `playlist_openclaw_desktop` Suno workspace before every Create.
2. Inspect the current model picker and select **`v6`**. Confirm the visible selection before Create; do not assume yesterday's selection persists.
3. Do not generate with v5.5/v5/unknown models. Do not silently substitute `v6-wild` or `v6-mini` for the requested standard v6. If v6 cannot be selected, preserve the work and report the actual blocker rather than falling back.
4. Keep full-song structure, original lyrics, channel/vocal-arrangement constraints, distinct singer identities, and advanced variation. Inspect actual current More options controls; do not fabricate slider settings or switch to an old model to regain legacy controls. If a required control is unavailable, record that incompatibility and pause the dependent generation rather than claim it was set.
5. Do not enable paid Max Mode, buy credits, change subscriptions, or enable a reusable voice/persona simply because the model changed.
6. Record proof with each new track: visible model label `v6`, Suno clip/source URL or ID, generation settings, and downloaded file identity. Keep a run manifest and private app/catalog provenance where supported. Existing `upload-audio --tags` can include the private catalog marker `suno_model:v6` **after verification**; this is not a public YouTube tag or proof by itself. There is no assumed `--suno-model` CLI flag.

[Official model-selection instructions](https://help.suno.com/en/articles/13924993) identify the Create-page model picker. [Suno's current-model guide](https://help.suno.com/en/articles/13924737) distinguishes v6, v6-wild, and v6-mini. [The v6 FAQ](https://help.suno.com/en/articles/13924481) states that previous songs are retained even though old generation models were retired. These sources were checked 2026-10-02; availability must still be verified in the actual signed-in UI.

## Official file acquisition when normal downloads are exhausted

Generation credits and song-download allowances are separate. `Downloads Remaining = 0` is not proof that standard v6 generation or every official export route is unavailable. [Suno's download allowance guide](https://help.suno.com/en/articles/13926209) explicitly excludes Suno Studio workflows from the normal limits; [Studio export instructions](https://help.suno.com/en/articles/13925249) document the official export controls. Verify the current plan and Studio access in the signed-in UI; do not buy downloads, enable paid modes, or change subscriptions automatically.

When Studio is available, use the existing song's **single-track full mix**, not a paid stem split, and preserve the source unchanged. Use Studio's official clip `Download .WAV`, or `Export > Full Song` and the resulting song's official Download menu. Saving to the library or seeing “unlocked” is not a completed local download. Verify an actual complete local file, duration, and successful full audio decode before uploading it to the app. Record both the original standard-v6 generation proof and the derived Studio export ID; Studio export is not a new song generation and cannot turn legacy/unknown material into v6.

On 2026-10-06, the Premier account had 9,410 generation credits and zero normal downloads. A Studio export was officially unlocked, but the managed browser's file-reception attempts timed out and Chrome recorded cancelled, zero-byte downloads. After restarting only the managed browser with its existing profile, the same official MP3 download succeeded: 219.576 seconds, 4,731,248 bytes, complete decode without errors. This establishes a working recovery, not the precise cause of the earlier cancellations. Before a similar controlled restart, confirm there is no active generation, unsaved edit, CAPTCHA, or manual-verification screen; preserve the account/profile and saved project, then reopen the same export rather than making duplicate projects. Never restart away from a human-verification screen. Never use private APIs, raw CDN URLs, or cache extraction as a download/quota workaround.

## Catalog eligibility for new releases

Apply model eligibility **in addition to**, not instead of, same-channel/lane, rights, approved/renderable file, singer/arrangement, dislike, and reuse-disabled checks.

| Candidate | New-release reuse | Position |
| --- | --- | --- |
| Verified standard Suno v6 track, otherwise compatible | Allowed | v6 main block; strongest title-relevant v6 opener |
| v5.5/v5/other legacy track with explicit human **Good** | Exception allowed if otherwise compatible | Tail only, after **all** v6 tracks; never the opening block |
| Legacy track without human Good | Not allowed | Do not attach |
| Unknown model without human Good | Not allowed; missing provenance is not v6 | Do not attach or relabel based on date/title/sound |
| Unknown/legacy model with human Good | Treat conservatively as the legacy exception | Tail only |
| v6-mini / v6-wild | Not established as standard v6 eligibility by this request | Do not generate/reuse automatically under this policy |

Good means the app's explicit human rating `user_rating="like"`; `status="approved"`, a high model score, or the agent's opinion is **not** Good. Inspect the actual rating and provenance before `reuse-track`. A private model marker is trustworthy only with the corresponding recorded generation evidence. Keep unknown entries unknown. The Good exception is for playlist tails, not permission to make a new standalone single entirely from an old-model song.

Start new releases with newly generated v6 songs. Reuse compatible verified v6 material as the v6 pool grows; do not operate an old-catalog reuse-only lane or change genres just because v6 stock is initially sparse. No arbitrary legacy reuse percentage is introduced by this request; any existing stricter channel/comment-request freshness limit still applies.

## One-hour assembly and explicit ordering

For each new automatic Playlist Release:

1. Plan a 3600-second target (`create-release --workspace-mode playlist --target-seconds 3600`) and build a genuine v6 lead/main block. Preserve channel-specific no-reuse rules such as BibliaCanto's same-passage new material.
2. Search/inspect candidates before attaching them. Catalog search is discovery, not a model eligibility check. Generate additional v6 songs whenever allowed compatible material is insufficient.
3. Check the active server back-half target (`playlist_reuse_back_half_target_seconds`, source default 3600). The no-backfill threshold is `max(3600, workspace target, active server back-half target)`; if it is configured higher, assemble that full eligible duration too. Do not assume a source default proves the deployed setting. If the target cannot be established, pause new-render submission rather than risk unfiltered fill. Attach only verified v6 songs and optional explicit-Good legacy tail tracks. Reach at least **3600 seconds of approved, renderable, policy-eligible audio before render**. Do not let server-side automatic back-half reuse select from the unfiltered old catalog to make up a shortfall.
4. Inspect the full workspace track list and provenance. Explicitly order `all v6 tracks -> optional Good legacy tail`, with a title-relevant v6 opener. The existing app endpoint `POST /playlists/{playlist_id}/tracks/reorder` accepts `track_ids`; use the established authenticated local API flow, not a guessed CLI flag.
5. Separate adjacent generated pairs within the v6 block by deliberate ordering if necessary. **Omit global `--randomize-order`** for these new releases: it can mix legacy songs into the front, and channel-specific reused-back-half behavior is not a model-version guarantee.
6. Re-read the workspace after ordering, then queue render once. Filling the approved total before render is important because the existing server automatically tries to backfill a short base block from old tracks. Do not call render on a short new workspace and hope it selects only v6.
7. Verify the rendered track/timestamp manifest still begins with v6 and places every legacy exception after the v6 block. If ordering or model eligibility cannot be verified, preserve assets and pause that new release; do not publish an unverified mixture.

This is an operator/automation procedure using existing APIs, **not a claim that the backend has acquired a new model filter**. No destructive catalog migration, retrospective rerender, or metadata bulk replacement is authorized. Existing pre-direction releases continue under their existing approved plan; later new releases follow this policy.
