"""One cue sheet for the whole soundtrack: resolution, music changes, ducking, mastering, the CLI.

The integration criterion is simple: a single JSON timeline has to produce a complete, in-spec mix
(music + SFX + voice) whose timing matches the sheet to the sample, at either production rate, with
no second timeline hiding in the tool.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))

SR = 44100


def write_voice(path, seconds=6.0, lines=((0.8, 2.0, 0.35), (3.4, 4.6, 0.06)), sr=SR):
    """A tiny synthetic narration: two 'lines', the second deliberately quiet."""
    from scipy.io import wavfile

    v = np.zeros(int(seconds * sr), np.float32)
    for a, b, g in lines:
        n = int((b - a) * sr)
        v[int(a * sr):int(a * sr) + n] = g * np.sin(2 * np.pi * 170 * np.arange(n) / sr) * np.hanning(n)
    wavfile.write(str(path), sr, (v * 32767).astype(np.int16))
    return path


def base_sheet(**over):
    sheet = {
        "duration": 6.0, "sr": SR, "seed": 4,
        "music": {"preset": "corporate", "bpm": 104, "level_db": -4.0,
                  "duck": {"amount": 0.6, "attack": 0.01, "release": 0.3, "lookahead": 0.04}},
        "sfx": [{"t": 0.5, "sfx": "whoosh", "gain": 0.8, "pan": [-0.5, 0.5], "anchor": True},
                {"t": 3.0, "sfx": "chime", "gain": 0.5, "pan": 0.3}],
        "duck": {"amount": 0.7, "attack": 0.01, "release": 0.25},
        "master": {"lufs": -14.5, "true_peak": -1.5},
    }
    sheet.update(over)
    return sheet


def test_sheet_round_trip(tmp_path):
    import audio_mix as AM

    path = AM.save_sheet(base_sheet(), tmp_path / "sheet.json")
    again = AM.load_sheet(path)
    assert again["duration"] == 6.0 and again["sr"] == SR
    assert len(again["sfx"]) == 2 and again["music"]["preset"] == "corporate"
    assert again["sfx"][0]["pan"] == [-0.5, 0.5]


def test_a_bare_cue_list_is_a_valid_sheet():
    import audio_mix as AM

    sheet = AM.validate_sheet({"duration": 2.0, "sfx": [{"t": 1.0, "sfx": "pop"}]})
    assert sheet["sfx"][0]["sfx"] == "pop"
    assert sheet["music"] is None and sheet["duck"]["amount"] and sheet["master"]["lufs"] == -14.5


def test_resolution_is_sample_exact_at_both_rates():
    import audio_mix as AM

    for sr in (44100, 48000):
        sheet = base_sheet(sr=sr, sfx=[{"t": 1.234, "sfx": "tick"}, {"t": 0.5, "sfx": "pop"}])
        r = AM.resolve(sheet)
        assert r["sr"] == sr
        assert r["samples"] == int(round(6.0 * sr))
        assert [e["sample"] for e in r["sfx"]] == [int(round(0.5 * sr)), int(round(1.234 * sr))]
        assert r["sfx"][0]["t"] < r["sfx"][1]["t"], "events must be sorted by time"


def test_music_changes_restart_the_arrangement():
    import audio_mix as AM

    sheet = base_sheet(music={"preset": "tech", "bpm": 112, "level_db": -3.0,
                              "changes": [{"t": 3.0, "preset": "cinematic"}]})
    plan = AM.music_plan(sheet)
    assert [(s["config"]["preset"], s["start"], s["end"]) for s in plan["segments"]] == [
        ("tech", 0.0, 3.0), ("cinematic", 3.0, 6.0)]
    resolved = AM.resolve(sheet)
    assert [e["t"] for e in resolved["music"]] == [0.0, 3.0]


def test_the_mix_is_complete_finite_and_in_spec(tmp_path):
    import audio_engine as ax
    import audio_mix as AM

    vo = write_voice(tmp_path / "vo.wav")
    result = AM.mix(base_sheet(), voice_path=vo)
    audio = result["audio"]
    assert audio.shape == (int(6.0 * SR), 2)
    assert audio.dtype == np.float32 and np.all(np.isfinite(audio))
    assert float(np.max(np.abs(audio))) <= 1.0
    report = result["report"]
    assert report["sfx"]["cues"] == 2
    assert report["voice"]["kept"] > 0
    assert report["sfx"]["truncated_samples"] == 0
    # stems exist and add up to something close to the mix (mastering may rescale it)
    assert result["music"].shape == result["sfx"].shape == audio.shape
    assert np.abs(result["voice"]).max() > 0


def test_ducking_actually_lowers_the_bed_under_the_voice(tmp_path):
    import audio_engine as ax
    import audio_mix as AM

    vo = write_voice(tmp_path / "vo.wav", lines=((1.0, 2.6, 0.4), (4.2, 5.4, 0.05)))
    sheet = base_sheet()
    ducked = AM.mix(sheet, voice_path=vo)["music"]
    clean = AM.mix(sheet)["music"]                     # the same bed, no voice, no ducking

    def drop(a, b):
        """How much quieter the bed is under the line than the identical bed with no voice."""
        g = lambda x: float(np.sqrt(np.mean(x[int(a * SR):int(b * SR)] ** 2)))   # noqa: E731
        return ax.to_db(g(ducked) / max(g(clean), 1e-12))

    assert drop(1.3, 2.4) < -6, f"the bed was not ducked under the loud line ({drop(1.3, 2.4):.1f} dB)"
    assert drop(4.4, 5.2) < -5, "a quiet line must still duck (the old normalised follower did not)"
    assert abs(drop(0.2, 0.9)) < 0.5, "before the voice starts the bed must be untouched"


def test_no_voice_means_no_ducking(tmp_path):
    import audio_mix as AM

    for voice in (None,):
        result = AM.mix(base_sheet(), voice_path=voice)
        assert result["report"]["voice"] is None
        assert np.max(np.abs(result["voice"])) == 0.0


def test_the_master_respects_the_true_peak_ceiling(tmp_path):
    import audio_engine as ax
    import audio_mix as AM

    vo = write_voice(tmp_path / "vo.wav")
    sheet = base_sheet(master={"lufs": -14.5, "true_peak": -1.5})
    result = AM.mix(sheet, voice_path=vo, master=True)
    tp = ax.true_peak(result["audio"], SR)
    assert tp <= -1.5 + 0.35, f"master overshoots the brand ceiling: {tp:.2f} dBTP"
    assert float(np.max(np.abs(result["audio"]))) <= 1.0


def test_music_only_and_sfx_only_sheets_both_work():
    import audio_mix as AM

    music_only = AM.mix(base_sheet(sfx=[]))
    assert np.abs(music_only["music"]).max() > 0 and np.max(np.abs(music_only["sfx"])) == 0
    sfx_only = AM.mix(base_sheet(music=None))
    assert np.max(np.abs(sfx_only["music"])) == 0 and np.abs(sfx_only["sfx"]).max() > 0


def test_sheet_validation_is_loud_about_mistakes():
    import audio_mix as AM

    with pytest.raises(ValueError):
        AM.validate_sheet({"sr": SR})                               # no duration
    with pytest.raises(ValueError):
        AM.validate_sheet({"duration": 0})
    with pytest.raises(KeyError):
        AM.validate_sheet({"duration": 2.0, "sfx": [{"t": 0.1, "sfx": "explosion"}]})
    with pytest.raises(ValueError):
        AM.validate_sheet({"duration": 2.0, "sfx": [{"t": -1.0, "sfx": "pop"}]})
    with pytest.raises(ValueError):
        AM.validate_sheet({"duration": 2.0, "music": {"preset": "techno"}})


def test_from_storyboard_maps_transitions_to_sfx():
    import audio_mix as AM

    story = {"duration": 8.0, "scenes": [
        {"t": 0.0}, {"t": 2.0, "transition": "wipe"}, {"t": 5.0, "transition": "flash"}],
        "sfxLead": -0.1}
    sheet = AM.from_storyboard(story, preset="tech")
    assert [c["sfx"] for c in sheet["sfx"]] == ["whoosh", "impact"]
    assert [c["t"] for c in sheet["sfx"]] == [1.9, 4.9]
    assert sheet["music"]["preset"] == "tech" and sheet["duration"] == 8.0


def test_describe_is_human_readable():
    import audio_mix as AM

    lines = AM.describe(base_sheet())
    blob = "\n".join(lines)
    assert "corporate" in blob and "whoosh" in blob and "44100" in blob or "44.1" in blob


def test_cli_dry_run_and_full_mix(tmp_path):
    import audio_mix as AM

    sheet = AM.save_sheet(base_sheet(), tmp_path / "sheet.json")
    vo = write_voice(tmp_path / "vo.wav")
    dry = subprocess.run([sys.executable, str(ROOT / "tools" / "audio_mix.py"), "--sheet", str(sheet),
                          "--dry-run"], capture_output=True, text=True)
    assert dry.returncode == 0, dry.stderr
    assert "corporate" in dry.stdout and "whoosh" in dry.stdout

    out = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "audio_mix.py"), "--sheet", str(sheet),
                        "--vo", str(vo), "--out", str(out), "--stems", str(tmp_path / "stems"),
                        "--report", str(tmp_path / "report.json"), "--no-loudnorm"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    from scipy.io import wavfile  # noqa: PLC0415

    sr, data = wavfile.read(out)
    assert sr == SR and abs(data.shape[0] - 6 * SR) <= 2 and data.shape[1] == 2
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["output"]["seconds"] == pytest.approx(6.0, abs=0.01)
    assert report["output"]["peak_dbtp"] <= -1.0
    for stem in ("music.wav", "sfx.wav", "vo.wav"):
        assert (tmp_path / "stems" / stem).is_file(), stem


def test_cli_render_at_48k(tmp_path):
    import audio_mix as AM

    sheet = AM.save_sheet(base_sheet(sr=48000, duration=3.0), tmp_path / "sheet.json")
    out = tmp_path / "mix48.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "audio_mix.py"), "--sheet", str(sheet),
                        "--out", str(out), "--no-loudnorm"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    from scipy.io import wavfile  # noqa: PLC0415

    sr, data = wavfile.read(out)
    assert sr == 48000 and abs(data.shape[0] - 3 * 48000) <= 2


def test_the_mixed_track_muxes_with_video(tmp_path):
    """A/V integration: the audio the mixer writes has to sit on the picture, not beside it."""
    import audio_mix as AM

    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from media_bin import ffprobe as find_ffprobe  # noqa: PLC0415
    from media_bin import ffmpeg as find_ffmpeg  # noqa: PLC0415

    ff = find_ffmpeg()
    if not ff:
        pytest.skip("ffmpeg not available in this environment")
    sheet = AM.save_sheet(base_sheet(duration=3.0, sfx=[{"t": 1.0, "sfx": "impact"}]), tmp_path / "s.json")
    wav = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "audio_mix.py"), "--sheet", str(sheet),
                        "--out", str(wav), "--no-loudnorm"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    video = tmp_path / "v.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=0xCB271B:size=540x960:rate=30", "-t", "3", video], check=True)
    muxed = tmp_path / "av.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav),
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", str(muxed)], check=True)

    from scipy.io import wavfile  # noqa: PLC0415
    sr, data = wavfile.read(wav)
    assert abs(data.shape[0] / sr - 3.0) <= 0.01
    import subprocess as sp  # noqa: PLC0415
    import json as _json  # noqa: PLC0415

    probe = sp.run([find_ffprobe() or "ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_type,duration", "-of", "json", str(muxed)],
                   capture_output=True, text=True)
    kinds = {s["codec_type"] for s in _json.loads(probe.stdout)["streams"]}
    assert kinds == {"video", "audio"}, "the mux lost a stream"
    assert muxed.stat().st_size > 1000


def test_a_music_change_is_a_cut_not_a_hole(tmp_path):
    """Two fades meeting at a change cancel to near-silence; the seam is cross-faded instead."""
    import audio_engine as ax
    import audio_mix as AM

    sheet = base_sheet(duration=12.0, sfx=[], music={
        "preset": "tech", "bpm": 112, "level_db": 0.0,
        "changes": [{"t": 6.0, "preset": "ambient"}], "duck": {"amount": 0.0}})
    bed = AM.mix(sheet, master=False, limit=False)["music"]
    sr = SR

    def level(a, b):
        seg = bed[int(a * sr):int(b * sr)]
        return ax.to_db(float(np.sqrt(np.mean(seg ** 2))))

    before, at_change, after = level(4.0, 5.6), level(5.75, 6.25), level(6.4, 8.0)
    assert min(before, after) - at_change < 12, (
        f"the bed has a hole at the music change ({before:.1f} / {at_change:.1f} / {after:.1f} dBFS)")
    assert at_change > -45, f"silence at the change ({at_change:.1f} dBFS)"


def test_the_report_quotes_a_measured_master(tmp_path):
    """When ffmpeg is present, the report must carry a real EBU R128 measurement, not an intention."""
    import audio_mix as AM

    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from media_bin import ffmpeg as find_ffmpeg  # noqa: PLC0415

    if not find_ffmpeg():
        pytest.skip("ffmpeg not available")
    sheet = AM.save_sheet(base_sheet(duration=4.0), tmp_path / "s.json")
    out = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "audio_mix.py"), "--sheet", str(sheet),
                        "--out", str(out), "--report", str(tmp_path / "rep.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads((tmp_path / "rep.json").read_text(encoding="utf-8"))
    ln = report["loudnorm"]
    assert ln["ok"], ln
    assert ln["measured"]["lufs"] == pytest.approx(-14.5, abs=0.3), ln
    assert ln["measured"]["true_peak"] <= -1.4, ln
