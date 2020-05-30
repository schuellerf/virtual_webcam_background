import cv2
import filters


class Blur:
    @classmethod
    def config(cls):
        return {
            "intensity_x": {"type": "numeric", "range": [0, 100], "default": 5},
            "intensity_y": {"type": "numeric", "range": [0, 100], "default": 5}
        }

    def __init__(self, intensity_x=5, intensity_y=-1, *args, **kwargs):
        self.intensity_x = intensity_x
        if intensity_y > 0:
            self.intensity_y = intensity_y
        else:
            self.intensity_y = intensity_x

    def apply(self, *args, **kwargs):
        frame = kwargs['frame']
        if self.intensity_x <= 0 and self.intensity_y <= 0:
            return frame
        # Do not blur the alpha channel
        frame[:,:,:3] = cv2.blur(frame[:,:,:3],
                (self.intensity_x, self.intensity_y))
        return frame


filters.register_filter("blur", Blur)
