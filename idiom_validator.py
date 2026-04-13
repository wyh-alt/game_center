import os
import sys
import json
import urllib.request
import gzip

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def load_idiom_dict():
    # 尝试从本地加载成语词典
    dict_path = get_resource_path("idioms.json")
    if os.path.exists(dict_path):
        try:
            with open(dict_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            pass
            
    print("Downloading idiom dictionary...")
    try:
        # 下载一个开源的成语词典精简版
        url = "https://raw.githubusercontent.com/pwxcoo/chinese-xinhua/master/data/idiom.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            idioms = set([item["word"] for item in data])
            
            # 保存到本地
            try:
                with open("idioms.json", "w", encoding="utf-8") as f:
                    json.dump(list(idioms), f, ensure_ascii=False)
            except:
                pass
                
            return idioms
    except Exception as e:
        print(f"Failed to download idiom dictionary: {e}")
        # fallback
        return set(["不可思议", "一鸣惊人", "人山人海", "海阔天空", "空前绝后"])

IDIOM_DICT = load_idiom_dict()

def is_valid_idiom(word):
    return word in IDIOM_DICT
