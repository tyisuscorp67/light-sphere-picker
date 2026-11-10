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
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from krita import DockWidget, Krita, ManagedColor

# DICCIONARIO BILINGÜE
TEXTS = {
    "es": {
        "title": "Esfera de Luz",
        "plastic": "Plástico / Tela",
        "skin": "Piel (Ilustración)",
        "sync": "🔗 Sync Krita",
        "shadow_analog": "Sombra: Ilustración (Cálida)",
        "shadow_comp": "Sombra: Complementaria",
        "shadow_mono": "Sombra: Monocroma",
        "custom_shadow": "Sombra...",
        "reset_shadow": "↺ Reset",
        "reset_tooltip": "Restablecer a sombra automática base",
        "bounce_color": "Rebote...",
        "auto_bounce": "Auto",
        "bounce_label": "Rebote:",
        "light": "Luz",
        "base": "Base",
        "trans": "Trans.",
        "shadow": "Sombra",
        "bounce": "Rebote",
        "save_tooltip": "Guardar paleta de 5 tonos en el historial",
        "tooltip_sphere": "• Clic Izquierdo (arrastrar): Mover Luz\n• Clic Derecho (arrastrar): Mover Rebote\n• Clic simple: Tomar color",
        "picker_title_shadow": "Elegir Color de Sombra",
        "picker_title_bounce": "Elegir Color de Rebote",
    },
    "en": {
        "title": "Light Sphere",
        "plastic": "Plastic / Fabric",
        "skin": "Skin (Illustration)",
        "sync": "🔗 Sync Krita",
        "shadow_analog": "Shadow: Illustration (Warm)",
        "shadow_comp": "Shadow: Complementary",
        "shadow_mono": "Shadow: Monochromatic",
        "custom_shadow": "Shadow...",
        "reset_shadow": "↺ Reset",
        "reset_tooltip": "Reset to base automatic shadow",
        "bounce_color": "Bounce...",
        "auto_bounce": "Auto",
        "bounce_label": "Bounce:",
        "light": "Light",
        "base": "Base",
        "trans": "Trans.",
        "shadow": "Shadow",
        "bounce": "Bounce",
        "save_tooltip": "Save 5-tone palette to history",
        "tooltip_sphere": "• Left Drag: Move Light\n• Right Drag: Move Bounce\n• Click: Pick color",
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
        self.bounce_intensity = 55
        self.auto_bounce = True

        self.base_color = QColor(225, 180, 145)
        self.bounce_color = QColor(135, 170, 220)
        self.custom_shadow_color = None

        self.shadow_mode = "analoga"
        self.material = "piel"

        self.dragging_light = False
        self.dragging_bounce = False
        self.press_pos = None
        self.has_dragged = False

    def get_transition_color(self):
        """Calcula el tono de borde vivo/cálido entre la luz y la sombra"""
        h = self.base_color.hue()
        if h < 0:
            h = 0
        s = self.base_color.saturation()
        v = self.base_color.value()

        # En piel y tonos cálidos, satura e intensifica hacia el carmín/naranja vivo
        if 10 <= h <= 65:
            trans_h = (h - 12) % 360
            trans_s = min(255, int(s * 1.35 + 25))
            trans_v = int(v * 0.82)
        elif 65 < h <= 170:  # Verdes
            trans_h = (h - 10) % 360
            trans_s = min(255, int(s * 1.25 + 20))
            trans_v = int(v * 0.78)
        else:  # Azules y fríos
            trans_h = (h + 10) % 360
            trans_s = min(255, int(s * 1.20 + 20))
            trans_v = int(v * 0.80)

        return QColor.fromHsv(trans_h, trans_s, trans_v)

    def get_shadow_color(self):
        """Calcula la sombra con cuerpo terroso como en la ilustración del usuario"""
        if self.custom_shadow_color:
            return self.custom_shadow_color

        h = self.base_color.hue()
        if h < 0:
            h = 0
        s = self.base_color.saturation()
        v = self.base_color.value()

        if self.shadow_mode == "analoga":
            # Estilo Bárbaro: sombras con cuerpo castaño/terracota sólido
            if 10 <= h <= 65:
                shift = -18  # Hacia castaño/carmín profundo
                new_s = min(255, int(s * 1.15 + 30))
                new_v = int(v * 0.48)
            elif 65 < h <= 170:  # Capa verde -> verde bosque profundo
                shift = 20
                new_s = min(255, int(s * 1.10 + 25))
                new_v = int(v * 0.40)
            elif 170 < h <= 255:  # Pantalón azul/gris -> carbón azulado profundo
                shift = -20
                new_s = min(255, int(s * 1.10 + 15))
                new_v = int(v * 0.38)
            else:
                shift = -15
                new_s = min(255, int(s * 1.15 + 20))
                new_v = int(v * 0.42)

            new_h = (h + shift) % 360
            return QColor.fromHsv(new_h, new_s, new_v)

        elif self.shadow_mode == "complementaria":
            comp_h = (h + 160) % 360
            comp_s = min(255, int(s * 1.15 + 20))
            comp_v = int(v * 0.38)
            return QColor.fromHsv(comp_h, comp_s, comp_v)
        else:
            new_s = min(255, int(s * 1.20 + 10))
            new_v = int(v * 0.40)
            return QColor.fromHsv(h, new_s, new_v)

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

        # Sombra en suelo
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
            self._render_skin_illust(painter, cx, cy, r)
        else:
            self._render_plastic(painter, cx, cy, r)

        painter.restore()

        # Oclusión perimetral (Fresnel suave)
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
            b_grad.setColorAt(0.65, QColor(col.red(), col.green(), col.blue(), 0))
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

    def _render_skin_illust(self, p, cx, cy, r):
        """Renderizado con la banda de transición visible como en la ilustración"""
        lx_pos = cx + self.lx * r * 0.74
        ly_pos = cy + self.ly * r * 0.74

        diffuse = QRadialGradient(lx_pos, ly_pos, r * 1.60)
        diffuse.setColorAt(0.0, self.base_color.lighter(125))
        diffuse.setColorAt(0.34, self.base_color)

        # Banda de transición viva (Terminador cálido)
        trans_col = self.get_transition_color()
        diffuse.setColorAt(0.55, trans_col)

        # Sombra con cuerpo
        shadow_col = self.get_shadow_color()
        diffuse.setColorAt(0.82, shadow_col)
        diffuse.setColorAt(1.0, shadow_col.darker(120))

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
            b_grad.setColorAt(0.70, QColor(col.red(), col.green(), col.blue(), 0))
            p.setBrush(QBrush(b_grad))
            p.drawRect(self.rect())

        # Brillo suave de ilustración
        spec_x = cx + self.lx * r * 0.78
        spec_y = cy + self.ly * r * 0.78
        spec = QRadialGradient(spec_x, spec_y, r * 0.25)
        spec.setColorAt(0.0, QColor(255, 248, 240, 150))
        spec.setColorAt(0.50, QColor(255, 240, 225, 45))
        spec.setColorAt(1.0, QColor(255, 240, 225, 0))
        p.setBrush(QBrush(spec))
        p.drawRect(self.rect())


class LightSpherePickerDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.last_sent_color = None
        self.ignore_sync_until = 0

        loc = QLocale.system().name().lower()
        self.lang = "es" if loc.startswith("es") else "en"

        self.material_memory = {
            "plastico": {
                "base": QColor(220, 60, 110),
                "shadow": None,
                "shadow_mode": "analoga",
                "bounce": QColor(100, 220, 255),
                "intensity": 60,
                "lx": -0.50,
                "ly": -0.55,
            },
            "piel": {
                "base": QColor(225, 180, 145),
                "shadow": None,
                "shadow_mode": "analoga",
                "bounce": QColor(135, 170, 220),
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

        self.btn_piel.setChecked(True)
        self.btn_plastico.clicked.connect(
            lambda: self.switch_material("plastico")
        )
        self.btn_piel.clicked.connect(lambda: self.switch_material("piel"))
        layout.addLayout(mat_layout)

        sync_row = QHBoxLayout()
        self.chk_sync = QCheckBox()
        self.chk_sync.setChecked(True)
        self.chk_sync.setStyleSheet("font-size: 11px;")
        sync_row.addWidget(self.chk_sync)
        layout.addLayout(sync_row)

        self.combo_shadow = QComboBox()
        self.combo_shadow.setStyleSheet(
            "QComboBox { background-color: #2A2B2E; color: #EEE; border: 1px solid #444; border-radius: 3px; padding: 2px 4px; font-size: 11px; }"
        )
        self.combo_shadow.addItem("", "analoga")
        self.combo_shadow.addItem("", "complementaria")
        self.combo_shadow.addItem("", "monocroma")
        self.combo_shadow.currentIndexChanged.connect(
            self.on_shadow_mode_changed
        )
        layout.addWidget(self.combo_shadow)

        shadow_row = QHBoxLayout()
        shadow_row.setSpacing(3)

        self.btn_custom_shadow = QPushButton()
        self.btn_custom_shadow.setStyleSheet(btn_style)
        self.btn_custom_shadow.clicked.connect(self.choose_custom_shadow)

        self.btn_reset_shadow = QPushButton()
        self.btn_reset_shadow.setStyleSheet(
            btn_style
            + "QPushButton:enabled { color: #E58B8B; } QPushButton:disabled { color: #666; }"
        )
        self.btn_reset_shadow.setEnabled(False)
        self.btn_reset_shadow.clicked.connect(self.reset_shadow_to_auto)

        shadow_row.addWidget(self.btn_custom_shadow)
        shadow_row.addWidget(self.btn_reset_shadow)
        layout.addLayout(shadow_row)

        bounce_row = QHBoxLayout()
        bounce_row.setSpacing(3)
        self.btn_bounce_col = QPushButton()
        self.btn_bounce_col.setStyleSheet(btn_style)
        self.btn_bounce_col.clicked.connect(self.choose_bounce_color)

        self.btn_auto_bounce = QPushButton()
        self.btn_auto_bounce.setStyleSheet(btn_style)
        self.btn_auto_bounce.clicked.connect(self.reset_auto_bounce)

        bounce_row.addWidget(self.btn_bounce_col)
        bounce_row.addWidget(self.btn_auto_bounce)
        layout.addLayout(bounce_row)

        slider_row = QHBoxLayout()
        self.lbl_rebote = QLabel()
        self.lbl_rebote.setStyleSheet("font-size: 10px; color: #AAA;")
        slider_row.addWidget(self.lbl_rebote)

        self.slider_bounce = QSlider(Qt.Horizontal)
        self.slider_bounce.setRange(0, 100)
        self.slider_bounce.setValue(55)
        self.slider_bounce.setFixedHeight(16)
        self.slider_bounce.valueChanged.connect(self.on_bounce_intensity_change)
        slider_row.addWidget(self.slider_bounce)
        layout.addLayout(slider_row)

        # 5 MUESTRAS EN VIVO PARA PINTURA: [Luz] [Base] [Trans.] [Sombra] [Rebote]
        self.palette_row = QHBoxLayout()
        self.palette_row.setSpacing(2)

        self.chip_light = QPushButton()
        self.chip_base = QPushButton()
        self.chip_trans = QPushButton()
        self.chip_shadow = QPushButton()
        self.chip_bounce = QPushButton()

        for chip in [
            self.chip_light,
            self.chip_base,
            self.chip_trans,
            self.chip_shadow,
            self.chip_bounce,
        ]:
            chip.setFixedHeight(22)
            chip.setStyleSheet(
                "border-radius: 3px; border: 1px solid #111; font-weight: bold; font-size: 9px; color: #FFF;"
            )
            self.palette_row.addWidget(chip)

        self.chip_light.clicked.connect(lambda: self.send_to_krita(self.col_lit))
        self.chip_base.clicked.connect(
            lambda: self.send_to_krita(self.sphere.base_color)
        )
        self.chip_trans.clicked.connect(
            lambda: self.send_to_krita(self.col_trans)
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

        self.combo_shadow.blockSignals(True)
        self.combo_shadow.setItemText(0, t["shadow_analog"])
        self.combo_shadow.setItemText(1, t["shadow_comp"])
        self.combo_shadow.setItemText(2, t["shadow_mono"])
        self.combo_shadow.blockSignals(False)

        self.btn_custom_shadow.setText(t["custom_shadow"])
        self.btn_reset_shadow.setText(t["reset_shadow"])
        self.btn_reset_shadow.setToolTip(t["reset_tooltip"])

        self.btn_bounce_col.setText(t["bounce_color"])
        self.btn_auto_bounce.setText(t["auto_bounce"])
        self.lbl_rebote.setText(t["bounce_label"])

        self.chip_light.setText(t["light"])
        self.chip_base.setText(t["base"])
        self.chip_trans.setText(t["trans"])
        self.chip_shadow.setText(t["shadow"])
        self.chip_bounce.setText(t["bounce"])
        self.btn_save_pal.setToolTip(t["save_tooltip"])

    def on_shadow_mode_changed(self, index):
        mode = self.combo_shadow.itemData(index)
        self.sphere.shadow_mode = mode
        self.sphere.custom_shadow_color = None
        self.btn_reset_shadow.setEnabled(False)
        self.sphere.update()
        self.update_live_palette()

    def choose_custom_shadow(self):
        t = TEXTS[self.lang]
        col = QColorDialog.getColor(
            self.sphere.get_shadow_color(), self, t["picker_title_shadow"]
        )
        if col.isValid():
            self.sphere.custom_shadow_color = col
            self.btn_reset_shadow.setEnabled(True)
            self.sphere.update()
            self.update_live_palette()

    def reset_shadow_to_auto(self):
        self.sphere.custom_shadow_color = None
        self.btn_reset_shadow.setEnabled(False)
        self.sphere.update()
        self.update_live_palette()

    def save_current_material_state(self):
        mat = self.sphere.material
        self.material_memory[mat] = {
            "base": QColor(self.sphere.base_color),
            "shadow": (
                QColor(self.sphere.custom_shadow_color)
                if self.sphere.custom_shadow_color
                else None
            ),
            "shadow_mode": self.sphere.shadow_mode,
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
        self.sphere.shadow_mode = data.get("shadow_mode", "analoga")
        self.sphere.bounce_color = QColor(data["bounce"])
        self.sphere.bounce_intensity = data["intensity"]
        self.sphere.lx = data["lx"]
        self.sphere.ly = data["ly"]

        idx = self.combo_shadow.findData(self.sphere.shadow_mode)
        if idx >= 0:
            self.combo_shadow.blockSignals(True)
            self.combo_shadow.setCurrentIndex(idx)
            self.combo_shadow.blockSignals(False)

        self.btn_reset_shadow.setEnabled(bool(self.sphere.custom_shadow_color))

        self.slider_bounce.blockSignals(True)
        self.slider_bounce.setValue(data["intensity"])
        self.slider_bounce.blockSignals(False)

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
        self.col_lit = self.sphere.base_color.lighter(130)
        self.col_base = self.sphere.base_color
        self.col_trans = self.sphere.get_transition_color()
        self.col_shadow = self.sphere.get_shadow_color()
        self.col_bounce = self.sphere.bounce_color

        def style_for(c):
            txt = "#000" if c.value() > 160 else "#FFF"
            return f"background-color: {c.name()}; color: {txt}; border: 1px solid #111; border-radius: 3px; font-weight: bold; font-size: 9px;"

        self.chip_light.setStyleSheet(style_for(self.col_lit))
        self.chip_base.setStyleSheet(style_for(self.col_base))
        self.chip_trans.setStyleSheet(style_for(self.col_trans))
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
        for col in [
            self.col_lit,
            self.col_base,
            self.col_trans,
            self.col_shadow,
            self.col_bounce,
        ]:
            dot = QPushButton()
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(
                f"background-color: {col.name()}; border-radius: 2px; border: 1px solid #111;"
            )
            dot.clicked.connect(lambda _, c=col: self.send_to_krita(c))
            self.history_layout.addWidget(dot)

        while self.history_layout.count() > 15:
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
