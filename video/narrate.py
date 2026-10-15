"""Narration, subtitles and music for the Turno demo.

Built from heatline's narrator (Hackathons/DEMO-RECORDING standard): every line
is keyed to the beat whose picture it describes, a line that overruns its beat
is a build error, subtitles come from the same cue sheet as the voice, and the
music is capped to the video so the streams end together.

The voice is Gemini TTS, directed to read like a person walking a colleague
through a screen: unhurried, with natural breaths and the odd soft "hm". The
voice is synthetic and the README says so.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "voice"
MARKS = HERE / "narration.json"
OUT = HERE / "narration.m4a"
VIDEO = HERE / "turno-demo.mp4"
SRT = HERE / "turno-demo.srt"
ENV = next((d / ".env" for d in HERE.parents if (d / ".env").is_file()), None)

# gemini-2.5-flash-preview-tts speaks only the line and applies the direction; the
# 3.8 models read the direction aloud (checked by transcribing the clips).
# Default voice since 16 Oct: Breeze TTS 2, open weights, run on this Mac with
# MLX. Chosen on the Artificial Analysis Speech Arena (blind pairwise listener
# votes): Elo 1219, the second open-weights model, above Gemini 3.1 Flash TTS;
# Chatterbox sits near 1005 to 1035 on the same board. One reference clip made
# by voice design keeps the speaker identical across every line, and every clip
# is transcribed with Whisper and regenerated if the words drift from the cue.
# Weights are under the BreezeBlue research and non-commercial licence.
BACKEND = os.environ.get("TURNO_TTS_BACKEND", "breeze")  # breeze | gemini
MODEL = os.environ.get("TURNO_TTS_MODEL", "mlx-community/Breeze-TTS-2-mlx" if BACKEND == "breeze" else "gemini-2.5-flash-preview-tts")
VOICE = os.environ.get("TURNO_TTS_VOICE", "breeze-ref" if BACKEND == "breeze" else "Charon")
BREEZE_REF = HERE / "breeze-ref.wav"
BREEZE_REF_TEXT = ("Every summer, Italian regions ban outdoor work from half past twelve to four, on days the heat is "
                   "rated high. A site supervisor still has to decide the rest of the day.")
BREEZE_INSTRUCT = ("A calm man in his thirties talking a colleague through a screen. Natural pace, small pauses, "
                   "relaxed, unhurried.")
BREEZE_CFG, BREEZE_TRIES, MAX_WER = 4.0, 4, 0.12
TEMPO = float(os.environ.get("TURNO_TTS_TEMPO", "1.0"))  # the directed read already sits near documentary pace
STYLE = ("Read this as a site engineer calmly walking a colleague through a screen they are both looking at. "
         "Natural, unhurried, conversational. Breathe between sentences. Where a line has a pause marked with "
         "three dots, pause briefly as if thinking. State facts plainly; never sell.")

VOICE_LUFS, MUSIC_LUFS = -16.0, -34.0
BREATH = 0.45
PAUSE_KEEP = 0.9
# A gap up to 4.5 s is allowed between beats: those seconds are the scene scrolling
# and clicking into the next view, which the viewer needs to follow. The limit
# still fails a stretch of dead picture (the 35 s wait seen in take two).
MAX_SILENCE, MIN_COVERAGE = 4.5, 0.72
MUSIC = Path("/Users/aashanjaved/Desktop/Drive -D - Aashan/Research Assistant/Hackathons/Music for Reels/ES_Towntones - Dusty Decks.mp3")

# The script. Every number spoken is on screen in that beat. Three dots mark a
# thinking pause for the voice. One idea per line.
CUES = [
    ("title", "This is Turno. Heat-safe shift planning for outdoor crews."),

    ("open", "Every summer, Italian regions ban outdoor work from half past twelve to four... on days the heat is rated high."),
    ("open", "A site supervisor still has to decide the rest of the day, hour by hour, and prove the ban was kept."),

    ("verdict", "Milan, the thirty-first of July. Heavy work, a crew new to the heat."),
    ("verdict", "Turno planned this day the day before... one hour of safe work in a thirteen-hour day."),
    ("verdict", "And then it checked itself against what actually happened. It allowed too much work in one hour. It says so."),

    ("strip", "The strip is the whole day. Each column is an hour."),
    ("strip", "Height is the minutes of work allowed. Colour is the heat. Above it, the forecast spread, and the black line is what really happened."),

    ("toohigh", "Nine o'clock... hmm. The forecast ran a little cool, so the plan allowed fifteen minutes, and reality allowed none."),
    ("toohigh", "Turno marks it as too high rather than hiding it. A plan you can audit is worth more than one that looks perfect."),

    ("alto", "Now the supervisor confirms the official rating for the day. High."),
    ("alto", "The law takes over the afternoon. Those hatched blocks are the ban, and no forecast can change them."),

    ("banned", "Two o'clock is banned by the regional ordinance, quoted from its own text."),

    ("decide", "Before the rating is confirmed, those same hours belong to the supervisor."),
    ("decide", "Turno never guesses the official rating. It assumes the ban, and hands the hour to a person... with the reason."),

    ("explain", "A model running on AMD explains the hour, in Italian and in English."),
    ("explain", "Every number it writes is checked against the plan before it is shown. If one is not in the plan, the text is dropped."),

    ("briefing", "Gemma four writes the crew briefing from the plan."),
    ("briefing", "Same rule. The labels for each hour are fixed by the rules, and every time and number is checked."),

    ("law", "Regions rewrite these ordinances every summer. This is where AMD does its heaviest work."),
    ("law", "MinerU reads the region's signed PDF. DeepSeek proposes every field with a quote copied from the text."),

    ("reread", "This re-read ran on AMD just now, while you watched."),
    ("reread", "Code accepts a field only if its quote is really in the document and contains the value. The rest goes to a person."),

    ("live", "Tomorrow's plan comes from the latest ECMWF ensemble run... the same forecast, the same rules."),

    ("evidence", "The dates and the predictions were written down before the test days were scored."),
    ("evidence", "On ten summer days the ensemble and the rules missed one percent of heat-restricted hours, against six point six for a single forecast."),

    ("close", "The models read and explain. The rules decide. The supervisor has the last word."),
    ("close", "The code, the sources and every number are open."),
]


def api_key() -> str:
    k = os.environ.get("GEMENI_KEY") or os.environ.get("GEMINI_API_KEY")
    if not k and ENV:
        for line in ENV.read_text().splitlines():
            n, _, v = line.partition("=")
            if n.strip() in ("GEMENI_KEY", "GEMINI_API_KEY") and v:
                k = v.strip().strip('"').strip("'")
    if not k:
        raise SystemExit("no Gemini key for TTS")
    return k


def ff(args):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{r.stderr.strip()}")


def duration(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], capture_output=True, text=True, check=True).stdout.strip())


def loudness(path: Path, seconds: float | None = None) -> float:
    args = ["ffmpeg", "-hide_banner", "-nostats"] + (["-t", f"{seconds}"] if seconds else []) + \
           ["-i", str(path), "-af", "ebur128=framelog=quiet", "-f", "null", "-"]
    r = subprocess.run(args, capture_output=True, text=True)
    m = re.search(r"I:\s*(-?\d+\.\d+) LUFS", r.stderr)
    if not m:
        raise SystemExit(f"could not measure {path.name}")
    return float(m.group(1))


def clip_path(text: str) -> Path:
    ref = hashlib.sha256(BREEZE_REF.read_bytes()).hexdigest()[:8] if BACKEND == "breeze" else ""
    key = hashlib.sha256(f"{BACKEND}|{MODEL}|{VOICE}|{ref}|{TEMPO}|{PAUSE_KEEP}|{STYLE}|{text}".encode()).hexdigest()[:16]
    return CLIPS / f"{key}.wav"


def normalise(src: Path, dest: Path, tempo: float = 1.0) -> None:
    stretch = "" if abs(tempo - 1.0) < 0.005 else f"atempo={tempo:.4f},"
    ff(["-i", str(src), "-af",
        # Leading silence goes; internal pauses are kept up to PAUSE_KEEP seconds.
        # At 0.3 s the written pauses ("...", "hm") were cut and lines read at
        # 150 to 220 words a minute; the breaths are the point of the direction.
        "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08"
        f":stop_periods=-1:stop_threshold=-50dB:stop_silence={PAUSE_KEEP}," + stretch +
        f"loudnorm=I={VOICE_LUFS}:TP=-1.5:LRA=7", "-ar", "24000", "-ac", "1", str(dest)])


_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "x x twenty thirty forty fifty sixty seventy eighty ninety".split()
_ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}


def _num_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    return str(n)


def _ordinal(n: int) -> str:
    w = _num_words(n).split()
    last = w[-1]
    w[-1] = _ORD.get(last, last[:-1] + "ieth" if last.endswith("ty") else last + "th")
    return " ".join(w)


def words_of(text: str) -> list[str]:
    """Spoken-word tokens: digits as words, so "15" and "fifteen" compare equal."""
    t = text.lower().replace("%", " percent ").replace("-", " ")
    t = re.sub(r"(\d+)(st|nd|rd|th)\b", lambda m: _ordinal(int(m.group(1))), t)
    t = re.sub(r"(\d+)\.(\d+)", lambda m: f"{_num_words(int(m.group(1)))} point {' '.join(_ONES[int(c)] for c in m.group(2))}", t)
    t = re.sub(r"\d+", lambda m: _num_words(int(m.group(0))), t)
    return re.findall(r"[a-z']+", t)


def wer(said: str, wanted: str) -> float:
    import difflib
    a, b = words_of(wanted), words_of(said)
    matched = sum(bl.size for bl in difflib.SequenceMatcher(None, a, b).get_matching_blocks())
    return (len(a) + len(b) - 2 * matched) / max(1, len(a))


_breeze = None


def synth_breeze(text: str, dest: Path) -> None:
    global _breeze
    import numpy as np
    import mlx_whisper
    if _breeze is None:
        from mlx_audio.tts import load
        _breeze = load(MODEL)
    raw = dest.with_suffix(".raw.wav")
    best = (9.9, None)
    for seed in range(BREEZE_TRIES):
        chunks = list(_breeze.generate(text=text, instruct=BREEZE_INSTRUCT, ref_audio=str(BREEZE_REF), ref_text=BREEZE_REF_TEXT,
                                       cfg_scale=BREEZE_CFG, voice="S0", seed=seed))
        audio = np.concatenate([np.array(c.audio, dtype=np.float32).reshape(-1) for c in chunks])
        rate = chunks[0].sample_rate
        cand = dest.with_name(f"{dest.stem}.try{seed}.wav")
        with wave.open(str(cand), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        heard = mlx_whisper.transcribe(str(cand), path_or_hf_repo="mlx-community/whisper-large-v3-turbo")["text"].strip()
        e = wer(heard, text)
        print(f"      try {seed}: {len(audio) / rate:.1f}s, word error {e:.2f}" + ("" if e <= MAX_WER else f"  heard: {heard}"), flush=True)
        if e < best[0]:
            if best[1] is not None:
                best[1].unlink()
            best = (e, cand)
        else:
            cand.unlink()
        if e <= MAX_WER:
            break
    if best[0] > MAX_WER:
        raise SystemExit(f"the voice would not read this line faithfully after {BREEZE_TRIES} tries: {text}")
    best[1].rename(raw)
    normalise(raw, dest, TEMPO)
    raw.unlink()


def synth(text: str, dest: Path) -> None:
    if BACKEND == "breeze":
        return synth_breeze(text, dest)
    import httpx
    # The direction goes in the system instruction. Given inline with the line,
    # the model read the direction aloud: a nineteen word line came back as
    # twenty five seconds of audio.
    # Google's convention for these models: the direction in the text, framed as
    # "Direction: line"; the voice speaks only what follows the colon.
    body = {"contents": [{"parts": [{"text": f"{STYLE} Now read only this line: {text}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
    for attempt in range(8):
        r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                       headers={"x-goog-api-key": api_key(), "Content-Type": "application/json"}, json=body, timeout=120)
        if r.status_code == 429:
            m = re.search(r'retryDelay"?:\s*"?(\d+)', r.text)
            wait = int(m.group(1)) + 3 if m else 30
            print(f"      quota, waiting {wait}s", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        import base64
        pcm = base64.b64decode(part["data"])
        rate = int(re.search(r"rate=(\d+)", part.get("mimeType", "")).group(1)) if "rate=" in part.get("mimeType", "") else 24000
        raw = dest.with_suffix(".raw.wav")
        with wave.open(str(raw), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
        normalise(raw, dest, TEMPO)
        raw.unlink()
        return
    raise SystemExit("TTS quota did not clear")


def stamp(t: float) -> str:
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    # Always start from the raw take, so a rerun trims the original, not a trim.
    raw = HERE / "turno-demo-raw.mp4"
    if raw.exists():
        import shutil
        shutil.copyfile(raw, VIDEO)
    data = json.loads(MARKS.read_text())
    beats, lead_in, scene = data["beats"], data["lead_in"], data["elapsed"]
    at_of = {b["id"]: b["at"] for b in beats}
    order = [b["id"] for b in beats]
    video_len = duration(VIDEO)
    CLIPS.mkdir(exist_ok=True)
    print(f"voice {VOICE} on {MODEL} ({BACKEND}), tempo {TEMPO}")
    fresh = 0
    for _, text in CUES:
        if not clip_path(text).exists():
            print(f"   synth: {text[:60]}", flush=True)
            synth(text, clip_path(text)); fresh += 1

    placed, running, needed = [], {}, {}
    for beat, text in CUES:
        if beat not in at_of:
            raise SystemExit(f"unknown beat {beat}")
        offset = running.get(beat, 0.0) + BREATH
        secs = duration(clip_path(text))
        placed.append({"beat": beat, "start": lead_in + at_of[beat] + offset, "secs": secs, "end": lead_in + at_of[beat] + offset + secs,
                       "path": clip_path(text), "text": text.replace("...", ","), "words": len(text.split())})
        running[beat] = offset + secs; needed[beat] = running[beat] + BREATH
    placed.sort(key=lambda c: c["start"])

    room = {b: (at_of[order[i + 1]] if i + 1 < len(order) else scene) - at_of[b] for i, b in enumerate(order)}

    # Dead picture is cut, not talked over. Where a beat held longer than its
    # lines need (the page waiting for a model answer), the excess is removed
    # from the take and every later beat moves up by the same amount.
    cuts = []
    for i, b in enumerate(order[:-1]):
        spare = room[b] - needed[b] - 1.0
        if spare > 2.5:
            a = lead_in + at_of[b] + needed[b] + 0.6
            cuts.append((a, a + spare))
    if cuts:
        expr = "+".join(f"between(t,{a:.3f},{z:.3f})" for a, z in cuts)
        trimmed = HERE / "turno-demo-trimmed.mp4"
        ff(["-i", str(VIDEO), "-vf", f"select='not({expr})',setpts=N/FRAME_RATE/TB", "-r", "30",
            "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-movflags", "+faststart", str(trimmed)])
        removed_before = lambda t: sum(min(z, t) - a for a, z in cuts if a < t)  # noqa: E731
        for b in order:
            at_of[b] -= removed_before(lead_in + at_of[b])
        scene -= sum(z - a for a, z in cuts)
        # The raw take is kept; the trimmed one is what the voice goes onto.
        raw = HERE / "turno-demo-raw.mp4"
        if not raw.exists():
            VIDEO.rename(raw)
        else:
            VIDEO.unlink()
        trimmed.rename(VIDEO)
        video_len = duration(VIDEO)
        print(f"  cut {sum(z - a for a, z in cuts):.1f}s of waiting from {len(cuts)} beats; take is now {video_len:.1f}s")
        placed, running, needed = [], {}, {}
        for beat, text in CUES:
            offset = running.get(beat, 0.0) + BREATH
            secs = duration(clip_path(text))
            placed.append({"beat": beat, "start": lead_in + at_of[beat] + offset, "secs": secs,
                           "end": lead_in + at_of[beat] + offset + secs, "path": clip_path(text),
                           "text": text.replace("...", ","), "words": len(text.split())})
            running[beat] = offset + secs; needed[beat] = running[beat] + BREATH
        placed.sort(key=lambda c: c["start"])
        room = {b: (at_of[order[i + 1]] if i + 1 < len(order) else scene) - at_of[b] for i, b in enumerate(order)}
    faults, prev = [], None
    for c in placed:
        c["gap"] = c["start"] - (prev["end"] if prev else 0.0)
        if prev and c["start"] < prev["end"] - 0.05:
            faults.append(f"{prev['beat']} runs {prev['end'] - c['start']:.1f}s into {c['beat']}")
        if c["gap"] > MAX_SILENCE:
            faults.append(f"{c['gap']:.1f}s of silence before {c['beat']} at {c['start']:.1f}s")
        nxt = [at_of[i] for i in order if at_of[i] > at_of[c["beat"]] + 0.001]
        if nxt and c["end"] > lead_in + min(nxt) + 0.6:
            faults.append(f"{c['beat']} is still speaking {c['end'] - (lead_in + min(nxt)):.1f}s after the picture changed")
        prev = c
    for b, want in needed.items():
        if room[b] < want - 0.05:
            faults.append(f"beat {b} holds {room[b]:.1f}s but its lines need {want:.1f}s: raise its hold in demo.js by {want - room[b]:.1f}s")
    spoken = sum(c["secs"] for c in placed); coverage = spoken / video_len
    tail = (lead_in + scene) - placed[-1]["end"]
    if tail > MAX_SILENCE:
        faults.append(f"{tail:.1f}s of silence at the end")
    if coverage < MIN_COVERAGE:
        faults.append(f"speech covers {coverage:.0%} of the running time, under {MIN_COVERAGE:.0%}")
    print(f"  {'beat':9s} {'in':>6s} {'out':>6s} {'gap':>5s} {'secs':>5s}")
    for c in placed:
        print(f"  {c['beat']:9s} {c['start']:6.1f} {c['end']:6.1f} {c['gap']:5.1f} {c['secs']:5.1f}")
    print(f"  speech {spoken:.1f}s of {video_len:.1f}s ({coverage:.0%}), tail {tail:.1f}s")
    if faults:
        raise SystemExit("the narration does not fit the picture:\n  " + "\n  ".join(faults))

    SRT.write_text("\n".join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n"
                             for i, c in enumerate(placed, start=1)), encoding="utf-8")

    inputs = ["-f", "lavfi", "-t", f"{video_len:.3f}", "-i", "anullsrc=r=24000:cl=mono"]
    filters, mixes = [], ["[0:a]"]
    for i, c in enumerate(placed, start=1):
        inputs += ["-i", str(c["path"])]; ms = int(c["start"] * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]"); mixes.append(f"[d{i}]")
    filters.append("".join(mixes) + f"amix=inputs={len(placed) + 1}:duration=first:normalize=0[vo]")
    if MUSIC.exists():
        gain = MUSIC_LUFS - loudness(MUSIC, seconds=video_len)
        inputs += ["-i", str(MUSIC)]
        # The track is shorter than the film, so it loops before the trim; the
        # mixer otherwise ends the whole mix at the bed's length (136 s).
        filters.append(f"[{len(placed) + 1}:a]aformat=sample_rates=24000:channel_layouts=mono,aloop=loop=-1:size=8000000,"
                       f"atrim=0:{video_len:.3f},asetpts=N/SR/TB,"
                       f"volume={gain:.2f}dB,afade=t=in:st=0:d=2.0,afade=t=out:st={max(0.0, video_len - 2.8):.2f}:d=2.8[bed]")
        filters.append("[bed][vo]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[out]")
    else:
        filters.append("[vo]alimiter=limit=0.95[out]")
        print("music: none found, voice only")
    ff([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-t", f"{video_len:.3f}", "-c:a", "aac", "-b:a", "192k", str(OUT)])
    # AAC adds encoder priming and padding at the end of the container (about a
    # tenth of a second at 24 kHz); the mux below uses -shortest and the muxed
    # streams are checked to 0.3 s, so this guard only catches a gross mismatch.
    if abs(duration(OUT) - video_len) > 1.0:
        raise SystemExit(f"audio {duration(OUT):.2f}s and video {video_len:.2f}s do not end together")

    final = HERE / "turno-demo-voiced.mp4"
    ff(["-i", str(VIDEO), "-i", str(OUT), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(final)])
    VIDEO.unlink(); final.rename(VIDEO)
    v = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", str(VIDEO)], capture_output=True, text=True).stdout.strip())
    a = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", str(VIDEO)], capture_output=True, text=True).stdout.strip())
    if abs(v - a) > 0.3:
        raise SystemExit(f"muxed streams do not end together: video {v:.2f}s, audio {a:.2f}s")
    print(f"  muxed: video {v:.2f}s, audio {a:.2f}s")
    # Captions ship as the SRT sidecar (YouTube takes it under Subtitles). A
    # burned-in copy is made only when this ffmpeg has the subtitles filter;
    # the Mac build does not, and the main file is final either way.
    filters_out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    if any(line.split()[1:2] == ["subtitles"] for line in filters_out.splitlines() if line.strip()):
        import shutil
        tmp_srt = Path("/tmp/claude_turno_captions.srt")  # the filter parser chokes on spaces in the repo path
        shutil.copyfile(SRT, tmp_srt)
        style = "FontSize=20,PrimaryColour=&HFFFFFF&,OutlineColour=&H80000000&,Outline=1,Shadow=0,MarginV=36".replace(",", "\\,")
        ff(["-i", str(VIDEO), "-vf", f"subtitles={tmp_srt}:force_style={style}",
            "-c:a", "copy", "-crf", "19", "-preset", "slow", "-movflags", "+faststart", str(HERE / "turno-demo-captioned.mp4")])
    else:
        print("captions: no subtitles filter in this ffmpeg; the SRT sidecar is the deliverable")
    print(f"\n{VIDEO.name} {duration(VIDEO):.1f}s, {fresh} lines synthesised, {len(placed) - fresh} cached; captions in {SRT.name}")


if __name__ == "__main__":
    main()
