"""Synthesise every cue line once, so the clips are cached before narrate.py runs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import narrate
for i, (beat, text) in enumerate(narrate.CUES, 1):
    d = narrate.clip_path(text)
    if not d.exists():
        narrate.synth(text, d)
    print(f"{i:2d} {beat:9s} {narrate.duration(d):5.2f}s {len(text.split())/narrate.duration(d)*60:4.0f} wpm", flush=True)
print("ALL LINES DONE")
