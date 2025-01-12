"""
File that checks if a point lies on a line segment.
"""

def check_lines_on_segment(p, q, r):
    """
    Check if point q lies on the line segment defined by points p and r.

    Args:
        p (tuple): A tuple representing the coordinates of the first endpoint of the segment 
            (x1, y1).
        q (tuple): A tuple representing the coordinates of the point to check (x2, y2).
        r (tuple): A tuple representing the coordinates of the second endpoint of the segment 
            (x3, y3).

    Returns:
        bool: True if point q lies on the line segment defined by points p and r, 
            False otherwise.
    """
    if ( (q[0] <= max(p[0], r[0])) and (q[0] >= min(p[0], r[0])) and
            (q[1] <= max(p[1], r[1])) and (q[1] >= min(p[1], r[1]))):
        return True
    return False
