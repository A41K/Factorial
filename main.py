import pygame
import random
import sys
import math
from enum import Enum, auto

# ==========================================
# CONFIGURATION
# ==========================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TILE_SIZE = 32
HALF_WIDTH = SCREEN_WIDTH // 2

COLORS = {
    "WHITE": (255, 255, 255),
    "BLACK": (10, 10, 14),
    "GRAY": (50, 50, 50),
    "LIGHT_GRAY": (150, 150, 150),
    "RED": (220, 60, 60),
    "GREEN": (60, 240, 120),
    "BLUE": (80, 120, 255),
    "SKY_BLUE": (135, 206, 235),
    "GOLD": (255, 215, 0),
    "PURPLE": (180, 60, 220),
    "GRASS": (70, 180, 80),
    "WATER": (60, 140, 220),
    "SAND": (230, 210, 160),
    "STONE": (110, 110, 125),
    "DIRT": (100, 70, 40),
    "TREE": (30, 130, 60),
    "WOOD": (140, 90, 50),
    "CONVEYOR": (160, 160, 170),
    "DRILL": (220, 140, 40),
    "COAL": (30, 30, 35),
    "GOLD_ORE": (255, 200, 50),
    "IRON": (180, 140, 140),
    "COPPER": (200, 100, 50),
    "UI_BG": (20, 20, 30),
    "UI_OVERLAY": (0, 0, 0, 230)
}

RECIPES = {
    "plank": {"inputs": {"wood": 1}, "output": 2, "type": "item"},
    "gear": {"inputs": {"iron_ingot": 1}, "output": 2, "type": "item"},
    "wire": {"inputs": {"copper_ingot": 1}, "output": 2, "type": "item"},
    "circuit": {"inputs": {"wire": 2, "iron_ingot": 1}, "output": 1, "type": "item"},
    "processor": {"inputs": {"circuit": 2, "gold_ingot": 1}, "output": 1, "type": "item"},
    "furnace": {"inputs": {"stone": 5}, "output": 1, "type": "building"},
    "drill": {"inputs": {"iron_ingot": 3, "gear": 2}, "output": 1, "type": "building"},
    "conveyor": {"inputs": {"iron_ingot": 1, "gear": 1}, "output": 4, "type": "building"},
    "assembler": {"inputs": {"stone": 10, "circuit": 2}, "output": 1, "type": "building"},
    "totem": {"inputs": {}, "output": 1, "type": "nature"},
}

UNLOCK_DATA = {
    "inventory": {"cost": 25, "name": "Backpack", "desc": "P1 can hold items."},
    "mining": {"cost": 50, "name": "Stone Pick", "desc": "P1 can mine Stone/Ore."},
    "crafting": {"cost": 100, "name": "Workbench", "desc": "P1 can Craft (Press Q)."},
    "smelting": {"cost": 200, "name": "Metallurgy", "desc": "Unlock Furnaces/Coal."},
    "automation": {"cost": 400, "name": "Logistics", "desc": "Unlock Drills & Belts."},
    "advanced": {"cost": 600, "name": "Engineering", "desc": "Assemblers & Gold."},
    "druidry": {"cost": 800, "name": "Nature Totem", "desc": "P2 can build Totems."}
}

class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    UNLOCK_MENU = auto()
    CRAFTING_MENU = auto()
    MAP_VIEW = auto()
    CONTROLS = auto()

class TileType(Enum):
    GRASS = 0
    SAND = 1
    WATER = 2
    STONE = 3
    TREE = 4
    ORE_IRON = 5
    ORE_COPPER = 6
    ORE_COAL = 7
    ORE_GOLD = 8
    ESSENCE = 9

# ==========================================
# UTILS
# ==========================================

def clamp_color(x): 
    return max(0, min(255, int(x)))

def vary_color(col, x, y, amt=15):
    random.seed(x * 1000 + y)
    d = random.randint(-amt, amt)
    return (clamp_color(col[0] + d), clamp_color(col[1] + d), clamp_color(col[2] + d))

# ==========================================
# CORE CLASSES
# ==========================================

class Inventory:
    def __init__(self):
        self.items = {}

    def add(self, item, amount=1):
        self.items[item] = self.items.get(item, 0) + amount

    def has(self, item, amount=1):
        return self.items.get(item, 0) >= amount

    def remove(self, item, amount=1):
        if self.has(item, amount):
            self.items[item] -= amount
            if self.items[item] <= 0:
                del self.items[item]
            return True
        return False
    
    def get_list(self):
        return list(self.items.keys())

class UnlockManager:
    def __init__(self):
        self.points = 0
        self.unlocks = {k: {**v, "unlocked": False} for k, v in UNLOCK_DATA.items()}

    def can_do(self, key):
        return self.unlocks.get(key, {}).get("unlocked", False)

    def purchase(self, key):
        data = self.unlocks.get(key)
        if data and self.points >= data["cost"] and not data["unlocked"]:
            self.points -= data["cost"]
            data["unlocked"] = True
            return True
        return False

class Tile:
    def __init__(self, x, y, t_type):
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.type = t_type
        self.base_color = self._resolve_color(t_type, x, y)
    
    def _resolve_color(self, t, x, y):
        mapping = {
            TileType.GRASS: (COLORS["GRASS"], 10),
            TileType.SAND: (COLORS["SAND"], 10),
            TileType.WATER: (COLORS["WATER"], 5),
            TileType.STONE: (COLORS["STONE"], 10)
        }
        if t in mapping:
            return vary_color(mapping[t][0], x, y, mapping[t][1])
        return COLORS["BLACK"]

class Building:
    def __init__(self, x, y, b_type, facing="DOWN"):
        self.x, self.y = x, y
        self.type = b_type
        self.facing = facing
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.inventory = Inventory()
        self.timer = 0
        self.max_timer = self._get_timer_limit()

    def _get_timer_limit(self):
        limits = {"drill": 100, "furnace": 150, "conveyor": 30, "assembler": 200, "totem": 60}
        return limits.get(self.type, 100)
        
    def update(self, world):
        self.timer += 1
        if self.timer >= self.max_timer:
            self.timer = 0
            self._perform_action(world)

    def _perform_action(self, world):
        if self.type == "drill":
            self._act_drill(world)
        elif self.type == "furnace":
            self._act_furnace()
        elif self.type == "conveyor":
            self._act_conveyor(world)
        elif self.type == "assembler":
            self._act_assembler()
        elif self.type == "totem":
            self._act_totem(world)

    def _act_drill(self, world):
        tile = world.get_tile_type(self.x, self.y)
        res_map = {
            TileType.ORE_IRON: "ore_iron",
            TileType.ORE_COPPER: "ore_copper",
            TileType.ORE_COAL: "coal",
            TileType.ORE_GOLD: "ore_gold",
            TileType.STONE: "stone"
        }
        if tile in res_map:
            self.output_item(world, res_map[tile])

    def _act_furnace(self):
        recipes = [("ore_iron", "iron_ingot"), ("ore_copper", "copper_ingot"), ("ore_gold", "gold_ingot")]
        for ore, ingot in recipes:
            if self.inventory.has(ore):
                self.inventory.remove(ore, 1)
                self.inventory.add(ingot, 1)
                break

    def _act_conveyor(self, world):
        for item, amt in list(self.inventory.items.items()):
            if amt > 0 and self.output_item(world, item):
                self.inventory.remove(item, 1)
                break 

    def _act_assembler(self):
        if self.inventory.has("iron_ingot", 1):
            self.inventory.remove("iron_ingot", 1)
            self.inventory.add("gear", 2)

    def _act_totem(self, world):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                b = world.get_building(self.x + dx, self.y + dy)
                if b and b.type != "totem":
                    b.timer += 20

    def output_item(self, world, item_name):
        nx, ny = self.x, self.y
        if self.facing == "UP": ny -= 1
        elif self.facing == "DOWN": ny += 1
        elif self.facing == "LEFT": nx -= 1
        elif self.facing == "RIGHT": nx += 1
        
        target = world.get_building(nx, ny)
        if target:
            target.inventory.add(item_name, 1)
            return True
        elif self.type == "drill":
            self.inventory.add(item_name, 1)
            return True
        return False

    def render(self, surface, cam):
        r = self.rect.move(-cam[0], -cam[1])
        
        if self.type == "furnace":
            pygame.draw.rect(surface, (60, 60, 70), r)
            pygame.draw.rect(surface, (20, 20, 20), r.inflate(-8, -8))
            if self.inventory.items: 
                 pygame.draw.rect(surface, (255, 100, 0), r.inflate(-12, -12))
        elif self.type == "assembler":
            pygame.draw.rect(surface, COLORS["BLUE"], r)
            pygame.draw.rect(surface, COLORS["WHITE"], r.inflate(-10,-10), 2)
        elif self.type == "drill":
            pygame.draw.rect(surface, COLORS["DRILL"], r)
            self._draw_arrow(surface, r)
        elif self.type == "conveyor":
            pygame.draw.rect(surface, COLORS["CONVEYOR"], r)
            self._draw_arrow(surface, r, (200, 200, 200))
            if self.inventory.items:
                pygame.draw.circle(surface, COLORS["BLUE"], r.center, 6)
        elif self.type == "totem":
            pygame.draw.rect(surface, (50, 200, 50), r)
            pygame.draw.circle(surface, COLORS["GOLD"], r.center, 8)

    def _draw_arrow(self, surf, rect, color=COLORS["BLACK"]):
        cx, cy = rect.center
        off = 8
        pts = []
        if self.facing == "UP": pts = [(cx, cy+off), (cx, cy-off)]
        elif self.facing == "DOWN": pts = [(cx, cy-off), (cx, cy+off)]
        elif self.facing == "LEFT": pts = [(cx+off, cy), (cx-off, cy)]
        elif self.facing == "RIGHT": pts = [(cx-off, cy), (cx+off, cy)]
        if pts: pygame.draw.line(surf, color, pts[0], pts[1], 3)

class Player:
    def __init__(self, p_id, x, y, color):
        self.id = p_id
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE-6, TILE_SIZE-6)
        self.color = color
        self.speed = 5
        self.inventory = Inventory()
        self.facing = "DOWN" 
        self.interact_rect = self.rect.copy()
        self.hotbar_index = 0

    def update(self, keys, w_px, h_px):
        dx, dy = 0, 0
        if self.id == 1: 
            if keys[pygame.K_w]: dy = -1; self.facing = "UP"
            if keys[pygame.K_s]: dy = 1; self.facing = "DOWN"
            if keys[pygame.K_a]: dx = -1; self.facing = "LEFT"
            if keys[pygame.K_d]: dx = 1; self.facing = "RIGHT"
        else: 
            if keys[pygame.K_UP]: dy = -1; self.facing = "UP"
            if keys[pygame.K_DOWN]: dy = 1; self.facing = "DOWN"
            if keys[pygame.K_LEFT]: dx = -1; self.facing = "LEFT"
            if keys[pygame.K_RIGHT]: dx = 1; self.facing = "RIGHT"

        if dx != 0 or dy != 0:
            mag = math.sqrt(dx*dx + dy*dy)
            new_rect = self.rect.move((dx/mag)*self.speed, (dy/mag)*self.speed)
            if 0 <= new_rect.left and new_rect.right <= w_px and 0 <= new_rect.top and new_rect.bottom <= h_px:
                self.rect = new_rect

        self._update_interaction_rect()

    def _update_interaction_rect(self):
        cx, cy = self.rect.centerx, self.rect.centery
        dist = 32
        if self.facing == "UP": cy -= dist
        elif self.facing == "DOWN": cy += dist
        elif self.facing == "LEFT": cx -= dist
        elif self.facing == "RIGHT": cx += dist
        self.interact_rect.center = (cx, cy)

    def cycle_hotbar(self):
        items = self.inventory.get_list()
        if items:
            self.hotbar_index = (self.hotbar_index + 1) % len(items)

    def get_selected_item(self):
        items = self.inventory.get_list()
        if not items: return None
        if self.hotbar_index >= len(items): self.hotbar_index = 0
        return items[self.hotbar_index]

    def render(self, surface, cam):
        r = self.rect.move(-cam[0], -cam[1])
        pygame.draw.rect(surface, self.color, r)
        pygame.draw.rect(surface, COLORS["BLACK"], r, 2)
        
        eye_off_x, eye_off_y = 0, 0
        if self.facing == "UP": eye_off_y = -4
        elif self.facing == "DOWN": eye_off_y = 4
        elif self.facing == "LEFT": eye_off_x = -4
        elif self.facing == "RIGHT": eye_off_x = 4
        
        pygame.draw.circle(surface, COLORS["WHITE"], (r.centerx + eye_off_x - 3, r.centery + eye_off_y - 3), 2)
        pygame.draw.circle(surface, COLORS["WHITE"], (r.centerx + eye_off_x + 3, r.centery + eye_off_y - 3), 2)

        sel = self.interact_rect.move(-cam[0], -cam[1])
        tx, ty = sel.centerx // TILE_SIZE, sel.centery // TILE_SIZE
        pygame.draw.rect(surface, COLORS["WHITE"], (tx*TILE_SIZE - cam[0], ty*TILE_SIZE - cam[1], TILE_SIZE, TILE_SIZE), 1)

class World:
    def __init__(self, seed, width=128, height=128):
        self.seed = seed
        self.width, self.height = width, height
        self.tiles = {}
        self.buildings = {} 
        self._generate()

    def _generate(self):
        random.seed(self.seed)
        for y in range(self.height):
            for x in range(self.width):
                nx, ny = x * 0.05, y * 0.05
                n = math.sin(nx) + math.cos(ny) + (math.sin(nx*3) * 0.5 + math.cos(ny*3) * 0.5) + random.uniform(-0.2, 0.2)

                t_type = TileType.GRASS
                if n < -1.5: t_type = TileType.WATER
                elif n < -1.1: t_type = TileType.SAND
                elif n > 1.8: t_type = TileType.STONE
                
                if t_type == TileType.GRASS:
                    rnd = random.random()
                    if rnd < 0.08: t_type = TileType.TREE
                    elif rnd < 0.10: t_type = TileType.ESSENCE
                    elif rnd < 0.115: t_type = TileType.ORE_COAL
                elif t_type == TileType.STONE:
                    rnd = random.random()
                    if rnd < 0.15: t_type = TileType.ORE_IRON
                    elif rnd < 0.25: t_type = TileType.ORE_COPPER
                    elif rnd < 0.28: t_type = TileType.ORE_GOLD

                self.tiles[(x, y)] = Tile(x, y, t_type)

    def get_tile_type(self, x, y):
        return self.tiles[(x, y)].type if (x, y) in self.tiles else None

    def set_tile_type(self, x, y, new_type):
        if (x, y) in self.tiles:
            self.tiles[(x, y)].type = new_type
            self.tiles[(x, y)].base_color = self.tiles[(x, y)]._resolve_color(new_type, x, y)

    def get_building(self, x, y):
        return self.buildings.get((x, y))

# ==========================================
# GAME ENGINE
# ==========================================

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Factorial")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14, bold=True)
        self.title_font = pygame.font.SysFont("Verdana", 40, bold=True)
        
        self.state = GameState.MENU
        self.unlocks = UnlockManager()
        self.world = None
        self.p1, self.p2 = None, None
        self.cams = [[0, 0], [0, 0]]
        self.notifications = []
        self.minimap_surface = None

    def start_game(self, seed=None):
        self.world = World(seed if seed else random.randint(0, 9999))
        self.p1 = Player(1, self.world.width//2, self.world.height//2, COLORS["BLUE"])
        self.p2 = Player(2, self.world.width//2 + 2, self.world.height//2, COLORS["GREEN"])
        self.state = GameState.PLAYING
        self._generate_minimap()

    def _generate_minimap(self):
        self.minimap_surface = pygame.Surface((self.world.width, self.world.height))
        color_map = {
            TileType.ORE_IRON: COLORS["IRON"], TileType.ORE_COPPER: COLORS["COPPER"],
            TileType.ORE_GOLD: COLORS["GOLD"], TileType.ORE_COAL: (20, 20, 20),
            TileType.TREE: COLORS["TREE"]
        }
        for loc, tile in self.world.tiles.items():
            self.minimap_surface.set_at(loc, color_map.get(tile.type, tile.base_color))

    def run(self):
        while True:
            self._handle_input()
            self._update()
            self._render()
            pygame.display.flip()
            self.clock.tick(FPS)

    def _handle_input(self):
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in [GameState.PLAYING, GameState.MAP_VIEW, GameState.CRAFTING_MENU, GameState.UNLOCK_MENU]: 
                        self.state = GameState.MENU
                    elif self.state == GameState.MENU: pygame.quit(); sys.exit()

                self._process_state_keys(event)

        if self.state == GameState.PLAYING:
            self.p1.update(keys, self.world.width*TILE_SIZE, self.world.height*TILE_SIZE)
            self.p2.update(keys, self.world.width*TILE_SIZE, self.world.height*TILE_SIZE)

    def _process_state_keys(self, event):
        if self.state == GameState.MENU:
            if event.key == pygame.K_RETURN: self.start_game()
            if event.key == pygame.K_c: self.state = GameState.CONTROLS
        
        elif self.state == GameState.CONTROLS:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_c: 
                self.state = GameState.PLAYING if self.p1 else GameState.MENU

        elif self.state == GameState.PLAYING:
            # P1
            if event.key == pygame.K_b: self.p1_interact()
            if event.key == pygame.K_q: self.state = GameState.CRAFTING_MENU
            if event.key == pygame.K_TAB: self.p1.cycle_hotbar()
            if event.key == pygame.K_m: self.state = GameState.MAP_VIEW
            if event.key == pygame.K_c: self.state = GameState.CONTROLS
            # P2
            if event.key in [pygame.K_SPACE, pygame.K_RETURN]: self.p2_interact()
            if event.key == pygame.K_p: self.state = GameState.UNLOCK_MENU
            if event.key == pygame.K_o: self.p2_build_totem()
            if event.key == pygame.K_l: self.p2_replant()

        elif self.state == GameState.MAP_VIEW:
            if event.key == pygame.K_m: self.state = GameState.PLAYING

        elif self.state == GameState.UNLOCK_MENU:
            if event.key == pygame.K_p: self.state = GameState.PLAYING
            if pygame.K_1 <= event.key <= pygame.K_7:
                keys = list(UNLOCK_DATA.keys())
                self.try_unlock(keys[event.key - pygame.K_1])

        elif self.state == GameState.CRAFTING_MENU:
            if event.key == pygame.K_q: self.state = GameState.PLAYING
            r_keys = list(RECIPES.keys())
            idx = -1
            if pygame.K_1 <= event.key <= pygame.K_9: idx = event.key - pygame.K_1
            elif event.key == pygame.K_0: idx = 9
            if 0 <= idx < len(r_keys): self.craft(r_keys[idx])

    def _update(self):
        if self.state == GameState.PLAYING:
            for b in self.world.buildings.values():
                b.update(self.world)
            self.cams[0] = [self.p1.rect.centerx - HALF_WIDTH//2, self.p1.rect.centery - SCREEN_HEIGHT//2]
            self.cams[1] = [self.p2.rect.centerx - HALF_WIDTH//2, self.p2.rect.centery - SCREEN_HEIGHT//2]

    # --- P1 ACTIONS ---
    def p1_interact(self):
        if not self.unlocks.can_do("inventory"):
            self.notify("Unlock Backpack first!", COLORS["RED"]); return

        tx = int(self.p1.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p1.interact_rect.centery // TILE_SIZE)
        
        b = self.world.get_building(tx, ty)
        if b:
            for item, amt in list(b.inventory.items.items()):
                b.inventory.remove(item, amt)
                self.p1.inventory.add(item, amt)
                self.notify(f"Took {amt} {item}")
                return 

        t_type = self.world.get_tile_type(tx, ty)
        if t_type and t_type not in [TileType.GRASS, TileType.SAND, TileType.WATER]:
            if t_type == TileType.TREE:
                self.p1.inventory.add("wood", 1)
                self.world.set_tile_type(tx, ty, TileType.GRASS)
                self.notify("Chopped Wood")
            elif self.unlocks.can_do("mining"):
                res_map = {TileType.STONE: "stone", TileType.ORE_IRON: "ore_iron", TileType.ORE_COPPER: "ore_copper", TileType.ORE_COAL: "coal", TileType.ORE_GOLD: "ore_gold"}
                if t_type in res_map:
                    self.p1.inventory.add(res_map[t_type], 1)
                    self.world.set_tile_type(tx, ty, TileType.GRASS)
                    self.notify(f"Mined {res_map[t_type]}")
            else:
                self.notify("Need Mining Pick!", COLORS["RED"])
            return

        selected = self.p1.get_selected_item()
        if selected in ["furnace", "drill", "conveyor", "assembler"]:
             reqs = {"furnace": "smelting", "drill": "automation", "conveyor": "automation", "assembler": "advanced"}
             if self.unlocks.can_do(reqs[selected]):
                 self._place_building(tx, ty, selected, self.p1)

    def _place_building(self, x, y, b_type, player):
        if (x, y) not in self.world.buildings and self.world.get_tile_type(x,y) != TileType.WATER:
            if player.inventory.remove(b_type, 1):
                self.world.buildings[(x, y)] = Building(x, y, b_type, player.facing)
                self.notify(f"Placed {b_type}")

    def craft(self, item_key):
        if item_key == "totem": return 
        recipe = RECIPES[item_key]
        for req, amt in recipe["inputs"].items():
            if not self.p1.inventory.has(req, amt):
                self.notify("Missing materials!", COLORS["RED"]); return
        
        for req, amt in recipe["inputs"].items():
            self.p1.inventory.remove(req, amt)
        self.p1.inventory.add(item_key, recipe["output"])
        self.notify(f"Crafted {item_key}!")

    # --- P2 ACTIONS ---
    def p2_interact(self):
        tx = int(self.p2.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p2.interact_rect.centery // TILE_SIZE)
        t_type = self.world.get_tile_type(tx, ty)
        
        if t_type == TileType.ESSENCE:
            pts = random.randint(15, 30)
            self.unlocks.points += pts
            self.world.set_tile_type(tx, ty, TileType.GRASS)
            self.notify(f"P2: +{pts} Essence", COLORS["GOLD"])
        elif t_type == TileType.TREE:
            self.unlocks.points += 5
            self.world.set_tile_type(tx, ty, TileType.GRASS)
            self.notify("P2 Cleared Tree (+5 pts)", COLORS["GREEN"])
        elif t_type == TileType.STONE and self.unlocks.points >= 10:
            self.unlocks.points -= 10
            r = random.random()
            new_t = TileType.ORE_IRON if r > 0.4 else (TileType.ORE_COPPER if r > 0.3 else TileType.ORE_COAL)
            self.world.set_tile_type(tx, ty, new_t)
            self.notify("P2: Transmuted Stone", COLORS["PURPLE"])

    def p2_replant(self):
        tx = int(self.p2.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p2.interact_rect.centery // TILE_SIZE)
        if self.world.get_tile_type(tx, ty) == TileType.GRASS and self.unlocks.points >= 5:
            self.unlocks.points -= 5
            self.world.set_tile_type(tx, ty, TileType.TREE)
            self.notify("P2: Replanted Tree", COLORS["GREEN"])

    def p2_build_totem(self):
        if not self.unlocks.can_do("druidry"): 
            self.notify("Unlock Nature Totem first!", COLORS["RED"]); return
        
        tx = int(self.p2.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p2.interact_rect.centery // TILE_SIZE)
        
        if (tx, ty) not in self.world.buildings:
            if self.unlocks.points >= 50:
                self.unlocks.points -= 50
                self.world.buildings[(tx, ty)] = Building(tx, ty, "totem", "DOWN")
                self.notify("P2: Summoned Totem", COLORS["GOLD"])
            else:
                self.notify("Need 50 Essence", COLORS["RED"])

    def try_unlock(self, key):
        if self.unlocks.purchase(key):
            self.notify(f"UNLOCKED: {key.upper()}!", COLORS["GREEN"])
        else:
            self.notify("Cannot Buy (Points/Already Owned)", COLORS["RED"])

    def notify(self, msg, color=COLORS["WHITE"]):
        self.notifications.append([msg, color, 120])

    # --- RENDERING ---
    def _render(self):
        if self.state == GameState.MENU:
            self._render_menu()
        elif self.state == GameState.CONTROLS:
            self._render_controls()
        elif self.state == GameState.MAP_VIEW:
            self._render_map()
        else:
            s1, s2 = pygame.Surface((HALF_WIDTH, SCREEN_HEIGHT)), pygame.Surface((HALF_WIDTH, SCREEN_HEIGHT))
            self._render_viewport(s1, self.cams[0], self.p1)
            self._render_viewport(s2, self.cams[1], self.p2)
            self.screen.blit(s1, (0,0))
            self.screen.blit(s2, (HALF_WIDTH, 0))
            pygame.draw.line(self.screen, COLORS["BLACK"], (HALF_WIDTH, 0), (HALF_WIDTH, SCREEN_HEIGHT), 4)
            self._render_hud()
            if self.state == GameState.UNLOCK_MENU: self._render_unlocks()
            if self.state == GameState.CRAFTING_MENU: self._render_crafting()

    def _render_viewport(self, surface, cam, player):
        surface.fill(COLORS["BLACK"])
        sx, sy = max(0, cam[0] // TILE_SIZE), max(0, cam[1] // TILE_SIZE)
        ex, ey = min(self.world.width, sx + (HALF_WIDTH // TILE_SIZE) + 2), min(self.world.height, sy + (SCREEN_HEIGHT // TILE_SIZE) + 2)

        for y in range(sy, ey):
            for x in range(sx, ex):
                t = self.world.tiles.get((x,y))
                if t:
                    r = t.rect.move(-cam[0], -cam[1])
                    pygame.draw.rect(surface, t.base_color, r)
                    if t.type == TileType.TREE: pygame.draw.circle(surface, COLORS["TREE"], r.center, 12)
                    elif t.type == TileType.ORE_IRON: pygame.draw.circle(surface, COLORS["IRON"], r.center, 6)
                    elif t.type == TileType.ORE_COPPER: pygame.draw.circle(surface, COLORS["COPPER"], r.center, 6)
                    elif t.type == TileType.ORE_GOLD: pygame.draw.circle(surface, COLORS["GOLD"], r.center, 6)
                    elif t.type == TileType.ORE_COAL: pygame.draw.circle(surface, COLORS["COAL"], r.center, 7)
                    elif t.type == TileType.ESSENCE:
                        pulse = 5 + math.sin(pygame.time.get_ticks()*0.01)*2
                        pygame.draw.circle(surface, COLORS["GOLD"], r.center, pulse)

        for b in self.world.buildings.values():
            if sx <= b.x <= ex and sy <= b.y <= ey:
                b.render(surface, cam)

        if player: player.render(surface, cam)

    def _render_hud(self):
        if not self.p1: return 
        
        # Top Bar
        pygame.draw.rect(self.screen, COLORS["UI_BG"], (0, 0, SCREEN_WIDTH, 40))
        self.screen.blit(self.font.render(f"P1 (Engineer) | TAB: Cycle | Q: Craft | B: Interact", True, COLORS["BLUE"]), (10, 10))
        self.screen.blit(self.font.render(f"P2 (Druid): {self.unlocks.points} Essence | P: Unlocks | O: Totem | L: Plant", True, COLORS["GREEN"]), (HALF_WIDTH + 10, 10))

        # Hotbar
        items = self.p1.inventory.get_list()
        if items:
            pygame.draw.rect(self.screen, (0, 0, 0, 150), (10, SCREEN_HEIGHT - 50, len(items)*40 + 10, 45))
            for i, item in enumerate(items):
                col = COLORS["WHITE"] if i == self.p1.hotbar_index else COLORS["GRAY"]
                pygame.draw.rect(self.screen, col, (15 + i*40, SCREEN_HEIGHT - 45, 36, 36), 2)
                self.screen.blit(self.font.render(item[:3].upper(), True, col), (18 + i*40, SCREEN_HEIGHT - 35))
                self.screen.blit(self.font.render(str(self.p1.inventory.items[item]), True, COLORS["WHITE"]), (18 + i*40, SCREEN_HEIGHT - 20))

        # Notifications
        y = 50
        for n in self.notifications[:]:
            txt = self.font.render(n[0], True, n[1])
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, y))
            y += 20
            n[2] -= 1
            if n[2] <= 0: self.notifications.remove(n)

    def _render_menu(self):
        self.screen.fill(COLORS["UI_BG"])
        t = self.title_font.render("ECO-FACTORY", True, COLORS["WHITE"])
        self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 200))
        b1 = self.font.render("Press ENTER to Start", True, COLORS["SKY_BLUE"])
        self.screen.blit(b1, (SCREEN_WIDTH//2 - b1.get_width()//2, 300))
        b2 = self.font.render("Press C for Controls", True, COLORS["GOLD"])
        self.screen.blit(b2, (SCREEN_WIDTH//2 - b2.get_width()//2, 350))

    def _render_controls(self):
        self.screen.fill(COLORS["UI_BG"])
        lines = ["CONTROLS", "", "PLAYER 1 (Blue)", "Move: WASD", "Interact: B", "Craft: Q", "Cycle: TAB", "Map: M", "",
                 "PLAYER 2 (Green)", "Move: ARROWS", "Interact: SPACE/ENTER", "Unlocks: P", "Totem: O", "Plant: L", "", "ESC/C to Return"]
        for i, line in enumerate(lines):
            c = COLORS["BLUE"] if "PLAYER 1" in line else (COLORS["GREEN"] if "PLAYER 2" in line else COLORS["WHITE"])
            t = self.font.render(line, True, c)
            self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 50 + i*30))

    def _render_map(self):
        if not self.minimap_surface: return
        scale = min(SCREEN_WIDTH / self.world.width, SCREEN_HEIGHT / self.world.height)
        w, h = int(self.world.width * scale), int(self.world.height * scale)
        
        self.screen.fill(COLORS["BLACK"])
        ox, oy = (SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2
        self.screen.blit(pygame.transform.scale(self.minimap_surface, (w, h)), (ox, oy))
        
        for p, col in [(self.p1, COLORS["BLUE"]), (self.p2, COLORS["GREEN"])]:
            px = int(p.rect.centerx / (self.world.width*TILE_SIZE) * w)
            py = int(p.rect.centery / (self.world.height*TILE_SIZE) * h)
            pygame.draw.circle(self.screen, col, (ox+px, oy+py), 5)
        
        self.screen.blit(self.title_font.render("WORLD MAP (M to close)", True, COLORS["WHITE"]), (20, 20))

    def _render_unlocks(self):
        self._draw_overlay("DRUIDIC KNOWLEDGE (P2)", COLORS["GOLD"])
        y, idx = 120, 1
        for k, v in self.unlocks.unlocks.items():
            col = COLORS["GREEN"] if v["unlocked"] else (COLORS["WHITE"] if self.unlocks.points >= v["cost"] else COLORS["GRAY"])
            txt = self.font.render(f"[{idx}] {v['name']} ({v['cost']} pts): {v['desc']}", True, col)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, y))
            y += 50; idx += 1

    def _render_crafting(self):
        self._draw_overlay("ENGINEER ASSEMBLY (P1)", COLORS["BLUE"])
        y, idx = 120, 1
        for k, v in RECIPES.items():
            if v["type"] == "nature": continue
            ins = ", ".join([f"{amt} {n}" for n, amt in v["inputs"].items()])
            affordable = all(self.p1.inventory.has(n, amt) for n, amt in v["inputs"].items())
            col = COLORS["WHITE"] if affordable else COLORS["GRAY"]
            txt = self.font.render(f"[{idx}] {k.upper()} (x{v['output']}) requires: {ins}", True, col)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, y))
            y += 40; idx += 1
        
        h = self.font.render("Press 1-9 to Craft | Q to Close", True, COLORS["SKY_BLUE"])
        self.screen.blit(h, (SCREEN_WIDTH//2 - h.get_width()//2, SCREEN_HEIGHT - 50))

    def _draw_overlay(self, title, color):
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill(COLORS["UI_OVERLAY"])
        self.screen.blit(s, (0,0))
        t = self.title_font.render(title, True, color)
        self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 50))

if __name__ == "__main__":
    GameEngine().run()