import pyxel
import random
import math

W, H = 256, 256
FPS = 30

PLAYER_SPD     = 2.5
BULLET_SPD     = 8.0
EBULLET_SPD    = 3.0
NUM_STARS      = 150


class Game:
    def __init__(self):
        pyxel.init(W, H, title="Side Shooter", fps=FPS)
        self.state = "title"
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── init ───────────────────────────────────────────────────

    def reset(self):
        self.px = 36.0
        self.py = H / 2

        self.bullets        = []   # player bullets  [x, y, vx, vy]
        self.bullet_count   = 1    # number of bullets per shot (max 5)
        self.enemies        = []
        self.enemy_bullets  = []   # enemy/boss bullets
        self.items          = []
        self.boss           = None
        self.boss_alert     = 0

        self.score          = 0
        self.kill_count     = 0
        self.player_hp      = 3
        self.barrier        = 0    # stacked barrier count (max 5)
        self.invincible     = 0    # invincibility frames after a hit
        self.shoot_cd       = 0
        self.shoot_interval = 15   # frames (default 0.5 s)
        self.spawn_timer    = 0

        # Stars: [x, y, scroll_speed]
        self.stars = [
            [random.uniform(0, W), random.uniform(0, H), random.uniform(0.4, 2.0)]
            for _ in range(NUM_STARS)
        ]

    # ── update ─────────────────────────────────────────────────

    def update(self):
        if self.state == "title":
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.state = "play"
            return

        if self.state == "gameover":
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.state = "play"
            return

        # Player movement (left half of screen)
        if pyxel.btn(pyxel.KEY_LEFT):
            self.px = max(10.0, self.px - PLAYER_SPD)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.px = min(W * 0.45, self.px + PLAYER_SPD)
        if pyxel.btn(pyxel.KEY_UP):
            self.py = max(10.0, self.py - PLAYER_SPD)
        if pyxel.btn(pyxel.KEY_DOWN):
            self.py = min(H - 10.0, self.py + PLAYER_SPD)

        # Scroll stars right→left
        for s in self.stars:
            s[0] -= s[2]
            if s[0] < 0:
                s[0] = W
                s[1] = random.uniform(0, H)

        # Auto-fire + manual fire
        if self.shoot_cd > 0:
            self.shoot_cd -= 1
        if self.shoot_cd == 0 or pyxel.btnp(pyxel.KEY_SPACE):
            n = self.bullet_count
            for i in range(n):
                angle = (i - (n - 1) / 2) * 0.18
                self.bullets.append([
                    self.px + 13, self.py,
                    BULLET_SPD * math.cos(angle),
                    BULLET_SPD * math.sin(angle),
                ])
            self.shoot_cd = self.shoot_interval

        # Move player bullets
        for b in self.bullets:
            b[0] += b[2]
            b[1] += b[3]
        self.bullets = [b for b in self.bullets
                        if -10 < b[0] < W + 10 and -10 < b[1] < H + 10]

        # Spawn enemies (pause during boss fight)
        if self.boss is None:
            self.spawn_timer += 1
            interval = max(20, 60 - self.score * 2)
            if self.spawn_timer >= interval:
                self.spawn_timer = 0
                self.enemies.append(self._new_enemy())

        # Move enemies
        for e in self.enemies:
            e['x'] += e['vx']
            e['y'] += e['vy']
            if e['y'] < 12 or e['y'] > H - 12:
                e['vy'] *= -1
            # Enemy fires toward player (every 100 frames)
            e['shoot_t'] += 1
            if e['shoot_t'] >= 100:
                e['shoot_t'] = 0
                self._fire_toward_player(e['x'], e['y'], EBULLET_SPD)
        self.enemies = [e for e in self.enemies if e['x'] > -20]

        # Bullet × enemy
        hit_e, hit_b = set(), set()
        for bi, b in enumerate(self.bullets):
            for ei, e in enumerate(self.enemies):
                if ei in hit_e or bi in hit_b:
                    continue
                if abs(b[0] - e['x']) < e['r'] and abs(b[1] - e['y']) < e['r']:
                    hit_e.add(ei)
                    hit_b.add(bi)
                    self.score += 1
                    self.kill_count += 1
                    # Rate-up item every 10 kills (yellow)
                    if self.kill_count % 10 == 0:
                        self.items.append({'x': e['x'], 'y': e['y'], 'kind': 'rate'})
                    # Spread item every 20 kills (green)
                    if self.kill_count % 20 == 0:
                        self.items.append({'x': e['x'], 'y': e['y'] + 16, 'kind': 'spread'})
                    # Barrier item every 30 kills (blue)
                    if self.kill_count % 30 == 0:
                        self.items.append({'x': e['x'], 'y': e['y'] - 16, 'kind': 'barrier'})
                    # Heal item every 50 kills (pink)
                    if self.kill_count % 50 == 0:
                        self.items.append({'x': e['x'], 'y': e['y'] + 32, 'kind': 'heal'})
                    # Boss every 30 kills
                    if self.kill_count % 30 == 0 and self.boss is None:
                        self.boss = {
                            'x': W + 60.0, 'y': H / 2,
                            'hp': 10, 'shoot_t': 0, 'vy': 1.2,
                        }
                        self.boss_alert = 90
        self.bullets = [b for i, b in enumerate(self.bullets) if i not in hit_b]
        self.enemies = [e for i, e in enumerate(self.enemies) if i not in hit_e]

        # Items: float left, collect on touch
        for item in self.items:
            item['x'] -= 1.2
        collected = [it for it in self.items
                     if abs(self.px - it['x']) < 12 and abs(self.py - it['y']) < 12]
        for it in collected:
            if it['kind'] == 'rate':
                self.shoot_interval = max(3, self.shoot_interval - 3)
            elif it['kind'] == 'spread':
                self.bullet_count = min(5, self.bullet_count + 1)
            elif it['kind'] == 'barrier':
                self.barrier = min(5, self.barrier + 1)
            elif it['kind'] == 'heal':
                self.player_hp = min(3, self.player_hp + 1)
        self.items = [it for it in self.items
                      if it not in collected and it['x'] > -10]

        # Boss movement + shooting
        if self.boss:
            bos = self.boss
            bos['x'] += (W * 0.72 - bos['x']) * 0.03   # slide to right side
            bos['y'] += bos['vy']
            if bos['y'] < 35 or bos['y'] > H - 35:
                bos['vy'] *= -1

            bos['shoot_t'] += 1
            if bos['shoot_t'] >= 45:
                bos['shoot_t'] = 0
                self._fire_toward_player(bos['x'], bos['y'], 4.0)

            # Player bullets × boss
            hit_b2 = set()
            for bi, b in enumerate(self.bullets):
                if bi in hit_b2:
                    continue
                if abs(b[0] - bos['x']) < 28 and abs(b[1] - bos['y']) < 28:
                    hit_b2.add(bi)
                    bos['hp'] -= 1
                    if bos['hp'] <= 0:
                        self.score += 10
                        self.boss = None
                        break
            self.bullets = [b for i, b in enumerate(self.bullets) if i not in hit_b2]

        # Move enemy bullets; check player hit
        if self.invincible > 0:
            self.invincible -= 1
        for eb in self.enemy_bullets:
            eb['x'] += eb['vx']
            eb['y'] += eb['vy']
        if self.invincible == 0:
            for eb in self.enemy_bullets:
                if abs(self.px - eb['x']) < 7 and abs(self.py - eb['y']) < 7:
                    if self._take_hit():
                        return
                    break
        self.enemy_bullets = [eb for eb in self.enemy_bullets
                               if 0 < eb['x'] < W and 0 < eb['y'] < H]

        # Enemy body × player
        if self.invincible == 0:
            for e in self.enemies:
                if abs(self.px - e['x']) < e['r'] + 5 and abs(self.py - e['y']) < e['r'] + 5:
                    if self._take_hit():
                        return
                    break

        # Boss body × player
        if self.boss and self.invincible == 0:
            if abs(self.px - self.boss['x']) < 32 and abs(self.py - self.boss['y']) < 32:
                if self._take_hit():
                    return

        if self.boss_alert > 0:
            self.boss_alert -= 1

    def _take_hit(self):
        """Apply one hit. Barrier absorbs it if available. Returns True if game over."""
        if self.barrier > 0:
            self.barrier -= 1
        else:
            self.player_hp -= 1
        self.invincible = 90
        if self.player_hp <= 0:
            self.state = "gameover"
            return True
        return False

    def _new_enemy(self):
        return {
            'x':       W + 20.0,
            'y':       random.uniform(20, H - 20),
            'vx':      -(1.5 + random.uniform(0, 1.5)),
            'vy':      random.uniform(-0.6, 0.6),
            'r':       10.0,
            'shape':   random.randint(0, 1),
            'shoot_t': random.randint(0, 80),
        }

    def _fire_toward_player(self, fx, fy, spd):
        dx = self.px - fx
        dy = self.py - fy
        dist = math.sqrt(dx * dx + dy * dy) or 1
        self.enemy_bullets.append({
            'x': fx, 'y': fy,
            'vx': dx / dist * spd,
            'vy': dy / dist * spd,
        })

    # ── draw ───────────────────────────────────────────────────

    def draw(self):
        pyxel.cls(0)

        # Stars
        for s in self.stars:
            c = 7 if s[2] > 1.5 else 6 if s[2] > 0.9 else 5
            pyxel.pset(int(s[0]), int(s[1]), c)

        if self.state == "title":
            pyxel.text(W//2 - 36, H//2 - 30, "SIDE SHOOTER",       11)
            pyxel.text(W//2 - 48, H//2 -  5, "ARROW KEYS : MOVE",   7)
            pyxel.text(W//2 - 36, H//2 +  5, "SPACE : FIRE",        7)
            pyxel.text(W//2 - 52, H//2 + 25, "PRESS SPACE TO START", 6)
            return

        if self.state == "gameover":
            pyxel.text(W//2 - 28, H//2 - 10, "GAME OVER",            8)
            pyxel.text(W//2 - 34, H//2 +  5, f"SCORE: {self.score}", 7)
            pyxel.text(W//2 - 45, H//2 + 20, "SPACE TO RESTART",     6)
            return

        # Player bullets
        for b in self.bullets:
            bx, by = int(b[0]), int(b[1])
            pyxel.pset(bx,     by, 10)
            pyxel.pset(bx - 1, by, 10)
            pyxel.pset(bx - 2, by, 10)

        # Enemy bullets (5×5 cross)
        for eb in self.enemy_bullets:
            bx, by = int(eb['x']), int(eb['y'])
            pyxel.line(bx - 2, by,     bx + 2, by,     8)
            pyxel.line(bx,     by - 2, bx,     by + 2, 8)

        # Items
        for item in self.items:
            self._draw_item(item)

        # Enemies
        for e in self.enemies:
            self._draw_enemy(e)

        # Boss
        if self.boss:
            self._draw_boss()

        # Player (blink during invincibility)
        if self.invincible == 0 or self.invincible % 6 < 4:
            self._draw_player()

        # HUD
        pyxel.text(4, 4, f"SCORE:{self.score:04d}", 7)
        pyxel.text(4, 12, f"RATE :{self.shoot_interval / 30:.1f}s", 10)
        pyxel.text(4, 20, "HP:" + "* " * self.player_hp, 8)
        pyxel.text(4, 28, f"SHOT:{self.bullet_count}", 11)
        pyxel.text(4, 36, "BAR:" + "# " * self.barrier, 12)

        # Boss HP bar
        if self.boss:
            bw = 120
            bx = W // 2 - bw // 2
            by = H - 18
            pyxel.text(bx, by - 8, "BOSS", 14)
            pyxel.rectb(bx, by, bw, 6, 7)
            filled = int(bw * self.boss['hp'] / 10)
            if filled > 0:
                pyxel.rect(bx, by, filled, 6, 8)

        # Boss warning (blink)
        if self.boss_alert > 0 and self.boss_alert % 10 < 7:
            pyxel.text(W // 2 - 28, H // 2 - 4, "!! BOSS !!", 14)

    def _draw_player(self):
        x, y = int(self.px), int(self.py)
        c = 11  # cyan
        # Arrow-shaped ship pointing right
        pyxel.line(x + 12, y,      x,      y - 8,  c)
        pyxel.line(x + 12, y,      x,      y + 8,  c)
        pyxel.line(x,       y - 8, x - 5,  y - 3,  c)
        pyxel.line(x,       y + 8, x - 5,  y + 3,  c)
        pyxel.line(x - 5,  y - 3, x - 5,  y + 3,  c)
        # Engine nacelles
        pyxel.line(x - 2,  y - 3, x - 9,  y - 3,  c)
        pyxel.line(x - 2,  y + 3, x - 9,  y + 3,  c)
        pyxel.pset(x - 9,  y - 3, 9)
        pyxel.pset(x - 9,  y + 3, 9)

    def _draw_enemy(self, e):
        x, y, r = int(e['x']), int(e['y']), int(e['r'])
        c = 8  # red
        if e['shape'] == 0:
            # Diamond
            pyxel.line(x,     y - r, x + r, y,     c)
            pyxel.line(x + r, y,     x,     y + r, c)
            pyxel.line(x,     y + r, x - r, y,     c)
            pyxel.line(x - r, y,     x,     y - r, c)
            pyxel.line(x - r, y,     x + r, y,     c)
        else:
            # Box with X
            pyxel.rectb(x - r, y - r, r * 2, r * 2, c)
            pyxel.line(x - r, y - r, x + r, y + r, c)
            pyxel.line(x + r, y - r, x - r, y + r, c)

    def _draw_item(self, item):
        x, y = int(item['x']), int(item['y'])
        r = 6
        angle = pyxel.frame_count * 0.1
        if item['kind'] == 'rate':
            c = 10  # yellow: 4-arm cross
            for i in range(4):
                a = angle + i * math.pi / 2
                pyxel.line(x, y, int(x + math.cos(a) * r), int(y + math.sin(a) * r), c)
        elif item['kind'] == 'spread':
            c = 11  # green: 3-arm triangle
            for i in range(3):
                a = angle + i * 2 * math.pi / 3
                pyxel.line(x, y, int(x + math.cos(a) * r), int(y + math.sin(a) * r), c)
            for i in range(3):
                a1 = angle + i * 2 * math.pi / 3
                a2 = angle + (i + 1) * 2 * math.pi / 3
                pyxel.line(int(x + math.cos(a1) * r), int(y + math.sin(a1) * r),
                           int(x + math.cos(a2) * r), int(y + math.sin(a2) * r), c)
        elif item['kind'] == 'barrier':
            c = 12  # blue: rotating hexagon
            for i in range(6):
                a1 = angle + i * math.pi / 3
                a2 = angle + (i + 1) * math.pi / 3
                pyxel.line(int(x + math.cos(a1) * r), int(y + math.sin(a1) * r),
                           int(x + math.cos(a2) * r), int(y + math.sin(a2) * r), c)
        else:  # heal
            c = 14  # pink: plus sign with outer diamond
            pyxel.line(x - r, y, x + r, y, c)
            pyxel.line(x, y - r, x, y + r, c)
            ri = int(r * 0.6)
            pyxel.line(x + ri, y - ri, x + ri, y + ri, c)
            pyxel.line(x - ri, y - ri, x - ri, y + ri, c)
            pyxel.line(x - ri, y - ri, x + ri, y - ri, c)
            pyxel.line(x - ri, y + ri, x + ri, y + ri, c)

    def _draw_boss(self):
        bos = self.boss
        x, y = int(bos['x']), int(bos['y'])
        r = 28
        c = 14  # pink
        # Outer hexagon
        pts = [(int(x + math.cos(i * math.pi / 3) * r),
                int(y + math.sin(i * math.pi / 3) * r)) for i in range(6)]
        for i in range(6):
            pyxel.line(pts[i][0], pts[i][1], pts[(i+1)%6][0], pts[(i+1)%6][1], c)
        # Spokes to center
        for pt in pts:
            pyxel.line(x, y, pt[0], pt[1], c)
        # Inner hexagon (rotated 30°)
        ri = r // 2
        ipts = [(int(x + math.cos(i * math.pi / 3 + math.pi/6) * ri),
                 int(y + math.sin(i * math.pi / 3 + math.pi/6) * ri)) for i in range(6)]
        for i in range(6):
            pyxel.line(ipts[i][0], ipts[i][1], ipts[(i+1)%6][0], ipts[(i+1)%6][1], c)


Game()
