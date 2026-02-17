import pygame
import random
import sys
import math
from enum import Enum

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TILE_SIZE = 32
HALF_WIDTH = SCREEN_WIDTH // 2

# Colors
WHITE = (255, 255, 255)
BLACK = (10, 10, 14)
GRAY = (50, 50, 50)
LIGHT_GRAY = (150, 150, 150)
RED = (220, 60, 60)
GREEN = (60, 240, 120)
BLUE = (80, 120, 255)
SKY_BLUE = (135, 206, 235)
GOLD = (255, 215, 0)
PURPLE = (180, 60, 220)

# Palette
GRASS_GREEN = (70, 180, 80)
WATER_BLUE = (60, 140, 220)
SAND_TAN = (230, 210, 160)
STONE_SLATE = (110, 110, 125)
DIRT_RICH = (100, 70, 40)
TREE_GREEN = (30, 130, 60)
WOOD_BROWN = (140, 90, 50)
CONVEYOR_GRAY = (160, 160, 170)
DRILL_ORANGE = (220, 140, 40)
COAL_BLACK = (30, 30, 35)
GOLD_ORE_COLOR = (255, 200, 50)

def _clamp(x): return max(0, min(255, int(x)))
def vary_color(col, x, y, amt=15):
    random.seed(x * 1000 + y)
    d = random.randint(-amt, amt)
    return (_clamp(col[0]+d), _clamp(col[1]+d), _clamp(col[2]+d))

# ==========================================
# DATA & RECIPES
# ==========================================

RECIPES = {
    # Basic Components
    "plank":     {"inputs": {"wood": 1}, "output": 2, "type": "item"},
    "gear":      {"inputs": {"iron_ingot": 1}, "output": 2, "type": "item"},
    "wire":      {"inputs": {"copper_ingot": 1}, "output": 2, "type": "item"},
    "circuit":   {"inputs": {"wire": 2, "iron_ingot": 1}, "output": 1, "type": "item"},
    "processor": {"inputs": {"circuit": 2, "gold_ingot": 1}, "output": 1, "type": "item"},
    
    # Buildings (P1)
    "furnace":   {"inputs": {"stone": 5}, "output": 1, "type": "building"},
    "drill":     {"inputs": {"iron_ingot": 3, "gear": 2}, "output": 1, "type": "building"},
    "conveyor":  {"inputs": {"iron_ingot": 1, "gear": 1}, "output": 4, "type": "building"},
    "assembler": {"inputs": {"stone": 10, "circuit": 2}, "output": 1, "type": "building"},
    
    # Nature Structures (P2 - unlocked via points, but listed here for logic)
    "totem":     {"inputs": {}, "output": 1, "type": "nature"}, 
}

# ==========================================
# SYSTEMS
# ==========================================

class GameState(Enum):
    MENU = 0
    PLAYING = 1
    UNLOCK_MENU = 2
    CRAFTING_MENU = 3 
    MAP_VIEW = 4
    CONTROLS = 5

class UnlockManager:
    def __init__(self):
        self.points = 0
        self.unlocks = {
            "inventory": {"cost": 25,  "unlocked": False, "name": "Backpack", "desc": "P1 can hold items."},
            "mining":    {"cost": 50,  "unlocked": False, "name": "Stone Pick", "desc": "P1 can mine Stone/Ore."},
            "crafting":  {"cost": 100, "unlocked": False, "name": "Workbench", "desc": "P1 can Craft (Press Q)."},
            "smelting":  {"cost": 200, "unlocked": False, "name": "Metallurgy", "desc": "Unlock Furnaces/Coal."},
            "automation":{"cost": 400, "unlocked": False, "name": "Logistics", "desc": "Unlock Drills & Belts."},
            "advanced":  {"cost": 600, "unlocked": False, "name": "Engineering", "desc": "Assemblers & Gold."},
            "druidry":   {"cost": 800, "unlocked": False, "name": "Nature Totem", "desc": "P2 can build Totems."}
        }

    def can_do(self, key):
        return self.unlocks.get(key, {}).get("unlocked", False)

    def purchase(self, key):
        data = self.unlocks.get(key)
        if data and self.points >= data["cost"] and not data["unlocked"]:
            self.points -= data["cost"]
            data["unlocked"] = True
            return True
        return False

# ==========================================
# WORLD
# ==========================================

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

class Tile:
    def __init__(self, x, y, t_type):
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.type = t_type
        self.base_color = self._get_color(t_type, x, y)
    
    def _get_color(self, t, x, y):
        if t == TileType.GRASS: return vary_color(GRASS_GREEN, x, y, 10)
        if t == TileType.SAND: return vary_color(SAND_TAN, x, y, 10)
        if t == TileType.WATER: return vary_color(WATER_BLUE, x, y, 5)
        if t == TileType.STONE: return vary_color(STONE_SLATE, x, y, 10)
        return BLACK 

class World:
    def __init__(self, seed, width=128, height=128):
        self.seed = seed
        self.width = width
        self.height = height
        self.tiles = {}
        self.buildings = {} 
        self.generate()

    def generate(self):
        random.seed(self.seed)
        for y in range(self.height):
            for x in range(self.width):
                nx = x * 0.05
                ny = y * 0.05
                base = math.sin(nx) + math.cos(ny)
                detail = math.sin(nx*3) * 0.5 + math.cos(ny*3) * 0.5
                n = base + detail + random.uniform(-0.2, 0.2)

                t_type = TileType.GRASS
                if n < -1.5: t_type = TileType.WATER
                elif n < -1.1: t_type = TileType.SAND
                elif n > 1.8: t_type = TileType.STONE
                
                if t_type == TileType.GRASS:
                    if random.random() < 0.08: t_type = TileType.TREE
                    elif random.random() < 0.02: t_type = TileType.ESSENCE
                    elif random.random() < 0.015: t_type = TileType.ORE_COAL
                elif t_type == TileType.STONE:
                    rnd = random.random()
                    if rnd < 0.15: t_type = TileType.ORE_IRON
                    elif rnd < 0.25: t_type = TileType.ORE_COPPER
                    elif rnd < 0.28: t_type = TileType.ORE_GOLD

                self.tiles[(x, y)] = Tile(x, y, t_type)

    def get_tile_type(self, x, y):
        t = self.tiles.get((x, y))
        return t.type if t else None

    def set_tile_type(self, x, y, new_type):
        if (x,y) in self.tiles:
            self.tiles[(x,y)].type = new_type
            self.tiles[(x,y)].base_color = self.tiles[(x,y)]._get_color(new_type, x, y)

    def get_building(self, x, y):
        return self.buildings.get((x, y))

# ==========================================
# ENTITIES
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

class Player:
    def __init__(self, p_id, x, y, color):
        self.id = p_id
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE-6, TILE_SIZE-6)
        self.color = color
        self.speed = 5
        self.inventory = Inventory()
        self.facing = "DOWN" 
        self.interact_rect = self.rect.copy()
        
        # Hotbar Logic
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
            dx, dy = (dx/mag)*self.speed, (dy/mag)*self.speed
            new_rect = self.rect.move(dx, dy)
            if 0 <= new_rect.left and new_rect.right <= w_px and 0 <= new_rect.top and new_rect.bottom <= h_px:
                self.rect = new_rect

        cx, cy = self.rect.centerx, self.rect.centery
        dist = 32
        if self.facing == "UP": cy -= dist
        elif self.facing == "DOWN": cy += dist
        elif self.facing == "LEFT": cx -= dist
        elif self.facing == "RIGHT": cx += dist
        self.interact_rect.center = (cx, cy)

    def cycle_hotbar(self):
        items = self.inventory.get_list()
        if not items: return
        self.hotbar_index = (self.hotbar_index + 1) % len(items)

    def get_selected_item(self):
        items = self.inventory.get_list()
        if not items: return None
        if self.hotbar_index >= len(items): self.hotbar_index = 0
        return items[self.hotbar_index]

    def render(self, surface, cam):
        r = self.rect.move(-cam[0], -cam[1])
        pygame.draw.rect(surface, self.color, r)
        pygame.draw.rect(surface, BLACK, r, 2)
        
        # Simple eyes to show direction
        eye_color = WHITE
        eye_off_x, eye_off_y = 0, 0
        if self.facing == "UP": eye_off_y = -4
        if self.facing == "DOWN": eye_off_y = 4
        if self.facing == "LEFT": eye_off_x = -4
        if self.facing == "RIGHT": eye_off_x = 4
        
        pygame.draw.circle(surface, eye_color, (r.centerx + eye_off_x - 3, r.centery + eye_off_y - 3), 2)
        pygame.draw.circle(surface, eye_color, (r.centerx + eye_off_x + 3, r.centery + eye_off_y - 3), 2)

        # Selection Box
        sel = self.interact_rect.move(-cam[0], -cam[1])
        tx, ty = sel.centerx // TILE_SIZE, sel.centery // TILE_SIZE
        grid_sel = pygame.Rect(tx*TILE_SIZE - cam[0], ty*TILE_SIZE - cam[1], TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surface, (255, 255, 255), grid_sel, 1)

# ==========================================
# BUILDINGS & AUTOMATION
# ==========================================

class Building:
    def __init__(self, x, y, b_type, facing="DOWN"):
        self.x, self.y = x, y
        self.type = b_type
        self.facing = facing
        self.rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.inventory = Inventory()
        self.timer = 0
        
    def update(self, world):
        self.timer += 1
        
        # --- DRILL ---
        if self.type == "drill":
            if self.timer >= 100: 
                self.timer = 0
                tile = world.get_tile_type(self.x, self.y)
                res = None
                if tile == TileType.ORE_IRON: res = "ore_iron"
                elif tile == TileType.ORE_COPPER: res = "ore_copper"
                elif tile == TileType.ORE_COAL: res = "coal"
                elif tile == TileType.ORE_GOLD: res = "ore_gold"
                elif tile == TileType.STONE: res = "stone"
                
                if res:
                    self.output_item(world, res)

        # --- FURNACE ---
        elif self.type == "furnace":
            # Simple simulation: 1 ore -> 1 ingot
            if self.timer >= 150: 
                self.timer = 0
                # Process
                for ore, ingot in [("ore_iron", "iron_ingot"), 
                                   ("ore_copper", "copper_ingot"), 
                                   ("ore_gold", "gold_ingot")]:
                    if self.inventory.has(ore):
                        self.inventory.remove(ore, 1)
                        self.inventory.add(ingot, 1)
                        break

        # --- CONVEYOR ---
        elif self.type == "conveyor":
            if self.timer >= 30: 
                self.timer = 0
                for item, amt in list(self.inventory.items.items()):
                    if amt > 0:
                        if self.output_item(world, item):
                            self.inventory.remove(item, 1)
                            break 
        
        # --- ASSEMBLER ---
        elif self.type == "assembler":
            if self.timer >= 200:
                self.timer = 0
                # Simple auto-craft gears if iron is present
                if self.inventory.has("iron_ingot", 1):
                    self.inventory.remove("iron_ingot", 1)
                    self.inventory.add("gear", 2)

        # --- TOTEM (P2) ---
        elif self.type == "totem":
            # Speed up nearby buildings
            if self.timer >= 60:
                self.timer = 0
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        b = world.get_building(self.x + dx, self.y + dy)
                        if b and b.type != "totem":
                            b.timer += 20 # Speed boost

    def output_item(self, world, item_name):
        nx, ny = self.get_neighbor_coords()
        target = world.get_building(nx, ny)
        if target:
            target.inventory.add(item_name, 1)
            return True
        elif self.type == "drill":
            # Drills can dump to internal inventory if no output
            self.inventory.add(item_name, 1)
            return True
        return False

    def get_neighbor_coords(self):
        nx, ny = self.x, self.y
        if self.facing == "UP": ny -= 1
        elif self.facing == "DOWN": ny += 1
        elif self.facing == "LEFT": nx -= 1
        elif self.facing == "RIGHT": nx += 1
        return nx, ny

    def render(self, surface, cam):
        r = self.rect.move(-cam[0], -cam[1])
        
        if self.type == "furnace":
            pygame.draw.rect(surface, (60, 60, 70), r)
            pygame.draw.rect(surface, (20, 20, 20), r.inflate(-8, -8))
            if self.inventory.items: 
                 pygame.draw.rect(surface, (255, 100, 0), r.inflate(-12, -12))
        
        elif self.type == "assembler":
            pygame.draw.rect(surface, BLUE, r)
            pygame.draw.rect(surface, WHITE, r.inflate(-10,-10), 2)

        elif self.type == "drill":
            pygame.draw.rect(surface, DRILL_ORANGE, r)
            self.draw_arrow(surface, r)

        elif self.type == "conveyor":
            pygame.draw.rect(surface, CONVEYOR_GRAY, r)
            self.draw_arrow(surface, r, color=(200, 200, 200))
            if self.inventory.items:
                pygame.draw.circle(surface, BLUE, r.center, 6)
        
        elif self.type == "totem":
            pygame.draw.rect(surface, (50, 200, 50), r)
            pygame.draw.circle(surface, GOLD, r.center, 8)

    def draw_arrow(self, surf, rect, color=BLACK):
        cx, cy = rect.center
        off = 8
        if self.facing == "UP":
            pygame.draw.line(surf, color, (cx, cy+off), (cx, cy-off), 3)
        elif self.facing == "DOWN":
            pygame.draw.line(surf, color, (cx, cy-off), (cx, cy+off), 3)
        elif self.facing == "LEFT":
            pygame.draw.line(surf, color, (cx+off, cy), (cx-off, cy), 3)
        elif self.facing == "RIGHT":
            pygame.draw.line(surf, color, (cx-off, cy), (cx+off, cy), 3)

# ==========================================
# MAIN GAME CLASS
# ==========================================

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Eco-Factory: Symbiosis")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14, bold=True)
        self.title_font = pygame.font.SysFont("Verdana", 40, bold=True)
        
        self.state = GameState.MENU
        self.unlocks = UnlockManager()
        self.world = None
        self.p1 = None
        self.p2 = None
        
        self.cam1 = [0, 0]
        self.cam2 = [0, 0]
        self.notifications = []
        
        self.minimap_surface = None

    def start_game(self, seed=None):
        if seed is None: seed = random.randint(0, 9999)
        self.world = World(seed)
        self.p1 = Player(1, self.world.width//2, self.world.height//2, BLUE)
        self.p2 = Player(2, self.world.width//2 + 2, self.world.height//2, GREEN)
        self.state = GameState.PLAYING
        self.generate_minimap()

    def generate_minimap(self):
        # Create a static surface for the terrain map
        self.minimap_surface = pygame.Surface((self.world.width, self.world.height))
        for loc, tile in self.world.tiles.items():
            c = tile.base_color
            if tile.type == TileType.ORE_IRON: c = (150, 100, 100)
            if tile.type == TileType.ORE_COPPER: c = (200, 120, 60)
            if tile.type == TileType.ORE_GOLD: c = GOLD
            if tile.type == TileType.ORE_COAL: c = (20, 20, 20)
            if tile.type == TileType.TREE: c = TREE_GREEN
            self.minimap_surface.set_at(loc, c)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in [GameState.PLAYING, GameState.MAP_VIEW, GameState.CRAFTING_MENU, GameState.UNLOCK_MENU]: 
                        self.state = GameState.MENU
                    elif self.state == GameState.MENU: pygame.quit(); sys.exit()
                    # If in CONTROLS, handle inside controls logic for smart return

            if self.state == GameState.MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN: self.start_game()
                    if event.key == pygame.K_c: self.state = GameState.CONTROLS
            
            elif self.state == GameState.CONTROLS:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_c: 
                        # Return to where we came from
                        if self.p1 is None: self.state = GameState.MENU
                        else: self.state = GameState.PLAYING

            elif self.state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN:
                    # P1 Controls
                    # *** CHANGED E -> B ***
                    if event.key == pygame.K_b: self.p1_interact()
                    if event.key == pygame.K_q: self.state = GameState.CRAFTING_MENU
                    if event.key == pygame.K_TAB: self.p1.cycle_hotbar()
                    if event.key == pygame.K_m: self.state = GameState.MAP_VIEW
                    if event.key == pygame.K_c: self.state = GameState.CONTROLS
                    
                    # P2 Controls
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN: self.p2_interact()
                    if event.key == pygame.K_p: self.state = GameState.UNLOCK_MENU
                    if event.key == pygame.K_o: self.p2_build_totem() # P2 Build
                    if event.key == pygame.K_l: self.p2_replant()

            elif self.state == GameState.MAP_VIEW:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m or event.key == pygame.K_ESCAPE: self.state = GameState.PLAYING

            elif self.state == GameState.UNLOCK_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p: self.state = GameState.PLAYING
                    # Numeric keys to unlock
                    if event.key == pygame.K_1: self.try_unlock("inventory")
                    if event.key == pygame.K_2: self.try_unlock("mining")
                    if event.key == pygame.K_3: self.try_unlock("crafting")
                    if event.key == pygame.K_4: self.try_unlock("smelting")
                    if event.key == pygame.K_5: self.try_unlock("automation")
                    if event.key == pygame.K_6: self.try_unlock("advanced")
                    if event.key == pygame.K_7: self.try_unlock("druidry")

            elif self.state == GameState.CRAFTING_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q: self.state = GameState.PLAYING
                    recipe_keys = list(RECIPES.keys())
                    if event.key >= pygame.K_1 and event.key <= pygame.K_9:
                        idx = event.key - pygame.K_1
                        if idx < len(recipe_keys):
                            self.craft(recipe_keys[idx])
                        # Handle 0 key for 10th item
                    if event.key == pygame.K_0 and len(recipe_keys) >= 10:
                        self.craft(recipe_keys[9])

        if self.state == GameState.PLAYING:
            self.p1.update(keys, self.world.width*TILE_SIZE, self.world.height*TILE_SIZE)
            self.p2.update(keys, self.world.width*TILE_SIZE, self.world.height*TILE_SIZE)

    # --- P1 ACTIONS ---
    def p1_interact(self):
        if not self.unlocks.can_do("inventory"):
            self.notify("Unlock Backpack first!", RED); return

        tx = int(self.p1.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p1.interact_rect.centery // TILE_SIZE)
        
        # 1. Check Building Interaction (Take items)
        b = self.world.get_building(tx, ty)
        if b:
            for item, amt in list(b.inventory.items.items()):
                b.inventory.remove(item, amt)
                self.p1.inventory.add(item, amt)
                self.notify(f"Took {amt} {item}")
                return 
            return # If building empty, do nothing else

        # 2. Check Tile Interaction (Mining/Chopping)
        t_type = self.world.get_tile_type(tx, ty)
        if t_type and t_type != TileType.GRASS and t_type != TileType.SAND:
            if t_type == TileType.TREE:
                self.p1.inventory.add("wood", 1)
                self.world.set_tile_type(tx, ty, TileType.GRASS)
                self.notify("Chopped Wood")
                return

            if self.unlocks.can_do("mining"):
                res_map = {
                    TileType.STONE: "stone", TileType.ORE_IRON: "ore_iron",
                    TileType.ORE_COPPER: "ore_copper", TileType.ORE_COAL: "coal",
                    TileType.ORE_GOLD: "ore_gold"
                }
                if t_type in res_map:
                    self.p1.inventory.add(res_map[t_type], 1)
                    self.world.set_tile_type(tx, ty, TileType.GRASS)
                    self.notify(f"Mined {res_map[t_type]}")
            else:
                self.notify("Need Mining Pick!", RED)
            return

        # 3. Place Building from Hotbar
        selected = self.p1.get_selected_item()
        if selected and selected in ["furnace", "drill", "conveyor", "assembler"]:
             # Check unlocks
             if selected == "furnace" and not self.unlocks.can_do("smelting"): return
             if (selected == "drill" or selected == "conveyor") and not self.unlocks.can_do("automation"): return
             if selected == "assembler" and not self.unlocks.can_do("advanced"): return
             
             self.place_building(tx, ty, selected, self.p1)

    def place_building(self, x, y, b_type, player):
        if (x, y) not in self.world.buildings and self.world.get_tile_type(x,y) != TileType.WATER:
            if player.inventory.remove(b_type, 1):
                self.world.buildings[(x, y)] = Building(x, y, b_type, player.facing)
                self.notify(f"Placed {b_type}")

    def craft(self, item_key):
        if item_key == "totem": return # P1 cant craft totems
        recipe = RECIPES[item_key]
        
        # Check inputs
        for req, amt in recipe["inputs"].items():
            if not self.p1.inventory.has(req, amt):
                self.notify("Missing materials!", RED); return
        
        # Craft
        for req, amt in recipe["inputs"].items():
            self.p1.inventory.remove(req, amt)
        self.p1.inventory.add(item_key, recipe["output"])
        self.notify(f"Crafted {item_key}!")

    # --- P2 ACTIONS ---
    def p2_interact(self):
        tx = int(self.p2.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p2.interact_rect.centery // TILE_SIZE)
        t_type = self.world.get_tile_type(tx, ty)
        
        # Gather Essence
        if t_type == TileType.ESSENCE:
            pts = random.randint(15, 30)
            self.unlocks.points += pts
            self.world.set_tile_type(tx, ty, TileType.GRASS)
            self.notify(f"P2: +{pts} Essence", GOLD)
        
        # Clear/Enrich Trees
        elif t_type == TileType.TREE:
            self.unlocks.points += 5
            self.world.set_tile_type(tx, ty, TileType.GRASS)
            self.notify("P2 Cleared Tree (+5 pts)", GREEN)

        # Transmute Stone
        elif t_type == TileType.STONE and self.unlocks.points >= 10:
            self.unlocks.points -= 10
            rnd = random.random()
            new_t = TileType.ORE_IRON
            if rnd < 0.3: new_t = TileType.ORE_COPPER
            elif rnd < 0.4: new_t = TileType.ORE_COAL
            self.world.set_tile_type(tx, ty, new_t)
            self.notify("P2: Transmuted Stone", PURPLE)

    def p2_replant(self):
        tx = int(self.p2.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p2.interact_rect.centery // TILE_SIZE)
        t_type = self.world.get_tile_type(tx, ty)

        if t_type == TileType.GRASS and self.unlocks.points >= 5:
            self.unlocks.points -= 5
            self.world.set_tile_type(tx, ty, TileType.TREE)
            self.notify("P2: Replanted Tree", GREEN)

    def p2_build_totem(self):
        if not self.unlocks.can_do("druidry"): 
            self.notify("Unlock Nature Totem first!", RED); return
        
        tx = int(self.p2.interact_rect.centerx // TILE_SIZE)
        ty = int(self.p2.interact_rect.centery // TILE_SIZE)
        
        if (tx, ty) not in self.world.buildings and self.unlocks.points >= 50:
            self.unlocks.points -= 50
            self.world.buildings[(tx, ty)] = Building(tx, ty, "totem", "DOWN")
            self.notify("P2: Summoned Totem", GOLD)
        elif self.unlocks.points < 50:
            self.notify("Need 50 Essence", RED)

    def try_unlock(self, key):
        if self.unlocks.purchase(key):
            self.notify(f"UNLOCKED: {key.upper()}!", GREEN)
        else:
            self.notify("Cannot Buy (Points/Already Owned)", RED)

    def notify(self, msg, color=WHITE):
        self.notifications.append([msg, color, 120])

    # --- RENDERING ---
    def render_world(self, surface, cam, player):
        surface.fill(BLACK)
        sx = max(0, cam[0] // TILE_SIZE)
        sy = max(0, cam[1] // TILE_SIZE)
        ex = min(self.world.width, sx + (HALF_WIDTH // TILE_SIZE) + 2)
        ey = min(self.world.height, sy + (SCREEN_HEIGHT // TILE_SIZE) + 2)

        for y in range(sy, ey):
            for x in range(sx, ex):
                t = self.world.tiles.get((x,y))
                if t:
                    r = t.rect.move(-cam[0], -cam[1])
                    pygame.draw.rect(surface, t.base_color, r)
                    # Details
                    if t.type == TileType.TREE: pygame.draw.circle(surface, TREE_GREEN, r.center, 12)
                    elif t.type == TileType.ORE_IRON: pygame.draw.circle(surface, (180, 140, 140), r.center, 6)
                    elif t.type == TileType.ORE_COPPER: pygame.draw.circle(surface, (200, 100, 50), r.center, 6)
                    elif t.type == TileType.ORE_GOLD: pygame.draw.circle(surface, GOLD, r.center, 6)
                    elif t.type == TileType.ORE_COAL: pygame.draw.circle(surface, COAL_BLACK, r.center, 7)
                    elif t.type == TileType.ESSENCE:
                        pulse = 5 + math.sin(pygame.time.get_ticks()*0.01)*2
                        pygame.draw.circle(surface, GOLD, r.center, pulse)

        for b in self.world.buildings.values():
            if sx <= b.x <= ex and sy <= b.y <= ey:
                b.render(surface, cam)

        self.p1.render(surface, cam)
        self.p2.render(surface, cam)

    def draw_hud(self):
        # *** FIX START: Prevent crash if player not initialized ***
        if self.p1 is None: return 
        # *** FIX END ***

        # Top Bar
        pygame.draw.rect(self.screen, (20, 20, 30), (0, 0, SCREEN_WIDTH, 40))
        # *** UPDATED STRING E -> B ***
        t1 = self.font.render(f"P1 (Engineer) | TAB: Cycle Item | Q: Craft | B: Interact", True, BLUE)
        self.screen.blit(t1, (10, 10))
        t2 = self.font.render(f"P2 (Druid): {self.unlocks.points} Essence | P: Unlocks | O: Totem | L: Plant", True, GREEN)
        self.screen.blit(t2, (HALF_WIDTH + 10, 10))

        # P1 Hotbar (Bottom Left)
        items = self.p1.inventory.get_list()
        if items:
            bar_w = len(items) * 40
            pygame.draw.rect(self.screen, (0, 0, 0, 150), (10, SCREEN_HEIGHT - 50, bar_w + 10, 45))
            for i, item in enumerate(items):
                col = WHITE if i == self.p1.hotbar_index else GRAY
                pygame.draw.rect(self.screen, col, (15 + i*40, SCREEN_HEIGHT - 45, 36, 36), 2)
                # Shorten names for HUD
                short = item[:3].upper()
                txt = self.font.render(short, True, col)
                self.screen.blit(txt, (18 + i*40, SCREEN_HEIGHT - 35))
                # Count
                cnt = self.p1.inventory.items[item]
                num = self.font.render(str(cnt), True, WHITE)
                self.screen.blit(num, (18 + i*40, SCREEN_HEIGHT - 20))

        # Notifications
        y = 50
        for n in self.notifications[:]:
            txt = self.font.render(n[0], True, n[1])
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, y))
            y += 20
            n[2] -= 1
            if n[2] <= 0: self.notifications.remove(n)

    def draw_menus(self):
        if self.state == GameState.CONTROLS:
            self.screen.fill((20, 25, 30))
            lines = [
                "CONTROLS",
                "",
                "PLAYER 1 (The Engineer - Blue)",
                "Move: W A S D",
                # *** UPDATED STRING E -> B ***
                "Interact/Mine/Take: B",
                "Open Crafting: Q",
                "Cycle Selected Item: TAB",
                "Place Selected Item: B (on empty ground)",
                "Open Map: M",
                "",
                "PLAYER 2 (The Druid - Green)",
                "Move: ARROWS",
                "Interact/Gather Essence: SPACE or ENTER",
                "Open Unlocks: P",
                "Build Nature Totem: O",
                "Replant Tree: L",
                "",
                "Press C or ESC to Return"
            ]
            y = 50
            for line in lines:
                c = WHITE
                if "PLAYER 1" in line: c = BLUE
                if "PLAYER 2" in line: c = GREEN
                t = self.font.render(line, True, c)
                self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, y))
                y += 30

        elif self.state == GameState.MAP_VIEW:
            if self.minimap_surface:
                scale = min(SCREEN_WIDTH / self.world.width, SCREEN_HEIGHT / self.world.height)
                w, h = int(self.world.width * scale), int(self.world.height * scale)
                scaled_map = pygame.transform.scale(self.minimap_surface, (w, h))
                
                ox = (SCREEN_WIDTH - w) // 2
                oy = (SCREEN_HEIGHT - h) // 2
                self.screen.fill((10,10,10))
                self.screen.blit(scaled_map, (ox, oy))
                
                # Draw Players
                p1x = int(self.p1.rect.centerx / (self.world.width*TILE_SIZE) * w)
                p1y = int(self.p1.rect.centery / (self.world.height*TILE_SIZE) * h)
                pygame.draw.circle(self.screen, BLUE, (ox+p1x, oy+p1y), 5)
                
                p2x = int(self.p2.rect.centerx / (self.world.width*TILE_SIZE) * w)
                p2y = int(self.p2.rect.centery / (self.world.height*TILE_SIZE) * h)
                pygame.draw.circle(self.screen, GREEN, (ox+p2x, oy+p2y), 5)
                
                txt = self.title_font.render("WORLD MAP (M to close)", True, WHITE)
                self.screen.blit(txt, (20, 20))

        elif self.state == GameState.UNLOCK_MENU:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0, 230))
            self.screen.blit(overlay, (0,0))
            header = self.title_font.render("DRUIDIC KNOWLEDGE (P2)", True, GOLD)
            self.screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, 50))
            y = 120
            idx = 1
            for k, v in self.unlocks.unlocks.items():
                col = GREEN if v["unlocked"] else (WHITE if self.unlocks.points >= v["cost"] else GRAY)
                txt = f"[{idx}] {v['name']} ({v['cost']} pts): {v['desc']}"
                surf = self.font.render(txt, True, col)
                self.screen.blit(surf, (SCREEN_WIDTH//2 - surf.get_width()//2, y))
                y += 50
                idx += 1

        elif self.state == GameState.CRAFTING_MENU:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0, 230))
            self.screen.blit(overlay, (0,0))
            header = self.title_font.render("ENGINEER ASSEMBLY (P1)", True, BLUE)
            self.screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, 50))
            y = 120
            idx = 1
            for k, v in RECIPES.items():
                if v["type"] == "nature": continue 
                ins = ", ".join([f"{amt} {n}" for n, amt in v["inputs"].items()])
                txt = f"[{idx}] {k.upper()} (x{v['output']}) requires: {ins}"
                affordable = True
                for n, amt in v["inputs"].items():
                    if not self.p1.inventory.has(n, amt): affordable = False
                col = WHITE if affordable else GRAY
                surf = self.font.render(txt, True, col)
                self.screen.blit(surf, (SCREEN_WIDTH//2 - surf.get_width()//2, y))
                y += 40
                idx += 1
            
            hint = self.font.render("Press 1-9 to Craft | Q to Close", True, SKY_BLUE)
            self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 50))

    def run(self):
        while True:
            self.handle_input()
            if self.state == GameState.PLAYING:
                for b in self.world.buildings.values():
                    b.update(self.world)
                self.cam1[0] = self.p1.rect.centerx - HALF_WIDTH//2
                self.cam1[1] = self.p1.rect.centery - SCREEN_HEIGHT//2
                self.cam2[0] = self.p2.rect.centerx - HALF_WIDTH//2
                self.cam2[1] = self.p2.rect.centery - SCREEN_HEIGHT//2

            if self.state == GameState.MENU:
                self.screen.fill((10, 10, 20))
                t = self.title_font.render("ECO-FACTORY", True, WHITE)
                self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 200))
                
                btn_text = "Press ENTER to Start"
                b1 = self.font.render(btn_text, True, SKY_BLUE)
                self.screen.blit(b1, (SCREEN_WIDTH//2 - b1.get_width()//2, 300))
                
                btn_ctrl = "Press C for Controls"
                b2 = self.font.render(btn_ctrl, True, GOLD)
                self.screen.blit(b2, (SCREEN_WIDTH//2 - b2.get_width()//2, 350))

            elif self.state in [GameState.CONTROLS, GameState.MAP_VIEW, GameState.UNLOCK_MENU, GameState.CRAFTING_MENU]:
                 if self.state == GameState.MAP_VIEW:
                     self.draw_menus()
                 else:
                    self.draw_hud() 
                    self.draw_menus()
            
            else:
                s1 = pygame.Surface((HALF_WIDTH, SCREEN_HEIGHT))
                s2 = pygame.Surface((HALF_WIDTH, SCREEN_HEIGHT))
                self.render_world(s1, self.cam1, self.p1)
                self.render_world(s2, self.cam2, self.p2)
                self.screen.blit(s1, (0,0))
                self.screen.blit(s2, (HALF_WIDTH, 0))
                pygame.draw.line(self.screen, BLACK, (HALF_WIDTH, 0), (HALF_WIDTH, SCREEN_HEIGHT), 4)
                self.draw_hud()
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    GameEngine().run()