from __future__ import annotations

from bisect import bisect_left
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QGraphicsView, QGraphicsLineItem, QToolTip
from PySide6.QtCharts import QChartView

from stockvision.core.market_data import Candle


class InteractiveChartView(QChartView):
    """
    Adds:
      - mouse wheel zoom
      - rectangle zoom (rubber band)
      - pan (right-mouse drag)
      - reset zoom (double click)
      - keyboard controls
      - crosshair + OHLC tooltip (candles)
    """

    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)

        # Smooth drawing
        self.setRenderHint(QPainter.Antialiasing, True)

        # Rectangle zoom (click+drag)
        self.setRubberBand(QChartView.RectangleRubberBand)
        self.setDragMode(QGraphicsView.NoDrag)

        self._panning = False
        self._last_pos = QPoint()

        # Make sure we can receive keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        # Data for tooltips
        self._symbol: str = ""
        self._candles: List[Candle] = []
        self._candle_times: List[int] = []
        self._last_idx: Optional[int] = None

        # Crosshair graphics items (in scene coordinates)
        self._vline = QGraphicsLineItem()
        self._hline = QGraphicsLineItem()

        pen = QPen(QColor(230, 230, 230, 90))
        pen.setWidth(1)
        self._vline.setPen(pen)
        self._hline.setPen(pen)

        self._vline.setZValue(9999)
        self._hline.setZValue(9999)

        # Add to scene and start hidden
        self.scene().addItem(self._vline)
        self.scene().addItem(self._hline)
        self._vline.setVisible(False)
        self._hline.setVisible(False)

    # ---------- API: provide candles for OHLC tooltips ----------
    def set_candles(self, symbol: str, candles: List[Candle]):
        self._symbol = symbol
        self._candles = candles or []
        self._candle_times = [c.t for c in self._candles]
        self._last_idx = None

    def clear_data(self):
        self._symbol = ""
        self._candles = []
        self._candle_times = []
        self._last_idx = None

    # ---------- Helpers ----------
    def _hide_crosshair(self):
        self._vline.setVisible(False)
        self._hline.setVisible(False)

    def _format_dt_local(self, epoch_ms: int) -> str:
        dt = datetime.fromtimestamp(epoch_ms / 1000.0)
        return dt.strftime("%Y-%m-%d %H:%M")

    def _nearest_candle_index(self, x_ms: int) -> Optional[int]:
        if not self._candle_times:
            return None
        i = bisect_left(self._candle_times, x_ms)
        if i <= 0:
            return 0
        if i >= len(self._candle_times):
            return len(self._candle_times) - 1
        # choose closest of i-1 and i
        prev_t = self._candle_times[i - 1]
        next_t = self._candle_times[i]
        return (i - 1) if abs(x_ms - prev_t) <= abs(next_t - x_ms) else i

    def _update_crosshair_and_tooltip(self, mouse_pos: QPoint):
        chart = self.chart()
        if chart is None:
            return

        # Convert widget coords -> scene coords
        scene_pos = self.mapToScene(mouse_pos)

        plot = chart.plotArea()  # QRectF in scene coords
        if not plot.contains(scene_pos):
            self._hide_crosshair()
            return

        # Map mouse to chart values
        try:
            val = chart.mapToValue(QPointF(mouse_pos))
        except TypeError:
            # Some bindings accept QPointF in scene coords
            val = chart.mapToValue(scene_pos)

        x_ms = int(val.x())
        y_val = float(val.y())

        # Position crosshair lines using scene coords:
        # get the scene x/y of the cursor itself:
        x_scene = scene_pos.x()
        y_scene = scene_pos.y()

        self._vline.setLine(x_scene, plot.top(), x_scene, plot.bottom())
        self._hline.setLine(plot.left(), y_scene, plot.right(), y_scene)
        self._vline.setVisible(True)
        self._hline.setVisible(True)

        # Tooltip: if we have candles, snap to nearest candle time and show OHLC
        idx = self._nearest_candle_index(x_ms)
        if idx is not None:
            c = self._candles[idx]
            if self._last_idx != idx:
                self._last_idx = idx
                tip = (
                    f"{self._symbol}\\n"
                    f"Time: {self._format_dt_local(c.t)}\\n"
                    f"O: {c.o:.4f}  H: {c.h:.4f}\\n"
                    f"L: {c.l:.4f}  C: {c.c:.4f}"
                )
                if c.v:
                    tip += f"\\nV: {c.v:.0f}"
                QToolTip.showText(self.mapToGlobal(mouse_pos), tip, self)

        else:
            # Fallback tooltip for non-candle charts (comparison): time + y
            tip = f"Time(ms): {x_ms}\\nY: {y_val:.4f}"
            QToolTip.showText(self.mapToGlobal(mouse_pos), tip, self)

    # ---------- Mouse Wheel Zoom ----------
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.chart().zoom(1.15)
        else:
            self.chart().zoom(0.87)
        event.accept()

    # ---------- Right-Mouse Pan ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._panning = True
            self._last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._last_pos
            self._last_pos = event.pos()
            self.chart().scroll(-delta.x(), delta.y())
            event.accept()
            return

        # Crosshair + tooltip (while moving, not panning)
        self._update_crosshair_and_tooltip(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self._panning:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ---------- Double Click Reset ----------
    def mouseDoubleClickEvent(self, event):
        self.chart().zoomReset()
        event.accept()

    def leaveEvent(self, event):
        # Hide crosshair when leaving the chart view
        self._hide_crosshair()
        super().leaveEvent(event)

    # ---------- Keyboard Controls ----------
    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Left:
            self.chart().scroll(-40, 0)
            return
        if key == Qt.Key_Right:
            self.chart().scroll(40, 0)
            return
        if key == Qt.Key_Up:
            self.chart().scroll(0, -40)
            return
        if key == Qt.Key_Down:
            self.chart().scroll(0, 40)
            return

        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self.chart().zoom(1.15)
            return
        if key in (Qt.Key_Minus, Qt.Key_Underscore):
            self.chart().zoom(0.87)
            return

        if key in (Qt.Key_0,):
            self.chart().zoomReset()
            return

        super().keyPressEvent(event)
