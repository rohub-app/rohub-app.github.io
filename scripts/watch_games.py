#!/usr/bin/env python3
"""Sends phone alerts about your own Roblox games through ntfy (https://ntfy.sh), a free app.

Runs in GitHub Actions after each sync (see .github/workflows/sync.yml):

  python3 scripts/watch_games.py .watch/state.json

It needs these repository settings (Settings -> Secrets and variables -> Actions) and does
nothing without them:
  NTFY_TOPIC         secret: the private topic your ntfy app subscribes to
  WATCH_USERNAME     variable: your Roblox username
  WATCH_COMMUNITIES  variable, optional: IDs of communities you publish under, comma-separated

Alerts: new visit and favorite milestones, a new record for players at once, a game showing up
on Roblox's charts, and new games. The last numbers are kept between runs in the state file.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = 'Mozilla/5.0 (compatible; RoHubAlerts/1.0)'
SITE = 'https://rohub-app.github.io/'
MILESTONES = [100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000]
FAV_MILESTONES = [10, 50, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000]
MIN_RECORD = 3      # don't celebrate player records below this many people
MAX_ALERTS = 6      # per run, so a busy day can't flood your phone


def fetch_json(url, body=None, tries=4):
    data = json.dumps(body).encode() if body is not None else None
    headers = {'User-Agent': UA, 'Accept': 'application/json'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:  # network hiccup: retry
            last = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError('%s failed: %s' % (url.split('?')[0], last))


def collect(url, limit=50):
    ids, cursor = [], ''
    for _ in range(3):
        res = fetch_json(url + ('&cursor=' + cursor if cursor else ''))
        ids += [g['id'] for g in res.get('data', []) if g.get('id') and g['id'] not in ids]
        cursor = res.get('nextPageCursor') or ''
        if not cursor or len(ids) >= limit:
            break
    return ids[:limit]


def my_games(username, communities):
    """Games on your profile, in communities you own, and in the communities you listed."""
    users = fetch_json('https://users.roblox.com/v1/usernames/users', {'usernames': [username], 'excludeBannedUsers': True}).get('data', [])
    if not users:
        raise RuntimeError('Roblox user %r not found' % username)
    uid = users[0]['id']
    ids = collect('https://games.roblox.com/v2/users/%d/games?accessFilter=2&limit=50&sortOrder=Desc' % uid)
    roles = fetch_json('https://groups.roblox.com/v1/users/%d/groups/roles' % uid).get('data', [])
    groups = {r['group']['id'] for r in roles if (r.get('role') or {}).get('rank') == 255}
    groups |= {int(c) for c in communities if c.isdigit()}
    for gid in sorted(groups):
        try:
            ids += [i for i in collect('https://games.roblox.com/v2/groups/%d/gamesV2?accessFilter=2&limit=50&sortOrder=Desc' % gid) if i not in ids]
        except RuntimeError:
            pass
    games = {}
    ids = ids[:100]
    for i in range(0, len(ids), 50):
        for g in fetch_json('https://games.roblox.com/v1/games?universeIds=' + ','.join(map(str, ids[i:i + 50]))).get('data', []):
            games[str(g['id'])] = {'name': g.get('sourceName') or g.get('name') or 'Your game', 'visits': g.get('visits') or 0,
                                   'favorites': g.get('favoritedCount') or 0, 'playing': g.get('playing') or 0}
    return games


def short(n):
    for size, unit in ((1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if n >= size:
            return ('%.1f' % (n / size)).rstrip('0').rstrip('.') + unit
    return str(int(n))


def crossed(marks, before, now):
    hit = [m for m in marks if before < m <= now]
    return hit[-1] if hit else None


def alerts_for(old, now, charts):
    """(title, message, ntfy tag) for everything worth a ping since the last run."""
    out = []
    for gid, g in now.items():
        b = old.get(gid)
        if b is None:
            out.append(('New game: %s' % g['name'], 'RoHub will send alerts for it too.', 'new'))
            continue
        v = crossed(MILESTONES, b['visits'], g['visits'])
        if v:
            out.append(('%s passed %s visits' % (g['name'], short(v)), 'A new milestone. Nice work!', 'tada'))
        f = crossed(FAV_MILESTONES, b['favorites'], g['favorites'])
        if f:
            out.append(('%s passed %s favorites' % (g['name'], short(f)), 'Players are saving your game.', 'star'))
        if g['playing'] >= MIN_RECORD and g['playing'] > b.get('best', 0):
            out.append(('New record on %s' % g['name'], '%d people are playing right now.' % g['playing'], 'fire'))
        if gid in charts and not b.get('charted'):
            out.append(('%s is on the charts!' % g['name'], "It just showed up in Roblox's top games.", 'chart_with_upwards_trend'))
    return out


def send(topic, title, message, tag):
    # JSON publishing keeps emojis and accents in titles intact.
    body = json.dumps({'topic': topic, 'title': title, 'message': message, 'tags': [tag], 'click': SITE + '#games'}).encode()
    req = urllib.request.Request('https://ntfy.sh/', data=body, headers={'Content-Type': 'application/json', 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else '.watch/state.json'
    topic = os.environ.get('NTFY_TOPIC', '').strip()
    username = os.environ.get('WATCH_USERNAME', '').strip()
    communities = [c.strip() for c in os.environ.get('WATCH_COMMUNITIES', '').split(',') if c.strip()]
    if not topic or not username:
        print('Phone alerts are off. Set NTFY_TOPIC and WATCH_USERNAME to turn them on.')
        return
    try:
        with open(path) as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = None
    now = my_games(username, communities)
    try:
        with open('site/data/trending.json') as f:
            charts = {str(g.get('universeId')) for g in json.load(f).get('games', [])}
    except (OSError, ValueError):
        charts = set()
    if old is None:
        send(topic, 'RoHub alerts are on', "You'll get a message when your %d games hit new milestones or records." % len(now), 'white_check_mark')
        sent = 1
    else:
        found = alerts_for(old.get('games', {}), now, charts)
        for title, message, tag in found[:MAX_ALERTS]:
            send(topic, title, message, tag)
        sent = min(len(found), MAX_ALERTS)
    # Remember the numbers, the best player count seen, and whether each game has been on the charts.
    prev = (old or {}).get('games', {})
    state = {gid: {'visits': g['visits'], 'favorites': g['favorites'], 'best': max(g['playing'], prev.get(gid, {}).get('best', 0)),
                   'charted': gid in charts or prev.get(gid, {}).get('charted', False)} for gid, g in now.items()}
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w') as f:
        json.dump({'at': int(time.time()), 'games': state}, f)
    print('Watched %d games and sent %d alerts.' % (len(now), sent))


if __name__ == '__main__':
    main()
