#!/usr/bin/env python3

import signal
import sys
import glob
import yaml

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtCore import Qt, QThread, QTimer
from gui.QFloatSlider import QFloatSlider

import virtual_webcam as vw
import filters


class Window(QWidget):
    def __init__(self, processing_thread):
        super().__init__()
        self.initUI()
        self.processing_thread = processing_thread

    def initUI(self):
        self.resize(640, 480)
        self.center()

        # Tree view of layers and filters
        self.tree = QTreeView()
        self.model = QStandardItemModel()
        self.tree.setModel(self.model)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setItemsExpandable(False)
        self.tree.selectionModel().selectionChanged.connect(self.item_click)
        
        # Tree actions
        add_layer_btn = QPushButton("Add Layer")
        add_layer_btn.clicked.connect(self.add_layer)
        add_filter_btn = QPushButton("Add Filter")
        add_filter_btn.clicked.connect(self.add_filter)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_selection)
        play_btn = QPushButton("⏸︎")
        play_btn.clicked.connect(self.toggle_play)

        tree_action_layout = QHBoxLayout()
        tree_action_layout.addWidget(add_layer_btn)
        tree_action_layout.addWidget(add_filter_btn)
        tree_action_layout.addWidget(remove_btn)
        tree_action_layout.addWidget(play_btn)
        tree_action_layout.addStretch(1)

        # Tree layout
        tree_layout = QVBoxLayout()
        tree_layout.addWidget(self.tree)
        tree_layout.addLayout(tree_action_layout)
        
        # Properties panel
        self.properties_layout = QVBoxLayout()

        # Rebuild tree
        self.rebuild_tree()
        
        # Action buttons
        load_btn = QPushButton("Reload config")
        load_btn.clicked.connect(self.reload_config)
        save_btn = QPushButton("Save config")
        save_btn.clicked.connect(self.save_config)
        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(QApplication.exit)
        
        # Layout:
        # tree | properties
        # action buttons
        main_layout = QHBoxLayout()
        main_layout.addLayout(tree_layout, 50)
        main_layout.addLayout(self.properties_layout, 50)
        action_button_layout = QHBoxLayout()
        action_button_layout.addWidget(load_btn)
        action_button_layout.addWidget(save_btn)
        action_button_layout.addWidget(quit_btn)
        
        layout = QVBoxLayout(self)
        layout.addLayout(main_layout)
        layout.addLayout(action_button_layout)

        self.setWindowIcon(QIcon("icon.ico"))
        self.setWindowTitle("Virtual Webcam Background")

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def center(self):
        frame = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())
    
    def reload_config(self):
        vw.config, vw.config_mtime = vw.load_config(0)
        self.rebuild_tree()

    def save_config(self):
        with open('config.yaml', 'w') as config_file:
            yaml.dump(vw.config, config_file)

    def toggle_play(self):
        if self.processing_thread.paused:
            self.processing_thread.paused = False
            self.sender().setText("⏸︎")
        else:
            self.processing_thread.paused = True
            self.sender().setText("⏵︎")

    def item_click(self, signal):
        index = signal.indexes()[0]
        item = self.model.itemFromIndex(index)
        self.construct_properties_layout(item.data())
    
    def construct_properties_layout(self, data):
        for i in reversed(range(self.properties_layout.count())): 
            child = self.properties_layout.takeAt(i)
            if child.widget() is not None:
                child.widget().deleteLater()
        
        # Determine if it's a layer or filters
        if data[0] == 'filter':
            (_, layer_filters, layer_filter) = data
            self.properties_layout.addWidget(QLabel("Filter type"))
            filter_type = layer_filter[0]
            
            types = QComboBox()
            filter_types = sorted(list(filters.filters.keys()))
            types.addItems(filter_types)
            types.setCurrentIndex(filter_types.index(filter_type))
            types.currentIndexChanged.connect(lambda x: self.update_filter_type(layer_filter, types.itemText(x)))
            self.properties_layout.addWidget(types)
            
            # Dynamic properties
            config = filters.get_filter(filter_type).config()
            for (i, (prop_name, prop)) in enumerate(config.items()):
                self.properties_layout.addWidget(QLabel(prop_name))
                if prop['type'] in ['integer', 'float']:
                    if prop.get('input', False):
                        if prop['type'] == 'integer':
                            slider = QSpinBox()
                        else:
                            slider = QDoubleSpinBox()
                    elif prop['type'] == 'integer':
                        slider = QSlider(Qt.Horizontal)
                        slider.setTickInterval(10)
                        slider.setTickPosition(QSlider.TicksBelow)
                    else:
                        slider = QFloatSlider(Qt.Horizontal)
                    slider.setSingleStep(prop.get('step_size', 1))
                    if 'range' in prop:
                        slider.setMinimum(prop['range'][0])
                        slider.setMaximum(prop['range'][1])
                    if len(layer_filter) > i + 1:
                        slider.setValue(layer_filter[i + 1])
                    
                    slider.valueChanged.connect(lambda value,i=i,slider=slider: self.update_filter_prop(layer_filter, i + 1, slider.value()))
                    self.properties_layout.addWidget(slider)
                elif prop['type'] == 'boolean':
                    checkbox = QCheckBox()
                    if len(layer_filter) > i + 1:
                        checkbox.setCheckState(Qt.Checked if layer_filter[i + 1] else Qt.Unchecked)
                    checkbox.stateChanged.connect(lambda value,i=i: self.update_filter_prop(layer_filter, i + 1, value))
                    self.properties_layout.addWidget(checkbox)
                elif prop['type'] == 'enum':
                    dropdown = QComboBox()
                    dropdown.addItems(prop['options'])
                    if len(layer_filter) > i + 1:
                        dropdown.setCurrentIndex(prop['options'].index(layer_filter[i+ 1]))
                    dropdown.currentIndexChanged.connect(lambda value,i=i: self.update_filter_prop(layer_filter, i + 1, self.sender().itemText(value)))
                    self.properties_layout.addWidget(dropdown)
                elif prop['type'] == 'file':
                    file_label = QLabel("File: %s" % layer_filter[i + 1])
                    self.properties_layout.addWidget(file_label)
                    file_selection_btn = QPushButton("Select file")
                    file_selection_btn.clicked.connect(lambda i=i,types=prop.get('file_types', None): self.select_file_property(types, data, i + 1, file_label))
                    self.properties_layout.addWidget(file_selection_btn)
                elif prop['type'] == 'dir':
                    dir_label = QLabel("Dir: %s" % layer_filter[i + 1])
                    self.properties_layout.addWidget(dir_label)
                    dir_selection_btn = QPushButton("Select directory")
                    dir_selection_btn.clicked.connect(lambda i=i: self.select_dir_property(data, i + 1, dir_label))
                    self.properties_layout.addWidget(dir_selection_btn)
                elif prop['type'] == 'constant':
                    label = QLabel("Constant: %s" % prop['value'])
                    self.properties_layout.addWidget(label)
                else:
                    label = QLabel("Unsupported type: %s" % prop['type'])
                    self.properties_layout.addWidget(label)
                
            self.properties_layout.addStretch(1)                
        elif data[0] == 'layer':
            (_, layer) = data
            self.properties_layout.addWidget(QLabel("Layer type"))
            types = QComboBox()
            layer_types = ["input", "foreground", "previous", "empty"];
            types.addItems(layer_types)
            types.setCurrentIndex(layer_types.index(next(iter(layer))))
            types.currentIndexChanged.connect(lambda x: self.update_layer_type(layer, types.itemText(x)))
            self.properties_layout.addWidget(types)
            self.properties_layout.addStretch(1)
    
    def select_file_property(self, types, data, i, file_label):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open file', '', types)
        if file_name:
            file_label.setText("File: %s" % file_name)
            self.update_filter_prop(data[2], i, file_name)

    def select_dir_property(self, data, i, dir_label):
        dir_name = QFileDialog.getExistingDirectory(self, 'Open directory', '',
                                                    QFileDialog.ShowDirsOnly)
        if dir_name:
            dir_label.setText("Dir: %s" % dir_name)
            self.update_filter_prop(data[2], i, dir_name)

    def get_selection_index(self):
        curr_index = self.tree.currentIndex()
        layer_index = curr_index.parent().row()
        filter_index = curr_index.row()
        if layer_index == -1:
            layer_index = filter_index
            filter_index = -1
        return (layer_index, filter_index)

    def rebuild_tree(self, index = None):
        if index is None:
            index = self.get_selection_index()
        layer_index, filter_index = index

        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Layer'])
        for layer_filters in vw.config.get("layers", []):
            layer_type = list(layer_filters.keys())[0]
            layer_item = QStandardItem(layer_type)
            layer_item.setData(("layer", layer_filters))
            for layer_filter in layer_filters[layer_type]:
                layer_filter_item = QStandardItem(layer_filter[0])
                layer_filter_item.setData(("filter", layer_filters, layer_filter))
                layer_item.appendRow(layer_filter_item)
            self.model.appendRow([layer_item])
        self.tree.expandAll()

        # Handle deletions
        if layer_index == -1:
            pass
        elif self.model.rowCount() <= layer_index:
            layer_index = self.model.rowCount() - 1
            filter_index = -1
        elif self.model.rowCount(self.model.item(layer_index).index()) <= filter_index:
            filter_index = self.model.rowCount(self.model.item(layer_index).index()) - 1

        # Reselect
        if filter_index != -1:
            self.tree.setCurrentIndex(self.model.item(layer_index).child(filter_index).index())
        elif layer_index != -1:
            self.tree.setCurrentIndex(self.model.item(layer_index).index())
        elif self.model.rowCount() != 0:
            self.tree.setCurrentIndex(self.model.item(0).index())

        if self.tree.currentIndex().isValid():
            self.construct_properties_layout(self.model.itemFromIndex(self.tree.currentIndex()).data())

        self.activate_changes()

    def add_layer(self):
        layer_index, filter_index = self.get_selection_index()
        vw.config.get("layers", []).insert(layer_index + 1, {"input": []})
        self.rebuild_tree((layer_index + 1, -1))

    def add_filter(self):
        layer_index, filter_index = self.get_selection_index()
        if layer_index == -1:
            return
        _, data = self.model.item(layer_index).data()
        data[list(data.keys())[0]].insert(filter_index + 1, ["gaussian_blur", 10, 10])
        self.rebuild_tree((layer_index, filter_index + 1))

    def remove_selection(self):
        curr_index = self.tree.currentIndex()
        if not curr_index.isValid():
            return

        data = self.model.itemFromIndex(curr_index).data()
        if data[0] == 'filter':
            next(iter(data[1].values())).remove(data[2])
        else:
            vw.config.get("layers", []).remove(data[1])
        self.rebuild_tree()

    def update_layer_type(self, layer_filters, new_layer_type):
        layer_type = list(layer_filters.keys())[0]
        filters = layer_filters[layer_type]
        layer_filters[new_layer_type] = filters
        del layer_filters[layer_type]
        self.rebuild_tree()
    
    def update_filter_type(self, layer_filter, new_filter_type):
        layer_filter[0] = new_filter_type
        while len(layer_filter) != 1:
            layer_filter.pop()
        config = filters.get_filter(new_filter_type).config()
        for (prop_name, prop) in config.items():
            if 'default' in prop:
                layer_filter.append(prop['default'])
            elif prop['type'] in ['integer', 'float']:
                layer_filter.append(prop['range'][0])
            elif prop['type'] == 'boolean':
                layer_filter.append(False)
            elif prop['type'] == 'constant':
                layer_filter.append(prop['value'])
            elif prop['type'] == 'enum':
                layer_filter.append(prop['options'][0])
            elif prop['type'] == 'file':
                layer_filter.append('images/fog.png')
            elif prop['type'] == 'dir':
                layer_filter.append('images/')
            else:
                layer_filter.append(None)

        self.rebuild_tree()
    
    def update_filter_prop(self, layer_filter, index, new_value):
        while len(layer_filter) <= index:
            layer_filter.append(None)
        layer_filter[index] = new_value
        self.activate_changes()
    
    def activate_changes(self):
        vw.layers = vw.reload_layers(vw.config)

class ProcessThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.paused = False

    def run(self):
        while self.running:
            if not self.paused:
                vw.mainloop()
            else:
                # Avoid slowing down the UI with a spin loop
                self.sleep(1)

def toggle_window(window):
    if window.isVisible():
        window.hide()
    else:
        window.showNormal()

def exit(app, processing_thread):
    processing_thread.running = False
    app.quit()

def main():
    app = QApplication(sys.argv)

    # Spin up processing thread
    thread = ProcessThread()
    thread.finished.connect(app.exit)
    thread.start()

    # Ugly hack to get nice termination behaviour :-/
    signal.signal(signal.SIGINT, lambda *a: exit(app, thread))
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    window = Window(thread)
    window.show()

    tray_icon = QSystemTrayIcon(QIcon("icon.ico"), app)
    tray_icon_menu = QMenu()
    config = tray_icon_menu.addAction('Configure')
    config.triggered.connect(window.showNormal)
    quit = tray_icon_menu.addAction('Quit')
    quit.triggered.connect(app.exit)
    tray_icon.setContextMenu(tray_icon_menu)
    tray_icon.activated.connect(lambda: toggle_window(window))
    tray_icon.setToolTip("Virtual Webcam Background")
    tray_icon.show()
    tray_icon.showMessage("Virtual Webcam Background running",
                          "... in the background ;-)")
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
