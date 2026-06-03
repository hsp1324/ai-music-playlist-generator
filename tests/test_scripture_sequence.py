from app.workflows.scripture_sequence import (
    complete_scripture_passage,
    reserve_scripture_passage,
    scripture_sequence_status,
)


def test_scripture_sequence_continues_after_current_ledger_edges(tmp_path) -> None:
    complete_scripture_passage(
        tmp_path,
        channel_title="The Old Verse",
        passage_range="Genesis 2:18-25",
        status="scheduled",
        release_id="old-edge",
    )
    complete_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        passage_range="Matthew 4:12-25",
        status="scheduled",
        release_id="new-edge",
    )

    status = scripture_sequence_status(tmp_path)

    assert status["next_suggestions"]["the_old_verse"]["passage_range"] == "Genesis 3:1-7"
    assert status["next_suggestions"]["the_old_verse"]["next_start_after_completion"] == "Genesis 3:8"
    assert status["next_suggestions"]["the_new_verse"]["passage_range"] == "Matthew 5:1-12"
    assert status["next_suggestions"]["the_new_verse"]["next_start_after_completion"] == "Matthew 5:13"

    old_reservation = reserve_scripture_passage(
        tmp_path,
        channel_title="The Old Verse",
        release_id="old-next",
        title="[playlist] Genesis 3:1-7 Scripture Hip-Hop",
    )
    new_reservation = reserve_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        release_id="new-next",
        title="[playlist] Matthew 5:1-12 New Testament R&B",
    )

    assert old_reservation["entry"]["passage_range"] == "Genesis 3:1-7"
    assert new_reservation["entry"]["passage_range"] == "Matthew 5:1-12"
