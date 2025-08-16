import random
import re
import sys
import threading
import time
import keyboard


class Entity:
    def __init__(self, game_width, game_height):
        self.entity_id = None
        self.can_control_by_user = False
        self.display_symbol = "E"
        self.hp = 1
        self.inventory_size = 0
        self.current_cord = None
        self.game_width = game_width
        self.game_height = game_height

        self.move_delay = 0.01
        self.delay = False
        self.random_spawn = False

        self.parser_dict = {
            "id": self.parser_entity_id,
            "can_control_by_user": self.parser_can_control_by_user,
            "display_symbol": self.parser_display_symbol,
            "hp": self.parser_hp,
            "inventory_size": self.parser_inventory_size,
            "default_coord": self.parser_default_coord,
            "move_delay": self.parser_move_delay,
        }

        self.uncrossable_cord_list = []

    def parser_move_delay(self, line):
        match = re.match(r"move_delay = (\d*\.\d+|)", line)
        if match:
            self.move_delay = float(match.groups()[0])

    def parser_entity_id(self, line):
        match = re.match(r"id = (.*)", line)

        if match:
            self.entity_id = match.groups()[0]

    def parser_can_control_by_user(self, line):
        match = re.match(r"can_control_by_user = (.*)", line)

        if match:
            if match.groups()[0] == "yes":
                self.can_control_by_user = True

    def parser_random_spawn(self, line):
        if self.can_control_by_user:
            return

        match = re.match(r"random_spawn = (.*)", line)

        if match:
            if match.groups()[0] == "yes":
                self.random_spawn = True

    def parser_display_symbol(self, line):
        match = re.match(r"display_symbol = (.*)", line)
        if match:
            self.display_symbol = match.groups()[0].replace("\"", "")

    def parser_hp(self, line):
        match = re.match(r"hp = (\d+)", line)
        if match:
            self.hp = int(match.groups()[0])

    def parser_inventory_size(self, line):
        match = re.match(r"inventory_size = (\d+)", line)
        if match:
            self.inventory_size = int(match.groups()[0])

    def parser_default_coord(self, line):
        match = re.match(r"default_coord = \((\d+), (\d+)\)", line)

        if match:
            self.current_cord = (int(match.groups()[0]), int(match.groups()[1]))

    def random_spawn_a_place(self):
        coord = (random.randint(0, self.game_width), random.randint(0, self.game_height))
        self.current_cord = coord

    def ngo(self, pos: int, side):  # no_negative_or_out_of_bounds_convert
        if side == "w":
            if pos < 0:
                pos = 0
            elif pos >= self.game_width:
                pos = self.game_width - 1
        elif side == "h":
            if pos < 0:
                pos = 0
            elif pos >= self.game_height:
                pos = self.game_height - 1

        return pos

    def up(self):
        new_cord = (self.current_cord[0], self.ngo(self.current_cord[1] - 1, "h"))
        if new_cord not in self.uncrossable_cord_list:
            self.current_cord = new_cord

    def down(self):
        new_cord = (self.current_cord[0], self.ngo(self.current_cord[1]+1, "h"))

        if new_cord not in self.uncrossable_cord_list:
            self.current_cord = new_cord

    def left(self):
        new_cord = (self.ngo(self.current_cord[0] - 1, "w"), self.current_cord[1])

        if new_cord not in self.uncrossable_cord_list:
            self.current_cord = new_cord

    def right(self):
        new_cord = (self.ngo(self.current_cord[0] + 1, "w"), self.current_cord[1])

        if new_cord not in self.uncrossable_cord_list:
            self.current_cord = new_cord

    def update_uncrossable_cord_list(self, uncrossable_cord_list):
        self.uncrossable_cord_list = uncrossable_cord_list

    def detect_keybind(self):
        if self.current_cord is None:
            return

        new_coord = None

        if keyboard.is_pressed("w") or keyboard.is_pressed("up"):
            self.up()
        elif keyboard.is_pressed("a") or keyboard.is_pressed("left"):
            self.left()
        elif keyboard.is_pressed("s") or keyboard.is_pressed("down"):
            self.down()
        elif keyboard.is_pressed("d") or keyboard.is_pressed("right"):
            self.right()

        if new_coord is not None:
            self.delay = True
            self.current_cord = new_coord

    def random_move(self, up_moveable, down_moveable, left_moveable, right_moveable):
        pass


class Block:
    def __init__(self, game_width, game_height):
        self.game_width = game_width
        self.game_height = game_height

        self.breakable = False
        self.break_level = 0
        self.block_id = None
        self.display_symbol = "E"
        self.game_width = game_width
        self.game_height = game_height

        self.parser_dict = {
            "id": self.parser_block_id,
            "display_symbol": self.parser_display_symbol,
            "breakable": self.parser_breakable,
            "break_level": self.parser_break_level,
        }

    def parser_block_id(self, line):
        match = re.match(r"id = (.*)", line)

        if match:
            self.block_id = match.groups()[0]


    def parser_display_symbol(self, line):
        match = re.match(r"display_symbol = (.*)", line)
        if match:
            self.display_symbol = match.groups()[0].replace("\"", "")


    def parser_breakable(self, line):
        match = re.match(r"breakable = (.*)", line)

        if match:
            if match.groups()[0] == "yes":
                self.breakable = True


    def parser_break_level(self, line):
        match = re.match(r"break_level = (\d+)", line)
        if match:
            self.break_level = int(match.groups()[0])


class PlayerEntityData:
    def __init__(self, hp=16, default_damage=1, enemies_id_list=None):
        if enemies_id_list is None:
            enemies_id_list = []
        self.id = "entity.tider.player"
        self.hp = hp
        self.default_damage = default_damage
        self.enemies_id_list = enemies_id_list

        self.ai_enable = False


class MonsterEntityData:
    def __init__(self, hp, default_damage=3, enemies_id_list=None):
        if enemies_id_list is None:
            enemies_id_list = ["entity.tider.player"]
        self.id = "entity.tider.monster"
        self.hp = hp
        self.default_damage = default_damage
        self.enemies_id_list = enemies_id_list

        self.ai_enable = True


class ControlDetector(threading.Thread):
    def __init__(self, object):
        threading.Thread.__init__(self, daemon=True)
        self.object = object

    def run(self):
        while True:
            time.sleep(self.object.move_delay)

            self.object.delay = False
            self.object.detect_keybind()
