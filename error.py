

class TiderMapFormatError(Exception):
    def __init__(self):
        self.message = "Map header is missing or data invalid."

    def __str__(self):
        return self.message