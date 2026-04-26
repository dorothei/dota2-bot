from typing import Any, Final
import html

from aiogram.utils.formatting import Bold, Code, Text
from app.services.opendota import opendota_client
from config.logger import logger

HERO_NAMES: Final[dict[int, str]] = {
    1: "Anti-Mage 🔮",
    2: "Axe 🪓",
    3: "Bane 😈",
    4: "Bloodseeker 🩸",
    5: "Crystal Maiden 🧊",
    6: "Drow Ranger 🏹",
    7: "Earthshaker 🌍",
    8: "Juggernaut 🎭",
    9: "Mirana 🌠",
    10: "Morphling 🌊",
    11: "Shadow Fiend 🔥",
    12: "Phantom Lancer 🪞",
    13: "Puck 🧚",
    14: "Pudge 🪝",
    15: "Razor ⚡",
    16: "Sand King 🦂",
    17: "Storm Spirit 🌩️",
    18: "Sven ⚔️",
    19: "Tiny 🪨",
    20: "Vengeful Spirit 👻",
    21: "Windranger 🍃",
    22: "Zeus ⚡",
    23: "Kunkka 🚢",
    25: "Lina 🔥",
    26: "Lion 🦁",
    27: "Shadow Shaman 🐍",
    28: "Slardar 🐟",
    29: "Tidehunter 🌊",
    30: "Witch Doctor 🪘",
    31: "Lich ☠️",
    32: "Riki 🥷",
    33: "Enigma 🕳️",
    34: "Tinker 🔧",
    35: "Sniper 🎯",
    36: "Necrophos ☣️",
    37: "Warlock 📖",
    38: "Beastmaster 🐗",
    39: "Queen of Pain 👑",
    40: "Venomancer ☠️",
    41: "Faceless Void 🌀",
    42: "Wraith King 👑",
    43: "Death Prophet 👻",
    44: "Phantom Assassin 🗡️",
    45: "Pugna 💚",
    46: "Templar Assassin 🔷",
    47: "Viper 🐍",
    48: "Luna 🌙",
    49: "Dragon Knight 🐉",
    50: "Dazzle ✨",
    51: "Clockwerk ⚙️",
    52: "Leshrac 🦄",
    53: "Nature's Prophet 🌳",
    54: "Lifestealer 🧟",
    55: "Dark Seer 🌑",
    56: "Clinkz 🔥",
    57: "Omniknight ✝️",
    58: "Enchantress 🦌",
    59: "Huskar 🩹",
    60: "Night Stalker 🌙",
    61: "Broodmother 🕷️",
    62: "Bounty Hunter 💰",
    63: "Weaver 🕸️",
    64: "Jakiro 🐲",
    65: "Batrider 🦇",
    66: "Chen ⛪",
    67: "Spectre 👻",
    68: "Ancient Apparition ❄️",
    69: "Doom 🔥",
    70: "Ursa 🐻",
    71: "Spirit Breaker 🐂",
    72: "Gyrocopter 🚁",
    73: "Alchemist ⚗️",
    74: "Invoker 📚",
    75: "Silencer 🤫",
    76: "Outworld Destroyer 🌌",
    77: "Lycan 🐺",
    78: "Brewmaster 🍺",
    79: "Shadow Demon 👤",
    80: "Lone Druid 🐻",
    81: "Chaos Knight 🌌",
    82: "Meepo ⛏️",
    83: "Treant Protector 🌲",
    84: "Ogre Magi 👹",
    85: "Undying 🧟",
    86: "Rubick 🪄",
    87: "Disruptor ⚡",
    88: "Nyx Assassin 🦂",
    89: "Naga Siren 🧜",
    90: "Keeper of the Light 🕯️",
    91: "Io 💡",
    92: "Visage 🪶",
    93: "Slark 🦈",
    94: "Medusa 🐍",
    95: "Troll Warlord 🪓",
    96: "Centaur Warrunner 🐎",
    97: "Magnus 🦣",
    98: "Timbersaw 🪚",
    99: "Bristleback 🦔",
    100: "Tusk 🦭",
    101: "Skywrath Mage 🕊️",
    102: "Abaddon 💀",
    103: "Elder Titan 🗿",
    104: "Legion Commander 🛡️",
    105: "Techies 💣",
    106: "Ember Spirit 🔥",
    107: "Earth Spirit 🪨",
    108: "Underlord 🔥",
    109: "Terrorblade 😈",
    110: "Phoenix 🔥",
    111: "Oracle 🔮",
    112: "Winter Wyvern 🐉",
    113: "Arc Warden ⚡",
    114: "Monkey King 🐒",
    119: "Dark Willow 🌿",
    120: "Pangolier 🦔",
    121: "Grimstroke 🖌️",
    123: "Hoodwink 🐿️",
    126: "Void Spirit 🟣",
    128: "Snapfire 🦎",
    129: "Mars 🔱",
    135: "Dawnbreaker ☀️",
    136: "Marci 👊",
    137: "Primal Beast 🦖",
    138: "Muerta 🌹",
    145: "Kez 🗡️",
    155: "Largo 🐸",
}

RANK_TIER_NAMES: Final[dict[int, str]] = {
    1: "Рекрут",
    2: "Страж",
    3: "Рыцарь",
    4: "Герой",
    5: "Легенда",
    6: "Властелин",
    7: "Божество",
    8: "Титан",
}

STAR_NAMES: Final[dict[int, str]] = {
    1: "★☆☆☆☆",
    2: "★★☆☆☆",
    3: "★★★☆☆",
    4: "★★★★☆",
    5: "★★★★★",
}

GAME_MODES: Final[dict[int, str]] = {
    0: "Unknown ❓",
    1: "All Pick 🎯",
    2: "Captains Mode 👑",
    3: "Random Draft 🎲",
    4: "Single Draft 1️⃣",
    5: "All Random 🔀",
    6: "Intro 🤖",
    7: "Diretide 🎃",
    8: "Reverse Captains Mode 🔄",
    9: "Greeviling 👹",
    10: "Tutorial 📚",
    11: "Mid Only ⚔️",
    12: "Least Played 📉",
    13: "Limited Heroes 🔒",
    14: "Compendium Match 📘",
    15: "Custom Mode 🛠️",
    16: "Captains Draft 🧠",
    17: "Balanced Draft ⚖️",
    18: "Ability Draft ✨",
    19: "Event 🎉",
    20: "All Random Deathmatch ☠️",
    21: "1v1 Solo Mid 🥊",
    22: "All Draft 📝",
    23: "Turbo ⚡",
    24: "Mutation 🧬",
}

LOBBY_TYPES: Final[dict[int, str]] = {
    0: "Public Matchmaking",
    1: "Practice",
    2: "Tournament",
    7: "Ranked Matchmaking",
    14: "Ranked All Pick",
}


def get_hero_name(hero_id: int) -> str:
    return HERO_NAMES.get(hero_id, f"Hero {hero_id}")


def get_game_mode_name(mode_id: int) -> str:
    return GAME_MODES.get(mode_id, f"Mode {mode_id}")


def get_lobby_type_name(lobby_id: int) -> str:
    return LOBBY_TYPES.get(lobby_id, f"Lobby {lobby_id}")


def get_rank_name(rank_tier: int) -> str:
    if not rank_tier or rank_tier == 0:
        return "Нет ранга"
    rank_num = rank_tier // 10
    star_num = rank_tier % 10
    rank_name = RANK_TIER_NAMES.get(rank_num, "Неизвестный ранг")
    if rank_num == 8:
        return rank_name
    return f"{rank_name} {STAR_NAMES.get(star_num, '')}".strip()


def format_winrate(wins: int, losses: int) -> str:
    total = wins + losses
    if total == 0:
        return "0%"
    return f"{(wins / total) * 100:.1f}%"


def format_kda(kills: int, deaths: int, assists: int) -> str:
    kda_value = (kills + assists) / max(1, deaths)
    return f"{kills}/{deaths}/{assists} ({kda_value:.2f})"


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}с"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}м {remaining_seconds}с"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}ч {remaining_minutes}м"


def format_match_details(match_data: dict[str, Any]) -> Text:
    try:
        match_id = match_data.get("match_id", "Unknown")
        duration = match_data.get("duration", 0)
        game_mode = match_data.get("game_mode", 0)
        lobby_type = match_data.get("lobby_type", 0)
        radiant_win = match_data.get("radiant_win", False)

        players = match_data.get("players", [])
        if not players:
            return Text("❌ Нет данных об игроках в матче.")

        result_emoji = "✅" if radiant_win else "❌"
        result_text = "Radiant Victory" if radiant_win else "Dire Victory"

        duration_text = format_duration(duration)
        game_mode_name = get_game_mode_name(game_mode)
        lobby_name = get_lobby_type_name(lobby_type)

        radiant_players = []
        dire_players = []

        for player in players:
            player_slot = player.get("player_slot", 0)
            is_radiant = player_slot < 128

            hero_id = player.get("hero_id", 0)
            hero_name = get_hero_name(hero_id)

            kills = player.get("kills", 0)
            deaths = player.get("deaths", 0)
            assists = player.get("assists", 0)
            kda_text = format_kda(kills, deaths, assists)

            level = player.get("level", 0)
            net_worth = player.get("net_worth", 0)
            gpm = player.get("gold_per_min", 0)
            xpm = player.get("xp_per_min", 0)

            account_id = player.get("account_id")
            player_info = Text(
                f"🦸 {hero_name} ",
                Bold("ID:"),
                " ",
                Code(str(account_id) if account_id else "unknown"),
                "\n",
                f"📊 KDA: {kda_text} | 🎯 Lvl: {level}\n",
                f"💰 Net Worth: {net_worth:,} 💵\n",
                f"⚡ GPM: {gpm} | 📈 XPM: {xpm}",
            )

            if is_radiant:
                radiant_players.append(player_info)
            else:
                dire_players.append(player_info)

        match_text = Text(
            Bold(f"🆔 Матч #{match_id}"),
            "\n\n",
            f"{result_emoji} ",
            Bold(result_text),
            "\n\n",
            Bold("⏱️ Длительность:"),
            f" {duration_text}\n",
            Bold("🎮 Режим:"),
            f" {game_mode_name}\n",
            Bold("🏆 Тип лобби:"),
            f" {lobby_name}\n\n",
            Bold("🔥 Radiant Team:"),
            "\n",
        )

        for i, player in enumerate(radiant_players, 1):
            match_text += Text(f"\n{i}. ", player)

        match_text += Text("\n\n", Bold("💀 Dire Team:"), "\n")

        for i, player in enumerate(dire_players, 1):
            match_text += Text(f"\n{i}. ", player)

        return match_text

    except Exception as e:
        logger.error(f"Ошибка форматирования матча: {e}")
        return Text("❌ Ошибка форматирования данных матча")


def get_item_name(item_id: int) -> str:
    if item_id == 0:
        return "Empty Slot"
    return f"Unknown Item {item_id}"


async def get_item_name_async(item_id: int) -> str:
    if item_id == 0:
        return "Empty Slot"

    if not opendota_client.items_dict:
        opendota_client.items_dict = await opendota_client.get_items_dict()

    name = opendota_client.items_dict.get(item_id)
    if name:
        return name

    # Если предмета нет в текущем кеше, попробуем обновить словарь
    refreshed = await opendota_client.get_items_dict()
    if refreshed:
        opendota_client.items_dict = refreshed
        name = refreshed.get(item_id)
        if name:
            return name

    return f"Unknown Item {item_id}"


async def format_player_items(player: dict) -> str:
    # Инвентарь
    inventory_items = []
    for i in range(6):
        item_id = player.get(f"item_{i}", 0)
        item_name = await get_item_name_async(item_id)
        inventory_items.append(item_name)

    # Рюкзак
    backpack_items = []
    for i in range(3):
        item_id = player.get(f"backpack_{i}", 0)
        item_name = await get_item_name_async(item_id)
        backpack_items.append(item_name)

    # Нейтральный предмет
    neutral_item_id = player.get("item_neutral", 0)
    neutral_item_name = await get_item_name_async(neutral_item_id)

    return (
        f"🪄 Инвентарь: {', '.join(inventory_items)}\n"
        f"🎒 Рюкзак: {', '.join(backpack_items)}\n"
        f"🧿 Нейтральный предмет: {neutral_item_name}"
    )


def format_match_result(match: dict) -> str:
    try:
        match_id = match.get("match_id", 0)
        hero_id = match.get("hero_id", 0)
        kills = match.get("kills", 0)
        deaths = match.get("deaths", 0)
        assists = match.get("assists", 0)
        duration = match.get("duration", 0)

        player_slot = match.get("player_slot", 0)
        radiant_win = match.get("radiant_win", False)

        is_radiant = player_slot < 128
        win = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)

        result_emoji = "✅" if win else "❌"
        result_text = "Победа" if win else "Поражение"

        kda_text = format_kda(kills, deaths, assists)
        duration_text = format_duration(duration)

        hero_name = get_hero_name(hero_id)

        match_text = Text(
            f"{result_emoji} {result_text}\n",
            "ID: ", Code(str(match_id)), "\n",
            f"Герой: {hero_name}\n",
            f"KDA: {kda_text}\n",
            f"Длительность: {duration_text}",
        )

        return match_text.as_html()
    except Exception as e:
        logger.error(f"Ошибка форматирования матча: {e}")
        return "❌ Ошибка форматирования данных матча"
