"""Generate an original, quiet looping purr locally; no API or audio downloads."""

from array import array
import math
from pathlib import Path
import sys
import wave


def create(target):
    rate, seconds = 22050, 2
    samples = array('h')
    for index in range(rate * seconds):
        t = index / rate
        # Integer frequencies make the two-second loop phase-continuous.
        breath = .65 + .35 * math.cos(math.tau * .5 * t)
        pulse = (.5 + .5 * math.cos(math.tau * 25 * t)) ** 2
        rumble = sum(weight * math.sin(math.tau * frequency * t)
                     for frequency, weight in ((75, .5), (150, .24), (225, .12),
                                               (325, .07), (475, .04)))
        samples.append(round(15000 * breath * (.2 + .8 * pulse) * rumble))
    if sys.byteorder != 'little':
        samples.byteswap()
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), 'wb') as output:
        output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        output.writeframes(samples.tobytes())


if __name__ == '__main__':
    create(Path(__file__).resolve().parent.parent / 'assets/audio/purr.wav')
