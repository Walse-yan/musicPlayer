from player import graphic
from PyQt5.QtWidgets import QApplication
import sys

if __name__ == '__main__':


    app = QApplication(sys.argv)
    test = graphic()
    test.run()
    test.show()
    sys.exit(app.exec_())   #退出应用