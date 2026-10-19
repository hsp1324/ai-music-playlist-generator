from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vocal_arrangement_policy_is_wired_into_openclaw_sources() -> None:
    policy_path = ROOT / "docs" / "openclaw-vocal-arrangement-policy.md"
    policy = policy_path.read_text(encoding="utf-8")
    normalized_policy = " ".join(policy.lower().split())

    assert "themed orchestral vocal" in normalized_policy
    assert "piano-only vocal" in normalized_policy
    assert "guitar-only acoustic vocal" in normalized_policy
    assert "do not mix families within one playlist" in normalized_policy

    for relative_path in (
        "docs/openclaw-skills.md",
        "docs/openclaw-suno-advanced-variation.md",
        "docs/openclaw-channel-genre-taxonomy.md",
        "docs/openclaw-channel-concepts/README.md",
        "docs/openclaw-channel-concepts/haruharu.md",
        "docs/openclaw-channel-concepts/tokyo-daydream-radio.md",
        "docs/openclaw-channel-concepts/sundaze.md",
        "docs/openclaw-channel-concepts/solwave-radio.md",
        "docs/openclaw-channel-concepts/bulsong.md",
        "docs/openclaw-channel-concepts/the-old-verse.md",
        "README.md",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "openclaw-vocal-arrangement-policy.md" in source


def test_vocal_reuse_requires_the_same_arrangement_family() -> None:
    policy = (
        ROOT / "docs" / "openclaw-vocal-arrangement-policy.md"
    ).read_text(encoding="utf-8")

    assert "same arrangement" in policy
    assert "publish the coherent shorter" in policy
