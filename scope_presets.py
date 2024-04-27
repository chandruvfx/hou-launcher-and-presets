import sys
import os 
import json
from PySide2.QtUiTools import QUiLoader
from PySide2 import (QtWidgets,
                     QtGui)
from PySide2.QtCore import Qt
from PySide2.QtGui import QPixmap

class ScopePresets(QtWidgets.QMainWindow):
    
    def __init__(self, 
                 parent=None) -> None:
         
        super().__init__(parent)

        self.houdini_launcher = parent
        
        dirname = os.path.dirname(__file__)
        ui_file = os.path.join(dirname, 
                               "ui\pfx_scope_preset.ui"
        )
        ui_loader = QUiLoader()
        self.scope_preset_window = ui_loader.load(ui_file)
        
        self.current_selected_scope = set()
        self.scope_list = self.scope_preset_window.findChild(
            QtWidgets.QListView,
            "scope_list_listview"
        )
        self.scope_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        self.model = QtGui.QStandardItemModel()
        
        self.add_scope_button = self.scope_preset_window.findChild(
            QtWidgets.QPushButton,
            "add_button"
        )
        self.add_scope_button.clicked.connect(self.add_scope)
        
        self.remove_scope_button = self.scope_preset_window.findChild(
            QtWidgets.QPushButton,
            "remove_button"
        )
        self.remove_scope_button.clicked.connect(self.remove_scope)
        
        self.preset_folder_path = os.environ['SCOPE_PRESET_PATH']
        
        self.make_folders(self.preset_folder_path)
        self.collect_presets()
        
    @staticmethod
    def make_folders(folder_path):
        
        try:
            os.makedirs(folder_path)
        except FileExistsError:
            pass
    
    def collect_presets(self) -> None:
        
        presets = os.listdir(self.preset_folder_path)
        if presets:
            for preset in presets:
                item = QtGui.QStandardItem(preset)
                self.model.appendRow(item)
            self.scope_list.setModel(self.model)
        
          
    def add_scope(self):
        
        proceed_adding_scope = True
        if self.scope_list.model():
            if self.scope_list.model().rowCount() >= int(os.environ['SCOPE_PRESET_COUNT']):
                proceed_adding_scope = False 
        
        if proceed_adding_scope:
            show = self.houdini_launcher.show_combo_box.currentText()
            sequence = self.houdini_launcher.sequence_combo_box.currentText()
            shot = self.houdini_launcher.shot_combo_box.currentText()
            task = self.houdini_launcher.task_combo_box.currentText()
            all_radio_btn_status = self.houdini_launcher.all_radio_btn.isChecked()
            user_radio_btn_status = self.houdini_launcher.user_radio_btn.isChecked()
            
            if all([show,
                sequence,
                shot,
                task]):

                scope_label_text, status = QtWidgets.QInputDialog.getText(
                        self, 'scope preset', 'Enter Scope Label name:')
                
                if scope_label_text and status:
                    item = QtGui.QStandardItem(scope_label_text)
                    self.model.appendRow(item)
                    self.scope_list.setModel(self.model)
                

                preset_file_path = os.path.join(
                    self.preset_folder_path, scope_label_text
                )
                
                preset_dict = {
                    'show': show,
                    'sequence': sequence,
                    'shot': shot,
                    'task': task,
                    'all_radio_btn': all_radio_btn_status,
                    'user_radio_btn': user_radio_btn_status
                }
                with open(preset_file_path, "w") as preset_file:
                    json.dump( preset_dict, preset_file, indent=4)
            
            else:
                QtWidgets.QMessageBox.information(self, "Scope Preset",
                                                "Show, Sequence, Shot, Task in PFX Houdini Launcher were Required to be Filled!!")
        else:
            QtWidgets.QMessageBox.warning(self, "Scope Preset", f"Only {os.environ['SCOPE_PRESET_COUNT']} Preset Entries Allowed. Maximum Limit Reached!!")
        
    def remove_scope(self) -> None:
        
        row = self.scope_list.selectionModel().selectedIndexes()[0].row()
        selected_preset = self.scope_list.model().index(row, 0).data()
        
        preset_file_path = os.path.join(
            self.preset_folder_path, selected_preset
        )
        if preset_file_path:
            os.remove(preset_file_path)
            
        self.scope_list.model().removeRow(row)
    


if __name__ == "__main__":
    
    app = QtWidgets.QApplication(sys.argv)
    pfx_houdini_launcer = ScopePresets()
    pfx_houdini_launcer.scope_preset_window.show()
    app.exec_()