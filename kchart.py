import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import argparse
import os
import pytz

# Argument parser to allow external file input
parser = argparse.ArgumentParser(description="Run Dash app with external data file")
parser.add_argument('--file', required=True, help="Path to the CSV data file")
args = parser.parse_args()

# Load OHLC data from the provided file path
data_path = args.file
data = pd.read_csv(data_path, encoding='big5')
data['datetime'] = pd.to_datetime(data['成交日期'] + ' ' + data['成交時間'])

# Resample data to 1-minute intervals for OHLC
ohlc_data = data.set_index('datetime').resample('min').agg({
    '成交價格': ['first', 'max', 'min', 'last']
}).dropna()
ohlc_data.columns = ['開盤價', '最高價', '最低價', '收盤價']
ohlc_data.reset_index(inplace=True)

# Extract the date from the input file for annotation
file_date = pd.Timestamp(os.path.basename(data_path).split('.')[0][-8:])

# Load trade log data from the corresponding backtest directory
trade_log_path = os.path.join("backtest", os.path.basename(data_path).replace(".csv", "-tradelog.csv"))
if os.path.exists(trade_log_path):
    trade_log = pd.read_csv(trade_log_path)

    # Combine file_date with Entry Time and Close Time
    trade_log['Entry Time'] = pd.to_datetime(file_date.strftime('%Y-%m-%d') + ' ' + trade_log['Entry Time'])
    trade_log['Close Time'] = pd.to_datetime(file_date.strftime('%Y-%m-%d') + ' ' + trade_log['Close Time'])

    # Prepare entry points and close points
    entry_points = trade_log[trade_log['Trade ID'].notna()]
    close_points = trade_log[(trade_log['Trade ID'].isna()) & (trade_log['Type'] == 'Close All')]
else:
    print(f"Trade log not found at {trade_log_path}")
    entry_points = pd.DataFrame()
    close_points = pd.DataFrame()

# Create initial candlestick chart
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=ohlc_data['datetime'],
    open=ohlc_data['開盤價'],
    high=ohlc_data['最高價'],
    low=ohlc_data['最低價'],
    close=ohlc_data['收盤價'],
    increasing_line_color='red',
    decreasing_line_color='green'
))

# Add entry points to the chart
for _, row in entry_points.iterrows():
    arrow_color = 'red' if row['Type'] == 'Buy' else 'green'
    fig.add_annotation(
        x=row['Entry Time'],
        y=row['Entry Price'],
        ax=0,
        ay=-40,
        xref="x",
        yref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=2,
        arrowwidth=2,
        arrowcolor=arrow_color,
        bgcolor="white",
        bordercolor="black",
        borderwidth=2,
        text=""
    )

# Add close points to the chart
for _, row in close_points.iterrows():
    fig.add_annotation(
        x=row['Close Time'],
        y=row['Close Price'],
        ax=0,
        ay=-40,
        xref="x",
        yref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=2,
        arrowwidth=2,
        arrowcolor="black",
        bgcolor="white",
        bordercolor="black",
        borderwidth=2,
        text=""
    )

fig.update_layout(
    title="Interactive 1-Minute K-Line Chart with Trade Annotations",
    xaxis_title="Time",
    yaxis_title="Price",
    xaxis=dict(rangeslider=dict(visible=False)),
    yaxis=dict(tickformat="d"),  # Ensure Y-axis values are displayed as integers
    hovermode="x unified",
    height=800  # Increase the height of the canvas
)

# Initialize Dash app
app = dash.Dash(__name__)
horizontal_lines = []

app.layout = html.Div([
    dcc.Graph(
        id='kline-chart',
        figure=fig,
        config={"scrollZoom": True}  # Enable zooming and panning
    ),
    html.Button("Clear All Lines", id="clear-all", n_clicks=0),
    html.Button("Clear Last Line", id="clear-last", n_clicks=0),
    html.Div(id='debug-output', style={'whiteSpace': 'pre-wrap'}),  # Div to show debug output
])

# Unified callback to handle all figure updates
@app.callback(
    [Output('kline-chart', 'figure'), Output('debug-output', 'children')],
    [
        Input('kline-chart', 'clickData'),
        Input('clear-all', 'n_clicks'),
        Input('clear-last', 'n_clicks')
    ],
    [State('kline-chart', 'figure')],
    prevent_initial_call=True
)
def update_figure(clickData, clear_all_clicks, clear_last_clicks, current_fig):
    global horizontal_lines
    ctx = dash.callback_context
    debug_message = "Callback triggered by: {}\n".format(ctx.triggered[0]['prop_id'])

    # Handle adding horizontal lines
    if ctx.triggered[0]['prop_id'] == 'kline-chart.clickData':
        debug_message += "clickData content: {}\n".format(clickData)
        if clickData and 'points' in clickData and len(clickData['points']) > 0:
            point = clickData['points'][0]
            debug_message += "Point keys: {}\n".format(list(point.keys()))
            if 'y' in point:
                y_value = point['y']  # Use the exact cursor Y value
            else:
                y_value = point.get('close', None)  # Fallback to 'close' value if 'y' is not present
                debug_message += "'y' not found, fallback to 'close': {}\n".format(y_value)

            if y_value is not None:
                debug_message += "Y-Value used for horizontal line: {}\n".format(y_value)

                # Ensure x0 and x1 are properly set
                x0 = current_fig['layout']['xaxis']['range'][0] if 'range' in current_fig['layout']['xaxis'] else ohlc_data['datetime'].iloc[0]
                x1 = current_fig['layout']['xaxis']['range'][1] if 'range' in current_fig['layout']['xaxis'] else ohlc_data['datetime'].iloc[-1]
                debug_message += "x0: {}, x1: {}\n".format(x0, x1)

                # Add a horizontal line at the clicked Y value
                new_line = dict(
                    type="line",
                    x0=x0,
                    x1=x1,
                    y0=y_value,
                    y1=y_value,
                    line=dict(color="blue", width=2, dash="dash"),
                    editable=True  # Allow selecting the line
                )
                horizontal_lines.append(new_line)
                debug_message += "Horizontal line added. Total lines: {}\n".format(len(horizontal_lines))
            else:
                debug_message += "No valid Y-Value found for horizontal line.\n"

    # Handle clearing all lines
    elif ctx.triggered[0]['prop_id'] == 'clear-all.n_clicks':
        horizontal_lines = []
        debug_message += "All lines cleared.\n"

    # Handle clearing the last line
    elif ctx.triggered[0]['prop_id'] == 'clear-last.n_clicks':
        if horizontal_lines:
            horizontal_lines.pop()
            debug_message += "Last line cleared. Total lines: {}\n".format(len(horizontal_lines))

    # Update figure shapes
    current_fig['layout']['shapes'] = horizontal_lines
    debug_message += "Current figure shapes: {}\n".format(current_fig['layout']['shapes'])
    return current_fig, debug_message

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
