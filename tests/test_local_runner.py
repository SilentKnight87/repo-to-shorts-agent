from pathlib import Path


def test_local_final_runner_is_executable_and_pins_default_workflow():
    script = Path("scripts/run-local-final.sh")

    assert script.exists()
    assert script.stat().st_mode & 0o111

    text = script.read_text(encoding="utf-8")
    assert 'TARGET="${1:-.}"' in text
    assert 'KIMI_MODEL="${KIMI_MODEL:-moonshotai/kimi-k2.6}"' in text
    assert 'TTS_PROVIDER="${TTS_PROVIDER:-xai}"' in text
    assert 'FALLBACK_TTS_PROVIDER="${FALLBACK_TTS_PROVIDER:-openai}"' in text
    assert '.venv/bin/repo-shorts creative "$TARGET"' in text
    assert '--kimi-model "$KIMI_MODEL"' in text
    assert '--tts-provider "$TTS_PROVIDER"' in text
    assert '--fallback-tts-provider "$FALLBACK_TTS_PROVIDER"' in text
    assert "--final" in text
    assert "metadata.json" in text
    assert "demo.mp4" in text
    assert 'REQUIRE_LIVE_KIMI="${REQUIRE_LIVE_KIMI:-1}"' in text
    assert '.kimi.mode // ""' in text
    assert "requires live Kimi" in text
