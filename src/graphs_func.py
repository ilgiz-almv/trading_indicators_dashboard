import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np

# Set the default style for seaborn plots
sns.set_style("whitegrid")

# Define quantile thresholds for filtering data
UPPER_QUANTILE = 0.97
LOWER_QUANTILE = 0.03

# Default step for Y-axis ticks
Y_TICKS_STEP_DEFAULT = 6


class IndexCounter:
    """
    A simple counter class to keep track of an index value.
    """
    def __init__(self, start=0):
        self.i = start

    def i_next(self):
        """Increment the index counter and return the new value."""
        self.i += 1
        return self.i

    def i_curr(self):
        """Return the current index value."""
        return self.i

    def reset(self):
        """Reset the index counter to zero."""
        self.i = 0


def get_font_size(text):
    """
    Determine an appropriate font size based on the length of the input text.

    Parameters:
    text (str): The input text.

    Returns:
    int: Suggested font size.
    """
    length = len(text)
    if length <= 14:
        return 10
    elif length <= 18:
        return 9
    elif length <= 22:
        return 8
    else:
        return 7


def calculate_quarterly_dates(df, shift_back_days=18):
    """
    Calculate specific quarterly dates by finding the last Friday of each quarter's last month
    and shifting it back by a given number of days.

    Parameters:
    df (pd.DataFrame): DataFrame with a DatetimeIndex.
    shift_back_days (int): Number of days to subtract from the last Friday of each quarter.

    Returns:
    pd.Series: A series containing the selected quarterly dates.
    """
    quarter_months = [3, 6, 9, 12]  # March, June, September, December
    dates = []

    # Loop through each quarter month within the DataFrame's year range
    for quarter_month in quarter_months:
        for year in range(df.index.year.min(), df.index.year.max() + 1):
            # Determine the last day of the given quarter month
            last_day = pd.Timestamp(year, quarter_month, 1) + pd.offsets.MonthEnd(0)

            # Find the last Friday of the month
            if last_day.weekday() == 4:  # If already a Friday
                last_friday = last_day
            else:
                last_friday = last_day - pd.offsets.Week(weekday=4)

            # Shift the date back by the given number of days
            target_day = last_friday - pd.Timedelta(days=shift_back_days)

            # Ensure the target day exists within the DataFrame index
            if target_day in df.index:
                dates.append(target_day)

    return pd.Series(dates)


def plot_vertical_lines(ax, dates):
    """
    Draw vertical dashed lines on a given plot at specified dates.

    Parameters:
    ax (matplotlib.axes.Axes): The axis on which to plot the lines.
    dates (list or pd.Series): The dates where vertical lines should be drawn.
    """
    for date in dates:
        ax.axvline(x=date, color='black', linestyle='--', lw=1, alpha=0.35)


def setup_x_axis(ax, start_date_obj, end_date_obj, t_freq):
    """
    Configure the X-axis of a plot by setting date limits, tick marks, and formatting labels.

    Parameters:
    ax (matplotlib.axes.Axes): The axis to configure.
    start_date_obj (datetime-like): The start date for the X-axis.
    end_date_obj (datetime-like): The end date for the X-axis.
    t_freq (str): The frequency of date ticks (e.g., 'D' for daily, 'H' for hourly).
    """
    ax.set_xlim(start_date_obj, end_date_obj)
    date_range = pd.date_range(start_date_obj, end_date_obj, freq=t_freq)
    ax.set_xticks(date_range)

    # Define the date format based on the tick frequency
    if t_freq[-1] == 'D':
        date_format = '%d.%m.%y'
    else:
        date_format = '%d.%m.%y %H:%M'

    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    ax.tick_params(axis='x', rotation=90)  # Rotate labels for better readability
    plt.xticks(rotation=90)


def draw_trade_info(ax, trade_info, with_sl_tp=False, linewidth_=0.6, alpha_=0.8):
    """
    Draw trade-related lines on a given plot.

    Parameters:
    ax (matplotlib.axes.Axes): The axis to draw on.
    trade_info (dict): Dictionary containing trade details (entry, exit, stop-loss, take-profit, etc.).
    with_sl_tp (bool): Whether to draw stop-loss and take-profit levels.
    linewidth_ (float): Line width for the plotted lines.
    alpha_ (float): Opacity of the plotted lines.
    """
    if with_sl_tp:
        ax.axhline(y=trade_info['sl_price'], color='red', linestyle='-', linewidth=linewidth_, alpha=alpha_)
        ax.axhline(y=trade_info['tp_price'], color='green', linestyle='-', linewidth=linewidth_, alpha=alpha_)

    ax.axvline(x=trade_info['t_entry'], color='black', linestyle='--', linewidth=linewidth_, alpha=alpha_)

    # Determine exit reason and assign corresponding color
    exit_colors = {
        'stop_loss': 'red',
        'take_profit': 'green'
    }
    exit_color = exit_colors.get(trade_info['reason_exit'], 'brown')
    ax.axvline(x=trade_info['t_exit'], color=exit_color, linestyle='--', linewidth=linewidth_, alpha=alpha_)


def adjust_limits(y_min, y_max, max_ticks=10):
    """
    Adjust Y-axis limits by rounding values and determining an appropriate step size.

    Parameters:
    y_min (float): Minimum Y value.
    y_max (float): Maximum Y value.
    max_ticks (int): Maximum number of ticks allowed on the Y-axis.

    Returns:
    tuple: Adjusted minimum Y, maximum Y, and step size.
    """
    magnitude = 10 ** np.floor(np.log10(max(abs(y_min), abs(y_max))))
    step = 5 * magnitude
    round_base = magnitude / 10
    y_min_rounded = np.floor(y_min / round_base) * round_base
    y_max_rounded = np.ceil(y_max / round_base) * round_base

    step_candidates = [magnitude * k for k in [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 2.5]]
    for step_i in step_candidates:
        if (y_max_rounded - y_min_rounded) / step_i <= max_ticks:
            step = step_i
            break

    y_min_rounded = np.floor(y_min / step) * step
    y_max_rounded = np.ceil(y_max / step) * step

    return y_min_rounded, y_max_rounded, step


def draw_line(ax, df, str_name, trade_info=None, y_min=None, y_max=None, df_bound=None,
              line_color='grey', linewidth_=0.3, sep_line=None, color_pos=None, color_neg=None):
    """
    Draw a line plot with optional trade information and shading.

    Parameters:
    ax (matplotlib.axes.Axes): The axis to draw on.
    df (pd.DataFrame): The dataset containing time-series data.
    str_name (str): The column name representing the data to plot.
    trade_info (dict, optional): Trade information for highlighting trades.
    y_min (float, optional): Minimum Y limit.
    y_max (float, optional): Maximum Y limit.
    df_bound (pd.DataFrame, optional): Alternative dataset for defining limits.
    line_color (str): Color of the line.
    linewidth_ (float): Width of the line.
    sep_line (float, optional): A separation line for distinguishing values.
    color_pos (str, optional): Color for positive fill.
    color_neg (str, optional): Color for negative fill.
    """
    font_s = get_font_size(str_name)

    if (y_min is None) and (y_max is None) and (df_bound is None):
        y_min, y_max, yticks_step = adjust_limits(df[str_name].min(), df[str_name].max())
    elif (y_min is None) and (y_max is None):
        y_min, y_max, yticks_step = adjust_limits(
            df_bound[str_name].quantile(LOWER_QUANTILE), df_bound[str_name].quantile(UPPER_QUANTILE)
        )
    else:
        yticks_step = (y_max - y_min) / Y_TICKS_STEP_DEFAULT

    ax.set_ylim(y_min, y_max)
    ax.set_yticks(np.arange(y_min, y_max + yticks_step, yticks_step))
    ax.set_ylabel(str_name, fontsize=font_s)

    if trade_info is not None:
        draw_trade_info(ax, trade_info)

    ax.step(df.index, df[str_name], color=line_color, where='mid', linewidth=linewidth_)

    if sep_line is not None:
        ax.axhline(sep_line, color='grey', linestyle='--', linewidth=1)
        if (color_pos is not None) and (color_neg is not None):
            ax.fill_between(df.index, df[str_name], 0, where=(df[str_name] > sep_line),
                            step='mid', facecolor=color_pos, alpha=0.4)
            ax.fill_between(df.index, df[str_name], 0, where=(df[str_name] <= sep_line),
                            step='mid', facecolor=color_neg, alpha=0.4)


def draw_price(ax, df, time_step_sec, trade_info=None, linewidth_=0.5, futures_price=True):
    """
    Plot price data with high, low, and close prices.

    Parameters:
    ax (matplotlib.axes.Axes): The axis to draw on.
    df (pd.DataFrame): The dataset containing price data.
    time_step_sec (int): Time step in seconds.
    trade_info (dict, optional): Trade information for highlighting trades.
    linewidth_ (float): Width of the line.
    futures_price (bool): Whether to use futures price column names.
    """
    if futures_price:
        high_price, low_price, close_price = 'high_d', 'low_d', 'close_d'
    else:
        high_price, low_price, close_price = 'high', 'low', 'close'

    t_freq = '6H' if time_step_sec == 300 else '1D'
    setup_x_axis(ax, df.index.min(), df.index.max(), t_freq)

    if trade_info is not None:
        max_price = max(df[high_price].max(), trade_info['sl_price'], trade_info['tp_price'])
        min_price = min(df[low_price].min(), trade_info['sl_price'], trade_info['tp_price'])
        draw_trade_info(ax, trade_info, with_sl_tp=True)
    else:
        max_price, min_price = df[high_price].max(), df[low_price].min()

    ax.step(df.index, df[close_price], color='blue', where='mid', linewidth=linewidth_)
    ax.step(df.index, df[high_price], color='dimgray', where='mid', linewidth=linewidth_)
    ax.step(df.index, df[low_price], color='dimgray', where='mid', linewidth=linewidth_)

    ax.set_ylabel(close_price, fontsize=get_font_size(close_price))
    y_min, y_max, yticks_step = adjust_limits(min_price, max_price)
    ax.set_yticks(np.arange(y_min, y_max + yticks_step, yticks_step))
    ax.set_ylim(y_min, y_max)


def draw_bar(
    ax, df, time_step_sec, str_name, trade_info=None,
    y_min=None, y_max=None, df_bound=None,
    sep_line=0, bar_color_pos='green', bar_color_neg=None
):
    """
    Draws a bar chart for a given dataset with optional trade highlights.

    Parameters:
    ax (matplotlib.axes.Axes): The axis on which to draw the bars.
    df (pd.DataFrame): The dataset containing the values to be plotted.
    time_step_sec (int): The time step in seconds for the bar width adjustment.
    str_name (str): The column name of the data to be plotted.
    trade_info (dict, optional): Dictionary containing trade details for additional highlights.
    y_min (float, optional): Minimum value for the Y-axis.
    y_max (float, optional): Maximum value for the Y-axis.
    df_bound (pd.DataFrame, optional): Alternative dataset for defining Y-axis limits.
    sep_line (float): A horizontal line separating positive and negative values.
    bar_color_pos (str): Color for bars above the separation line.
    bar_color_neg (str, optional): Color for bars below the separation line.
    """
    font_s = get_font_size(str_name)
    width_in_days = 0.7 * time_step_sec / (24 * 60 * 60)  # Convert time step to days for bar width

    # Determine Y-axis limits
    if (y_min is None) and (y_max is None) and (df_bound is None):
        y_min, y_max, yticks_step = adjust_limits(df[str_name].min(), df[str_name].max())
    elif (y_min is None) and (y_max is None):
        y_min, y_max, yticks_step = adjust_limits(
            df_bound[str_name].quantile(LOWER_QUANTILE), df_bound[str_name].quantile(UPPER_QUANTILE)
        )
    else:
        yticks_step = Y_TICKS_STEP_DEFAULT

    # Set Y-axis properties
    ax.set_yticks(np.arange(y_min, y_max + yticks_step, yticks_step))
    ax.set_ylim(y_min, y_max)
    ax.set_ylabel(str_name, fontsize=font_s)

    # Draw trade information if provided
    if trade_info:
        draw_trade_info(ax, trade_info)

    # Draw the bar chart with color differentiation if negative color is provided
    if bar_color_neg is not None:
        bar_colors = [bar_color_pos if value > sep_line else bar_color_neg for value in df[str_name]]
        ax.bar(df.index, df[str_name], color=bar_colors, width=width_in_days, linewidth=0)
    else:
        ax.bar(df.index, df[str_name], color=bar_color_pos, width=width_in_days, linewidth=0)
