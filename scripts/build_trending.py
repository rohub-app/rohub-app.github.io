#!/usr/bin/env python3
"""Builds RoHub's trending data from Roblox's public charts.

Runs in GitHub Actions every 30 minutes (see .github/workflows/sync.yml):

  python3 scripts/build_trending.py site/data/trending.json

The notes on why each game is trending, and what a developer could borrow
from it, are written from the data itself, so no AI key is needed. Set
SITE_URL to the published site so the previous file can be read for
"since yesterday" player changes.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

UA = 'Mozilla/5.0 (compatible; RoHubSync/2.0)'
TOP_N = 10
EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF←-⇿⌀-⏿■-◿☀-➿⬀-⯿️‍⃣]')
UPDATE_PARENS_RE = re.compile(r'\((?=[^)]*\b(?:UPDATE|UPD|NEW|FIX|EVENT|BETA|ALPHA|TEST|TESTING|RELEASE|OUT NOW)\b)[^)]*\)', re.I)
PLAIN_TAGS = {'UPD', 'UPDATE', 'NEW', 'BETA', 'ALPHA', 'SANDBOX', 'EARLY ACCESS', 'TESTING', 'TEST', 'RELEASE', 'FREE', 'OPEN'}
SEASONS = [
    (re.compile(r'🎃|👻|halloween|spooky', re.I), '🎃 Its Halloween update is live.'),
    (re.compile(r'🎄|🎅|christmas|xmas|winter', re.I), '🎄 Its winter holiday update is live.'),
    (re.compile(r'🏖|summer', re.I), '☀️ Its summer update is live.'),
]
# (pattern over name, description and genre) -> tip a small developer could borrow
TIPS = [
    (r'\bsteal|\brob\b|raid', 'Let players steal from each other\'s bases: the risk and the revenge keep sessions going.'),
    (r'\begg|hatch|\bpets?\b|mutation', 'Add a collect-and-hatch loop with rare variants so every hatch could be a jackpot.'),
    (r'\brng\b|\broll|\bluck|aura', 'Use rarity rolls with tiny odds for the best items; big pulls get shared with friends.'),
    (r'rebirth|prestige', 'Add rebirths so players restart stronger and keep coming back.'),
    (r'tycoon|money|cash|\bearn', 'Give players a steady upgrade path: earn, upgrade, earn faster.'),
    (r'\bobby|parkour|platformer|runner|\bjump', 'Keep levels short with instant retries, and add a timer so friends can race.'),
    (r'horror|scary|killer|monster|anomal|nightmare|jumpscare|creepy|eerie', 'Build tension with a threat players hear before they see it.'),
    (r'survive|survival|escape', 'Make each death teach the player something, so failing feels fair.'),
    (r'1v1|duel|pvp|fight|battle|combat|shooter|\bfps\b|weapon', 'Keep matches short so players always go for one more round.'),
    (r'contract|challenge|quest|daily', 'Add daily challenges that unlock exclusive cosmetics.'),
    (r'roleplay|\brp\b|town|city|house|home', 'Let players own and decorate a space they can show their friends.'),
    (r'co-?op|friends|together|\bteam|\bcamp', 'Make the main goal a team effort so friends invite friends.'),
    (r'trade|trading|collect', 'Add collectible items that players can trade with each other.'),
    (r'vehicle|\bcars?\b|bike|drive|racing|\brace\b|moped|plane|flight', 'Reward style, not just speed: pay players for tricks and near misses.'),
    (r'event|limited', 'Run limited-time events with items that won\'t come back.'),
    (r'update|out now|release|\bv2\b', 'Ship small updates often and put "UPDATE" in your game\'s title when you do.'),
]
FALLBACK_TIPS = ['Look at its first minute: notice how fast it gets you to the fun part.',
                 'Copy its update rhythm: check how often it changes its title, icon and events.']


def fetch(url, body=None, tries=4):
    data = json.dumps(body).encode() if body is not None else None
    headers = {'User-Agent': UA, 'Accept': 'application/json'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:  # network hiccup: retry
            last = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError('%s failed: %s' % (url.split('?')[0], last))


def fetch_json(url, body=None):
    return json.loads(fetch(url, body))


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def clean_name(raw):
    """Drop tag text like [HIRED KILLER] and update notes, but keep every emoji."""
    s = re.sub(r'\[([^\]]*)\]', lambda m: ' ' + ''.join(EMOJI_RE.findall(m.group(1))) + ' ', raw or '')
    s = UPDATE_PARENS_RE.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -|:•')
    return s or (raw or '').strip()


def excerpt(text, n):
    s = re.sub(r'\n{3,}', '\n\n', (text or '').replace('\r', '')).strip()
    return s if len(s) <= n else s[:n].rstrip() + '…'


def parse_iso(iso):
    try:
        return datetime.strptime((iso or '')[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
    except Exception:
        return None


def hours_since(iso, now_ms):
    t = parse_iso(iso)
    return (now_ms - t.timestamp() * 1000) / 3.6e6 if t else None


def day_label(iso):
    t = parse_iso(iso)
    return t.strftime('%b %d, %Y').replace(' 0', ' ') if t else ''


def short(n):
    n = n or 0
    for div, unit in ((1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if n >= div:
            return ('%.1f' % (n / div)).rstrip('0').rstrip('.') + unit
    return str(n)


def ago_text(hours):
    if hours < 1:
        return 'less than an hour ago'
    if hours < 24:
        return '%d hour%s ago' % (round(hours), '' if round(hours) == 1 else 's')
    return '%d day%s ago' % (round(hours / 24), '' if round(hours / 24) == 1 else 's')


# ---------- Roblox ----------

def game_details(ids):
    out = {}
    for part in chunks(ids, 50):
        for g in fetch_json('https://games.roblox.com/v1/games?universeIds=' + ','.join(map(str, part))).get('data', []):
            out[g['id']] = g
    return out


def game_votes(ids):
    out = {}
    for part in chunks(ids, 50):
        for v in fetch_json('https://games.roblox.com/v1/games/votes?universeIds=' + ','.join(map(str, part))).get('data', []):
            out[v['id']] = (v.get('upVotes') or 0, v.get('downVotes') or 0)
    return out


def game_icons(ids):
    out = {}
    for part in chunks(ids, 50):
        url = ('https://thumbnails.roblox.com/v1/games/icons?returnPolicy=PlaceHolder&size=256x256&format=Webp&isCircular=false&universeIds='
               + ','.join(map(str, part)))
        for t in fetch_json(url).get('data', []):
            if t.get('state') == 'Completed' and t.get('imageUrl'):
                out[t['targetId']] = t['imageUrl']
    return out


# ---------- notes ----------

def why_notes(e, top_two, now):
    out = []
    text = e['rawName'] + '\n' + e['about']
    for rx, msg in SEASONS:
        if rx.search(text):
            out.append(msg)
            break
    tags = [EMOJI_RE.sub('', t).strip(' xX&-|') for t in re.findall(r'\[([^\]]*)\]', e['rawName'])]
    tags = [t for t in tags if t and t.upper() not in PLAIN_TAGS]
    if tags:
        out.append('Running its new "%s" update, from the tag in its title.' % tags[0].title())
    upd = hours_since(e['updated'], now)
    if upd is not None and upd < 48:
        out.append('Updated %s.' % ago_text(upd))
    age = hours_since(e['created'], now)
    if age is not None and age / 24 <= 45:
        out.append('Brand new: released %s, only %d days ago.' % (day_label(e['created']), max(1, round(age / 24))))
    if e['change'] is not None:
        pct = round(e['change'] * 100)
        if pct >= 10:
            out.append('Up %d%% in players since yesterday.' % pct)
        elif pct <= -10:
            out.append('Down %d%% since yesterday, so it may be cooling off.' % -pct)
    for x in e['alsoOn']:
        rank, chart = x.split(' ', 1)
        out.append({'Most played': 'Also %s most played on Roblox.' % rank,
                    'Rising fast': 'Also %s on Roblox\'s Top Trending chart.' % rank,
                    'Up-and-Coming': 'Also %s on Roblox\'s Up-and-Coming chart.' % rank}[chart])
    if e['list'] == 'Most played' and e['rank'] == 1 and top_two and top_two[1]:
        ratio = e['ccu'] / top_two[1]
        if ratio >= 2:
            out.append('About %dx the players of the #2 game.' % ratio)
    if e['likeRatio'] and e['likeRatio'] >= 90:
        out.append('Players love it: %d%% likes.' % e['likeRatio'])
    if (e['visits'] or 0) >= 1e9:
        out.append('Huge: %s visits so far.' % short(e['visits']))
    seen, notes = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            notes.append(n)
    return notes[:3] or ['%s players are in it right now.' % short(e['ccu'])]


def tip_notes(e):
    text = ' '.join((e['rawName'], e['about'], e['genre'], e['genre2'])).lower()
    tips = [tip for pattern, tip in TIPS if re.search(pattern, text)]
    return (tips + [t for t in FALLBACK_TIPS if t not in tips])[:3]


# ---------- build ----------

def previous(site_url):
    if not site_url:
        return None
    try:
        return json.loads(fetch(site_url.rstrip('/') + '/data/trending.json?ts=%d' % time.time(), tries=2))
    except Exception as e:
        print('No previous trending file (%s); changes since yesterday start next run.' % e)
        return None


def baseline(prev, now):
    """Player counts from about a day ago, to compute 'since yesterday' changes."""
    if not prev:
        return {}
    if (now - (prev.get('updatedAt') or 0)) / 3.6e6 >= 12:
        return {g['key']: {'at': prev['updatedAt'], 'ccu': g.get('ccu')} for g in prev.get('games', []) if g.get('key')}
    return prev.get('ref') or {}


def build():
    now = int(time.time() * 1000)
    explore = fetch_json('https://apis.roblox.com/explore-api/v1/get-sorts?sessionId=' + str(uuid.uuid4()))
    sorts = {s.get('sortId'): (s.get('games') or []) for s in explore.get('sorts', [])}
    top, rising, upcoming = sorts.get('top-playing-now', []), sorts.get('top-trending', []), sorts.get('up-and-coming', [])
    if len(top) < TOP_N or len(rising) < TOP_N:
        raise SystemExit('Roblox charts came back incomplete (%d most played, %d trending); keeping the old file.' % (len(top), len(rising)))
    positions = {}
    for label, games in (('Most played', top), ('Rising fast', rising), ('Up-and-Coming', upcoming)):
        for i, g in enumerate(games[:25]):
            positions.setdefault(g['universeId'], {})[label] = i + 1
    picks = [('Most played', 'mp', top[:TOP_N]), ('Rising fast', 'rf', rising[:TOP_N])]
    ids = []
    for _, _, games in picks:
        ids += [g['universeId'] for g in games if g['universeId'] not in ids]
    details, votes, icons = game_details(ids), game_votes(ids), game_icons(ids)
    ref = baseline(previous(os.environ.get('SITE_URL')), now)

    entries = []
    for label, prefix, games in picks:
        for i, g in enumerate(games):
            uid = g['universeId']
            d = details.get(uid, {})
            up, down = votes.get(uid) or (g.get('totalUpVotes') or 0, g.get('totalDownVotes') or 0)
            raw = g.get('name') or d.get('name') or ''
            place = d.get('rootPlaceId')
            e = {
                'id': '%s-%02d' % (prefix, i + 1), 'list': label, 'rank': i + 1,
                'key': str(uid), 'universeId': uid, 'placeId': place,
                'name': clean_name(raw), 'rawName': raw,
                'ccu': g.get('playerCount') or d.get('playing') or 0,
                'visits': d.get('visits'), 'favorites': d.get('favoritedCount'),
                'likeRatio': round(100 * up / (up + down)) if up + down else None,
                'genre': d.get('genre_l1') or g.get('genreL1') or '', 'genre2': d.get('genre_l2') or '',
                'creator': (d.get('creator') or {}).get('name') or '', 'maxPlayers': d.get('maxPlayers'),
                'created': d.get('created'), 'updated': d.get('updated'),
                'about': excerpt(d.get('description'), 420),
                'url': 'https://www.roblox.com/games/%s' % place if place else '',
                'icon': icons.get(uid, ''),
                'alsoOn': ['#%d %s' % (rk, lb) for lb, rk in positions.get(uid, {}).items() if lb != label],
                'change': None, 'changeHours': None,
            }
            base = ref.get(str(uid))
            if base and base.get('ccu'):
                hrs = (now - base['at']) / 3.6e6
                if 12 <= hrs <= 36:
                    e['change'] = round((e['ccu'] - base['ccu']) / base['ccu'], 4)
                    e['changeHours'] = round(hrs)
            entries.append(e)
    top_two = [g.get('playerCount') or 0 for g in top[:2]]
    for e in entries:
        e['why'] = why_notes(e, top_two, now)
        e['tips'] = tip_notes(e)
    return {'version': 1, 'updatedAt': now, 'source': 'Roblox charts', 'games': entries, 'ref': ref}


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'site/data/trending.json'
    data = build()
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    for label in ('Most played', 'Rising fast'):
        top3 = [g for g in data['games'] if g['list'] == label][:3]
        print('%s: %s' % (label, ', '.join('%s (%s)' % (g['name'], short(g['ccu'])) for g in top3)))
