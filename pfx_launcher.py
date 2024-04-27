
import os
import sys 
import requests
import yaml
import json
import subprocess
from shutil import which
from PySide2.QtUiTools import QUiLoader
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtGui import QPixmap
from thadam_base import thadam_api
from thadam_base import logger

class PfxHoudiniLauncher(QtWidgets.QMainWindow):
    
    """An Standalone GUI Houdini Launcher get show, seq, shot
    task information and launch the houdini in the user specified
    context.
    
    The launcher splitted into two sections. One section of functionality
    collects all the user assigned thadam entity schemas and another 
    section collects all the thadam entitties.
    
    Based upon the user selection operation, The GUI communicate to the 
    thadam api to get projects, seq, shot and tasks. 
    """
    def __init__(self) -> None:
        
        """ Initializing the GUI elements of widgets and functionality
        
        GUI QT widgets UI file, QT Widget signal functionalitiese setter up. 
        User assigned task entities queried and loaded up as a default 
        selection for the user. 
        """
        
        super().__init__()
        
        self.user_name = os.environ['USERNAME']
        self.launcher_preset = os.path.join(os.environ['TEMP'], "launcher_preset.json")
        
        # Sub task path
        self.root_subtask_path =  os.environ['SUB_TASK_DIR']
        self.pfx_logger = logger.PFXLogger("houdini_logs.log")
        
        #Sub task List 
        self.subtasks = []
        
        dirname = os.path.dirname(__file__)
        ui_file = os.path.join(dirname, 
                               "ui\pfx_houdini_shot_launcher.ui"
        )
        ui_loader = QUiLoader()
        self.launcher_window = ui_loader.load(ui_file)
        self.pfx_logger.info_logger("PFX GUI Loading")

        self.thadam_api_server = thadam_api.ThadamParser()
        self.thadam_user_api_server = thadam_api.ThadamUserParser()
        self.pfx_logger.info_logger(f"Running From API {thadam_api.ThadamRestServer().api}")
        self.pfx_logger.info_logger("Initializing thadam parser")
        
        self.pfx_logger.info_logger("Collecting User Assigned Entities...")
        self.user_info = \
                self.thadam_user_api_server.get_artist_details(
                    artist_name=os.environ['USERNAME']
                )
        self.pfx_logger.info_logger(self.user_info)
        
        self.user_assigned_entities = \
            self.thadam_user_api_server.get_artist_assigned_item_details(
                        artist_id=self.user_info['id']
            )
        self.pfx_logger.info_logger("Collected User Assigned Entities")
        self.pfx_logger.info_logger(
            json.dumps(self.user_assigned_entities, indent=4)
        )
        
        self.show_combo_box = self.launcher_window.findChild(
            QtWidgets.QComboBox,
            "show_list_combobox"
        )
        self.sequence_combo_box = self.launcher_window.findChild(
            QtWidgets.QComboBox,
            "sequence_list_combobox"
        )
        self.shot_combo_box = self.launcher_window.findChild(
            QtWidgets.QComboBox,
            "shot_list_combobox"
        )
        self.task_combo_box = self.launcher_window.findChild(
            QtWidgets.QComboBox,
            "task_list_combobox"
        )
        self.show_info_plaintextedit = self.launcher_window.findChild(
            QtWidgets.QPlainTextEdit,
            "show_info_textedit"
        )
        self.launch_houdini_button = self.launcher_window.findChild(
            QtWidgets.QPushButton,
            "launch_houdini_button"
        )
        
        self.all_radio_btn = self.launcher_window.findChild(
            QtWidgets.QRadioButton,
            "all_radio_btn"
        )
           
        self.user_radio_btn = self.launcher_window.findChild(
            QtWidgets.QRadioButton,
            "user_radio_btn"
        )
        
        self.presets_button = self.launcher_window.findChild(
            QtWidgets.QPushButton,
            "presets_button"
        )
        
        self.template_chkbox = self.launcher_window.findChild(
            QtWidgets.QCheckBox,
            "template_chkbox"
        )
        
        self.master_icon = self.launcher_window.findChild(
            QtWidgets.QLabel,
            "icon"
        )
        # Signals triggered if the radio button is changed
        self.user_radio_btn.toggled.connect(self.set_projects)
        self.all_radio_btn.toggled.connect(self.set_projects)
        
        self.user_radio_btn.setChecked(True)
        
        # Resized the dropdown the QlistView of the QComboBox
        # to certain size. AS so the horizontal text gonna fit well
        project_combobox_list_view_width = self.sequence_combo_box.view().width()
        project_combobox_list_view_height = self.sequence_combo_box.view().height()
        self.sequence_combo_box.view().setFixedSize(
                        project_combobox_list_view_width + 100,
                        project_combobox_list_view_height
        )
        
        # Initialize the text auto completer for the QComboBox widgets 
        # When a partial words typed the comobobox filter the best match 
        # upshow to the user for suggested selection
        self.configure_widget_text_completer(self.show_combo_box, "Select Show..")
        self.configure_widget_text_completer(self.sequence_combo_box, "Select Sequence..")
        self.configure_widget_text_completer(self.shot_combo_box, "Select Shot..")
        self.configure_widget_text_completer(self.task_combo_box, "Select Task..")
        
        self.launch_houdini_button.clicked.connect(self.launch_houdini)
        
        # Load sequence and the project info from the thadam server 
        # once the show is clicked 
        self.show_combo_box.activated[str].connect(self.set_sequence)
        self.show_combo_box.activated[str].connect(self.set_project_info)
        
        # Show and Seq entries passed to signal method 
        # once the sequence is selected 
        seq_args = lambda: self.set_shot(self.show_combo_box.currentText(), 
                                          self.sequence_combo_box.currentText()
        )
        self.sequence_combo_box.activated[str].connect(seq_args)
        
        # Preserve the cursor positions for frame range
        self.frame_range_text_edit_last_cursor_positions = []
        
        # Preserve the cursor positions for sub task
        self.sub_task_text_edit_last_cursor_positions = []
        
        # Task selection signals to the sub task module
        self.task_combo_box.activated[str].connect(self.sub_task)
        
        tool_icon = os.path.join(dirname, "icons/satellite.png")
        tool_pixmap = QPixmap(tool_icon)
        self.master_icon.setPixmap(tool_pixmap.scaled(60,60, Qt.KeepAspectRatio))
        
        self.presets_button.clicked.connect(self.launch_preset_gui)
        if os.path.exists(self.launcher_preset):
            self.apply_values_to_launcher_fields(self.launcher_preset)
        
        
    def show_warning_gui(self, 
                     message: str) -> None:
        
        """General Message Box to show warnings

        Args:
            message (str): warning message to show
        """
        QtWidgets.QMessageBox.warning(self, 
                                    'Warning',
                                    message
        )

    def show_msg_box(self,
                     message: str) -> None:
        
        """General Message Box to show information
        
        Args:
            message (str): information message to show
        """
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("PFX Houdini")
        msg.setText(message)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.show()
    
    @staticmethod
    def configure_widget_text_completer(widget,
                                   place_holder_text: str) -> None:
        
        """Bring the matching pattern drop down text to the
        user suggestion if the user typed partial words exist 
        in the the combobox list 
        
        Args:
            place_holder_text (str): User typed text 
        """
        widget.lineEdit().setPlaceholderText(place_holder_text)
        widget.completer().setCompletionMode(
            QtWidgets.QCompleter.PopupCompletion
        )
        widget.setCurrentIndex(-1)  
    
    def thadam_entity_exist(self,
                            widgets : QtWidgets,
                            thadam_entities: list,
                            selected_entity: str,
                            warning: str='') -> None:
        """Method checks whether the user entered words
        exist in the dropdown item. If not exist throw
        Warning QT message box exceptions.
        
        If the passed QT widget item matches with the 
        predefined object name then it perform those section
        operations. 
        
        Example:
            If the Show typed entry made by the user is wrong
        then all the dependent widget show, seq, shot and task 
        text cleared 

        Args:
            widgets (QtWidgets): The Qtwidget Object 
            thadam_entities (list): List of collection gathered from the 
                                    respective entities
            selected_entity (str): Selected entity from dropdown
            warning (str, optional): Respective warning message. Defaults to ''.
        """
        
        # Iterate through the catched entities and if the list 
        # contains the user typed entity then make the enity_exist status true
        # nothing proceed.
        entity_exist = False
        if selected_entity:
            for entities in thadam_entities:
                for _, entity_name in entities.items():
                    if selected_entity == entity_name:
                        entity_exist = True
                        
            # IF the entered entity is not exist in the entity list then 
            # the warning message showed from where the user 
            # performing operations from 
            if not entity_exist:
                self.show_warning_gui(warning)
                self.pfx_logger.error_logger(warning) 
                if widgets.objectName() == "show_list_combobox":
                    self.pfx_logger.error_logger(
                            f"Entered Show \"{self.show_combo_box.currentText()}\" Does not Exist.Clearing all"
                    ) 
                    self.show_info_plaintextedit.clear()
                    self.show_combo_box.lineEdit().clear()
                    self.sequence_combo_box.lineEdit().clear()
                    self.shot_combo_box.lineEdit().clear()
                    self.task_combo_box.lineEdit().clear()
                    
                    
                if widgets.objectName() == "sequence_list_combobox":
                    logger_msg  = f"Entered Sequence \"{self.sequence_combo_box.currentText()}\""
                    logger_msg  += "Does not Exist. Clearing sequence, shot and task"
                    
                    self.pfx_logger.error_logger(
                        logger_msg
                    )
                    self.sequence_combo_box.lineEdit().clear()
                    self.shot_combo_box.lineEdit().clear()
                    self.task_combo_box.lineEdit().clear()
                     
                    
                if widgets.objectName() == "shot_list_combobox":
                    
                    self.pfx_logger.error_logger(
                        f"Entered Shot \"{self.shot_combo_box.currentText()}\" Does not Exist. Clearing shot and task"
                    ) 
                    self.shot_combo_box.lineEdit().clear()
                    self.task_combo_box.lineEdit().clear()
                    
                    
                if widgets.objectName() == "task_list_combobox":
                    
                    self.pfx_logger.error_logger(
                                f"Entered Task \"{self.task_combo_box.currentText()}\" Does not Exist. Clearing task"
                    ) 
                    self.task_combo_box.lineEdit().clear()
                    


    def set_project_info(self, project_name: str) -> None:
        
        """Project level configuration files pulled from the 
        config directory. a project name determined by the passing value
        argument.
        
        If the config file not exist it throw errors. 
        All the config entries loaded as attrbutes as part of the class
        
        Args:
            project_name (str): Name of the project to pull the settings.yml
                                file from 
        """
        self.show_info_plaintextedit.clear()
        self.project_infos = self.thadam_api_server.get_project_infos(project_name)
        for project_infos in self.project_infos:
            for title, value in project_infos.items():
                self.show_info_plaintextedit.appendPlainText(title +" : " + str(value))
        
        custom_env_path = r'%s\%s\settings.yml' \
                                            %(os.environ['HOUDINI_SHOW_SETTINGS'],
                                              self.show_combo_box.currentText()
                                            )                      
        if not os.path.exists(custom_env_path):
            
            self.show_msg_box("Project Settings Not Configured!!..")
            self.sequence_combo_box.clear()
            self.pfx_logger.error_logger(
                        f"{custom_env_path} not exist!!.. Lead and Supervisor Call!!"
            ) 

        else:                                               
            with open(custom_env_path, 'r') as cus_env_file:
                self.custom_env_file = yaml.safe_load(cus_env_file)
            self.pfx_logger.info_logger(f"{custom_env_path} loaded!!")
            
            for title, value in self.custom_env_file.items():
                self.show_info_plaintextedit.appendPlainText(title +" : " + str(value))
                self.pfx_logger.info_logger(
                        f"Info Text edit class updated with {title} = {str(value)} loaded!!"
                )
    
    def preserve_text_edit_cursor_position(self,
                                           preserve_list: list) -> None:
        
        """Records the last text position in the QLineEdit widget in a list.
        ONce the entry made in the list. THe anchor postion take that value
        as a new value for all the subsequent upcoming changes. Cursor Position
        always this value to update the texts
        
        Used for Showcasing frame range and sub task entry. 
        
        Args:
            preserve_list(str): List that store the initial value of anchor point
        """
        
        if not preserve_list:
            self.text_edit_last_cursor_position = self.show_info_plaintextedit.textCursor()
            preserve_list.append(
                self.text_edit_last_cursor_position.position()
            )

        self.text_edit_last_cursor_position.setPosition(
            preserve_list[0], 
            self.text_edit_last_cursor_position.KeepAnchor
        )
        self.show_info_plaintextedit.setTextCursor(
            self.text_edit_last_cursor_position
        )

    def set_projects(self) -> None:
        
        """Intially clear all the comboboxes and the 
        index is -1. Loads all the projects collects from the 
        thadam entities 
        """
        self.show_info_plaintextedit.clear()
        self.show_combo_box.clear()
        self.sequence_combo_box.clear()
        self.shot_combo_box.clear()
        self.task_combo_box.clear()
        
        if self.all_radio_btn.isChecked():
            self.projects = self.thadam_api_server.get_projects()
            self.projects = sorted(self.projects, key=lambda d: d['proj_code'])
            
            
        if self.user_radio_btn.isChecked():
            self.projects= []
            for project in list(self.user_assigned_entities):
                project_dict = {}
                project_dict['proj_code'] =  project
                if project_dict not in self.projects:
                    self.projects.append(project_dict)

        for project in self.projects:
            self.show_combo_box.addItem(project['proj_code'])
        
        self.show_combo_box.setCurrentIndex(-1) 
        
        self.show_combo_box.lineEdit().editingFinished.connect(
            lambda : self.thadam_entity_exist(self.show_combo_box,
                                              self.projects, 
                                              self.show_combo_box.currentText(),
                                              warning="Entered Project Does Not Exist!!",
            )
        )
        
    def set_sequence(self, 
                     project_name:str
        )-> None:

        """ Load all the sequences of the given project
        From the thadam entity
        
        Args:
            project_name (str): User selected project name
        """
        
        sequences = set()
        self.sequence_combo_box.clear()
        self.shot_combo_box.clear()
        self.task_combo_box.clear()
        
        if self.all_radio_btn.isChecked():
            self.get_sequences = self.thadam_api_server.get_sequences(project_name)
            
        if self.user_radio_btn.isChecked():
            self.get_sequences = []
            for sequence in self.user_assigned_entities[project_name]:
                sequence_dict = {}
                sequence_dict['seq_name'] =  list(sequence.keys())[0]
                if sequence_dict not in self.get_sequences:
                    self.get_sequences.append(sequence_dict)

        for sequence in self.get_sequences:
            sequences.add(sequence['seq_name'])
        
        for sequence in sorted(sequences):
            self.sequence_combo_box.addItem(sequence)
        
        self.sequence_combo_box.setCurrentIndex(-1)
        self.sequence_combo_box.lineEdit().editingFinished.connect(
            lambda : self.thadam_entity_exist(self.sequence_combo_box,
                                              self.get_sequences, 
                                              self.sequence_combo_box.currentText(),
                                              warning="Entered Sequence Does Not Exist!!",
            )
        )
        
     
    def set_shot(self, 
                 project_name: str,
                 seq_name: str) -> None:
        
        """Loads all the shots for the given project and sequence
        name
        
        Args:
            project_name (str): User selected project name
            seq_name (str): User selected seq name
        """
        
        self.shot_combo_box.clear()
        self.task_combo_box.clear()
        
        if self.all_radio_btn.isChecked():
            self.shots = self.thadam_api_server.get_shots(project_name,
                                                    seq_name
            )
            self.shots = sorted(self.shots, key=lambda d: d['shot_name'])
            
        if self.user_radio_btn.isChecked():
            self.shots = []
            for sequences in self.user_assigned_entities[project_name]:
                try:
                    for shots in sequences[seq_name]:
                        shot_dict = {}
                        shot_dict['shot_name'] =  shots
                        if shot_dict not in self.shots:
                            self.shots.append(shot_dict)
                except KeyError: pass
                
        for shot in self.shots:
            self.shot_combo_box.addItem(shot['shot_name'])
        
        self.preserve_text_edit_cursor_position(
                    self.frame_range_text_edit_last_cursor_positions
        )
        self.show_info_plaintextedit.insertPlainText(" ")
        
        self.shot_combo_box.setCurrentIndex(-1)
        self.shot_combo_box.activated[str].connect(self.set_task)
        self.shot_combo_box.lineEdit().editingFinished.connect(
            lambda : self.thadam_entity_exist(self.shot_combo_box,
                                              self.shots, 
                                              self.shot_combo_box.currentText(),
                                              warning="Entered Shot Does Not Exist!!",
            )
        )
    
    def set_task(self) -> None:
        
        """Load all the task from thadam server by passing 
        project name, show id, sequence id
        """
        self.task_combo_box.clear()
        
        tasks = set()
        get_selected_project_name = self.show_combo_box.currentText()
        get_selected_sequence = self.sequence_combo_box.currentText()
        get_selected_shot = self.shot_combo_box.currentText()
        
        if self.all_radio_btn.isChecked():
            for project in self.projects:
                if project['proj_code'] == get_selected_project_name:
                    get_selected_show_id = project['proj_id']
            
            for shots in self.shots:
                if shots['shot_name'] == get_selected_shot:
                    get_selected_shot_id = shots['scope_id']

            self.task_types = self.thadam_api_server.get_tasks(
                                                        get_selected_project_name,
                                                        get_selected_show_id,
                                                        get_selected_shot_id
            )
        if self.user_radio_btn.isChecked():
            
            get_selected_shot = self.shot_combo_box.currentText()
            self.task_types = []
            for sequences in self.user_assigned_entities[get_selected_project_name]:
                try:
                    for shots in sequences[get_selected_sequence]:
                        if shots == get_selected_shot:
                            for task in sequences[get_selected_sequence][shots]:
                                task_dict = {}
                                task_dict['type_name'] =  task
                                if task_dict not in self.task_types:
                                    self.task_types.append(task_dict)
                except: pass          
        
        self.preserve_text_edit_cursor_position(self.frame_range_text_edit_last_cursor_positions)

        # If shots have the frame range then it given priority
        # the frame ranfe property updated with this else it 
        # take from the task
        for shot in self.shots:
            if 'shot_name' in shot:
                if shot['shot_name'] == self.shot_combo_box.currentText():
                    if 'frame_range' in shot:
                        if shot['frame_range']:
                            self.frame_range = shot['frame_range']
                            self.show_info_plaintextedit.insertPlainText(
                                "\nframe_range : " + self.frame_range
                            )
                        else:
                            self.frame_range = '1001-1200'
                            self.show_info_plaintextedit.insertPlainText(
                                "\nframe_range [launcher] : " + self.frame_range
                            )
        # If the shot dont have frame range and taske has
        # the it given priority         
        for task_types in self.task_types:
            if task_types['type_name']:
                if '-' in task_types['type_name']:
                    self.frame_range = task_types['type_name']
                    self.show_info_plaintextedit.insertPlainText(
                        "\nframe_range : " + self.frame_range
                    )
                elif not task_types['type_name']:
                    self.frame_range = '1001-1200' 
                    self.show_info_plaintextedit.insertPlainText(
                        "\nframe_range [launcher] : " + self.frame_range
                    )
                else:
                    tasks.add(task_types['type_name'])
            else:
                self.frame_range = '1001-1200'
                self.show_info_plaintextedit.insertPlainText(
                        "\nframe_range : " + self.frame_range
                    )
                
        for task_types in sorted(tasks):
            self.task_combo_box.addItem(task_types)
        self.task_combo_box.setCurrentIndex(-1)
        self.task_combo_box.lineEdit().editingFinished.connect(
            lambda : self.thadam_entity_exist(self.task_combo_box,
                                              self.task_types, 
                                              self.task_combo_box.currentText(),
                                              warning="Entered Task Does Not Exist!!",
            )
        )
        self.show_info_plaintextedit.insertPlainText(" ")

    def sub_task_file_path(self) -> None:
        
        """ Return the path of the subtask file path"""
        
        return os.path.join(
            self.root_subtask_path,
            self.show_combo_box.currentText(),
            self.sequence_combo_box.currentText(),
            self.shot_combo_box.currentText(),
            self.task_combo_box.currentText(),
            "subtasks.json"
        )
        
    def sub_task(self) -> None:
        
        """
        Gather all the sub tasks and show cases in the text info
        """
        subtask_file = self.sub_task_file_path()
        
        if os.path.exists(subtask_file):
            with open(subtask_file, "r") as subtaskfile:
                self.subtasks = json.load(subtaskfile)

            self.preserve_text_edit_cursor_position(
                        self.sub_task_text_edit_last_cursor_positions
            )
            self.show_info_plaintextedit.insertPlainText(" ")
            self.show_info_plaintextedit.insertPlainText(
                            "\nsub_tasks : " + ",".join(self.subtasks)
            )
        else:
            self.preserve_text_edit_cursor_position(
                        self.sub_task_text_edit_last_cursor_positions
            )
            self.show_info_plaintextedit.insertPlainText(" ")

    def generate_houdini_environment_variables(self) -> None:
        
        """ Generate all the environment variables to ingest 
        while opening houdini"""
        
        os.environ['PFXSHOW'] = self.show_combo_box.currentText()
        self.pfx_logger.info_logger(f"Project Setted \"{os.environ['PFXSHOW']}\"")
        
        os.environ['PFXPRDSTEP'] = self.sequence_combo_box.currentText().split('/')[0]
        self.pfx_logger.info_logger(f"Production Step Setted \"{os.environ['PFXPRDSTEP']}\"")
        
        os.environ['PFXSEQ'] = self.sequence_combo_box.currentText().split('/')[-1]
        self.pfx_logger.info_logger(f"Sequence Setted \"{os.environ['PFXSEQ']}\"")
        
        os.environ['PFXSHOT'] = self.shot_combo_box.currentText()
        self.pfx_logger.info_logger(f"Shot Setted \"{os.environ['PFXSHOT']}\"")
        
        os.environ['PFXTASK'] = self.task_combo_box.currentText()
        self.pfx_logger.info_logger(f"Shot Setted \"{os.environ['PFXTASK']}\"")
        
        # Frame range environment variable created if available
        if hasattr(self,'frame_range'):
            os.environ['PFXFRAME_RANGE'] = self.frame_range
            self.pfx_logger.info_logger(f"Frame Range Setted \"{os.environ['PFXFRAME_RANGE']}\"")
        else:
            self.pfx_logger.error_logger(f"No Frame range setted. Production Call!!")
        
        # Sub Tasks Created if existed 
        if hasattr(self,'subtasks'):
            os.environ['PFXSUBTASKS'] = ",".join(self.subtasks)
            self.pfx_logger.info_logger(f"Retrived Subtasks \"{os.environ['PFXSUBTASKS']}\"")
        else:
            self.pfx_logger.error_logger(f"No Subtasks Setted. Lead or Sup Call!!")
            
            
        for project_infos in self.project_infos:
            for title, value in project_infos.items():
                os.environ[f'PFX{title.upper()}'] = str(value)
                self.pfx_logger.info_logger(f'PFX{title.upper()} = {str(value)}')
                
        for title, value in self.custom_env_file.items():
            
            os.environ[f'PFX{title.upper()}'] = str(value)
            self.pfx_logger.info_logger(f'PFX{title.upper()} = {str(value)}')
            
        # Fx publish dir path 
        os.environ[f'PFXFX_PUBLISH_DIR'] = os.environ['FX_PUBLISH_DB_DIR']
        self.pfx_logger.info_logger(f"fx publish dir setted to \"{os.environ[f'PFXFX_PUBLISH_DIR']}\"")
        
        os.environ['JOB'] = os.environ['PFXPROJECT_PATH'] + '/' + \
                os.environ['PFXSHOW'] + '/' + \
                os.environ['PFXSEQ']  + '/' + \
                os.environ['PFXSHOT'] + '/' + \
                os.environ['PFXTASK'] + '/' + \
                self.user_name   
        self.pfx_logger.info_logger(f"JOB = \"{os.environ['JOB']}\"")
        
        houdini_internal_pkg_dir = ''
        for houdini_internal_pkg_dirs in os.environ['HOUDINI_INTERNAL_PACKAGE_DIR'].split(';'):
            if os.environ['PFXHOUDINI_VERSION'] not in houdini_internal_pkg_dirs: 
                houdini_internal_pkg_dir += \
                    houdini_internal_pkg_dirs + os.sep + os.environ['PFXHOUDINI_VERSION'] + ';'
  
        if houdini_internal_pkg_dir not in os.environ['HOUDINI_PACKAGE_DIR']:
            os.environ['HOUDINI_PACKAGE_DIR'] +=  os.pathsep + houdini_internal_pkg_dir
        self.pfx_logger.info_logger(f"HOUDINI_PACKAGE_DIR = \"{os.environ['HOUDINI_PACKAGE_DIR']}\"")
         
        os.environ['HOUDINI_BIN_PATH'] = \
            fr"C:\Program Files\Side Effects Software\Houdini {os.environ['PFXHOUDINI_VERSION']}\bin\houdini.exe"
        self.pfx_logger.info_logger(f"Houdini exe path = \"{os.environ['HOUDINI_BIN_PATH']}\"")
        
    def create_folders(self) -> None:
        
        """ Create all the necessary folders for the given job path"""
        
        folders = ['geo',
                 'hda',
                 'sim',
                 'abc',
                 'tex',
                 'render',
                 'flip',
                 'temp'
                 ]
        
        if not os.path.exists(os.environ['JOB']):
            self.pfx_logger.info_logger(f"Creating {os.environ['JOB']} folders")
            os.makedirs(os.environ['JOB']) 
        
        for folder in folders:
            folder_path = os.path.join(
                    os.environ['JOB'], folder
            )
            if not os.path.exists(folder_path): 
                self.pfx_logger.info_logger(f"Not {folder_path} Exist!!.. Creating..") 
                os.makedirs(folder_path) 
    
    def launch_preset_gui(self) -> None:
        
        import scope_presets
        from imp import reload
        reload(scope_presets)
        self.sp = scope_presets.ScopePresets(self)
        self.sp.scope_preset_window.show()
        
        
        def apply_user_selected_scope_item():
            
            row = self.sp.scope_list.selectionModel().selectedIndexes()[0].row()
            selected_preset = self.sp.scope_list.model().index(row, 0).data()
            
            preset_file_path = os.path.join(
                os.environ['SCOPE_PRESET_PATH'], selected_preset
            )
            
            self.apply_values_to_launcher_fields(preset_file_path)
                
        try:    
            self.sp.scope_list.clicked.connect(
                        apply_user_selected_scope_item
            )
        except AttributeError: pass
        
    def apply_values_to_launcher_fields(self,
                                        preset_file_path: str) -> None:
        
        with open(preset_file_path, "r") as preset_file:
                preset_data = json.load(preset_file)
            
        show = preset_data['show']
        sequence = preset_data['sequence']
        shot = preset_data['shot']
        task = preset_data['task']
        all_radio_btn_status = preset_data['all_radio_btn']
        user_radio_btn_status = preset_data['user_radio_btn']
        
        if all_radio_btn_status:
            self.all_radio_btn.setChecked(True)
        elif user_radio_btn_status:
            self.user_radio_btn.setChecked(True)
        
        proceed_other_entries = [True for projects in self.projects if show == projects['proj_code']]
        
        if proceed_other_entries:      
            show_index = self.show_combo_box.findText(show)
            self.show_combo_box.setCurrentIndex(show_index)
            self.set_sequence(show)
            self.set_project_info(show)
            
            seq_index = self.sequence_combo_box.findText(sequence)
            self.sequence_combo_box.setCurrentIndex(seq_index)
            self.set_shot(show, sequence)
            
            shot_index = self.shot_combo_box.findText(shot)
            self.shot_combo_box.setCurrentIndex(shot_index)
            self.set_task()
            
            task_index = self.task_combo_box.findText(task)
            self.task_combo_box.setCurrentIndex(task_index)
            self.sub_task()
            
        else:
            self.show_combo_box.setCurrentIndex(-1)
            self.sequence_combo_box.setCurrentIndex(-1)
            self.shot_combo_box.setCurrentIndex(-1)
            self.task_combo_box.setCurrentIndex(-1)
            self.show_info_plaintextedit.clear()
            QtWidgets.QMessageBox.information(self, 
                                                "PFX Houdini Launcher",
                                            "The Project Does Not Exist or Not Assigned !!")
                
    def register_last_selected_entries(self) -> None:
        
        preset_dict = {
                'show': self.show_combo_box.currentText(),
                'sequence': self.sequence_combo_box.currentText(),
                'shot': self.shot_combo_box.currentText(),
                'task': self.task_combo_box.currentText(),
                'all_radio_btn': self.all_radio_btn.isChecked(),
                'user_radio_btn': self.user_radio_btn.isChecked()
            }
        
        with open(self.launcher_preset, "w") as preset_file:
            json.dump( preset_dict, preset_file, indent=4)
        
          
    def launch_houdini(self) -> None:
        
        """Launch houdini from the bin path with all the ingested 
        environment variable
        
        Check if all the fields in the pfx launcher selected
        If done then then launch houdini with necessary settings else 
        rise warning message
        """
        
        if not self.shot_combo_box.currentText() \
            or not self.sequence_combo_box.currentText() \
            or not self.shot_combo_box.currentText() \
            or not self.task_combo_box.currentText():
                
                self.show_warning_gui("All Fields Are Required To Be Filled!!")
                self.pfx_logger.error_logger("All Fields Are Required To Be Filled!!") 
                
        else:
            self.register_last_selected_entries()
            self.generate_houdini_environment_variables()
            self.create_folders()

            if not which(os.environ['HOUDINI_BIN_PATH']):
                msgs = os.environ['HOUDINI_BIN_PATH']
                msgs += "\n\nSpecified Houdini Version Not Exist"
                self.show_msg_box(msgs)
                self.pfx_logger.error_logger(f"{os.environ['HOUDINI_BIN_PATH']} Not Exist!!. Contact IT") 
                
            else:
                self.pfx_logger.info_logger(f"Opening Houdini {os.environ['HOUDINI_BIN_PATH']}")
                if self.template_chkbox.isChecked():
                    subprocess.Popen([os.environ['HOUDINI_BIN_PATH'], r"R:/studio/pipeline/internal/apps/houdini/19.5.493/hip/generic/generic_workflow.hip"],
                                    shell=True,
                                    env=os.environ)
                else:
                    subprocess.Popen(os.environ['HOUDINI_BIN_PATH'],
                                    shell=True,
                                    env=os.environ)
        

if __name__ == "__main__":
    
    app = QtWidgets.QApplication(sys.argv)
    pfx_houdini_launcer = PfxHoudiniLauncher()
    pfx_houdini_launcer.launcher_window.show()
    app.exec_()
