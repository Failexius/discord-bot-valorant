import asyncio
import os
from dotenv import load_dotenv
import discord
from discord import app_commands
import random
import aiohttp
from typing import Optional

load_dotenv()

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
        await get_agents()
        if not VALORANT_AGENTS:
            print("WARNING: Could not load Valorant agents from the API.")
        else:
            print(f"{len(VALORANT_AGENTS)} Valorant agents loaded from the API.")

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


async def load_valorant_agents(retries: int = 3) -> list[dict]:
    url = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
    timeout = aiohttp.ClientTimeout(total=10)

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(
                            f"Valorant API returned status {response.status} "
                            f"(attempt {attempt}/{retries})"
                        )
                    else:
                        data = await response.json()
                        agents = []
                        for item in data.get("data", []):
                            try:
                                agents.append(
                                    {
                                        "name": item["displayName"],
                                        "icon": item.get("displayIcon"),
                                        "role": (
                                            item["role"]["displayName"]
                                            if item.get("role")
                                            else "Unknown"
                                        ),
                                        "description": item.get(
                                            "description", "No description available."
                                        ),
                                    }
                                )
                            except (KeyError, TypeError):
                                continue  # skip malformed entry
                        if agents:
                            return agents
                        print(f"Valorant API returned no agents (attempt {attempt}/{retries})")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            print(f"Error loading Valorant agents (attempt {attempt}/{retries}): {e}")

        if attempt < retries:
            await asyncio.sleep(2 * attempt)

    return []


async def get_agents() -> list[dict]:
    """Liefert die Agentenliste und lädt sie bei Bedarf (ein Reload gleichzeitig)."""
    global VALORANT_AGENTS
    if not VALORANT_AGENTS:
        async with _load_lock:
            if not VALORANT_AGENTS:
                VALORANT_AGENTS = await load_valorant_agents()
    return VALORANT_AGENTS


def pick_agent(role_name: Optional[str]) -> Optional[dict]:
    """Zufälliger Agent, optional gefiltert nach Rolle. None, wenn der Pool leer ist."""
    pool = [a for a in VALORANT_AGENTS if not role_name or a.get("role") == role_name]
    return random.choice(pool) if pool else None


@client.event
async def on_ready():
    print(f"Logged in as {client.user} – Commands synchronized!")


class RerollView(discord.ui.View):
    def __init__(self, author_id: int, selected_role: Optional[str] = None):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.selected_role = selected_role
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
        selected_agent = pick_agent(self.selected_role)
        if not selected_agent:
            await interaction.response.send_message(
                "Keine passenden Agenten gefunden.", ephemeral=True
            )
            return

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
    view = RerollView(author_id=interaction.user.id, selected_role=role_name)
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
