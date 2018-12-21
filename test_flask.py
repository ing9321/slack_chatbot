# -*- coding: utf-8 -*-
import csv
import json
import os
import re
import urllib.request

from datetime import date, datetime
from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template

app = Flask(__name__)

slack_token = ""
slack_client_id = ""
slack_client_secret = ""
slack_verification = ""
sc = SlackClient(slack_token)

def user_info():
    with open('user.json') as file:
        return json.loads(file.read())
def user_update(new_user):
    with open('user.json', 'w') as file:
        file.write(json.dumps(new_user))

def preprocess_cities():
    cities = []
    with open('cities.csv') as file:
        reader = csv.reader(file, delimiter=',')
        for row in reader:
            try:
                city = {
                    'name': row[0],
                    'code': row[1]
                }
            except:
                pass
            cities.append(city)
    return cities
def preprocess_departures():
    departures = []
    with open('departure.csv') as file:
        reader = csv.reader(file, delimiter=',')
        for row in reader:
            try:
                city = {
                    'name': row[0],
                    'code': row[1]
                }
            except:
                pass
            departures.append(city)
    return departures

def crawling_flights(url):
    result = []
    soup = BeautifulSoup(urllib.request.urlopen(url).read(), "html.parser")

    table = soup.find('table', id='air072_table')
    tbody = table.find('tbody')
    for i, data in enumerate(tbody.find_all('tr')):
        try:
            if i < 10:
                airline = data.find('td').get_text().split()[0]
                applyDate = data.find('span', class_='ApplyDate').get_text().strip()  # 여행기간
                arrDate = data.find('span', class_='ArrDate').get_text().strip()  # 귀국날짜
                arrDate = arrDate[:4] + '.' + arrDate[4:6] + '.' + arrDate[6:]
                depDate = data.find('span', class_='DepDate').get_text().strip()  # 출국날짜
                depDate = depDate[:4] + '.' + depDate[4:6] + '.' + depDate[6:]
                depCity = data.find('span', class_='DepCity').get_text().strip()  # 출발도시
                depCityLclName = data.find('span', class_='DepCityLclName').get_text().strip()
                arrCity = data.find('span', class_='ArrCity').get_text().strip()  # 도착도시
                arrCityLclName = data.find('span', class_='ArrCityLclName').get_text().strip()
                regionCode = data.find('span', class_='RegionCode').get_text().strip()
                mkAirCode = data.find('span', class_='MkAirCode').get_text().strip()  # 항공사코드
                via_yn = data.find('span', class_='VIA_YN').get_text().strip()  # 경유 A
                way_gb = data.find('span', class_='WAY_GB').get_text().strip()  # 왕복2/편도
                tckout_charge = data.find('span', class_='tckout_charge').get_text().strip()  # 발권이용료
                normalFare = data.find('span', class_='NormalFareAdt').get_text().strip()  # 기본가격
                dcFare = data.find('span', class_='DcFareAdt').get_text().strip()  # 할인가격
                tax = data.find('span', class_='TaxAdt').get_text().strip()  # 텍스

                result.append(str(i + 1) + '. ' + airline + ' ' + depCityLclName + '-' + arrCityLclName + ' _' + depDate + '~' + arrDate + '_ (' + applyDate + ') *' + str(format(int(dcFare) + int(tax), ',')) + '원*')
        except:
            result.append("땡처리 항공권 검색결과가 없습니다.")
    return result

def chatbot_ddaengflight(text):
    user = user_info()
    cities = preprocess_cities()
    departures = preprocess_departures()
    # 도착도시
    for city in cities:
        if city['name'] in text:
            user['arrCity'] = city['code']

    koEx = re.compile("[ㄱ-ㅎ가-힣]+")
    result = koEx.findall(text)

    if len(result) <= 0:
        return "땡처리여행봇입니다.\n현재 땡처리항공권 검색이 가능한 지역은 *방콕/대만/싱가포르/하노이/북경/상해/홍콩/도쿄/오사카/삿포로* 입니다." + \
               "\n출발 도시(인천/김포/부산/제주) 지정이 가능하며 출발 날짜 변경과 출력결과를 정렬(최근출발순/낮은가격순/높은가격순) 할 수 있습니다."

    elif '초기화' in text:
        user['depCity'] = ''
        user['arrCity'] = ''
        user['depDate'] = ''
        user['via_yn'] = ''
        user['airline'] = ''
        user['sorting'] = ''
        user_update(user)
        return '사용자 정보가 초기화되었습니다.'
    else:
        # 출발도시
        for departure in departures:
            if departure['name'] in text:
                user['depCity'] = departure['code']
        if '서울' in text:
            user['depCity'] = 'ICN%2FGMP'
        if '월' in text or '일' in text:
            # 출발일
            dep_date = [str(date.today().year), str(date.today().month), str(date.today().day)]
            compile_text = re.compile("\d+")
            if '월' in text:
                index = text.find('월')
                month = text[index - 2:index]
                month = month.strip()
                match_text = compile_text.findall(month)
                month_string = '0' + match_text[0] if int(match_text[0]) < 10 else match_text[0]
                dep_date[1] = month_string
            if '일' in text:
                index = text.find('일')
                day = text[index - 2:index]
                day = day.strip()
                match_text = compile_text.findall(day)
                day_string = '0' + match_text[0] if int(match_text[0]) < 10 else match_text[0]
                dep_date[2] = day_string
            d = ''.join(dep_date)
            formatted_date = datetime.strptime(d, '%Y%m%d').date()

            if formatted_date >= date.today():
                user['depDate'] = formatted_date.strftime('%Y-%m-%d')
            else:
                formatted_date = formatted_date.replace(formatted_date.year + 1)
                user['depDate'] = formatted_date.strftime('%Y-%m-%d')
        # 정렬
        if '낮은' in text:
            user['sorting'] = 'B'
        elif '높은' in text:
            user['sorting'] = 'C'
        elif '최근' in text:
            user['sorting'] = 'A'

        user_update(user)
        url = "http://072air.com/rn2016/air072/air072.asp?srtCity=" + user['depCity'] + "&srtDate=" + user['depDate'] + "&city_cd=" + user['arrCity'] + "&via=&trip=&sortType=" + user['sorting']
        flights = crawling_flights(url)
        return u'\n'.join(flights)


# 블로그
def dol(text):
    trip_location = makeurl(text)
    url="https://m.post.naver.com/search/post.nhn?keyword="+trip_location+"+%EC%97%AC%ED%96%89"
    req = urllib.request.Request(url)
    sourcecode = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(sourcecode, "html.parser")
    title = []
    image = []
    link = []
    for indexx, post in enumerate(soup.find_all("div", class_="inner_feed_box")):
        if indexx < 3:
            for t in post.find_all("strong", class_="tit_feed ell"):
                title.append(t.get_text().strip())
            #     블로그 제목
            for i in post.find_all("a", attrs={'class': 'link_end'}):
                link.append('https://m.post.naver.com' + i.get('href'))
            #     블로그 링크
            for img in post.find_all("div", attrs={'class': 'image_area'}):
                image.append(img.find('img')['data-src'])
            #     블로그 이미지
    return title,link,image

def makeurl(location):
    if '방콕' in location :
        return "%EB%B0%A9%EC%BD%95"
    elif '대만' in location:
        return "%EB%8C%80%EB%A7%8C"
    elif '싱가폴' in location:
        return "%EC%8B%B1%EA%B0%80%ED%8F%B4"
    elif '싱가포르' in location:
        return "%EC%8B%B1%EA%B0%80%ED%8F%AC%EB%A5%B4"
    elif '홍콩' in location:
        return "%ED%99%8D%EC%BD%A9"
    elif '하노이' in location:
        return "%ED%95%98%EB%85%B8%EC%9D%B4"
    elif '북경' in location:
        return "%EB%B6%81%EA%B2%BD"
    elif '베이징' in location:
        return "%EB%B2%A0%EC%9D%B4%EC%A7%95"
    elif '상해' in location:
        return "%EC%83%81%ED%95%B4"
    elif '상하이' in location:
        return "%EC%83%81%ED%95%98%EC%9D%B4"
    elif '도쿄' in location:
        return "%EB%8F%84%EC%BF%84"
    elif '오사카' in location:
        return "%EC%98%A4%EC%82%AC%EC%B9%B4"
    elif '삿포로' in location:
        return "%EC%82%BF%ED%8F%AC%EB%A1%9C"

def _crawl_keywords(num,title,link,image):
    atth = [{"title": title[num], "title_link": link[num], "image_url": image[num]}]
    return atth

# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):
    # print(slack_event["event"])

    if event_type == "app_mention":
        channel = slack_event["event"]["channel"]
        text = slack_event["event"]["text"]

        if '항공권' in text:
            keywords = chatbot_ddaengflight(text)
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=keywords
            )
            return make_response("App mention message has been sent", 200, )
        elif '블로그' in text:
            title, link, image = dol(text)
            for num in range(3):
                attach = _crawl_keywords(num, title, link, image)
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    # text=keywords,
                    attachments=attach
                )
            return make_response("App mention message has been sent", 200, )
        else:
            keywords = chatbot_ddaengflight(text)
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=keywords
            )
            title, link, image = dol(text)
            for num in range(3):
                attach = _crawl_keywords(num, title, link, image)
                sc.api_call(
                    "chat.postMessage",
                    channel=channel,
                    # text=keywords,
                    attachments=attach
                )
            return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/listening", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)
