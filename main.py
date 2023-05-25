import sys
from PySide6.QtWidgets import *
from PySide6 import QtCharts
from PySide6.QtCore import *
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat, QPainter, QPalette, QBrush, QPaintEvent, QMouseEvent, QFont
import pyqtgraph as pg
import pandas as pd
from functools import partial
from range_slider import RangeSlider
import numpy as np

# Initialize data - read the pre-processed data
batting_data = pd.read_csv('data/batting_f.csv')
pitching_data = pd.read_csv('data/pitching_f.csv')
fielding_data = pd.read_csv('data/fielding_f.csv')

# To use columns from pandas dataframe as lists
batting_data['teams'] = batting_data['teams'].apply(eval)
pitching_data['teams'] = pitching_data['teams'].apply(eval)
fielding_data['teams'] = fielding_data['teams'].apply(eval)
fielding_data['field_positions'] = fielding_data['field_positions'].apply(eval)

# Initialize data - get the list of players from all three dataframes
players = np.concatenate((batting_data['player'].values, pitching_data['player'].values, fielding_data['player'].values))
players, indexes = np.unique(players, return_index=True)

# Initialize data - pre-compute the limits for the aggregated data
pitching_att_selection = list(range(1, 3, 1)) + list(range(4, 8, 1))
batting_att_selection = list(range(2, 8, 1))
fielding_att_selection = list(range(2, 6, 1))
batting_averages_min = batting_data.groupby('player').mean(numeric_only=True).min()[batting_att_selection]
batting_averages_max = batting_data.groupby('player').mean(numeric_only=True).quantile(0.8)[batting_att_selection]
pitching_averages_min = pitching_data.groupby('player').mean(numeric_only=True).min()[pitching_att_selection]
pitching_averages_max = pitching_data.groupby('player').mean(numeric_only=True).quantile(0.8)[pitching_att_selection]
fielding_averages_min = fielding_data.groupby('player').mean(numeric_only=True).min()[fielding_att_selection]
fielding_averages_max = fielding_data.groupby('player').mean(numeric_only=True).quantile(0.8)[fielding_att_selection]

# Attributes description to use in plots, titles, ...
attributes_bat = ['doubles',
                 'triples',
                 'homeruns',
                 'at_bats',
                 'runs',
                 'hits']

attributes_pitch = ['wins',
                    'losses',
                    'saves',
                    'hits',
                    'strikeouts',
                    'wild_pitches']

attributes_field = ['putouts',
                     'assists',
                     'errors',
                    'innings_played_in_outs',
                    ]

attributes_description = {'year' : 'YEAR',
                          'player' : 'PLAYER',
                          'games_on_bat' : 'TOTAL GAMES ON BAT',
                          'at_bats' : 'AT BAT (AB)',
                          'runs': 'RUN (R)',
                          'hits': 'HIT (H)',
                          'doubles' : 'DOUBLE (2B)',
                          'triples' : 'TRIPLE (3B)',
                          'homeruns' : 'HOME RUN (HR)',
                          'strikeouts' : 'STRIKEOUT (SO)',
                          'games_in_field': 'TOTAL GAMES IN FIELD',
                          'innings_played_in_outs' : 'INNING PLAYED (INN)',
                          'putouts' : 'PUTOUT (PO)',
                          'assists' : "ASSIST (A)",
                          'errors' : "ERROR (E)",
                          'field_positions' : "FIELD POSITIONS",
                          'teams' : 'TEAM(S)',
                          'wins' : 'WIN (W)',
                          'losses' : "LOSS (L)",
                          'shutouts' : 'SHUTOUT (SO)',
                          'saves' : 'SAVE (SV)',
                          'outs_pitched' : 'OUTS PITCHED (IPOuts)',
                          'earned_runs' : 'EARNED RUN (ER)',
                          'wild_pitches' : 'WILD PITCH (WP)',
                          'balks' : "BALK (BK)",
                          'runs_allowed' : 'RUNS ALLOWED (AR)'}

# Individual attributes tabs + chart for these attributes
class PlayerTabStats(QtCharts.QChartView):
    def __init__(self, parent, attributes, button_style):
        self.object = QWidget()
        layout = QVBoxLayout()
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout()
        self.button_group = []
        for attr in attributes:
            button = QToolButton()
            button.setText(attributes_description[attr])
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
            button.setStyleSheet(button_style)
            button.clicked.connect(partial(parent.handleTabAttributes, attr))
            self.button_group.append(button)
            buttons_layout.addWidget(button)
        buttons_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget)
        layout.addSpacing(10)
        self.graphWidget = pg.PlotWidget()
        layout.addWidget(self.graphWidget)
        self.object.setLayout(layout)

# Manual selection of year range
class IntervalSelector(QtCharts.QChartView):
    def __init__(self, parent):
        self.min_spinbox = QSpinBox()
        self.min_spinbox.setMinimum(1884)
        self.min_spinbox.setMaximum(2023)
        self.min_spinbox.setSingleStep(1)
        self.min_spinbox.setMaximumWidth(50)


        self.max_spinbox = QSpinBox()
        self.max_spinbox.setMinimum(1884)
        self.max_spinbox.setMaximum(2023)
        self.max_spinbox.setSingleStep(1)
        self.min_spinbox.setMaximumWidth(50)

        self.min_spinbox.valueChanged.connect(parent.updateSpinbox)
        self.max_spinbox.valueChanged.connect(parent.updateSpinbox)

        self.object = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.min_spinbox, alignment=Qt.AlignLeft)
        controls_layout.addWidget(self.max_spinbox, alignment=Qt.AlignRight)
        self.object.setLayout(controls_layout)

# Individual player stats
class LeftView(QtCharts.QChartView):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.parent = parent

        # Fielding/batting/pitching stats selection tabs
        self.tabs = QTabWidget()
        self.tabs.tabBarClicked.connect(self.handleDataCategory)
        self.tabs.setTabPosition(QTabWidget.West)
        button_style = """
                
                QToolButton:checked {
                    background-color: orange;
                    color: black;
                    font-weight: bold;

                }
                QToolButton:hover {
                    background-color: orange;
                    color: white;
                }
                """

        # Create the tabs for batting stats group
        batting_stats = PlayerTabStats(self, attributes_bat, button_style)
        self.batting_tab = batting_stats.object
        self.batting_group = batting_stats.button_group
        self.graphWidget_bat = batting_stats.graphWidget

        # Create the tabs for pitching stats group
        pitching_stats = PlayerTabStats(self, attributes_pitch, button_style)
        self.pitching_tab = pitching_stats.object
        self.pitching_group = pitching_stats.button_group
        self.graphWidget_pitch = pitching_stats.graphWidget

        # Create the tabs for fielding stats group
        fielding_stats = PlayerTabStats(self, attributes_field, button_style)
        self.fielding_tab = fielding_stats.object
        self.fielding_group = fielding_stats.button_group
        self.graphWidget_field = fielding_stats.graphWidget

        # Create the tabs for fielding stats group
        self.tabs.addTab(self.batting_tab, 'Batting stats')
        self.tabs.addTab(self.pitching_tab, 'Pitching stats')
        self.tabs.addTab(self.fielding_tab, 'Fielding stats')

        # Create year selection slide
        self.slider = RangeSlider(Qt.Horizontal)
        self.slider.setMinimumHeight(30)
        self.slider.setMinimum(1884)
        self.slider.setMaximum(2022)
        self.slider.setLow(1884)
        self.slider.setHigh(2022)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.sliderMoved.connect(self.updateSlider)

        self.manual_range_selector = IntervalSelector(self)

        layout.addWidget(self.tabs)
        layout.addWidget(self.slider)
        layout.addWidget(self.manual_range_selector.object)

        # set default values to be displayed
        self.datap1 = None
        self.datap2 = None
        # self.parent.selected_domain = 'batting'
        self.attribute = 'doubles' # default on startup
        self.graphWidget = self.graphWidget_bat
        self.setLayout(layout)

    # propagates change from manual selected year range
    def updateSpinbox(self):
        min_value = self.manual_range_selector.min_spinbox.value()
        max_value = self.manual_range_selector.max_spinbox.value()
        self.slider.setLow(min_value)
        self.slider.setHigh(max_value)
        self.update_plot(self.player_name1, self.player_name2, min_value, max_value, trigger_mode='year_change')
        self.parent.selected_year_range = (min_value, max_value)
        self.parent.update_right_view()

    # propagates change from slider selected year range
    def updateSlider(self, from_year, to_year):
        with QSignalBlocker(self.manual_range_selector.min_spinbox):
            self.manual_range_selector.min_spinbox.setValue(from_year)
        with QSignalBlocker(self.manual_range_selector.max_spinbox):
            self.manual_range_selector.max_spinbox.setValue(to_year)
        self.parent.selected_year_range = (from_year, to_year)
        self.parent.update_right_view()
        self.update_plot(self.player_name1, self.player_name2, from_year, to_year, trigger_mode='year_change')

    # handle when attribute category is changed by user
    def handleDataCategory(self, index):
        if index == 0:
            self.parent.selected_domain = 'batting'
            self.handleTabAttributes('doubles')
            self.graphWidget = self.graphWidget_bat
            self.handleTabAttributes(attributes_bat[0])
        elif index == 1:
            self.parent.selected_domain = 'pitching'
            self.handleTabAttributes('wins')
            self.graphWidget = self.graphWidget_pitch
            self.handleTabAttributes(attributes_pitch[0])
        else:
            self.parent.selected_domain = 'fielding'
            self.handleTabAttributes('putouts')
            self.graphWidget = self.graphWidget_field
            self.handleTabAttributes(attributes_field[0])
        self.parent.update_right_view()

    # routine to uncheck all buttons except the selected (becasue QToolButton does not implements this)
    def checkSingleButton(self, buttons, attribute):
        for btn in buttons:
            if btn.text() == attributes_description[attribute]:
                btn.setChecked(True)
            else:
                btn.setChecked(False)

    # handle when an attribute is choosen, propagates further
    def handleTabAttributes(self, attribute):
        if self.parent.selected_domain == 'batting':
            self.checkSingleButton(self.batting_group, attribute)
            self.attribute = attribute
        elif self.parent.selected_domain == 'pitching':
            self.checkSingleButton(self.pitching_group, attribute)
            self.attribute = attribute
        elif self.parent.selected_domain == 'fielding':
            self.checkSingleButton(self.fielding_group, attribute)
            self.attribute = attribute
        self.update_plot(self.player_name1, self.player_name2, trigger_mode='attribute_change')

    # creats the line chart
    def plotStats(self, player1_data, player2_data):
        player1 = self.player_name1
        player2 = self.player_name2
        attribute = self.attribute
        self.graphWidget.clear()
        self.graphWidget.setBackground('w')
        # Add Title
        self.graphWidget.setTitle(attributes_description[attribute], color="gray", size="40pt")

        # Add Axis Labels
        styles = {"color": "gray", "font-size": "15px"}
        self.graphWidget.setLabel("left", attributes_description[attribute], **styles)
        self.graphWidget.setLabel("bottom", 'Year', **styles)
        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)

        # Set Range
        padd = 1
        try:
            self.graphWidget.setXRange(min(player1_data['year'].min(), player2_data['year'].min())-padd, max(player1_data['year'].max(), player2_data['year'].max())+padd, padding=0)
            self.graphWidget.setYRange(min(player1_data[attribute].min(), player2_data[attribute].min())-padd, max(player1_data[attribute].max(), player2_data[attribute].max())+padd, padding=0)
        except:
            pass
        self.plot(player1_data['year'], player1_data[attribute], player1 + " - " + attributes_description[attribute], 'blue')
        self.plot(player2_data['year'], player2_data[attribute], player2 + " - " + attributes_description[attribute], 'orange')

    def plot(self, x, y, plotname, color):
        pen = pg.mkPen(color=color, width=5)
        self.graphWidget.plot(x.to_list(), y.to_list(), name=plotname, pen=pen, symbol='o', symbolSize=10, symbolBrush=(color))

    # Propagates newly filtered data to other view, sets up the data at initialization
    def update_plot(self, player1, player2, year_from=1884, year_to=2022, trigger_mode='player_change'):
        self.parent.selected_year_range = (year_from, year_to)
        if trigger_mode == 'year_change':
            player1_data = self.datap1
            player2_data = self.datap2
            player1_data = player1_data[(player1_data['year'] >= year_from) & (player1_data['year'] <= year_to)]
            player2_data = player2_data[(player2_data['year'] >= year_from) & (player2_data['year'] <= year_to)]
        else:
            if trigger_mode == 'player_change':
                for i in range(3):
                    self.tabs.setTabEnabled(i, True)

            if self.parent.selected_domain == 'batting':
                data = batting_data
            elif self.parent.selected_domain == 'pitching':
                data = pitching_data
            elif self.parent.selected_domain == 'fielding':
                data = fielding_data
            else:   # not initialized yet
                data = batting_data
                self.parent.selected_domain = 'batting'
            year_filtered = data[(data['year'] >= year_from) & (data['year'] <= year_to)]
            player1_data = year_filtered[year_filtered['player'] == player1]
            player2_data = year_filtered[year_filtered['player'] == player2]

            # when there are no data for both players, discard the tab (batting/pitching)
            if player1_data.empty and player2_data.empty:
                if self.parent.selected_domain == 'batting':
                    self.tabs.setTabEnabled(0, False)
                elif self.parent.selected_domain == 'pitching':
                    self.tabs.setTabEnabled(1, False)
                elif self.parent.selected_domain == 'fielding':
                    self.tabs.setTabEnabled(2, False)
                self.parent.selected_domain = 'batting'
                self.attribute = 'doubles'
                self.update_plot(player1, player2, year_from, year_to, trigger_mode='category_change')
                return

            self.datap1 = player1_data
            self.datap2 = player2_data
            self.player_name1 = player1
            self.player_name2 = player2
            try:
                self.year_limits = (min(player1_data['year'].min(), player2_data['year'].min()), max(player1_data['year'].max(), player2_data['year'].max()))
                data_year_min, data_year_max = self.year_limits
                with QSignalBlocker(self.slider):
                    self.slider.setMaximum(data_year_max)
                    self.slider.setMinimum(data_year_min)
                    self.slider.setLow(data_year_min)
                    self.slider.setHigh(data_year_max)
                with QSignalBlocker(self.manual_range_selector.min_spinbox):
                    self.manual_range_selector.min_spinbox.setMinimum(data_year_min)
                    self.manual_range_selector.min_spinbox.setValue(data_year_min)
                with QSignalBlocker(self.manual_range_selector.max_spinbox):
                    self.manual_range_selector.max_spinbox.setMaximum(data_year_max)
                    self.manual_range_selector.max_spinbox.setValue(data_year_max)
            except:
                pass

        self.plotStats(player1_data, player2_data)

# Aggreagated stats for one player
class AggStats(QWidget):
    def __init__(self, parent, player_index):
        super().__init__(parent)
        self.player_index = player_index
        layout = QVBoxLayout(self)
        font_name = QFont()
        font_name.setPixelSize(25)
        font_name.setBold(True)
        font = QFont()
        font.setPixelSize(15)

        # Player name label
        self.player_label = QLabel()
        self.player_label.setFont(font_name)
        layout.addWidget(self.player_label)

        # Team names
        self.team_label = QLabel()
        self.team_label.setFont(font)
        self.team_label.setWordWrap(True)
        layout.addWidget(self.team_label)

        self.game_count_label = QLabel()
        self.game_count_label.setFont(font)
        layout.addWidget(self.game_count_label)

        # Star glyph plot
        self.StarWidget = pg.PlotWidget()

        layout.addWidget(self.StarWidget)
        self.setLayout(layout)
        self.layout = layout

    # propagates newly filtered data, initialize new plots
    def update_aggregated_stats(self, player_data, limits_min, limits_max, player_name, data_category):
        teams = player_data['teams'].explode()
        team_names = ', '.join(teams.unique())[:-1]
        self.player_label.setText(player_name)
        self.team_label.setText(team_names)
        self.game_count_label.setText("Total games: " + str(player_data['games_played'].sum()))
        if data_category == "batting":
            self.plot_star_glyph(player_data.iloc[:, [x+1 for x in batting_att_selection]], limits_min, limits_max)
        elif data_category == "pitching":
            self.plot_star_glyph(player_data.iloc[:, [x+1 for x in pitching_att_selection]], limits_min, limits_max)
        elif data_category == "fielding":
            self.plot_star_glyph(player_data.iloc[:, [x+1 for x in fielding_att_selection]], limits_min, limits_max)

    # create the STAR Glyph plot
    def plot_star_glyph(self, player_data, limits_min, limits_max):
        self.StarWidget.clear()
        self.StarWidget.setAspectLocked()
        self.StarWidget.setBackground('w')
        self.StarWidget.showGrid(x=False, y=False)
        self.StarWidget.getPlotItem().hideAxis('bottom')
        self.StarWidget.getPlotItem().hideAxis('left')

        # Add polar grid lines
        for r in range(1, 5, 1):
            circle = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
            circle.setPen(pg.mkPen(color='gray', width=1))
            self.StarWidget.addItem(circle)
        circle = QGraphicsEllipseItem(-5, -5, 5 * 2, 5 * 2)
        circle.setPen(pg.mkPen(color='darkgray', width=3))
        self.StarWidget.addItem(circle)

        player_values = player_data.mean().values.tolist()
        min_value = 0
        max_value = 5
        normalized_values = (player_values - limits_min.values) / (limits_max.values - limits_min.values) * (max_value - min_value) + min_value
        normalized_values[normalized_values > max_value] = max_value
        radius = normalized_values.tolist()
        radius.append(radius[0])
        theta = np.linspace(0, 2 * np.pi, len(player_data.columns)+1).tolist()
        font = QFont()
        font.setPixelSize(9)

        # add attribute labels
        for i in range(len(theta) - 1):
            x = 7 * np.cos(theta[i])
            y = 7 * np.sin(theta[i])
            txt = pg.TextItem(attributes_description[player_data.columns[i]], color='gray', anchor=(0.5, 0.5))
            txt.setPos(x, y)
            txt.setFont(font)
            self.StarWidget.addItem(txt)

        # tranform player data polar
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)
        if self.player_index == 0:
            self.plot(x, y, 'blue')
        else:
            self.plot(x, y, 'orange')

    def plot(self, x, y, color):
        pen = pg.mkPen(color=color, width=5)
        self.StarWidget.plot(x, y, pen=pen, symbol='o', symbolSize=10, symbolBrush=(color), brush='orange')
# Individual attributes stats
class RightView(QtCharts.QChartView):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setMaximumWidth(parent.width() // 2)

        self.player1_widget = AggStats(self, 0)
        self.player2_widget = AggStats(self, 1)

        layout.addWidget(self.player1_widget)
        layout.addStretch()
        layout.addWidget(self.player2_widget)
        self.setLayout(layout)

    # Propagates newly filtered data to other view, sets up the data at initialization
    def update_plot(self, player1, player2, year_range, attribute_category):
        if attribute_category == 'batting':
            data = batting_data
            attributes_limits_min = batting_averages_min
            attributes_limits_max = batting_averages_max
        elif attribute_category == 'pitching':
            data = pitching_data
            attributes_limits_min = pitching_averages_min
            attributes_limits_max = pitching_averages_max
        elif attribute_category == 'fielding':
            data = fielding_data
            attributes_limits_min = fielding_averages_min
            attributes_limits_max = fielding_averages_max
        year_from, year_to = year_range
        year_filtered = data[(data['year'] >= year_from) & (data['year'] <= year_to)]
        player1_data = year_filtered[year_filtered['player'] == player1]
        player2_data = year_filtered[year_filtered['player'] == player2]
        self.player1_widget.update_aggregated_stats(player1_data, attributes_limits_min, attributes_limits_max, player1, attribute_category)
        self.player2_widget.update_aggregated_stats(player2_data, attributes_limits_min, attributes_limits_max, player2, attribute_category)

# Dropdown player selection button
class PlayerSelection(QComboBox):
    def __init__(self, parent, player_index):
        super().__init__(parent)
        self.setEditable(True)  # autocompletion is only available for an editable combobox.
        self.completer().setCompletionMode(QCompleter.PopupCompletion) # sets required behavior for autocomplete method
        self.setInsertPolicy(QComboBox.NoInsert) #  prevents the user to add items to the list
        self.player_index = player_index
        self.addItems(players)
        self.currentIndexChanged.connect(parent.update_plot)
        self.setFixedWidth(150)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Baseball players across years')
        self.setMinimumSize(800, 600)
        self.createGraphicView()

        # Initialize all the views
        self.selected_year_range = (None, None)
        self.selected_domain = None

        self.update_plot()
    def createGraphicView(self):
        format = QSurfaceFormat();
        format.setSamples(4);
        gl = QOpenGLWidget();
        gl.setFormat(format);
        gl.setAutoFillBackground(True)

        # Create the main widget and layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.controls_layout = QVBoxLayout()

        # Create the left view
        self.left_view = LeftView(self)
        self.main_layout.addWidget(self.left_view)

        # Create the player selection dropdown
        self.player_selection = PlayerSelection(self, 1)
        self.player_selection2 = PlayerSelection(self, 2)

        self.controls_layout.addWidget(self.player_selection, alignment=Qt.AlignVCenter | Qt.AlignHCenter)
        self.controls_layout.addWidget(self.player_selection2, alignment=Qt.AlignVCenter | Qt.AlignHCenter)

        self.main_layout.addLayout(self.controls_layout)

        # Create the right view
        self.right_view = RightView(self)
        self.main_layout.addWidget(self.right_view)

        # Set the layout
        self.central_widget.setLayout(self.main_layout)
        self.main_layout.setGeometry(QRect(0, 0, 800, 600))

    # Propagates newly filtered data to other view, sets up the data at initialization
    def update_plot(self):
        selected_player1 = self.player_selection.currentText()
        selected_player2 = self.player_selection2.currentText()
        self.left_view.update_plot(selected_player1, selected_player2)
        self.right_view.update_plot(selected_player1, selected_player2, self.selected_year_range, self.selected_domain)

    def update_right_view(self):
        selected_player1 = self.player_selection.currentText()
        selected_player2 = self.player_selection2.currentText()
        self.right_view.update_plot(selected_player1, selected_player2, self.selected_year_range, self.selected_domain)
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()