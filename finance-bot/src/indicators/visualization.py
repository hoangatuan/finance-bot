"""
Support and Resistance Visualization Module

This module provides visualization capabilities for candlestick charts with
support and resistance levels, volume, and other technical indicators.

Reference: https://medium.com/@itay1542/how-to-calculate-support-and-resistance-levels-using-python-a-step-by-step-guide-e94a33c6cbda
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os


class SupportResistanceVisualizer:
    """Visualizer for support and resistance levels on candlestick charts"""
    
    # Color scheme
    COLORS = {
        'support_zone': '#90EE90',      # Light green fill
        'support_line': '#228B22',       # Dark green border
        'resistance_zone': '#FFB6C1',    # Light red fill
        'resistance_line': '#DC143C',    # Dark red border
        'current_price': '#0000FF',      # Blue line
        'candlestick_up': '#00FF00',     # Green candles
        'candlestick_down': '#FF0000',   # Red candles
        'volume_up': '#90EE90',          # Light green volume
        'volume_down': '#FFB6C1',        # Light red volume
    }
    
    def __init__(
        self,
        style: str = 'default',
        figsize: Tuple[int, int] = (16, 10),
        dpi: int = 100
    ):
        """
        Initialize visualizer
        
        Args:
            style: Chart style ('default', 'dark', 'minimal')
            figsize: Figure size (width, height)
            dpi: Resolution for saved images
        """
        self.style = style
        self.figsize = figsize
        self.dpi = dpi
    
    def plot_chart(
        self,
        df: pd.DataFrame,
        support_resistance_data: Dict,
        ticker: str,
        save_path: Optional[str] = None,
        show: bool = True
    ) -> None:
        """
        Main plotting function - creates candlestick chart with volume and support/resistance lines
        
        Args:
            df: DataFrame with OHLCV data (must have columns: timestamp, open, high, low, close, volume)
            support_resistance_data: Dictionary with support/resistance levels from analyze_support_resistance
            ticker: Stock symbol
            save_path: Optional path to save chart
            show: Whether to display chart
        """
        if df.empty:
            print("❌ Cannot plot: DataFrame is empty")
            return
        
        # Prepare data for plotting
        df_plot = df.copy()
        
        # Ensure timestamp is datetime and set as index
        if 'timestamp' in df_plot.columns:
            df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
            df_plot = df_plot.set_index('timestamp')
        elif not isinstance(df_plot.index, pd.DatetimeIndex):
            df_plot.index = pd.to_datetime(df_plot.index)
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df_plot.columns]
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return
        
        # Filter out non-trading days:
        # 1. Remove rows with missing/invalid OHLCV data
        # 2. Remove rows with zero volume (non-trading days)
        # 3. Remove rows where all prices are the same and volume is zero (likely data errors)
        initial_count = len(df_plot)
        
        # Remove rows with any missing values in required columns
        df_plot = df_plot.dropna(subset=required_cols)
        
        # Remove rows with zero or negative volume (non-trading days)
        if 'volume' in df_plot.columns:
            df_plot = df_plot[df_plot['volume'] > 0]
        
        # Remove rows where prices are invalid (negative or zero)
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df_plot.columns:
                df_plot = df_plot[df_plot[col] > 0]
        
        # Sort by timestamp to ensure proper ordering
        df_plot = df_plot.sort_index()
        
        filtered_count = len(df_plot)
        if initial_count != filtered_count:
            print(f"📊 Filtered {initial_count - filtered_count} non-trading days from {initial_count} total rows")
        
        if df_plot.empty:
            print("❌ Cannot plot: No valid trading days found after filtering")
            return
        
        # Create sequential index for x-axis to avoid gaps from non-trading days
        # We'll use this for plotting but keep datetime index for date labels
        # Save the datetime index before resetting
        datetime_index = df_plot.index.copy()
        df_plot = df_plot.reset_index()
        
        # Ensure we have a timestamp column (might be named 'timestamp' or index name)
        if 'timestamp' not in df_plot.columns:
            # Check if index had a name
            if df_plot.index.name == 'timestamp' or len(df_plot.columns) > 0:
                # Use the first column that looks like a datetime
                for col in df_plot.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_plot[col]):
                        df_plot = df_plot.rename(columns={col: 'timestamp'})
                        break
        
        df_plot['plot_index'] = range(len(df_plot))
        # Use the datetime index we saved, or the timestamp column
        date_index = datetime_index if isinstance(datetime_index, pd.DatetimeIndex) else (
            df_plot['timestamp'] if 'timestamp' in df_plot.columns else pd.DatetimeIndex(df_plot.index)
        )
        
        # Create figure with subplots (price chart and volume chart)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, 
                                       gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.1})
        
        # Plot candlestick chart (using sequential index)
        self._plot_candlesticks(ax1, df_plot, use_sequential_index=True)
        
        # Plot support and resistance lines
        current_price = support_resistance_data.get('current_price')
        if current_price:
            self._plot_current_price(ax1, current_price)
        
        # Plot support levels
        support_levels = support_resistance_data.get('support_levels', [])
        if support_levels:
            self._plot_levels(ax1, support_levels, is_resistance=False)
        
        # Plot resistance levels
        resistance_levels = support_resistance_data.get('resistance_levels', [])
        if resistance_levels:
            self._plot_levels(ax1, resistance_levels, is_resistance=True)
        
        # Plot volume (using sequential index)
        self._plot_volume(ax2, df_plot, use_sequential_index=True)
        
        # Format axes with date labels
        self._format_axes(ax1, ax2, ticker, date_index, df_plot['plot_index'] if 'plot_index' in df_plot.columns else None)
        
        # Save or show
        if save_path:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            print(f"✅ Chart saved to: {save_path}")
        
        if show:
            try:
                plt.show()
            except:
                # If display is not available, just save
                if not save_path:
                    print("⚠️  Display not available. Use save_path to save the chart.")
        else:
            plt.close()
    
    def _plot_candlesticks(self, ax: plt.Axes, df: pd.DataFrame, use_sequential_index: bool = False) -> None:
        """
        Plot candlestick chart
        
        Args:
            ax: Matplotlib axes
            df: DataFrame with OHLCV data
            use_sequential_index: If True, use sequential index (0, 1, 2...) instead of datetime
        """
        # Calculate bar width
        if len(df) > 1:
            if use_sequential_index and 'plot_index' in df.columns:
                # Use sequential index
                bar_width = max(0.3, min(0.8, 0.6))
            else:
                # Use datetime index
                if isinstance(df.index, pd.DatetimeIndex):
                    dates_num = mdates.date2num(df.index)
                    date_range = dates_num[-1] - dates_num[0]
                    bar_width = max(0.3, min(0.8, date_range / len(df) * 0.6))
                else:
                    bar_width = 0.6
        else:
            bar_width = 0.6
        
        # Plot each candlestick
        for idx, row in df.iterrows():
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            
            # Determine color based on open vs close
            is_up = close_price >= open_price
            color = self.COLORS['candlestick_up'] if is_up else self.COLORS['candlestick_down']
            
            # Get x-coordinate
            if use_sequential_index and 'plot_index' in df.columns:
                x_pos = row['plot_index']
            elif isinstance(df.index, pd.DatetimeIndex):
                x_pos = mdates.date2num(idx)
            else:
                x_pos = idx
            
            # Draw the wick (high-low line) using vlines
            ax.vlines(x_pos, low_price, high_price, 
                     color='black', linewidth=0.8, alpha=0.6, zorder=1)
            
            # Draw the body (open-close rectangle)
            body_low = min(open_price, close_price)
            body_high = max(open_price, close_price)
            body_height = body_high - body_low
            
            if body_height > 0:
                # Create rectangle for candle body
                rect = Rectangle(
                    (x_pos - bar_width / 2, body_low),
                    bar_width,
                    body_height,
                    facecolor=color,
                    edgecolor='black',
                    linewidth=0.8,
                    alpha=0.8,
                    zorder=2
                )
                ax.add_patch(rect)
            else:
                # For doji candles (open == close), draw a horizontal line
                ax.hlines(open_price, x_pos - bar_width / 2, x_pos + bar_width / 2,
                         color=color, linewidth=2.5, alpha=0.9, zorder=2)
        
        # Set y-axis label
        ax.set_ylabel('Price', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
    
    def _plot_volume(self, ax: plt.Axes, df: pd.DataFrame, use_sequential_index: bool = False) -> None:
        """
        Plot volume bars
        
        Args:
            ax: Matplotlib axes
            df: DataFrame with OHLCV data
            use_sequential_index: If True, use sequential index (0, 1, 2...) instead of datetime
        """
        # Determine color based on price movement
        colors = []
        x_positions = []
        
        for idx, row in df.iterrows():
            is_up = row['close'] >= row['open']
            colors.append(self.COLORS['volume_up'] if is_up else self.COLORS['volume_down'])
            
            # Get x-coordinate
            if use_sequential_index and 'plot_index' in df.columns:
                x_positions.append(row['plot_index'])
            elif isinstance(df.index, pd.DatetimeIndex):
                x_positions.append(mdates.date2num(idx))
            else:
                x_positions.append(idx)
        
        # Plot volume bars
        ax.bar(x_positions, df['volume'], color=colors, alpha=0.6, width=0.8)
        
        # Format volume axis
        ax.set_ylabel('Volume', fontsize=10, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    def _plot_levels(self, ax: plt.Axes, levels: List[Dict], is_resistance: bool) -> None:
        """
        Plot support or resistance levels as horizontal lines
        
        Args:
            ax: Matplotlib axes
            levels: List of level dictionaries with 'price', 'strength', 'touch_count'
            is_resistance: True for resistance, False for support
        """
        if not levels:
            return
        
        # Limit to top 5 most relevant levels
        levels_to_plot = levels[:5]
        
        for level in levels_to_plot:
            price = level.get('price')
            if price is None:
                continue
            
            strength = level.get('strength', 'weak')
            touch_count = level.get('touch_count', 0)
            
            # Determine color and style based on type and strength
            if is_resistance:
                color = self.COLORS['resistance_line']
                label_prefix = 'Resistance'
            else:
                color = self.COLORS['support_line']
                label_prefix = 'Support'
            
            # Line style based on strength
            linewidth = 2.5 if strength == 'strong' else 1.5
            linestyle = '-' if strength == 'strong' else '--'
            alpha = 0.9 if strength == 'strong' else 0.6
            
            # Get x-axis limits for drawing line across entire chart
            xlim = ax.get_xlim()
            
            # Draw horizontal line
            ax.axhline(
                price,
                color=color,
                linestyle=linestyle,
                linewidth=linewidth,
                alpha=alpha,
                label=f'{label_prefix}: {price:,.0f} ({touch_count} touches)'
            )
            
            # Add text label on the right side
            label_text = f'{price:,.0f}'
            if touch_count > 0:
                label_text += f' ({touch_count})'
            
            ax.text(
                xlim[1],
                price,
                label_text,
                verticalalignment='center',
                horizontalalignment='left',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                         edgecolor=color, alpha=0.8),
                fontsize=9,
                color=color,
                fontweight='bold' if strength == 'strong' else 'normal'
            )
    
    def _plot_current_price(self, ax: plt.Axes, current_price: float) -> None:
        """
        Plot current price as reference line
        
        Args:
            ax: Matplotlib axes
            current_price: Current stock price
        """
        ax.axhline(
            current_price,
            color=self.COLORS['current_price'],
            linestyle='--',
            linewidth=2,
            alpha=0.8,
            label=f'Current Price: {current_price:,.0f}'
        )
        
        # Add label
        xlim = ax.get_xlim()
        ax.text(
            xlim[0],
            current_price,
            f'Current: {current_price:,.0f}',
            verticalalignment='bottom',
            horizontalalignment='left',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor=self.COLORS['current_price'], alpha=0.9),
            fontsize=9,
            color=self.COLORS['current_price'],
            fontweight='bold'
        )
    
    def _format_axes(
        self,
        ax1: plt.Axes,
        ax2: plt.Axes,
        ticker: str,
        timestamps: pd.DatetimeIndex,
        plot_indices: Optional[pd.Series] = None
    ) -> None:
        """
        Format chart axes with labels, title, and date formatting
        
        Args:
            ax1: Price chart axes
            ax2: Volume chart axes
            ticker: Stock symbol
            timestamps: Datetime index for date labels
            plot_indices: Sequential indices used for plotting (if using sequential index)
        """
        # Set title
        ax1.set_title(
            f'{ticker} - Candlestick Chart with Support & Resistance',
            fontsize=16,
            fontweight='bold',
            pad=20
        )
        
        # If using sequential index, set x-axis limits and format with dates
        if plot_indices is not None and len(plot_indices) > 0:
            # Set x-axis limits based on sequential indices
            ax1.set_xlim(plot_indices.min() - 0.5, plot_indices.max() + 0.5)
            ax2.set_xlim(plot_indices.min() - 0.5, plot_indices.max() + 0.5)
            
            # Format x-axis with dates but use sequential positions
            # Select a reasonable number of tick positions
            num_ticks = min(10, len(plot_indices))
            step = max(1, len(plot_indices) // num_ticks)
            tick_positions = plot_indices.iloc[::step].values
            
            # Get corresponding date labels
            if isinstance(timestamps, pd.Series) or isinstance(timestamps, pd.Index):
                tick_labels = [pd.Timestamp(ts).strftime('%Y-%m-%d') if isinstance(ts, (pd.Timestamp, datetime)) else str(ts) 
                              for ts in timestamps[::step]]
            else:
                # If timestamps is a single value or array-like
                tick_labels = [pd.Timestamp(ts).strftime('%Y-%m-%d') if isinstance(ts, (pd.Timestamp, datetime)) else str(ts) 
                              for ts in (timestamps[::step] if hasattr(timestamps, '__getitem__') else [timestamps])]
            
            # Set ticks for both axes
            ax1.set_xticks(tick_positions)
            ax1.set_xticklabels([])  # Hide x-axis labels on price chart
            ax2.set_xticks(tick_positions)
            ax2.set_xticklabels(tick_labels, rotation=45, ha='right')
        else:
            # Use datetime formatting (original approach)
            # Format x-axis for price chart (hide labels, volume chart will show them)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax1.set_xticklabels([])  # Hide x-axis labels on price chart
            
            # Format x-axis for volume chart
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Set date range on x-axis
            if len(timestamps) > 0:
                ax1.set_xlim(timestamps[0], timestamps[-1])
                ax2.set_xlim(timestamps[0], timestamps[-1])
        
        # Add legend to price chart
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
        
        # Adjust layout
        plt.tight_layout()

