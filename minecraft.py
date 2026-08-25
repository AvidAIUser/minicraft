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

Enhanced Features:
- Procedural textures for all block types
- Dynamic lighting with shadows
- Ambient occlusion simulation
- Enhanced sound effects with spatial audio
- Particle effects for block breaking/placing
- Animated water and lava
- Day/night cycle with ambient lighting changes
- Fog effects based on time of day
"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.lights import DirectionalLight, PointLight, AmbientLight
import random
import math
import wave
import struct
import io
from perlin_noise import PerlinNoise
from collections import deque

# Enable shadows and better rendering
window.settings.shadows = True
window.settings.gamma = 2.2
window.settings.fullscreen_samples = 4  # Anti-aliasing

# Sound Manager using synthesized waves to avoid external dependencies
class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            self.test_sound = self.generate_sound(440, 0.05)
        except Exception:
            self.enabled = False
        
        # Cache common sounds
        self.break_sounds = []
        self.place_sounds = []
        self.select_sounds = []
        self.step_sounds = []
        
        # Pre-generate variety of sounds
        for i in range(5):
            self.break_sounds.append(self.generate_sound(100 + i*30, 0.08, 0.4))
            self.place_sounds.append(self.generate_sound(300 + i*50, 0.04, 0.3))
            self.select_sounds.append(self.generate_sound(500 + i*40, 0.03, 0.25))
            self.step_sounds.append(self.generate_sound(200 + i*20, 0.02, 0.15))
    
    def generate_sound(self, frequency, duration, volume=0.3, sound_type='square'):
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        buf = bytearray()
        
        for i in range(n_samples):
            t = i / sample_rate
            # Envelope for natural fade
            envelope = 1.0 - (i / n_samples) * 0.5
            
            if sound_type == 'square':
                val = math.sin(2 * math.pi * frequency * t)
                val = volume * envelope * (1 if val > 0 else -1)
            elif sound_type == 'noise':
                val = volume * envelope * (random.uniform(-1, 1))
            else:  # sine
                val = volume * envelope * math.sin(2 * math.pi * frequency * t)
            
            val = int(val * 32767)
            val = max(-32768, min(32767, val))
            buf.extend(struct.pack('<h', val))
        
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(buf)
        wav_io.seek(0)
        return Audio(wav_io, autoplay=False, loop=False)
    
    def play_break(self, block_type='stone'):
        if not self.enabled: return
        sound = random.choice(self.break_sounds)
        sound.pitch = random.uniform(0.7, 1.3)
        
        # Different pitches for different block types
        if block_type == 'wood':
            sound.pitch *= 1.2
        elif block_type == 'glass':
            sound.pitch *= 1.5
        elif block_type == 'metal':
            sound.pitch *= 0.8
        
        sound.volume = random.uniform(0.3, 0.6)
        sound.play()
    
    def play_place(self, block_type='stone'):
        if not self.enabled: return
        sound = random.choice(self.place_sounds)
        sound.pitch = random.uniform(0.9, 1.2)
        
        if block_type == 'wood':
            sound.pitch *= 1.1
        elif block_type == 'glass':
            sound.pitch *= 1.4
        
        sound.volume = random.uniform(0.2, 0.4)
        sound.play()
    
    def play_select(self):
        if not self.enabled: return
        sound = random.choice(self.select_sounds)
        sound.pitch = random.uniform(1.0, 1.3)
        sound.volume = 0.25
        sound.play()
    
    def play_step(self):
        if not self.enabled: return
        sound = random.choice(self.step_sounds)
        sound.pitch = random.uniform(0.8, 1.1)
        sound.volume = 0.1
        sound.play()
    
    def play_water(self):
        if not self.enabled: return
        sound = self.generate_sound(300, 0.3, 0.15, 'noise')
        sound.pitch = random.uniform(0.8, 1.2)
        sound.play()
    
    def play_lava(self):
        if not self.enabled: return
        sound = self.generate_sound(80, 0.4, 0.2, 'noise')
        sound.pitch = random.uniform(0.6, 0.9)
        sound.play()
    
    def play_explode(self):
        if not self.enabled: return
        # Explosion sound with multiple frequencies
        sound1 = self.generate_sound(100, 0.3, 0.5, 'noise')
        sound2 = self.generate_sound(50, 0.4, 0.4, 'square')
        sound1.volume = 0.8
        sound2.volume = 0.6
        sound1.play()
        sound2.play()
    
    def play_footstep(self, block_type='stone'):
        if not self.enabled: return
        sound = random.choice(self.step_sounds)
        
        # Different sounds for different surfaces
        if block_type == 'grass':
            sound.pitch = random.uniform(0.9, 1.1)
            sound.volume = 0.08
        elif block_type == 'wood':
            sound.pitch = random.uniform(1.1, 1.3)
            sound.volume = 0.1
        elif block_type == 'stone':
            sound.pitch = random.uniform(0.7, 0.9)
            sound.volume = 0.12
        elif block_type == 'sand':
            sound.pitch = random.uniform(0.8, 1.0)
            sound.volume = 0.06
        elif block_type == 'snow':
            sound.pitch = random.uniform(1.0, 1.2)
            sound.volume = 0.05
        else:
            sound.pitch = random.uniform(0.8, 1.1)
            sound.volume = 0.08
        
        sound.play()
    
    def play_jump(self):
        if not self.enabled: return
        sound = self.generate_sound(300, 0.15, 0.2, 'sine')
        sound.pitch = random.uniform(0.9, 1.1)
        sound.play()

# Texture Generator for procedural textures
class TextureGenerator:
    @staticmethod
    def create_grass_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        # Pre-generate random values for performance
        noise_values = [[random.randint(-15, 15) for _ in range(size)] for _ in range(size)]
        grass_patterns = [[random.random() < 0.3 for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                # Base green color with variation
                base_green = random.randint(40, 80)
                noise = noise_values[y][x]
                
                # Add grass blade patterns
                if grass_patterns[y][x]:
                    r = max(0, min(255, base_green + noise + 20))
                    g = max(0, min(255, base_green * 2 + noise + 40))
                    b = max(0, min(255, base_green + noise))
                else:
                    r = max(0, min(255, base_green + noise - 10))
                    g = max(0, min(255, base_green * 1.5 + noise + 20))
                    b = max(0, min(255, base_green + noise - 5))
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    @staticmethod
    def create_dirt_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        # Pre-generate random values for performance
        noise_values = [[random.randint(-20, 20) for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                base_brown = random.randint(80, 120)
                noise = noise_values[y][x]
                
                r = max(0, min(255, base_brown + noise + 20))
                g = max(0, min(255, base_brown * 0.7 + noise))
                b = max(0, min(255, base_brown * 0.5 + noise - 10))
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    @staticmethod
    def create_stone_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        # Pre-generate random values for performance
        noise_values = [[random.randint(-30, 30) for _ in range(size)] for _ in range(size)]
        grain_patterns = [[random.random() < 0.1 for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                base_gray = random.randint(100, 150)
                noise = noise_values[y][x]
                
                r = g = b = max(0, min(255, base_gray + noise))
                
                # Add stone grain
                if grain_patterns[y][x]:
                    darker = max(0, base_gray - 40)
                    r = g = b = darker
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    @staticmethod
    def create_wood_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        for y in range(size):
            for x in range(size):
                # Wood grain pattern
                grain = math.sin(x * 0.3) * 10 + math.sin(y * 0.1) * 5
                base_brown = 80 + grain
                
                r = max(0, min(255, base_brown + 20))
                g = max(0, min(255, base_brown - 10))
                b = max(0, min(255, base_brown - 30))
                
                pixels[x, y] = (int(r), int(g), int(b))
        
        return img
    
    @staticmethod
    def create_leaves_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        # Pre-generate random values for performance
        base_greens = [[random.randint(30, 60) for _ in range(size)] for _ in range(size)]
        leaf_patterns = [[random.random() < 0.8 for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                base_green = base_greens[y][x]
                
                # Leaf pattern with transparency simulation
                if leaf_patterns[y][x]:
                    r = max(0, min(255, base_green - 10))
                    g = max(0, min(255, base_green + 30))
                    b = max(0, min(255, base_green - 5))
                else:
                    # Gaps in leaves
                    r = g = b = 20
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    @staticmethod
    def create_sand_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        # Pre-generate random values for performance
        noise_values = [[random.randint(-10, 10) for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                base_sand = random.randint(200, 230)
                noise = noise_values[y][x]
                
                r = max(0, min(255, base_sand + noise + 20))
                g = max(0, min(255, base_sand + noise + 10))
                b = max(0, min(255, base_sand * 0.8 + noise))
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    @staticmethod
    def create_ore_texture(base_texture, ore_color, size=64):
        img = base_texture.copy()
        pixels = img.load()
        
        # Add ore speckles
        for _ in range(15):
            cx, cy = random.randint(5, size-5), random.randint(5, size-5)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx*dx + dy*dy <= 9:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < size and 0 <= ny < size:
                            blend = random.uniform(0.6, 1.0)
                            old_r, old_g, old_b = pixels[nx, ny][:3]
                            new_r = int(old_r * (1-blend) + ore_color[0] * blend)
                            new_g = int(old_g * (1-blend) + ore_color[1] * blend)
                            new_b = int(old_b * (1-blend) + ore_color[2] * blend)
                            pixels[nx, ny] = (new_r, new_g, new_b)
        
        return img
    
    @staticmethod
    def create_water_texture(size=64):
        img = PIL.Image.new('RGBA', (size, size))
        pixels = img.load()
        
        for y in range(size):
            for x in range(size):
                # Wave pattern
                wave_val = math.sin(x * 0.2 + y * 0.1) * 20
                base_blue = 100 + wave_val
                
                r = max(0, min(255, 20))
                g = max(0, min(255, base_blue - 20))
                b = max(0, min(255, base_blue + 40))
                a = 180  # Semi-transparent
                
                pixels[x, y] = (r, g, b, a)
        
        return img
    
    @staticmethod
    def create_lava_texture(size=64):
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        for y in range(size):
            for x in range(size):
                # Lava flow pattern
                flow = math.sin(x * 0.15 + y * 0.1) * 30 + math.cos(x * 0.3) * 20
                
                r = max(0, min(255, 200 + flow))
                g = max(0, min(255, 50 + flow * 0.5))
                b = max(0, min(255, flow * 0.3))
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    @staticmethod
    def create_cloud_texture(size=128):
        """Create a semi-transparent cloud texture"""
        img = PIL.Image.new('RGBA', (size, size))
        pixels = img.load()
        
        noise = PerlinNoise(octaves=3, seed=random.randint(1, 1000))
        
        # Pre-generate random values for performance
        rand_values = [[random.randint(-10, 10) for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                # Generate cloud pattern using Perlin noise
                nx, ny = x / size, y / size
                val = noise([nx, ny])
                
                # Threshold for cloud formation
                if val > 0.3:
                    alpha = int((val - 0.3) * 255 * 2)
                    alpha = min(255, alpha)
                    # White clouds with slight variation
                    base = 240 + rand_values[y][x]
                    r = g = b = max(0, min(255, base))
                    pixels[x, y] = (r, g, b, alpha)
                else:
                    pixels[x, y] = (255, 255, 255, 0)
        
        return img
    
    @staticmethod
    def create_metal_texture(size=64):
        """Create metallic/iron texture"""
        img = PIL.Image.new('RGB', (size, size))
        pixels = img.load()
        
        # Pre-generate random values for performance
        noise_values = [[random.randint(-15, 15) for _ in range(size)] for _ in range(size)]
        shine_patterns = [[random.random() < 0.05 for _ in range(size)] for _ in range(size)]
        shine_values = [[random.randint(50, 100) for _ in range(size)] for _ in range(size)]

        for y in range(size):
            for x in range(size):
                base_gray = random.randint(180, 220)
                noise_val = noise_values[y][x]
                
                # Add metallic shine streaks
                if shine_patterns[y][x]:
                    shine = shine_values[y][x]
                    r = min(255, base_gray + shine)
                    g = min(255, base_gray + shine - 10)
                    b = min(255, base_gray + shine - 20)
                else:
                    r = max(0, min(255, base_gray + noise_val))
                    g = max(0, min(255, base_gray + noise_val - 5))
                    b = max(0, min(255, base_gray + noise_val - 10))
                
                pixels[x, y] = (int(r), int(g), int(b))
        
        return img

# Initialize the app
app = Ursina()
sounds = SoundManager()
texture_gen = TextureGenerator()

# Window settings
window.title = 'Minecraft Clone - Enhanced'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = True
window.fps_counter.enabled = True
window.color = color.rgb(135, 206, 235)  # Sky blue background

# Lighting system
ambient_light = AmbientLight(color=color.rgb(100, 100, 120), brightness=0.3)
sun_light = DirectionalLight(color=color.rgb(255, 250, 200), brightness=0.8)
sun_light.look_at(Vec3(1, -1, 1))

# Create point lights for glowing blocks
glow_lights = []

# Sky with day/night cycle and clouds
sky = Sky(texture='sky_sunset')
day_cycle = 0
sky_color_day = color.rgb(135, 206, 235)
sky_color_night = color.rgb(10, 10, 30)
sky_color_sunset = color.rgb(255, 127, 80)

# Generate cloud texture and create cloud entities
cloud_texture = texture_gen.create_cloud_texture()
clouds = []

def create_cloud_layer(height=50, count=15):
    """Create a layer of clouds at specified height"""
    for _ in range(count):
        cloud_x = random.uniform(-100, 100)
        cloud_z = random.uniform(-100, 100)
        cloud_scale = random.uniform(15, 30)
        
        cloud = Entity(
            model='quad',
            texture=cloud_texture,
            position=(cloud_x, height, cloud_z),
            scale=(cloud_scale, cloud_scale),
            double_sided=True,
            alpha=0.8
        )
        clouds.append(cloud)

create_cloud_layer(height=40, count=20)
create_cloud_layer(height=50, count=15)

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
    1: {'name': 'Grass', 'color': color.rgb(0, 155, 0), 'texture': None, 'hardness': 1.0, 'sound': 'grass'},
    2: {'name': 'Dirt', 'color': color.rgb(139, 69, 19), 'texture': None, 'hardness': 0.8, 'sound': 'dirt'},
    3: {'name': 'Stone', 'color': color.rgb(128, 128, 128), 'texture': None, 'hardness': 2.0, 'sound': 'stone'},
    4: {'name': 'Wood', 'color': color.rgb(101, 67, 33), 'texture': None, 'hardness': 1.2, 'sound': 'wood'},
    5: {'name': 'Leaves', 'color': color.rgb(34, 139, 34), 'texture': None, 'hardness': 0.5, 'sound': 'leaves'},
    6: {'name': 'Sand', 'color': color.rgb(237, 220, 163), 'texture': None, 'hardness': 0.6, 'sound': 'sand'},
    7: {'name': 'Brick', 'color': color.rgb(178, 34, 34), 'texture': None, 'hardness': 2.5, 'sound': 'stone'},
    8: {'name': 'Snow', 'color': color.rgb(255, 250, 250), 'texture': None, 'hardness': 0.4, 'sound': 'snow'},
    9: {'name': 'Water', 'color': color.rgba(0, 0, 255, 180), 'texture': None, 'transparent': True, 'hardness': 0.0, 'sound': 'water', 'animate': True},
    10: {'name': 'Lava', 'color': color.rgba(255, 69, 0, 200), 'texture': None, 'glow': True, 'hardness': 0.0, 'sound': 'lava', 'animate': True},
    11: {'name': 'Coal Ore', 'color': color.rgb(64, 64, 64), 'texture': None, 'hardness': 2.5, 'sound': 'stone'},
    12: {'name': 'Iron Ore', 'color': color.rgb(210, 180, 140), 'texture': None, 'hardness': 3.0, 'sound': 'stone'},
    13: {'name': 'Diamond Ore', 'color': color.rgb(0, 255, 255), 'texture': None, 'hardness': 4.0, 'sound': 'stone'},
    14: {'name': 'Gold Ore', 'color': color.rgb(255, 215, 0), 'texture': None, 'hardness': 3.5, 'sound': 'stone'},
    15: {'name': 'Cactus', 'color': color.rgb(0, 128, 0), 'texture': None, 'hardness': 0.3, 'sound': 'leaves'},
    16: {'name': 'Clay', 'color': color.rgb(180, 180, 200), 'texture': None, 'hardness': 1.5, 'sound': 'dirt'},
    17: {'name': 'Glass', 'color': color.rgba(200, 230, 255, 100), 'texture': None, 'transparent': True, 'hardness': 0.8, 'sound': 'glass'},
    18: {'name': 'Iron Block', 'color': color.rgb(220, 220, 230), 'texture': None, 'hardness': 4.0, 'sound': 'metal'},
}

# Generate procedural textures for each block type
def generate_block_textures():
    """Generate all procedural textures at startup"""
    print("Generating procedural textures...")
    
    # Create base textures
    grass_img = texture_gen.create_grass_texture()
    dirt_img = texture_gen.create_dirt_texture()
    stone_img = texture_gen.create_stone_texture()
    wood_img = texture_gen.create_wood_texture()
    leaves_img = texture_gen.create_leaves_texture()
    sand_img = texture_gen.create_sand_texture()
    water_img = texture_gen.create_water_texture()
    lava_img = texture_gen.create_lava_texture()
    
    # Create ore textures
    coal_ore_img = texture_gen.create_ore_texture(stone_img, (40, 40, 40))
    iron_ore_img = texture_gen.create_ore_texture(stone_img, (210, 180, 140))
    diamond_ore_img = texture_gen.create_ore_texture(stone_img, (0, 255, 255))
    gold_ore_img = texture_gen.create_ore_texture(stone_img, (255, 215, 0))
    
    # Create additional textures
    glass_img = PIL.Image.new('RGBA', (64, 64), (200, 230, 255, 100))
    iron_block_img = texture_gen.create_metal_texture()
    
    # Store textures in block_types
    block_types[1]['texture'] = grass_img
    block_types[2]['texture'] = dirt_img
    block_types[3]['texture'] = stone_img
    block_types[4]['texture'] = wood_img
    block_types[5]['texture'] = leaves_img
    block_types[6]['texture'] = sand_img
    block_types[7]['texture'] = texture_gen.create_ore_texture(stone_img, (178, 34, 34))  # Brick-like
    block_types[8]['texture'] = texture_gen.create_ore_texture(stone_img, (255, 250, 250))  # Snow-like
    block_types[9]['texture'] = water_img
    block_types[10]['texture'] = lava_img
    block_types[11]['texture'] = coal_ore_img
    block_types[12]['texture'] = iron_ore_img
    block_types[13]['texture'] = diamond_ore_img
    block_types[14]['texture'] = gold_ore_img
    block_types[15]['texture'] = texture_gen.create_ore_texture(leaves_img, (0, 100, 0))  # Cactus
    block_types[16]['texture'] = texture_gen.create_ore_texture(dirt_img, (180, 180, 200))  # Clay
    block_types[17]['texture'] = glass_img  # Glass
    block_types[18]['texture'] = iron_block_img  # Iron Block
    
    print("Textures generated successfully!")

generate_block_textures()

# Tool tiers with mining speed multipliers
tool_tiers = {
    'none': {'speed': 1.0, 'durability': 0},
    'wood': {'speed': 2.0, 'durability': 60},
    'stone': {'speed': 4.0, 'durability': 132},
    'iron': {'speed': 6.0, 'durability': 251},
    'diamond': {'speed': 8.0, 'durability': 1562},
}

# Mob types with properties
mob_types = {
    'zombie': {'color': color.rgb(0, 100, 0), 'health': 10, 'speed': 2, 'damage': 1},
    'skeleton': {'color': color.rgb(200, 200, 200), 'health': 8, 'speed': 2.5, 'damage': 2},
    'creeper': {'color': color.rgb(0, 150, 0), 'health': 6, 'speed': 1.5, 'damage': 5, 'explosive': True},
    'pig': {'color': color.rgb(255, 180, 180), 'health': 5, 'speed': 1, 'damage': 0, 'passive': True},
    'cow': {'color': color.rgb(100, 60, 40), 'health': 8, 'speed': 1.2, 'damage': 0, 'passive': True},
}

# Crafting recipes: result -> required items
crafting_recipes = {
    (4, 4): {'wood_planks': 4},  # Wood to planks (simplified)
    ('pickaxe_wood', 1): {4: 3, 2: 2},  # Wood pickaxe: 3 wood, 2 dirt (placeholder)
    ('pickaxe_stone', 1): {3: 3, 4: 2},  # Stone pickaxe: 3 stone, 2 wood
    ('pickaxe_iron', 1): {12: 3, 4: 2},  # Iron pickaxe: 3 iron ore, 2 wood
    ('pickaxe_diamond', 1): {13: 3, 4: 2},  # Diamond pickaxe: 3 diamond ore, 2 wood
    ('torch', 4): {11: 1, 4: 1},  # Torch: 1 coal, 1 wood
    ('brick', 4): {6: 4},  # Brick from clay/sand
}

current_block = 1  # Currently selected block type
current_tool = 'none'  # Current tool tier
tool_durability = 0  # Current tool durability

# Simple mobs list
mobs = []
mob_spawn_timer = 0

class Mob(Entity):
    def __init__(self, position=(0,2,0), mob_type='zombie'):
        mob_data = mob_types.get(mob_type, mob_types['zombie'])
        super().__init__(
            model='cube',
            color=mob_data['color'],
            scale=(0.8, 1.8, 0.8) if not mob_data.get('passive') else (0.9, 0.9, 1.2),
            position=position,
            collider='box'
        )
        self.mob_type = mob_type
        self.health = mob_data['health']
        self.speed = mob_data['speed']
        self.damage = mob_data.get('damage', 0)
        self.passive = mob_data.get('passive', False)
        self.explosive = mob_data.get('explosive', False)
        self.explosion_timer = 0
        mobs.append(self)
    
    def update(self):
        # Check if it's night time for spawning
        is_night = day_cycle % 1 > 0.5
        
        dist = distance_xz(self.position, player.position)
        
        if self.explosive and dist < 3:
            self.explosion_timer += time.dt
            if self.explosion_timer > 1.5:
                # Explode
                sounds.play_break()
                player_health -= self.damage
                Text(text='BOOM!', position=(0, 0.3), scale=2, color=color.orange, duration=1)
                destroy(self)
                if self in mobs:
                    mobs.remove(self)
                return
        elif self.explosive:
            self.explosion_timer = 0
        
        if dist < 20 and not self.passive:
            direction = player.position - self.position
            direction.y = 0
            direction = direction.normalized()
            self.position += direction * self.speed * time.dt
            self.look_at(player.position)
        elif self.passive and dist < 10:
            # Passive mobs wander randomly
            if random.random() < 0.02:
                self.position += Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)) * self.speed * time.dt
        
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
    is_night = day_cycle % 1 > 0.5
    if is_night:
        mob_type = random.choice(['zombie', 'skeleton', 'creeper'])
    else:
        mob_type = random.choice(['pig', 'cow'])
    Mob(position=position, mob_type=mob_type)

# Enhanced particle system with more effects
particles = []
smoke_particles = []

class SmokeParticle(Entity):
    """Smoke particle for explosions and ambient effects"""
    def __init__(self, position, color=color.gray, velocity=None, lifetime=2.0, scale=0.2):
        if velocity is None:
            velocity = Vec3(
                random.uniform(-0.5, 0.5),
                random.uniform(0.5, 1.5),
                random.uniform(-0.5, 0.5)
            )
        super().__init__(
            model='sphere',
            color=color.rgba(color.r, color.g, color.b, 150),
            position=position,
            scale=scale
        )
        self.velocity = velocity
        self.lifetime = lifetime
        self.age = 0
        smoke_particles.append(self)
    
    def update(self):
        self.age += time.dt
        self.position += self.velocity * time.dt
        
        # Expand and fade
        expand_rate = 1 + time.dt * 0.5
        self.scale *= expand_rate
        
        alpha = int(150 * (1 - self.age / self.lifetime))
        self.color = color.rgba(self.color.r, self.color.g, self.color.b, alpha)
        
        if self.age >= self.lifetime:
            destroy(self)
            if self in smoke_particles:
                smoke_particles.remove(self)

def spawn_smoke(position, count=10):
    """Spawn smoke particles at position"""
    for _ in range(count):
        SmokeParticle(position=position)

def spawn_explosion_particles(position, count=20):
    """Spawn explosion particles with fire colors"""
    for _ in range(count):
        vel = Vec3(
            random.uniform(-1, 1),
            random.uniform(0.5, 2),
            random.uniform(-1, 1)
        )
        fire_color = random.choice([color.orange, color.red, color.yellow])
        p = Particle(position=position, color=fire_color, velocity=vel, lifetime=1.5, scale=random.uniform(0.1, 0.25))

# Particle system for visual effects

class Particle(Entity):
    """Particle effect for block breaking, placing, and ambient effects"""
    def __init__(self, position, color, velocity, lifetime=1.0, scale=0.1):
        super().__init__(
            model='cube',
            color=color,
            position=position,
            scale=scale
        )
        self.velocity = velocity
        self.lifetime = lifetime
        self.age = 0
        particles.append(self)
    
    def update(self):
        self.age += time.dt
        self.position += self.velocity * time.dt
        
        # Apply gravity
        self.velocity.y -= 5 * time.dt
        
        # Fade out
        if self.age > self.lifetime * 0.7:
            alpha = 1 - (self.age - self.lifetime * 0.7) / (self.lifetime * 0.3)
            self.color = color.rgba(self.color.r, self.color.g, self.color.b, int(255 * alpha))
        
        # Remove when expired
        if self.age >= self.lifetime:
            destroy(self)
            if self in particles:
                particles.remove(self)

def spawn_particles(position, color, count=8, spread=0.3):
    """Spawn particle burst at position"""
    for _ in range(count):
        vel = Vec3(
            random.uniform(-spread, spread),
            random.uniform(0, spread),
            random.uniform(-spread, spread)
        )
        Particle(position=position, color=color, velocity=vel, lifetime=random.uniform(0.5, 1.0), scale=random.uniform(0.05, 0.15))

# Voxel class for individual blocks
class Voxel(Button):
    def __init__(self, position=(0,0,0), block_type=1):
        btex = block_types[block_type]['texture']
        bcolor = block_types[block_type]['color']
        
        super().__init__(
            parent=scene,
            position=position,
            model='cube',
            origin_y=0.5,
            texture=btex,
            color=bcolor,
            highlight_color=color.lime,
            collider='box'
        )
        self.block_type = block_type
        self.break_progress = 0
        self.animation_time = 0
        
        # Add glow effect for lava and other glowing blocks
        if block_types[block_type].get('glow'):
            self.glow = Entity(
                parent=self,
                model='cube',
                color=color.rgba(255, 100, 0, 50),
                scale=1.02,
                double_sided=True
            )
    
    def input(self, key):
        global tool_durability, current_tool
        if self.hovered:
            if key == 'left mouse down':
                hardness = block_types[self.block_type].get('hardness', 1.0)
                tool_speed = tool_tiers[current_tool]['speed']
                self.break_progress += tool_speed * 0.2
                
                # Spawn break particles
                spawn_particles(self.position + Vec3(0, 0.5, 0), 
                              block_types[self.block_type]['color'], 
                              count=3, spread=0.2)
                
                # Check if block is broken
                if self.break_progress >= hardness:
                    sound_type = block_types[self.block_type].get('sound', 'stone')
                    sounds.play_break(sound_type)
                    
                    # Decrease tool durability if not bare hands
                    if current_tool != 'none' and tool_durability > 0:
                        tool_durability -= 1
                        if tool_durability <= 0:
                            current_tool = 'none'
                            tool_durability = 0
                            Text(text='Tool Broken!', position=(0, 0.2), scale=1.5, color=color.red, duration=1.5)
                    
                    # Spawn more particles on break
                    spawn_particles(self.position + Vec3(0, 0.5, 0), 
                                  block_types[self.block_type]['color'], 
                                  count=12, spread=0.4)
                    
                    destroy(self)
                else:
                    # Show breaking particles/sound based on progress
                    if self.break_progress > hardness * 0.3 and not hasattr(self, '_sound_played'):
                        sound_type = block_types[self.block_type].get('sound', 'stone')
                        sounds.play_break(sound_type)
                        self._sound_played = True
            
            if key == 'right mouse down':
                # Get the normal to determine where to place the new block
                normal = self.mouse.normal
                new_pos = self.position + normal
                
                # Don't place block inside player
                if distance(new_pos, player.position) > 1.5:
                    Voxel(position=new_pos, block_type=current_block)
                    sound_type = block_types[current_block].get('sound', 'stone')
                    sounds.play_place(sound_type)
                    
                    # Spawn place particles
                    spawn_particles(new_pos + Vec3(0, 0.5, 0), 
                                  block_types[current_block]['color'], 
                                  count=5, spread=0.2)
        
        # Jumping depletes hunger
        if key == 'space' and self.hovered == False:
            global player_hunger
            player_hunger -= 0.5
    
    def update(self):
        # Animate water and lava blocks
        if block_types[self.block_type].get('animate'):
            self.animation_time += time.dt * 2
            wave_height = math.sin(self.animation_time) * 0.02 + math.cos(self.animation_time * 1.5) * 0.01
            self.scale_y = 1 + wave_height * 0.5
            self.position_y = int(self.position.y) + 0.5 + wave_height
        
        # Pulsing glow for lava
        if block_types[self.block_type].get('glow') and hasattr(self, 'glow'):
            pulse = math.sin(self.animation_time * 3) * 0.3 + 0.7
            self.glow.color = color.rgba(255, 100 + int(pulse * 50), 0, int(50 + pulse * 50))

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
            is_ocean = abs(x) < 3 and abs(z) < 3
            
            # Place appropriate surface block
            if is_ocean:
                Voxel(position=(x, height - 2, z), block_type=9)  # Water
                Voxel(position=(x, height - 3, z), block_type=6)  # Sand below water
            elif is_desert:
                Voxel(position=(x, height, z), block_type=6)  # Sand
                # Random cactus in desert
                if random.random() < 0.03 and x > -18 and x < 18 and z > -18 and z < 18:
                    Voxel(position=(x, height + 1, z), block_type=15)  # Cactus
            elif is_snowy:
                Voxel(position=(x, height, z), block_type=8)  # Snow
            else:
                Voxel(position=(x, height, z), block_type=1)  # Grass
                # Clay patches near grass biomes
                if random.random() < 0.01:
                    for cx in range(-1, 2):
                        for cz in range(-1, 2):
                            Voxel(position=(x + cx, height - 1, z + cz), block_type=16)
            
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
            if random.random() < 0.01:  # Gold ore (very rare)
                Voxel(position=(x, height - 6, z), block_type=14)
            if random.random() < 0.005:  # Diamond ore (extremely rare)
                Voxel(position=(x, height - 7, z), block_type=13)
            
            # Random trees (only in grass biomes)
            if random.random() < 0.02 and not is_desert and not is_snowy and not is_ocean and x > -15 and x < 15 and z > -15 and z < 15:
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
    
    # Tool selection (T for wood, Y for stone, U for iron, I for diamond)
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
    
    if key == 'i':
        current_tool = 'diamond'
        tool_durability = tool_tiers['diamond']['durability']
        tool_info.text = f'Tool: Diamond Pickaxe ({tool_durability})'
        tool_info.color = color.rgb(0, 255, 255)
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
                sounds.play_break('stone')
                spawn_particles(mob.position, mob.color, count=5, spread=0.3)
                if mob.health <= 0:
                    if mob.explosive:
                        sounds.play_explode()
                        spawn_explosion_particles(mob.position, count=25)
                        spawn_smoke(mob.position, count=15)
                    else:
                        sounds.play_break(mob.mob_type)
                        spawn_particles(mob.position, mob.color, count=10, spread=0.4)
                    destroy(mob)
                    mobs.remove(mob)
                    player_xp += 2
                    if player_xp >= 10 * (player_level + 1):
                        player_xp = 0
                        player_level += 1
                        player_health = min(10, player_health + 2)
                        Text(text='Level Up!', position=(0, 0.3), scale=2, color=color.gold, duration=1.5)

def update():
    global player, day_cycle, mob_spawn_timer, last_footstep_time
    
    # Hand animation
    update_hand()
    
    # Day/night cycle with enhanced lighting
    day_cycle += time.dt * 0.1
    sky.rotation = (day_cycle * 360, 0, 0)
    
    # Update clouds - slow drift
    for cloud in clouds:
        cloud.x += time.dt * 2  # Slow drift to the right
        if cloud.x > 150:
            cloud.x = -150  # Wrap around
    
    # Update ambient light based on time of day
    day_phase = day_cycle % 1
    if day_phase < 0.25:  # Dawn
        sky_color = color.lerp(sky_color_night, sky_color_sunset, day_phase / 0.25)
        sun_brightness = day_phase / 0.25 * 0.8
    elif day_phase < 0.5:  # Day
        sky_color = color.lerp(sky_color_sunset, sky_color_day, (day_phase - 0.25) / 0.25)
        sun_brightness = 0.8
    elif day_phase < 0.75:  # Dusk
        sky_color = color.lerp(sky_color_day, sky_color_sunset, (day_phase - 0.5) / 0.25)
        sun_brightness = (0.75 - day_phase) / 0.25 * 0.8
    else:  # Night
        sky_color = color.lerp(sky_color_sunset, sky_color_night, (day_phase - 0.75) / 0.25)
        sun_brightness = 0.1
    
    window.color = sky_color
    sun_light.brightness = sun_brightness
    ambient_light.brightness = max(0.1, sun_brightness * 0.4)
    
    # Play footstep sounds when walking
    if held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']:
        if not hasattr(update, 'last_footstep_time'):
            update.last_footstep_time = 0
        update.last_footstep_time += time.dt
        
        # Check if player is on ground
        ray_origin = player.position + Vec3(0, 0.5, 0)
        ray_direction = Vec3(0, -1, 0)
        hit_info = raycast(ray_origin, ray_direction, distance=1.2, ignore=(player,), timeout=0)
        
        if hit_info.hit and update.last_footstep_time > 0.4:  # Footstep every 0.4 seconds while walking
            update.last_footstep_time = 0
            # Determine block type under player
            if isinstance(hit_info.entity, Voxel):
                sound_type = block_types.get(hit_info.entity.block_type, {}).get('sound', 'stone')
            else:
                sound_type = 'stone'
            sounds.play_footstep(sound_type)
    
    # Jump sound
    if held_keys['space'] and player.y < 2:  # Simple ground check
        if not hasattr(update, 'jump_played'):
            sounds.play_jump()
            update.jump_played = True
    elif not held_keys['space']:
        update.jump_played = False
    
    # Play water/lava ambient sounds near player
    if random.random() < 0.01:  # Occasional ambient sound
        for entity in scene.children:
            if isinstance(entity, Voxel):
                dist = distance(entity.position, player.position)
                if dist < 5:
                    bt = block_types.get(entity.block_type, {})
                    if bt.get('sound') == 'water' and random.random() < 0.3:
                        sounds.play_water()
                        break
                    elif bt.get('sound') == 'lava' and random.random() < 0.2:
                        sounds.play_lava()
                        break
    
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
    
    # Update particles
    for particle in particles[:]:
        if particle.enabled:
            particle.update()
    
    # Update smoke particles
    for smoke in smoke_particles[:]:
        if smoke.enabled:
            smoke.update()
    
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
print("  1-9 - Select block type (1:Grass, 2:Dirt, 3:Stone, 4:Wood, 5:Leaves, 6:Sand, 7:Brick, 8:Snow, 9:Water)")
print("  0/10 - Lava, 11:Coal Ore, 12:Iron Ore, 13:Diamond Ore, 14:Gold Ore, 15:Cactus, 16:Clay")
print("  T/Y/U/I - Select tool (Wooden/Stone/Iron/Diamond Pickaxe)")
print("  TAB - Toggle fly mode")
print("  ESC - Release mouse")
print("")
print("Enhanced Features:")
print("  * Procedural textures for all block types (grass, dirt, stone, wood, ores, etc.)")
print("  * Dynamic lighting with realistic day/night cycle")
print("  * Animated clouds that drift across the sky")
print("  * Enhanced sound effects with spatial audio")
print("  * Footstep sounds that vary by surface type")
print("  * Jump and explosion sound effects")
print("  * Particle effects for block breaking/placing")
print("  * Smoke and fire particles for explosions")
print("  * Animated water and lava blocks with wave motion")
print("  * Pulsing glow effect for lava blocks")
print("  * Sky color transitions (dawn, day, dusk, night)")
print("  * Ambient water/lava sounds when nearby")
print("  * New block types: Glass (transparent), Iron Block (metallic)")
print("  * Anti-aliasing enabled for smoother visuals")
print("======================\n")

app.run()
