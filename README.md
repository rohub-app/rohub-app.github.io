# RoHub

Your Roblox ideas, tasks, games and what's trending, all in one place. Works on any phone or computer, with no account needed.

**Open it:** https://rohub-app.github.io

## What's in here

| Path | What it does |
|---|---|
| `site/` | The app: one page that works offline and installs to your home screen |
| `scripts/build_trending.py` | Builds the Trending tab from Roblox's charts |
| `.github/workflows/sync.yml` | Runs that every 30 minutes on GitHub and publishes the site |
| `scripts/make_icons.py` | Draws the app icons |
| `scripts/watch_games.py` | Sends phone alerts about your own games (see below) |
| `promo/` | Makes RoHub's TikTok videos: voiceover, original music, sound effects and app screens |

## Put it online (free, about 5 minutes)

1. **Get a GitHub account.** Sign up for free at [github.com](https://github.com) if you don't have one.
2. **Create a repository named `rohub`.** Click **+** → **New repository**, type `rohub`, choose **Public**, then **Create repository**.
3. **Upload these files.** On the new repository's page, click **uploading an existing file** and drag in everything inside this folder, including the hidden `.github` folder (in Finder, press **Cmd + Shift + .** to show it). Then click **Commit changes**.
4. **Turn on the website.** Go to **Settings → Pages**. Under **Build and deployment**, set **Source** to **GitHub Actions**.
5. **Run the first sync.** Go to **Actions → RoHub sync → Run workflow**. After about a minute, RoHub is live at `https://YOUR-USERNAME.github.io/rohub/`.

For a shorter link like `https://rohub-app.github.io`, create a free GitHub organization and name the repository `ORGANIZATION-NAME.github.io`.

From then on, GitHub refreshes the Trending tab every 30 minutes by itself. Your computer can be off.

## Use it on your iPhone

Open the link in Safari, tap **Share**, then **Add to Home Screen**. RoHub opens full screen like an app.

## Good to know

- **Your data stays on your device.** Ideas, tasks and your numbers are saved only in the browser you use. To move them, use **Settings → Download backup**, then **Restore backup** on the other device.
- **Your games load live from Roblox** through [RoProxy](https://roproxy.com), a public proxy that lets websites read Roblox's public data. If RoProxy is down, RoHub shows your last saved numbers. Like ratios aren't available this way, so they only show on the Trending tab.
- **Trending notes are written from Roblox's data**, such as recent updates, seasonal events, player changes and chart positions. No AI key is needed.
- **Search on the Trending tab covers every Roblox game.** Results come live from Roblox's own search through RoProxy. Sponsored results and 17+ games are left out.
- **The AI idea helper** (Tasks tab, the Ideas tab, and any game you search) uses [Pollinations](https://pollinations.ai), a free AI service that needs no key or account. Only the game's name, its description and what you type are sent. Answers usually take 5 to 30 seconds.
- **The idea bank on the Ideas tab** is built into the page (`IDEA_BANK` in `site/index.html`), so it works offline. Add your own ideas to that list to grow it. The idea of the day comes from the same list, and the streak counts the days in a row RoHub was opened on that device.
- **Team projects share by link.** A game's tasks travel in the part of the link after `#`, which browsers never send to a server. When a teammate opens it, RoHub adds new tasks and keeps the newest version of each one. Deleting a task only removes it on that device.
- **Game pass prices** come live from Roblox through RoProxy. The Robux calculator uses Roblox's standard DevEx rate of $0.0038 per earned Robux and the 30,000 Robux minimum (2026), and the 70% creators keep from game pass sales. If Roblox changes them, update `DEVEX_RATE` in `site/index.html`.
- **The bell shows what changed since your last visit:** visits, milestones and player records on your games, tasks due, and new games on the charts. It compares with the numbers saved on that device during the last visit.
- **Robux earned and ad spend aren't public on Roblox**, so you add those yourself per game.
- **RoHub counts visitors anonymously.** Each browser session adds one visit, and each phone or computer adds one device the first time it opens RoHub. The welcome screen also asks where people heard about RoHub. All of these are anonymous tallies kept by [Abacus](https://abacus.jasoncameron.dev), a free counting service: no username or other personal data is sent, and copies running on localhost don't count. See them in **Settings → RoHub stats**, or open the site with `#stats` at the end of the link.
- **RoHub used to live at `creatorluisrobiz-dot.github.io/rohub`.** That link still works: it forwards here and brings each device's ideas, tasks and Roblox link along. If you added the old one to your Home Screen, add the new link again.
- RoHub isn't made by or affiliated with Roblox.

## Phone alerts for your games

Every 30 minutes, GitHub checks your own games and sends a notification through [ntfy](https://ntfy.sh), a free app with no account. You get one when a game passes a visits or favorites milestone, sets a new record for players at once, shows up on Roblox's charts, or when a new game appears.

1. Install **ntfy** on your phone and subscribe to a private topic name, like `rohub-` followed by random letters.
2. In this repository, go to **Settings → Secrets and variables → Actions**. Add a secret `NTFY_TOPIC` with that topic name.
3. On the **Variables** tab, add `WATCH_USERNAME` with your Roblox username. Optionally add `WATCH_COMMUNITIES` with the IDs of communities you publish under, separated by commas.

The first run sends "RoHub alerts are on". To stop the alerts, delete the `NTFY_TOPIC` secret. Anyone who knows the topic name can read the alerts, so keep it private.

## Make the TikTok videos

On a Mac, with nothing extra to install (it uses the Mac's built-in voice):

```bash
cd promo
python3 make_audio.py                     # voiceover, music, sound effects and timeline
swiftc -O render.swift -o build/render    # first time only
./build/render build/rohub-tiktok-1-intro.json
```

The finished `.mp4` lands in `promo/`. Change what's said and shown in `VIDEOS` at the top of `make_audio.py`, and swap the app screenshots in `promo/shots/`.
