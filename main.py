import sys
import json
import os
import difflib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QTabWidget, QMessageBox, QScrollArea, QFrame, QTextEdit, QDialog,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QWheelEvent

CONFIG_FILE = "config.json"
ITEMS_FILE = "items.json"

class CustomScrollArea(QScrollArea):
    """자식 위젯의 휠 이벤트를 처리하기 위한 커스텀 스크롤 영역"""
    def wheelEvent(self, event: QWheelEvent):
        self.verticalScrollBar().event(event)

class CustomListWidget(QListWidget):
    """휠 이벤트를 부모 스크롤 영역으로 전달하는 리스트 위젯"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
        parent_scroll_area = self.window().findChild(CustomScrollArea)
        if parent_scroll_area:
            # 새 휠 이벤트를 생성하여 부모로 전달
            new_event = QWheelEvent(event.pos(), event.globalPos(), event.pixelDelta(),
                                    event.angleDelta(), event.buttons(), event.modifiers(),
                                    event.phase(), event.inverted(), event.source())
            QApplication.sendEvent(parent_scroll_area, new_event)
        else:
            super().wheelEvent(event)

class ItemEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("에스테리아 아이템 생성기")
        self.resize(800, 700)

        # 1. 설정 파일 로드 (오류 처리 강화)
        self.config = self.load_config()
        if self.config is None:
            # load_config 내부에서 이미 오류 메시지를 표시했으므로 바로 종료
            sys.exit(1)

        # 2. 설정 파일의 키 값에 오타가 있는지 확인하고 수정 제안 (훈수 기능)
        self.check_and_suggest_corrections()

        self.items = self.load_items()
        self.current_type = "무기"
        self.is_dark_mode = True

        self.init_ui()
        self.apply_styles()

    def show_config_help_dialog(self):
        """config.json 파일의 올바른 예시를 보여주는 도움말 대화상자"""
        dialog = QDialog(self)
        dialog.setWindowTitle("config.json 작성 예시")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        label = QLabel("아래는 올바르게 작성된 `config.json` 파일의 예시입니다.\n파일을 이 형식에 맞게 수정해 보세요.", dialog)
        label.setWordWrap(True)
        layout.addWidget(label)

        # 올바른 JSON 예시를 보여주는 텍스트 상자
        example_text = QTextEdit(dialog)
        example_text.setReadOnly(True)
        example_text.setFont(QFont("Courier New", 10))
        example_text.setPlainText("""
{
  "공통": {
    "이름": {
      "tooltip": "아이템의 고유한 이름입니다."
    },
    "등급": {
      "options": ["일반", "고급", "희귀", "영웅", "전설"],
      "tooltip": "아이템의 등급을 선택합니다."
    }
  },
  "무기": {
    "무기 종류": {
      "options": ["한손검", "양손검", "활", "지팡이"],
      "tooltip": "무기의 종류를 선택합니다."
    },
    "공격력": {
      "tooltip": "무기의 기본 공격력입니다."
    }
  },
  "방어구": {
    "방어구 종류": {
      "options": ["투구", "갑옷", "장갑", "신발"],
      "tooltip": "방어구의 종류를 선택합니다."
    },
    "방어력": {
      "tooltip": "방어구의 기본 방어력입니다."
    }
  }
}
""")
        layout.addWidget(example_text)

        close_button = QPushButton("닫기", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec_()


    def load_config(self):
        """설정 파일을 불러옵니다. 오류 발생 시 사용자 친화적인 메시지를 표시합니다."""
        if not os.path.exists(CONFIG_FILE):
            QMessageBox.critical(self, "오류", f"'{CONFIG_FILE}' 파일을 찾을 수 없습니다. 프로그램을 종료합니다.")
            return None

        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # 더 이해하기 쉬운 오류 메시지 상자 생성
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("설정 파일 오류")

            # 사용자 친화적인 설명 추가
            error_intro = f"'{CONFIG_FILE}' 파일의 형식이 잘못되었습니다.\n" \
                          "JSON 형식은 중괄호 `{{ }}`, 대괄호 `[ ]`, 쉼표 `,` 등의 규칙이 매우 중요합니다.\n\n" \
                          "오타나 빠진 쉼표가 있는지 확인해주세요."

            # 오류 위치 정보 추가
            error_details = f"오류 종류: {e.msg}\n"
            error_location = ""
            try:
                # 오류가 발생한 줄을 찾아서 보여주기
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f_read:
                    lines = f_read.readlines()
                    if 1 <= e.lineno <= len(lines):
                        problem_line = lines[e.lineno - 1].rstrip()
                        error_location = f"오류 발생 위치 (대략):\n" \
                                         f"줄 {e.lineno}: {problem_line}\n" + \
                                         ' ' * (len(f"줄 {e.lineno}: ") + e.colno - 1) + "▲\n"
            except Exception:
                pass # 파일 읽기 실패 시 위치 정보는 생략

            msg_box.setText(error_intro)
            msg_box.setInformativeText(error_details + error_location + "파일을 수정한 후 프로그램을 다시 시작해주세요.")

            # 도움말("예시 보기") 버튼과 종료 버튼 추가
            help_button = msg_box.addButton("예시 보기", QMessageBox.HelpRole)
            exit_button = msg_box.addButton("종료", QMessageBox.RejectRole)

            msg_box.exec_()

            # '예시 보기' 버튼이 눌렸는지 확인
            if msg_box.clickedButton() == help_button:
                self.show_config_help_dialog()

            return None # 오류가 발생했으므로 None 반환
        except Exception as e:
            QMessageBox.critical(self, "알 수 없는 오류", f"'{CONFIG_FILE}' 파일 처리 중 오류 발생: {e}")
            return None

    def check_and_suggest_corrections(self):
        """설정 파일의 키 값에 오타가 있는지 확인하고 수정 제안 (훈수 기능)"""
        if not self.config:
            return

        valid_keys = {"options", "tooltip"}
        corrections_made = False

        # config 딕셔너리를 재귀적으로 탐색하는 함수
        def find_and_correct(data_dict):
            nonlocal corrections_made
            # "dictionary changed size during iteration" 오류 방지를 위해 키 목록 복사
            for key in list(data_dict.keys()):
                # 하위 딕셔너리 탐색
                if isinstance(data_dict[key], dict):
                    find_and_correct(data_dict[key])

                # 유효한 키 목록과 비교하여 비슷한 키 찾기
                matches = difflib.get_close_matches(key, valid_keys, n=1, cutoff=0.7)
                if matches and key != matches[0]:
                    reply = QMessageBox.question(self, "오타 수정 제안 (훈수)",
                                                 f"`config.json` 파일에서 '{key}' 키를 찾았습니다.\n"
                                                 f"혹시 '{matches[0]}'의 오타인가요? 수정하시겠습니까?",
                                                 QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        # 키 이름을 올바른 것으로 수정
                        data_dict[matches[0]] = data_dict.pop(key)
                        corrections_made = True

        find_and_correct(self.config)

        # 수정된 내용이 있다면 파일에 저장할지 물어봄
        if corrections_made:
            reply = QMessageBox.question(self, "저장 확인",
                                         "오타가 수정되었습니다. 변경된 내용을\n"
                                         f"'{CONFIG_FILE}' 파일에 저장하시겠습니까?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                self.status_message("설정 파일이 업데이트되었습니다.")


    def load_items(self):
        if os.path.exists(ITEMS_FILE):
            with open(ITEMS_FILE, encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError as e:
                    QMessageBox.warning(self, "아이템 파일 오류",
                                        f"'{ITEMS_FILE}' 파일이 손상되었습니다.\n오류: {e}\n새 목록으로 시작합니다.")
                    return []
        return []

    def save_items(self):
        with open(ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def init_ui(self):
        self.main_scroll_area = CustomScrollArea()
        self.main_scroll_area.setWidgetResizable(True)

        self.main_widget_content = QWidget()
        main_layout = QVBoxLayout(self.main_widget_content)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        self.theme_toggle_btn = QPushButton("라이트 모드로 전환")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        main_layout.addWidget(self.theme_toggle_btn, alignment=Qt.AlignRight)

        self.tabs = QTabWidget()
        # config가 유효할 때만 탭 이름 설정
        if self.config:
            tab_names = [name for name in self.config.keys() if name != "공통"]
            self.tabs.clear()
            for name in tab_names:
                self.tabs.addTab(QWidget(), name)
            if tab_names:
                self.current_type = tab_names[0]
        else:
            self.tabs.addTab(QWidget(), "무기")
            self.tabs.addTab(QWidget(), "방어구")


        self.tabs.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs)

        self.type_label = QLabel(f"현재 타입: {self.current_type}")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.type_label.setFont(font)
        self.type_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.type_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        self.form_scroll = CustomScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)
        self.form_layout.setAlignment(Qt.AlignTop)
        self.form_layout.setContentsMargins(10, 10, 10, 10)
        self.form_layout.setSpacing(10)
        self.form_scroll.setWidget(self.form_widget)
        self.form_scroll.setMinimumWidth(380)
        self.form_scroll.setFrameShape(QFrame.NoFrame)
        content_layout.addWidget(self.form_scroll, 3)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        item_list_label = QLabel("생성된 아이템 리스트")
        item_list_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        right_layout.addWidget(item_list_label)

        self.item_list = CustomListWidget()
        self.item_list.itemClicked.connect(self.on_item_selected)
        right_layout.addWidget(self.item_list, 3)

        detail_label = QLabel("선택 아이템 상세 보기")
        detail_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        right_layout.addWidget(detail_label)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("아이템 선택 시 상세 정보가 여기에 표시됩니다.")
        right_layout.addWidget(self.detail_text, 3)

        btn_layout_row1 = QHBoxLayout()
        btn_layout_row2 = QHBoxLayout()
        btn_layout_row1.setSpacing(8)
        btn_layout_row2.setSpacing(8)

        self.add_btn = QPushButton("아이템 추가/수정")
        self.add_btn.clicked.connect(self.add_item)
        self.copy_json_btn = QPushButton("JSON 복사")
        self.copy_json_btn.clicked.connect(self.copy_selected_item_json)
        self.copy_text_btn = QPushButton("일반 텍스트 복사")
        self.copy_text_btn.clicked.connect(self.copy_selected_item_text)
        self.copy_latest_btn = QPushButton("최근 생성 아이템 복사")
        self.copy_latest_btn.clicked.connect(self.copy_latest_item)
        self.delete_btn = QPushButton("선택 아이템 삭제")
        self.delete_btn.clicked.connect(self.delete_selected_item)
        self.delete_btn.setObjectName("delete_btn")

        btn_layout_row1.addWidget(self.add_btn)
        btn_layout_row1.addWidget(self.copy_json_btn)
        btn_layout_row1.addWidget(self.copy_text_btn)
        btn_layout_row2.addWidget(self.copy_latest_btn)
        btn_layout_row2.addWidget(self.delete_btn)

        right_layout.addLayout(btn_layout_row1)
        right_layout.addLayout(btn_layout_row2)
        content_layout.addLayout(right_layout, 4)

        main_layout.addLayout(content_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.main_scroll_area.setWidget(self.main_widget_content)

        layout = QVBoxLayout(self)
        layout.addWidget(self.main_scroll_area)
        layout.setContentsMargins(0,0,0,0)

        self.selected_index = None
        self.on_tab_changed(self.tabs.currentIndex()) # 초기 폼 생성
        self.refresh_item_list()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_styles()
        if self.is_dark_mode:
            self.theme_toggle_btn.setText("라이트 모드로 전환")
        else:
            self.theme_toggle_btn.setText("다크 모드로 전환")

    def apply_styles(self):
        dark_stylesheet = """
            QWidget { background-color: #2b2b2b; font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; font-size: 10pt; color: #e0e0e0; }
            QTabWidget::pane { border: 1px solid #505050; border-top-left-radius: 6px; border-top-right-radius: 6px; background-color: #3c3c3c; }
            QTabBar::tab { background: #4a4a4a; border: 1px solid #505050; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; padding: 8px 15px; margin-right: 2px; color: #cccccc; }
            QTabBar::tab:selected { background: #3c3c3c; border-color: #505050; border-bottom-color: #3c3c3c; font-weight: bold; color: #ffffff; }
            QLabel { padding: 2px 0; color: #e0e0e0; }
            QLabel#status_label { font-size: 10pt; font-weight: bold; padding: 5px; color: #28a745; }
            QLineEdit, QTextEdit, QComboBox { background-color: #4a4a4a; border: 1px solid #606060; border-radius: 4px; padding: 6px 8px; color: #ffffff; selection-background-color: #6699ff; }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #88bbee; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left-width: 1px; border-left-color: #606060; border-left-style: solid; border-top-right-radius: 3px; border-bottom-right-radius: 3px; }
            QComboBox::down-arrow { image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAMFBMVEVHcEz///////////////////////////////////////////////////////////9EPuwCAAAAD3RSTlMAAQIDBAUGBwgJCgsMDQ4PEBESgSPQZwAAADFJREFUCNdjYHBgYGBgYhBTAwMDIxMTgwYDEwMDYxMDAyYDJgYGBiYogwYGBgAARkYECvABa/4AAAAASUVORK5CYII=); }
            QPushButton { background-color: #5a8be0; color: white; border: none; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #4a7ad0; }
            QPushButton:pressed { background-color: #3a69c0; }
            QPushButton#delete_btn { background-color: #cc4d4d; }
            QPushButton#delete_btn:hover { background-color: #bb3d3d; }
            QPushButton#delete_btn:pressed { background-color: #aa2d2d; }
            QListWidget { background-color: #3c3c3c; border: 1px solid #505050; border-radius: 4px; padding: 5px; color: #e0e0e0; }
            QListWidget::item { padding: 5px; border-bottom: 1px solid #4a4a4a; }
            QListWidget::item:selected { background-color: #4f6e9f; color: #ffffff; border-radius: 3px; }
            QScrollArea { border: 1px solid #505050; border-radius: 6px; background-color: #3c3c3c; }
            QScrollBar:vertical { border: none; background: #4a4a4a; width: 8px; margin: 0px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #707070; min-height: 20px; border-radius: 4px; }
        """
        light_stylesheet = """
            QWidget { background-color: #f7f9fc; font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; font-size: 10pt; color: #333333; }
            QTabWidget::pane { border: 1px solid #e0e0e0; border-top-left-radius: 6px; border-top-right-radius: 6px; background-color: #ffffff; }
            QTabBar::tab { background: #e0e0e0; border: 1px solid #e0e0e0; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; padding: 8px 15px; margin-right: 2px; color: #555555; }
            QTabBar::tab:selected { background: #ffffff; border-color: #e0e0e0; border-bottom-color: #ffffff; font-weight: bold; color: #333333; }
            QLabel { padding: 2px 0; }
            QLabel#status_label { font-size: 10pt; font-weight: bold; padding: 5px; color: #28a745; }
            QLineEdit, QTextEdit, QComboBox { background-color: #ffffff; border: 1px solid #d0d0d0; border-radius: 4px; padding: 6px 8px; selection-background-color: #a0c4ff; }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #6699ff; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left-width: 1px; border-left-color: #d0d0d0; border-left-style: solid; border-top-right-radius: 3px; border-bottom-right-radius: 3px; }
            QComboBox::down-arrow { image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAMFBMVEVHcEwzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzPdw2a6AAAAD3RSTlMAAQIDBAUGBwgJCgsMDQ4PEBESgSPQZwAAADFJREFUCNdjYHBgYGBgYhBTAwMDIxMTgwYDEwMDYxMDAyYDJgYGBiYogwYGBgAARkYECvABa/4AAAAASUVORK5CYII=); }
            QPushButton { background-color: #6699ff; color: white; border: none; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #5588ee; }
            QPushButton:pressed { background-color: #4477dd; }
            QPushButton#delete_btn { background-color: #dc3545; }
            QPushButton#delete_btn:hover { background-color: #c82333; }
            QPushButton#delete_btn:pressed { background-color: #bb2d3b; }
            QListWidget { background-color: #ffffff; border: 1px solid #d0d0d0; border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 5px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background-color: #e6f0ff; color: #333333; border-radius: 3px; }
            QScrollArea { border: 1px solid #e0e0e0; border-radius: 6px; background-color: #ffffff; }
            QScrollBar:vertical { border: none; background: #f0f0f0; width: 8px; margin: 0px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #c0c0c0; min-height: 20px; border-radius: 4px; }
        """
        self.setStyleSheet(dark_stylesheet if self.is_dark_mode else light_stylesheet)


    def on_tab_changed(self, idx):
        if idx < 0: return # 탭이 없을 경우 방지
        self.current_type = self.tabs.tabText(idx)
        self.type_label.setText(f"현재 타입: {self.current_type}")
        self.build_form()
        self.selected_index = None
        self.item_list.clearSelection()
        self.detail_text.clear()
        self.clear_form_fields()

    def build_form(self):
        """폼 UI를 생성하거나 탭 변경 시 새로고침합니다."""
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        merged = {}
        if self.config:
            merged.update(self.config.get("공통", {}))
            merged.update(self.config.get(self.current_type, {}))

        self.widgets = {}
        for key, data in merged.items():
            if key == "타입": continue
            container = QFrame()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(4)
            label = QLabel(f"{key}:")
            label.setToolTip(data.get("tooltip", ""))
            label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
            container_layout.addWidget(label)
            
            options = data.get("options", [])

            if options:
                # ComboBox for predefined options
                combo = QComboBox()
                combo.addItems(options)
                combo.setToolTip(data.get("tooltip", ""))
                container_layout.addWidget(combo)
                
                # Direct input field
                edit = QLineEdit()
                edit.setPlaceholderText(f"직접 입력 (선택 사항)")
                edit.setToolTip(data.get("tooltip", ""))
                container_layout.addWidget(edit)

                self.widgets[key] = {"combobox": combo, "input": edit}
            else:
                # Only input field
                edit = QLineEdit()
                edit.setPlaceholderText(f"{key} 입력")
                edit.setToolTip(data.get("tooltip", ""))
                container_layout.addWidget(edit)
                self.widgets[key] = {"input": edit}
            
            self.form_layout.addWidget(container)
        self.form_layout.addStretch(1)

    def get_form_data(self):
        """폼에서 현재 입력된 데이터를 가져옵니다."""
        data = {"타입": self.current_type}
        for key, w_dict in self.widgets.items():
            # 직접 입력 필드가 존재하고, 그곳에 값이 있다면 우선적으로 사용
            if "input" in w_dict:
                val = w_dict["input"].text().strip()
                if val:
                    data[key] = val
                    continue  # 직접 입력 값을 사용했으므로 다음 키로 넘어감

            # 직접 입력 값이 없을 경우, 콤보박스 값 사용
            if "combobox" in w_dict:
                val = w_dict["combobox"].currentText().strip()
                if val:
                    data[key] = val
        return data

    def fill_form(self, item):
        """선택된 아이템의 데이터로 폼을 채웁니다."""
        # 아이템 타입에 맞는 탭으로 먼저 전환
        if item.get("타입") != self.current_type:
            try:
                tab_names = [self.tabs.tabText(i) for i in range(self.tabs.count())]
                idx = tab_names.index(item.get("타입"))
                self.tabs.setCurrentIndex(idx)
                QApplication.processEvents()
            except (ValueError, IndexError):
                return

        for key, w_dict in self.widgets.items():
            val = item.get(key, "")
            val_str = str(val)

            # 콤보박스와 입력 필드가 모두 있는 경우
            if "combobox" in w_dict and "input" in w_dict:
                combo = w_dict["combobox"]
                edit = w_dict["input"]
                
                index = combo.findText(val_str)
                if index != -1:
                    combo.setCurrentIndex(index)
                    edit.clear()
                else:
                    edit.setText(val_str)
                    combo.setCurrentIndex(-1) # 콤보박스 선택 해제
            
            # 입력 필드만 있는 경우
            elif "input" in w_dict:
                w_dict["input"].setText(val_str)

    def add_item(self):
        data = self.get_form_data()
        name = data.get("이름", "")
        if not name:
            QMessageBox.warning(self, "경고", "이름은 필수 입력 항목입니다.")
            return

        existing_index = None
        for i, item in enumerate(self.items):
            if item.get("이름") == name and item.get("타입") == self.current_type:
                existing_index = i
                break

        if self.selected_index is not None:
            self.items[self.selected_index] = data
            self.status_message("아이템 수정 완료")
        elif existing_index is not None:
            reply = QMessageBox.question(self, "확인", f"'{name}' ({self.current_type}) 아이템이 이미 존재합니다. 수정하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.items[existing_index] = data
                self.status_message("아이템 수정 완료")
            else: return
        else:
            self.items.append(data)
            self.status_message("아이템 추가 완료")

        self.save_items()
        self.refresh_item_list()
        self.clear_form_fields()
        self.selected_index = None

    def refresh_item_list(self):
        self.item_list.clear()
        current_selection = self.selected_index
        for i, item in enumerate(self.items):
            display = f"{item.get('이름','(이름 없음)')} [{item.get('타입','?')}]"
            list_item = QListWidgetItem(display)
            self.item_list.addItem(list_item)
        if current_selection is not None and current_selection < self.item_list.count():
            self.item_list.setCurrentRow(current_selection)

    def clear_form_fields(self):
        for w_dict in self.widgets.values():
            if "input" in w_dict:
                w_dict["input"].clear()
            if "combobox" in w_dict:
                w_dict["combobox"].setCurrentIndex(0)
        self.selected_index = None
        self.item_list.clearSelection()
        self.detail_text.clear()

    def on_item_selected(self, list_item: QListWidgetItem):
        idx = self.item_list.row(list_item)
        self.selected_index = idx
        data = self.items[idx]
        self.fill_form(data)
        lines = [f"<b>{k}</b>: {', '.join(v) if isinstance(v, list) else v}" for k, v in data.items() if k != "타입"]
        self.detail_text.setHtml("<br>".join(lines))

    def delete_selected_item(self):
        if self.selected_index is None:
            QMessageBox.information(self, "정보", "삭제할 아이템을 선택하세요.")
            return
        item_name = self.items[self.selected_index].get("이름", "(이름 없음)")
        reply = QMessageBox.question(self, "확인", f"정말로 '{item_name}' 아이템을 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.items[self.selected_index]
            self.save_items()
            self.selected_index = None
            self.refresh_item_list()
            self.clear_form_fields()
            self.status_message("아이템 삭제 완료")

    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)

    def copy_selected_item_json(self):
        if self.selected_index is None: return
        item = self.items[self.selected_index]
        self.copy_to_clipboard(json.dumps(item, ensure_ascii=False, indent=2))
        self.status_message("선택 아이템 JSON 복사 완료")

    def copy_selected_item_text(self):
        if self.selected_index is None: return
        item = self.items[self.selected_index]
        lines = [f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in item.items() if k != "타입"]
        self.copy_to_clipboard("\n".join(lines))
        self.status_message("선택 아이템 일반 텍스트 복사 완료")

    def copy_latest_item(self):
        if not self.items: return
        self.copy_to_clipboard(json.dumps(self.items[-1], ensure_ascii=False, indent=2))
        self.status_message("최근 생성 아이템 JSON 복사 완료")

    def status_message(self, msg, timeout=3000):
        self.status_label.setText(msg)
        QTimer.singleShot(timeout, self.status_label.clear)

def main():
    app = QApplication(sys.argv)
    editor = ItemEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
