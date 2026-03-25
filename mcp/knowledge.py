from __future__ import annotations


class KnowledgeBase:
    """Minimal fallback knowledge provider.

    The original project references a bundled knowledge module, but some copies
    of the repo do not include that file. This fallback keeps the MCP server
    operational and degrades the knowledge tools gracefully instead of failing
    at import time.
    """

    def get_general_strategy(self, max_chars: int = 6000) -> str:
        text = (
            "Bundled strategy notes are not installed in this copy of the project. "
            "Use get_run_policy(), get_fast_game_state(), and the live game state "
            "as the primary source of decisions."
        )
        return text[:max_chars]

    def lookup_card(self, card_name: str) -> str:
        return f"No bundled card knowledge is installed for '{card_name}'."

    def lookup_enemy(self, enemy_name: str) -> str:
        return f"No bundled enemy knowledge is installed for '{enemy_name}'."

    def lookup_relic(self, relic_name: str) -> str:
        return f"No bundled relic knowledge is installed for '{relic_name}'."

    def lookup_builds(self, character_name: str, max_results: int = 5) -> str:
        return (
            f"No bundled build notes are installed for '{character_name}'. "
            "Rely on the active run policy and current deck state instead."
        )
