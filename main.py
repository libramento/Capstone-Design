import os
import cv2
import time
import sys
from picamera.array import PiRGBArray
from picamera import PiCamera
import RPi.GPIO as g
from gtts import gTTS
from ocr import OCR
from pygame import mixer

class Main():
    def __init__(self):        
        self.G_CHANGE_MODE_BUTTON = 23
        self.G_FUNCTION_BUTTON = 24

        self.setup()

    def setup(self):
        g.setmode(g.BCM)
        # 핀 입력 출력 설정
        g.setup(self.G_CHANGE_MODE_BUTTON, g.IN, pull_up_down=g.PUD_UP)
        g.setup(self.G_FUNCTION_BUTTON,g.IN, pull_up_down=g.PUD_UP)

        time.sleep(0.1)

        g.add_event_detect(self.G_CHANGE_MODE_BUTTON, g.FALLING)
        g.add_event_detect(self.G_FUNCTION_BUTTON, g.FALLING)
        
        #increase sound volume
        os.system("amixer set PCM -- 100%")

    def run(self): #프로그램을 실행하는 함수
        text = ('책을 올려주시고 오른쪽 버튼을 누르시면 책 읽기를 시작합니다. 왼쪽버튼은 모드 변경버튼 입니다.')
        print(text)
        tts = gTTS(text=text, lang='ko')
        tts.save('/home/pi/backup/text.mp3')
        mixer.init()
        mixer.music.load('/home/pi/backup/text.mp3')
        mixer.music.play()
        #음성안내 출력
        ocr_tts = OCR()
            
        while True:
            ocr_tts.run_book() #책을 읽어 주는 함수 실행
            
            #모드 변경버튼이 입력되면 다른 모드가 실행되게 if문 사용
            if g.event_detected(self.G_CHANGE_MODE_BUTTON) and g.input(self.G_CHANGE_MODE_BUTTON) == False: 
                text = ('모드가 변경되었습니다. 간단한 메모나 영수증을 올려주시고 오른쪽 버튼을 누르시면 기기가 작동됩니다.')
                print(text)
                tts = gTTS(text=text, lang='ko')
                tts.save('/home/pi/backup/text.mp3')
                mixer.init()
                mixer.music.load('/home/pi/backup/text.mp3')
                mixer.music.play()
                #음성안내 출력
                print("TTS START")
                time.sleep(0.3)
                while True:
                    ocr_tts.TTS() #간단한 메모나 영수증을 읽어주는 함수 실행
                    break
                text = ('독서 모드로 변경되었습니다.')
                print(text)
                tts = gTTS(text=text, lang='ko')
                tts.save('/home/pi/backup/text.mp3')
                mixer.init()
                mixer.music.load('/home/pi/backup/text.mp3')
                mixer.music.play()
                print("TTS STOP")
            
            time.sleep(1)


def main():
    M = Main()
    M.run()

if __name__ == '__main__':
    main()