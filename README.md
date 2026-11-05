# Valorant Agent Bot

Discord-Bot, der zufällig einen Valorant-Agenten auswählt – optional nach Rolle gefiltert, mit Reroll-Button.

## Befehl

| Befehl | Parameter | Beschreibung |
| :--- | :--- | :--- |
| `/agent` | `role` (optional) | Zufälliger Agent. Filter: Duelist, Initiator, Controller, Sentinel. |

Der Reroll-Button ist 180 Sekunden aktiv, nur für den Aufrufer nutzbar und wiederholt nie direkt denselben Agenten. Die Agentendaten kommen von [valorant-api.com](https://valorant-api.com) und werden alle 24 Stunden aktualisiert.

## Setup

Voraussetzung: Python 3.10+

```bash
git clone git@github.com:Failexius/discord-bot-valorant.git
cd discord-bot-valorant
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DISCORD_TOKEN eintragen
python bot.py
```

`.env`:

| Variable | Pflicht | Beschreibung |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | ja | Bot-Token aus dem Discord Developer Portal |
| `GUILD_ID` | nein | Server-ID für sofortiges Command-Sync beim Testen (sonst global, bis zu 1 h Verzögerung) |

## Bot einladen

Developer Portal → OAuth2 → URL Generator:

- Scopes: `bot`, `applications.commands`
- Permissions: `Send Messages`, `Embed Links`
