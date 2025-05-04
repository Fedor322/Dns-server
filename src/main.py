import socket
import sys
import threading
import time

from cache import load_cache, clean_cache, is_expired, name_to_ip, ip_to_name, save_cache
from dns_server import parse_question, parse_header, build_response, parse_records

UPS_DNS = ("8.8.8.8", 53)

def main():
    load_cache()
    threading.Thread(target=clean_cache, daemon=True).start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 53))
    sock.settimeout(5.0)

    print(f"DNS сервер запущен на порту {53}")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            header, offset = parse_header(data)
            questions, offset = parse_question(data, offset, header["qdcount"])


            name, qtype, _ = questions[0]

            if qtype in (1, 28, 2):
                key = (name, qtype)
                if key in name_to_ip:
                    valid_records = [r for r in name_to_ip[key] if not is_expired(r[2], r[1])]
                    if valid_records:
                        print("Ответ из кэша name_to_ip:", valid_records)
                        response = build_response(data, header, questions,
                                                  [(name, qtype, 1, r[1], r[0]) for r in valid_records])
                        sock.sendto(response, addr)
                        continue

            elif qtype == 12:
                ip_parts = name.split(".")[:-4]
                ip = ".".join(ip_parts[::-1])
                if ip in ip_to_name:
                    valid_records = [r for r in ip_to_name[ip] if not is_expired(r[2], r[1])]
                    if valid_records:
                        print("Ответ из кэша ip_to_name:", valid_records)
                        response = build_response(data, header, questions,
                                                  [(name, qtype, 1, r[1], r[0]) for r in valid_records])
                        sock.sendto(response, addr)
                        continue

            try:
                upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                upstream_sock.settimeout(5.0)
                upstream_sock.sendto(data, ("8.8.8.8", 53))
                response, _ = upstream_sock.recvfrom(4096)

                resp_header, offset = parse_header(response)
                _, offset = parse_question(response, offset, resp_header["qdcount"])
                answers, offset = parse_records(response, offset, resp_header["ancount"])
                authority, offset = parse_records(response, offset, resp_header["nscount"])
                additional, _ = parse_records(response, offset, resp_header["arcount"])


                for record in answers + authority + additional:
                    r_name, r_type, _, ttl, r_data = record
                    r_key = (r_name, r_type)
                    if r_type in (1, 28, 2):
                        key = (r_name, r_type)
                        if key not in name_to_ip:
                            name_to_ip[key] = []
                        name_to_ip[key].append((r_data, ttl, time.time()))
                        print(f"Добавлено в name_to_ip: {key} -> {r_data}")
                        if r_type in (1, 28):
                            if r_data not in ip_to_name:
                                ip_to_name[r_data] = []
                            ip_to_name[r_data].append((r_name, ttl, time.time()))
                            print(f"Добавлено в ip_to_name: {r_data} -> {r_name}")
                    elif r_type == 12:
                        ip_parts = r_name.split(".")[:-4]
                        ip = ".".join(ip_parts[::-1])
                        if ip not in ip_to_name:
                            ip_to_name[ip] = []
                        ip_to_name[ip].append((r_data, ttl, time.time()))
                        print(f"Добавлено в ip_to_name: {ip} -> {r_data}")
                sock.sendto(response, addr)
            except socket.timeout:
                print(f"Тайм-аут от {UPS_DNS}")
                response = build_response(data, header, questions)
                sock.sendto(response, addr)
            except Exception as e:
                print(f"Ошибка сети: {e}")
                response = build_response(data, header, questions)
                sock.sendto(response, addr)
        except KeyboardInterrupt:
            print("Остановка сервера...")
            save_cache()
            sys.exit()
        except Exception as e:
            print(f"Ошибка обработки запроса: {e}")

if __name__ == "__main__":
    main()