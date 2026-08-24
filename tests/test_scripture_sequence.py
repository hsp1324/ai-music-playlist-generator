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


def test_scripture_sequence_continues_after_biblia_current_edges(tmp_path) -> None:
    old_complete = complete_scripture_passage(
        tmp_path,
        channel_title="The Old Verse",
        passage_range="Genesis 11:10-32",
        status="scheduled",
        release_id="old-current-edge",
    )
    new_complete = complete_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        passage_range="Matthew 8:1-4",
        status="scheduled",
        release_id="new-current-edge",
    )

    assert old_complete["next_start"] == "Genesis 12:1"
    assert new_complete["next_start"] == "Matthew 8:5"

    status = scripture_sequence_status(tmp_path)

    assert status["next_suggestions"]["the_old_verse"]["passage_range"] == "Genesis 12:1-9"
    assert status["next_suggestions"]["the_old_verse"]["next_start_after_completion"] == "Genesis 12:10"
    assert status["next_suggestions"]["the_new_verse"]["passage_range"] == "Matthew 8:5-13"
    assert status["next_suggestions"]["the_new_verse"]["next_start_after_completion"] == "Matthew 8:14"


def test_scripture_sequence_continues_after_matthew_ten_twenty_five(tmp_path) -> None:
    complete_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        passage_range="Matthew 10:16-25",
        release_id="matthew-ten-persecution",
        status="scheduled",
    )

    reserved = reserve_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        release_id="matthew-ten-fearless",
        title="[playlist] Matthew 10:26-33 New Testament Scripture Songs",
    )

    assert reserved["entry"]["passage_range"] == "Matthew 10:26-33"
    assert reserved["entry"]["next_start_after_completion"] == "Matthew 10:34"


def test_scripture_sequence_continues_into_genesis_eighteen(tmp_path) -> None:
    complete_scripture_passage(
        tmp_path,
        channel_title="The Old Verse",
        passage_range="Genesis 17:1-27",
        release_id="genesis-seventeen-covenant",
        status="scheduled",
    )

    reserved = reserve_scripture_passage(
        tmp_path,
        channel_title="The Old Verse",
        release_id="genesis-eighteen-promise",
        title="[playlist] Genesis 18:1-15 Promise at the Tent Scripture Songs",
    )

    assert reserved["entry"]["passage_range"] == "Genesis 18:1-15"
    assert reserved["entry"]["next_start_after_completion"] == "Genesis 18:16"


def test_scripture_sequence_continues_into_matthew_ten(tmp_path) -> None:
    complete_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        passage_range="Matthew 9:35-38",
        release_id="matthew-nine",
        status="scheduled",
    )

    reserved = reserve_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        release_id="matthew-ten",
        title="[playlist] Matthew 10:1-15 New Testament Scripture Songs",
    )

    assert reserved["entry"]["passage_range"] == "Matthew 10:1-15"
    assert reserved["entry"]["next_start_after_completion"] == "Matthew 10:16"


def test_scripture_sequence_continues_through_matthew_ten_mission_warning(tmp_path) -> None:
    complete_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        passage_range="Matthew 10:1-15",
        release_id="matthew-ten-sent",
        status="scheduled",
    )

    reserved = reserve_scripture_passage(
        tmp_path,
        channel_title="New Testament",
        release_id="matthew-ten-warning",
        title="[playlist] Matthew 10:16-25 New Testament Scripture Songs",
    )

    assert reserved["entry"]["passage_range"] == "Matthew 10:16-25"
    assert reserved["entry"]["next_start_after_completion"] == "Matthew 10:26"
