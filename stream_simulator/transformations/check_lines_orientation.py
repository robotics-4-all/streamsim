"""
File that contains the check_lines_orientation function.
"""

def check_lines_orientation(p, q, r):
    """
    Determines the orientation of the triplet (p, q, r).

    Parameters:
    p (tuple): The first point as a tuple (x, y).
    q (tuple): The second point as a tuple (x, y).
    r (tuple): The third point as a tuple (x, y).

    Returns:
    int: Returns 1 if the orientation is clockwise, 
            2 if the orientation is counterclockwise, 
            and 0 if the points are collinear.
    """
    val = (float(q[1] - p[1]) * (r[0] - q[0])) - \
        (float(q[0] - p[0]) * (r[1] - q[1]))
    if val > 0:
        # Clockwise orientation
        return 1
    if val < 0:
        # Counterclockwise orientation
        return 2
    # Colinear orientation
    return 0
