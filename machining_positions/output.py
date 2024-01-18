import plotly.express as px
import pandas as pd

def generate_plot(envelope_array_df: pd.DataFrame, machining_positions_df: pd.DataFrame, output_path = None):
    # Create the line plot
    fig = px.line(envelope_array_df, x="x", y="y", color="shape")

    for shape in machining_positions_df["shape"].unique():
        mask_shape = machining_positions_df["shape"] == shape
        n_sample = int(0.2 * mask_shape.sum())
        machining_positions_shape = machining_positions_df[mask_shape].sample(n_sample)
        fig.add_scatter(
            x=machining_positions_shape["x"],
            y=machining_positions_shape["y"],
            mode="markers",
        )
    fig.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
    )
    if output_path is not None:
        fig.write_html(output_path)