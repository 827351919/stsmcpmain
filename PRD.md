# STS2MCP 产品需求文档 (PRD)

> Slay The Spire 2 MCP Server - AI 游戏代理桥接系统
>
> 版本: 0.3.0 | 最后更新: 2026-03-25

---

## 1. 产品概述

### 1.1 产品定位

STS2MCP 是一个**Slay The Spire 2（杀戮尖塔2）**的游戏 Mod + MCP 服务器桥接系统，旨在让 AI 代理（如 Claude）能够：

1. **读取游戏状态** - 实时获取游戏中的所有关键信息
2. **执行游戏操作** - 通过 API 控制游戏，实现自动化游戏
3. **智能决策辅助** - 基于内置知识库提供策略建议

### 1.2 核心价值

| 价值点 | 描述 |
|--------|------|
| **自动化游戏** | AI 可以自主完成从战斗到地图导航的完整游戏流程 |
| **智能分析** | 基于 577 张卡牌、63 种药水、24 种遗物的完整知识库 |
| **多人支持** | 支持多人联机模式的协调与投票机制 |
| **实时交互** | HTTP API 提供毫秒级响应的游戏状态获取 |

### 1.3 技术架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude / AI Agent                        │
│                   (Claude Desktop / Claude Code)                │
└───────────────────────┬─────────────────────────────────────────┘
                        │ MCP Protocol (stdio)
┌───────────────────────▼─────────────────────────────────────────┐
│                      MCP Server (Python)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │  HTTP Client │  │ KnowledgeBase │  │ Contextual Advisor  │    │
│  │   (httpx)   │  │  (JSON+MD)   │  │   (Rule-based)      │    │
│  └──────┬──────┘  └──────────────┘  └─────────────────────┘    │
└─────────┼───────────────────────────────────────────────────────┘
          │ HTTP/JSON
┌─────────▼───────────────────────────────────────────────────────┐
│                      STS2_MCP Mod (C#/.NET 9)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │ HTTP Server │  │ StateBuilder │  │   ActionExecutor    │    │
│  │ (15526)     │  │ (GameState)  │  │  (UI Automation)    │    │
│  └─────────────┘  └──────────────┘  └─────────────────────┘    │
└───────────────────────┬─────────────────────────────────────────┘
                        │ Godot Engine
┌───────────────────────▼─────────────────────────────────────────┐
│                     Slay The Spire 2 Game                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 系统架构详解

### 2.1 游戏端 Mod (C#/.NET 9)

#### 2.1.1 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **主入口** | `McpMod.cs` | Mod 初始化、HTTP 服务器启动、请求路由 |
| **状态构建** | `McpMod.StateBuilder.cs` | 从游戏内存构建标准化状态对象 |
| **动作执行** | `McpMod.Actions.cs` | 将 API 调用转换为游戏 UI 操作 |
| **多人状态** | `McpMod.MultiplayerState.cs` | 多人游戏状态同步 |
| **多人动作** | `McpMod.MultiplayerActions.cs` | 多人投票和同步机制 |
| **辅助工具** | `McpMod.Helpers.cs` | 反射、节点查找、安全取值等工具 |
| **格式化** | `McpMod.Formatting.cs` | JSON/Markdown 输出格式化 |

#### 2.1.2 HTTP API 设计

```
Base URL: http://localhost:15526

Endpoints:
├── GET  /                      → 健康检查
├── GET  /api/v1/singleplayer   → 获取单人游戏状态
├── POST /api/v1/singleplayer   → 执行单人游戏操作
├── GET  /api/v1/multiplayer    → 获取多人游戏状态
└── POST /api/v1/multiplayer    → 执行多人游戏操作
```

#### 2.1.3 状态类型系统

```csharp
// 游戏状态类型枚举 (state_type)
public enum GameStateType
{
    menu,              // 主菜单
    monster,           // 普通战斗
    elite,             // 精英战斗
    boss,              // Boss 战斗
    hand_select,       // 战斗中手牌选择
    combat_rewards,    // 战斗奖励
    card_reward,       // 卡牌奖励选择
    map,               // 地图导航
    rest_site,         // 营地休息
    shop,              // 商店
    event,             // 事件/上古者
    card_select,       // 卡牌选择（转换/升级/移除）
    relic_select,      // 遗物选择
    treasure,          // 宝藏房间
    overlay,           // 未处理的覆盖层
    unknown            // 未知状态
}
```

#### 2.1.4 主线程队列机制

由于 Godot 引擎要求 UI 操作必须在主线程执行，Mod 实现了**生产者-消费者模式**：

```csharp
// HTTP 线程（生产者）
_mainThreadQueue.Enqueue(() => {
    // 游戏操作代码
    button.ForceClick();
});

// 主线程（消费者）- 每帧处理
void ProcessMainThreadQueue() {
    while (_mainThreadQueue.TryDequeue(out var action)) {
        action();
    }
}
```

### 2.2 MCP 服务器 (Python 3.11+)

#### 2.2.1 架构设计

```python
# FastMCP 框架架构
mcp = FastMCP("sts2")

# 工具分类：
# 1. 状态获取工具
@mcp.tool()
async def get_game_state(format: str = "markdown") -> str:
    """获取当前游戏状态"""

# 2. 知识查询工具
@mcp.tool()
async def lookup_card(card_name: str) -> str:
    """查询卡牌信息"""

# 3. 策略建议工具
@mcp.tool()
async def get_contextual_advice() -> str:
    """基于当前状态的策略建议"""

# 4. 游戏操作工具
@mcp.tool()
async def combat_play_card(card_index: int, target: str | None = None) -> str:
    """战斗中出牌"""
```

#### 2.2.2 知识库系统

| 数据文件 | 内容 | 用途 |
|----------|------|------|
| `cards.json` | 577 张卡牌数据 | 卡牌查询、战斗建议 |
| `relics.json` | 24 种遗物数据 | 遗物选择建议 |
| `enemies.json` | 敌人数据 | 威胁评估 |
| `potions.json` | 63 种药水数据 | 药水使用建议 |
| `events.json` | 事件数据 | 事件决策 |
| `builds.json` | 推荐构建 | 卡组构建指导 |
| `game_mechanics.json` | 游戏机制 | 规则查询 |
| `general_strategy.md` | 通用策略 | 高级指导 |

#### 2.2.3 智能建议引擎

```python
# 上下文感知建议生成流程
def _contextual_advice_from_state(state: dict) -> str:
    # 1. 解析状态类型
    state_type = state.get("state_type")

    # 2. 根据状态类型生成特定建议
    match state_type:
        case "monster" | "elite" | "boss":
            return _generate_combat_advice(state)
        case "map":
            return _generate_map_advice(state)
        case "card_reward":
            return _generate_card_reward_advice(state)
        # ... 其他状态

def _generate_combat_advice(state):
    # 分析威胁
    attacking_enemies = _detect_attacking_enemies(state)

    # 分析手牌
    playable_cards = _get_playable_cards(state)

    # 遗物协同
    relic_synergies = _analyze_relic_synergies(state)

    # 知识库查询
    card_notes = _combat_knowledge_notes(hand, playable, enemies)

    return formatted_advice
```

---

## 3. 功能规格

### 3.1 状态获取功能

#### 3.1.1 战斗状态 (Battle State)

```json
{
  "state_type": "monster",
  "battle": {
    "round": 3,
    "turn": "player",
    "is_play_phase": true,
    "player": {
      "character": "Ironclad",
      "hp": 65,
      "max_hp": 80,
      "block": 12,
      "energy": 3,
      "max_energy": 3,
      "stars": null,
      "hand": [
        {
          "index": 0,
          "id": "strike",
          "name": "Strike",
          "type": "Attack",
          "cost": "1",
          "star_cost": null,
          "description": "Deal 6 damage.",
          "target_type": "AnyEnemy",
          "can_play": true,
          "is_upgraded": false,
          "keywords": [...]
        }
      ],
      "draw_pile_count": 15,
      "discard_pile_count": 8,
      "exhaust_pile_count": 2,
      "draw_pile": [...],
      "discard_pile": [...],
      "exhaust_pile": [...],
      "orbs": [...],
      "orb_slots": 3,
      "orb_empty_slots": 1,
      "gold": 145,
      "status": [...],
      "relics": [...],
      "potions": [...]
    },
    "enemies": [
      {
        "entity_id": "jaw_worm_0",
        "combat_id": 1001,
        "name": "Jaw Worm",
        "hp": 42,
        "max_hp": 45,
        "block": 0,
        "status": [...],
        "intents": [
          {
            "type": "Attack",
            "label": "11",
            "title": "Chomp",
            "description": "Deal 11 damage."
          }
        ]
      }
    ]
  },
  "run": {
    "act": 1,
    "floor": 12,
    "ascension": 0
  }
}
```

#### 3.1.2 地图状态 (Map State)

```json
{
  "state_type": "map",
  "map": {
    "player": {
      "character": "Ironclad",
      "hp": 65,
      "max_hp": 80,
      "gold": 145,
      "potion_slots": 3,
      "open_potion_slots": 1
    },
    "current_position": {"col": 8, "row": 2, "type": "Monster"},
    "visited": [...],
    "next_options": [
      {
        "index": 0,
        "col": 9,
        "row": 1,
        "type": "Elite",
        "leads_to": [...]
      },
      {
        "index": 1,
        "col": 9,
        "row": 2,
        "type": "RestSite",
        "leads_to": [...]
      }
    ],
    "nodes": [...],
    "boss": {"col": 15, "row": 1}
  }
}
```

#### 3.1.3 事件状态 (Event State)

```json
{
  "state_type": "event",
  "event": {
    "event_id": "golden_idol",
    "event_name": "Golden Idol",
    "is_ancient": false,
    "in_dialogue": false,
    "body": "You find a golden idol...",
    "player": {...},
    "options": [
      {
        "index": 0,
        "title": "Take the Idol",
        "description": "Gain Golden Idol. Trigger a trap.",
        "is_locked": false,
        "is_proceed": false,
        "was_chosen": false,
        "keywords": [...]
      }
    ]
  }
}
```

### 3.2 动作执行功能

#### 3.2.1 战斗动作

| 动作 | 参数 | 说明 |
|------|------|------|
| `play_card` | `card_index`, `target?` | 打出指定手牌 |
| `use_potion` | `slot`, `target?` | 使用指定位置药水 |
| `end_turn` | - | 结束回合 |
| `combat_select_card` | `card_index` | 战斗中选择手牌（消耗/弃牌） |
| `combat_confirm_selection` | - | 确认战斗中的选择 |

#### 3.2.2 非战斗动作

| 动作 | 适用场景 | 说明 |
|------|----------|------|
| `choose_map_node` | 地图 | 选择下一个节点 |
| `choose_event_option` | 事件 | 选择事件选项 |
| `advance_dialogue` | 上古者事件 | 推进对话 |
| `choose_rest_option` | 营地 | 选择休息/锻造等 |
| `shop_purchase` | 商店 | 购买物品 |
| `claim_reward` | 奖励 | 领取奖励 |
| `select_card_reward` | 卡牌奖励 | 选择卡牌 |
| `skip_card_reward` | 卡牌奖励 | 跳过奖励 |
| `proceed` | 多个场景 | 前往地图 |

#### 3.2.3 卡牌选择动作

| 动作 | 说明 |
|------|------|
| `select_card` | 选择/切换卡牌（转换/升级/移除） |
| `confirm_selection` | 确认选择 |
| `cancel_selection` | 取消/跳过选择 |

### 3.3 知识库查询功能

#### 3.3.1 查询工具列表

| 工具 | 输入 | 输出 |
|------|------|------|
| `lookup_card` | 卡牌名称/ID | 卡牌详情（费用、类型、描述） |
| `lookup_enemy` | 敌人名称 | 敌人信息和已知行动 |
| `lookup_relic` | 遗物名称 | 遗物效果和触发条件 |
| `lookup_potion` | 药水名称 | 药水效果和使用时机 |
| `lookup_power` | 状态名称 | 状态效果和堆叠规则 |
| `lookup_event` | 事件名称 | 事件描述和选项 |
| `lookup_builds` | 角色名称 | 推荐构建策略 |
| `lookup_character` | 角色名称 | 角色特点和玩法风格 |
| `lookup_mechanic` | 机制关键词 | 游戏规则说明 |
| `lookup_enchantment` | 附魔名称 | 附魔效果 |

#### 3.3.2 智能建议工具

```python
# 上下文感知建议
get_contextual_advice() → 基于当前游戏状态生成:
- 当前状态分析 (HP比例、能量、威胁)
- 角色构建参考
- 具体场景建议
  - 战斗: 威胁评估、出牌建议、遗物协同
  - 地图: 路径推荐
  - 奖励: 优先级建议
  - 商店: 购买建议
  - 事件: 风险/收益分析
```

---

## 4. 多人联机支持

### 4.1 多人状态扩展

```json
{
  "game_mode": "multiplayer",
  "net_type": "SteamMultiplayer",
  "player_count": 2,
  "local_player_slot": 0,
  "players": [
    {
      "character": "Ironclad",
      "is_local": true,
      "hp": 65,
      "max_hp": 80,
      "gold": 145,
      "is_alive": true
    },
    {
      "character": "Silent",
      "is_local": false,
      "hp": 52,
      "max_hp": 70,
      "gold": 120,
      "is_alive": true
    }
  ],
  "battle": {
    "all_players_ready": false,
    "players": [
      {
        "character": "Ironclad",
        "is_local": true,
        "is_alive": true,
        "is_ready_to_end_turn": false,
        // 完整状态（本地玩家）
        "hp": 65,
        "block": 12,
        "energy": 3,
        "hand": [...]
      },
      {
        "character": "Silent",
        "is_local": false,
        "is_alive": true,
        "is_ready_to_end_turn": true,
        // 摘要状态（其他玩家）
        "hp": 52,
        "block": 8,
        "energy": 3
      }
    ]
  }
}
```

### 4.2 投票机制

| 场景 | 机制 | API |
|------|------|-----|
| **回合结束** | 所有玩家提交后才结束 | `mp_combat_end_turn()` / `mp_combat_undo_end_turn()` |
| **地图选择** | 投票决定目的地 | `mp_map_vote()` |
| **共享事件** | 投票选择选项 | `mp_event_choose_option()` |
| **宝藏竞拍** | 竞拍遗物 | `mp_treasure_claim_relic()` |

### 4.3 多人专属字段

```json
{
  "map": {
    "votes": [
      {
        "player": "Ironclad",
        "is_local": true,
        "voted": true,
        "vote_col": 9,
        "vote_row": 1
      },
      {
        "player": "Silent",
        "is_local": false,
        "voted": false,
        "vote_col": null,
        "vote_row": null
      }
    ],
    "all_voted": false
  },
  "treasure": {
    "is_bidding_phase": true,
    "bids": [...],
    "all_bid": false
  }
}
```

---

## 5. 数据模型

### 5.1 卡牌数据模型

```typescript
interface Card {
  id: string;              // 唯一标识，如 "strike"
  nameEn: string;          // 英文名称
  nameZh: string;          // 中文名称
  slug: string;            // URL 友好名称
  characterId: number;     // 所属角色 (1-5)
  cardType: string;        // Attack/Skill/Power/Curse/Status
  rarity: string;          // Basic/Common/Uncommon/Rare
  energyCost: number;      // 能量消耗
  descriptionEn: string;   // 英文描述
  descriptionZh: string;   // 中文描述
}
```

### 5.2 敌人数据模型

```typescript
interface Enemy {
  id: string;
  nameEn: string;
  nameZh: string;
  slug: string;
  moves: EnemyMove[];      // 已知行动列表
}

interface EnemyMove {
  id: string;
  titleEn: string;
  titleZh: string;
}
```

### 5.3 遗物数据模型

```typescript
interface Relic {
  id: string;
  nameEn: string;
  nameZh: string;
  rarity: string;          // Common/Uncommon/Rare/Boss
  characterId: number | null;  // null 表示通用
  triggerTimingEn: string; // 触发时机
  effectSummaryEn: string; // 效果摘要
  conditionSummaryEn: string; // 条件摘要
}
```

---

## 6. 使用流程

### 6.1 单人模式典型流程

```
1. 获取游戏状态
   GET /api/v1/singleplayer?format=json
   → 返回 state_type: "monster" + battle 数据

2. 分析战斗情况
   - 查看 player.hand 中的可用卡牌
   - 查看 enemies[0].intents 了解敌人意图
   - 评估威胁和出牌策略

3. 执行游戏操作
   POST /api/v1/singleplayer
   { "action": "play_card", "card_index": 0, "target": "jaw_worm_0" }

4. 重复直到战斗结束
   → state_type 变为 "combat_rewards"

5. 领取奖励
   POST { "action": "claim_reward", "index": 0 }

6. 选择卡牌奖励
   → state_type 变为 "card_reward"
   POST { "action": "select_card_reward", "card_index": 1 }

7. 前往地图
   POST { "action": "proceed" }
   → state_type 变为 "map"

8. 选择路径
   POST { "action": "choose_map_node", "index": 0 }
   → 进入下一个房间
```

### 6.2 MCP 工具调用流程

```python
# 推荐决策流程
async def play_turn():
    # 1. 获取状态
    state = await get_game_state(format="json")

    # 2. 获取智能建议
    advice = await get_contextual_advice()
    # advice 包含:
    # - 威胁分析
    # - 出牌建议
    # - 遗物协同提示
    # - 相关知识引用

    # 3. 如需详细信息，查询知识库
    card_info = await lookup_card("Demon Form")
    enemy_info = await lookup_enemy("Jaw Worm")

    # 4. 执行决策
    await combat_play_card(card_index=0, target="jaw_worm_0")
    await combat_end_turn()
```

### 6.3 多人模式流程

```python
# 多人战斗回合
async def multiplayer_turn():
    # 1. 获取多人状态
    state = await mp_get_game_state(format="json")

    # 2. 检查其他玩家是否已提交
    if state["battle"]["all_players_ready"]:
        return "Turn already ending"

    # 3. 执行本地玩家操作
    await mp_combat_play_card(card_index=0)

    # 4. 提交回合结束投票
    await mp_combat_end_turn()

    # 5. 如需撤销
    # await mp_combat_undo_end_turn()
```

---

## 7. 错误处理

### 7.1 HTTP 状态码

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 200 | 成功 | 请求成功完成 |
| 400 | 请求错误 | 缺少参数、无效 JSON |
| 404 | 未找到 | 端点不存在 |
| 405 | 方法不允许 | 使用了错误的 HTTP 方法 |
| 409 | 冲突 | 单/多人模式不匹配 |
| 500 | 服务器错误 | 游戏内部错误 |

### 7.2 错误响应格式

```json
{
  "status": "error",
  "error": "Card 'Strike' cannot be played: Not enough energy (need 1, have 0)"
}
```

### 7.3 常见错误场景

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| "Not in combat" | 在非战斗状态调用战斗操作 | 检查 state_type |
| "Not in play phase" | 在敌人回合尝试操作 | 等待玩家回合 |
| "card_index out of range" | 手牌索引变化 | 重新获取状态 |
| "Multiplayer run is active" | 在多人游戏使用单人端点 | 使用 /api/v1/multiplayer |
| "Cannot connect to STS2_MCP mod" | 游戏未运行或 Mod 未启用 | 启动游戏并启用 Mod |

---

## 8. 开发与扩展

### 8.1 构建要求

| 组件 | 要求 |
|------|------|
| **游戏端** | .NET 9 SDK |
| **MCP 服务器** | Python 3.11+, uv |
| **游戏版本** | Slay the Spire 2 v0.99.1+ |

### 8.2 安装步骤

```powershell
# 1. 构建 Mod
.\build.ps1 -GameDir "D:\SteamLibrary\steamapps\common\Slay the Spire 2"

# 2. 复制到游戏目录
cp out/STS2_MCP/STS2_MCP.dll <game>/mods/
cp mod_manifest.json <game>/mods/STS2_MCP.json

# 3. 启动游戏并启用 Mod

# 4. 配置 Claude Code
echo '{"mcpServers":{"sts2":{"command":"uv","args":["run","--directory","/path/to/STS2MCP/mcp","python","server.py"]}}}' > .mcp.json
```

### 8.3 扩展指南

#### 添加新动作

```csharp
// 1. 在 McpMod.Actions.cs 中添加执行逻辑
private static Dictionary<string, object?> ExecuteNewAction(Dictionary<string, JsonElement> data)
{
    // 实现动作逻辑
    return new Dictionary<string, object?> {
        ["status"] = "ok",
        ["message"] = "Action completed"
    };
}

// 2. 在 ExecuteAction switch 中添加路由
case "new_action" => ExecuteNewAction(data),

// 3. 在 Python MCP 服务器中添加工具
@mcp.tool()
async def new_action(param: str) -> str:
    """描述新动作"""
    return await _post({"action": "new_action", "param": param})
```

#### 添加新状态类型

```csharp
// 1. 在 StateBuilder 中检测新状态
if (currentRoom is NewRoomType newRoom)
{
    result["state_type"] = "new_state";
    result["new_state"] = BuildNewState(newRoom, runState);
}

// 2. 实现状态构建方法
private static Dictionary<string, object?> BuildNewState(NewRoomType room, RunState runState)
{
    // 构建状态对象
}
```

---

## 9. 安全与限制

### 9.1 安全考虑

| 项目 | 说明 |
|------|------|
| **本地-only** | HTTP 服务器只监听 localhost，不接受外部连接 |
| **无认证** | 设计上不需要认证，仅本地访问 |
| **游戏状态只读** | 不会修改游戏存档或核心数据 |
| **UI 自动化** | 所有操作通过模拟 UI 点击完成，与玩家操作等效 |

### 9.2 使用限制

- 仅适用于 Slay the Spire 2 v0.99.1+
- 需要游戏启用 Mod 支持
- 多人模式为 Beta 状态，可能存在同步问题
- 某些复杂 UI 场景可能需要手动干预

### 9.3 风险提示

> [!WARNING]
> 此 Mod 允许外部程序通过本地 API 读取和控制游戏。请谨慎使用，特别是在进行您在乎的游戏存档时。

> [!CAUTION]
> 多人联机支持处于 Beta 阶段。如果遇到问题，请先禁用 Mod 验证问题是否仍然存在，再向游戏开发者报告。

---

## 10. 附录

### 10.1 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 尖塔 | Spire | 游戏场景，玩家需要攀登的塔 |
| 角色 | Character | 可玩英雄：铁甲战士、沉默猎手、故障机器人、摄政王、缚灵者 |
| 卡牌 | Card | 游戏中的主要战斗单位 |
| 遗物 | Relic | 提供被动效果的物品 |
| 药水 | Potion | 一次性使用的消耗品 |
| 能量 | Energy | 每回合可用的资源，用于打出卡牌 |
| 格挡 | Block | 抵消伤害的保护层 |
| 状态 | Power/Status | 持续效果的 Buff/Debuff |
| 抽牌堆 | Draw Pile | 未抽到的卡牌 |
| 弃牌堆 | Discard Pile | 已使用或弃掉的卡牌 |
| 消耗 | Exhaust | 将牌移出当前战斗 |

### 10.2 文件清单

```
STS2MCP-main/
├── McpMod.cs                    # Mod 主入口
├── McpMod.Actions.cs            # 单人动作执行
├── McpMod.MultiplayerActions.cs # 多人动作执行
├── McpMod.StateBuilder.cs       # 状态构建
├── McpMod.MultiplayerState.cs   # 多人状态构建
├── McpMod.Helpers.cs            # 辅助工具
├── McpMod.Formatting.cs         # 格式化输出
├── STS2_MCP.csproj              # .NET 项目文件
├── mod_manifest.json            # Mod 清单
├── build.ps1                    # 构建脚本
├── docs/
│   └── raw_api.md               # HTTP API 文档
└── mcp/
    ├── server.py                # MCP 服务器
    ├── knowledge.py             # 知识库查询
    ├── pyproject.toml           # Python 项目配置
    └── knowledge/               # 知识库数据
        ├── cards.json
        ├── relics.json
        ├── enemies.json
        ├── events.json
        ├── builds.json
        ├── characters.json
        ├── potions.json
        ├── powers.json
        ├── enchantments.json
        ├── game_mechanics.json
        └── general_strategy.md
```

### 10.3 参考链接

- [Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk)

---

*文档版本: 1.0 | 生成时间: 2026-03-25*
