import os
from dotenv import load_dotenv
import discord
from discord import app_commands
import random
import aiohttp
from typing import Optional

load_dotenv()

VALORANT_AGENTS = []

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


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


async def load_valorant_agents():
    url = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return [
                    {
                        "name": item["displayName"],
                        "icon": item["displayIcon"],
                        "role": (
                            item["role"]["displayName"]
                            if item.get("role")
                            else "Unknown"
                        ),
                        "description": item.get(
                            "description", "No description available."
                        ),
                    }
                    for item in data["data"]
                ]
    return []


@client.event
async def on_ready():
    global VALORANT_AGENTS
    VALORANT_AGENTS = await load_valorant_agents()
    print(f"{len(VALORANT_AGENTS)} Valorant agents loaded from the API.")

    guild = discord.Object(id=784016011762466816)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)
    print(f"Logged in as {client.user} – Commands synchronized!")


class RerollView(discord.ui.View):
    def __init__(self, selected_role: Optional[str] = None):
        super().__init__(timeout=180)
        self.selected_role = selected_role
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def reroll_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Filter anwenden, falls eine Rolle aktiv ist
        pool = VALORANT_AGENTS
        if self.selected_role:
            pool = [a for a in VALORANT_AGENTS if a.get("role") == self.selected_role]

        if not pool:
            await interaction.response.send_message(
                "Keine passenden Agenten gefunden.", ephemeral=True
            )
            return

        selected_agent = random.choice(pool)
        embed = create_agent_embed(selected_agent)
        await interaction.response.edit_message(embed=embed, view=self)


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
    if not VALORANT_AGENTS:
        await interaction.response.send_message(
            "Agentenliste noch nicht geladen.", ephemeral=True
        )
        return

    # Pool nach Wahl filtern oder alle nehmen
    role_name = role.value if role else None
    pool = (
        [a for a in VALORANT_AGENTS if a.get("role") == role_name]
        if role_name
        else VALORANT_AGENTS
    )

    selected_agent = random.choice(pool)
    embed = create_agent_embed(selected_agent)

    # Rolle an die View übergeben
    await interaction.response.send_message(
        embed=embed, view=RerollView(selected_role=role_name)
    )

    view = RerollView(selected_role=role_name)
    response = await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()


client.run(os.getenv("DISCORD_TOKEN"))
