"""A line's saved color is determined by its per-security allocation, never focus."""
import colorsys

LINE_COLORS = (
    (1.0,.74,.36,1), (.59,.64,1,1), (1,.49,.62,1),
    (.42,.76,1,1), (.78,.58,.96,1), (.60,.84,.42,1),
    (1,.62,.40,1), (.38,.84,.92,1),
)


def line_color(index):
    if index < len(LINE_COLORS):
        return LINE_COLORS[index]
    return (*colorsys.hsv_to_rgb((index*.61803398875+.13)%1,.52,.98),1)
