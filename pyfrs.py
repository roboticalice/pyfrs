#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
----------------------------------------------------
pyfrs()
Python Futaba RS servo ttl control For Raspberry Pi
----------------------------------------------------
Fuatabaのシリアルコマンドサーボ RS204MD他 を RaspberryPiから簡単に扱うクラス
    ※確認済：RS204MD、RS306MD / TTL通信
----------------------------------------------------
簡単な使い方例 sample
    以下のプログラムで接続、右端まで回転、左端まで回転、真ん中に戻して、終了です。

    frs = pyfrs()               #インスタンス生成
    frs.openSerialPort()        #シリアルポートを開く
    frs.setTorque(1,1)          #サーボ１をトルクON/ドール
    frs.setMove(1,1500,60)      #サーボ１を、+150.0度まで0.6秒で回転
    time.sleep(1)               #wait
    frs.setMove(1,-1500,120)    #サーボ１を、-150.0度まで1.2秒で回転
    time.sleep(2)               #wait
    frs.setMove(1,0,60)         #サーボ１を、0.0度まで0.6秒で回転
    time.sleep(1)               #wait
    frs.closeSerialPort()       #シリアルポートをクローズ

使用出来る機能
    openSerialPort()
    closeSerialPort()
    writeFlashRom()
    setReboot()
    initFactorySetting()
    setId()
    setBaudrate()
    setAngleLimit()
    setReturnDelay()
    setReverse()
    setTorque()
    setCompliance()
    setPID()
    setMaxTorque()
    setMove()
    setTempLimit()
    setTorque_multi()
    setMove_multi()

RaspberryPiとサーボの接続
    4番 (5V)       : RSサーボのVCCに接続（真ん中の線）
    6番 (GND)      : RSサーボのGNDに接続（下端の線）
    8番 (GPIO 14)  : RSサーボの信号線に接続（上端の線）
        RS204MD: GND=黒 VCC=黒 信号線=灰
        RS306MD: GND=黒 VCC=赤 信号線=赤

※ショートパケット送信・ロングパケット送信に対応/リターンパケット受信は準備中
※動作には pySerial が必要です。 >  pip install pySerial
'''

__author__ = "RoboticAlice"
__version__ = "0.0.1"
__date__    = "30 November 2019"


import time
import serial

class pyfrs(object):
    '''
    class pyfrs()
    Python Futaba RS servo Control For Raspberry Pi

    '''
    def __init__(self):
        '''
        __init__

        Parameters
        ----------
        なし
        '''
        self.ser = serial.Serial()

    def openSerialPort(self, port = '/dev/serial0', baudrate = 115200, timeout = 0.1 ):
        '''
        シリアルポートをオープン

        Parameters
        ----------
        port :  string
            シリアルポートを指定
        baudrate : int
            ボーレートを指定
        timeout : float
            タイムアウト値を指定

        Returns
        ----------
        True : オープンに成功
        False : オープンに失敗
        '''
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.timeout = timeout
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        try :
            self.ser.open()
        except IOError :
            return False
        else :
            return True

    def closeSerialPort(self):
        '''
        シリアルポートをクローズ

        Returns
        ----------
        True : オープンに成功
        False : オープンに失敗
        '''
        try :
            self.ser.close()
        except IOError :
            return False
        else :
            return True

    def _getChecksum(self, buf):
        '''
        書き込み用bytearrayのチェックサムを取得

        Parameters
        ----------
        buf :  bytearray
            チェックサムを計算する書き込み用bytearray

        Returns
        ----------
        sum : int
            チェックサムの値（3バイト目から最終バイトまでのxor）
        '''
        sum = buf[2]
        for i in range(3, len(buf)):
            sum = sum ^ buf[i]
        return sum

    def _makeShortPacket(self, id, flags, addr, data, length):
        '''
        ショートパケットを作成

        Parameters
        ----------
        id : int
            サーボidの指定 1-127
        flags : int
            フラグの指定
        addr : int
            アドレスの指定
        data : int or List
            データの指定
        length : int
            データ長さの指定

        Returns
        ----------
        True : ショートパケットの作成に成功
        self.sendData : 作成されたパケットデータ bytearray
        '''
        self.sendData = bytearray([
            0xFA,0xAF,   #0-1 Header FAAF固定
            id & 0xff,     #2 サーボID
            flags & 0xff,  #3 Flags
            addr & 0xff,   #4 Address メモリーマップ上のアドレス
            length & 0xff, #5 Length データのバイト数
            0x01,   #6 Count サーボの数 default=1
        ])
        if ( (flags & 0xF0) != 0x00 ) or ( (flags & 0x0F) == 0x0F) :        #6 Count サーボの数
            self.sendData[6] = 0            # FlashROM書き込み時、サーボ再起動時、FactoryReset時、指定アドレスから読み込み時の場合、Countを0セット
        if length > 0 :        #7 Dataのセット
            if length == 1 :
                self.sendData.append( data & 0xff )
            else :
                for d in data :
                    self.sendData.append(d)
        self.sendData.append(self._getChecksum(self.sendData))        #8 CheckSumのセット
        return True

    def _makeLongPacket(self, addr, length, count, data):
        '''
        ロングパケットを作成

        Parameters
        ----------
        addr : int
            アドレスの指定
        length : int
            1件のデータ長さの指定
        count : int
            サーボ個数の指定
        data : list
            データの指定

        Returns
        ----------
        1: bool : True : ロングパケットの作成に成功
        self.sendData : 作成されたパケットデータ bytearray
        '''
        self.sendData = bytearray([
            0xFA,0xAF,   #0-1 Header FAAF固定
            0x00,   #2 サーボID longPacketだと常に0
            0x00,   #3 Flags  longPacketだと常に0
            addr & 0xff,   #4 Address メモリーマップ上のアドレス
            length & 0xff, #5 Length データのバイト数
            count & 0xff,   #6 Count サーボの数
        ])
        if (length * count) > 0 :
            if (length * count) == 1 :
                self.sendData.append( data & 0xff )
            else :
                for d in data :
                    self.sendData.append(d)
        self.sendData.append(self._getChecksum(self.sendData))
        return True

    def _sendPacket(self):
        '''
        パケットを送信する

        Parameters
        ----------
        なし

        Returns
        ----------
        1 : bool 送信できたか(True or False)
        2 : int 送信出来たバイト数

        '''
        try :
            bytes = self.ser.write(bytearray(self.sendData))
        except SerialTimeoutException :
            return False,bytes
        else :
            self.ser.flush()
        return True,bytes

    def _readPacket(self):
        '''
        リターンパケットを読み込む
        ※実装予定
        '''
        return


    def writeFlashRom(self, id):
        '''
        指定サーボのFlashROMに書き込む(addr 4～29)

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x40, 0xFF, 0, 0)
        self._sendPacket()

    def setReboot(self, id):
        '''
        指定サーボを再起動する

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x20, 0xFF, 0, 0)
        self._sendPacket()

    def initFactorySetting(self, id):
        '''
        指定サーボを工場出荷時の状態に戻す

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x10, 0xFF, 0, 0)
        self._sendPacket()

    def setId(self, id, newId ):
        '''
        指定サーボIDを設定する
            ※トルクOFF時のみ変更可能

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        newId : int
            新しいサーボIDを指定 1-127

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x04, newId & 0xff, 1)
        self._sendPacket()
        self._readPacket()

    def setReverse(self, id, rev = 0x00 ):
        '''
        指定サーボのリバース値を設定する
            ※トルクOFF時のみ変更可能

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        rev : int
            リバース値を指定 0=正転 1=反転

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x05, rev & 0xff, 1)
        self._sendPacket()
        self._readPacket()

    def setBaudrate(self, id, brate = 0x07 ):
        '''
        指定サーボの通信速度値を設定する

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        brate : int
            通信速度値の指定
            0: 9600bps
            1: 14400bps
            2: 19200bps
            3: 28800bps
            4: 38400bps
            5: 57600bps
            6: 76800bps
            7: 115200bps
            8: 153600bps
            9: 230400bps

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x06, brate & 0xff, 1)
        self._sendPacket()
        self._readPacket()

    def setReturnDelay(self, id, rdelay = 0x00 ):
        '''
        指定サーボの返信ディレイ時間を設定する
            ※トルクOFF時のみ変更可能

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        rdelay : int
            返信ディレイ時間を指定

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x07, rdelay & 0xff, 1)
        self._sendPacket()
        self._readPacket()

    def setAngleLimit(self, id, cwLimit = 0x05DC , ccwLimit = 0xFA24 ) :
        '''
        指定サーボのリミット角度を設定する
            ※トルクOFF時のみ変更可能

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        cwLimit : int
            時計回りのリミット角度を指定 0～-1500
        ccwLimit : int
            反時計回りのリミット角度を指定 0～-1500

        Returns
        ----------
        なし
        '''
        dat = bytearray([
            cwLimit & 0x00FF,
            (cwLimit >> 8) & 0x00FF,
            ccwLimit & 0x00FF,
            (ccwLimit >> 8) & 0x00FF
        ])
        self._makeShortPacket(id, 0x00, 0x08, dat, 4)
        self._sendPacket()
        self._readPacket()

    def setTempLimit(self, id, tempLimit = 0x0037 ) :
        '''
        指定サーボの温度リミットを設定する

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        tempLimit : int
            リミット温度値を指定

        Returns
        ----------
        なし
        '''
        dat = bytearray([
            tempLimit & 0x00FF,
            (tempLimit >> 8) & 0x00FF,
        ])
        self._makeShortPacket(id, 0x00, 0x0E, dat, 2)
        self._sendPacket()
        self._readPacket()

    def setCompliance(self, id, margin_cw = 0x02, margin_ccw = 0x02, slope_cw = 0x01, slope_ccw = 0x01, punch = 0x0008):
        '''
        指定サーボのコンプライアンス　マージン値、スロープ値、パンチ値を設定する

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        margin_cw : byte
            時計回りのコンプライアンスマージン値を指定 0-255
        margin_ccw : byte
            反時計回りのコンプライアンスマージン値を指定 0-255
        slope_cw : byte
            時計回りのコンプライアンススロープ値を指定 0-255
        slope_ccw : byte
            反時計回りのコンプライアンススロープ値を指定 0-255
        punch : int
            パンチの値を指定 0-255

        Returns
        ----------
        なし
        '''
        dat = bytearray([
            margin_cw & 0xff,
            margin_ccw & 0xff,
            slope_cw & 0xff,
            slope_ccw & 0xff,
            punch & 0x00FF,
            (punch >> 8) & 0x00FF
        ])
        self._makeShortPacket(id, 0x00, 0x18, dat, 6)
        self._sendPacket()
        self._readPacket()

    def setMove(self, id, pos = 0x00, tim = 0x00) :
        '''
        指定サーボの目標位置、時間の設定

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        pos : int
            回転目標位置の指定 -1500～0～1500
            -150.0度から+150.0度までを指定できる。
        tim : int
            サーボ移動時間の指定 0～0x3fff
                1=10ms ex)1秒で移動したい場合は 100(0x64)を指定

        Returns
        ----------
        なし
        '''
        dat = bytearray([
            pos & 0x00FF,
            (pos >> 8) & 0x00FF,
            tim & 0x00FF,
            (tim >> 8) & 0x00FF
        ])
        self._makeShortPacket(id, 0x00, 0x1E, dat, 4)
        self._sendPacket()
        self._readPacket()

    def setMaxTorque(self,id,maxTorque = 0x64):
        '''
        指定サーボの最大トルク値の設定

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        maxTorque : byte
            サーボの最大出力トルクを指定 0～100(0x64)
                1%刻みで設定、100の時に100%

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x23, maxTorque, 1)
        self._sendPacket()
        self._readPacket()


    def setTorque(self,id,torque = 0x00 ):
        '''
        指定サーボのトルクon/off値の設定

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        torque : bytes
            トルクのon/offを指定
            0:トルクoff
            1:トルクon
            2:ブレーキモード(弱トルク発生)

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x24, torque, 1)
        self._sendPacket()
        self._readPacket()

    def setPID(self,id,pid = 0x64):
        '''
        指定サーボのPID値の設定

        Parameters
        ----------
        id : int
            サーボIDを指定 1-127
        pid : byte
            モータの制御係数を指定 1-255(0xff)

        Returns
        ----------
        なし
        '''
        self._makeShortPacket(id, 0x00, 0x26, pid, 1)
        self._sendPacket()
        self._readPacket()

    def setTorque_multi(self,dat):
        '''
        複数サーボのトルクのon/offの一括設定

        Parameters
        ----------
        dat : list
            複数サーボの値指定をlistで行います。
            dat = [
                id1 , torque1,
                id2 , torque2,
                id3 , torque3,
                …
            ]
            -------
            id : サーボIDを指定 1-127
            torque : トルクのon/offを指定 0/1/2

        Returns
        ----------
        なし
        '''
        addr = 0x24
        length = 2
        count = int(len(dat)/2)
        _cnt = 0
        _dat = bytearray()
        while (len(dat) > _cnt) :
            _dat.append(dat[_cnt] & 0xff)
            _cnt += 1
            _dat.append(dat[_cnt] & 0xff)
            _cnt += 1
        self._makeLongPacket(addr, length , count ,  _dat)
        self._sendPacket()

    def setMove_multi(self,dat):
        '''
        複数サーボの目標位置、時間の一括設定
        Parameters
        ----------
        dat : list
            複数サーボの値指定をlistで行います。
            dat = [
                id1 , pos1, tim1,
                id2 , pos2, tim2,
                id3 , pos3, tim3,
                …
            ]
            -------
            id : サーボIDを指定 1-127
            pos : 回転目標位置の指定 -1500～0～+1500
            tim : 移動時間の指定 0-0x3fff

        Returns
        ----------
        なし
        '''
        addr = 0x1E
        length = 5
        count = int(len(dat)/3)
        _cnt = 0
        _dat = bytearray()
        while (len(dat) > _cnt) :
            _dat.append(dat[_cnt])
            _cnt += 1
            _dat.append(dat[_cnt] & 0xff)
            _dat.append((dat[_cnt] >> 8) & 0xff)
            _cnt += 1
            _dat.append(dat[_cnt] & 0xff)
            _dat.append((dat[_cnt] >> 8) & 0xff)
            _cnt += 1
        self._makeLongPacket(addr, length , count ,  _dat)
        self._sendPacket()

def main():
    frs = pyfrs()
    if frs.openSerialPort('/dev/serial0', 115200, 0.1) :
        frs.writeFlashRom(1)
        frs.setReboot(1)
        frs.initFactorySetting(1)
        frs.setId(1,1)
        frs.setBaudrate(1, 0x07 )
        frs.setAngleLimit(1, 0x05DC , 0xFA24 )
        frs.setReturnDelay(1, 0x00 )
        frs.setReverse(1, 0x00 )
        frs.setTorque(1,1)
        frs.setCompliance(1, 0x02, 0x02, 0x01, 0x01, 0x0008)
        frs.setPID(1,0x64)
        frs.setMaxTorque(2,0x64)
        frs.setTempLimit(3,0x0037)
        te_dat = [ 1,1, 2,1, 3,1 ]
        frs.setTorque_multi(te_dat)
        mv1_dat = [ 1,1500,40, 2,1500,40, 3,1500,40 ]
        frs.setMove_multi(mv1_dat)
        time.sleep(0.6)
        frs.setMove(1,-1500, 80)
        frs.setMove(2,-1500, 80)
        frs.setMove(3,-1500, 80)
        time.sleep(1.2)
        mv2_dat = [ 1,0,40, 2,0,40, 3,0,40]
        frs.setMove_multi(mv2_dat)
        time.sleep(0.6)
        te2_dat = [ 1,0, 2,0, 3,0 ]
        frs.setTorque_multi(te2_dat)
    frs.closeSerialPort()

if __name__ == '__main__':
    main()
