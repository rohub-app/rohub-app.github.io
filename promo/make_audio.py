#!/usr/bin/env python3
"""Builds the soundtrack and timeline for RoHub's TikTok videos.

For each video it records the voiceover with macOS `say`, synthesizes original
background music and sound effects (so there is nothing to license), mixes them
into build/<name>.wav, and writes build/<name>.json for render.swift to draw.

  python3 make_audio.py
"""
import array
import json
import math
import os
import random
import subprocess
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
SHOTS = os.path.join(HERE, 'shots')
SR = 44100
VOICE, RATE = 'Samantha', '192'
LINK = 'rohub-app.github.io'
TAU = 2 * math.pi
random.seed(7)

# Each segment is one voice line. hook = big centered lines; head = headline above the phone;
# phone screens: (shot, segment index, start fraction, zoom from, zoom to, focus from (x, y), focus to (x, y)).
VIDEOS = [
    {'name': 'rohub-tiktok-1-intro',
     'segments': [
         {'say': 'Roblox devs, stop losing your game ideas.',
          'hook': [('ROBLOX DEVS 👀', None, 132), ('stop losing your\ngame ideas', 'game ideas', 96)], 'sfx': [(0.0, 'whoosh'), (0.75, 'pop')]},
         {'say': 'This is RoHub.', 'logo': True, 'sfx': [(-0.45, 'riser'), (0.0, 'ding')]},
         {'say': 'Save every idea and task in one place.', 'head': ('Ideas + tasks\nin one place', 'one place'), 'sfx': [(0.0, 'whoosh'), (0.55, 'swipe')]},
         {'say': 'Type your Roblox username, no password, and see all your games and stats.',
          'head': ('All your games\n+ stats 📊', 'games'), 'sfx': [(0.0, 'pop'), (0.42, 'swipe')]},
         {'say': "Plus what's trending on Roblox right now, and why.", 'head': ("What's trending\n+ WHY 🔥", 'WHY'), 'sfx': [(0.0, 'pop'), (0.5, 'swipe')]},
         {'say': "It's free. Link in bio.", 'endcard': True, 'sfx': [(0.0, 'ding'), (0.0, 'whoosh')], 'tail': 1.8},
     ],
     'phone': {'segments': (2, 4), 'screens': [
         ('ideas', 2, 0.0, 1.0, 1.05, (.5, .3), (.5, .3)), ('tasks', 2, 0.55, 1.0, 1.05, (.5, .3), (.5, .3)),
         ('welcome-typed', 3, 0.0, 1.0, 1.09, (.5, .8), (.5, .85)), ('games-hero', 3, 0.42, 1.02, 1.15, (.22, .25), (.22, .3)),
         ('trending', 4, 0.0, 1.0, 1.06, (.5, .3), (.5, .33)), ('trend-detail', 4, 0.5, 1.04, 1.09, (.42, .4), (.42, .6))]}},
    {'name': 'rohub-tiktok-2-trending',
     'segments': [
         {'say': 'Ever wonder why a Roblox game suddenly blows up?',
          'hook': [('Why is THIS game', 'THIS', 104), ('blowing up? 🤯', None, 124)], 'hook_y': [0.40, 0.50], 'sfx': [(0.0, 'whoosh'), (0.8, 'pop')]},
         {'say': 'RoHub checks the top Roblox charts every thirty minutes.', 'head': ('Top Roblox games\nevery 30 min ⏱️', 'every 30 min'), 'sfx': [(0.0, 'whoosh')]},
         {'say': "Tap any game to see exactly why it's trending,", 'head': ("See WHY it's\ntrending 🔥", 'WHY'), 'sfx': [(0.0, 'swipe'), (0.55, 'pop')]},
         {'say': 'and get ideas you can use in your own game.', 'head': ('Ideas for\nYOUR game 💡', 'YOUR game'), 'sfx': [(0.0, 'pop'), (0.6, 'click')]},
         {'say': "RoHub is free. Link in bio.", 'endcard': True, 'sfx': [(0.0, 'ding'), (0.0, 'whoosh')], 'tail': 1.8},
     ],
     'phone': {'segments': (1, 3), 'screens': [
         ('trending', 1, 0.0, 1.0, 1.1, (.5, .3), (.5, .4)), ('trend-detail', 2, 0.0, 1.03, 1.09, (.42, .15), (.42, .9))]}},
    {'name': 'rohub-tiktok-3-stats',
     'segments': [
         {'say': 'P.O.V. You finally see all your Roblox stats in one place.',
          'hook': [('POV:', None, 150), ('all your Roblox stats\nin ONE place', 'ONE place', 92)], 'sfx': [(0.0, 'whoosh'), (0.7, 'pop')]},
         {'say': 'Just type your username. No password.', 'head': ('Just your username\nno password 🔒', 'no password'), 'sfx': [(0.0, 'whoosh'), (0.7, 'click')]},
         {'say': 'RoHub finds all your games, even the ones in your groups.', 'head': ('Even your\ngroup games 👥', 'group games'), 'sfx': [(0.0, 'swipe'), (0.6, 'pop')]},
         {'say': 'Visits, favorites, players online, all in one place.', 'head': ('Visits · Favorites\n· Players 📈', 'Visits'),
          'sfx': [(0.0, 'swipe'), (0.35, 'pop'), (0.95, 'pop'), (1.6, 'pop')]},
         {'say': "It's free. Link in bio.", 'endcard': True, 'sfx': [(0.0, 'ding'), (0.0, 'whoosh')], 'tail': 1.8},
     ],
     'phone': {'segments': (1, 3), 'screens': [
         ('welcome-typed', 1, 0.0, 1.0, 1.09, (.5, .75), (.5, .85)), ('games-communities', 2, 0.0, 1.0, 1.08, (.45, .5), (.45, .7)),
         ('games-hero', 3, 0.0, 1.04, 1.15, (.22, .2), (.22, .35))]}},
]


# ---------- audio helpers ----------

def zeros(n):
    return array.array('f', bytes(4 * n))


def mix_into(dst, src, at, gain=1.0):
    start = int(at * SR)
    for i in range(max(0, -start), min(len(src), len(dst) - start)):
        dst[start + i] += src[i] * gain


def read_wav(path):
    with wave.open(path) as w:
        raw = w.readframes(w.getnframes())
        ch = w.getnchannels()
    pcm = array.array('h', raw)
    return array.array('f', (pcm[i] / 32768.0 for i in range(0, len(pcm), ch)))


def write_wav(path, mono):
    peak = max(1e-9, max(abs(x) for x in mono))
    scale = min(1.0, 0.95 / peak)
    out = array.array('h', bytes(4 * len(mono)))
    for i, x in enumerate(mono):
        v = int(max(-1.0, min(1.0, x * scale)) * 32767)
        out[2 * i] = v
        out[2 * i + 1] = v
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())


def voice_line(text, path):
    aiff = path.replace('.wav', '.aiff')
    subprocess.run(['say', '-v', VOICE, '-r', RATE, '-o', aiff, text], check=True)
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@%d' % SR, '-c', '1', aiff, path], check=True)
    s = read_wav(path)
    loud = [i for i in range(len(s)) if abs(s[i]) > 0.02]
    s = s[max(0, loud[0] - 200):loud[-1] + 2000] if loud else s
    peak = max(abs(x) for x in s) or 1
    return array.array('f', (x * 0.85 / peak for x in s))


# ---------- original music: soft lo-fi loop at 96 BPM ----------

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def make_music_loop():
    beat = 60 / 96
    bar = beat * 4
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 60, 64], [55, 59, 62, 64]]  # Am7, Fmaj7, Cmaj7, G6
    roots = [45, 41, 48, 43]
    n = int(SR * bar * 4)
    buf = zeros(n)
    for b, chord in enumerate(chords):
        b0 = b * bar
        for note in chord:  # warm pad: two slightly detuned sines per note
            f = mtof(note)
            s0, s1 = int(b0 * SR), min(n, int((b0 + bar + 0.35) * SR))
            for i in range(s0, s1):
                t = i / SR - b0
                env = min(1.0, t / 0.35) * (1.0 if t < bar else max(0.0, 1 - (t - bar) / 0.35))
                tt = i / SR
                buf[i % n] += 0.028 * env * (math.sin(TAU * f * 1.0012 * tt) + math.sin(TAU * f * 0.9988 * tt))
        for k in range(4):
            bt = b0 + k * beat
            if k in (0, 2):  # kick + bass on 1 and 3
                ph = 0.0
                for i in range(int(SR * 0.35)):
                    t = i / SR
                    ph += TAU * (48 + 70 * math.exp(-t / 0.03)) / SR
                    j = (int(bt * SR) + i) % n
                    buf[j] += 0.30 * math.sin(ph) * math.exp(-t / 0.12)
                f = mtof(roots[b])
                for i in range(int(SR * 0.7)):
                    t = i / SR
                    j = (int(bt * SR) + i) % n
                    buf[j] += 0.15 * math.exp(-t / 0.28) * (math.sin(TAU * f * t) + 0.3 * math.sin(TAU * 2 * f * t))
            else:  # soft clap on 2 and 4
                lp = 0.0
                for i in range(int(SR * 0.18)):
                    t = i / SR
                    x = random.uniform(-1, 1)
                    lp += 0.25 * (x - lp)
                    buf[(int(bt * SR) + i) % n] += 0.06 * (x - lp) * math.exp(-t / 0.05)
            lp = 0.0
            for i in range(int(SR * 0.05)):  # hi-hat on the off-beat
                t = i / SR
                x = random.uniform(-1, 1)
                lp += 0.5 * (x - lp)
                buf[(int((bt + beat / 2) * SR) + i) % n] += 0.022 * (x - lp) * math.exp(-t / 0.012)
        for k, idx in enumerate([0, 2, 1, 3, 2, 1, 3, 2]):  # little pluck melody on eighth notes
            f = mtof(chord[idx] + 12)
            st = int((b0 + k * beat / 2) * SR)
            for i in range(int(SR * 0.4)):
                t = i / SR
                buf[(st + i) % n] += 0.045 * math.exp(-t / 0.16) * min(1.0, t / 0.004) * (math.sin(TAU * f * t) + 0.25 * math.sin(TAU * 2 * f * t))
    y = 0.0
    a = 1 - math.exp(-TAU * 4200 / SR)  # gentle low-pass for a warm, lo-fi sound
    for i in range(n):
        y += a * (buf[i] - y)
        buf[i] = math.tanh(y * 1.3) / 1.3
    return buf


# ---------- original sound effects ----------

def sfx_whoosh(dur=0.42, lo=500.0, hi=6500.0, gain=0.9):
    n = int(SR * dur)
    out = zeros(n)
    y = y2 = 0.0
    for i in range(n):
        p = i / n
        env = (p / 0.6 if p < 0.6 else (1 - p) / 0.4) ** 1.6
        a = 1 - math.exp(-TAU * (lo + (hi - lo) * p) / SR)
        y += a * (random.uniform(-1, 1) - y)
        y2 += 0.02 * (y - y2)
        out[i] = (y - y2) * env * gain
    return out


def sfx_pop():
    n = int(SR * 0.1)
    out, ph = zeros(n), 0.0
    for i in range(n):
        t = i / SR
        ph += TAU * (520 + 9000 * t) / SR
        out[i] = math.sin(ph) * min(1.0, t / 0.003) * math.exp(-t / 0.028) * 0.8
    return out


def sfx_ding():
    n = int(SR * 1.4)
    out = zeros(n)
    for i in range(n):
        t = i / SR
        env = math.exp(-t / 0.38) * min(1.0, t / 0.002)
        out[i] = env * 0.42 * (math.sin(TAU * 1318.5 * t) + 0.45 * math.sin(TAU * 2637 * t) * math.exp(-t / 0.2)
                               + 0.2 * math.sin(TAU * 3951 * t) * math.exp(-t / 0.1))
    return out


def sfx_riser(dur=0.5):
    n = int(SR * dur)
    out, ph, y = zeros(n), 0.0, 0.0
    for i in range(n):
        p = i / n
        ph += TAU * 220 * 2 ** (p * 2.6) / SR
        y += 0.2 * (random.uniform(-1, 1) - y)
        out[i] = (0.5 * math.sin(ph) + 0.35 * y) * p * p * 0.7
    return out


def sfx_click():
    n = int(SR * 0.04)
    out = zeros(n)
    for i in range(n):
        t = i / SR
        out[i] = random.uniform(-1, 1) * math.exp(-t / 0.004) * 0.5 + math.sin(TAU * 2400 * t) * math.exp(-t / 0.01) * 0.35
    return out


SFX = {'whoosh': (sfx_whoosh(), 0.5), 'swipe': (sfx_whoosh(0.24, 1500, 9000, 0.8), 0.45), 'pop': (sfx_pop(), 0.45),
       'ding': (sfx_ding(), 0.5), 'riser': (sfx_riser(), 0.45), 'click': (sfx_click(), 0.5)}


# ---------- build ----------

def build(video, loop):
    name = video['name']
    segs = video['segments']
    t = 0.35
    for k, seg in enumerate(segs):
        seg['voice'] = voice_line(seg['say'], os.path.join(BUILD, '%s-line%d.wav' % (name, k)))
        seg['start'] = t
        seg['voice_at'] = t + 0.12
        seg['end'] = seg['voice_at'] + len(seg['voice']) / SR + seg.get('tail', 0.28)
        t = seg['end']
    total = round(t, 3)
    n = int(SR * total)

    # Soundtrack: voice on top, music ducked under it, effects on the cuts.
    voice, fx, music = zeros(n), zeros(n), zeros(n)
    for seg in segs:
        mix_into(voice, seg['voice'], seg['voice_at'])
        for at, kind in seg.get('sfx', []):
            sound, gain = SFX[kind]
            mix_into(fx, sound, max(0.0, seg['start'] + at), gain)
    for i in range(n):
        music[i] = loop[i % len(loop)]
    follower, out = 0.0, zeros(n)
    for i in range(n):
        v = abs(voice[i])
        follower = max(v, follower * 0.9996)
        duck = 1 - 0.5 * min(1.0, follower * 3)
        fade = min(1.0, i / (SR * 0.4), (n - i) / (SR * 1.0))
        out[i] = voice[i] + music[i] * 0.55 * duck * fade + fx[i]
    wav = os.path.join(BUILD, name + '.wav')
    write_wav(wav, out)

    # Picture timeline for render.swift
    items = []
    shot = lambda s: os.path.join(SHOTS, s + ('.png' if s == 'logo' else '.jpg'))
    for seg in segs:
        s, e = seg['start'], seg['end']
        if 'hook' in seg:
            lines = seg['hook']
            ys = seg.get('hook_y') or ([0.42] if len(lines) == 1 else [0.38, 0.52])
            for j, (text, accent, size) in enumerate(lines):
                items.append({'kind': 'big', 'start': s + j * 0.75, 'end': e, 'text': text, 'accent': accent, 'size': size, 'y': ys[j]})
        if 'head' in seg:
            text, accent = seg['head']
            items.append({'kind': 'head', 'start': s, 'end': e, 'text': text, 'accent': accent, 'size': 82, 'y': 0.135})
        if seg.get('logo'):
            items += [{'kind': 'flash', 'start': s, 'end': s + 0.2},
                      {'kind': 'logo', 'start': s, 'end': e, 'image': shot('logo'), 'size': 400, 'y': 0.4},
                      {'kind': 'big', 'start': s + 0.15, 'end': e, 'text': 'RoHub', 'size': 160, 'y': 0.6}]
        if seg.get('endcard'):
            items += [{'kind': 'flash', 'start': s, 'end': s + 0.2},
                      {'kind': 'logo', 'start': s, 'end': e, 'image': shot('logo'), 'size': 300, 'y': 0.3},
                      {'kind': 'big', 'start': s + 0.1, 'end': e, 'text': 'RoHub', 'size': 140, 'y': 0.47},
                      {'kind': 'pill', 'start': s + 0.25, 'end': e, 'text': LINK, 'size': 52, 'y': 0.575},
                      {'kind': 'sub', 'start': s + 0.4, 'end': e, 'text': 'Free · no account · no password', 'size': 44, 'y': 0.655},
                      {'kind': 'sub', 'start': s + 0.6, 'end': e, 'text': '🔗 link in bio', 'size': 56, 'y': 0.74, 'accent': 'link in bio'}]
    ph = video['phone']
    a, b = ph['segments']
    screens = []
    for shot_name, k, frac, z0, z1, f0, f1 in ph['screens']:
        seg = segs[k]
        screens.append({'image': shot(shot_name), 'from': seg['start'] + frac * (seg['end'] - seg['start']),
                        'zoom': [z0, z1], 'focus': [f0[0], f0[1], f1[0], f1[1]]})
    items.append({'kind': 'phone', 'start': segs[a]['start'], 'end': segs[b]['end'], 'y': 0.6, 'height': 1214, 'screens': screens})
    spec = {'width': 1080, 'height': 1920, 'fps': 30, 'duration': total, 'items': items,
            'video': os.path.join(BUILD, name + '-silent.mp4'), 'audio': wav, 'out': os.path.join(HERE, name + '.mp4')}
    with open(os.path.join(BUILD, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print('%s: %.1fs, %d voice lines' % (name, total, len(segs)))


if __name__ == '__main__':
    os.makedirs(BUILD, exist_ok=True)
    loop = make_music_loop()
    for v in VIDEOS:
        build(v, loop)
