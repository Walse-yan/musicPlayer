import os
from PyQt5 import QtGui
import requests
import jsonpath as jp
from pygame import mixer
from mutagen.id3 import ID3, APIC, TIT2, TPE1    #对MP3头做操作
from mutagen.mp3 import MP3

from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QPushButton, QFileDialog
from PyQt5.QtCore import QTimer, QDir, QThread
from widget import Ui_MainWindow
import random

dir_music = './音乐下载'      #音乐文件夹
dir_img = './Image'   #图片文件夹

# 界面制作

class graphic(QMainWindow):
    def __init__(self):
        super(graphic, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("DQ播放器")
        mixer.init()  # 初始化播放器


        self.searchResult = []   #爬取下来的结果  url,作者，图片，歌词
        self.localResult = []    #本地音乐结果  path

        self.all = {}     #存放当前播放的音乐，本地音乐列表
        self.all['playing'] = []     #正在播放音乐的路径、歌名、作者名、总时长、所在列表位置, site


        self.passTimes = 0   #记录已经播放的时间
        self.rateTimer = QTimer()     #播放进度的计时器
        self.rateTimer.timeout.connect(self.controlRateMusic)    #每隔一秒触发一次

        self.showSearchList()    #初始化默认显示搜索列表
        self.ui.voiceBT.hide()
        self.ui.voiceBar.hide()


        self.searchThread = searchMusic()

    def run(self):
        self.ui.playBT.clicked.connect(self.makeMusic)
        self.ui.searchBT.clicked.connect(self.searchMusic)
        self.ui.rateBar.sliderReleased.connect(self.controlMusic)   #滑块控制音乐播放进度

        self.ui.searchList.itemClicked.connect(self.clickedSearchListItem)   #搜索列表的点击播放
        self.ui.searchResultBT.clicked.connect(self.showSearchList)   #显示搜索结果列表
        self.ui.loacalResultBT.clicked.connect(self.showLocalList)    #显示本地音乐列表

        self.ui.addLocalMusicBT.clicked.connect(self.addLocalMusic)    #添加本地音乐按钮
        self.ui.localList.itemClicked.connect(self.clickedlocalListItem)   #播放本地列表

        self.ui.lastBT.clicked.connect(self.last)   #上一首
        self.ui.nextBT.clicked.connect(self.next)   #下一首



    def download(self, url, songName, author, url_mg=None):    #返回下载后文件的路径
        os.makedirs(dir_music, exist_ok=True)  # 创建目录，如果目录存在则不理会
        path = dir_music + '/{} - {}.mp3'.format(songName, author)
        res = requests.get(url)
        if res.status_code != 200:
            print("下载失败")
            return None
        else:
            with open(path, 'wb') as f:
                # 下载音频
                f.write(res.content)
                f.flush()

                # 下载封面
                audio = ID3(path)
                if url_mg != None:
                    img = requests.get(url_mg).content
                    audio['APIC'] = APIC(
                        encodings=3,
                        mime='image/jpeg',
                        type=3,
                        desc=u'Cover',
                        data=img)
                # 插入歌名
                audio['TIT2'] = TIT2(
                    encodings=3,
                    text=songName)
                # 插入第一演奏家
                audio['TPE1'] = TPE1(
                    encodings=3,
                    text=author)
                audio.save()
                print("下载成功")
                return path

    def controlMusic(self):     #音乐条控制播放进度
        self.play(self.all['playing'][0], start= self.ui.rateBar.value())

    def controlRateMusic(self):     #播放进度控制音乐条进度
        self.passTimes += 1
        self.ui.rateBar.setValue(self.passTimes)    #获取当前播放位置

        self.ui.rateText.setText(str(self.passTimes) + ":" + str(self.all['playing'][3]))

        if not mixer.music.get_busy():   #当前没有在播放音乐
            isOK = self.next()    #播放到底了
            if not isOK: self.rateTimer.stop()    #所以停止
    def showSearchList(self):   #显示搜索结果
        self.ui.stackedWidget.setCurrentIndex(0)  # 显示搜索列表
        self.ui.addLocalMusicBT.hide()    #隐藏添加本地音乐按钮

    def showLocalList(self):    #显示本地列表
        self.ui.stackedWidget.setCurrentIndex(1)   #显示本地列表
        self.ui.addLocalMusicBT.show()

    def addLocalMusic(self):   #添加本地音乐
        curPath = QDir.currentPath()   #添加文件路径
        dlgTitle = "选择音频文件"
        filet = "音频文件(*.mp3 *.wav *.wma);"    #文件名过滤，默认只能添加mp3文件
        fileList, flt = QFileDialog.getOpenFileNames(self, dlgTitle, curPath, filet)   #一定要加一个self
        count = len(self.localResult)
        for file in fileList:
            item = QListWidgetItem()
            fileName = os.path.split(file)[1]
            item.setText(fileName)
            item.setWhatsThis(str(count))  #设置编号
            count += 1
            item.setIcon(QtGui.QIcon(dir_img + '/musicIcon.png'))  # 设置图标
            self.ui.localList.addItem(item)  # 将歌曲加入列表

            self.localResult.append(file)    #把本地音乐路径信息保存到localResult中

    def clickedlocalListItem(self, item):
        path = self.localResult[int(item.whatsThis())]  # 点击每一条音乐的结果
        print(path)
        songName, author = item.text().split(' - ')
        print('准备播放音乐', songName)

        self.all['playing'] = [path, songName, author]
        music_lenth = int(MP3(path).info.length)  # 获取音乐时长，取整

        self.all['playing'].append(music_lenth)
        self.all['playing'].append(1)
        self.all['playing'].append(int(item.whatsThis()))    #当前列表正在播放的位置

        print("音乐长度是：", music_lenth)
        self.ui.rateBar.setMaximum(self.all['playing'][3])  # 音乐长度
        self.ui.rateBar.setValue(0)  # 滑动条的起始位置
        self.play(path)  # 播放音乐

    def searchMusic(self):   #搜索歌曲，同时把结果加载在listWidget中
        songName = self.ui.searchLine.text()
        if songName == '':
            print('请输入搜索内容')
            return
        self.searchResult = self.searchThread.get_music_url(songName)   #获取歌曲的链接以及对应演唱者等
        if self.searchResult == None: return
        print('搜索音乐')
        count = 0
        self.ui.searchList.clear()   #先清空列表
        for res in self.searchResult:
            item = QListWidgetItem()
            #btn = QPushButton(songName + ' - ' + res[1])
            item.setText(songName + ' - ' + res[1])
            item.setWhatsThis(str(count))   #设置编号
            count += 1
            item.setIcon(QtGui.QIcon(dir_img + '/musicIcon.png'))   #设置图标
            self.ui.searchList.addItem(item)      #将同名歌曲加入列表

        self.showSearchList()

    def clickedSearchListItem(self, item):
        res = self.searchResult[int(item.whatsThis())]   #点击每一条音乐的结果
        songName, author = item.text().split(' - ')
        print('准备播放音乐', songName)
        path = dir_music + '/{} - {}.mp3'.format(songName, author)
        if os.path.exists(path) == False:   #还没有下载音频
            path = self.download(res[0], songName, author)  # 获取下载后保存的文件的路径
        self.all['playing'] = [path, songName, author]
        music_lenth = int(MP3(path).info.length)  # 获取音乐时长，取整

        self.all['playing'].append(music_lenth)
        self.all['playing'].append(0)    #判断当前播放的是什么列表，0表示是搜索列表
        self.all['playing'].append(int(item.whatsThis()))  # 当前列表正在播放的位置
        print("音乐长度是：", music_lenth)


        self.ui.rateBar.setMaximum(self.all['playing'][3])  # 音乐长度
        self.ui.rateBar.setValue(0) #滑动条的起始位置
        self.play(path)    #播放音乐

    def last(self):
        if self.all['playing'] != []:
            if self.all['playing'][4] == 0:
                if self.searchResult != "" and self.all['playing'][5] != 0:
                    self.ui.searchList.setCurrentRow(self.all['playing'][5] - 1)
                    self.clickedSearchListItem(self.ui.searchList.item(self.all['playing'][5] - 1))
            elif self.all['playing'][4] == 1:
                if self.localResult != "" and self.all['playing'][5] != 0:
                    self.ui.localList.setCurrentRow(self.all['playing'][5] - 1)
                    self.clickedlocalListItem(self.ui.localList.item(self.all['playing'][5] - 1))
    def next(self):
        if self.all['playing'] != []:
            if self.all['playing'][4] == 0:
                if self.searchResult != "" and self.all['playing'][5] != len(self.searchResult) - 1:
                    self.ui.searchList.setCurrentRow(self.all['playing'][5] + 1)
                    self.clickedSearchListItem(self.ui.searchList.item(self.all['playing'][5] + 1))
                    return True
            elif self.all['playing'][4] == 1:
                if self.localResult != "" and self.all['playing'][5] != len(self.localResult) - 1:
                    self.ui.localList.setCurrentRow(self.all['playing'][5] + 1)
                    self.clickedlocalListItem(self.ui.localList.item(self.all['playing'][5] + 1))
                    return True
        else: return False


    def randomPlay(self):    #随机播放
        if self.all['playing'][4] == 0:
            if self.searchResult != "":
                choose = random.randint(0, len(self.searchResult) - 1)
                self.ui.searchList.setCurrentRow(choose)
                self.clickedSearchListItem(self.ui.searchList.item(choose))
        elif self.all['playing'][4] == 1:
            if self.localResult != "":
                choose = random.randint(0, len(self.localResult) - 1)
                self.ui.localList.setCurrentRow(choose)
                self.clickedlocalListItem(self.ui.localList.item(choose))


    def makeMusic(self):   #播放，暂停，继续
        text = self.ui.playBT.text()
        if text == '播放':
            print(self.ui.stackedWidget.currentIndex())
            if self.ui.stackedWidget.currentIndex() == 0:    #当前界面在搜索列表
                if self.ui.searchList != "":   #列表不为空
                    self.ui.searchList.setCurrentRow(0)
                    self.clickedSearchListItem(self.ui.searchList.item(0))
            elif self.ui.stackedWidget.currentIndex() == 1:  #当前界面在本地列表
                if self.ui.localList != "":  # 列表不为空
                    self.ui.localList.setCurrentRow(0)
                    self.clickedlocalListItem(self.ui.localList.item(0))
        elif text == '暂停':
            self.pause()
        elif text == '继续':
            self.unpause()
    def play(self, filePath, start=0):  # 播放音乐

        mixer.music.load(filePath)
        mixer.music.play(start= start)   #从指定位置开始播放音乐

        self.ui.rateBar.setMaximum(self.all['playing'][3])  # 音乐长度
        self.ui.rateBar.setValue(start)  # 滑动条的起始位置

        self.passTimes = start   #更新当前播放时间
        self.rateTimer.start(1000)   #开始计时，1秒触发一次
        self.ui.rateText.setText(str(self.passTimes) + ":" + str(self.all['playing'][3]))

        print("播放音乐")
        self.ui.playBT.setText("暂停")
    def pause(self):  # 暂停播放
        self.rateTimer.stop()  # 进度条计时器暂停
        mixer.music.pause()
        self.ui.playBT.setText("继续")
    def unpause(self,):  # 继续播放
        mixer.music.unpause()
        self.rateTimer.start(1000)  # 重新开始计时
        self.ui.playBT.setText("暂停")


class searchMusic(QThread):
    def __init__(self):
        super().__init__()

    def run(self):    #暂时还么有实现多线程搜索
        pass

    def get_music_url(self, songName) :    #核心，爬取网络音乐
        data = {'input': songName,
                'filter': 'name',
                'type': 'kugou',
                'page': 1}
        url = "https://music.sonimei.cn/"  # 请求网址
        header = {'X-Requested-With': 'XMLHttpRequest',  # 异步请求，这个需要看一下请求格式中是否有，很重要
                  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36", }
        try:
            response = requests.post(url, data=data, headers=header)
            result = response.json()  # 得到json格式的响应
            url = jp.jsonpath(result, '$..url')  # 下载链接的列表
            author = jp.jsonpath(result, '$..author')  # 对应作者
            mag = jp.jsonpath(result, '$..pic')  # 对应图片链接
            lrc = jp.jsonpath(result, '$..lrc')  # 对应歌词
            result = []
            for ur, au, mg, l in zip(url, author, mag, lrc):
                result.append([ur, au, mg, l])  # url,作者，图片，歌词
            return result
        except:
            print("获取音乐失败,请重试")
            return None



