from functools import cached_property
import numpy as np
import pandas as pd
import bezier
from scipy.spatial import Voronoi, distance as scipy_distance
from shapely import Polygon, Point, distance, LineString
from typing import List, Literal
from svgpathtools.path import Path


def envelope_from_excel_points(points, num_points):
    bezier_curve_list = [
        bezier.Curve(
            bezier_points,
            degree=3,
        )
        for bezier_points in points
    ]
    array_0_1 = np.linspace(0, 1, num_points)
    bezier_evaluation_list = []
    for bezier_curve in bezier_curve_list:
        bezier_evaluation_list.append(bezier_curve.evaluate_multi(array_0_1).T)
    envelope_array = np.concatenate(bezier_evaluation_list)
    return envelope_array


def envelope_from_svg_points(path: Path, num_points: int):
    array_0_1 = np.linspace(0, 1, num_points)
    envelope_points = []
    for shape in path:
        try:
            envelope_points.append(shape.points(array_0_1))
        except AttributeError:
            envelope_points.append([shape.point(value) for value in array_0_1])
    envelope_array = np.concatenate(envelope_points)
    # Convert numpy array of complex numbers to array of arrays of floats (x, y)
    envelope_array = np.array([[point.real, point.imag] for point in envelope_array])
    return envelope_array


def machining_positions_and_distances_from_envelope(envelope_array, resolution=1):
    polygon_evaluations = Polygon(envelope_array)
    linestring_evaluations = LineString(envelope_array)
    evaluations_list = [
        linestring_evaluations.line_interpolate_point(step)
        for step in np.arange(0, linestring_evaluations.length, resolution)
    ]
    evaluations_array = np.array([[point.x, point.y] for point in evaluations_list])
    vor = Voronoi(evaluations_array)
    inside_vertices = []
    inside_vertices_distance = []
    for vertex in vor.vertices:
        point = Point(vertex)
        if polygon_evaluations.contains(Point(vertex)):
            inside_vertices.append(vertex)
            inside_vertices_distance.append(distance(point, linestring_evaluations))
    inside_vertices = np.array(inside_vertices)
    inside_vertices_distance = np.array(inside_vertices_distance)
    return inside_vertices, inside_vertices_distance


class MachiningPositions:
    z_0 = 5

    def __init__(self, envelope_array: np.ndarray, resolution: float = 1) -> None:
        self.envelope_array = envelope_array
        self.resolution = resolution

    @cached_property
    def polygon_envelope(self):
        return Polygon(self.envelope_array)

    @cached_property
    def linestring_envelope(self):
        return LineString(self.envelope_array)
    
    @cached_property
    def envelope_sampling(self):
        evaluations_list = [
            self.linestring_envelope.line_interpolate_point(step)
            for step in np.arange(0, self.linestring_envelope.length, self.resolution)
        ]
        evaluations_array = np.array([[point.x, point.y] for point in evaluations_list])
        return evaluations_array

    @cached_property
    def vertices(self):
        vor = Voronoi(self.envelope_sampling)
        inside_vertices = []
        inside_vertices_distance = []
        for vertex in vor.vertices:
            if self.polygon_envelope.contains(Point(vertex)):
                inside_vertices.append(vertex)
        inside_vertices = np.array(inside_vertices)

        return inside_vertices, inside_vertices_distance

    @cached_property
    def ordered_vertices(self):
        return self.order_vertices(self.vertices)

    @staticmethod
    def closest_point(point, points):
        distances = scipy_distance.cdist([point], points)
        index_closest = distances.argmin()
        distance_closest = distances[0, index_closest]
        return points[index_closest], index_closest, distance_closest

    @classmethod
    def order_vertices(cls, vertices: np.ndarray) -> np.ndarray:
        start_index = vertices.argmin(axis=0)[0]
        start_point = vertices[start_index]
        # Find the closest point to the start point that is not the start point
        # machining_positions is a numpy array, so we have to index it properly to
        # remove only start_index from the search
        search_positions = vertices[np.arange(len(vertices)) != start_index]
        ordered_points_all = []
        ordered_points_subset = [start_point]
        current_distances = []
        while len(search_positions) > 0:
            next_point, next_index, next_distance = cls.closest_point(
                start_point, search_positions
            )
            search_positions = search_positions[
                np.arange(len(search_positions)) != next_index
            ]
            current_distances.append(next_distance)
            if next_distance > 5 * sum(current_distances) / len(current_distances):
                ordered_points_all.append(ordered_points_subset)
                ordered_points_subset = []
                current_distances = []
            ordered_points_subset.append(next_point)
            start_point = next_point
        ordered_points_all.append(ordered_points_subset)
        return ordered_points_all

    def distance_to_envlope(self, points: np.ndarray) -> np.ndarray:
        return np.array(
            [self.linestring_envelope.distance(Point(point)) for point in points]
        )

    @property
    def dataframe(self) -> pd.DataFrame:
        dataframe_list = []
        for ordered_vertices_subset in self.ordered_vertices:
            inside_vertices_distance = self.distance_to_envlope(ordered_vertices_subset)
            dataframe_list.append(
                self.dataframe_from_machining_positions_and_distances(
                    ordered_vertices_subset, inside_vertices_distance
                )
            )
        return pd.concat(dataframe_list, axis=0, ignore_index=True)

    def write(self, path: str):
        self.dataframe.apply(self.format_line, axis=1).to_csv(
            path, index=False, header=False
        )

    @classmethod
    def format_line(cls, line):
        return f'G{line["type"]} X{line["x"]} Y{line["y"]} Z{line["z"]}'

    def __repr__(self) -> str:
        return f"MachiningPositions(vertices={self.vertices}, distance={self.distance})"

    @classmethod
    def dataframe_from_machining_positions_and_distances(
        cls, inside_vertices, inside_vertices_distance
    ):
        first_line_df = pd.DataFrame()
        first_line_df["type"] = "0"
        first_line_df["x"] = inside_vertices[0, 0]
        first_line_df["y"] = inside_vertices[0, 1]
        first_line_df["z"] = cls.z_0

        middle_df = pd.DataFrame()
        middle_df[["x", "y"]] = pd.DataFrame(inside_vertices)
        middle_df["distance"] = inside_vertices_distance
        middle_df["z"] = -middle_df["distance"]
        middle_df["type"] = "1"

        last_line_df = pd.DataFrame()
        last_line_df["type"] = "0"
        last_line_df["x"] = inside_vertices[-1, 0]
        last_line_df["y"] = inside_vertices[-1, 1]
        last_line_df["z"] = cls.z_0

        output_df = pd.concat(
            [first_line_df, middle_df, last_line_df], axis=0, ignore_index=True
        )
        return output_df


def write(path: str, df: pd.DataFrame):
    def format_line(line):
        return f'{line["type"]} X{line["x"]} Y{line["y"]} Z{line["z"]}'

    df.apply(format_line, axis=1).to_csv(path, index=False, header=False)
