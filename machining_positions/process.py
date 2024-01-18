from machining_positions.load import SVGBezierLoader
from machining_positions.compute import (
    envelope_from_svg_points,
    machining_positions_and_distances_from_envelope,
    MachiningPositions,
    write,
)
from machining_positions.output import generate_plot
import matplotlib.pyplot as plt
import plotly.express as px
from tqdm import tqdm
import pandas as pd
from pathlib import Path


def main(input_path: str, output_folder: str, num_points: int, resolution: int, tqdm_instance=tqdm):
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    paths = SVGBezierLoader(input_path).load()
    envelope_array_dict = {}
    machining_positions_dict = {}
    for i, path in enumerate(tqdm_instance(paths)):
        envelope_array = envelope_from_svg_points(path, num_points)
        envelope_array_dict[i] = pd.DataFrame(envelope_array)
        machining_positions = MachiningPositions(envelope_array, resolution)
        machining_positions_dict[i] = pd.DataFrame(machining_positions.dataframe)
        machining_positions.write(output_folder / f"machining_positions_{i}.gecode")

    envelope_array_df = (
        pd.concat(envelope_array_dict)
        .rename(columns={0: "x", 1: "y"})
        .reset_index(level=0, names=("shape"))
    )
    machining_positions_df = (
        pd.concat(machining_positions_dict)
        .rename(columns={0: "x", 1: "y"})
        .reset_index(level=0, names=("shape"))
    )
    generate_plot(envelope_array_df, machining_positions_df, output_folder/"visualisation.html")
