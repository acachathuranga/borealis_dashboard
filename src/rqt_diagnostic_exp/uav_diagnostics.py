import rospy, rostopic
import rospkg

import PyQt5 as qt
from PyQt5.QtCore import QObject, QThread, QTimer
from uwb_msgs.msg import UUBmsg, UWBReading

class UAV_Diagnostic(QObject):
    publish_rate_signal = qt.QtCore.pyqtSignal() 
    delay_signal = qt.QtCore.pyqtSignal(float)  #seconds
    max_delay_signal = qt.QtCore.pyqtSignal(float)   #seconds
    time_since_max_delay_signal = qt.QtCore.pyqtSignal()   
    port_status_signal = qt.QtCore.pyqtSignal(str)
    ping_status_signal = qt.QtCore.pyqtSignal(str)
    start_record_signal = qt.QtCore.pyqtSignal(bool)
    value_out_of_range_signal = qt.QtCore.pyqtSignal(bool)

    def __init__(self, widget, topic, uav_name):
        super(UAV_Diagnostic, self).__init__()
        
        # Attributes
        self.topic = topic
        self.widget = widget
        self.max_delay = 0.0
        self.max_delay_time_stamp = 0.0
        self.record = False

        # Retrieve GUI Components
        self.publish_rate_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_publish_rate_label')
        self.delay_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_delay_label')
        self.max_delay_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_max_delay_label')
        self.TSMD_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_TSMD_label')
        self.port_status_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_port_status_label')
        self.ping_status_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_ping_status_label')
        self.value_range_label = self.widget.findChild(qt.QtWidgets.QLabel, uav_name + '_value_range_label')
        self.record_button = self.widget.findChild(qt.QtWidgets.QPushButton, uav_name + '_record_pushButton')
        

        # Subscribers
        self.rate = rostopic.ROSTopicHz(-1)
        rospy.Subscriber(topic, UUBmsg, self.rate.callback_hz, callback_args=topic)
        rospy.Subscriber(topic, UUBmsg, self.UUBCallback)
        # TODO Subscribe to Diagnostic Topic

        # Signal Connections
        self.publish_rate_signal.connect(self.showMessageRate)
        self.delay_signal.connect(self.showMessageDelay)
        self.max_delay_signal.connect(self.showMaxDelay)
        self.time_since_max_delay_signal.connect(self.showTSMD)
        self.value_out_of_range_signal.connect(self.showValueRange)
        

        # Start Class timer
        self.classTimer = self.ClassTimer(self.timerCallback)
        self.classTimer.start()

    def deinit(self):
        pass

    def clear(self):
        self.publish_rate_label.setText('0')
        self.delay_label.setText('0')
        self.max_delay_label.setText('0')
        self.TSMD_label.setText('0')
        self.port_status_label.setText('OK')
        self.ping_status_label.setText('OK')
        self.value_range_label.setText('OK')
        self.record_button.setText('Start Recording')

        self.publish_rate_label.setStyleSheet("")
        self.delay_label.setStyleSheet("")
        self.max_delay_label.setStyleSheet("")
        self.TSMD_label.setStyleSheet("")
        self.port_status_label.setStyleSheet("QLabel { background: rgb(71, 255, 62) }")
        self.ping_status_label.setStyleSheet("QLabel { background: rgb(71, 255, 62) }")
        self.value_range_label.setStyleSheet("QLabel { background: rgb(71, 255, 62) }")
        self.record_button.setStyleSheet("")
        
    def UUBCallback(self, msg):
        msgTime = msg.header.stamp.secs +  msg.header.stamp.nsecs * 1e-9
        curentTime = rospy.get_time()
        msgDelay = curentTime - msgTime 
        if msgDelay > self.max_delay:
            self.max_delay = msgDelay
            self.max_delay_time_stamp = curentTime
            self.max_delay_signal.emit(self.max_delay)
        
        for reading in msg.readings:
            if reading.distance > 10:
                self.value_out_of_range_signal.emit(False)
                break
            self.value_out_of_range_signal.emit(True)

            
        self.delay_signal.emit(msgDelay)
    
    def showMessageRate(self):
        try:
            rate = str(round( (self.rate.get_hz(topic=self.topic)[0]), 2))
            self.publish_rate_label.setStyleSheet("")
        except:
            rate = 'None'
            self.publish_rate_label.setStyleSheet("QLabel { background: red }")
        
        self.publish_rate_label.setText(rate)

    def showMessageDelay(self, delay):
        delay = round( delay * 1000, 2) # Milliseconds
        if abs(delay) > 100:
            self.delay_label.setStyleSheet("QLabel { background: red }")
        else:
            self.delay_label.setStyleSheet("")

        self.delay_label.setText(str(delay))

    def showMaxDelay(self, maxDelay):
        maxDelay = round( maxDelay * 1000, 2) # Milliseconds
        if abs(maxDelay) > 100:
            self.max_delay_label.setStyleSheet("QLabel { background: rgb(255, 170, 0) }")
        else:
            self.max_delay_label.setStyleSheet("")

        self.max_delay_label.setText(str(maxDelay))

    """ Show Time Since Max Delay
    """
    def showTSMD(self):
        if self.max_delay > 0:
            tsmd = round( (rospy.get_time() - self.max_delay_time_stamp), 2)
            self.TSMD_label.setText(str(tsmd))

    """ Show Value of range error
        :param status: Value out of range status
                        True : In Range
                        False : Out of range
    """
    def showValueRange(self, status):
        if status:
            self.value_range_label.setStyleSheet("QLabel { background: rgb(71, 255, 62) }")
            self.value_range_label.setText(str("OK"))
        else:
            self.value_range_label.setStyleSheet("QLabel { background: red }")
            self.value_range_label.setText(str("OOR"))


    """ 1 Hz Timer Callback
    """
    def timerCallback(self):
        # Publish Message Rate
        self.publish_rate_signal.emit()
        # Update TSMD
        self.time_since_max_delay_signal.emit()
        
        

    class ClassTimer(QThread):
        def __init__(self, callback):
            QThread.__init__(self)
            self.timer = QTimer()
            # self.timer.moveToThread(self)
            self.timer.setInterval(int(1000))
            self.timer.timeout.connect(callback)
            self.timer.start()
            

        def __del__(self):
            self.wait()

        def run(self):        
            pass