"""
File that implements the calc_distance function.
"""

import math

def calc_distance(p1, p2):
    """
    Calculate the Euclidean distance between two points.

    Args:
        p1 (tuple): The first point as a tuple of (x, y) coordinates.
        p2 (tuple): The second point as a tuple of (x, y) coordinates.

    Returns:
        float: The Euclidean distance between the two points.
    """
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
