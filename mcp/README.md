# MCP Tools

## Recommended Flow

- Use a **calculated greed** decision style: prefer the line with higher expected long-term reward when the extra risk is controlled and does not create a serious chance of immediate collapse.
- Unified decision SOP:
  1. Call `get_game_state(format="json")`.
  2. Call `get_contextual_advice()`.
  3. Form a provisional action using a calculated-greed standard.
  4. If still uncertain, call only the most relevant targeted lookup tools.
  5. Execute the action.
- In combat, `get_contextual_advice()` already prioritizes:
  - enemies currently attacking
  - cards you can actually play this turn
  - active powers / buffs / debuffs
  - key mechanics such as block, vulnerable, weak, and poison
- Outside combat, `get_contextual_advice()` already tries to reference:
  - event knowledge on event screens
  - reward and card reward knowledge
  - affordable relic / card / potion knowledge in shops
  - route-aware build and survival hints on the map
- If you still need more detail, follow up with only the most relevant targeted lookup:
  - `lookup_enemy(enemy_name)` for a threatening enemy or boss
  - `lookup_card(card_name)` for a key hand card or reward card
  - `lookup_relic(relic_name)` when a relic changes sequencing or valuation
  - `lookup_potion(potion_name)` when potion timing matters
  - `lookup_event(event_name)` when an event branch has meaningful long-term tradeoffs
  - `lookup_power(power_name)` or `lookup_mechanic(query)` when combat math is unclear
  - `lookup_builds(character_name)` when deck direction is unclear
- Avoid calling every knowledge tool every turn. Prefer the smallest set of lookups that resolves the current decision.

## Run-End Notifications

- A standalone watcher script is available as `run_end_notifier.py`.
- It polls the local STS2 MCP HTTP API and watches for a transition from an active run to `state_type = "menu"`.
- When a run ends, it sends a Feishu webhook notification containing:
  - likely result
  - character
  - act / floor reached
  - ascension
  - HP and gold
  - relic count and potion count
  - last visible screen
- Run it with:

```bash
uv run --directory /path/to/STS2_MCP/mcp python run_end_notifier.py
```

- Optional flags:
  - `--host`
  - `--port`
  - `--webhook-url`
  - `--poll-interval`

## Singleplayer

| Tool | Scope | Description |
|---|---|---|
| `get_game_state(format?)` | General | Get current game state (`markdown` or `json`) |
| `get_general_strategy(max_chars?)` | Knowledge | Get bundled high-level gameplay strategy notes |
| `get_contextual_advice()` | Knowledge | Get lightweight state-aware advice using current game state |
| `lookup_card(card_name)` | Knowledge | Look up a card by English/Chinese name or slug |
| `lookup_character(character_name)` | Knowledge | Look up a character profile and playstyle summary |
| `lookup_event(event_name)` | Knowledge | Look up an event and summarize its visible options |
| `lookup_potion(potion_name)` | Knowledge | Look up a potion including usage and targeting |
| `lookup_power(power_name)` | Knowledge | Look up a power or status effect |
| `lookup_enchantment(enchantment_name)` | Knowledge | Look up an enchantment and its effect |
| `lookup_mechanic(query, max_results?)` | Knowledge | Search core game mechanics notes |
| `lookup_enemy(enemy_name)` | Knowledge | Look up an enemy and its known move names |
| `lookup_relic(relic_name)` | Knowledge | Look up a relic by English/Chinese name or slug |
| `lookup_builds(character_name, max_results?)` | Knowledge | Get a few bundled build recommendations for a character |
| `use_potion(slot, target?)` | General | Use a potion (works in and out of combat) |
| `proceed_to_map()` | General | Proceed from rewards/rest site/shop/treasure to the map |
| `combat_play_card(card_index, target?)` | Combat | Play a card from hand |
| `combat_end_turn()` | Combat | End the current turn |
| `combat_select_card(card_index)` | Combat Selection | Select a card from hand during exhaust/discard prompts |
| `combat_confirm_selection()` | Combat Selection | Confirm the in-combat card selection |
| `rewards_claim(reward_index)` | Rewards | Claim a reward from the post-combat screen |
| `rewards_pick_card(card_index)` | Rewards | Select a card from the card reward screen |
| `rewards_skip_card()` | Rewards | Skip the card reward |
| `map_choose_node(node_index)` | Map | Choose a map node to travel to |
| `rest_choose_option(option_index)` | Rest Site | Choose a rest site option (rest, smith, etc.) |
| `shop_purchase(item_index)` | Shop | Purchase an item from the shop |
| `event_choose_option(option_index)` | Event | Choose an event option (including Proceed) |
| `event_advance_dialogue()` | Event | Advance ancient event dialogue |
| `deck_select_card(card_index)` | Card Select | Pick/toggle a card in the selection screen |
| `deck_confirm_selection()` | Card Select | Confirm the current card selection |
| `deck_cancel_selection()` | Card Select | Cancel/skip card selection |
| `relic_select(relic_index)` | Relic Select | Choose a relic from the selection screen |
| `relic_skip()` | Relic Select | Skip relic selection |
| `treasure_claim_relic(relic_index)` | Treasure | Claim a relic from the treasure chest |

## Multiplayer

All multiplayer tools are prefixed with `mp_`. They route through `/api/v1/multiplayer` and are only available during multiplayer (co-op) runs. The endpoints automatically guard against cross-mode calls.

| Tool | Scope | Description |
|---|---|---|
| `mp_get_game_state(format?)` | General | Get multiplayer game state (all players, votes, bids) |
| `mp_combat_play_card(card_index, target?)` | Combat | Play a card from the local player's hand |
| `mp_combat_end_turn()` | Combat | Submit end-turn vote (turn ends when all players submit) |
| `mp_combat_undo_end_turn()` | Combat | Retract end-turn vote |
| `mp_use_potion(slot, target?)` | General | Use a potion from the local player's slots |
| `mp_proceed_to_map()` | General | Proceed from current screen to the map |
| `mp_map_vote(node_index)` | Map | Vote for a map node (travel when all agree) |
| `mp_event_choose_option(option_index)` | Event | Vote for / choose an event option |
| `mp_event_advance_dialogue()` | Event | Advance ancient event dialogue |
| `mp_rest_choose_option(option_index)` | Rest Site | Choose a rest site option (per-player, no vote) |
| `mp_shop_purchase(item_index)` | Shop | Purchase an item (per-player inventory) |
| `mp_rewards_claim(reward_index)` | Rewards | Claim a post-combat reward |
| `mp_rewards_pick_card(card_index)` | Rewards | Select a card from the card reward screen |
| `mp_rewards_skip_card()` | Rewards | Skip the card reward |
| `mp_deck_select_card(card_index)` | Card Select | Pick/toggle a card in the selection screen |
| `mp_deck_confirm_selection()` | Card Select | Confirm the current card selection |
| `mp_deck_cancel_selection()` | Card Select | Cancel/skip card selection |
| `mp_combat_select_card(card_index)` | Combat Selection | Select a card during in-combat selection prompts |
| `mp_combat_confirm_selection()` | Combat Selection | Confirm in-combat card selection |
| `mp_relic_select(relic_index)` | Relic Select | Choose a relic from the selection screen |
| `mp_relic_skip()` | Relic Select | Skip relic selection |
| `mp_treasure_claim_relic(relic_index)` | Treasure | Bid on a relic (relic fight if contested) |
