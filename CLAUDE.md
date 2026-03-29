# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
pip install pyxel
python shooter3d.py
```

## Project Overview

A single-file 2D arcade space shooter (`shooter3d.py`) built with [Pyxel](https://github.com/kitao/pyxel) — a retro pixel-art game engine. The game runs at 256×256 pixels, 30 FPS.

## Architecture

All game logic lives in a single `Game` class in `shooter3d.py`. State is managed via a `state` string field: `"title"` → `"play"` → `"gameover"`.

**Core data structures** (plain lists of dicts on `self`):
- `self.enemies` — active enemy ships
- `self.bullets` — player projectiles
- `self.enemy_bullets` — enemy projectiles
- `self.items` — collectible power-ups
- `self.stars` — background parallax starfield (150 entries)
- `self.boss` — single boss dict (or `None`)

**Game loop:** `pyxel.run(self.update, self.draw)` drives two methods:
- `update()` — dispatches to `update_title/play/gameover()` based on state
- `draw()` — dispatches similarly

**Collision detection** uses circle-distance checks (no physics library).

**Difficulty scaling:** Enemy spawn interval shrinks as score increases (calculated in `update_play()`).

**Boss spawning:** Every 30 kills; boss has 10 HP, fires every 45 frames, bounces vertically on the right side.

**Power-up types** (drop on specific kill milestones):
| Item | Color | Effect | Trigger |
|------|-------|--------|---------|
| Rate | Yellow | Faster fire rate (min 3 frames) | every 10 kills |
| Spread | Green | More bullets (max 5) | every 20 kills |
| Barrier | Blue | Shield charges (max 5) | every 30 kills |
| Heal | Pink | Restore HP (max 3) | every 50 kills |

## MCP Integration

`.mcp.json.txt` configures a `pyxel-mcp` stdio server. Rename to `.mcp.json` to activate it with Claude Code for Pyxel-aware tooling.
