Play Slay the Spire 2 using the MCP tools (`mcp__sts2__*`). Your goal is to win the run while strictly obeying the active run policy when one exists.

## Setup
1. Read `AGENTS.md` for general MCP calling tips.
2. Call `get_run_policy()` before making any deck-building decision.
3. Immediately summarize the active run policy in 4-8 concise bullet points before taking any meaningful action, including:
   - target build name
   - win condition
   - core cards
   - support cards
   - avoid cards
   - removal and upgrade priorities
   - what must be hard-avoided
4. Treat the returned run policy as the highest-priority deck-building rule set.
5. Use `get_fast_game_state()` as the default state tool.
6. Only call `get_game_state(format="markdown")` when you need a broad overview for map, event, or treasure screens.
7. Only call `get_game_state(format="json")` when you need the full detailed payload.

## Hard Policy Rules
- If `get_run_policy()` returns an active policy, you must follow it for card rewards, shop purchases, upgrades, removals, and other deck-shaping choices.
- If a tool returns `Blocked by run policy: ...`, do not retry the same off-policy action.
- When blocked on a card reward, prefer `rewards_skip_card()`.
- When blocked on a shop card purchase, consider relics, potions, card removal, or saving gold instead.
- When blocked on an upgrade or removal target, re-read the current state and choose a policy-approved target.
- Do not override the policy just because a card looks generically strong.

## Gameplay Loop
- Refresh state often. Re-check after each action that can change indices or screen context.
- In combat, prefer `get_fast_game_state()` and only pull full JSON when precise card text or enemy detail is necessary.
- On reward, shop, rest, and card-selection screens, inspect the available choices and prefer entries marked by policy metadata such as `policy_tag` and `policy_reason`.
- If a run policy is active, deck-building decisions must serve that build first and generic value second.
- Before each non-trivial deck-building decision, briefly state why the chosen option fits the run policy.

## Combat Priorities
- Read the current battle state, enemy intents, energy, hand, and likely lethal lines.
- Sequence turns to maximize the active build's win condition, not generic card value.
- Use potions before cards when the potion grants a buff that improves the turn.
- Re-check state after every important play because card indices shift.
- If the current run policy describes a specific combo or engine, prioritize finding and enabling that engine.
- Before committing to a combat line, briefly explain the intended turn plan in visible text.

## Screen Guidance
- Map: choose routes that support the active build, including upgrades, removals, and safe elite timings.
- Rewards: claim gold and relics as appropriate, but only take cards that fit policy.
- Rest Sites: prefer upgrades that match policy priorities; rest only when survival requires it.
- Shop: prefer policy-approved cards, relics, and removal. Avoid off-policy card purchases.
- Events: evaluate outcomes through the lens of the active build and current survival needs.

## Tool Usage Notes
- Prefer `get_fast_game_state()` for speed and lower token use.
- Use `get_game_state(format="markdown")` for quick human-readable overviews.
- Use `get_game_state(format="json")` when you need exact structure or full details.
- Use `get_contextual_advice()` sparingly when the next step is unclear.
- Use knowledge tools only when they materially help a current decision.

## Important Rules
- Always re-check state after playing cards because hand indices shift.
- Always provide `target` for single-target cards and potions that require one.
- Claim rewards from right to left when index shifting matters.
- If the active build is not yet fully online, preserve long-term build integrity instead of stuffing the deck with filler.

## Learning
- After boss fights, briefly reflect on what improved or hurt the active build.
- If you discover a repeatable insight that clearly fits this project, update the relevant local docs only if asked.
