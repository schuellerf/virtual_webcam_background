import filters
import numpy as np


class Roll:
    @classmethod
    def config(cls):
        return {
            "Horizontal Speed": {"type": "numeric", "range": [-200, 200], "input": True, "default": 0},
            "Vertical Speed": {"type": "numeric", "range": [-200, 200], "input": True, "default": 0}
        }

    def __init__(self, speed_x, speed_y, *args, **kwargs):
        self.position_x = 0
        self.position_y = 0
        self.speed_x = speed_x
        self.speed_y = speed_y

    def apply(self, *args, **kwargs):
        frame = kwargs['frame']
        self.position_x = (self.position_x + self.speed_x) % frame.shape[1]
        self.position_y = (self.position_y + self.speed_y) % frame.shape[0]
        return np.roll(frame,
                       shift=(self.position_x, self.position_y),
                       axis=(1, 0))


filters.register_filter("roll", Roll)
