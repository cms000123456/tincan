"""Deterministic map generation and decoration.

decorate(mid, rows, m, seed, biome)  -> rows with forests, rocks, bushes,
    flowers and tall-grass patches grown into empty ground, never blocking
    paths, exits, NPCs, chests or making any important spot unreachable.
field(...), dungeon(...), town(...)  -> new maps (rows + metadata) for the
    later chapters.

Tile chars used here (see world.SOLIDS): T tree  V rock  h bush  j stump
f flowers  , tall grass  ~ water  # path  _ cave floor  C cave wall
O cave mouth/stairs  a sand  w snow  . grass
"""
import collections
import random

GROUND = {"grass": ".", "snow": "w", "sand": "a", "cave": "_",
          "marsh": "m", "metal": "z", "ash": "y"}
WALKABLE_DECOR = ",f"


def _noise(w, h, rng, cell):
    gx, gy = w // cell + 2, h // cell + 2
    pts = [[rng.random() for _ in range(gx)] for _ in range(gy)]
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            fx, fy = x / cell, y / cell
            x0, y0 = int(fx), int(fy)
            tx, ty = fx - x0, fy - y0
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            a = pts[y0][x0] + (pts[y0][x0 + 1] - pts[y0][x0]) * tx
            b = pts[y0 + 1][x0] + (pts[y0 + 1][x0 + 1] - pts[y0 + 1][x0]) * tx
            out[y][x] = a + (b - a) * ty
    return out


def _important(m):
    """Cells that must stay walkable/reachable, plus their halo."""
    keep = set()
    for e in m.get("exits", []):
        keep.add((e["x"], e["y"]))
    for n in m.get("npcs", []):
        keep.add((n["x"], n["y"]))
    for c in m.get("chests", []):
        keep.add((c["x"], c["y"]))
    for c in m.get("crystals", []):
        keep.add(tuple(c))
    signs = m.get("signs") or {}
    if isinstance(signs, dict):
        keep.update(signs.keys())
    for e in m.get("entities", []):
        keep.add(tuple(e["pos"]))
    return keep


def _arrivals(mid, all_maps):
    """Spawn points other maps send the player to on this map."""
    out = set()
    for om in all_maps.values():
        for e in om.get("exits", []):
            if e["to"] == mid:
                out.add((e["tx"], e["ty"]))
    return out


def _reach(rows, start, solid):
    h, w = len(rows), len(rows[0])
    seen = {start}
    q = collections.deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and \
                    rows[ny][nx] not in solid:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def decorate(mid, rows, m, seed, biome="grass", all_maps=None,
             solid=None, density=1.0, grass_patches=True):
    """Grow scenery into empty ground. Returns new rows (list of str)."""
    rng = random.Random(seed)
    h, w = len(rows), len(rows[0])
    grid = [list(r) for r in rows]
    ground = GROUND.get(biome, ".")
    base_ok = {ground, "."} if biome != "snow" else {"w"}
    if biome == "mixed":
        base_ok = {".", "w"}
    keep = _important(m) | (_arrivals(mid, all_maps) if all_maps else set())
    # protect a halo around exits/spawns and every path tile
    halo = set()
    for (x, y) in keep:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                halo.add((x + dx, y + dy))
    for y in range(h):
        for x in range(w):
            if grid[y][x] in "#BDO":
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        halo.add((x + dx, y + dy))
    free = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1)
            if grid[y][x] in base_ok and (x, y) not in halo]
    forest = _noise(w, h, rng, 6)
    detail = _noise(w, h, rng, 3)
    placed = []                       # (x, y, old) so we can roll back
    for (x, y) in free:
        n, d = forest[y][x], detail[y][x]
        ch = None
        if n > 0.72 - 0.06 * (density - 1):
            ch = "T"
        elif n > 0.64 and d > 0.6:
            ch = "h" if rng.random() < 0.6 else "j"
        elif grass_patches and n < 0.22 and d > 0.45 and biome != "cave":
            ch = ","
        elif rng.random() < 0.025 * density:
            ch = rng.choice("Vhjff" if grid[y][x] == "." else "Vhj")
        elif rng.random() < 0.03 * density and grid[y][x] == ".":
            ch = "f"
        if ch:
            placed.append((x, y, grid[y][x]))
            grid[y][x] = ch
    # connectivity: every kept walkable cell must be reachable from one
    solid = solid or set()
    targets = [p for p in keep if 0 <= p[0] < w and 0 <= p[1] < h and
               grid[p[1]][p[0]] not in solid]
    if targets:
        for _ in range(len(placed) + 1):
            reach = _reach(["".join(r) for r in grid], targets[0], solid)
            lost = [p for p in targets if p not in reach]
            if not lost:
                break
            # remove the placed obstacle nearest to a lost target
            lx, ly = lost[0]
            blockers = [p for p in placed if grid[p[1]][p[0]] in solid]
            if not blockers:
                break
            bx, by, old = min(blockers, key=lambda p: abs(p[0] - lx) +
                              abs(p[1] - ly))
            grid[by][bx] = old
            placed.remove((bx, by, old))
    return ["".join(r) for r in grid]


# ---------------------------------------------------------------------------
# New maps
# ---------------------------------------------------------------------------
def _carve_path(grid, a, b, rng, ch="#"):
    """Wobbly L-ish path from a to b."""
    (x, y), (tx, ty) = a, b
    while (x, y) != (tx, ty):
        if rng.random() < 0.5 and x != tx:
            x += 1 if tx > x else -1
        elif y != ty:
            y += 1 if ty > y else -1
        else:
            x += 1 if tx > x else -1
        if grid[y][x] not in "DO":
            grid[y][x] = ch


def field(w, h, seed, biome, entries, water=0.0):
    """Outdoor area. entries: list of (x, y) edge/door cells to link with
    paths. Returns rows (border of trees, paths, optional lakes)."""
    rng = random.Random(seed)
    g = GROUND[biome]
    grid = [[g] * w for _ in range(h)]
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = "T"
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = "T"
    if water:
        nz = _noise(w, h, rng, 7)
        for y in range(2, h - 2):
            for x in range(2, w - 2):
                if nz[y][x] < water:
                    grid[y][x] = "~"
    hub = (w // 2, h // 2)
    for e in entries:
        _carve_path(grid, e, hub, rng)
    for (x, y) in entries:
        grid[y][x] = "#"
    # bridges where paths cross water
    for y in range(h):
        for x in range(w):
            if grid[y][x] == "#" and water:
                pass
    return ["".join(r) for r in grid]


def dungeon(w, h, seed, entry, exit_, fill=0.44, steps=4):
    """Cellular-automata cave: C walls, _ floor; entry/exit cells are
    guaranteed connected. Returns rows."""
    rng = random.Random(seed)
    grid = [["C" if (x in (0, w - 1) or y in (0, h - 1) or
                     rng.random() < fill) else "_" for x in range(w)]
            for y in range(h)]
    for _ in range(steps):
        new = [row[:] for row in grid]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                walls = sum(grid[y + dy][x + dx] == "C"
                            for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                new[y][x] = "C" if walls >= 5 else "_"
        grid = new
    # open rooms around entry/exit and a winding tunnel between them
    for (cx, cy) in (entry, exit_):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                x, y = cx + dx, cy + dy
                if 0 < x < w - 1 and 0 < y < h - 1:
                    grid[y][x] = "_"
    _carve_path(grid, entry, exit_, rng, "_")
    # connect every floor pocket to the main cave
    rows = ["".join(r) for r in grid]
    main = _reach(rows, entry, {"C"})
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if grid[y][x] == "_" and (x, y) not in main:
                _carve_path(grid, (x, y), entry, rng, "_")
                rows = ["".join(r) for r in grid]
                main = _reach(rows, entry, {"C"})
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = "C"
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = "C"
    return ["".join(r) for r in grid]


def floor_cells(rows, ch="_"):
    return [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r)
            if c == ch]


def pick_far(rows, start, cells, rng, n, min_d=6, solid=("C", "T", "~")):
    """Pick n floor cells spread out and away from start."""
    reach = _reach(rows, start, set(solid))
    cand = [c for c in cells if c in reach and
            abs(c[0] - start[0]) + abs(c[1] - start[1]) >= min_d]
    rng.shuffle(cand)
    out = []
    for c in cand:
        if all(abs(c[0] - o[0]) + abs(c[1] - o[1]) >= 4 for o in out):
            out.append(c)
        if len(out) >= n:
            break
    return out
