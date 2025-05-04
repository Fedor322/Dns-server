import socket
import struct


def encode_name(name):
    parts = name.split(".")
    result = b""
    for part in parts:
        result += bytes([len(part)]) + part.encode("utf-8")
    result += b"\x00"
    return result

def parse_name(data, offset):
    name = []
    while True:
        length = data[offset]
        offset += 1
        if length == 0:
            break
        if length & 0xC0 == 0xC0:  # Сжатие
            pointer = struct.unpack("!H", data[offset-1:offset+1])[0] & 0x3FFF
            sub_name, _ = parse_name(data, pointer)
            name.extend(sub_name)
            offset += 1
            break
        name.append(data[offset:offset+length].decode("utf-8"))
        offset += length
    return name, offset

def parse_header(data):
    id, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", data[:12])
    return {
        "id": id,
        "flags": flags,
        "qdcount": qdcount,
        "ancount": ancount,
        "nscount": nscount,
        "arcount": arcount
    }, 12


def parse_question(data, offset, qdcount):
    questions = []
    for _ in range(qdcount):
        name_parts, new_offset = parse_name(data, offset)
        name = ".".join(name_parts)
        qtype, qclass = struct.unpack("!HH", data[new_offset:new_offset+4])
        offset = new_offset + 4
        questions.append((name, qtype, qclass))
    return questions, offset


def parse_resource_record(data, offset):
    name_parts, offset = parse_name(data, offset)
    name = ".".join(name_parts)
    rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset + 10])
    offset += 10
    rdata = data[offset:offset + rdlength]

    if rtype == 1:
        data = socket.inet_ntoa(rdata)
    elif rtype == 28:
        data = socket.inet_ntop(socket.AF_INET6, rdata)
    elif rtype in (2, 12):
        data_parts, _ = parse_name(data, offset)
        data = ".".join(data_parts)
    else:
        data = rdata.hex()

    offset += rdlength
    return (name, rtype, rclass, ttl, data), offset


def parse_records(data, offset, count):
    records = []
    for _ in range(count):
        record, new_offset = parse_resource_record(data, offset)
        records.append(record)
        offset = new_offset
    return records, offset


def build_response(query_data, header, questions, answers=None):
    flags = 0x8180
    if not answers:
        flags |= 0x0003
    qdcount = header["qdcount"]
    ancount = len(answers) if answers else 0
    print("Из кеша")
    packet = struct.pack("!HHHHHH", header["id"], flags, qdcount, ancount, 0, 0)
    packet += query_data[12:header["qdcount"] * 20 + 12]


    if answers:
        for name, rtype, rclass, ttl, data in answers:
            packet += encode_name(name)
            if rtype == 1:
                rdata = socket.inet_aton(data)
            elif rtype == 28:
                rdata = socket.inet_pton(socket.AF_INET6, data)
            else:
                rdata = encode_name(data)
            packet += struct.pack("!HHIH", rtype, rclass, ttl, len(rdata)) + rdata

    return packet


