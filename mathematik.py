from typing import Tuple, Iterable


def generate_route(c_from: Tuple[float, float],
                   c_to: Tuple[float, float],
                   steps: int) -> Iterable[Tuple[float, float]]:
    """
    Ultra verbose python example
    returns a list of coordinate tuple between the points

    same as
    def calc_route(c_from, c_to, steps: int):
    """
    d_x = c_to[0] - c_from[0]
    d_y = c_to[1] - c_from[1]
    x_step = d_x / steps
    y_step = d_y / steps

    return [(c_from[0] + i * x_step, c_from[1] + i * y_step) for i in range(steps)]

