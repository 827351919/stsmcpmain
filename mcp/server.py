"""MCP server bridge for Slay the Spire 2.

Connects to the STS2_MCP mod's HTTP server and exposes game actions
as MCP tools for Claude Desktop / Claude Code.
"""

import argparse
import json
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from knowledge import KnowledgeBase

mcp = FastMCP("sts2")

_base_url: str = "http://localhost:15526"
_knowledge = KnowledgeBase()


def _sp_url() -> str:
    return f"{_base_url}/api/v1/singleplayer"


def _mp_url() -> str:
    return f"{_base_url}/api/v1/multiplayer"


async def _get(params: dict | None = None) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(_sp_url(), params=params)
        r.raise_for_status()
        return r.text


async def _post(body: dict) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(_sp_url(), json=body)
        r.raise_for_status()
        return r.text


async def _mp_get(params: dict | None = None) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(_mp_url(), params=params)
        r.raise_for_status()
        return r.text


async def _mp_post(body: dict) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(_mp_url(), json=body)
        r.raise_for_status()
        return r.text


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.ConnectError):
        return "Error: Cannot connect to STS2_MCP mod. Is the game running with the mod enabled?"
    if isinstance(e, httpx.HTTPStatusError):
        return f"Error: HTTP {e.response.status_code} — {e.response.text}"
    return f"Error: {e}"


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_game_state(format: str = "markdown") -> str:
    """Get the current Slay the Spire 2 game state.

    Returns the full game state including player stats, hand, enemies, potions, etc.
    The state_type field indicates the current screen (combat, map, event, shop, etc.).

    Args:
        format: "markdown" for human-readable output, "json" for structured data.
    """
    try:
        return await _get({"format": format})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_general_strategy(max_chars: int = 6000) -> str:
    """Get bundled high-level Slay the Spire 2 strategy notes.

    Use this when the agent needs broad deck-building, combat, or map guidance.

    Args:
        max_chars: Maximum number of characters to return.
    """
    return _knowledge.get_general_strategy(max_chars=max_chars)


@mcp.tool()
async def lookup_card(card_name: str) -> str:
    """Look up a card from the bundled Slay the Spire 2 knowledge set.

    Args:
        card_name: Card name, slug, or Chinese name.
    """
    return _knowledge.lookup_card(card_name)


@mcp.tool()
async def lookup_enemy(enemy_name: str) -> str:
    """Look up an enemy and list its known move names.

    Args:
        enemy_name: Enemy name, slug, or Chinese name.
    """
    return _knowledge.lookup_enemy(enemy_name)


@mcp.tool()
async def lookup_relic(relic_name: str) -> str:
    """Look up a relic from the bundled Slay the Spire 2 knowledge set.

    Args:
        relic_name: Relic name, slug, or Chinese name.
    """
    return _knowledge.lookup_relic(relic_name)


@mcp.tool()
async def lookup_builds(character_name: str, max_results: int = 5) -> str:
    """Get a few recommended builds for a character.

    Args:
        character_name: Character name in English or Chinese.
        max_results: Maximum number of builds to return.
    """
    return _knowledge.lookup_builds(character_name, max_results=max_results)


@mcp.tool()
async def lookup_character(character_name: str) -> str:
    """Look up a character profile and playstyle summary.

    Args:
        character_name: Character name in English or Chinese.
    """
    return _knowledge.lookup_character(character_name)


@mcp.tool()
async def lookup_event(event_name: str) -> str:
    """Look up an event and summarize its visible options.

    Args:
        event_name: Event name or slug.
    """
    return _knowledge.lookup_event(event_name)


@mcp.tool()
async def lookup_potion(potion_name: str) -> str:
    """Look up a potion, including usage and targeting.

    Args:
        potion_name: Potion name or slug.
    """
    return _knowledge.lookup_potion(potion_name)


@mcp.tool()
async def lookup_power(power_name: str) -> str:
    """Look up a power or status effect.

    Args:
        power_name: Power/status name or slug.
    """
    return _knowledge.lookup_power(power_name)


@mcp.tool()
async def lookup_enchantment(enchantment_name: str) -> str:
    """Look up an enchantment and summarize its gameplay effect.

    Args:
        enchantment_name: Enchantment name or slug.
    """
    return _knowledge.lookup_enchantment(enchantment_name)


@mcp.tool()
async def lookup_mechanic(query: str, max_results: int = 5) -> str:
    """Search core game mechanics notes.

    Args:
        query: Mechanic keyword such as energy, block, weak, poison, or draw.
        max_results: Maximum number of notes to return.
    """
    return _knowledge.lookup_mechanic(query, max_results=max_results)


def _safe_get(mapping: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _hp_ratio(state: dict[str, Any]) -> float | None:
    player = state.get("player") or {}
    hp = player.get("hp")
    max_hp = player.get("max_hp")
    if isinstance(hp, (int, float)) and isinstance(max_hp, (int, float)) and max_hp > 0:
        return hp / max_hp
    return None


def _recommend_map_node(next_options: list[dict[str, Any]], hp_ratio: float | None) -> str | None:
    if not next_options:
        return None

    preferred_order: list[str]
    if hp_ratio is not None and hp_ratio < 0.5:
        preferred_order = ["RestSite", "Shop", "Unknown", "Monster", "Treasure", "Elite"]
    elif hp_ratio is not None and hp_ratio > 0.7:
        preferred_order = ["Elite", "Monster", "Unknown", "Treasure", "Shop", "RestSite"]
    else:
        preferred_order = ["Monster", "Unknown", "Shop", "Treasure", "RestSite", "Elite"]

    for preferred in preferred_order:
        for option in next_options:
            if option.get("type") == preferred:
                return (
                    f"Prefer map node #{option.get('index', '?')} ({preferred})"
                    f" at ({option.get('col', '?')}, {option.get('row', '?')})."
                )
    return None


def _summarize_relic_synergy(state: dict[str, Any]) -> list[str]:
    player = state.get("player") or {}
    relics = player.get("relics") or []
    names = [str(relic.get("name", "")).lower() for relic in relics if isinstance(relic, dict)]
    notes: list[str] = []

    if any("anchor" in name for name in names):
        notes.append("You have Anchor, so turn 1 already starts with extra Block. Lean more aggressive on the opening turn.")
    if any("akabeko" in name for name in names):
        notes.append("You have Akabeko, so try to make your first attack hit hard instead of spending it on a weak poke.")
    if any("bag of marbles" in name for name in names):
        notes.append("You have Bag of Marbles, so front-load attack damage while enemies are Vulnerable.")
    return notes


def _pick_core_hand_cards(hand: list[dict[str, Any]], max_cards: int = 3) -> list[dict[str, Any]]:
    def score(card: dict[str, Any]) -> tuple[int, int, int]:
        card_type = str(card.get("type", "")).lower()
        rarity = str(card.get("rarity", "")).lower()
        playable = 1 if card.get("can_play") else 0
        power = 1 if card_type == "power" else 0
        zero_cost = 1 if card.get("cost") == 0 else 0
        rare = 1 if rarity == "rare" else 0
        return (playable, power + rare, zero_cost)

    seen: set[str] = set()
    ranked = sorted(hand, key=score, reverse=True)
    picked: list[dict[str, Any]] = []
    for card in ranked:
        name = str(card.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        picked.append(card)
        if len(picked) >= max_cards:
            break
    return picked


def _enemy_is_attacking(enemy: dict[str, Any]) -> bool:
    intents = enemy.get("intents") or []
    text = " ".join(str(intent.get("title", "")) + " " + str(intent.get("label", "")) for intent in intents)
    lowered = text.lower()
    return any(word in lowered for word in ("attack", "attacks", "damage", "hit"))


def _prioritized_enemy_targets(enemies: list[dict[str, Any]], max_enemies: int = 2) -> list[dict[str, Any]]:
    attackers = [enemy for enemy in enemies if _enemy_is_attacking(enemy)]
    if attackers:
        return attackers[:max_enemies]
    return enemies[:max_enemies]


def _combat_knowledge_notes(hand: list[dict[str, Any]], playable: list[dict[str, Any]], enemies: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []

    for enemy in _prioritized_enemy_targets(enemies, max_enemies=2):
        enemy_name = str(enemy.get("name", "")).strip()
        if not enemy_name:
            continue
        note = _knowledge.brief_enemy_note(enemy_name, max_moves=3)
        if note:
            notes.append(f"Enemy action cue: {note}")

    source_cards = playable if playable else hand
    for card in _pick_core_hand_cards(source_cards, max_cards=3):
        card_name = str(card.get("name", "")).strip()
        if not card_name:
            continue
        note = _knowledge.brief_card_note(card_name)
        if note:
            notes.append(f"Card action cue: {note}")

    return notes


def _collect_power_names(entity: dict[str, Any]) -> list[str]:
    powers = entity.get("powers") or entity.get("status") or []
    names: list[str] = []
    for power in powers:
        if not isinstance(power, dict):
            continue
        name = str(power.get("name", "") or power.get("title", "")).strip()
        if name:
            names.append(name)
    return names


def _status_knowledge_notes(state: dict[str, Any], max_notes: int = 4) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()

    player = state.get("player") or {}
    for power_name in _collect_power_names(player):
        key = power_name.casefold()
        if key in seen:
            continue
        seen.add(key)
        note = _knowledge.brief_power_note(power_name)
        if note:
            notes.append(f"Status cue: {note}")
        if len(notes) >= max_notes:
            return notes

    battle = state.get("battle") or {}
    for enemy in battle.get("enemies") or []:
        for power_name in _collect_power_names(enemy):
            key = power_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            note = _knowledge.brief_power_note(power_name)
            if note:
                notes.append(f"Status cue: {note}")
            if len(notes) >= max_notes:
                return notes

    return notes[:max_notes]


def _mechanic_knowledge_notes(queries: list[str], max_notes: int = 2) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = query.casefold()
        if key in seen:
            continue
        seen.add(key)
        text = _knowledge.lookup_mechanic(query, max_results=1)
        if not text.startswith("# Mechanics"):
            continue
        lines = text.splitlines()
        if len(lines) >= 3:
            notes.append(f"Mechanic cue: {lines[1].lstrip('- ').strip()} {lines[2].strip()}")
        if len(notes) >= max_notes:
            break
    return notes


def _event_knowledge_notes(event_state: dict[str, Any]) -> list[str]:
    event_name = str(event_state.get("name", "") or event_state.get("id", "")).strip()
    if not event_name:
        return []
    note = _knowledge.brief_event_note(event_name)
    return [f"Event cue: {note}"] if note else []


def _potion_knowledge_notes(state: dict[str, Any], max_notes: int = 3) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()

    player = state.get("player") or {}
    for potion in player.get("potions") or []:
        if not isinstance(potion, dict):
            continue
        name = str(potion.get("name", "")).strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        note = _knowledge.brief_potion_note(name)
        if note:
            notes.append(f"Potion cue: {note}")
        if len(notes) >= max_notes:
            break

    return notes


def _contextual_advice_from_state(state: dict[str, Any]) -> str:
    state_type = state.get("state_type", "unknown")
    player = state.get("player") or {}
    hp = player.get("hp", "?")
    max_hp = player.get("max_hp", "?")
    gold = player.get("gold", "?")
    character = player.get("character", "Unknown")
    hp_ratio = _hp_ratio(state)

    lines = [
        f"# Contextual Advice",
        f"- State: {state_type}",
        f"- Character: {character} | HP: {hp}/{max_hp} | Gold: {gold}",
    ]

    build_hint = _knowledge.lookup_builds(str(character), max_results=2)
    if not build_hint.startswith("Unknown character") and not build_hint.startswith("No builds found"):
        lines.append("")
        lines.append("## Build Reference")
        lines.extend(build_hint.splitlines()[:6])

    if state_type in {"monster", "elite", "boss", "hand_select"}:
        battle = state.get("battle") or {}
        battle_player = battle.get("player") or {}
        hand = battle_player.get("hand") or []
        enemies = battle.get("enemies") or []
        energy = battle_player.get("energy", 0)
        block = battle_player.get("block", 0)
        playable = [card for card in hand if card.get("can_play")]
        attacking = []
        for enemy in enemies:
            if _enemy_is_attacking(enemy):
                attacking.append(enemy.get("name", enemy.get("entity_id", "Enemy")))

        lines.append("")
        lines.append("## Combat Advice")
        lines.append(f"- Energy: {energy} | Block: {block} | Playable cards: {len(playable)}")
        if attacking:
            lines.append(f"- Threats attacking now: {', '.join(attacking[:3])}")
            lines.append("- Cover meaningful incoming damage before dumping all energy into offense.")
        else:
            lines.append("- No obvious attack intent detected, so prioritize damage, draw, scaling, or setup over block.")

        if playable:
            expensive = [card.get("name", "?") for card in playable if card.get("cost", 99) == energy]
            zero_cost = [card.get("name", "?") for card in playable if card.get("cost", 99) == 0]
            if zero_cost:
                lines.append(f"- Free cards to consider first: {', '.join(zero_cost[:4])}")
            if expensive:
                lines.append(f"- Cards that spend your remaining energy efficiently: {', '.join(expensive[:4])}")
        else:
            lines.append("- No playable cards detected; ending turn may be correct after checking potion usage.")

        if enemies:
            lowest = min(enemies, key=lambda enemy: enemy.get("hp", 10**9))
            lines.append(
                f"- Check for lethal on {lowest.get('name', lowest.get('entity_id', 'enemy'))}"
                f" first; current HP appears to be {lowest.get('hp', '?')}."
            )

        for note in _summarize_relic_synergy(state):
            lines.append(f"- {note}")

        knowledge_notes = _combat_knowledge_notes(hand, playable, enemies)
        if knowledge_notes:
            lines.append("")
            lines.append("## Knowledge References")
            for note in knowledge_notes[:5]:
                lines.append(f"- {note}")

        status_notes = _status_knowledge_notes(state, max_notes=4)
        mechanic_queries: list[str] = []
        if any("weak" in str(name).lower() for name in attacking):
            mechanic_queries.append("weak")
        for enemy in enemies:
            for power_name in _collect_power_names(enemy):
                lowered = power_name.casefold()
                if "poison" in lowered:
                    mechanic_queries.append("poison")
                if "vulnerable" in lowered:
                    mechanic_queries.append("vulnerable")
                if "weak" in lowered:
                    mechanic_queries.append("weak")
        for power_name in _collect_power_names(player):
            lowered = power_name.casefold()
            if "block" in lowered or "barricade" in lowered or "blur" in lowered:
                mechanic_queries.append("block")
        mechanic_notes = _mechanic_knowledge_notes(mechanic_queries, max_notes=2)
        if status_notes or mechanic_notes:
            lines.append("")
            lines.append("## Status References")
            for note in status_notes + mechanic_notes:
                lines.append(f"- {note}")

    elif state_type == "combat_rewards":
        rewards = state.get("rewards") or {}
        items = rewards.get("items") or []
        lines.append("")
        lines.append("## Reward Advice")
        if items:
            reward_types = ", ".join(str(item.get("type", "?")) for item in items[:6])
            lines.append(f"- Visible rewards: {reward_types}")
            lines.append("- Relics are usually highest priority, then strong card rewards, then potions if slots are open.")
            lines.append("- Claim rewards from right to left to reduce index shifting mistakes.")
        if rewards.get("can_proceed"):
            lines.append("- If all useful rewards are already taken, proceed to map.")

    elif state_type == "card_reward":
        reward = state.get("card_reward") or {}
        cards = reward.get("cards") or []
        lines.append("")
        lines.append("## Card Reward Advice")
        lines.append("- Prefer cards that clearly strengthen your current build; skip mediocre filler.")
        if cards:
            names = ", ".join(str(card.get("name", "?")) for card in cards[:5])
            lines.append(f"- Offered cards: {names}")

    elif state_type == "map":
        map_data = state.get("map") or {}
        next_options = map_data.get("next_options") or []
        lines.append("")
        lines.append("## Map Advice")
        if hp_ratio is not None:
            lines.append(f"- HP ratio is about {hp_ratio:.0%}.")
        suggestion = _recommend_map_node(next_options, hp_ratio)
        if suggestion:
            lines.append(f"- {suggestion}")
        lines.append("- Healthy runs can route into Elites for relics; low-HP runs should bias toward Rest Sites, Shops, and safer fights.")

    elif state_type == "rest_site":
        rest_site = state.get("rest_site") or {}
        options = rest_site.get("options") or []
        lines.append("")
        lines.append("## Rest Site Advice")
        if hp_ratio is not None and hp_ratio < 0.5:
            lines.append("- HP is low, so Rest is usually safer than greedier options.")
        else:
            lines.append("- If HP is comfortable, upgrading a core card is often better than resting.")
        if options:
            lines.append("- Available options: " + ", ".join(str(option.get("name", "?")) for option in options[:6]))

    elif state_type == "shop":
        shop = state.get("shop") or {}
        lines.append("")
        lines.append("## Shop Advice")
        lines.append("- Prioritize high-impact relics, premium card removal, or cards that fix a real deck weakness.")
        affordable_relics = [
            item.get("name", "?")
            for item in (shop.get("relics") or [])
            if item.get("affordable")
        ]
        if affordable_relics:
            lines.append(f"- Affordable relics: {', '.join(affordable_relics[:4])}")
        potion_notes = _potion_knowledge_notes(state, max_notes=3)
        if potion_notes:
            lines.append("")
            lines.append("## Potion References")
            for note in potion_notes:
                lines.append(f"- {note}")

    elif state_type == "event":
        event = state.get("event") or {}
        options = event.get("options") or []
        lines.append("")
        lines.append("## Event Advice")
        lines.append("- Read costs carefully. Favor low-risk permanent gains; avoid big HP losses unless the payoff is exceptional.")
        unlocked = [str(option.get("title", "?")) for option in options if not option.get("locked")]
        if unlocked:
            lines.append(f"- Available options: {', '.join(unlocked[:6])}")
        event_notes = _event_knowledge_notes(event)
        if event_notes:
            lines.append("")
            lines.append("## Knowledge References")
            for note in event_notes:
                lines.append(f"- {note}")

    elif state_type == "relic_select":
        relic_select = state.get("relic_select") or {}
        relics = relic_select.get("relics") or []
        lines.append("")
        lines.append("## Relic Choice Advice")
        lines.append("- Favor relics that immediately improve energy, scaling, or consistency over narrow gimmicks.")
        if relics:
            lines.append("- Offered relics: " + ", ".join(str(relic.get("name", "?")) for relic in relics[:5]))

    elif state_type == "treasure":
        treasure = state.get("treasure") or {}
        relics = treasure.get("relics") or []
        lines.append("")
        lines.append("## Treasure Advice")
        lines.append("- Treasure relics are usually worth taking unless a specific downside is severe.")
        if relics:
            lines.append("- Visible relics: " + ", ".join(str(relic.get("name", "?")) for relic in relics[:5]))

    else:
        lines.append("")
        lines.append("## General Advice")
        lines.append("- Use get_game_state(json) to inspect the current screen details, then call focused knowledge tools as needed.")

    return "\n".join(lines)


@mcp.tool()
async def get_contextual_advice() -> str:
    """Get lightweight rule-based advice for the current game state.

    This tool fetches the latest game state as JSON and returns concise,
    state-aware guidance plus a small character build reference when available.
    """
    try:
        raw = await _get({"format": "json"})
        state = json.loads(raw)
        if not isinstance(state, dict):
            return "Error: Unexpected game state payload."
        return _contextual_advice_from_state(state)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def use_potion(slot: int, target: str | None = None) -> str:
    """Use a potion from the player's potion slots.

    Works both during and outside of combat. Combat-only potions require an active battle.

    Args:
        slot: Potion slot index (as shown in game state).
        target: Entity ID of the target enemy (e.g. "JAW_WORM_0"). Required for enemy-targeted potions.
    """
    body: dict = {"action": "use_potion", "slot": slot}
    if target is not None:
        body["target"] = target
    try:
        return await _post(body)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def proceed_to_map() -> str:
    """Proceed from the current screen to the map.

    Works from: rewards screen, rest site, shop.
    Does NOT work for events — use event_choose_option() with the Proceed option's index.
    """
    try:
        return await _post({"action": "proceed"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Combat (state_type: monster / elite / boss)
# ---------------------------------------------------------------------------


@mcp.tool()
async def combat_play_card(card_index: int, target: str | None = None) -> str:
    """[Combat] Play a card from the player's hand.

    Args:
        card_index: Index of the card in hand (0-based, as shown in game state).
        target: Entity ID of the target enemy (e.g. "JAW_WORM_0"). Required for single-target cards.

    Note that the index can change as cards are played - playing a card will shift the indices of remaining cards in hand.
    Refer to the latest game state for accurate indices. New cards are drawn to the right, so playing cards from right to left can help maintain more stable indices for remaining cards.
    """
    body: dict = {"action": "play_card", "card_index": card_index}
    if target is not None:
        body["target"] = target
    try:
        return await _post(body)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def combat_end_turn() -> str:
    """[Combat] End the player's current turn."""
    try:
        return await _post({"action": "end_turn"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# In-Combat Card Selection (state_type: hand_select)
# ---------------------------------------------------------------------------


@mcp.tool()
async def combat_select_card(card_index: int) -> str:
    """[Combat Selection] Select a card from hand during an in-combat card selection prompt.

    Used when a card effect asks you to select a card to exhaust, discard, etc.
    This is different from deck_select_card which handles out-of-combat card selection overlays.

    Args:
        card_index: 0-based index of the card in the selectable hand cards (as shown in game state).
    """
    try:
        return await _post({"action": "combat_select_card", "card_index": card_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def combat_confirm_selection() -> str:
    """[Combat Selection] Confirm the in-combat card selection.

    After selecting the required number of cards from hand (exhaust, discard, etc.),
    use this to confirm the selection. Only works when the confirm button is enabled.
    """
    try:
        return await _post({"action": "combat_confirm_selection"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Rewards (state_type: combat_rewards / card_reward)
# ---------------------------------------------------------------------------


@mcp.tool()
async def rewards_claim(reward_index: int) -> str:
    """[Rewards] Claim a reward from the post-combat rewards screen.

    Gold, potion, and relic rewards are claimed immediately.
    Card rewards open the card selection screen (state changes to card_reward).

    Args:
        reward_index: 0-based index of the reward on the rewards screen.

    Note that claiming a reward may change the indices of remaining rewards, so refer to the latest game state for accurate indices.
    Claiming from right to left can help maintain more stable indices for remaining rewards, as rewards will always shift left to fill in gaps.
    """
    try:
        return await _post({"action": "claim_reward", "index": reward_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def rewards_pick_card(card_index: int) -> str:
    """[Rewards] Select a card from the card reward selection screen.

    Args:
        card_index: 0-based index of the card to add to the deck.
    """
    try:
        return await _post({"action": "select_card_reward", "card_index": card_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def rewards_skip_card() -> str:
    """[Rewards] Skip the card reward without selecting a card."""
    try:
        return await _post({"action": "skip_card_reward"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Map (state_type: map)
# ---------------------------------------------------------------------------


@mcp.tool()
async def map_choose_node(node_index: int) -> str:
    """[Map] Choose a map node to travel to.

    Args:
        node_index: 0-based index of the node from the next_options list.
    """
    try:
        return await _post({"action": "choose_map_node", "index": node_index})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Rest Site (state_type: rest_site)
# ---------------------------------------------------------------------------


@mcp.tool()
async def rest_choose_option(option_index: int) -> str:
    """[Rest Site] Choose a rest site option (rest, smith, etc.).

    Args:
        option_index: 0-based index of the option from the rest site state.
    """
    try:
        return await _post({"action": "choose_rest_option", "index": option_index})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Shop (state_type: shop)
# ---------------------------------------------------------------------------


@mcp.tool()
async def shop_purchase(item_index: int) -> str:
    """[Shop] Purchase an item from the shop.

    Args:
        item_index: 0-based index of the item from the shop state.
    """
    try:
        return await _post({"action": "shop_purchase", "index": item_index})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Event (state_type: event)
# ---------------------------------------------------------------------------


@mcp.tool()
async def event_choose_option(option_index: int) -> str:
    """[Event] Choose an event option.

    Works for both regular events and ancients (after dialogue ends).
    Also used to click the Proceed option after an event resolves.

    Args:
        option_index: 0-based index of the unlocked option.
    """
    try:
        return await _post({"action": "choose_event_option", "index": option_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def event_advance_dialogue() -> str:
    """[Event] Advance ancient event dialogue.

    Click through dialogue text in ancient events. Call repeatedly until options appear.
    """
    try:
        return await _post({"action": "advance_dialogue"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Card Selection (state_type: card_select)
# ---------------------------------------------------------------------------


@mcp.tool()
async def deck_select_card(card_index: int) -> str:
    """[Card Selection] Select or deselect a card in the card selection screen.

    Used when the game asks you to choose cards from your deck (transform, upgrade,
    remove, discard) or pick a card from offered choices (potions, effects).

    For deck selections: toggles card selection. For choose-a-card: picks immediately.

    Args:
        card_index: 0-based index of the card (as shown in game state).
    """
    try:
        return await _post({"action": "select_card", "index": card_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def deck_confirm_selection() -> str:
    """[Card Selection] Confirm the current card selection.

    After selecting the required number of cards, use this to confirm.
    If a preview is showing (e.g., transform preview), this confirms the preview.
    Not needed for choose-a-card screens where picking is immediate.
    """
    try:
        return await _post({"action": "confirm_selection"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def deck_cancel_selection() -> str:
    """[Card Selection] Cancel the current card selection.

    If a preview is showing, goes back to the selection grid.
    For choose-a-card screens, clicks the skip button (if available).
    Otherwise, closes the card selection screen (only if cancellation is allowed).
    """
    try:
        return await _post({"action": "cancel_selection"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Relic Selection (state_type: relic_select)
# ---------------------------------------------------------------------------


@mcp.tool()
async def relic_select(relic_index: int) -> str:
    """[Relic Selection] Select a relic from the relic selection screen.

    Used when the game offers a choice of relics (e.g., boss relic rewards).

    Args:
        relic_index: 0-based index of the relic (as shown in game state).
    """
    try:
        return await _post({"action": "select_relic", "index": relic_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def relic_skip() -> str:
    """[Relic Selection] Skip the relic selection without choosing a relic."""
    try:
        return await _post({"action": "skip_relic_selection"})
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Treasure (state_type: treasure)
# ---------------------------------------------------------------------------


@mcp.tool()
async def treasure_claim_relic(relic_index: int) -> str:
    """[Treasure] Claim a relic from the treasure chest.

    The chest is auto-opened when entering the treasure room.
    After claiming, use proceed_to_map() to continue.

    Args:
        relic_index: 0-based index of the relic (as shown in game state).
    """
    try:
        return await _post({"action": "claim_treasure_relic", "index": relic_index})
    except Exception as e:
        return _handle_error(e)


# ===========================================================================
# MULTIPLAYER tools — all route through /api/v1/multiplayer
# ===========================================================================


@mcp.tool()
async def mp_get_game_state(format: str = "markdown") -> str:
    """[Multiplayer] Get the current multiplayer game state.

    Returns full game state for ALL players: HP, powers, relics, potions,
    plus multiplayer-specific data: map votes, event votes, treasure bids,
    end-turn ready status. Only works during a multiplayer run.

    Args:
        format: "markdown" for human-readable output, "json" for structured data.
    """
    try:
        return await _mp_get({"format": format})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_combat_play_card(card_index: int, target: str | None = None) -> str:
    """[Multiplayer Combat] Play a card from the local player's hand.

    Same as singleplayer combat_play_card but routed through the multiplayer
    endpoint for sync safety.

    Args:
        card_index: Index of the card in hand (0-based).
        target: Entity ID of the target enemy (e.g. "JAW_WORM_0"). Required for single-target cards.
    """
    body: dict = {"action": "play_card", "card_index": card_index}
    if target is not None:
        body["target"] = target
    try:
        return await _mp_post(body)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_combat_end_turn() -> str:
    """[Multiplayer Combat] Submit end-turn vote.

    In multiplayer, ending the turn is a VOTE — the turn only ends when ALL
    players have submitted. Use mp_combat_undo_end_turn() to retract.
    """
    try:
        return await _mp_post({"action": "end_turn"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_combat_undo_end_turn() -> str:
    """[Multiplayer Combat] Retract end-turn vote.

    If you submitted end turn but want to play more cards, use this to undo.
    Only works if other players haven't all committed yet.
    """
    try:
        return await _mp_post({"action": "undo_end_turn"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_use_potion(slot: int, target: str | None = None) -> str:
    """[Multiplayer] Use a potion from the local player's potion slots.

    Args:
        slot: Potion slot index (as shown in game state).
        target: Entity ID of the target enemy. Required for enemy-targeted potions.
    """
    body: dict = {"action": "use_potion", "slot": slot}
    if target is not None:
        body["target"] = target
    try:
        return await _mp_post(body)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_map_vote(node_index: int) -> str:
    """[Multiplayer Map] Vote for a map node to travel to.

    In multiplayer, map selection is a vote — travel happens when all players
    agree. Re-voting for the same node sends a ping to other players.

    Args:
        node_index: 0-based index of the node from the next_options list.
    """
    try:
        return await _mp_post({"action": "choose_map_node", "index": node_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_event_choose_option(option_index: int) -> str:
    """[Multiplayer Event] Choose or vote for an event option.

    For shared events: this is a vote (resolves when all players vote).
    For individual events: immediate choice, same as singleplayer.

    Args:
        option_index: 0-based index of the unlocked option.
    """
    try:
        return await _mp_post({"action": "choose_event_option", "index": option_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_event_advance_dialogue() -> str:
    """[Multiplayer Event] Advance ancient event dialogue."""
    try:
        return await _mp_post({"action": "advance_dialogue"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_rest_choose_option(option_index: int) -> str:
    """[Multiplayer Rest Site] Choose a rest site option (rest, smith, etc.).

    Per-player choice — no voting needed.

    Args:
        option_index: 0-based index of the option.
    """
    try:
        return await _mp_post({"action": "choose_rest_option", "index": option_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_shop_purchase(item_index: int) -> str:
    """[Multiplayer Shop] Purchase an item from the shop.

    Per-player inventory — no voting needed.

    Args:
        item_index: 0-based index of the item.
    """
    try:
        return await _mp_post({"action": "shop_purchase", "index": item_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_rewards_claim(reward_index: int) -> str:
    """[Multiplayer Rewards] Claim a reward from the post-combat rewards screen.

    Args:
        reward_index: 0-based index of the reward.
    """
    try:
        return await _mp_post({"action": "claim_reward", "index": reward_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_rewards_pick_card(card_index: int) -> str:
    """[Multiplayer Rewards] Select a card from the card reward screen.

    Args:
        card_index: 0-based index of the card to add to the deck.
    """
    try:
        return await _mp_post({"action": "select_card_reward", "card_index": card_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_rewards_skip_card() -> str:
    """[Multiplayer Rewards] Skip the card reward."""
    try:
        return await _mp_post({"action": "skip_card_reward"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_proceed_to_map() -> str:
    """[Multiplayer] Proceed from the current screen to the map.

    Works from: rewards screen, rest site, shop.
    """
    try:
        return await _mp_post({"action": "proceed"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_deck_select_card(card_index: int) -> str:
    """[Multiplayer Card Selection] Select or deselect a card in the card selection screen.

    Args:
        card_index: 0-based index of the card.
    """
    try:
        return await _mp_post({"action": "select_card", "index": card_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_deck_confirm_selection() -> str:
    """[Multiplayer Card Selection] Confirm the current card selection."""
    try:
        return await _mp_post({"action": "confirm_selection"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_deck_cancel_selection() -> str:
    """[Multiplayer Card Selection] Cancel the current card selection."""
    try:
        return await _mp_post({"action": "cancel_selection"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_combat_select_card(card_index: int) -> str:
    """[Multiplayer Combat Selection] Select a card from hand during in-combat card selection.

    Args:
        card_index: 0-based index of the card in the selectable hand cards.
    """
    try:
        return await _mp_post({"action": "combat_select_card", "card_index": card_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_combat_confirm_selection() -> str:
    """[Multiplayer Combat Selection] Confirm the in-combat card selection."""
    try:
        return await _mp_post({"action": "combat_confirm_selection"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_relic_select(relic_index: int) -> str:
    """[Multiplayer Relic Selection] Select a relic (boss relic rewards).

    Args:
        relic_index: 0-based index of the relic.
    """
    try:
        return await _mp_post({"action": "select_relic", "index": relic_index})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_relic_skip() -> str:
    """[Multiplayer Relic Selection] Skip the relic selection."""
    try:
        return await _mp_post({"action": "skip_relic_selection"})
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def mp_treasure_claim_relic(relic_index: int) -> str:
    """[Multiplayer Treasure] Bid on / claim a relic from the treasure chest.

    In multiplayer, this is a bid — if multiple players pick the same relic,
    a "relic fight" determines the winner. Others get consolation prizes.

    Args:
        relic_index: 0-based index of the relic.
    """
    try:
        return await _mp_post({"action": "claim_treasure_relic", "index": relic_index})
    except Exception as e:
        return _handle_error(e)


def main():
    parser = argparse.ArgumentParser(description="STS2 MCP Server")
    parser.add_argument("--port", type=int, default=15526, help="Game HTTP server port")
    parser.add_argument("--host", type=str, default="localhost", help="Game HTTP server host")
    args = parser.parse_args()

    global _base_url
    _base_url = f"http://{args.host}:{args.port}"

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
