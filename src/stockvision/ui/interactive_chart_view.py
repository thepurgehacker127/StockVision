from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCharts import QChartView


class InteractiveChartView(QChartView):
    """
    Adds:
      - mouse wheel zoom
      - rectangle zoom (rubber band)
      - pan (right-mouse drag)
      - reset zoom (double click)
      - keyboard controls
    """

    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)

        # Smooth drawing
        self.setRenderHint(QPainter.Antialiasing, True)

        # Rectangle zoom (click+drag)
        self.setRubberBand(QChartView.RectangleRubberBand)

        # Optional: allow hand-drag scrolling of the scene
        # (we will implement reliable chart panning using right mouse drag below)
        self.setDragMode(QGraphicsView.NoDrag)

        self._panning = False
        self._last_pos = QPoint()

        # Make sure we can receive keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)

    # ---------- Mouse Wheel Zoom ----------
    def wheelEvent(self, event):
        # Zoom in/out
        delta = event.angleDelta().y()

        # If you want CTRL+wheel to zoom and normal wheel to scroll,
        # uncomment this guard:
        # if not (event.modifiers() & Qt.ControlModifier):
        #     return super().wheelEvent(event)

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

            # chart().scroll(dx, dy) uses pixels.
            # Negative dx moves view right; positive dx moves view left.
            self.chart().scroll(-delta.x(), delta.y())

            event.accept()
            return

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

    # ---------- Keyboard Controls ----------
    def keyPressEvent(self, event):
        key = event.key()

        # Pan with arrow keys
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

        # Zoom with + / -
        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self.chart().zoom(1.15)
            return
        if key in (Qt.Key_Minus, Qt.Key_Underscore):
            self.chart().zoom(0.87)
            return

        # Reset zoom
        if key in (Qt.Key_0,):
            self.chart().zoomReset()
            return

        super().keyPressEvent(event)
