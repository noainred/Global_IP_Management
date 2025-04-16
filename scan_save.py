import ipaddress
import socket
import csv
import platform
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor
from pysnmp.hlapi import *

# 포트 번호와 OS 매핑
PORTS = {
    22: "Linux",
    3389: "Windows",
    10250: "Windows"
}
TIMEOUT = 1  # 포트 스캔 타임아웃 (초)

# SNMP로 호스트 이름 조회
def get_hostname_snmp(ip, community='dvcadmin'):
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),  # SNMP v2c
            UdpTransportTarget((ip, 161), timeout=1, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.2.1.1.5.0'))  # sysName
        )
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication or errorStatus:
            return "Unknown"
        for varBind in varBinds:
            return str(varBind[1])
        return "Unknown"
    except Exception:
        return "Unknown"

# ping 응답 체크
def ping_check(ip):
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(["ping", param, "1", ip],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

# 포트 및 ping 상태 확인
def check_ports_and_ping(ip):
    result = {
        "ip": ip,
        "Linux": False,
        "Windows": False,
        "hostname": "Unknown",
        "ping": False
    }

    result["ping"] = ping_check(ip)
    port_open = False

    for port, os_name in PORTS.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            try:
                s.connect((ip, port))
                if os_name == "Linux":
                    result["Linux"] = True
                elif os_name == "Windows":
                    result["Windows"] = True
                port_open = True
            except (socket.timeout, socket.error):
                continue

    if result["ping"] or port_open:
        result["hostname"] = get_hostname_snmp(ip)

    return result

# 서브넷 전체 스캔
def scan_subnet(subnet):
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        with ThreadPoolExecutor(max_workers=100) as executor:
            results = list(executor.map(check_ports_and_ping, [str(ip) for ip in network.hosts()]))
        return results
    except ValueError:
        print(f"❌ Invalid subnet: {subnet}")
        return []

# 결과 파일 이름 포맷
def format_filename(subnet):
    return subnet.replace(".", "-").replace("/", "_") + ".log"

# 결과 저장 (덮어쓰기)
def save_results(results, filename):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        for result in results:
            # 우선순위: BOTH > Linux > Windows > ping > NOTuse
            if result["Linux"] and result["Windows"]:
                os_type = "BOTH"
            elif result["Linux"]:
                os_type = "Linux"
            elif result["Windows"]:
                os_type = "Windows"
            elif result["ping"]:
                os_type = "ping"
            else:
                os_type = "NOTuse"
            writer.writerow([result["ip"], os_type, result["hostname"]])

# config.txt 파싱: logdir만 읽음
def parse_config(config_path="config.txt"):
    config = {}
    try:
        with open(config_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    config[key.strip()] = value.strip()
        if not config.get("logdir"):
            print("❌ config.txt 에 logdir 값이 없습니다.")
            exit(1)
        return config
    except FileNotFoundError:
        print("❌ config.txt 파일을 찾을 수 없습니다.")
        exit(1)

# 메인 실행
def main():
    config = parse_config()
    log_dir = config["logdir"]
    os.makedirs(log_dir, exist_ok=True)

    try:
        with open("input.txt", "r") as infile:
            for line in infile:
                subnet = line.strip()
                if subnet:
                    results = scan_subnet(subnet)
                    filename = os.path.join(log_dir, format_filename(subnet))
                    save_results(results, filename)
    except FileNotFoundError:
        print("❌ input.txt not found.")
        exit(1)

if __name__ == "__main__":
    main()
