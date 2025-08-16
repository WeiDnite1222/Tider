import datetime
import os
import random
import re
import shutil
import string
import sys
import traceback

from error import TiderMapFormatError

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

                self.data.append(line_cleaned)


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
            self.name = match.group(0)
        else:
            self.name = "Unnamed Map"


    def parser_map_description(self, text):
        pattern = r'map_description = "(.*)"'
        match = re.match(pattern, text)

        if match:
            self.description = match.group(0)
        else:
            self.description = "No Description"


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
        elif found_map_herder:
            full_map_data += line + "\n"
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

    return map

def render_game(game_draw_width, game_draw_height, debug=False):
    buffer = []
    start_pos = 0,0
    # -1是因為從0,0 開始畫
    end_pos = game_draw_width-1, game_draw_height-1

    # random_symbol = ["@", "#", "$", "%", "*", "~"]
    # line += "{}".format(random.choice(random_symbol))*game_draw_width

    class Line:
        def __init__(self, start_pos, end_pos, display_symbol="#"):
            self.start_pos = start_pos
            self.end_pos = end_pos

            self.type = "entity.line.tider"

            # 計算斜率 (delta_x / delta_y)
            dx = self.end_pos[0] - self.start_pos[0]
            dy = self.end_pos[1] - self.start_pos[1]
            if dy != 0:
                self.y_offset = dx / dy  # 每增加 1 行，水平移動多少
            else:
                self.y_offset = 0

            # 如果想允許一些誤差，可以用範圍
            self.y_offset_allow_range = [self.y_offset]

            self.display_symbol = display_symbol

        def render_check(self, pixel_coord):
            x_pos = pixel_coord[0]
            y_pos = pixel_coord[1]

            # 修正範圍檢查
            if (self.start_pos[0] <= x_pos <= self.end_pos[0] and
                    self.start_pos[1] <= y_pos <= self.end_pos[1]):
                for offset in self.y_offset_allow_range:
                    # 預期 x = x_start + offset*(y - y_start)
                    expected_x = self.start_pos[0] + offset * (y_pos - self.start_pos[1])
                    if x_pos == round(expected_x):
                        return True

            return False

    line_a = Line(start_pos, end_pos)

    entities = []
    symbol_list = list(string.printable)

    for i in range(1, 10):
        a = random.randint(1, game_draw_width)
        b = random.randint(1, game_draw_width)
        pos = (a, b)
        line = Line(pos, pos
             , display_symbol=random.choice(symbol_list))
        entities.append(line)

    #V2
    for y in range(0, game_draw_height):
        current_line = ""

        if debug:
            index = str(y).zfill(3)
            current_line += index

        # "Rendering" entities starts here
        for x in range(0, game_draw_width):
            pixel_pos = x,y

            used = False
            for entity in entities:
                result = entity.render_check(pixel_pos)
                if result:
                    current_line += entity.display_symbol
                # if result and not used:
                #
                #     used = True
                # elif result and used:
                #     current_line = current_line[:-1] + entity.display_symbol

            if not used:
                current_line += " "

        buffer.append(current_line)

    return buffer


def render_map(map_object: Map, debug=False):
    buffer = []
    for line, y in zip(map_object.data, range(0, len(map_object.data))):
        current_line = ""
        if debug:
            index = str(y).zfill(3)
            current_line += index + line
        else:
            current_line += line

        buffer.append(current_line)

    return buffer


def main():
    debug = False
    fps_count = 0
    freeze_fps = "Counting"
    reset_time = datetime.datetime.now()
    current_map = None
    try:
        path = str(input("Enter the map path: "))
        current_map = load_map(path)
    except TiderMapFormatError:
        print("Map format is not correct.")
        sys.exit(1)

    while True:
        buffer = ["Tider > Version {}".format(tider_version)] # Terminal Dynamic Printer

        terminal_size = get_terminal_size()
        buffer.append(f"Terminal width: {terminal_size[0]} height: {terminal_size[1]}")

        wall_width = int(terminal_size[0] * 0.85)
        wall_height = int(terminal_size[1] * 0.85)

        game_draw_width = wall_width - 0
        game_draw_height = wall_height - 2

        if current_map is not None:
            game_draw_width = current_map.width
            game_draw_height = current_map.height

        min_height = current_map.height+9 if debug else current_map.height+5
        min_width = current_map.width+4 if debug else current_map.width

        buffer.append("Max map size: {}x{} char as {}x{} cm".format(game_draw_width, game_draw_height,
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
                buffer.append("###" + width_index_info)
        print_width_index()

        # Print top wall
        buffer.append("XXX"+"=" * wall_width if debug else ""+"=" * wall_width)

        # Game render place
        if terminal_size[1] < min_height:
            buffer.append("Stop rendering game because window size is too small.")
        elif terminal_size[0] < min_width:
            buffer.append(str(min_width))
            buffer.append("Stop rendering game because window size is too small.")
        else:
            if current_map is not None:
                buffer.extend(render_map(current_map, debug=debug))
            else:
                buffer.extend(render_game(game_draw_width, game_draw_height, debug=debug))

        # Print bottom wall
        buffer.append("XXX"+"=" * wall_width if debug else ""+"=" * wall_width)

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
