import pandas as pd
import numpy as np
from typing import List
from svgpathtools import svg2paths
from svgpathtools.path import Path


class ExcelBezierLoader:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> List[List[np.ndarray]]:
        """
        Load Bezier points from an Excel file.

        Returns
        -------
            A list of lists, where each inner list represents a set of
            Bezier points. Each Bezier point is represented as a 2D numpy
            array of shape (2, 4), where each column represents the x and y
            coordinates of the control points.

        Raises
        ------
            ValueError: If the first line of the Bezier Excel point is not
            of type M (Move).
        """
        bezier_df = pd.read_excel(self.path)
        if not all(
            map(
                lambda col: col in bezier_df.columns,
                ["Type", "P0X", "P0Y", "P1X", "P1Y", "P2X", "P2Y", "P3X", "P3Y"],
            )
        ):
            raise ValueError(
                "Bezier Excel should have the following columns: "
                "Type, P0X, P0Y, P1X, P1Y, P2X, P2Y, P3X, P3Y."
            )
        bezier_points_list = []
        bezier_points = None
        for row in bezier_df.itertuples():
            if row.Type == "M":
                if bezier_points is not None:
                    bezier_points_list.append(bezier_points)
                bezier_points = []
                continue
            elif bezier_points is None:
                raise ValueError(
                    "First line of Bezier Excel point should be of type M"
                    f" (Move), found {row.Type}."
                )
            single_bezier_point = np.array(
                [
                    [row.P0X, row.P0Y],
                    [row.P1X, row.P1Y],
                    [row.P2X, row.P2Y],
                    [row.P3X, row.P3Y],
                ]
            ).T
            bezier_points.append(single_bezier_point)
        bezier_points_list.append(bezier_points)
        return bezier_points_list

class SVGBezierLoader:
    def __init__(self, path: str):
        self.path = path
    
    def load(self) -> List[Path]:
        paths, _ = svg2paths(self.path)
        return paths