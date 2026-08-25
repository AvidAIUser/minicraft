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

# Block types with colors/textures
block_types = {
    1: {'name': 'Grass', 'color': color.rgb(0, 155, 0), 'texture': 'grass'},
    2: {'name': 'Dirt', 'color': color.rgb(139, 69, 19), 'texture': 'dirt'},
    3: {'name': 'Stone', 'color': color.rgb(128, 128, 128), 'texture': 'white_cube'},
    4: {'name': 'Wood', 'color': color.rgb(101, 67, 33), 'texture': 'white_cube'},
    5: {'name': 'Leaves', 'color': color.rgb(34, 139, 34), 'texture': 'white_cube'},
    6: {'name': 'Sand', 'color': color.rgb(237, 220, 163), 'texture': 'white_cube'},
    7: {'name': 'Brick', 'color': color.rgb(178, 34, 34), 'texture': 'white_cube'},
    8: {'name': 'Snow', 'color': color.rgb(255, 250, 250), 'texture': 'white_cube'},
}

current_block = 1  # Currently selected block type

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
    
    def input(self, key):
        if self.hovered:
            if key == 'left mouse down':
                sounds.play_break()
                destroy(self)
            
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

# Generate initial terrain
def generate_terrain():
    print("Generating terrain...")
    for x in range(-20, 20):
        for z in range(-20, 20):
            # Simple height variation
            height = int(math.sin(x / 5) * 2 + math.cos(z / 5) * 2)
            
            # Place grass on top
            Voxel(position=(x, height, z), block_type=1)
            
            # Place dirt below
            for y in range(height - 1, height - 3, -1):
                Voxel(position=(x, y, z), block_type=2)
            
            # Place stone at bottom
            Voxel(position=(x, height - 3, z), block_type=3)
            
            # Random trees
            if random.random() < 0.02 and x > -15 and x < 15 and z > -15 and z < 15:
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

# Health and Hunger bars
health_bar = Entity(parent=camera.ui, model='quad', texture='white_cube', scale=(0.3, 0.03), position=(-0.7, -0.4), color=color.red)
hunger_bar = Entity(parent=camera.ui, model='quad', texture='white_cube', scale=(0.3, 0.03), position=(-0.7, -0.45), color=color.orange)
health_text = Text(text='Health', position=(-0.85, -0.38), scale=0.7, color=color.white)
hunger_text = Text(text='Hunger', position=(-0.85, -0.43), scale=0.7, color=color.white)

player_health = 10
player_hunger = 10

controls_info = Text(
    text='WASD: Move | Space: Jump | LMB: Break | RMB: Place | 1-8: Blocks',
    position=(-0.85, -0.52),
    scale=0.7,
    color=color.gray
)

fly_mode = False

def input(key):
    global current_block, fly_mode
    
    # Block selection (1-8)
    if key in ('1', '2', '3', '4', '5', '6', '7', '8'):
        current_block = int(key)
        block_info.text = f'Block: {block_types[current_block]["name"]}'
        block_info.color = block_types[current_block]['color']
        
        # Update hand color
        hand.color = block_types[current_block]['color']
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

def update():
    global player, day_cycle
    
    # Hand animation
    update_hand()
    
    # Day/night cycle
    day_cycle += time.dt * 0.1
    sky.rotation = (day_cycle * 360, 0, 0)
    
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
    global player_health, player_hunger
    if time.dt > 0:
        player_hunger -= time.dt * 0.05
        if player_hunger <= 0:
            player_hunger = 0
            player_health -= time.dt * 0.1
    
    # Update health and hunger bars
    health_bar.scale_x = max(0, player_health / 10) * 0.3
    hunger_bar.scale_x = max(0, player_hunger / 10) * 0.3
    
    # Game over check
    if player_health <= 0:
        Text(text='GAME OVER - Press R to Restart', position=(0, 0), scale=2, color=color.red, origin=(0, 0))
        if held_keys['r']:
            player_health = 10
            player_hunger = 10
            player.position = (0, 5, 0)

# Generate the world
generate_terrain()

# Run the game
print("\n=== MINECRAFT CLONE ===")
print("Controls:")
print("  WASD - Move")
print("  SPACE - Jump")
print("  SHIFT/CTRL - Fly up/down (when fly mode is on)")
print("  LEFT CLICK - Break block")
print("  RIGHT CLICK - Place block")
print("  1-8 - Select block type (1:Grass, 2:Dirt, 3:Stone, 4:Wood, 5:Leaves, 6:Sand, 7:Brick, 8:Snow)")
print("  TAB - Toggle fly mode")
print("  ESC - Release mouse")
print("======================\n")

app.run()
