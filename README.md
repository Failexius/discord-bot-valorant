# Valorant Discord Agent Selector Bot

Discord-Bot zur zufälligen Auswahl von Valorant-Agenten mit optionaler Rollenfilterung und interaktiver Reroll-Funktion.

---

## Funktionsumfang

- **Rollenbasierte Auswahl:** Filterung nach den offiziellen Valorant-Rollen (*Duelist*, *Initiator*, *Controller*, *Sentinel*).
- **Interaktiver Reroll-Button:** Erlaubt dem aufrufenden Nutzer, direkt in Discord ohne erneute Befehlseingabe einen neuen Agenten aus dem gewählten Pool zu ziehen (Timeout: 180 Sekunden).
- **Dynamischer Datenabruf:** Automatische Synchronisation der spielbaren Agenten, Icons und Rollenbeschreibungen über die offizielle `valorant-api.com` beim Bot-Start.
- **Slash Commands (`app_commands`):** Moderne Discord-Befehlsintegration mit automatischer Parameter-Vervollständigung.

---

## Befehle

| Befehl | Parameter | Beschreibung |
| :--- | :--- | :--- |
| `/agent` | `role` (Optional) | Wählt einen zufälligen Agenten. Filterbar nach Duelist, Initiator, Controller oder Sentinel. |

---

## Technologie-Stack

- **Python 3.10+**
- **`discord.py` (v2.x):** Asynchroner Discord API Client mit UI-Views und Slash-Commands.
- **`aiohttp`:** Asynchrone HTTP-Requests zum Abruf der Agenten-Daten.
- **`python-dotenv`:** Sichere Verwaltung von Umgebungsvariablen.

---

## Installation & Lokaler Start

### 1. Repository klonen & Abhängigkeiten installieren

```bash
git clone git@github.com:Failexius/discord-bot-valorant.git
cd discord-bot-valorant

# Virtuelle Umgebung erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### 2. Konfiguration (`.env`)

Erstelle eine `.env`-Datei auf Basis der Beispieldatei:

```bash
cp .env.example .env
```

Füge dein Discord-Bot-Token ein:

```env
DISCORD_TOKEN=dein_bot_token_hier

# Optional: Server-ID für sofortige lokale Befehlssynchronisation zu Testzwecken
# GUILD_ID=123456789012345678
```

### 3. Erforderliche Bot-Berechtigungen (Discord Developer Portal)

Im Discord Developer Portal unter OAuth2 -> URL Generator folgende Scopes und Berechtigungen vergeben:
- Scopes: bot, applications.commands
- Bot Permissions: Send Messages, Embed Links, Use Slash Commands

### 4. Bot starten

```bash
python bot.py
```

---

## Projektstruktur

```text
discord-bot-valorant/
├── bot.py                # Bot-Client, API-Loader, Reroll-View & Slash-Commands
├── requirements.txt      # Python-Abhängigkeiten
├── .env.example          # Vorlage für Umgebungsvariablen
├── .gitignore            # Git-Ausschlussregeln
└── README.md             # Technische Dokumentation
```
