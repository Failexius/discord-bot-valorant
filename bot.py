import asyncio
import logging
import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import tasks
import random
import aiohttp
from typing import Optional

load_dotenv()

log = logging.getLogger(__name__)

VALORANT_AGENTS: list[dict] = []
_load_lock = asyncio.Lock()

# Optional: GUILD_ID beim Start validieren, damit Fehler sofort sichtbar sind.
_guild_id_raw = os.getenv("GUILD_ID")
try:
    GUILD_ID = int(_guild_id_raw) if _guild_id_raw else None
except ValueError:
    raise SystemExit(f"GUILD_ID must be a number, got: {_guild_id_raw!r}")


class ValorantBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Läuft genau einmal pro Prozessstart (im Gegensatz zu on_ready).
        # Lädt die Agenten sofort und danach alle 24 h neu.
        refresh_agents.start()

        if GUILD_ID:
            # Instant sync for a single (test) server
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            # Global sync (can take up to an hour to propagate)
            await self.tree.sync()


client = ValorantBot()
tree = client.tree


def create_agent_embed(agent_data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"Valorant Agent: {agent_data['name']}",
        description=agent_data.get("description", "Good luck on the battlefield!"),
        color=discord.Color.blue(),
    )
    if agent_data.get("icon"):
        embed.set_thumbnail(url=agent_data["icon"])

    embed.set_footer(text=f"Role: {agent_data.get('role')}")
    return embed


def _parse_agent(item: dict) -> Optional[dict]:
    """Wandelt einen API-Eintrag in unser Format um. None bei kaputten Daten."""
    try:
        return {
            "name": item["displayName"],
            "icon": item.get("displayIcon"),
            "role": item["role"]["displayName"] if item.get("role") else "Unknown",
            "description": item.get("description", "No description available."),
        }
    except (KeyError, TypeError):
        return None


async def load_valorant_agents(retries: int = 3) -> list[dict]:
    url = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(1, retries + 1):
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        log.warning(
                            "Valorant API returned status %s (attempt %d/%d)",
                            response.status, attempt, retries,
                        )
                    else:
                        data = await response.json()
                        parsed = (_parse_agent(i) for i in data.get("data", []))
                        agents = [a for a in parsed if a]
                        if agents:
                            return agents
                        log.warning(
                            "Valorant API returned no agents (attempt %d/%d)",
                            attempt, retries,
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                log.warning(
                    "Error loading Valorant agents (attempt %d/%d): %s",
                    attempt, retries, e,
                )

            if attempt < retries:
                await asyncio.sleep(2 * attempt)

    return []


@tasks.loop(hours=24)
async def refresh_agents():
    """Hält die Liste aktuell. Bei einem Fehler bleibt die alte Liste bestehen."""
    global VALORANT_AGENTS
    agents = await load_valorant_agents()
    if agents:
        VALORANT_AGENTS = agents
        log.info("%d Valorant agents loaded from the API.", len(agents))
    else:
        log.warning("Could not refresh Valorant agents; keeping %d.", len(VALORANT_AGENTS))


async def get_agents() -> list[dict]:
    """Liefert die Agentenliste und lädt sie bei Bedarf (ein Reload gleichzeitig)."""
    global VALORANT_AGENTS
    if not VALORANT_AGENTS:
        async with _load_lock:
            if not VALORANT_AGENTS:
                VALORANT_AGENTS = await load_valorant_agents()
    return VALORANT_AGENTS


def pick_agent(
    role_name: Optional[str], exclude: Optional[str] = None
) -> Optional[dict]:
    """Zufälliger Agent, optional nach Rolle gefiltert. None, wenn der Pool leer ist.

    `exclude` (Agentenname) wird übersprungen, solange noch eine Alternative existiert.
    """
    pool = [a for a in VALORANT_AGENTS if not role_name or a.get("role") == role_name]
    others = [a for a in pool if a["name"] != exclude]
    pool = others or pool
    return random.choice(pool) if pool else None


@client.event
async def on_ready():
    log.info("Logged in as %s", client.user)


class RerollView(discord.ui.View):
    def __init__(
        self, author_id: int, selected_role: Optional[str], current_agent: str
    ):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.selected_role = selected_role
        self.current_agent = current_agent
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Nur der Ausführende darf rerollen.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def reroll_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        selected_agent = pick_agent(self.selected_role, exclude=self.current_agent)
        if not selected_agent:
            await interaction.response.send_message(
                "Keine passenden Agenten gefunden.", ephemeral=True
            )
            return

        self.current_agent = selected_agent["name"]
        await interaction.response.edit_message(
            embed=create_agent_embed(selected_agent), view=self
        )


@tree.command(name="agent", description="Chooses a random Valorant agent for you.")
@app_commands.describe(role="Filter by a specific agent role")
@app_commands.choices(
    role=[
        app_commands.Choice(name="Duelist", value="Duelist"),
        app_commands.Choice(name="Initiator", value="Initiator"),
        app_commands.Choice(name="Controller", value="Controller"),
        app_commands.Choice(name="Sentinel", value="Sentinel"),
    ]
)
async def agent(
    interaction: discord.Interaction, role: Optional[app_commands.Choice[str]] = None
):
    # Ist die Liste leer, wird neu geladen. Dann vorher defern, weil der Request
    # länger als Discords 3-Sekunden-Fenster dauern kann.
    deferred = not VALORANT_AGENTS
    if deferred:
        await interaction.response.defer(thinking=True)
        await get_agents()

    role_name = role.value if role else None
    selected_agent = pick_agent(role_name)
    if not selected_agent:
        msg = "Keine passenden Agenten gefunden (Agentenliste evtl. nicht ladbar)."
        if deferred:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    embed = create_agent_embed(selected_agent)
    view = RerollView(interaction.user.id, role_name, selected_agent["name"])
    if deferred:
        view.message = await interaction.followup.send(embed=embed, view=view, wait=True)
    else:
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token."
        )
    client.run(token)
