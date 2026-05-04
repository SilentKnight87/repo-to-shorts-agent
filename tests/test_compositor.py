from __future__ import annotations

import subprocess
from pathlib import Path

from repo_to_shorts.compositor import (
    EDGE_TTS_PITCH,
    EDGE_TTS_RATE,
    EDGE_TTS_VOICE,
    _escape_drawtext,
    compose,
    generate_ambient_music,
    generate_tts,
    mix_audio,
)


def test_compose_calls_ffmpeg_correctly(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        prog = command[0]
        if prog == "edge-tts":
            out = Path(command[command.index("--write-media") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake mp3")
        elif prog == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)
    monkeypatch.setattr("repo_to_shorts.compositor._ffmpeg_has_filter", lambda name: name == "drawtext")

    scenes = [
        {"video_path": tmp_path / "scene0.mp4", "narration": "Hello world", "duration_seconds": 2},
        {"video_path": tmp_path / "scene1.mp4", "narration": "Second scene", "duration_seconds": 3},
    ]
    output_path = tmp_path / "final.mp4"
    music_path = tmp_path / "music.mp3"

    result = compose(scenes, output_path, music_path)

    assert result == output_path.resolve()

    tts_cmds = [cmd for cmd in commands if cmd[0] == "edge-tts"]
    assert len(tts_cmds) == 2
    assert "Hello world" in tts_cmds[0]
    assert "Second scene" in tts_cmds[1]

    ffmpeg_cmds = [cmd for cmd in commands if cmd[0] == "ffmpeg"]
    assert any("amix" in " ".join(cmd) for cmd in ffmpeg_cmds)
    assert any("drawtext" in " ".join(cmd) for cmd in ffmpeg_cmds)
    assert any("copy" in cmd for cmd in ffmpeg_cmds)
    assert any("concat" in cmd for cmd in ffmpeg_cmds)


def test_generate_tts_calls_edge_tts(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        prog = command[0]
        if prog == "edge-tts":
            out = Path(command[command.index("--write-media") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake mp3")
        elif prog == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)
    monkeypatch.setattr("repo_to_shorts.compositor._ffmpeg_has_filter", lambda name: name == "drawtext")

    output = tmp_path / "tts.wav"
    result = generate_tts("Test narration", output)

    assert result == output.resolve()

    tts_cmds = [cmd for cmd in commands if cmd[0] == "edge-tts"]
    assert len(tts_cmds) == 1
    assert "Test narration" in tts_cmds[0]
    assert "--voice" in tts_cmds[0]
    assert EDGE_TTS_VOICE in tts_cmds[0]
    assert "--rate" in tts_cmds[0]
    assert EDGE_TTS_RATE in tts_cmds[0]
    assert "--pitch" in tts_cmds[0]
    assert EDGE_TTS_PITCH in tts_cmds[0]
    assert "--volume" in tts_cmds[0]

    ffmpeg_cmds = [cmd for cmd in commands if cmd[0] == "ffmpeg"]
    assert len(ffmpeg_cmds) == 1


def test_generate_tts_fails_loudly_without_implicit_say_fallback(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "edge-tts":
            raise FileNotFoundError("edge-tts missing")
        msg = "say fallback should not run unless explicitly requested"
        raise AssertionError(msg)

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    output = tmp_path / "tts.wav"
    try:
        generate_tts("Test narration", output)
    except RuntimeError as exc:
        assert "Edge TTS failed" in str(exc)
    else:
        raise AssertionError("generate_tts should fail when Edge TTS is unavailable")

    assert [cmd[0] for cmd in commands] == ["edge-tts"]


def test_generate_tts_allows_explicit_say_fallback(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        prog = command[0]
        if prog == "edge-tts":
            raise subprocess.CalledProcessError(1, command)
        if prog == "say":
            out = Path(command[command.index("-o") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake aiff")
        elif prog == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    output = tmp_path / "tts.wav"
    result = generate_tts("Draft narration", output, allow_say_fallback=True)

    assert result == output.resolve()
    assert [cmd[0] for cmd in commands] == ["edge-tts", "say", "ffmpeg"]


def test_generate_tts_uses_xai_provider(monkeypatch, tmp_path: Path):
    requests = []
    commands = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"fake mp3"

    def fake_urlopen(request, timeout=60):
        requests.append(request)
        return FakeResponse()

    def fake_run(command, **kwargs):
        commands.append(command)
        out = Path(command[-1])
        out.write_bytes(b"fake wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("XAI_API_KEY", "test-xai")
    monkeypatch.setattr("repo_to_shorts.compositor.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    result = generate_tts("Ship this repo.", tmp_path / "tts.wav", provider="xai", voice="orpheus")

    assert result == (tmp_path / "tts.wav").resolve()
    assert requests
    assert requests[0].full_url == "https://api.x.ai/v1/tts"
    assert requests[0].headers["Authorization"] == "Bearer test-xai"
    assert b"Ship this repo." in requests[0].data
    assert b"orpheus" in requests[0].data
    assert commands[0][0] == "ffmpeg"


def test_generate_tts_falls_back_from_xai_to_openai(monkeypatch, tmp_path: Path):
    urls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"fake mp3"

    def fake_urlopen(request, timeout=60):
        urls.append(request.full_url)
        if "x.ai" in request.full_url:
            raise OSError("xai down")
        return FakeResponse()

    monkeypatch.setenv("XAI_API_KEY", "test-xai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr("repo_to_shorts.compositor.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "repo_to_shorts.compositor.subprocess.run",
        lambda command, **kwargs: (Path(command[-1]).write_bytes(b"fake wav"), subprocess.CompletedProcess(command, 0, "", ""))[1],
    )

    result = generate_tts("Fallback voice.", tmp_path / "tts.wav", provider="xai", fallback_provider="openai")

    assert result == (tmp_path / "tts.wav").resolve()
    assert urls == ["https://api.x.ai/v1/tts", "https://api.openai.com/v1/audio/speech"]


def test_generate_tts_none_provider_raises_clear_error(tmp_path: Path):
    try:
        generate_tts("No voice.", tmp_path / "tts.wav", provider="none")
    except RuntimeError as exc:
        assert "TTS provider is none" in str(exc)
    else:
        raise AssertionError("provider=none should not generate audio")


def test_mix_audio_with_music(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake audio")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    voice = tmp_path / "voice.wav"
    music = tmp_path / "music.mp3"
    output = tmp_path / "mixed.aac"

    result = mix_audio(voice, music, output, 5)

    assert result == output.resolve()
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd[0] == "ffmpeg"
    assert "amix=inputs=2:duration=longest:dropout_transition=0" in " ".join(cmd)
    assert "apad[voice]" in " ".join(cmd)
    assert "volume=0.18" in " ".join(cmd)
    assert "sidechaincompress" in " ".join(cmd)
    assert "alimiter=limit=0.95" in " ".join(cmd)
    assert "-stream_loop" in cmd


def test_mix_audio_without_music(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake audio")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    voice = tmp_path / "voice.wav"
    output = tmp_path / "mixed.aac"

    result = mix_audio(voice, None, output, 5)

    assert result == output.resolve()
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd[0] == "ffmpeg"
    assert "loudnorm=I=-16:TP=-1.5:LRA=11" in " ".join(cmd)


def test_generate_ambient_music_uses_electronic_lavfi_synth(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        out = Path(command[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake mp3")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    output = tmp_path / "music.mp3"
    result = generate_ambient_music(output, duration=12)

    assert result == output.resolve()
    assert len(commands) == 1
    cmd = commands[0]
    joined = " ".join(cmd)
    assert cmd[0] == "ffmpeg"
    assert "lavfi" in cmd
    assert "aevalsrc=" in joined
    assert "sin(2*PI*55*t)" in joined
    assert "tremolo=f=4.5" in joined
    assert "anoisesrc" not in joined
    assert "color=brown" not in joined


def test_burn_captions_escapes_text():
    assert _escape_drawtext("hello:world") == "hello\\:world"
    assert _escape_drawtext("it's") == "it\\'s"
    assert _escape_drawtext("path\\to\\file") == "path\\\\to\\\\file"
    assert _escape_drawtext("a:b'c\\d") == "a\\:b\\'c\\\\d"
