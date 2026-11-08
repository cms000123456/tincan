"""Dev tool: renders generated art to /tmp/tcc_art/*.png for visual QA."""
import os
import pygame

import assets

os.makedirs("/tmp/tcc_art", exist_ok=True)
pygame.init()
pygame.display.set_mode((100, 100))
A = assets.load_assets()

# tiles: arrange all known chars on grass background
chars = list(A["tiles"].keys()) + list(A["anim"].keys())
sheet = pygame.Surface((16 * 12, 16 * 4))
tiles = dict(A["tiles"])
for k, v in A["anim"].items():
    if isinstance(v, list):
        tiles[k] = v[0]
tiles["!"] = assets.make_props()["chest_closed"]
tiles["?"] = assets.make_props()["crystal"][0]
tiles["b_"] = assets.make_props()["barrel"]
sheet.blit(tiles["."], (0, 0))
for i, k in enumerate(sorted(tiles.keys())):
    x, y = (i + 1) % 12 * 16, (i + 1) // 12 * 16
    if k == ".":
        continue
    sheet.blit(tiles["."], (x, y))
    t = tiles[k]
    sheet.blit(t, (x, y))
pygame.image.save(sheet, "/tmp/tcc_art/tiles.png")

# characters
CHARS = {
    "kai": dict(H=(255, 120, 60), h=(200, 70, 30), S=(250, 210, 170),
                E=(40, 30, 40), O=(60, 90, 190), o=(40, 62, 140),
                T=(250, 210, 90), B=(60, 50, 60)),
    "nara": dict(H=(250, 230, 120), h=(205, 180, 80), S=(255, 224, 196),
                 E=(40, 30, 40), O=(130, 200, 235), o=(90, 155, 195),
                 T=(255, 255, 255), B=(90, 70, 80)),
    "vela": dict(H=(150, 120, 235), h=(100, 78, 185), S=(250, 210, 170),
                 E=(40, 30, 40), O=(232, 238, 242), o=(180, 188, 196),
                 T=(255, 150, 60), B=(70, 70, 80)),
    "villager": dict(H=(80, 60, 40), h=(56, 42, 28), S=(240, 200, 160),
                     E=(40, 30, 40), O=(120, 170, 90), o=(86, 130, 64),
                     T=(230, 210, 170), B=(70, 56, 40)),
    "elder": dict(H=(220, 220, 220), h=(160, 160, 165), S=(240, 200, 160),
                  E=(40, 30, 40), O=(160, 120, 80), o=(120, 90, 60),
                  T=(240, 240, 240), B=(60, 50, 45)),
}
cs = pygame.Surface((len(CHARS) * 16 * 3 * 6 + 60, 20 * 3 * 3 + 40))
cs.fill((40, 40, 60))
for i, (name, pal) in enumerate(CHARS.items()):
    sheet_c = assets.build_char_sheet(pal)
    for j, (d, fr) in enumerate([("down", "idle"), ("down", "a"), ("down", "b"),
                                 ("left", "idle"), ("left", "a"), ("left", "b"),
                                 ("up", "idle"), ("right", "idle")]):
        img = pygame.transform.scale(sheet_c[(d, fr)], (48, 60))
        cs.blit(img, (i * 288 + j * 50 + 2, 4))
pygame.image.save(cs, "/tmp/tcc_art/chars.png")

# enemies
en = pygame.Surface((900, 200))
enemies = A["enemies"]
en.fill((40, 40, 60))
x = 4
for k, surf in enemies.items():
    scale = 5 if k != "boss" else 4
    img = pygame.transform.scale(surf, (surf.get_width() * scale, surf.get_height() * scale))
    en.blit(img, (x + 2, 20))
    x += img.get_width() + 30
pygame.image.save(en, "/tmp/tcc_art/enemies.png")
print("saved /tmp/tcc_art/")

# tiles big
big = pygame.transform.scale(pygame.image.load("/tmp/tcc_art/tiles.png"), (640, 256))
pygame.image.save(big, "/tmp/tcc_art/tiles_big.png")
