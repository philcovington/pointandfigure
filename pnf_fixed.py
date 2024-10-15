import yfinance as yf
import pandas as pd
import numpy as np

from dataclasses import dataclass
from datetime import datetime
from PyQt5 import QtWidgets, QtGui, QtCore

@dataclass
class Settings:
    CHART_FONT: str = 'Segoe Print'
    XO_FONT: str = 'Fira Code'
    CROSSHAIR_FONT_SIZE: int = 14
    CHART_START_DATE: str = '2023-12-01'
    UPDATE_TIME_MS: int = 60 * 15 * 1000
    FIXED_BOX_SIZE: int = 0
    REVERSAL_SIZE: int = 3 
    BACKGROUND_COLOR: tuple = (245, 222, 179, 95)  
    FILL_MODE: bool = True

SET = Settings()

def get_stock_data(symbol, start, end):
    stock_data = yf.download(symbol, start=start, end=end)
    return stock_data

def get_intraday_data(symbol):
    intraday_data = yf.download(tickers=symbol, period='1d', interval='1m', prepost=True)
    return intraday_data

def round_to_nearest(x, base=1):
    return base * round(x / base)

def determine_box_size(price):
    if SET.FIXED_BOX_SIZE > 0:
        return SET.FIXED_BOX_SIZE
    else:
        if price < 5:
            return 0.25
        elif price < 20:
            return 0.50
        elif price < 100:
            return 1
        elif price < 200:
            return 2
        elif price < 500:
            return 4
        else:
            return 5

def calculate_pf_data(highs, lows, box_size, reversal):
    direction = None
    pf_data = []
    current_column = []
    pf_data.append(current_column)
    last_price = round_to_nearest(highs[0] if highs[0] > lows[0] else lows[0], box_size)
    current_column.append(last_price)

    for high, low in zip(highs[1:], lows[1:]):
        if direction is None:
            if high >= last_price + box_size:
                direction = 'X'
                while high >= last_price + box_size:
                    last_price += box_size
                    current_column.append(last_price)
            elif low <= last_price - box_size:
                direction = 'O'
                while low <= last_price - box_size:
                    last_price -= box_size
                    current_column.append(last_price)
        elif direction == 'X':
            if high >= last_price + box_size:
                while high >= last_price + box_size:
                    last_price += box_size
                    current_column.append(last_price)
            elif low <= last_price - reversal * box_size:
                direction = 'O'
                current_column = []
                pf_data.append(current_column)
                while low <= last_price - box_size:
                    last_price -= box_size
                    current_column.append(last_price)
        elif direction == 'O':
            if low <= last_price - box_size:
                while low <= last_price - box_size:
                    last_price -= box_size
                    current_column.append(last_price)
            elif high >= last_price + reversal * box_size:
                direction = 'X'
                current_column = []
                pf_data.append(current_column)
                while high >= last_price + box_size:
                    last_price += box_size
                    current_column.append(last_price)

    return pf_data

def read_stock_list(file_path='stock_list.txt'):
    try:
        with open(file_path, 'r') as file:
            stocks = [line.strip() for line in file.readlines()]
        return stocks
    except FileNotFoundError:
        return []

class ChartCanvas(QtWidgets.QWidget):
    def __init__(self, symbol='AMD'):
        super().__init__()
        self.symbol = symbol
        self.start = SET.CHART_START_DATE
        self.end = datetime.now().strftime('%Y-%m-%d')
        self.box_size = SET.FIXED_BOX_SIZE
        self.reversal = SET.REVERSAL_SIZE
        self.crosshair_pos = None
        self.last_update = None
        self.flip = False
        self.average_price = 0.0
        self.setMouseTracking(True)
        self.update_chart()

    def update_chart(self, flip=False):
        self.flip = flip
        stock_data = get_stock_data(self.symbol, self.start, self.end)
        highs = stock_data['High'].values
        lows = stock_data['Low'].values

        try:
            intraday_data = get_intraday_data(self.symbol)
            self.close_price = intraday_data['Close'].values[-1]
        except:
            pass

        self.average_price = (np.mean(highs) + np.mean(lows)) / 2
        self.box_size = determine_box_size(self.average_price)

        self.pf_data = calculate_pf_data(highs, lows, self.box_size, self.reversal)

        self.min_price = round_to_nearest(min(min(column) for column in self.pf_data), self.box_size)
        self.max_price = round_to_nearest(max(max(column) for column in self.pf_data), self.box_size)
        self.rows = int((self.max_price - self.min_price) / self.box_size) + 2  # Add one more row

        self.last_update = datetime.now()

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        width = self.width()
        height = self.height()

        background_color = QtGui.QColor(*SET.BACKGROUND_COLOR)

        # Fill the background with the custom color
        painter.fillRect(self.rect(), background_color)
        
        # Add space at the top for additional text
        top_text_height = 10

        box_dim = min(width / (len(self.pf_data) + 1), (height - top_text_height) / self.rows)

        box_width = box_dim
        box_height = box_dim

        grid_width = len(self.pf_data) * box_width
        grid_height = self.rows * box_height

        left_margin = int(box_width * 6)
        top_margin = int((height - grid_height) / 2) + top_text_height

        # Set font size based on box dimensions
        font = QtGui.QFont(SET.XO_FONT, int(box_height * 0.6), QtGui.QFont.Bold)
        painter.setFont(font)

        # Draw the y-axis price labels with background
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
        painter.setBrush(QtGui.QBrush(background_color))
        y_axis_font = QtGui.QFont(SET.CHART_FONT, int(box_height * 0.5), QtGui.QFont.Bold)  # Slightly smaller font for y-axis labels
        painter.setFont(y_axis_font)
        for j in range(self.rows):
            price = self.min_price + j * self.box_size
            y = int(height - (j + 1) * box_height + box_height / 2 + top_margin)
            painter.drawRect(0, y - int(box_height // 2), int(left_margin - 5), int(box_height))
            rect = QtCore.QRect(0, y - int(box_height // 2), int(left_margin - 5), int(box_height))
            if self.box_size >= 1:
                painter.drawText(rect, QtCore.Qt.AlignCenter, f'{price:.0f}')
            else:
                painter.drawText(rect, QtCore.Qt.AlignCenter, f'{price:.2f}')

        # Draw the grid and fill the boxes
        painter.setFont(font)  # Set back to grid font
        painter.setPen(QtGui.QPen(QtCore.Qt.lightGray, 0.5))
        for i in range(len(self.pf_data)):
            for j in range(self.rows):
                x0 = int(i * box_width + left_margin)
                y0 = int(height - (j + 1) * box_height + top_margin)
                x1 = int(box_width)
                y1 = int(box_height)

                if SET.FILL_MODE:
                    # Determine if the box is part of the current column and fill with color
                    price = self.min_price + j * self.box_size
                    if price in self.pf_data[i]:
                        if i % 2 == 0:
                            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                        else:
                            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 100, 0)))
                    else:
                        painter.setBrush(QtGui.QBrush(background_color))
                    painter.drawRect(x0, y0, x1, y1)
                else:
                    # Draw the grid only when not in fill mode
                    painter.setBrush(QtGui.QBrush(background_color))
                    painter.drawRect(x0, y0, x1, y1)

        # Extend the x-axis columns to the right
        extra_columns = int((width - grid_width - left_margin) / box_width)
        for i in range(len(self.pf_data), len(self.pf_data) + extra_columns):
            for j in range(self.rows):
                x0 = int(i * box_width + left_margin)
                y0 = int(height - (j + 1) * box_height + top_margin)
                x1 = int(box_width)
                y1 = int(box_height)
                painter.setBrush(QtGui.QBrush(background_color))
                painter.drawRect(x0, y0, x1, y1)

        if not SET.FILL_MODE:
            # Set font size for X and O
            font_size = int(box_height * 0.8)
            font.setPointSize(font_size)
            painter.setFont(font)

            # Draw the Xs and Os
            for i, column in enumerate(self.pf_data):
                for price in column:
                    row = int((price - self.min_price) / self.box_size)
                    x = int(i * box_width + box_width / 2 + left_margin)
                    y = int(height - (row + 1) * box_height + box_height / 2 + top_margin)
                    if self.flip == False:
                        if i % 2 == 0:
                            painter.setPen(QtGui.QPen(QtCore.Qt.red, 1))
                            painter.drawText(x - font_size // 2, y + font_size // 2, "O")
                        else:
                            painter.setPen(QtGui.QPen(QtCore.Qt.blue, 1))
                            painter.drawText(x - font_size // 2, y + font_size // 2, "X")
                    else:
                        if i % 2 == 0:
                            painter.setPen(QtGui.QPen(QtCore.Qt.blue, 1))
                            painter.drawText(x - font_size // 2, y + font_size // 2, "X")
                        else:
                            painter.setPen(QtGui.QPen(QtCore.Qt.red, 1))
                            painter.drawText(x - font_size // 2, y + font_size // 2, "O") 

        # Draw the current close price line
        close_price_row = int((round_to_nearest(self.close_price, self.box_size) - self.min_price) / self.box_size)
        y = int(height - (close_price_row + 1) * box_height + box_height / 2 + top_margin)
        painter.setPen(QtGui.QPen(QtCore.Qt.blue, 2))
        painter.drawLine(left_margin, y, width, y)

        # Draw the box size and reversal info with smaller font
        calc_height = int(box_height * 0.25)
        if calc_height > 10:
            calc_height = 10
        elif calc_height < 8:
            calc_height = 8
        
        info_font = QtGui.QFont(SET.CHART_FONT, calc_height, QtGui.QFont.Bold)
        painter.setFont(info_font)
        painter.setPen(QtGui.QPen(QtCore.Qt.darkBlue, 1))
        painter.drawText(left_margin, top_text_height // 2 + 10, f'Box Size: {self.box_size}, Reversal: {self.reversal}, Price: ${self.close_price:1.2f}, Last Updated: {self.last_update.strftime("%Y-%d-%m %H:%M:%S")}')

        # Draw the crosshair if the mouse is over the widget
        if self.crosshair_pos:
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.DashLine))
            painter.drawLine(self.crosshair_pos.x(), 0, self.crosshair_pos.x(), height)
            painter.drawLine(0, self.crosshair_pos.y(), width, self.crosshair_pos.y())

            # Calculate and display the price at the crosshair position
            mouse_y = self.crosshair_pos.y()
            relative_y = mouse_y - top_margin + box_height / 2
            if 0 <= relative_y <= grid_height:
                price_index = int((relative_y) // (box_height))
                crosshair_price = self.min_price + (self.rows - price_index) * self.box_size
                painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))
                crosshair_font = QtGui.QFont(SET.CHART_FONT, SET.CROSSHAIR_FONT_SIZE, QtGui.QFont.Bold)
                painter.setFont(crosshair_font)
                painter.drawText(self.crosshair_pos.x() + 10, mouse_y, f'${crosshair_price:.2f}')

    def mouseMoveEvent(self, event):
        self.crosshair_pos = event.pos()
        self.update()

    def leaveEvent(self, event):
        self.crosshair_pos = None
        self.update()

    def save_chart_as_image(self, file_path):
        pixmap = self.grab()
        pixmap.save(file_path, 'PNG')

class ChartWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()               
        
    def initUI(self, symbol=''):
        self.stock_list = read_stock_list()
        symbol = self.stock_list[0]
        self.setWindowTitle(f"{symbol} Point and Figure Chart")
        self.setGeometry(100, 100, 2048, 1024)
        self.flip = False        
        
        self.label_size_selector = QtWidgets.QLabel(self)
        self.label_size_selector.setText('Box Size:')

        self.box_size_selector = QtWidgets.QComboBox(self)
        self.box_size_selector.addItems(['Auto', '0.25', '0.50', '1.0', '2.0', '4.0', '5.0'])
        self.box_size_selector.setCurrentIndex(0)
        self.box_size_selector.currentIndexChanged.connect(self.change_box_size)

        self.label_reversal = QtWidgets.QLabel(self)
        self.label_reversal.setText('Reversal:')

        self.reversal_selector = QtWidgets.QComboBox(self)
        self.reversal_selector.addItems(['1', '2', '3'])
        self.reversal_selector.setCurrentIndex(SET.REVERSAL_SIZE-1)
        self.reversal_selector.currentIndexChanged.connect(self.change_reversal)

        self.label_symbol_input = QtWidgets.QLabel(self)
        self.label_symbol_input.setText('Symbol:')
        
        self.symbol_input = QtWidgets.QComboBox(self)
        self.symbol_input.setEditable(True)
        self.symbol_input.addItems(self.stock_list)
        self.symbol_input.setCurrentText(symbol)
        self.symbol_input.lineEdit().returnPressed.connect(self.change_symbol)
        self.symbol_input.activated.connect(self.change_symbol)  # Ensure change_symbol is called when an item is selected
        self.symbol_input.setFixedWidth(100)

        self.spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)     

        self.save_button = QtWidgets.QPushButton('Save', self)
        self.save_button.clicked.connect(self.save_chart)

        self.flip_button = QtWidgets.QPushButton('Flip', self)
        self.flip_button.clicked.connect(self.flip_xo)

        self.font_button = QtWidgets.QPushButton('Font', self)
        self.font_button.clicked.connect(self.font_change)

        self.fill_mode_button = QtWidgets.QPushButton('Fill Mode', self)
        self.fill_mode_button.clicked.connect(self.toggle_fill_mode)

        self.canvas = ChartCanvas(symbol)

        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.addWidget(self.label_size_selector)
        self.top_layout.addWidget(self.box_size_selector)
        self.top_layout.addWidget(self.label_reversal)
        self.top_layout.addWidget(self.reversal_selector)
        self.top_layout.addWidget(self.label_symbol_input)
        self.top_layout.addWidget(self.symbol_input)
        self.top_layout.addItem(self.spacer)
        self.top_layout.addWidget(self.save_button)
        self.top_layout.addWidget(self.flip_button)
        self.top_layout.addWidget(self.font_button)
        self.top_layout.addWidget(self.fill_mode_button)
        
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.top_layout)
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        
        self.schedule_updates()

    def change_symbol(self):
        try:
            new_symbol = self.symbol_input.currentText().upper()
            self.canvas.symbol = new_symbol
            self.setWindowTitle(f"{new_symbol} Point and Figure Chart")
            self.canvas.update_chart()
        except:
            pass        

    def change_box_size(self):
        try:
            SET.FIXED_BOX_SIZE = float(self.box_size_selector.currentText())
        except ValueError:            
            if self.box_size_selector.currentText() == 'Auto':
                SET.FIXED_BOX_SIZE = 0                
            
        self.canvas.update_chart(self.flip)

    def change_reversal(self):
        try:
            self.canvas.reversal = int(self.reversal_selector.currentText())
            SET.REVERSAL_SIZE = self.canvas.reversal
        except ValueError:
            pass

        self.canvas.update_chart(self.flip)

    def save_chart(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Chart As Image", f"C:\\Users\\philc\\Pictures\\PNF Charts\\{self.canvas.symbol}_PNF_{datetime.now().strftime('%Y-%m-%d')}", "PNG Files (*.png);;All Files (*)", options=options)
        if file_path:
            self.canvas.save_chart_as_image(file_path)

    def flip_xo(self):
        if self.flip == True:
            self.flip = False
        else:
            self.flip = True

        self.canvas.update_chart(self.flip)

    def font_change(self):
        if SET.CHART_FONT == 'Segoe Print':
            SET.CHART_FONT = 'Fira Code'
        else:
            SET.CHART_FONT = 'Segoe Print'

        self.canvas.update_chart(self.flip)

    def toggle_fill_mode(self):
        SET.FILL_MODE = not SET.FILL_MODE
        self.canvas.update_chart(self.flip)

    def schedule_updates(self):
        self.canvas.update_chart(self.flip)
        QtCore.QTimer.singleShot(SET.UPDATE_TIME_MS, self.schedule_updates)  # Schedule the next update in SET.UPDATE_TIME_MS minutes

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = ChartWindow()
    window.show()
    app.exec_()

