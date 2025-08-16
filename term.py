import datetime
import os
import random
import re
import shutil
import string
import sys
import traceback
import keyboard

from error import TiderMapFormatError
from objectdefine import Entity, ControlDetector, Block

tider_version = "paper-2"


def get_terminal_size():
    try:
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 60


def clear():
    print("\033[H\033[J", end="")

class Map:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.name = "Unnamed Map"
        self.description = "No Description"

        self.data = []
        self.object_list = []
        self.block_map = {}

        self.control_thread = None


    def parser_map_data(self, full_map_data):
        found_map_header = False
        map_broken = False
        map_height = 0
        for line, index in zip(full_map_data.splitlines(), range(len(full_map_data))):
            if index == 0 and line == "!map_draw_start:":
                print("Found map header!")
                found_map_header = True
            elif line == "!map_draw_end:":
                print("Found map stop point! stopping...")
                break
            elif index == 1 and found_map_header:
                if line.startswith("XX"):
                    width = line.count("123456789") * 10
                    if width != self.width:
                        print("Map size is incorrect!")
                        map_broken = True
            else:
                if not found_map_header:
                    print("Missing map header...")
                    map_broken = True
                    break

                if (len(line)-2) != self.width:
                    print("Map size is incorrect!")
                    map_broken = True
                    continue

                map_height += 1
                if map_height == 10:
                    map_height = 1

                if not line.startswith(str(map_height)+":"):
                    print("Map index is incorrect!")
                    map_broken = True
                    continue

                line_cleaned = line.replace(str(map_height)+":", "")

                current_line = ""
                for char in line_cleaned:
                    if char == "~":
                        current_line += " "
                    else:
                        current_line += char
                self.data.append(current_line)

        if map_broken:
            return False

        return True

    def parser_map_size(self, text):
        pattern = r"map_size = (\d+)x(\d+)"
        match = re.match(pattern, text)
        if match:
            self.width = int(match.groups()[0]) * 10
            self.height = int(match.groups()[1]) * 10
        else:
            self.width, self.height = 0, 0

    def parser_map_map_name(self, text):
        pattern = r'map_name = "(.*)"'
        match = re.match(pattern, text)
        if match:
            self.name = match.groups()[0]
        else:
            self.name = "Unnamed Map"

    def parser_map_description(self, text):
        pattern = r'map_description = "(.*)"'
        match = re.match(pattern, text)

        if match:
            self.description = match.group(0)
        else:
            self.description = "No Description"

    def parser_map_object_list(self, object_data_list):
        require_control_thread = False
        require_control_thread_obj_list = []
        for object_data in object_data_list:
            lines = object_data.split("\n")
            if object_data.count("!define_start:") != 1 and object_data.count("!define_end") != 1:
                continue

            object_id_line = lines[2]

            match = re.match(r"id = (.*)", object_id_line)

            if not match:
                match = re.match(r"id = \"(.*)\"", object_id_line)

            if not match:
                continue

            object_id = match.groups()[0].replace("\"", "")

            line = lines.remove("!define_start:")
            line = lines.remove("!define_end:")

            if object_id.startswith("entity"):
                entity = Entity(self.width, self.height)

                for line in lines:
                    for key in entity.parser_dict.keys():
                        if line.startswith(key):
                            func = entity.parser_dict[key]
                            func(line)

                self.object_list.append(entity)

                if entity.can_control_by_user and not require_control_thread:
                    require_control_thread = True
                    require_control_thread_obj_list.append(entity)
                elif entity.can_control_by_user:
                    require_control_thread_obj_list.append(entity)
            elif object_id.startswith("block"):
                block = Block(self.width, self.height)
                for line in lines:
                    for key in block.parser_dict.keys():
                        if line.startswith(key):
                            func = block.parser_dict[key]
                            func(line)

                self.block_map[block.display_symbol] = block


        if require_control_thread:
            self.control_thread = ControlDetector(require_control_thread_obj_list[0])
            self.control_thread.start()

        return True

def load_map(map_filepath):
    if not os.path.exists(map_filepath):
        raise FileNotFoundError(map_filepath)

    with open(map_filepath, mode="r", encoding="utf-8") as map_file:
        map_data = map_file.read()

    parser_list = []

    map = Map()

    parser_dict = {
        "map_size": map.parser_map_size,
        "map_name": map.parser_map_map_name,
        "map_description": map.parser_map_description,
    }

    index = 0

    full_map_data = ""
    found_map_herder = False

    define_start = False
    define_list = []
    current_define = ""

    for line in map_data.splitlines():
        index += 1

        line = line.strip()
        if line.startswith("#"):
            continue

        if index == 1 and line != "#!im_tider_map":
            raise TiderMapFormatError()

        if line.startswith("!map_draw_start"):
            found_map_herder = True
            full_map_data += line + "\n"
        elif line.startswith("!map_draw_end:"):
            full_map_data += line + "\n"
            found_map_herder = False
        elif line.startswith("!define_start"):
            define_start = True
            current_define += line + "\n"
        elif line.startswith("!define_end:"):
            define_start = False
            current_define += line
            define_list.append(current_define)
            current_define = ""
        elif found_map_herder:
            full_map_data += line + "\n"
        elif define_start:
            current_define += line + "\n"
        elif not line.startswith("!"):
            for parser_text in parser_dict:
                if line.startswith(parser_text):
                    func = parser_dict[parser_text]
                    parser_list.append({"data": line, "parser": func})

    for parser_item in parser_list:
        data = parser_item["data"]
        func = parser_item["parser"]

        func(data)

    status_code = map.parser_map_data(full_map_data)

    if not status_code:
        raise TiderMapFormatError()

    status_code = map.parser_map_object_list(define_list)

    if not status_code:
        raise TiderMapFormatError()

    return map


def render_map(map_object: Map, debug=False):
    multi_d_array = []  # multidimensional
    data = map_object.data
    uncrossable_coord_list = []

    # First time render (Render space and block)
    for line, y in zip(data, range(0, len(data))):
        current_line_list = []

        for char, x in zip(line, range(0, len(line))):
            coord = (x, y)
            used = False

            current_block = map_object.block_map.get(char, None)
            if current_block is not None:
                current_line_list.append(current_block.display_symbol)
                used = True
                uncrossable_coord_list.append(coord)

            if not used:
               current_line_list.append(char)

        multi_d_array.append(current_line_list)

    # Second time render (Render entity)
    new_array = []
    for line, y in zip(multi_d_array, range(0, len(multi_d_array))):
        current_line_list = []
        for char, x in zip(line, range(0, len(line))):
            used = False
            coord = (x, y)

            for entity in map_object.object_list:
                if entity.current_cord == coord:
                    current_line_list.append(entity.display_symbol)
                    entity.update_uncrossable_cord_list(uncrossable_coord_list)
                    used = True

            if not used:
                current_line_list.append(char)

        new_array.append(current_line_list)


    buffer = []
    for line in new_array:
        current_line = ""
        for char in line:
            current_line += char
        buffer.append(current_line)

    return buffer


def main():
    debug = True
    fps_count = 0
    freeze_fps = "Counting > (If you fps stuck at \"Counting\", try restarting the game)"
    reset_time = datetime.datetime.now()
    current_map = None
    try:
        path = str(input("Enter the map path: "))
        current_map = load_map(path)
        print("Map Info")
        print("Name: {}".format(current_map.name))
        print("Description: {}".format(current_map.description))
        input("Press enter to start game...")
    except TiderMapFormatError:
        print("Map format is not correct.")
        sys.exit(1)

    while True:
        buffer = ["Tider > Version {}".format(tider_version)] # Terminal Dynamic Printer

        terminal_size = get_terminal_size()
        buffer.append(f"Terminal width: {terminal_size[0]} height: {terminal_size[1]}")

        wall_width = int(terminal_size[0] * 0.85)
        wall_height = int(terminal_size[1] * 0.85)

        game_draw_width = current_map.width
        game_draw_height = current_map.height

        if current_map is not None:
            game_draw_width = current_map.width
            game_draw_height = current_map.height

        min_height = current_map.height+9 if debug else current_map.height+5
        min_width = current_map.width+4 if debug else current_map.width

        buffer.append("Current map size: {}x{} char as {}x{} cm".format(game_draw_width, game_draw_height,
                                                                    int(game_draw_width / 10), int(game_draw_height / 10)))


        def print_width_index():
            if debug:
                index_count = 0
                width_index_info = ""
                for t in range(0, int(game_draw_width / 9) + 1):
                    for i in range(1, 10):
                        width_index_info += str(i)

                        if index_count == game_draw_width - 1:
                            break
                        else:
                            index_count += 1
                buffer.append(width_index_info)
        print_width_index()

        # Print top wall
        buffer.append(""+"=" * game_draw_width)

        # Game render place
        if terminal_size[1] < min_height:
            buffer.append("Stop rendering game because window size is too small.")
        elif terminal_size[0] < min_width:
            buffer.append(str(min_width))
            buffer.append("Stop rendering game because window size is too small.")
        else:
            buffer.extend(render_map(current_map, debug=debug))

        # Print bottom wall
        buffer.append(""+"=" * game_draw_width)

        print_width_index()

        now = datetime.datetime.now()

        if (now.second - reset_time.second) == 1:
            freeze_fps = fps_count
            buffer.append("FPS: {}".format(freeze_fps))
            fps_count = 0
            reset_time = datetime.datetime.now()
        else:
            fps_count += 1
            buffer.append("FPS: {}".format(freeze_fps))

        print("\033[H\033[J" + "\n".join(buffer))

        del buffer


def test():
    new_map = load_map("map.tm")
    print(new_map.data)

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "-test":
        main_func = test
    else:
        main_func = main

    try:
        main_func()
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)
    except Exception as _:
        print("Unexpected error:", sys.exc_info()[0])
        traceback.print_exc()
