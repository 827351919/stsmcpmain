"""Watch STS2 run state and notify Feishu when a run ends."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


DEFAULT_WEBHOOK_URL = (
    "https://open.feishu.cn/open-apis/bot/v2/hook/"
    "cf0f81f8-cae9-42e2-9cbc-067381d0f04d"
)


@dataclass
class RunSnapshot:
    state_type: str
    act: int | None
    floor: int | None
    ascension: int | None
    character: str
    hp: int | None
    max_hp: int | None
    gold: int | None
    relic_count: int
    potion_count: int
    last_screen: str
    likely_result: str


def _safe_get(mapping: dict[str, Any] | None, *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _extract_player(state: dict[str, Any]) -> dict[str, Any]:
    battle_player = _safe_get(state, "battle", "player")
    if isinstance(battle_player, dict):
        return battle_player
    player = state.get("player")
    return player if isinstance(player, dict) else {}


def _infer_result(state: dict[str, Any], player: dict[str, Any]) -> str:
    hp = player.get("hp")
    if isinstance(hp, int) and hp <= 0:
        return "Likely Defeat"

    state_type = str(state.get("state_type", "unknown"))
    act = _safe_get(state, "run", "act")
    floor = _safe_get(state, "run", "floor")
    if act == 3 and isinstance(floor, int) and floor >= 50:
        return "Likely Victory"
    if state_type == "treasure" and act == 3:
        return "Likely Victory"
    return "Run Ended"


def _snapshot_from_state(state: dict[str, Any]) -> RunSnapshot:
    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    player = _extract_player(state)
    relics = player.get("relics") if isinstance(player.get("relics"), list) else []
    potions = player.get("potions") if isinstance(player.get("potions"), list) else []

    return RunSnapshot(
        state_type=str(state.get("state_type", "unknown")),
        act=run.get("act") if isinstance(run, dict) else None,
        floor=run.get("floor") if isinstance(run, dict) else None,
        ascension=run.get("ascension") if isinstance(run, dict) else None,
        character=str(player.get("character", "Unknown")),
        hp=player.get("hp") if isinstance(player.get("hp"), int) else None,
        max_hp=player.get("max_hp") if isinstance(player.get("max_hp"), int) else None,
        gold=player.get("gold") if isinstance(player.get("gold"), int) else None,
        relic_count=len(relics),
        potion_count=len(potions),
        last_screen=str(state.get("state_type", "unknown")),
        likely_result=_infer_result(state, player),
    )


def _build_feishu_payload(snapshot: RunSnapshot) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "STS2 run finished.",
        f"Result: {snapshot.likely_result}",
        f"Character: {snapshot.character}",
        f"Act / Floor: {snapshot.act or '?'} / {snapshot.floor or '?'}",
        f"Ascension: {snapshot.ascension if snapshot.ascension is not None else '?'}",
        f"HP: {snapshot.hp if snapshot.hp is not None else '?'} / "
        f"{snapshot.max_hp if snapshot.max_hp is not None else '?'}",
        f"Gold: {snapshot.gold if snapshot.gold is not None else '?'}",
        f"Relics: {snapshot.relic_count}",
        f"Potions: {snapshot.potion_count}",
        f"Last screen: {snapshot.last_screen}",
        f"Time: {timestamp}",
    ]
    return {
        "msg_type": "text",
        "content": {
            "text": "\n".join(lines)
        },
    }


async def _fetch_state(base_url: str) -> dict[str, Any] | None:
    url = f"{base_url.rstrip('/')}/api/v1/singleplayer"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params={"format": "json"})
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None


async def _send_feishu(webhook_url: str, snapshot: RunSnapshot) -> None:
    payload = _build_feishu_payload(snapshot)
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()


async def watch_runs(base_url: str, webhook_url: str, poll_interval: float) -> None:
    active_snapshot: RunSnapshot | None = None
    notified_signature: str | None = None

    while True:
        try:
            state = await _fetch_state(base_url)
            if state is None:
                await asyncio.sleep(poll_interval)
                continue

            state_type = str(state.get("state_type", "unknown"))
            if state_type != "menu":
                active_snapshot = _snapshot_from_state(state)
                notified_signature = None
            elif active_snapshot is not None:
                signature = json.dumps(active_snapshot.__dict__, sort_keys=True, ensure_ascii=True)
                if signature != notified_signature:
                    await _send_feishu(webhook_url, active_snapshot)
                    print(
                        f"[notifier] Sent run-end notification for "
                        f"{active_snapshot.character} floor {active_snapshot.floor}"
                    )
                    notified_signature = signature
                active_snapshot = None
        except Exception as exc:
            print(f"[notifier] {type(exc).__name__}: {exc}")

        await asyncio.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Notify Feishu when an STS2 run ends")
    parser.add_argument("--host", default="localhost", help="STS2 MCP mod host")
    parser.add_argument("--port", type=int, default=15526, help="STS2 MCP mod port")
    parser.add_argument(
        "--webhook-url",
        default=DEFAULT_WEBHOOK_URL,
        help="Feishu bot webhook URL",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds",
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    asyncio.run(watch_runs(base_url, args.webhook_url, args.poll_interval))


if __name__ == "__main__":
    main()
