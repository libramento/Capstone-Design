import cv2
import os, time
import pytesseract
import sys
import pygame
import random
import numpy as np
from PIL import ImageFont, ImageDraw, Image
from pygame import mixer
from picamera.array import PiRGBArray
from picamera import PiCamera
import RPi.GPIO as g
from gtts import gTTS
from io import BytesIO
from time import sleep
import imutils
from transform import four_point_transform
from skimage.filters import threshold_local
import argparse


class OCR(): #기기의 기능을 담당하는 클래스
    def __init__(self):
        #GPIO 핀 설정
        g.setmode(g.BCM)
        self.capture_button = 24
        self.mode_exit = 23
        
        g.setup(self.capture_button, g.IN, pull_up_down=g.PUD_UP)
        g.setup(self.mode_exit, g.IN, pull_up_down=g.PUD_UP)
        
        #카메라 설정
        self.camera = PiCamera()
        self.camera.rotation = 180
        self.camera.resolution = (800, 480)
        self.camera.framerate = 30
        
        self.rawCapture = PiRGBArray(self.camera, size=(800, 480))

    def Scan(self,img): #OCR의 정확도를 높이기위해 스캔하는 함수 
        #이미지를 받아와 이미지 디워핑하여 후처리된 이미지를 리턴하는 함수
        ratio = img.shape[0] / 500.0
        orig = img.copy()
        img = imutils.resize(img, height = 500)

        edged = cv2.Canny(img, 75, 200)

        cnts = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:5]
        
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            if len(approx) == 4:                
                screenCnt = approx
                break
            else:
                print("NO EDGES")
                return img
            
        cv2.drawContours(img, [screenCnt], -1, (0, 255, 0), 2)

        warped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)
        warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
   
        winname = "Scanned"
        cv2.namedWindow(winname)  
        cv2.moveWindow(winname, 400, 20)
        winname2 = "Captured"
        cv2.namedWindow(winname2)  
        cv2.moveWindow(winname2, 0, 20)
        warped3 = cv2.resize(orig, (400, 283))
        cv2.imshow("Captured", warped3)
        warped2 = cv2.resize(warped, (400, 283))
        cv2.imshow("Scanned", warped2)
        
        cv2.waitKey(1) & 0xFF

        return warped

    def TTS(self): #이미지에서 텍스트를 추출하여 음성신호로 출력하는 함수
        # 
        for frame in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):
            img = frame.array
            winname = "Camera"
            cv2.namedWindow(winname, cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty(winname, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(winname, img)
            cv2.waitKey(1) & 0xFF
            self.rawCapture.truncate(0)
            #영상을 실시간으로 디스플레이에 출력하기 위한 구문들

            if g.input(self.capture_button) == False: #함수 실행 버튼을 누르면 OCR->TTS시작
                text = pytesseract.image_to_string(self.Scan(img), lang = 'Hangul') #OCR-tesseract
                print(text)
                
                if len(text) > 7 : #추출한 텍스트가 있을때만 TTS를 실행
                    font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
                    img = np.full((150, 600, 3), (255, 255, 255), np.uint8)
                    img = Image.fromarray(img)
                    draw = ImageDraw.Draw(img)
                    draw.text((0, 0),  text, font=font, fill=(0, 0, 0))
                    img = np.array(img)
                    winname = "text"
                    cv2.namedWindow(winname)
                    cv2.moveWindow(winname, 100, 300)
                    cv2.imshow(winname, img)
                    tts = gTTS(text, lang='ko')
                    tts.save('/home/pi/backup/text.mp3')
                    mixer.init()
                    mixer.music.load('/home/pi/backup/text.mp3')
                    mixer.music.play()
                    
                else : #추출한 텍스트가 없을 때 안내음성 출력
                    text = ('글자를 찾지못했습니다.')
                    tts = gTTS(text, lang='ko')
                    tts.save('/home/pi/backup/text.mp3')
                    mixer.init()
                    mixer.music.load('/home/pi/backup/text.mp3')
                    mixer.music.play()
                if g.input(self.capture_button) == False:
                    cv2.destroyAllWindows()
                
            elif g.input(self.mode_exit) == False: #모드변경버튼이 눌리면 함수종료
                cv2.destroyAllWindows()
                break
           

    def feautureMatching(self, img) : #데이터베이스에 저장된 이미지와 현재 캡쳐된 이미지를 비교하여 같은이미지를 찾아 리턴하는 함수
        file_list = os.listdir("/home/pi/images") #이미지 경로에서 이미지 경로 list로 저장

        i = 0
        arr = []
        
        print(file_list)
        
        for file in file_list: #데이터 베이스에 저장된 이미지 비교
            img1 = img
            img2 = cv2.imread('/home/pi/images/'+file)
            
            img1_gray = cv2.cvtColor(img1 , cv2.COLOR_BGR2GRAY)
            img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            sift = cv2.SIFT_create() #이미지 매칭에 SIFT알고리즘 사용
            kp1, des1 = sift.detectAndCompute(img1_gray, None)
            kp2, des2 = sift.detectAndCompute(img2_gray, None)

            bf = cv2.BFMatcher()
            matches = bf.knnMatch(des1, des2, k=2)
            
            good=[] #좋은 특징점을 저장하기 위한 list
           
            for m,n in matches:
                if m.distance < 0.75*n.distance:
                    good.append([m])
                
            random.shuffle(good)
            matchImage = cv2.drawMatchesKnn(img1, kp1, img2, kp2, good[:50], flags = 2, outImg = None)
            path = '/home/pi/images2'
            cv2.imwrite(os.path.join(path , file), matchImage)
            #매칭된 이미지와 캡처한이미지끼리의 같은 특징점을 선으로 이어 새로운 이미지로 저장

            arr.append([])
            arr[i].append(file) 
            arr[i].append(len(good))
            print(arr[i][0], arr[i][1])
            i+=1
            #이차원 배열을 사용하여 데이터베이스에 저장된 이미지별 캡쳐된 이미지와의 매칭된 특징점을 저장

        arr_cp = []

        for j in  range(0, 12):
            arr_cp.append([])
            arr_cp[j].append(arr[j][1])

        index_max = arr_cp.index(max(arr_cp))
        
        if arr[index_max][1] > 20:
            return arr[index_max][0]
        else:
            return 'xpage'
        #가장 많은 특징점을 가진 이미지가 유사한 이미지 이기 때문에 가장많은 특징점을 가진 이미지를 리턴
        
    def text_tts(self, page):#책의 내용을 음성으로 출력하는 함수
        #파이썬 딕셔너리를 사용하여 이미지매칭함수에서 리턴된 이미지파일 이름을 키 값으로 하여 저장된 텍스트의 내용을 TTS를 사용하여 출력
        text = {'xpage' : "저장되지 않은 페이지입니다.",
                '1-0page.png' : "표지, \n꼬마 몬스터의 바른 예절 가이드 \n글,그림: 안토아나 오레스키 \n제목: 비행기를 타면",
                '1-1page.png' : "1 페이지, \n오늘은 여행 가는 날이에요. \n옷과 크레파스, \n스케치북을 가방에 차곡차곡 넣었어요. \n비행기 티켓도 잘 챙겼지요. \n엄마, 아빠와 함께 공항에 왔어요.",
                '1-2page.png' : "2 페이지, \n나는 비행기를 탈 때 승무원 아저씨께 반갑게 인사하고 정해진 자리에 앉아요. \n등받이에 발을 올리지 않고, 남의 자리에 앉지 않아요. \n제자리에 앉으렴.",
                '1-3page.png' : "3 페이지, \n그리고 비행기 안전 교육을 집중해서 잘 들어요. \n시끄럽게 떠들거나 구명조끼를 꺼내 입고 장난치지 않지요. \n하지마!",
                '1-4page.png' : "4 페이지, \n자리에 앉아 있을 때는 항상 안전띠를 매요. \n자리에서 일어나 마음대로 돌아다니거나 뛰어다니지 않아요. \n자리에 앉아!",
                '1-5page.png' : "5 페이지, \n자리에서 조용히 만화를 보거나 색칠 놀이를 해요. \n나는 착하고 멋진 아이니까요!",
                '2-0page.png' : "표지, \n꼬마 몬스터의 바른 예절 가이드 \n글,그림: 안토아나 오레스키 \n제목: 식당에 가면",
                '2-1page.png' : "1 페이지, \n나는 털을 가지런히 빗었어요. \n깔끔하고 멋있는 옷도 입었지요. \n왜냐하면 오늘은 식당에 가서 저녁을 먹는 날이거든요!",
                '2-2page.png' : "2 페이지, \n나는 식당에 가면 항상 의자에 똑바로 앉아요. \n절대 식탁 밑으로 들어가지 않아요. \n똑바로 앉으렴!",
                '2-3page.png' : "3 페이지, \n그리고 음식이 나올 때까지 얌전히 기다려요.\n음식이 나오면 감사합니다. 하고 인사를 하지요.\n식탁 위에 올라가거나 젓가락을 콧구멍에 꽂거나 메뉴판을 서로 보겠다며 동생과 싸우지 않아요.\n얌전히 있으라니까!",
                '2-4page.png' : "4 페이지, \n음식은 숟가락이나 포크, 젓가락으로 먹어요. \n손으로 집어 먹거나 음식 대신 그릇을 먹지도 않아요. \n안 돼!",
                '2-5page.png' : "5 페이지, \n음식을 다 먹고 식당을 나설 때는 맛있게 잘 먹었습니다. 라고 인사해요. \n나는 착하고 멋진 아이니까요!"
                }
       

        font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)            
        font2 = cv2.FONT_HERSHEY_SIMPLEX           
        img = cv2.imread('/home/pi/images2/'+page)
        match = cv2.resize(img, (800, 200))
        gray=np.zeros((50, match.shape[1],3), np.uint8)
        gray[:] = (220, 220, 220)
        vcat = cv2.vconcat((gray, match))
        cv2.putText(vcat,"Captured                 Database",(0,40), font2, 1, (0,0,0))
        winname = "match"
        cv2.namedWindow(winname)
        cv2.moveWindow(winname, 0, 0)    
        cv2.imshow("match",vcat)
        #캡쳐된 이미지와 데이터베이스의 이미지를 구별하기위해 이미지위에 텍스트를 출력하는 구문
        
        txt = text.get(page)
        
        img2 = np.full((150, 800, 3), (255, 255, 255), np.uint8)
        img2 = Image.fromarray(img2)
        draw = ImageDraw.Draw(img2)
        draw.text((0, 0),  txt, font=font, fill=(0, 0, 0))
        img2 = np.array(img2)
        winname2 = "text"
        cv2.namedWindow(winname2)
        cv2.moveWindow(winname2, 0, 300)
        cv2.imshow("text", img2)
        #책의 텍스트를 화면에 출력하는 구문

        tts = gTTS(txt, lang='ko')
        tts.save('/home/pi/backup/text.mp3')
        mixer.init()
        mixer.music.load('/home/pi/backup/text.mp3')
        mixer.music.play()
        #TTS
        
    def run_book(self):#책을 읽어주는 기능을 하는 함수
        for frame in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):
            img = frame.array
            winname = "Camera"
            cv2.namedWindow(winname, cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty(winname, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(winname, img)
            cv2.waitKey(1) & 0xFF
            self.rawCapture.truncate(0)
            #영상을 실시간으로 디스플레이에 출력하기 위한 구문들
            
            if g.input(self.capture_button) == False: #함수 실행버튼이 눌리면 실행
                tts = gTTS('인식중 입니다. 잠시만 기다려주세요.', lang='ko')
                tts.save('/home/pi/backup/text.mp3')
                mixer.init()
                mixer.music.load('/home/pi/backup/text.mp3')
                mixer.music.play()
                page = self.feautureMatching(img)#이미지매칭 함수를 이용하여 같은 이미지의 찾는다.
                print(page)#찾은 이미지이름 출력
                
                if len(page) > 3 : #같은 페이지를 찾았을때만 TTS 실행
                    self.text_tts(page)#페이지의 내용을 TTS를 통해 음성 출력
                else:
                    print("일치하는 페이지가 없습니다.")
                    
            elif g.input(self.mode_exit) == False: #모드 변경 버튼을 누르면 함수 종료
                cv2.destroyAllWindows()
                break


if __name__ == '__main__':
    pass


