"""
File that checks if two line segments intersect.
"""

from .check_lines_orientation import check_lines_orientation
from .check_lines_on_segment import check_lines_on_segment

def check_lines_intersection(p1, q1, p2, q2):
    """
    Check if two lines (or segments) intersect.

    This function determines if the line segment 'p1q1' and 'p2q2' intersect.
    It uses the orientation method to check for general and special cases of intersection.

    Parameters:
    p1 (tuple): The first point of the first line segment.
    q1 (tuple): The second point of the first line segment.
    p2 (tuple): The first point of the second line segment.
    q2 (tuple): The second point of the second line segment.

    Returns:
    bool: True if the line segments intersect, False otherwise.
    """
    # Find the 4 orientations required for
    # the general and special cases
    o1 = check_lines_orientation(p1, q1, p2)
    o2 = check_lines_orientation(p1, q1, q2)
    o3 = check_lines_orientation(p2, q2, p1)
    o4 = check_lines_orientation(p2, q2, q1)
    # General case
    if ((o1 != o2) and (o3 != o4)):
        return True
    # Special Cases
    # p1 , q1 and p2 are colinear and p2 lies on segment p1q1
    if ((o1 == 0) and check_lines_on_segment(p1, p2, q1)):
        return True
    # p1 , q1 and q2 are colinear and q2 lies on segment p1q1
    if ((o2 == 0) and check_lines_on_segment(p1, q2, q1)):
        return True
    # p2 , q2 and p1 are colinear and p1 lies on segment p2q2
    if ((o3 == 0) and check_lines_on_segment(p2, p1, q2)):
        return True
    # p2 , q2 and q1 are colinear and q1 lies on segment p2q2
    if ((o4 == 0) and check_lines_on_segment(p2, q1, q2)):
        return True
    # If none of the cases
    return False
