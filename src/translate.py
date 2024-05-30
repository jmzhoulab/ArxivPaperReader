import os
import time
import json
import uuid
import hashlib
import requests


def addAuthParams(appKey, appSecret, params):
    '''Add auth params'''
    q = params.get('q')
    if q is None:
        q = params.get('img')
    q = "".join(q)
    salt = str(uuid.uuid1())
    curtime = str(int(time.time()))
    sign = calculateSign(appKey, appSecret, q, salt, curtime)
    params['appKey'] = appKey
    params['salt'] = salt
    params['curtime'] = curtime
    params['signType'] = 'v3'
    params['sign'] = sign

def calculateSign(appKey, appSecret, q, salt, curtime):
    strSrc = appKey + getInput(q) + salt + curtime + appSecret
    return encrypt(strSrc)


def encrypt(strSrc):
    hash_algorithm = hashlib.sha256()
    hash_algorithm.update(strSrc.encode('utf-8'))
    return hash_algorithm.hexdigest()


def getInput(input):
    if input is None:
        return input
    inputLen = len(input)
    return input if inputLen <= 20 else input[0:10] + str(inputLen) + input[inputLen - 10:inputLen]


def get_md5(*args, **kwargs):
    md5 = hashlib.md5()
    input_str = str(args) + str(kwargs)
    md5.update(input_str.encode('utf-8'))
    return md5.hexdigest()


class YoudaoTranslator:
    def __init__(self, api_key: str, api_secret: str, delta_t: int=5, cache_dir: str=None) -> None:
        cache_dir = cache_dir or os.getcwd()
        self._cache_file = os.path.join(cache_dir, 'translator.jsonl')
        self._latest_trans_time = time.time()
        self._cache = {}
        if os.path.exists(self._cache_file):
            for line in open(self._cache_file, encoding='utf-8'):
                if len(line.strip()) == 0:
                    continue
                item = json.loads(line)
                self._cache[item['id']] = item
        self.delta_t = delta_t
        self._api_key = api_key
        self._api_secret = api_secret

    def _cache_translate(self, uuid, item):
        item['id'] = uuid
        self._cache[uuid] = item
        with open(self._cache_file, mode='a', encoding='utf-8') as fwriter:
            fwriter.write(json.dumps(item, ensure_ascii=False)+'\n')

    def translate(self, text: str, src: str='en', dst: str='zh', domain: str='computers', **kwargs):
        # zh 默认代表简体中文
        src = 'zh-CHS' if src == 'zh' else src
        dst = 'zh-CHS' if dst == 'zh' else dst
        playload = {"q": text, "from": src, "to": dst, "domain": domain, **kwargs}
    
        uuid = get_md5(playload)
        if uuid in self._cache:
            # print("INFO:     Translate use cache")
            return self._cache[uuid]['translation']

        time_diff = time.time() - self._latest_trans_time
        if time_diff < self.delta_t:
            time.sleep(self.delta_t-time_diff)
            self._latest_trans_time = time.time()
        addAuthParams(self._api_key, self._api_secret, playload)

        header = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post('https://openapi.youdao.com/api', playload, header)
        try:
            translation = response.json()['translation'][0]
        except Exception as e:
            print(f"ERROR:    response: {response.json()}")
            if self.delta_t > 0:
                time.sleep(5*self.delta_t)
                translation = response.json()['translation'][0]
            else:
                raise Exception(e)
        item = dict(
            text=text,
            translation=translation,
            type=f"{src}2{dst}",
            domain=domain
        )
        item.update(kwargs)
        self._cache_translate(uuid=uuid, item=item)
        return translation
