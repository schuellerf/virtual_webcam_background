import sys
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QFormLayout, QComboBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QDesktopWidget, QPushButton, QSlider, QTreeView, QWidget
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt, QThread

import virtual_webcam
import filters

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.resize(640, 480)
        self.center()

        # Tree
        self.tree = QTreeView()
        self.model = QStandardItemModel()
        self.tree.header().setDefaultSectionSize(180)
        self.tree.setModel(self.model)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setItemsExpandable(False)
        self.tree.clicked.connect(self.item_click)
        
        # Tree actions
        add_layer_btn = QPushButton("Add Layer")
        add_filter_btn = QPushButton("Add Filter")
        remove_btn = QPushButton("Remove")
        tree_action_layout = QHBoxLayout()
        tree_action_layout.addWidget(add_layer_btn)
        tree_action_layout.addWidget(add_filter_btn)
        tree_action_layout.addWidget(remove_btn)
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
        save_btn = QPushButton("Save config")
        
        # Layout:
        # tree | properties
        # action buttons
        main_layout = QHBoxLayout()
        main_layout.addLayout(tree_layout, 50)
        main_layout.addLayout(self.properties_layout, 50)
        action_button_layout = QHBoxLayout()
        action_button_layout.addWidget(load_btn)
        action_button_layout.addWidget(save_btn)
        
        layout = QVBoxLayout(self)
        layout.addLayout(main_layout)
        layout.addLayout(action_button_layout)
                
        self.setWindowTitle("Virtual Webcam Background")
        self.show()

    def center(self):
        frame = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())
    
    def item_click(self, signal):
        item = self.model.itemFromIndex(signal)
        print(item, item.data())
        self.construct_properties_layout(item.data())
    
    def construct_properties_layout(self, data = None):
        print("construct_properties", data)
        for i in reversed(range(self.properties_layout.count())): 
            child = self.properties_layout.takeAt(i)
            if child.widget() is not None:
                child.widget().deleteLater()
        
        # Determine if it's a layer or filters
        if isinstance(data, tuple):
            self.properties_layout.addWidget(QLabel("Filter type"))
            filter_type = data[1][0]
            
            types = QComboBox()
            filter_types = list(filters.filters.keys())
            types.addItems(filter_types)
            types.setCurrentIndex(filter_types.index(filter_type))
            types.currentIndexChanged.connect(lambda x: self.update_filter_type(data[1], types.itemText(x)))
            self.properties_layout.addWidget(types)
            
            # Dynamic properties
            for i, prop in enumerate(filters.get_filter_properties(filter_type)):
                self.properties_layout.addWidget(QLabel(prop[0]))
                if prop[1] == 'numeric':
                    slider = QSlider(Qt.Horizontal)
                    slider.setTickInterval(10)
                    slider.setSingleStep(1)
                    slider.setMinimum(prop[2])
                    slider.setMaximum(prop[3])
                    if len(data[1]) > i + 1:
                        slider.setValue(data[1][i + 1])
                    
                    slider.valueChanged.connect(lambda value: self.update_filter_prop(data[1], i + 1, value))
                    self.properties_layout.addWidget(slider)
                else:
                    self.properties_layout.addWidget(QLabel("Unsupported type: %s" % prop[1]))
                
            self.properties_layout.addStretch(1)                
        else:
            self.properties_layout.addWidget(QLabel("Layer type"))
            types = QComboBox()
            layer_types = ["input", "foreground", "previous", "empty"];
            types.addItems(layer_types)
            types.setCurrentIndex(layer_types.index(list(data.keys())[0]))
            types.currentIndexChanged.connect(lambda x: self.update_layer_type(data, types.itemText(x)))
            self.properties_layout.addWidget(types)
            self.properties_layout.addStretch(1)
    
    def rebuild_tree(self):
        curr_index = self.tree.currentIndex()
        layer_index = curr_index.parent().row()
        filter_index = curr_index.row()
        if layer_index == -1:
            layer_index = filter_index
            filter_index = -1

        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Layer'])
        for layer_filters in virtual_webcam.config.get("layers", []):
            layer_type = list(layer_filters.keys())[0]

            layer_item = QStandardItem(layer_type)
            layer_item.setData(layer_filters)

            for layer_filter in layer_filters[layer_type]:
                layer_filter_item = QStandardItem(layer_filter[0])
                layer_filter_item.setData((layer_filters, layer_filter))
                layer_item.appendRow(layer_filter_item)
            self.model.appendRow([layer_item])
        self.tree.expandAll()

        print(layer_index, filter_index)
        if filter_index != -1:
            self.tree.setCurrentIndex(self.model.item(layer_index).child(filter_index).index())
        elif layer_index != -1:
            self.tree.setCurrentIndex(self.model.item(layer_index).index())
        else:
            self.tree.setCurrentIndex(self.model.item(0).index())
        self.construct_properties_layout(self.model.itemFromIndex(self.tree.currentIndex()).data())
        # DEBUG
        self.activate_changes()

    def update_layer_type(self, layer_filters, new_layer_type):
        # FIXME: Absolutely ugly!
        layer_filters = next(x for x in virtual_webcam.config.get("layers", []) if x == layer_filters)

        layer_type = list(layer_filters.keys())[0]
        filters = layer_filters[layer_type]
        layer_filters[new_layer_type] = filters
        del layer_filters[layer_type]
        self.rebuild_tree()
    
    def update_filter_type(self, layer_filter, new_filter_type):
        layer_filter[0] = new_filter_type
        self.rebuild_tree()
    
    def update_filter_prop(self, layer_filter, index, new_value):
        while len(layer_filter) <= index:
            layer_filter.append(None)
        layer_filter[index] = new_value
        # DEBUG
        self.activate_changes()
    
    def activate_changes(self):
        # DEBUG
        virtual_webcam.layers = virtual_webcam.reload_layers(virtual_webcam.config)

class ProcessThread(QThread):

    def run(self):
        while True:
            virtual_webcam.mainloop()

def main():
    app = QApplication(sys.argv)
    window = Window()
    
    # Spin up thread
    thread = ProcessThread()
    thread.finished.connect(app.exit)
    thread.start()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
