# RoHub

Your Roblox ideas, tasks, games and what's trending, all in one place. Works on any phone or computer, with no account needed.

## What's in here

| Path | What it does |
|---|---|
| `site/` | The app: one page that works offline and installs to your home screen |
| `scripts/build_trending.py` | Builds the Trending tab from Roblox's charts |
| `.github/workflows/sync.yml` | Runs that every 30 minutes on GitHub and publishes the site |
| `scripts/make_icons.py` | Draws the app icons |

## Put it online (free, about 5 minutes)

1. **Get a GitHub account.** Sign up for free at [github.com](https://github.com) if you don't have one.
2. **Create a repository named `rohub`.** Click **+** → **New repository**, type `rohub`, choose **Public**, then **Create repository**.
3. **Upload these files.** On the new repository's page, click **uploading an existing file** and drag in everything inside this folder, including the hidden `.github` folder (in Finder, press **Cmd + Shift + .** to show it). Then click **Commit changes**.
4. **Turn on the website.** Go to **Settings → Pages**. Under **Build and deployment**, set **Source** to **GitHub Actions**.
5. **Run the first sync.** Go to **Actions → RoHub sync → Run workflow**. After about a minute, RoHub is live at `https://YOUR-USERNAME.github.io/rohub/`.

From then on, GitHub refreshes the Trending tab every 30 minutes by itself. Your computer can be off.

## Use it on your iPhone

Open the link in Safari, tap **Share**, then **Add to Home Screen**. RoHub opens full screen like an app.

## Good to know

- **Your data stays on your device.** Ideas, tasks and your numbers are saved only in the browser you use. To move them, use **Settings → Download backup**, then **Restore backup** on the other device.
- **Your games load live from Roblox** through [RoProxy](https://roproxy.com), a public proxy that lets websites read Roblox's public data. If RoProxy is down, RoHub shows your last saved numbers. Like ratios aren't available this way, so they only show on the Trending tab.
- **Trending notes are written from Roblox's data**, such as recent updates, seasonal events, player changes and chart positions. No AI key is needed.
- **Robux earned and ad spend aren't public on Roblox**, so you add those yourself per game.
- **The welcome screen asks where people heard about RoHub.** Each answer adds one to an anonymous tally kept by [Abacus](https://abacus.jasoncameron.dev), a free counting service; no username or other personal data is sent. See the totals in **Settings → Where people found RoHub**, or open the site with `#stats` at the end of the link.
- RoHub isn't made by or affiliated with Roblox.
