import math
import time
from PyQt5.QtCore import QLocale, QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from krita import DockWidget, Krita, ManagedColor

# DICCIONARIO DE TRADUCCIÓN (I18N)
TEXTS = {
    "es": {
        "title": "Esfera de Luz",
        "plastic": "Plástico / Mate",
        "skin": "Piel (Orgánico)",
        "sync": "🔗 Sync Krita",
        "auto_shadow": "🎨 Sombra Auto",
        "custom_shadow": "Sombra...",
        "bounce_color": "Rebote...",
        "auto_bounce": "Auto",
        "bounce_label": "Rebote:",
        "light": "Luz",
        "mid": "Medio",
        "shadow": "Sombra",
        "bounce": "Rebote",
        "save_tooltip": "Guardar colores en el historial",
        "tooltip_sphere": "• Arrastrar con Clic Izquierdo: Mover Luz\n• Arrastrar con Clic Derecho: Mover Rebote\n• Clic simple: Tomar color",
        "picker_title_shadow": "Elegir Color de Sombra",
        "picker_title_bounce": "Elegir Color de Rebote",
    },
    "en": {
        "title": "Light Sphere",
        "plastic": "Plastic / Matte",
        "skin": "Skin (Organic)",
        "sync": "🔗 Sync Krita",
        "auto_shadow": "🎨 Auto Shadow",
        "custom_shadow": "Shadow...",
        "bounce_color": "Bounce...",
        "auto_bounce": "Auto",
        "bounce_label": "Bounce:",
        "light": "Light",
        "mid": "Mid",
        "shadow": "Shadow",
        "bounce": "Bounce",
        "save_tooltip": "Save colors to history",
        "tooltip_sphere": "• Left Click Drag: Move Light\n• Right Click Drag: Move Bounce\n• Click: Pick color",
        "picker_title_shadow": "Select Shadow Color",
        "picker_title_bounce": "Select Bounce Color",
    },
}


class LitSphereView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(130, 140)

        self.lx = -0.50
        self.ly = -0.55
        self.bx = 0.60
        self.by = 0.70
        self.bounce_intensity = 60
        self.auto_bounce = True

        self.base_color = QColor(230, 180, 140)
        self.bounce_color = QColor(130, 175, 235)
        self.custom_shadow_color = None
        self.use_complementary_shadow = True

        self.material = "plastico"

        self.dragging_light = False
        self.dragging_bounce = False
        self.press_pos = None
        self.has_dragged = False

    def get_shadow_color(self):
        if not self.use_complementary_shadow and self.custom_shadow_color:
            return self.custom_shadow_color

        h = self.base_color.hue()
        if h < 0:
            h = 0
        s = self.base_color.saturation()
        v = self.base_color.value()

        if self.use_complementary_shadow:
            comp_h = (h + 160) % 360
            comp_s = min(255, int(s * 1.15 + 25))
            comp_v = int(v * 0.38)
            return QColor.fromHsv(comp_h, comp_s, comp_v)
        else:
            return self.base_color.darker(260)

    def mousePressEvent(self, event):
        self.press_pos = event.pos()
        self.has_dragged = False
        if event.button() == Qt.LeftButton:
            self.dragging_light = True
        elif event.button() == Qt.RightButton:
            self.dragging_bounce = True
            self.auto_bounce = False

    def mouseMoveEvent(self, event):
        if (
            self.press_pos
            and (event.pos() - self.press_pos).manhattanLength() > 4
        ):
            self.has_dragged = True

        if self.dragging_light:
            self._update_light_from_mouse(event.pos())
        elif self.dragging_bounce:
            self._update_bounce_from_mouse(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.has_dragged:
                self.pick_color(event.pos())
            self.dragging_light = False
        elif event.button() == Qt.RightButton:
            self.dragging_bounce = False

        self.has_dragged = False
        self.press_pos = None

    def _update_light_from_mouse(self, pos):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 8
        r = min(w, h) * 0.36
        nx = (pos.x() - cx) / r
        ny = (pos.y() - cy) / r
        dist = math.sqrt(nx * nx + ny * ny)

        if dist > 0.98:
            nx = (nx / dist) * 0.98
            ny = (ny / dist) * 0.98

        self.lx = nx
        self.ly = ny

        if self.auto_bounce:
            self.bx = -self.lx * 0.90
            self.by = max(0.18, -self.ly * 0.85)

        self.update()
        self._notify_parent()

    def _update_bounce_from_mouse(self, pos):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 8
        r = min(w, h) * 0.36
        nx = (pos.x() - cx) / r
        ny = (pos.y() - cy) / r
        dist = math.sqrt(nx * nx + ny * ny)
        if dist > 0.001:
            self.bx = (nx / dist) * 0.92
            self.by = (ny / dist) * 0.92
        self.update()
        self._notify_parent()

    def _notify_parent(self):
        parent = self.window()
        if hasattr(parent, "update_live_palette"):
            parent.update_live_palette()

    def pick_color(self, pos):
        pixmap = self.grab()
        image = pixmap.toImage()
        if 0 <= pos.x() < image.width() and 0 <= pos.y() < image.height():
            qcol = image.pixelColor(pos)
            parent = self.window()
            if hasattr(parent, "send_to_krita"):
                parent.send_to_krita(qcol)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(32, 33, 36))

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 8
        r = min(w, h) * 0.36

        # Sombra proyectada
        shadow_ox = cx - (self.lx * r * 0.65)
        shadow_oy = cy + r + 10
        shadow_w = r * 1.65 + abs(self.lx) * 20
        shadow_h = r * 0.32
        shadow_rect = QRectF(
            shadow_ox - shadow_w / 2, shadow_oy - shadow_h / 2, shadow_w, shadow_h
        )

        shadow_grad = QRadialGradient(shadow_ox, shadow_oy, shadow_w / 2)
        shadow_grad.setColorAt(0.0, QColor(10, 10, 12, 230))
        shadow_grad.setColorAt(0.5, QColor(15, 15, 18, 120))
        shadow_grad.setColorAt(1.0, QColor(32, 33, 36, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_grad))
        painter.drawEllipse(shadow_rect)

        # Máscara circular
        sphere_rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        clip_path = QPainterPath()
        clip_path.addEllipse(sphere_rect)
        painter.save()
        painter.setClipPath(clip_path)

        if self.material == "piel":
            self._render_skin(painter, cx, cy, r)
        else:
            self._render_plastic(painter, cx, cy, r)

        painter.restore()

        # Oclusión perimetral (Fresnel)
        fresnel = QRadialGradient(cx, cy, r)
        fresnel.setColorAt(0.0, QColor(0, 0, 0, 0))
        fresnel.setColorAt(0.85, QColor(0, 0, 0, 0))
        fresnel.setColorAt(1.0, QColor(0, 0, 0, 140))
        painter.setBrush(QBrush(fresnel))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(sphere_rect)

        painter.setPen(QColor(0, 0, 0, 80))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(sphere_rect)

    def _render_plastic(self, p, cx, cy, r):
        lx_pos = cx + self.lx * r * 0.78
        ly_pos = cy + self.ly * r * 0.78

        diffuse = QRadialGradient(lx_pos, ly_pos, r * 1.65)
        diffuse.setColorAt(0.0, self.base_color.lighter(130))
        diffuse.setColorAt(0.38, self.base_color)

        shadow_col = self.get_shadow_color()
        diffuse.setColorAt(0.75, shadow_col)
        diffuse.setColorAt(1.0, shadow_col.darker(140))

        p.setBrush(QBrush(diffuse))
        p.setPen(Qt.NoPen)
        p.drawRect(self.rect())

        if self.bounce_intensity > 0:
            bx_pos = cx + self.bx * r * 0.96
            by_pos = cy + self.by * r * 0.96
            b_grad = QRadialGradient(bx_pos, by_pos, r * 0.85)
            alpha = int(210 * (self.bounce_intensity / 100.0))
            col = QColor(self.bounce_color)
            col.setAlpha(alpha)
            b_grad.setColorAt(0.0, col)
            col_t = QColor(self.bounce_color)
            col_t.setAlpha(0)
            b_grad.setColorAt(0.65, col_t)
            p.setBrush(QBrush(b_grad))
            p.drawRect(self.rect())

        spec_x = cx + self.lx * r * 0.82
        spec_y = cy + self.ly * r * 0.82
        spec = QRadialGradient(spec_x, spec_y, r * 0.22)
        spec.setColorAt(0.0, QColor(255, 255, 255, 245))
        spec.setColorAt(0.40, QColor(255, 255, 255, 90))
        spec.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(spec))
        p.drawRect(self.rect())

    def _render_skin(self, p, cx, cy, r):
        lx_pos = cx + self.lx * r * 0.74
        ly_pos = cy + self.ly * r * 0.74

        diffuse = QRadialGradient(lx_pos, ly_pos, r * 1.60)
        diffuse.setColorAt(0.0, self.base_color.lighter(120))
        diffuse.setColorAt(0.35, self.base_color)

        h = self.base_color.hue()
        if h < 0:
            h = 0
        warm_shadow = QColor.fromHsv(
            (h - 10) % 360,
            min(255, int(self.base_color.saturation() * 1.15 + 15)),
            int(self.base_color.value() * 0.55),
        )
        diffuse.setColorAt(0.68, warm_shadow)

        shadow_col = self.get_shadow_color()
        diffuse.setColorAt(1.0, shadow_col)

        p.setBrush(QBrush(diffuse))
        p.setPen(Qt.NoPen)
        p.drawRect(self.rect())

        if self.bounce_intensity > 0:
            bx_pos = cx + self.bx * r * 0.95
            by_pos = cy + self.by * r * 0.95
            b_grad = QRadialGradient(bx_pos, by_pos, r * 0.85)
            alpha = int(180 * (self.bounce_intensity / 100.0))
            col = QColor(self.bounce_color)
            col.setAlpha(alpha)
            b_grad.setColorAt(0.0, col)
            col_t = QColor(self.bounce_color)
            col_t.setAlpha(0)
            b_grad.setColorAt(0.70, col_t)
            p.setBrush(QBrush(b_grad))
            p.drawRect(self.rect())

        spec_x = cx + self.lx * r * 0.80
        spec_y = cy + self.ly * r * 0.80
        spec = QRadialGradient(spec_x, spec_y, r * 0.28)
        spec.setColorAt(0.0, QColor(255, 245, 235, 140))
        spec.setColorAt(0.45, QColor(255, 235, 220, 50))
        spec.setColorAt(1.0, QColor(255, 235, 220, 0))
        p.setBrush(QBrush(spec))
        p.drawRect(self.rect())


class LightSpherePickerDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.last_sent_color = None
        self.ignore_sync_until = 0

        # DETECCIÓN AUTOMÁTICA DEL IDIOMA
        # Si el sistema está en español, usa 'es', para todo lo demás usa 'en'
        loc = QLocale.system().name().lower()
        self.lang = "es" if loc.startswith("es") else "en"

        self.material_memory = {
            "plastico": {
                "base": QColor(220, 60, 110),
                "shadow": None,
                "use_comp": True,
                "bounce": QColor(100, 220, 255),
                "intensity": 60,
                "lx": -0.50,
                "ly": -0.55,
            },
            "piel": {
                "base": QColor(230, 180, 140),
                "shadow": None,
                "use_comp": True,
                "bounce": QColor(120, 160, 220),
                "intensity": 50,
                "lx": -0.50,
                "ly": -0.55,
            },
        }

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Barra superior con selector de idioma
        top_bar = QHBoxLayout()
        self.btn_lang = QPushButton(self.lang.upper())
        self.btn_lang.setFixedSize(28, 18)
        self.btn_lang.setToolTip("Switch Language (ES / EN)")
        self.btn_lang.setStyleSheet(
            "background-color: #242528; color: #888; border: 1px solid #444; border-radius: 2px; font-size: 9px;"
        )
        self.btn_lang.clicked.connect(self.toggle_language)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_lang)
        layout.addLayout(top_bar)

        self.sphere = LitSphereView()
        layout.addWidget(self.sphere)

        btn_style = """
            QPushButton {
                background-color: #383A40;
                color: #DDD;
                border: 1px solid #222;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #484B52;
            }
            QPushButton:checked {
                background-color: #2D6BBA;
                color: white;
                font-weight: bold;
                border: 1px solid #5A9BEF;
            }
        """

        mat_layout = QHBoxLayout()
        mat_layout.setSpacing(4)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_plastico = QPushButton()
        self.btn_piel = QPushButton()
        self.btn_plastico.setCheckable(True)
        self.btn_piel.setCheckable(True)

        for b in [self.btn_plastico, self.btn_piel]:
            b.setStyleSheet(btn_style)
            self.btn_group.addButton(b)
            mat_layout.addWidget(b)

        self.btn_plastico.setChecked(True)
        self.btn_plastico.clicked.connect(
            lambda: self.switch_material("plastico")
        )
        self.btn_piel.clicked.connect(lambda: self.switch_material("piel"))
        layout.addLayout(mat_layout)

        checks_row = QHBoxLayout()
        checks_row.setSpacing(4)
        self.chk_sync = QCheckBox()
        self.chk_sync.setChecked(True)
        self.chk_sync.setStyleSheet("font-size: 11px;")

        self.chk_comp_shadow = QCheckBox()
        self.chk_comp_shadow.setChecked(True)
        self.chk_comp_shadow.setStyleSheet("font-size: 11px;")
        self.chk_comp_shadow.toggled.connect(self.on_toggle_comp_shadow)

        checks_row.addWidget(self.chk_sync)
        checks_row.addWidget(self.chk_comp_shadow)
        layout.addLayout(checks_row)

        adj_row = QHBoxLayout()
        adj_row.setSpacing(3)

        self.btn_custom_shadow = QPushButton()
        self.btn_custom_shadow.setStyleSheet(btn_style)
        self.btn_custom_shadow.clicked.connect(self.choose_custom_shadow)

        self.btn_bounce_col = QPushButton()
        self.btn_bounce_col.setStyleSheet(btn_style)
        self.btn_bounce_col.clicked.connect(self.choose_bounce_color)

        self.btn_auto_bounce = QPushButton()
        self.btn_auto_bounce.setStyleSheet(btn_style)
        self.btn_auto_bounce.clicked.connect(self.reset_auto_bounce)

        adj_row.addWidget(self.btn_custom_shadow)
        adj_row.addWidget(self.btn_bounce_col)
        adj_row.addWidget(self.btn_auto_bounce)
        layout.addLayout(adj_row)

        slider_row = QHBoxLayout()
        self.lbl_rebote = QLabel()
        self.lbl_rebote.setStyleSheet("font-size: 10px; color: #AAA;")
        slider_row.addWidget(self.lbl_rebote)

        self.slider_bounce = QSlider(Qt.Horizontal)
        self.slider_bounce.setRange(0, 100)
        self.slider_bounce.setValue(60)
        self.slider_bounce.setFixedHeight(16)
        self.slider_bounce.valueChanged.connect(self.on_bounce_intensity_change)
        slider_row.addWidget(self.slider_bounce)
        layout.addLayout(slider_row)

        self.palette_row = QHBoxLayout()
        self.palette_row.setSpacing(3)

        self.chip_light = QPushButton()
        self.chip_mid = QPushButton()
        self.chip_shadow = QPushButton()
        self.chip_bounce = QPushButton()

        for chip in [
            self.chip_light,
            self.chip_mid,
            self.chip_shadow,
            self.chip_bounce,
        ]:
            chip.setFixedHeight(22)
            chip.setStyleSheet(
                "border-radius: 3px; border: 1px solid #111; font-weight: bold; font-size: 10px; color: #FFF;"
            )
            self.palette_row.addWidget(chip)

        self.chip_light.clicked.connect(lambda: self.send_to_krita(self.col_lit))
        self.chip_mid.clicked.connect(
            lambda: self.send_to_krita(self.sphere.base_color)
        )
        self.chip_shadow.clicked.connect(
            lambda: self.send_to_krita(self.col_shadow)
        )
        self.chip_bounce.clicked.connect(
            lambda: self.send_to_krita(self.col_bounce)
        )
        layout.addLayout(self.palette_row)

        history_box = QHBoxLayout()
        self.btn_save_pal = QPushButton("💾")
        self.btn_save_pal.setFixedWidth(28)
        self.btn_save_pal.setStyleSheet(btn_style)
        self.btn_save_pal.clicked.connect(self.save_current_palette_to_history)
        history_box.addWidget(self.btn_save_pal)

        self.history_layout = QHBoxLayout()
        self.history_layout.setSpacing(2)
        history_box.addLayout(self.history_layout)
        history_box.addStretch()
        layout.addLayout(history_box)

        scroll.setWidget(content)
        self.setWidget(scroll)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_with_krita_color)
        self.timer.start(120)

        # Aplicar textos del idioma actual
        self.retranslate_ui()
        self.update_live_palette()

    def canvasChanged(self, canvas):
        pass

    def toggle_language(self):
        self.lang = "en" if self.lang == "es" else "es"
        self.btn_lang.setText(self.lang.upper())
        self.retranslate_ui()

    def retranslate_ui(self):
        t = TEXTS[self.lang]
        self.setWindowTitle(t["title"])
        self.sphere.setToolTip(t["tooltip_sphere"])
        self.btn_plastico.setText(t["plastic"])
        self.btn_piel.setText(t["skin"])
        self.chk_sync.setText(t["sync"])
        self.chk_comp_shadow.setText(t["auto_shadow"])
        self.btn_custom_shadow.setText(t["custom_shadow"])
        self.btn_bounce_col.setText(t["bounce_color"])
        self.btn_auto_bounce.setText(t["auto_bounce"])
        self.lbl_rebote.setText(t["bounce_label"])
        self.chip_light.setText(t["light"])
        self.chip_mid.setText(t["mid"])
        self.chip_shadow.setText(t["shadow"])
        self.chip_bounce.setText(t["bounce"])
        self.btn_save_pal.setToolTip(t["save_tooltip"])

    def save_current_material_state(self):
        mat = self.sphere.material
        self.material_memory[mat] = {
            "base": QColor(self.sphere.base_color),
            "shadow": (
                QColor(self.sphere.custom_shadow_color)
                if self.sphere.custom_shadow_color
                else None
            ),
            "use_comp": self.sphere.use_complementary_shadow,
            "bounce": QColor(self.sphere.bounce_color),
            "intensity": self.sphere.bounce_intensity,
            "lx": self.sphere.lx,
            "ly": self.sphere.ly,
        }

    def switch_material(self, new_mat):
        self.save_current_material_state()
        self.sphere.material = new_mat
        data = self.material_memory[new_mat]

        self.sphere.base_color = QColor(data["base"])
        self.sphere.custom_shadow_color = (
            QColor(data["shadow"]) if data["shadow"] else None
        )
        self.sphere.use_complementary_shadow = data["use_comp"]
        self.sphere.bounce_color = QColor(data["bounce"])
        self.sphere.bounce_intensity = data["intensity"]
        self.sphere.lx = data["lx"]
        self.sphere.ly = data["ly"]

        self.chk_comp_shadow.blockSignals(True)
        self.chk_comp_shadow.setChecked(data["use_comp"])
        self.chk_comp_shadow.blockSignals(False)

        self.slider_bounce.blockSignals(True)
        self.slider_bounce.setValue(data["intensity"])
        self.slider_bounce.blockSignals(False)

        self.sphere.update()
        self.update_live_palette()

    def on_toggle_comp_shadow(self, checked):
        self.sphere.use_complementary_shadow = checked
        self.sphere.update()
        self.update_live_palette()

    def choose_custom_shadow(self):
        t = TEXTS[self.lang]
        col = QColorDialog.getColor(
            self.sphere.get_shadow_color(), self, t["picker_title_shadow"]
        )
        if col.isValid():
            self.sphere.custom_shadow_color = col
            self.sphere.use_complementary_shadow = False
            self.chk_comp_shadow.setChecked(False)
            self.sphere.update()
            self.update_live_palette()

    def choose_bounce_color(self):
        t = TEXTS[self.lang]
        col = QColorDialog.getColor(
            self.sphere.bounce_color, self, t["picker_title_bounce"]
        )
        if col.isValid():
            self.sphere.bounce_color = col
            self.sphere.update()
            self.update_live_palette()

    def on_bounce_intensity_change(self, val):
        self.sphere.bounce_intensity = val
        self.sphere.update()
        self.update_live_palette()

    def reset_auto_bounce(self):
        self.sphere.auto_bounce = True
        self.sphere.bx = -self.sphere.lx * 0.90
        self.sphere.by = max(0.18, -self.sphere.ly * 0.85)
        self.sphere.update()
        self.update_live_palette()

    def update_live_palette(self):
        self.col_lit = self.sphere.base_color.lighter(135)
        self.col_mid = self.sphere.base_color
        self.col_shadow = self.sphere.get_shadow_color()
        self.col_bounce = self.sphere.bounce_color

        def style_for(c):
            txt = "#000" if c.value() > 160 else "#FFF"
            return f"background-color: {c.name()}; color: {txt}; border: 1px solid #111; border-radius: 3px; font-weight: bold; font-size: 10px;"

        self.chip_light.setStyleSheet(style_for(self.col_lit))
        self.chip_mid.setStyleSheet(style_for(self.col_mid))
        self.chip_shadow.setStyleSheet(style_for(self.col_shadow))
        self.chip_bounce.setStyleSheet(style_for(self.col_bounce))

    def send_to_krita(self, qcol):
        self.last_sent_color = qcol
        self.ignore_sync_until = time.time() + 0.6

        app = Krita.instance()
        if app.activeWindow() and app.activeWindow().activeView():
            view = app.activeWindow().activeView()
            mc = ManagedColor.fromQColor(qcol, view.canvas())
            view.setForeGroundColor(mc)

    def save_current_palette_to_history(self):
        for col in [self.col_lit, self.col_mid, self.col_shadow]:
            dot = QPushButton()
            dot.setFixedSize(16, 16)
            dot.setStyleSheet(
                f"background-color: {col.name()}; border-radius: 2px; border: 1px solid #111;"
            )
            dot.clicked.connect(lambda _, c=col: self.send_to_krita(c))
            self.history_layout.addWidget(dot)

        while self.history_layout.count() > 12:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def sync_with_krita_color(self):
        if not self.chk_sync.isChecked():
            return
        if time.time() < self.ignore_sync_until:
            return

        app = Krita.instance()
        if not app:
            return
        win = app.activeWindow()
        if not win:
            return
        view = win.activeView()
        if not view:
            return

        canvas = view.canvas()
        fg = view.foregroundColor()
        if not fg:
            return

        qcol = None
        try:
            if canvas:
                qcol = fg.colorForCanvas(canvas)
        except:
            pass

        if not qcol or not qcol.isValid():
            try:
                comps = fg.componentsOrdered()
                if len(comps) >= 3:
                    qcol = QColor.fromRgbF(
                        max(0.0, min(1.0, comps[0])),
                        max(0.0, min(1.0, comps[1])),
                        max(0.0, min(1.0, comps[2])),
                    )
            except:
                pass

        if qcol and qcol.isValid():
            if self.last_sent_color and self._is_same_color(
                qcol, self.last_sent_color
            ):
                return
            if not self._is_same_color(qcol, self.sphere.base_color):
                self.sphere.base_color = qcol
                self.sphere.update()
                self.update_live_palette()

    def _is_same_color(self, c1, c2):
        return (
            abs(c1.red() - c2.red()) <= 1
            and abs(c1.green() - c2.green()) <= 1
            and abs(c1.blue() - c2.blue()) <= 1
        )
