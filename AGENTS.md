# STS2 MCP — AI Gameplay Guide

## MCP Tool Calling Tips

### Decision Style
- Use a **calculated greed** playstyle.
- This means: prefer lines with clearly higher expected long-term value, even when they involve controlled short-term risk.
- Do **not** default to the safest option when a riskier line has materially better upside and the run is not close to collapsing.
- Do **not** confuse calculated greed with recklessness. Avoid lines that create a serious chance of immediate run death without commensurate payoff.
- HP is a resource. Gold, relics, scaling, strong upgrades, and archetype-defining picks often justify taking manageable damage or risk.

### State Polling
- After `combat_end_turn`, the state may show `is_play_phase: false` or `turn: enemy`. Call `get_game_state` again to advance to the next player turn.
- Sometimes you need to call `get_game_state` twice — once to see enemy turn results, once to see your new hand.
- Use `format: "json"` during combat for structured data; `format: "markdown"` for map/event overview.

### Card Index Shifting
- **CRITICAL**: Playing a card removes it from hand and shifts all indices. Play cards from RIGHT to LEFT (highest index first) to keep lower indices stable, or re-check state between plays.
- When targeting, always provide `target` for single-target cards. Entity IDs are UPPER_SNAKE_CASE with a `_0` suffix (e.g. `KIN_PRIEST_0`).

### Event & Reward Flow
- Events: `event_choose_option`. After choosing, there's often a "Proceed" option at index 0.
- Rest sites: `rest_choose_option`, then `proceed_to_map`.
- Rewards: claim from right-to-left (highest index first) to avoid index shifting. Card rewards open a sub-screen; use `rewards_pick_card` or `rewards_skip_card`.

### Potions
- `use_potion(slot=N)` — slot is the potion slot index, not a card index.
- Potions don't cost energy or count as card plays. Use buff potions BEFORE playing cards.

### Knowledge Tools
- Treat `get_contextual_advice()` as the default first knowledge step for any non-trivial decision.
- Unified decision SOP:
  1. Call `get_game_state(format="json")`.
  2. Call `get_contextual_advice()`.
  3. Read the `Recommended Follow-up Tools` section from `get_contextual_advice()` and execute the suggested lookups unless the decision is truly trivial.
  4. Form a provisional line using a **calculated greed** standard: prefer higher expected payoff when the added risk is controlled.
  5. Execute the action.
- Knowledge usage should be the default, not the exception. For elite fights, boss fights, card rewards, shops, events, relic choices, and treasure screens, do not stop at `get_contextual_advice()` alone when it suggests a relevant lookup.
- In combat, if there is a dangerous enemy, an unfamiliar key card, an important relic interaction, or meaningful status math, use at least one targeted knowledge lookup before committing the turn.
- On `card_reward`, `shop`, `event`, `relic_select`, and `treasure`, use at least one targeted lookup whenever there is a non-obvious option with meaningful long-term value.
- If `get_contextual_advice()` suggests a follow-up lookup, strongly prefer performing it rather than answering from memory.
- In combat, `get_contextual_advice()` already tries to reference:
  - enemies that are currently attacking
  - cards you can actually play this turn
  - active powers / buffs / debuffs
  - relevant mechanic rules such as block, vulnerable, weak, or poison
- Outside combat, `get_contextual_advice()` already tries to reference:
  - event knowledge on event screens
  - reward knowledge on reward and card reward screens
  - affordable relic / card / potion knowledge in shops
  - route-aware build and survival hints on the map
- Use `lookup_enemy(enemy_name)` when a dangerous enemy, elite, or boss still needs more detailed move-context than `get_contextual_advice()` provided.
- Use `lookup_card(card_name)` when a hand card, reward card, or selection card remains strategically unclear after the contextual summary.
- Use `lookup_relic(relic_name)` when a relic may meaningfully change sequencing, valuation, or long-term routing.
- Use `lookup_potion(potion_name)` when potion timing, target choice, or conservation is the key decision.
- Use `lookup_event(event_name)` when an event branch has meaningful long-term consequences and the contextual summary is still insufficient.
- Use `lookup_power(power_name)` or `lookup_mechanic(query)` when combat math depends on a specific status effect or rules interaction.
- Use `lookup_builds(character_name)` when deck direction is unclear and you need high-level archetype guidance for the current character.
- Use `get_general_strategy()` only as a broad fallback. Prefer state-aware and targeted tools first.
- Do NOT spam every knowledge tool every turn. Prefer the smallest set of lookups that resolves the current decision.
- If `get_contextual_advice()` already provides enough guidance and suggests no follow-up lookup, you may act directly; otherwise, prefer following the suggested knowledge calls first.

---

## General Strategy

### Core Principles
1. **HP is a resource, not a score.** Spend it when the return is strong enough.
2. **Prefer expected value, not safety theater.** Choose the line with better long-term payoff when the extra risk is controlled.
3. **Deck quality > deck size.** Skip filler, but be willing to take powerful synergy and scaling pieces over merely safe cards.
4. **Front-load damage and scaling.** Winning fights faster and snowballing harder usually beats over-defending.
5. **Read intents carefully.** Sleep/Buff = punish greedily. Attack = balance block and damage. Debuff = often an invitation to push offense or setup.

### Combat Sequencing (General)
1. Play 0-cost utility/setup cards first.
2. Play skills before attacks when possible — many mechanics reward this order (e.g. Slow debuff on enemies stacks per card played).
3. Play biggest attacks last to benefit from accumulated buffs/debuffs.
4. Check enemy HP — if you can kill this turn, skip blocking entirely.
5. Do not overvalue preventing small damage if a greedier line creates much better lethal, scaling, or tempo.

### Map Pathing
- **Elites** give relics and snowball runs. Prefer elite routes aggressively when survival is still credible.
- **Rest before Boss** only when the survival gain clearly beats the value of an upgrade.
- **Unknown nodes** are flexible, but do not over-prefer them over clearly higher-value routes.
- **Shops** are valuable with meaningful gold, especially when they can buy power spikes or remove weak cards.
- **Deck quality matters more than quantity** — don't add cards just because they're offered, but do take strong archetype-defining cards.

### Boss Fights
- **Kill the leader, not the minions.** Enemies with "Minion" power flee when their leader dies.
- Use potions aggressively in boss fights — they don't carry between acts.
- Boss fights are wars of attrition. The longer they go, the more enemies scale with Strength buffs.

### Potion Usage
- Don't hoard potions. Dying with full potions is the worst outcome.
- Use permanent-value potions (Fruit Juice = +5 Max HP) early in any combat.
- Use buff potions (Flex Potion) on turns with multiple attacks.

### Common Mistakes
- Blocking when enemies are sleeping/buffing — waste of energy.
- Taking the safest line by reflex when a greedier line has much better expected value.
- Not checking card indices after playing — indices shift left.
- Taking too long to kill bosses — enemies scale every turn.
- Adding mediocre cards that dilute the deck before boss fights.
