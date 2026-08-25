"""
Minecraft Clone in Python using Ursina Engine
A fully functional voxel game with block placing, breaking, inventory, and more.

Controls:
- WASD: Move
- Space: Jump
- Shift: Fly up (in creative mode)
- Ctrl: Fly down (in creative mode)
- Left Click: Break block
- Right Click: Place block
- 1-8: Select block type
- Tab: Toggle fly mode
- Esc: Release mouse / Pause
"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math
import wave
import struct
import io

# Sound Manager using synthesized waves to avoid external dependencies
class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            self.test_sound = self.generate_sound(440, 0.05)
        except Exception:
            self.enabled = False

    def generate_sound(self, frequency, duration, volume=0.3):
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        buf = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            val = int(volume * 32767 * (1 if math.sin(2 * math.pi * frequency * t) > 0 else -1))
            buf.extend(struct.pack('<h', val))
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(buf)
        wav_io.seek(0)
        return Audio(wav_io, autoplay=False, loop=False)

    def play_break(self):
        if not self.enabled: return
        sound = self.generate_sound(150, 0.1, 0.5)
        sound.pitch = random.uniform(0.8, 1.2)
        sound.play()

    def play_place(self):
        if not self.enabled: return
        sound = self.generate_sound(400, 0.05, 0.4)
        sound.pitch = random.uniform(1.0, 1.4)
        sound.play()

    def play_select(self):
        if not self.enabled: return
        sound = self.generate_sound(600, 0.03, 0.3)
        sound.play()

# Initialize the app
app = Ursina()
sounds = SoundManager()

# Window settings
window.title = 'Minecraft Clone'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = True
window.fps_counter.enabled = True

# Sky with day/night cycle
sky = Sky(texture='sky_sunset')
day_cycle = 0

# Ground plane (base layer)
ground = Entity(
    model='plane',
    texture='grass',
    collider='box',
    scale=(100, 1, 100),
    texture_scale=(100, 100)
)

# Block types with colors/textures and properties
block_types = {
    1: {'name': 'Grass', 'color': color.rgb(0, 155, 0), 'texture': 'grass', 'hardness': 1.0},
    2: {'name': 'Dirt', 'color': color.rgb(139, 69, 19), 'texture': 'dirt', 'hardness': 0.8},
    3: {'name': 'Stone', 'color': color.rgb(128, 128, 128), 'texture': 'white_cube', 'hardness': 2.0},
    4: {'name': 'Wood', 'color': color.rgb(101, 67, 33), 'texture': 'white_cube', 'hardness': 1.2},
    5: {'name': 'Leaves', 'color': color.rgb(34, 139, 34), 'texture': 'white_cube', 'hardness': 0.5},
    6: {'name': 'Sand', 'color': color.rgb(237, 220, 163), 'texture': 'white_cube', 'hardness': 0.6},
    7: {'name': 'Brick', 'color': color.rgb(178, 34, 34), 'texture': 'white_cube', 'hardness': 2.5},
    8: {'name': 'Snow', 'color': color.rgb(255, 250, 250), 'texture': 'white_cube', 'hardness': 0.4},
    9: {'name': 'Water', 'color': color.rgba(0, 0, 255, 180), 'texture': 'white_cube', 'transparent': True, 'hardness': 0.0},
    10: {'name': 'Lava', 'color': color.rgba(255, 69, 0, 200), 'texture': 'white_cube', 'glow': True, 'hardness': 0.0},
    11: {'name': 'Coal Ore', 'color': color.rgb(64, 64, 64), 'texture': 'white_cube', 'hardness': 2.5},
    12: {'name': 'Iron Ore', 'color': color.rgb(210, 180, 140), 'texture': 'white_cube', 'hardness': 3.0},
}

# Tool tiers with mining speed multipliers
tool_tiers = {
    'none': {'speed': 1.0, 'durability': 0},
    'wood': {'speed': 2.0, 'durability': 60},
    'stone': {'speed': 4.0, 'durability': 132},
    'iron': {'speed': 6.0, 'durability': 251},
    'diamond': {'speed': 8.0, 'durability': 1562},
}

# Crafting recipes: result -> required items
crafting_recipes = {
    (4, 4): {'wood_planks': 4},  # Wood to planks (simplified)
    ('pickaxe_wood', 1): {4: 3, 2: 2},  # Wood pickaxe: 3 wood, 2 dirt (placeholder)
    ('pickaxe_stone', 1): {3: 3, 4: 2},  # Stone pickaxe: 3 stone, 2 wood
    ('pickaxe_iron', 1): {12: 3, 4: 2},  # Iron pickaxe: 3 iron ore, 2 wood
}

current_block = 1  # Currently selected block type
current_tool = 'none'  # Current tool tier
tool_durability = 0  # Current tool durability

# Simple mobs list
mobs = []
mob_spawn_timer = 0

class Mob(Entity):
    def __init__(self, position=(0,2,0), mob_type='zombie'):
        super().__init__(
            model='cube',
            color=color.rgb(0, 255, 0) if mob_type == 'zombie' else color.rgb(255, 255, 255),
            scale=(0.8, 1.8, 0.8),
            position=position,
            collider='box'
        )
        self.mob_type = mob_type
        self.health = 10
        self.speed = 2
        mobs.append(self)
    
    def update(self):
        # Check if it's night time for spawning
        is_night = day_cycle % 1 > 0.5
        
        if distance_xz(self.position, player.position) < 20:
            direction = player.position - self.position
            direction.y = 0
            direction = direction.normalized()
            self.position += direction * self.speed * time.dt
            self.look_at(player.position)
        
        # Despawn in daylight (optional realism)
        if not is_night and self.mob_type in ['zombie', 'skeleton']:
            if distance_xz(self.position, player.position) > 30:
                destroy(self)
                if self in mobs:
                    mobs.remove(self)
        
        if self.y < -10:
            destroy(self)
            if self in mobs:
                mobs.remove(self)

def spawn_mob(position):
    mob_type = random.choice(['zombie', 'skeleton'])
    Mob(position=position, mob_type=mob_type)

# Voxel class for individual blocks
class Voxel(Button):
    def __init__(self, position=(0,0,0), block_type=1):
        super().__init__(
            parent=scene,
            position=position,
            model='cube',
            origin_y=0.5,
            texture=block_types[block_type]['texture'],
            color=block_types[block_type]['color'],
            highlight_color=color.lime,
            collider='box'
        )
        self.block_type = block_type
        self.break_progress = 0
    
    def input(self, key):
        global tool_durability, current_tool
        if self.hovered:
            if key == 'left mouse down':
                hardness = block_types[self.block_type].get('hardness', 1.0)
                tool_speed = tool_tiers[current_tool]['speed']
                self.break_progress += tool_speed * 0.2
                
                # Check if block is broken
                if self.break_progress >= hardness:
                    sounds.play_break()
                    
                    # Decrease tool durability if not bare hands
                    if current_tool != 'none' and tool_durability > 0:
                        tool_durability -= 1
                        if tool_durability <= 0:
                            current_tool = 'none'
                            tool_durability = 0
                            Text(text='Tool Broken!', position=(0, 0.2), scale=1.5, color=color.red, duration=1.5)
                    
                    destroy(self)
                else:
                    # Show breaking particles/sound based on progress
                    if self.break_progress > hardness * 0.3 and not hasattr(self, '_sound_played'):
                        sounds.play_break()
                        self._sound_played = True
            
            if key == 'right mouse down':
                # Get the normal to determine where to place the new block
                normal = self.mouse.normal
                new_pos = self.position + normal
                
                # Don't place block inside player
                if distance(new_pos, player.position) > 1.5:
                    Voxel(position=new_pos, block_type=current_block)
                    sounds.play_place()
        
        # Jumping depletes hunger
        if key == 'space' and self.hovered == False:
            global player_hunger
            player_hunger -= 0.5

# Generate initial terrain with ores and varied biomes
def generate_terrain():
    print("Generating terrain...")
    for x in range(-20, 20):
        for z in range(-20, 20):
            # Simple height variation with biome-like features
            height = int(math.sin(x / 5) * 2 + math.cos(z / 5) * 2)
            
            # Determine biome based on position
            is_desert = x > 10 or x < -10
            is_snowy = z > 10 or z < -10
            
            # Place appropriate surface block
            if is_desert:
                Voxel(position=(x, height, z), block_type=6)  # Sand
            elif is_snowy:
                Voxel(position=(x, height, z), block_type=8)  # Snow
            else:
                Voxel(position=(x, height, z), block_type=1)  # Grass
            
            # Place dirt below
            for y in range(height - 1, height - 3, -1):
                Voxel(position=(x, y, z), block_type=2)
            
            # Place stone at bottom
            Voxel(position=(x, height - 3, z), block_type=3)
            
            # Generate ores in stone layer (random distribution)
            if random.random() < 0.03:  # Coal ore
                Voxel(position=(x, height - 4, z), block_type=11)
            if random.random() < 0.02:  # Iron ore (rarer)
                Voxel(position=(x, height - 5, z), block_type=12)
            
            # Random trees (only in grass biomes)
            if random.random() < 0.02 and not is_desert and not is_snowy and x > -15 and x < 15 and z > -15 and z < 15:
                create_tree(x, height + 1, z)
    
    print("Terrain generation complete!")

def create_tree(x, y, z):
    """Create a simple tree"""
    # Trunk
    for i in range(4):
        Voxel(position=(x, y + i, z), block_type=4)
    
    # Leaves
    for lx in range(-2, 3):
        for lz in range(-2, 3):
            for ly in range(2, 4):
                if abs(lx) + abs(lz) < 3:  # Circular pattern
                    Voxel(position=(x + lx, y + ly, z + lz), block_type=5)

# Player setup
player = FirstPersonController(speed=12)
player.cursor.visible = True
player.gravity = 0.5
player.y = 5  # Start above ground

# Hand (for block placement visualization)
hand = Entity(
    parent=camera.ui,
    model='cube',
    texture='white_cube',
    scale=(0.2, 0.2, 0.2),
    rotation=(-15, -15, 0),
    position=(0.5, -0.5),
    color=color.rgb(255, 200, 150)
)

# Hand animation
def update_hand():
    if held_keys['left mouse'] or held_keys['right mouse']:
        hand.position = Vec3(0.4, -0.4)
    else:
        hand.position = Vec3(0.5, -0.5)

# UI Text
block_info = Text(
    text=f'Block: {block_types[current_block]["name"]}',
    position=(-0.85, 0.45),
    scale=1.5,
    color=color.white
)

# Tool info UI
tool_info = Text(
    text=f'Tool: None',
    position=(-0.85, 0.40),
    scale=1.2,
    color=color.white
)

# Health and Hunger bars
health_bar = Entity(parent=camera.ui, model='quad', texture='white_cube', scale=(0.3, 0.03), position=(-0.7, -0.4), color=color.red)
hunger_bar = Entity(parent=camera.ui, model='quad', texture='white_cube', scale=(0.3, 0.03), position=(-0.7, -0.45), color=color.orange)
health_text = Text(text='Health', position=(-0.85, -0.38), scale=0.7, color=color.white)
hunger_text = Text(text='Hunger', position=(-0.85, -0.43), scale=0.7, color=color.white)

# Experience bar
xp_bar = Entity(parent=camera.ui, model='quad', texture='white_cube', scale=(0.3, 0.02), position=(-0.7, -0.5), color=color.cyan)
xp_text = Text(text='Experience', position=(-0.85, -0.48), scale=0.7, color=color.white)

player_health = 10
player_hunger = 10
player_xp = 0
player_level = 0

controls_info = Text(
    text='WASD: Move | Space: Jump | LMB: Break | RMB: Place | 1-10: Blocks',
    position=(-0.85, -0.52),
    scale=0.7,
    color=color.gray
)

crosshair = Entity(parent=camera.ui, model='quad', texture='circle', scale=(0.01, 0.01), color=color.white)

fly_mode = False

def input(key):
    global current_block, fly_mode, player_xp, player_level, current_tool, tool_durability
    
    # Block selection (1-10)
    if key in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
        block_num = 10 if key == '0' else int(key)
        if block_num <= len(block_types):
            current_block = block_num
            block_info.text = f'Block: {block_types[current_block]["name"]}'
            block_info.color = block_types[current_block]['color']
            
            # Update hand color
            hand.color = block_types[current_block]['color']
            sounds.play_select()
    
    # Tool selection (T for wood, Y for stone, U for iron)
    if key == 't':
        current_tool = 'wood'
        tool_durability = tool_tiers['wood']['durability']
        tool_info.text = f'Tool: Wooden Pickaxe ({tool_durability})'
        tool_info.color = color.rgb(139, 69, 19)
        sounds.play_select()
    
    if key == 'y':
        current_tool = 'stone'
        tool_durability = tool_tiers['stone']['durability']
        tool_info.text = f'Tool: Stone Pickaxe ({tool_durability})'
        tool_info.color = color.gray
        sounds.play_select()
    
    if key == 'u':
        current_tool = 'iron'
        tool_durability = tool_tiers['iron']['durability']
        tool_info.text = f'Tool: Iron Pickaxe ({tool_durability})'
        tool_info.color = color.rgb(210, 180, 140)
        sounds.play_select()
    
    # Toggle fly mode
    if key == 'tab':
        fly_mode = not fly_mode
        player.gravity = 0 if fly_mode else 0.5
        Text(text=f'Fly Mode: {"ON" if fly_mode else "OFF"}', position=(0.85, 0.45), scale=1.5, duration=2)
    
    # Escape releases mouse
    if key == 'escape':
        if mouse.locked:
            mouse.locked = False
        else:
            mouse.locked = True
    
    # Attack mobs with left click when not hovering a block
    if key == 'left mouse down' and not mouse.hovered_entity:
        for mob in mobs[:]:
            if distance(mob.position, player.position) < 4:
                mob.health -= 3
                sounds.play_break()
                if mob.health <= 0:
                    destroy(mob)
                    mobs.remove(mob)
                    player_xp += 2
                    if player_xp >= 10 * (player_level + 1):
                        player_xp = 0
                        player_level += 1
                        player_health = min(10, player_health + 2)
                        Text(text='Level Up!', position=(0, 0.3), scale=2, color=color.gold, duration=1.5)

def update():
    global player, day_cycle, mob_spawn_timer
    
    # Hand animation
    update_hand()
    
    # Day/night cycle
    day_cycle += time.dt * 0.1
    sky.rotation = (day_cycle * 360, 0, 0)
    
    # Spawn mobs at night
    mob_spawn_timer += time.dt
    if mob_spawn_timer > 5 and day_cycle % 1 > 0.5:  # Night time
        spawn_x = random.randint(-20, 20)
        spawn_z = random.randint(-20, 20)
        if distance_xz((spawn_x, spawn_z), (player.x, player.z)) > 10:
            spawn_mob(position=(spawn_x, 5, spawn_z))
        mob_spawn_timer = 0
    
    # Update mobs
    for mob in mobs[:]:
        if mob.enabled:
            mob.update()
        if distance(mob.position, player.position) < 1.5:
            player_health -= time.dt * 0.5
    
    # Flying controls
    if fly_mode:
        if held_keys['shift']:
            player.y += 0.5
        if held_keys['control']:
            player.y -= 0.5
    
    # Check if player fell off the world
    if player.y < -20:
        player.y = 10
        player.x = 0
        player.z = 0
    
    # Hunger depletion over time
    if time.dt > 0:
        player_hunger -= time.dt * 0.05
        if player_hunger <= 0:
            player_hunger = 0
            player_health -= time.dt * 0.1
    
    # Update health and hunger bars
    health_bar.scale_x = max(0, player_health / 10) * 0.3
    hunger_bar.scale_x = max(0, player_hunger / 10) * 0.3
    xp_bar.scale_x = max(0, player_xp / (10 * (player_level + 1))) * 0.3
    
    # Update tool durability display
    if current_tool != 'none':
        tool_info.text = f'Tool: {current_tool.capitalize()} Pickaxe ({tool_durability})'
    
    # Game over check
    if player_health <= 0:
        Text(text='GAME OVER - Press R to Restart', position=(0, 0), scale=2, color=color.red, origin=(0, 0))
        if held_keys['r']:
            player_health = 10
            player_hunger = 10
            player_xp = 0
            player_level = 0
            current_tool = 'none'
            tool_durability = 0
            tool_info.text = 'Tool: None'
            player.position = (0, 5, 0)
            for mob in mobs[:]:
                destroy(mob)
            mobs.clear()

# Generate the world
generate_terrain()

# Run the game
print("\n=== MINECRAFT CLONE ===")
print("Controls:")
print("  WASD - Move")
print("  SPACE - Jump")
print("  SHIFT/CTRL - Fly up/down (when fly mode is on)")
print("  LEFT CLICK - Break block / Attack mobs")
print("  RIGHT CLICK - Place block")
print("  1-0 - Select block type (1:Grass, 2:Dirt, 3:Stone, 4:Wood, 5:Leaves, 6:Sand, 7:Brick, 8:Snow, 9:Water, 10:Lava, 11:Coal Ore, 12:Iron Ore)")
print("  T/Y/U - Select tool (Wooden/Stone/Iron Pickaxe)")
print("  TAB - Toggle fly mode")
print("  ESC - Release mouse")
print("Features: Health, Hunger, XP/Levels, Mob spawning at night, Day/Night cycle, Tool durability, Block hardness")
print("======================\n")

app.run()
