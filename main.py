import re
import os
import csv
import ast
import json
import mosspy
import pymongo
import requests
from pprint import pprint

client = pymongo.MongoClient()
db = client.da_database['spring97-ca3']
scores = client.da_database['spring97-ca3-scores']
problems = db.distinct('challenge')
users = db.distinct('hacker_username')
with open('config.json', 'r') as f:
    config = json.load(f)
mossServer = {}

# Set of headers from a request after login to HackerRank
# This script doesn't support automatic login to browser (yet). So you should set any request's
# headers after login here to make it able to retrieve submissions.
headers = {
    "Host": "www.hackerrank.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.hackerrank.com/contests/ut-da-spring97-ca3/challenges/da-spring97-2/submissions/code/1307528564",
    "X-CSRF-Token": "ccZ6GZpUXxEBOacTjN1yvjCy9/0FZE3tu190NAX2rfFzUZSrBQupi1ijjt8f742BqHBUGH8ATQZx5SZxNl+fsw==",
    "X-Request-Unique-Id": "1eckk0fp6",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": "hackerrank_mixpanel_token=64b69f6c-6517-406b-83b3-0048cd204876; h_r=community_home; h_l=in_app; h_v=log_in; __utma=74197771.1818293894.1524200376.1530176350.1530210593.19; __utmz=74197771.1525810345.9.4.utmcsr=cecm.ut.ac.ir|utmccn=(referral)|utmcmd=referral|utmcct=/mod/forum/discuss.php; optimizelyEndUserId=oeu1524200377524r0.6940224341179795; optimizelySegments=%7B%221709580323%22%3A%22false%22%2C%221717251348%22%3A%22ff%22%2C%221719390155%22%3A%22referral%22%2C%222308790558%22%3A%22none%22%7D; optimizelyBuckets=%7B%7D; _hp2_id.698647726=%7B%22userId%22%3A%226940524239390275%22%2C%22pageviewId%22%3A%227056858165071794%22%2C%22sessionId%22%3A%228103777451893119%22%2C%22identity%22%3Anull%2C%22trackerVersion%22%3A%224.0%22%7D; _biz_uid=2ffe511894644395ec2b72059ea8ff6a; _biz_nA=122; _biz_pendingA=%5B%5D; hacker_editor_theme=light; enableIntellisenseUserPref=true; ut-ce-da-spring97_crp=*nil*; ut-da-spring97-ca3_crp=*nil*; mp_bcb75af88bccc92724ac5fd79271e1ff_mixpanel=%7B%22distinct_id%22%3A%20%2264b69f6c-6517-406b-83b3-0048cd204876%22%2C%22%24initial_referrer%22%3A%20%22https%3A%2F%2Fwww.hackerrank.com%2Fadministration%2Fcontests%2Fedit%2F33496%2Foverview%22%2C%22%24initial_referring_domain%22%3A%20%22www.hackerrank.com%22%7D; mp_86cf4681911d3ff600208fdc823c5ff5_mixpanel=%7B%22distinct_id%22%3A%20%22162e2c4dd441870-02a44e2de1f4c-495861-13c680-162e2c4dd4614eb%22%2C%22%24initial_referrer%22%3A%20%22https%3A%2F%2Fwww.hackerrank.com%2Fadministration%2Fcontests%2Fedit%2F33496%2Foverview%22%2C%22%24initial_referring_domain%22%3A%20%22www.hackerrank.com%22%7D; default_cdn_url=hrcdn.net; _hrank_session=c4b194d8ce6acc079886885666d5e97be3e094e4aa63e844f24cc443a86dbc489cd619b6f158a26b6504821c82715ac9cc35b03d17d4130829fec6f9fd5258ef; session_id=7wpazrnf-1530173687097; cdn_url=hrcdn.net; cdn_set=true; __utmc=74197771; remember_hacker_token=BAhbCFsGaQOpCiNJIhlmNEVRWThnbDRKMzlDVkFQU1BrSAY6BkVUSSIXMTUzMDE3MzcwMy4wODYxMjgyBjsARg%3D%3D--0b19088618d0ffb29caf5013334d51af367c96cf; metrics_user_identifier=230aa9-b30006d00d5dcf5983f6d3b0b2913f257aeafd09; react_var=false__trm6; react_var2=true__trm6; web_browser_id=6212849f7c4be88d360d684d7b3c54cf; _biz_flagsA=%7B%22Version%22%3A1%2C%22XDomain%22%3A%221%22%7D",
    "Connection": "keep-alive",
}


def makeNormal(data):
    if data:
        return ast.literal_eval(json.dumps(data))
    return None


def init():
    for p in problems:
        makeDirs(p['name'])


def makeDirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def loadData(dataPath = './data.json'):
    with open(dataPath) as f:
        data = json.load(f)
        db.insert_many(data)


def getCode(submissionId):
    URL = 'https://www.hackerrank.com/rest/contests/{}/submissions/{}?&_=1530252865797'
    res = requests.get(URL.format(config['contest'], submissionId), headers=headers).json()
    return res['model']['code'].replace(u"\u2018", "'").replace(u"\u2019", "'"), res['model']['language']


def getLangExtension(language):
    if re.match('^c$', language):
        return '.c'
    if re.match('^c+', language):
        return '.cpp'
    if re.match('^java', language):
        return '.java'
    if re.match('^python', language):
        return '.py'


def findBestSubmission(user, problem):
    submission = db.find_one(
        {
            "hacker_username": user,
            "challenge": problem,
            "time_from_start": {
                "$lte": config['contestEndTime']
            }
        },
        projection={
            '_id': False,
            'id': True,
            'language': True,
            'time_from_start': True,
            'hacker_username': True,
            'score': True,
            'challenge': True,
        },
        sort=[('score', pymongo.DESCENDING), ('time_from_start', pymongo.DESCENDING)]
    )

    return submission


def saveSubmission(submission):
    challenge = submission['challenge']['name']
    username = submission['hacker_username']
    path = challenge + '/' + username + getLangExtension(submission['language'])

    with open(path, 'w') as f:
        code, language = getCode(submission['id'])
        f.write(code)


def computeScore(user):
    res = []
    for p in problems:
        s = makeNormal(findBestSubmission(user, p))
        if s:
            res.append(s['score'])
            saveSubmission(s)

    return res


def sendToMoss():
    for p in problems:
        for l in config['languages']:
            moss = mosspy.Moss(config['userid'], l)
            moss.addFilesByWildcard('./{}/*.{}'.format(p['name'], getLangExtension(l)))
            url = moss.send()
            print "Moss url: ", url
            print p['name'], l

            # Seems buggy from mosspy project
            mosspy.download_report(url, 'Plagiarism/{}/{}/'.format(p['name'], l), connections=8)

def main():
    print users
    init()
    finalResult = []
    with open(config['outputPath'], "w") as output:
        writer = csv.writer(output, lineterminator='\n')
        for u in users:
            s = computeScore(u)
            writer.writerow([u] + s)
            scores.insert_one({'username': u, 'score': s})
            finalResult.append([u] + s)
    pprint(finalResult)

    sendToMoss()


if __name__ == '__main__':
    main()
