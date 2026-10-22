---
name: suno-studio-acquisition
description: Download owned standard-v6 Suno songs through Premier Studio, including known missing files from a current production batch. Use when normal song downloads are exhausted or generated audio is missing locally.
---

# Suno Studio Acquisition

Work from the existing AI Music runtime checkout. Keep the shared app-side browser/release lock, original songs, generation provenance, lyrics/settings and server-managed publishing. The human cancelled broad historical Library recovery after confirming the Studio route already worked. Standing audio pre-approval applies; do not introduce listening/QC or per-song approval gates.

Before any historical-library browsing, run this skill's `scripts/recovery_state.py --state STATE status`. Use one persistent state file: the runtime checkout's `storage/suno-studio-recovery.json`, shared across sessions. Do not keep recovery state in a temporary run directory or the installed skill directory.

| State/action | Next step |
| --- | --- |
| `needs_initial_inventory` | Do not start historical discovery without fresh explicit human authorization. Use the guide only for known current-batch IDs. |
| `resume_inventory` | Continue from the saved cursor and frozen cutoff; save each page. Do not restart the library from page one. |
| `recover_known_tracks` | Work only the returned known source IDs. Save and ingest recovered music before generating replacements. A temporary failure stays pending; it is not completion. |
| `fresh_production` | **Do not search old library pages, scan missing downloads, read the historical inventory, or run recovery again.** Continue the regular producer. Read the download steps only when acquiring a known current-batch song. |

Use the official UI: the owned song's `…` menu → `Edit` → `Open in Studio`, then the original full-mix clip's `Download .WAV` or `Export` → `Full Song`. Never choose stems/MIDI, selected-range exports, new generation, remix or paid controls just to acquire the original file. The guide distinguishes the official source facts from local automation decisions and describes file verification and bounded recovery.

Use original Suno source ID as the identity, not title or derived Studio export ID. Reconcile that ID with existing manifests/app receipts to avoid duplicate downloads/uploads. A downloaded file is not accepted until its real audio stream, duration and full decode pass; a library export or an “unlocked” label alone does not count. Record the official Studio project/export separately from the original standard-v6 proof.

The current historical batch is cancelled, not complete. Preserve its audit records and do not read pending historical entries. Never reactivate historical discovery on a later pass without fresh explicit human authorization. Failed downloads of newly generated songs are retried by their current run's known IDs, not by reopening the cancelled recovery.

For playlists, prioritize compatible v6 material already assigned to the target release and finish ready releases before replacements. Keep channel/lane/scripture constraints, original assignments and one-hour assembly. Generate only a genuine compatible shortfall. New playlists are v6-only under the 2026-10-20 policy. Rendering/publishing uses the existing app helpers; the server owns Wednesday scheduling.
