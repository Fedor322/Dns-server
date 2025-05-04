import os
import pickle
import time


name_to_ip = {}
ip_to_name = {}

def is_expired(timestamp, ttl):
    return time.time() > timestamp + ttl

def save_cache():
    with open("cache_name_to_ip.pkl", "wb") as f:
        pickle.dump(name_to_ip, f)
        print(f"Кэш name_to_ip сохранен")
    with open("cache_ip_to_name.pkl", "wb") as f:
        pickle.dump(ip_to_name, f)
        print(f"Кэш ip_to_name сохранен")

def load_cache():
    global name_to_ip, ip_to_name
    try:
        with open("cache_name_to_ip.pkl", "rb") as f:
            name_to_ip = pickle.load(f)
        for key in list(name_to_ip.keys()):
            name_to_ip[key] = [r for r in name_to_ip[key] if not is_expired(r[2], r[1])]
            if not name_to_ip[key]:
                del name_to_ip[key]
    except FileNotFoundError:
        name_to_ip = {}
        print("Кэш name_to_ip: {}")
    try:
        with open("cache_ip_to_name.pkl", "rb") as f:
            ip_to_name = pickle.load(f)
        for key in list(ip_to_name.keys()):
            ip_to_name[key] = [r for r in ip_to_name[key] if not is_expired(r[2], r[1])]
            if not ip_to_name[key]:
                del ip_to_name[key]
    except FileNotFoundError:
        ip_to_name = {}
        print("Кэш ip_to_name: {}")




def clean_cache():
    while True:
        time.sleep(60)
        global name_to_ip, ip_to_name
        for key in list(name_to_ip.keys()):
            name_to_ip[key] = [r for r in name_to_ip[key] if not is_expired(r[2], r[1])]
            if not name_to_ip[key]:
                del name_to_ip[key]
        for key in list(ip_to_name.keys()):
            ip_to_name[key] = [r for r in ip_to_name[key] if not is_expired(r[2], r[1])]
            if not ip_to_name[key]:
                del ip_to_name[key]
        save_cache()