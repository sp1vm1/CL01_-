"""Shared timing for the KICPA Assistant promo (audio + video stay in lockstep)."""

BPM = 128
BEAT = 60.0 / BPM          # 0.46875 s
HOOK = 1.6                 # cold-open hook before the music starts (seconds)
TOTAL_BEATS = 72
DURATION = HOOK + TOTAL_BEATS * BEAT + 0.4
FPS = 30
W, H = 1920, 1080
SR = 48000

# Section boundaries, in beats from music start
A_OPEN = 0      # black screen, big type, a boom per phrase
B_BUILD = 12    # document windows pile up, riser
STOP = 27       # one beat of silence
C_DROP = 28     # one word per beat, matched to real app category cards
D_APP = 44      # real app screens
E_PIVOT = 56    # filtered, emotional
F_END = 64      # brand line + logo


def t_of(beat):
    """Beat index -> absolute time in seconds."""
    return HOOK + beat * BEAT


def beat_of(t):
    """Absolute time -> fractional beat (negative during the hook)."""
    return (t - HOOK) / BEAT
