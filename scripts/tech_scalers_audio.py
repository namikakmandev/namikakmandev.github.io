# -*- coding: utf-8 -*-
"""Build the soundtrack and the scene timings for film/tech-scalers.html.

Reads film/tech-scalers-narration.json, speaks every line with Piper, and
sets each scene's length to fit its narration (never shorter than the scene's
visual minimum). Under the voice sits a quiet synthesised pad, generated here
so nothing is licensed or fetched. Writes:

  film/tech-scalers-audio.wav   the mixed track, exactly as long as the film
  film/tech-scalers-cues.json   {"scenes": [[key, seconds], ...], ...}

Then: node scripts/render_canvas_film.js film/tech-scalers.html out.mp4 \
          --cues film/tech-scalers-cues.json --audio film/tech-scalers-audio.wav

With --music-only no line is spoken: each scene runs for its "min" (sized for
reading) and the track is the pad alone. Piper is not needed for that.

Needs: ffprobe on PATH, numpy, and Piper (pip install piper-tts) with a voice:
  PIPER=/path/to/piper  PIPER_MODEL=/path/to/en-us-lessac-medium.onnx
The voice tarballs live on github.com/rhasspy/piper/releases (v0.0.2).
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SPEC = os.path.join(ROOT, "film", "tech-scalers-narration.json")
OUT_WAV = os.path.join(ROOT, "film", "tech-scalers-audio.wav")
OUT_CUES = os.path.join(ROOT, "film", "tech-scalers-cues.json")
SR = 22050  # Piper's medium voices speak at 22.05 kHz; the bed is made at the same rate


def speak(line, voice, path):
    piper = os.environ.get("PIPER", "piper")
    model = os.environ.get("PIPER_MODEL")
    if not model:
        sys.exit("set PIPER_MODEL to the .onnx voice file")
    cmd = [piper, "-m", model, "-f", path,
           "--length-scale", str(voice.get("length_scale", 1.0)),
           "--sentence-silence", str(voice.get("sentence_silence", 0.2))]
    r = subprocess.run(cmd, input=line, text=True, capture_output=True)
    if r.returncode:
        sys.exit(f"piper failed: {r.stderr[-400:]}")


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, "expected 16-bit mono"
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if rate != SR:
        n = int(len(data) * SR / rate)
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype(np.float32)
    return data


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def pad_bed(total, speech_mask):
    """A slow pad: four-voice chords, each 10 s with a 3 s crossfade, soft
    partials, a gentle low-pass, ducked a little while the voice speaks."""
    n = int(total * SR)
    t = np.arange(n) / SR
    # A minor, F major, C major, G major in a low, close voicing (Hz)
    chords = [[110.0, 164.81, 220.0, 261.63], [87.31, 130.81, 174.61, 220.0],
              [130.81, 164.81, 196.0, 261.63], [98.0, 146.83, 196.0, 246.94]]
    hold, fade = 10.0, 3.0
    out = np.zeros(n, dtype=np.float32)
    k = 0
    start = 0.0
    while start < total:
        chord = chords[k % len(chords)]
        end = min(start + hold + fade, total)
        i0, i1 = int(start * SR), int(end * SR)
        seg = t[i0:i1] - start
        env = np.minimum(1, seg / fade) * np.minimum(1, (end - start - seg) / fade)
        env = np.clip(env, 0, 1)
        tone = np.zeros(i1 - i0, dtype=np.float32)
        for f in chord:
            for p, amp in ((1, 1.0), (2, 0.35), (3, 0.12)):
                tone += amp * np.sin(2 * np.pi * f * p * t[i0:i1] + 0.7 * p).astype(np.float32)
            tone += 0.6 * np.sin(2 * np.pi * (f * 1.003) * t[i0:i1]).astype(np.float32)  # slight detune
        out[i0:i1] += (tone * env).astype(np.float32)
        start += hold
        k += 1
    out /= np.max(np.abs(out)) + 1e-9
    # slow breathing on the level, then a low-pass by moving average
    out *= (0.8 + 0.2 * np.sin(2 * np.pi * t / 14.0)).astype(np.float32)
    win = np.hanning(48).astype(np.float32); win /= win.sum()
    out = np.convolve(out, win, mode="same").astype(np.float32)
    # fade in and out
    fi, fo = int(1.5 * SR), int(3.0 * SR)
    out[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    out[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    # duck under speech: smooth the mask so the level moves over ~0.4 s
    duck = np.convolve(speech_mask, np.ones(int(0.4 * SR), dtype=np.float32) / int(0.4 * SR), mode="same")
    level = 0.07 * (1 - 0.5 * np.clip(duck, 0, 1))
    return out * level.astype(np.float32)


def main():
    spec = json.load(open(SPEC))
    voice = spec["voice"]
    lead, tail = spec.get("lead", 0.3), spec.get("tail", 0.5)
    music_only = "--music-only" in sys.argv
    tmp = tempfile.mkdtemp(prefix="tech-scalers-tts-")
    clips, scenes = [], []
    t0 = 0.0
    for sc in spec["scenes"]:
        if music_only:
            audio, dur, length = np.zeros(0, dtype=np.float32), 0.0, float(sc["min"])
        else:
            path = os.path.join(tmp, sc["key"] + ".wav")
            speak(sc["line"], voice, path)
            audio = read_wav(path)
            dur = len(audio) / SR
            length = max(float(sc["min"]), lead + dur + tail)
        clips.append((t0 + lead, audio))
        scenes.append([sc["key"], round(length, 2)])
        print(f"{sc['key']:10s} speech {dur:5.2f}s  scene {length:5.2f}s  starts {t0:6.2f}s")
        t0 += length
    total = round(t0, 2)
    n = int(total * SR)
    mix = np.zeros(n, dtype=np.float32)
    mask = np.zeros(n, dtype=np.float32)
    for start, audio in clips:
        i0 = int(start * SR); i1 = min(n, i0 + len(audio))
        mix[i0:i1] += audio[: i1 - i0]
        mask[i0:i1] = 1
    if not music_only:
        mix *= 0.85 / (np.max(np.abs(mix)) + 1e-9)
        write_wav(OUT_WAV.replace(".wav", "-voice.wav"), mix)   # narration alone, for checking
    mix += pad_bed(total, mask)
    if music_only:   # the bed is the whole track: bring it to a normal level
        mix *= 0.3 / (np.max(np.abs(mix)) + 1e-9)
    write_wav(OUT_WAV, mix)
    json.dump({"scenes": scenes, "total": total, "audio": os.path.relpath(OUT_WAV, ROOT), "voice": not music_only,
               "sample_rate": SR, "source": os.path.relpath(SPEC, ROOT)}, open(OUT_CUES, "w"), indent=1)
    print(f"total {total}s -> {os.path.relpath(OUT_WAV, ROOT)}, {os.path.relpath(OUT_CUES, ROOT)}")


if __name__ == "__main__":
    main()
