import pygame
import random
import sys
import math

# --- CONFIGURATION ---
SCREEN_WIDTH = 1180
SCREEN_HEIGHT = 720
TILE_SIZE = 32
FPS = 60

# Colors
C_BG = (20, 20, 20)
C_GRID = (50, 50, 50)
C_WHITE = (255, 255, 255)
C_GREEN = (0, 200, 0)
C_RED = (200, 0, 0)
C_BLUE = (0, 100, 200)
C_ORANGE = (255, 140, 0)
C_UI_BG = (60, 60, 60)
C_UI_TITLE = (40, 40, 80)
C_UI_BORDER = (200, 200, 200)
C_SLOT = (40, 40, 40)
C_SLOT_HOVER = (80, 80, 90)

# --- ASSET GENERATOR ---
def draw_icon(surface, name):
    w, h = surface.get_size()
    if name == 'wood': pygame.draw.rect(surface, (139, 69, 19), (4,4,w-8,h-8))
    elif name == 'stone': pygame.draw.circle(surface, (128, 128, 128), (w//2, h//2), w//2-4)
    elif name == 'iron_ore': 
        pygame.draw.circle(surface, (128, 128, 128), (w//2, h//2), w//2-4)
        pygame.draw.circle(surface, (183, 65, 14), (w//2, h//2), w//4)
    elif name == 'copper_ore': 
        pygame.draw.circle(surface, (128, 128, 128), (w//2, h//2), w//2-4)
        pygame.draw.circle(surface, C_ORANGE, (w//2, h//2), w//4)
    elif name == 'iron_bar': pygame.draw.rect(surface, (200, 200, 200), (6, 10, w-12, h-20))
    elif name == 'copper_bar': pygame.draw.rect(surface, C_ORANGE, (6, 10, w-12, h-20))

# --- CLASSES ---

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type, group):
        super().__init__(group)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.tile_type = tile_type
        if tile_type == 'grass': self.image.fill((34, 139, 34))
        elif tile_type == 'sand': self.image.fill((238, 214, 175))
        elif tile_type == 'water': self.image.fill((0, 105, 148))
        else: self.image.fill((255, 0, 255))
        self.rect = self.image.get_rect(topleft=(x*TILE_SIZE, y*TILE_SIZE))

class Resource(pygame.sprite.Sprite):
    def __init__(self, x, y, res_type, group):
        super().__init__(group)
        self.res_type = res_type
        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        cx, cy = 10, 10
        if res_type == 'rock': 
            pygame.draw.circle(self.image, (100,100,100), (cx,cy), 10)
            self.yield_item = 'stone'
        elif res_type == 'tree': 
            pygame.draw.circle(self.image, (0,100,0), (cx,cy), 10)
            self.yield_item = 'wood'
        elif res_type == 'iron_ore':
            pygame.draw.circle(self.image, (183, 65, 14), (cx,cy), 10)
            self.yield_item = 'iron_ore'
        elif res_type == 'copper_ore':
            pygame.draw.circle(self.image, C_ORANGE, (cx,cy), 10)
            self.yield_item = 'copper_ore'
        self.rect = self.image.get_rect(center=(x*TILE_SIZE+16, y*TILE_SIZE+16))

class Building(pygame.sprite.Sprite):
    def __init__(self, x, y, b_type, group):
        super().__init__(group)
        self.b_type = b_type
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect(topleft=(x*TILE_SIZE, y*TILE_SIZE))
        
        self.input_slot = None 
        self.output_slot = None
        
        self.energy = 0
        self.max_energy = 500
        self.process_timer = 0
        self.process_max = 120
        self.being_charged = False 
        
        if b_type == 'furnace':
            self.color = (150, 50, 50)
            self.valid_inputs = ['iron_ore', 'copper_ore']
        elif b_type == 'solar':
            self.color = (50, 50, 150)
            self.valid_inputs = []
        elif b_type == 'science_lab':
            self.color = (200, 200, 255)
            self.valid_inputs = ['iron_bar', 'copper_bar']

        self.redraw()

    def redraw(self):
        self.image.fill(self.color)
        if self.energy > 0:
            pct = self.energy / self.max_energy
            pygame.draw.rect(self.image, (0, 255, 0), (0, 28, 32*pct, 4))
        if self.process_timer > 0:
            pygame.draw.circle(self.image, (255, 255, 0), (16, 16), 5)

    def update(self, global_state):
        if self.b_type == 'furnace':
            if self.energy > 0 and self.input_slot:
                inp_name = self.input_slot['name']
                if inp_name in self.valid_inputs:
                    self.process_timer += 1
                    speed_mod = 1.5 if global_state.upgrades['efficiency'] else 1.0
                    self.energy -= (0.5 / speed_mod) 
                    target = self.process_max / speed_mod
                    if self.process_timer >= target:
                        out_name = inp_name.replace('ore', 'bar')
                        if self.output_slot is None:
                            self.output_slot = {'name': out_name, 'count': 1}
                            self.consume_input()
                        elif self.output_slot['name'] == out_name and self.output_slot['count'] < 64:
                            self.output_slot['count'] += 1
                            self.consume_input()
                        self.process_timer = 0
                else: self.process_timer = 0
            else: self.process_timer = 0
        
        elif self.b_type == 'science_lab':
            if self.energy > 0 and self.input_slot:
                self.energy -= 0.5
                self.process_timer += 1
                if self.process_timer >= 180: 
                    global_state.science_points += 1
                    self.consume_input()
                    self.process_timer = 0
                    global_state.add_message("Produced 1 Science Data!")

        self.redraw()

    def consume_input(self):
        self.input_slot['count'] -= 1
        if self.input_slot['count'] <= 0:
            self.input_slot = None

# --- UI CLASSES ---

class Slot:
    def __init__(self, x, y, size=40):
        # Coordinates are RELATIVE to the window!
        self.rel_x = x
        self.rel_y = y
        self.w = size
        self.h = size
        self.rect = pygame.Rect(x, y, size, size)
        self.item = None 
        self.hovered = False

    def update_rect(self, win_x, win_y):
        self.rect.x = win_x + self.rel_x
        self.rect.y = win_y + self.rel_y

    def draw(self, surface):
        col = C_SLOT_HOVER if self.hovered else C_SLOT
        pygame.draw.rect(surface, col, self.rect)
        pygame.draw.rect(surface, C_UI_BORDER, self.rect, 2)
        if self.item:
            icon_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
            draw_icon(icon_surf, self.item['name'])
            surface.blit(icon_surf, (self.rect.x+8, self.rect.y+8))
            font = pygame.font.SysFont("Arial", 12, bold=True)
            txt = font.render(str(self.item['count']), True, C_WHITE)
            surface.blit(txt, (self.rect.right - txt.get_width()-2, self.rect.bottom - txt.get_height()))

class DraggableWindow:
    def __init__(self, title, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.title = title
        self.dragging = False
        self.drag_offset = (0, 0)
        self.visible = False
        self.title_bar = pygame.Rect(x, y, w, 30)
        self.font = pygame.font.SysFont("Arial", 16, bold=True)

    def handle_event(self, event):
        if not self.visible: return False
        
        mx, my = pygame.mouse.get_pos()
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Check Title Bar click
                if self.title_bar.collidepoint(mx, my):
                    self.dragging = True
                    self.drag_offset = (mx - self.rect.x, my - self.rect.y)
                    return True # Captured event
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mx - self.drag_offset[0]
                self.rect.y = my - self.drag_offset[1]
                # Clamp to screen
                self.rect.x = max(0, min(SCREEN_WIDTH-self.rect.width, self.rect.x))
                self.rect.y = max(0, min(SCREEN_HEIGHT-self.rect.height, self.rect.y))
                self.title_bar.x = self.rect.x
                self.title_bar.y = self.rect.y
                self.on_move() # Callback for children to update slot positions

        return False

    def on_move(self):
        pass # Override in children

    def draw_window(self, screen):
        # Draw Body
        pygame.draw.rect(screen, C_UI_BG, self.rect)
        pygame.draw.rect(screen, C_UI_BORDER, self.rect, 2)
        # Draw Title Bar
        pygame.draw.rect(screen, C_UI_TITLE, self.title_bar)
        pygame.draw.rect(screen, C_UI_BORDER, self.title_bar, 2)
        # Draw Text
        txt = self.font.render(self.title, True, C_WHITE)
        screen.blit(txt, (self.rect.x + 10, self.rect.y + 5))
        # Draw Close 'X'
        pygame.draw.line(screen, C_WHITE, (self.rect.right-20, self.rect.y+5), (self.rect.right-5, self.rect.y+20), 2)
        pygame.draw.line(screen, C_WHITE, (self.rect.right-5, self.rect.y+5), (self.rect.right-20, self.rect.y+20), 2)

    def is_close_button_clicked(self, pos):
        # Simple check for top right corner
        cr = pygame.Rect(self.rect.right-25, self.rect.y, 25, 30)
        return cr.collidepoint(pos)

class InventoryWindow(DraggableWindow):
    def __init__(self, player):
        super().__init__("INVENTORY & MACHINE", 100, 100, 400, 350)
        self.player = player
        self.target_machine = None
        
        # Player Slots
        self.inv_slots = []
        for r in range(4):
            for c in range(8):
                if len(self.inv_slots) < 30:
                    s = Slot(20 + c*44, 150 + r*44)
                    self.inv_slots.append(s)
        
        # Machine Slots
        self.mach_in = Slot(80, 60, 50)
        self.mach_out = Slot(250, 60, 50)
        
        self.on_move() # Init positions

    def on_move(self):
        for s in self.inv_slots: s.update_rect(self.rect.x, self.rect.y)
        self.mach_in.update_rect(self.rect.x, self.rect.y)
        self.mach_out.update_rect(self.rect.x, self.rect.y)

    def sync(self):
        # Sync Player
        idx = 0
        for name, count in self.player.inventory.items():
            if count > 0:
                self.inv_slots[idx].item = {'name': name, 'count': count}
                idx += 1
        for i in range(idx, len(self.inv_slots)): self.inv_slots[i].item = None

        # Sync Machine
        if self.target_machine:
            self.mach_in.item = self.target_machine.input_slot
            self.mach_out.item = self.target_machine.output_slot

    def write_back(self):
        # Rebuild Player Inv
        new_inv = {'wood': 0, 'stone': 0, 'iron_ore': 0, 'copper_ore': 0, 'iron_bar': 0, 'copper_bar': 0}
        for s in self.inv_slots:
            if s.item:
                n, c = s.item['name'], s.item['count']
                new_inv[n] = new_inv.get(n, 0) + c
        self.player.inventory = new_inv
        
        # Machine
        if self.target_machine:
            self.target_machine.input_slot = self.mach_in.item
            self.target_machine.output_slot = self.mach_out.item

    def handle_click_content(self, cursor_item):
        mx, my = pygame.mouse.get_pos()
        
        for s in self.inv_slots:
            if s.rect.collidepoint(mx, my):
                return self.swap_logic(s, cursor_item, False)

        if self.target_machine:
            if self.mach_in.rect.collidepoint(mx, my):
                res = self.swap_logic(self.mach_in, cursor_item, True)
                self.write_back()
                return res
            if self.mach_out.rect.collidepoint(mx, my):
                # Output take-only/stack logic
                if not cursor_item and self.mach_out.item:
                    cursor_item = self.mach_out.item
                    self.mach_out.item = None
                    self.write_back()
                    return cursor_item
                elif cursor_item and self.mach_out.item:
                    if cursor_item['name'] == self.mach_out.item['name']:
                         cursor_item['count'] += self.mach_out.item['count']
                         self.mach_out.item = None
                         self.write_back()
                         return cursor_item
        return cursor_item

    def swap_logic(self, slot, cursor, is_machine):
        if not cursor and slot.item: # Pick up
            cursor = slot.item
            slot.item = None
        elif cursor and not slot.item: # Place
            slot.item = cursor
            cursor = None
        elif cursor and slot.item: # Stack/Swap
            if cursor['name'] == slot.item['name']:
                slot.item['count'] += cursor['count']
                cursor = None
            else:
                temp = slot.item
                slot.item = cursor
                cursor = temp
        
        if not is_machine: self.write_back()
        return cursor

    def draw(self, screen):
        self.sync()
        self.draw_window(screen)
        
        mx, my = pygame.mouse.get_pos()
        
        # Inv Slots
        for s in self.inv_slots:
            s.hovered = s.rect.collidepoint(mx, my)
            s.draw(screen)
            
        # Machine
        if self.target_machine:
            font = pygame.font.SysFont("Arial", 16, bold=True)
            lbl = font.render(self.target_machine.b_type.upper(), True, C_WHITE)
            screen.blit(lbl, (self.rect.x+20, self.rect.y+40))
            
            self.mach_in.hovered = self.mach_in.rect.collidepoint(mx, my)
            self.mach_out.hovered = self.mach_out.rect.collidepoint(mx, my)
            self.mach_in.draw(screen)
            self.mach_out.draw(screen)
            
            # Arrow
            sx, sy = self.rect.x + 160, self.rect.y + 80
            pygame.draw.polygon(screen, C_WHITE, [(sx, sy-10), (sx+30, sy), (sx, sy+10)])

class RecipeWindow(DraggableWindow):
    def __init__(self, game_ref):
        super().__init__("CONSTRUCTION", 550, 100, 500, 400)
        self.game = game_ref
        self.recipes = [
            ('furnace', {'wood': 5, 'stone': 5}),
            ('solar', {'iron_bar': 5, 'copper_bar': 5}),
            ('science_lab', {'stone': 10, 'iron_bar': 2})
        ]
        self.buttons = [] # List of Rects relative to window
        for i in range(len(self.recipes)):
            self.buttons.append(pygame.Rect(10, 50 + i*50, 480, 40))

    def handle_click_content(self, cursor_item):
        mx, my = pygame.mouse.get_pos()
        # Convert mouse to relative
        rel_x = mx - self.rect.x
        rel_y = my - self.rect.y
        
        for i, btn in enumerate(self.buttons):
            if btn.collidepoint(rel_x, rel_y):
                name, cost = self.recipes[i]
                # Check cost
                can = True
                for r, c in cost.items():
                    if self.game.player.inventory.get(r, 0) < c: can = False
                
                if can:
                    for r, c in cost.items(): self.game.player.inventory[r] -= c
                    gx, gy = round(self.game.player.rect.x/TILE_SIZE), round(self.game.player.rect.y/TILE_SIZE)
                    Building(gx, gy, name, self.game.buildings)
                    self.game.add_message(f"Built {name}!")
                else:
                    self.game.add_message("Missing Resources!")
        return cursor_item # Pass through

    def draw(self, screen):
        self.draw_window(screen)
        font = pygame.font.SysFont("Courier New", 14, bold=True)
        
        for i, (name, cost) in enumerate(self.recipes):
            # Draw button background relative to window
            r = self.buttons[i]
            abs_r = pygame.Rect(self.rect.x + r.x, self.rect.y + r.y, r.w, r.h)
            
            pygame.draw.rect(screen, C_SLOT, abs_r)
            pygame.draw.rect(screen, C_UI_BORDER, abs_r, 1)
            
            name_txt = font.render(name.upper(), True, C_ORANGE)
            screen.blit(name_txt, (abs_r.x + 10, abs_r.y + 12))
            
            c_str = ", ".join([f"{v} {k}" for k,v in cost.items()])
            c_txt = font.render(c_str, True, (200, 200, 200))
            screen.blit(c_txt, (abs_r.x + 130, abs_r.y + 12))

# --- GAME ENGINE ---

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("TerraSky: Desktop Window System")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier New", 14, bold=True)
        
        self.map_w = 80
        self.map_h = 80
        self.tiles = pygame.sprite.Group()
        self.resources = pygame.sprite.Group()
        self.buildings = pygame.sprite.Group()
        self.player_grp = pygame.sprite.Group()
        self.tile_map = {}
        
        self.generate_world()
        
        px, py = (self.map_w*TILE_SIZE)//2, (self.map_h*TILE_SIZE)//2
        self.player = type('Player', (), {})()
        self.player.rect = pygame.Rect(px, py, 20, 20)
        self.player.image = pygame.Surface((20,20)); self.player.image.fill(C_WHITE)
        self.player.inventory = {'wood': 10, 'stone': 10, 'iron_ore': 0, 'copper_ore': 0, 'iron_bar': 0, 'copper_bar': 0}
        self.player_sprite = pygame.sprite.Sprite(self.player_grp)
        self.player_sprite.image = self.player.image
        self.player_sprite.rect = self.player.rect
        
        self.role = 'GROUND'
        self.messages = []
        self.global_energy = 100
        self.science_points = 0
        self.upgrades = {'regen': False, 'capacity': False, 'efficiency': False}

        self.ui_sky_tree_open = False
        
        # Windows System
        self.win_inv = InventoryWindow(self.player)
        self.win_recipe = RecipeWindow(self)
        self.windows = [self.win_inv, self.win_recipe] # List allows z-order (last = top)
        
        self.held_item = None 
        
        # Sky Camera
        self.sky_zoom = 1.0
        self.sky_cam_pos = [px, py]

    def generate_world(self):
        print("Generating...")
        seed = random.randint(0, 100)
        for x in range(self.map_w):
            for y in range(self.map_h):
                dx = x - self.map_w // 2
                dy = y - self.map_h // 2
                dist = math.sqrt(dx*dx + dy*dy)
                island_mask = 1.0 - (dist / (self.map_w * 0.4)) 
                noise_val = random.uniform(-0.2, 0.2)
                height = island_mask + noise_val
                
                t_type = 'water'
                if height > 0.1: t_type = 'sand'
                if height > 0.4: t_type = 'grass'
                
                Tile(x, y, t_type, self.tiles)
                self.tile_map[(x,y)] = t_type
                
                if t_type != 'water':
                    if random.random() < 0.1: Resource(x, y, 'tree', self.resources)
                    elif random.random() < 0.05:
                        rnd = random.random()
                        if rnd < 0.5: Resource(x, y, 'rock', self.resources)
                        elif rnd < 0.8: Resource(x, y, 'iron_ore', self.resources)
                        else: Resource(x, y, 'copper_ore', self.resources)

    def add_message(self, txt):
        self.messages.append([txt, 120])

    def get_ground_camera(self, target):
        x = -target.rect.x + SCREEN_WIDTH // 2
        y = -target.rect.y + SCREEN_HEIGHT // 2
        return (x, y)

    def input(self):
        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            
            # 1. Handle Window Dragging First (Top-level)
            event_handled = False
            
            if event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
                # Iterate windows in reverse order (Top to Bottom) for clicks
                for win in reversed(self.windows):
                    if win.handle_event(event):
                        # Bring to front
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            self.windows.remove(win)
                            self.windows.append(win)
                            
                            # Check close button
                            if win.is_close_button_clicked(event.pos):
                                win.visible = False
                        event_handled = True
                        break # Stop propagation if window caught it
            
            if event_handled: continue

            # 2. Standard Input
            if event.type == pygame.MOUSEWHEEL:
                if self.role == 'SKY':
                    self.sky_zoom += event.y * 0.1
                    self.sky_zoom = max(0.5, min(3.0, self.sky_zoom))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.role = 'SKY' if self.role == 'GROUND' else 'GROUND'
                    self.add_message(f"Role: {self.role}")
                    # Hide windows in Sky? Or allow them? Let's hide them for immersion
                    if self.role == 'SKY':
                        for w in self.windows: w.visible = False

                if self.role == 'GROUND':
                    if event.key == pygame.K_r: 
                        self.win_recipe.visible = not self.win_recipe.visible
                        if self.win_recipe.visible: # Bring to front
                            self.windows.remove(self.win_recipe)
                            self.windows.append(self.win_recipe)
                    
                    if event.key == pygame.K_e:
                        if self.win_inv.visible:
                            self.win_inv.visible = False
                        else:
                            # Check building
                            hits = pygame.sprite.spritecollide(self.player_sprite, self.buildings, False)
                            if hits:
                                self.win_inv.target_machine = hits[0]
                            else:
                                self.win_inv.target_machine = None
                            self.win_inv.visible = True
                            self.windows.remove(self.win_inv)
                            self.windows.append(self.win_inv)

                    if event.key == pygame.K_SPACE:
                        hits = pygame.sprite.spritecollide(self.player_sprite, self.resources, True)
                        for h in hits:
                            self.player.inventory[h.yield_item] += 1
                            self.add_message(f"+1 {h.yield_item}")

                if self.role == 'SKY':
                    if event.key == pygame.K_3: self.input_sky_beam(mx, my)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: self.handle_click(mx, my)
        
        # Mouse Pan in Sky
        if self.role == 'SKY':
            spd = 10 / self.sky_zoom
            if mx < 50: self.sky_cam_pos[0] -= spd
            if mx > SCREEN_WIDTH - 50: self.sky_cam_pos[0] += spd
            if my < 50: self.sky_cam_pos[1] -= spd
            if my > SCREEN_HEIGHT - 50: self.sky_cam_pos[1] += spd

        # Movement blocked if interacting with top window?
        # For fluid gameplay, we allow movement unless dragging
        dragging = any(w.dragging for w in self.windows)
        if self.role == 'GROUND' and not dragging:
            s = 4
            if keys[pygame.K_w]: self.player.rect.y -= s
            if keys[pygame.K_s]: self.player.rect.y += s
            if keys[pygame.K_a]: self.player.rect.x -= s
            if keys[pygame.K_d]: self.player.rect.x += s
            self.player_sprite.rect = self.player.rect

    def handle_click(self, mx, my):
        # Click content of top-most visible window
        for win in reversed(self.windows):
            if win.visible and win.rect.collidepoint(mx, my):
                # We are clicking inside this window
                # Check for Close button logic again just in case (handled in events usually)
                if not win.is_close_button_clicked((mx,my)):
                    self.held_item = win.handle_click_content(self.held_item)
                return

    def input_sky_beam(self, mx, my):
        wx, wy = self.screen_to_world(mx, my)
        beam_range = 150 
        closest_building = None
        min_dist = beam_range
        
        for b in self.buildings:
            dist = ((b.rect.centerx - wx)**2 + (b.rect.centery - wy)**2)**0.5
            if dist < min_dist:
                closest_building = b
                min_dist = dist
        
        if closest_building:
            give = 5
            if self.global_energy >= give:
                closest_building.energy = min(closest_building.max_energy, closest_building.energy + give)
                self.global_energy -= give
                closest_building.being_charged = True 

    def update(self):
        self.messages = [[m, t-1] for m, t in self.messages if t > 0]
        self.buildings.update(self)
        
        regen = 0.5 if self.upgrades['regen'] else 0.1
        solars = [b for b in self.buildings if b.b_type == 'solar']
        regen += (len(solars) * 0.2)
        
        cap = 200 if self.upgrades['capacity'] else 100
        self.global_energy = min(cap, self.global_energy + regen)

    def world_to_screen(self, wx, wy):
        off_x = wx - self.sky_cam_pos[0]
        off_y = wy - self.sky_cam_pos[1]
        scr_x = (off_x * self.sky_zoom) + SCREEN_WIDTH//2
        scr_y = (off_y * self.sky_zoom) + SCREEN_HEIGHT//2
        return scr_x, scr_y

    def screen_to_world(self, sx, sy):
        off_x = (sx - SCREEN_WIDTH//2) / self.sky_zoom
        off_y = (sy - SCREEN_HEIGHT//2) / self.sky_zoom
        wx = off_x + self.sky_cam_pos[0]
        wy = off_y + self.sky_cam_pos[1]
        return wx, wy

    def draw(self):
        self.screen.fill(C_BG)
        
        if self.role == 'GROUND':
            cam_off = self.get_ground_camera(self.player_sprite)
            for t in self.tiles:
                r = t.rect.move(cam_off)
                if self.screen.get_rect().colliderect(r): self.screen.blit(t.image, r)
            for g in [self.resources, self.buildings]:
                for e in g:
                    r = e.rect.move(cam_off)
                    if self.screen.get_rect().colliderect(r): self.screen.blit(e.image, r)
            self.screen.blit(self.player_sprite.image, self.player_sprite.rect.move(cam_off))
            
            # Draw Windows (Order matters: Bottom to Top)
            for win in self.windows:
                if win.visible: win.draw(self.screen)
            
            if self.held_item:
                mx, my = pygame.mouse.get_pos()
                icon = pygame.Surface((32,32), pygame.SRCALPHA); 
                draw_icon(icon, self.held_item['name'])
                self.screen.blit(icon, (mx-16, my-16))
                
        elif self.role == 'SKY':
            self.draw_sky_view()
            if self.ui_sky_tree_open: self.draw_sky_upgrades()

        self.draw_hud()
        pygame.display.flip()

    def draw_sky_view(self):
        tl_w = self.screen_to_world(0, 0)
        br_w = self.screen_to_world(SCREEN_WIDTH, SCREEN_HEIGHT)
        vis_rect = pygame.Rect(tl_w[0], tl_w[1], br_w[0]-tl_w[0], br_w[1]-tl_w[1])
        
        tile_size_z = TILE_SIZE * self.sky_zoom
        if tile_size_z < 2: return 
        
        for t in self.tiles:
            if vis_rect.colliderect(t.rect):
                sx, sy = self.world_to_screen(t.rect.x, t.rect.y)
                r = pygame.Rect(sx, sy, tile_size_z+1, tile_size_z+1)
                col = (0,0,0)
                if t.tile_type == 'grass': col = (34, 139, 34)
                elif t.tile_type == 'sand': col = (238, 214, 175)
                elif t.tile_type == 'water': col = (0, 105, 148)
                pygame.draw.rect(self.screen, col, r)
        
        mx, my = pygame.mouse.get_pos()
        for b in self.buildings:
            if vis_rect.colliderect(b.rect):
                sx, sy = self.world_to_screen(b.rect.centerx, b.rect.centery)
                rad = 6 * self.sky_zoom
                col = C_RED
                if b.b_type == 'solar': col = C_BLUE
                elif b.energy > 0: col = C_GREEN
                
                if getattr(b, 'being_charged', False):
                    pygame.draw.line(self.screen, (0, 255, 255), (mx, my), (sx, sy), 3)
                    pygame.draw.circle(self.screen, (200, 255, 255), (sx, sy), rad + 4, 2)
                    col = (0, 255, 255)
                    b.being_charged = False 

                pygame.draw.circle(self.screen, col, (sx, sy), max(3, rad))

        sx, sy = self.world_to_screen(self.player.rect.x, self.player.rect.y)
        w, h = 20 * self.sky_zoom, 20 * self.sky_zoom
        pygame.draw.rect(self.screen, C_WHITE, (sx, sy, w, h), 2)

    def draw_sky_upgrades(self):
        # Placeholder for Sky Upgrade Tree UI (could be made into a window too!)
        pass

    def draw_hud(self):
        for i, (msg, t) in enumerate(self.messages):
            txt = self.font.render(msg, True, C_WHITE)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 100 + i*20))
        info = f"ROLE: {self.role} | ENERGY: {int(self.global_energy)}"
        if self.role == 'GROUND': info += " | [R] RECIPES | [E] INV/MACHINE | [TAB] SKY"
        else: info += " | SCROLL: ZOOM | [3] BEAM | [U] UPGRADES | [TAB] GROUND"
        pygame.draw.rect(self.screen, C_BG, (0,0,SCREEN_WIDTH, 30))
        self.screen.blit(self.font.render(info, True, C_WHITE), (10, 5))

if __name__ == "__main__":
    g = Game()
    while True:
        g.input()
        g.update()
        g.draw()
        g.clock.tick(FPS)