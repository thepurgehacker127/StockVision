from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout

from PySide6.QtCharts import (
    QChart,
    QDateTimeAxis,
    QValueAxis,
    QCandlestickSeries,
    QCandlestickSet,
    QLineSeries,
)

from stockvision.core.market_data import Candle
from stockvision.ui.interactive_chart_view import InteractiveChartView


@dataclass
class SeriesColors:
    up: QColor = field(default_factory=lambda: QColor("#2ecc71"))
    down: QColor = field(default_factory=lambda: QColor("#e74c3c"))
    grid: QColor = field(default_factory=lambda: QColor(255, 255, 255, 40))
    text: QColor = field(default_factory=lambda: QColor(230, 230, 230, 220))


class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.colors = SeriesColors()

        self.chart = QChart()
        self.chart.legend().setVisible(True)
        self.chart.setBackgroundVisible(False)
        self.chart.setPlotAreaBackgroundVisible(False)
        self.chart.setTitle("")

        # ✅ Use our interactive view instead of plain QChartView
        self.view = InteractiveChartView(self.chart)
        self.view.setRenderHint(QPainter.Antialiasing, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.axis_x = QDateTimeAxis()
        self.axis_x.setFormat("MM-dd HH:mm")
        self.axis_x.setLabelsAngle(-35)

        self.axis_y = QValueAxis()

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        self._apply_axis_style()

        self._candle_series: Optional[QCandlestickSeries] = None
        self._line_series: Dict[str, QLineSeries] = {}

    def _apply_axis_style(self):
        pen = QPen(self.colors.grid)
        self.axis_x.setGridLinePen(pen)
        self.axis_y.setGridLinePen(pen)

        self.axis_x.setLabelsColor(self.colors.text)
        self.axis_y.setLabelsColor(self.colors.text)

        self.axis_x.setTitleBrush(self.colors.text)
        self.axis_y.setTitleBrush(self.colors.text)

    def clear(self):
        self.chart.removeAllSeries()
        self._candle_series = None
        self._line_series.clear()

    def set_title(self, text: str):
        self.chart.setTitle(text)

    def plot_candles(self, symbol: str, candles: List[Candle]):
        self.clear()

        series = QCandlestickSeries()
        series.setName(f"{symbol} (Candles)")
        series.setIncreasingColor(self.colors.up)
        series.setDecreasingColor(self.colors.down)

        lows = []
        highs = []
        for c in candles:
            cs = QCandlestickSet(c.o, c.h, c.l, c.c, c.t)
            series.append(cs)
            lows.append(c.l)
            highs.append(c.h)

        self.chart.addSeries(series)
        series.attachAxis(self.axis_x)
        series.attachAxis(self.axis_y)
        self._candle_series = series

        t0 = candles[0].t
        t1 = candles[-1].t
        self.axis_x.setRange(QDateTime.fromMSecsSinceEpoch(t0), QDateTime.fromMSecsSinceEpoch(t1))

        lo = min(lows)
        hi = max(highs)
        pad = (hi - lo) * 0.08 if hi > lo else 1.0
        self.axis_y.setRange(lo - pad, hi + pad)

        self.set_title(f"{symbol} — Candlestick Chart")

        # ✅ Reset zoom each time new data loads (optional but feels good)
        self.chart.zoomReset()

    def plot_compare(self, symbol_to_candles: Dict[str, List[Candle]], normalize: bool = True):
        self.clear()

        all_times = []
        for candles in symbol_to_candles.values():
            if candles:
                all_times.append(candles[0].t)
                all_times.append(candles[-1].t)
        if not all_times:
            return

        t0 = min(all_times)
        t1 = max(all_times)
        self.axis_x.setRange(QDateTime.fromMSecsSinceEpoch(t0), QDateTime.fromMSecsSinceEpoch(t1))

        palette = ["#2b72ff", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#e84393"]
        ymin, ymax = None, None

        for idx, (sym, candles) in enumerate(symbol_to_candles.items()):
            if not candles:
                continue

            ls = QLineSeries()
            ls.setName(sym)

            base = candles[0].c if normalize else 1.0
            if base == 0:
                base = 1.0

            for c in candles:
                y = ((c.c / base) - 1.0) * 100.0 if normalize else c.c
                ls.append(float(c.t), float(y))
                ymin = y if ymin is None else min(ymin, y)
                ymax = y if ymax is None else max(ymax, y)

            color = QColor(palette[idx % len(palette)])
            pen = QPen(color)
            pen.setWidth(2)
            ls.setPen(pen)

            self.chart.addSeries(ls)
            ls.attachAxis(self.axis_x)
            ls.attachAxis(self.axis_y)
            self._line_series[sym] = ls

        if ymin is None or ymax is None:
            return

        pad = (ymax - ymin) * 0.10 if ymax > ymin else 1.0
        self.axis_y.setRange(ymin - pad, ymax + pad)

        if normalize:
            self.axis_y.setTitleText("% Change (from start)")
            self.set_title("Comparison — Normalized Performance")
        else:
            self.axis_y.setTitleText("Price")
            self.set_title("Comparison — Price")

        self.axis_x.setTitleText("Time")
        self.chart.zoomReset()
