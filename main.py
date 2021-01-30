from PyQt5 import uic
from PyQt5.QtWidgets import (QAction, QApplication, QLineEdit, QWidget, QLabel,
              qApp, QSystemTrayIcon, QMenu)
from PyQt5.QtCore import (QFile, Qt)
from PyQt5.QtGui import QIcon
from easysettings import EasySettings
import sys, os, threading, time, schedule, json
from urllib.request import urlopen
from win10toast import ToastNotifier
from os.path import expanduser


#icon taskbar
try:
    from PyQt5.QtWinExtras import QtWin
    myappid = 'ip.information.python.program'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)    
except ImportError:
    pass

#pyinstaller
def resource_path(relative_path):
    """is used for pyinstaller so it can read the relative path"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)

#resources
userfold = expanduser("~")
config = EasySettings(userfold+"./ipinfo.conf")
logo = resource_path('./icons/logo.png')
logoIco = resource_path('./icons/logo.ico')
iconExit = resource_path('./icons/exit.png')
guiFile = resource_path('./gui/main.ui')
URL = 'https://ipinfo.io/json'



app = QApplication([])
app.setQuitOnLastWindowClosed(False)
toaster = ToastNotifier()


def notification(message):
    """Windows10 notification"""
    toaster.show_toast("IPinfo",
                   message,
                   icon_path=logoIco,
                   duration=3,
                   threaded=True)

class Config(QWidget):
    """Config window - called from taskbar"""
    def __init__(self):
        super().__init__()
        UIFile = QFile(guiFile)
        UIFile.open(QFile.ReadOnly)
        uic.loadUi(UIFile, self)
        UIFile.close()

        self.getData.clicked.connect(self.fetchIP)
        self.remData.clicked.connect(self.delData)

    def delData(self):
        """delete the data in the forms"""

        self.IpE.clear()
        self.hostnameE.clear()
        self.cityE.clear()
        self.regionE.clear()
        self.countryE.clear()
        self.locationE.clear()
        self.orgE.clear()
        self.postE.clear()
        self.timezE.clear()       

    def fetchIP(self):
        """fetch the data from ipinfo.io"""

        ipData = urlopen(URL)
        data = json.load(ipData)

        self.IpE.setText(data['ip'])
        self.hostnameE.setText(data['hostname'])
        self.cityE.setText(data['city'])
        self.regionE.setText(data['region'])
        self.countryE.setText(data['country'])
        self.locationE.setText(data['loc'])
        self.orgE.setText(data['org'])
        self.postE.setText(data['postal'])
        self.timezE.setText(data['timezone'])
        tray.setToolTip(f"Your IP is: {data['ip']}")
        notification(f"Your IP is: {data['ip']}")
        
class ContinuousScheduler(schedule.Scheduler):
    """this is a class which uses inheritance to act as a normal Scheduler,
        but also can run_continuously() in another thread"""
        #https://stackoverflow.com/questions/46453938/python-schedule-library-needs-to-get-busy-loop
    def run_continuously(self, interval=1):
            """Continuously run, while executing pending jobs at each elapsed
            time interval.
            @return cease_continuous_run: threading.Event which can be set to
            cease continuous run.
            Please note that it is *intended behavior that run_continuously()
            does not run missed jobs*. For example, if you've registered a job
            that should run every minute and you set a continuous run interval
            of one hour then your job won't be run 60 times at each interval but
            only once.
            """
            cease_continuous_run = threading.Event()

            class ScheduleThread(threading.Thread):
                """The job that should run continuous"""
                @classmethod
                def run(cls):
                    # I've extended this a bit by adding self.jobs is None
                    # now it will stop running if there are no jobs stored on this schedule
                    while not cease_continuous_run.is_set() and self.jobs:
                        # for debugging
                        # print("ccr_flag: {0}, no. of jobs: {1}".format(cease_continuous_run.is_set(), len(self.jobs)))
                        self.run_pending()
                        time.sleep(interval)

            continuous_thread = ScheduleThread()
            continuous_thread.start()
            return cease_continuous_run

c = Config()


class Worker():
    """Handles the threads"""
    getIP = ContinuousScheduler()
    stopSche = object

    def schedDo(self, schedTime):
        """Starts the shedule and kills the current running"""
        self.getIP.every(schedTime).minutes.do(lambda: c.fetchIP())
        self.stopSche = self.getIP.run_continuously()
        notification(f"Schedule started! Will fetch IP every {schedTime} minutes!")

    def scheStop(self):
        """Kill the running thread and schedule"""
        self.stopSche.set()


w = Worker()


def cmd_config():
    """#calls QWidget"""
    c.show()
    c.setWindowIcon(QIcon(logoIco))


tray = QSystemTrayIcon()
trayIcon = QIcon(logo)
tray.setIcon(trayIcon)
tray.setVisible(True)

menu = QMenu()


settApp = QAction("IP information")
settApp.triggered.connect(cmd_config)
menu.addAction(settApp)

fetchApp = QAction("Fetch IP")
fetchApp.triggered.connect(lambda: c.fetchIP())
menu.addAction(fetchApp)

scheMenu = menu.addMenu("Schedule")

schedSixt = QAction("Every 60 minutes")
schedSixt.triggered.connect(lambda: w.schedDo(int(60)))
scheMenu.addAction(schedSixt)

# Quit app
exitApp = QAction(QIcon(iconExit),"Exit")
exitApp.triggered.connect(app.quit)
exitApp.triggered.connect(lambda: w.scheStop())
menu.addAction(exitApp)

#start standard schedule with the app
tray.setToolTip("IPinfo: No IP fetched!\nStart a manual from settings or start a schedule!")


# Add the menu to the tray
tray.setContextMenu(menu)


app.exec_()