# pyfrs()
## Python Futaba RS servo ttl control For Raspberry Pi
----------------------------------------------------
### Fuatabaのシリアルコマンドサーボ RS204MD他 を RaspberryPiから簡単に扱うクラス
- ※確認済：RS204MD、RS306MD / TTL通信
----------------------------------------------------
## 簡単な使い方例 sample
    以下のプログラムで接続、右端まで回転、左端まで回転、真ん中に戻して、終了です。
```
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
```

## 使用出来る機能
- openSerialPort()
- closeSerialPort()
- writeFlashRom()
- setReboot()
- initFactorySetting()
- setId()
- setBaudrate()
- setAngleLimit()
- setReturnDelay()
- setReverse()
- setTorque()
- setCompliance()
- setPID()
- setMaxTorque()
- setMove()
- setTempLimit()
- setTorque_multi()
- setMove_multi()

## RaspberryPiとサーボの接続
- 4番 (5V)       : RSサーボのVCCに接続（真ん中の線）
- 6番 (GND)      : RSサーボのGNDに接続（下端の線）
- 8番 (GPIO 14)  : RSサーボの信号線に接続（上端の線）
        RS204MD: GND=黒 VCC=黒 信号線=灰
        RS306MD: GND=黒 VCC=赤 信号線=赤

※ショートパケット送信・ロングパケット送信に対応/リターンパケット受信は準備中
※動作には pySerial が必要です。 >  pip install pySerial
