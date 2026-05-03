from __future__ import annotations

import subprocess
from pathlib import Path

from repo_to_shorts.compositor import (
    _escape_drawtext,
    compose,
    generate_tts,
    mix_audio,
)


def test_compose_calls_ffmpeg_correctly(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        prog = command[0]
        if prog == "say":
            idx = command.index("-o")
            out = Path(command[idx + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake aiff")
        elif prog == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    scenes = [
        {"video_path": tmp_path / "scene0.mp4", "narration": "Hello world", "duration_seconds": 2},
        {"video_path": tmp_path / "scene1.mp4", "narration": "Second scene", "duration_seconds": 3},
    ]
    output_path = tmp_path / "final.mp4"
    music_path = tmp_path / "music.mp3"

    result = compose(scenes, output_path, music_path)

    assert result == output_path.resolve()

    say_cmds = [cmd for cmd in commands if cmd[0] == "say"]
    assert len(say_cmds) == 2
    assert "Hello world" in say_cmds[0]
    assert "Second scene" in say_cmds[1]

    ffmpeg_cmds = [cmd for cmd in commands if cmd[0] == "ffmpeg"]
    assert any("amix" in " ".join(cmd) for cmd in ffmpeg_cmds)
    assert any("drawtext" in " ".join(cmd) for cmd in ffmpeg_cmds)
    assert any("copy" in cmd for cmd in ffmpeg_cmds)
    assert any("concat" in cmd for cmd in ffmpeg_cmds)


def test_generate_tts_calls_say(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        prog = command[0]
        if prog == "say":
            idx = command.index("-o")
            out = Path(command[idx + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake aiff")
        elif prog == "ffmpeg":
            out = Path(command[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    output = tmp_path / "tts.wav"
    result = generate_tts("Test narration", output)

    assert result == output.resolve()

    say_cmds = [cmd for cmd in commands if cmd[0] == "say"]
    assert len(say_cmds) == 1
    assert "Test narration" in say_cmds[0]
    assert "-o" in say_cmds[0]

    ffmpeg_cmds = [cmd for cmd in commands if cmd[0] == "ffmpeg"]
    assert len(ffmpeg_cmds) == 1


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
    assert "amix=inputs=2:duration=first:dropout_transition=0" in " ".join(cmd)
    assert "volume=0.25" in " ".join(cmd)


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


def test_burn_captions_escapes_text():
    assert _escape_drawtext("hello:world") == "hello\\:world"
    assert _escape_drawtext("it's") == "it\\'s"
    assert _escape_drawtext("path\\to\\file") == "path\\\\to\\\\file"
    assert _escape_drawtext("a:b'c\\d") == "a\\:b\\'c\\\\d"
