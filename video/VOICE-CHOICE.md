# Why the narrator is Breeze TTS 2

Aashan's note on take five (16 Oct 2026): the voice must sound human, and the choice must rest on research,
with no reliance on Gemini alone. This is the evidence and the decision.

## The evidence

The only large blind listening test of current voices is the Artificial Analysis Speech Arena: listeners hear
two clips of the same text without knowing the models and pick the better one; models are ranked by Elo.
Read on 16 Oct 2026 at https://artificialanalysis.ai/text-to-speech/leaderboard (the page carries no
"last updated" date; its newest entries are dated October 2026).

| Model | Weights | Elo | Fits this Mac (M5 Pro, 25.7 GB)? | Licence |
|---|---|---|---|---|
| Eleven v4 Turbo | closed | 1327 | no (API) | commercial |
| Gemini 3.8 Flash TTS | closed | 1272 | no (API) | commercial |
| Fish Audio Drama 3 Preview | open | 1242 | no: 35B MoE, 19.75 GB at 3-bit, 23.78 GB at 4-bit | weights under the Fish Audio Research License |
| Breeze TTS 2 | open | 1219 | yes: 7.63 GB bf16 on MLX | BreezeBlue research and non-commercial |
| Gemini 3.1 Flash TTS | closed | 1213 | no (API) | commercial |
| Voxtral TTS (Mistral) | open | about 1067 | yes | CC BY-NC |
| Kokoro 82M | open | about 1063 | yes | Apache 2.0 |
| Chatterbox HD / Chatterbox | open | 1035 / 1006 | yes | MIT |

The Gemini 2.5 Flash preview voice used on takes one to five is not in the top 25.

Chatterbox Turbo's "beats ElevenLabs" figures come from a vendor-commissioned Podonos study, not from the
arena, so they are not comparable with the table.

## The decision

Breeze TTS 2: the highest-ranked open-weights voice that runs on this machine. It takes a text description of
the speaker (voice design), a reference clip plus transcript (cloning), and spoken events in parentheses.

How it is used in `narrate.py`:
- one reference clip, `breeze-ref.wav`, made once by voice design from the instruction "A calm man in his
  thirties talking a colleague through a screen. Natural pace, small pauses, relaxed, unhurried.";
- every line is cloned from that clip with the same instruction, so the speaker is identical across the film;
- every clip is read back with Whisper (large-v3-turbo on MLX) and compared with the cue, digits spelled out;
  a word error above 0.12 regenerates the line with a new seed, up to four times, and the narrator stops if
  none passes. The trial showed why: a cloned line once dropped "The" and the reference once added "the".

Measured on the trial lines (video/voice-trial/): Breeze 112 to 169 words a minute with 0.3 to 1.4 s pauses
where the script marks them, the "hmm" audible; Chatterbox Turbo 147 to 171 words a minute with fewer pauses.

Licence: the Breeze weights and their outputs are for research and non-commercial use. A hackathon demo
narration is that use; the video description says which model spoke. If the narration is ever needed for
commercial material, re-voice with Chatterbox Turbo (MIT): `TURNO_TTS_BACKEND=gemini` still works too.

## What was tried and rejected

- Fish Audio Drama 3: top open voice, but even the 3-bit MLX build needs 19.75 GB of the Mac's 25.7 GB with
  Chromium also running, and 3-bit is not the model the listeners rated.
- Chatterbox Turbo (MIT): installed and compared on the same three lines; kept as the fallback. The A/B file
  `voice-trial/A-B Breeze-then-Chatterbox.m4a` plays Breeze's three lines, then Chatterbox's.
- Gemini 2.5 Flash preview TTS: the earlier choice; keeps working as a backend, but it is below every open
  model above on the arena.

Sources: Artificial Analysis leaderboard (above); https://github.com/Blaizzy/mlx-audio (model support,
Breeze usage); https://github.com/resemble-ai/chatterbox (versions, MIT, Podonos evaluation);
https://huggingface.co/fishaudio/drama-3 (35B-A3B, research licence); https://huggingface.co/mlx-community
(file sizes read from the model API on 16 Oct 2026).
