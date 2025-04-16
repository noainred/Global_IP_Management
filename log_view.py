from flask import Flask, render_template_string, request, abort
import os
from collections import defaultdict
import csv

app = Flask(__name__)
BASE_DIR = "/IPAM/logs"

def read_config_path():
    config_path = os.path.join(os.path.dirname(__file__), "config.txt")
    try:
        with open(config_path, "r") as f:
            for line in f:
                if line.strip().startswith("logs"):
                    return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[config.txt 읽기 실패] {e}")
    return None

    out_filename = f"parsed_{os.path.basename(original_filename).replace('-', '.')}".replace(".log", ".csv")
    out_path = os.path.join(save_dir, out_filename)
    try:
        with open(out_path, "w", newline='', encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Subnet(/24)", "IP", "OS", "Hostname"])
            for subnet, rows in grouped_rows.items():
                for row, _ in rows:
                    writer.writerow([f"{subnet}.0/24", row[0], row[1], row[2]])
        print(f"[✔] 결과 저장: {out_path}")
    except Exception as e:
        print(f"[✘] CSV 저장 실패: {e}")

class Item:
    def __init__(self, full_path, rel_path):
        self.full = full_path
        self.rel = rel_path
        self.is_dir = os.path.isdir(full_path)
        filename = os.path.basename(rel_path)
        name_only = filename.replace(".log", "")
        if not self.is_dir and filename.endswith(".log") and filename.count("-") == 3:
            self.label = name_only.replace("-", ".", 3)
        else:
            self.label = name_only

def list_directory(subpath=""):
    target_dir = os.path.join(BASE_DIR, subpath)
    items = []
    for name in sorted(os.listdir(target_dir)):
        full_path = os.path.join(target_dir, name)
        rel_path = os.path.relpath(full_path, BASE_DIR)
        items.append(Item(full_path, rel_path))
    return items

def find_ip_folder(ip):
    for root, _, files in os.walk(BASE_DIR):
        for filename in files:
            if filename.endswith(".log"):
                path = os.path.join(root, filename)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if ip in line:
                                return os.path.relpath(root, BASE_DIR)
                except:
                    continue
    return None

TEMPLATE_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DVC IP Management Service</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>.file-item { font-family: monospace; }</style>
</head>
<body class="bg-light">
<div class="container mt-4">
    <h2>DVC IP Management Service</h2>
    <form method="get" action="/">
        <div class="input-group my-3">
            <input type="text" name="ip" class="form-control" placeholder="예: 10.93.92.235" value="{{ query or '' }}">
            <button type="submit" class="btn btn-primary">IP 위치 검색</button>
        </div>
    </form>
    {% if found_path %}
        <div class="alert alert-info">
            지금 입력하신 IP는 <strong>{{ found_path }}</strong> 폴더에 저장되어 있습니다.
        </div>
    {% elif query %}
        <div class="alert alert-warning">❌ 입력하신 IP가 포함된 파일을 찾을 수 없습니다.</div>
    {% endif %}
    <h5 class="mt-4">📂 {{ current_path or '루트' }} 디렉터리</h5>
    {% if parent_path %}
        <p><a href="/browse/{{ parent_path }}" class="btn btn-outline-secondary btn-sm">⬆ 상위 폴더로</a></p>
    {% elif current_path %}
        <p><a href="/" class="btn btn-outline-secondary btn-sm">⬅ 루트로 돌아가기</a></p>
    {% endif %}
    <ul class="list-group">
        {% for item in files %}
        <li class="list-group-item file-item">
            {% if item.is_dir %}
                📁 <a href="/browse/{{ item.rel }}">{{ item.rel }}</a>
            {% else %}
                📄 <a href="/view/{{ item.rel }}">{{ item.label }}</a>
            {% endif %}
        </li>
        {% endfor %}
    </ul>
</div>
</body>
</html>
"""


TEMPLATE_VIEW = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DVC IP Management Service - {{ filename }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>.highlight { background-color: #fffbcc !important; }</style>
    <script>
    function filterTables() {
        const query = document.getElementById("search").value.toLowerCase();
        const rows = document.querySelectorAll("tbody tr");
        let firstMatch = null;
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            if (text.includes(query)) {
                row.style.display = "";
                row.classList.add("highlight");
                if (!firstMatch) firstMatch = row;
            } else {
                row.style.display = "none";
                row.classList.remove("highlight");
            }
        });
        if (firstMatch) {
            setTimeout(() => {
                firstMatch.scrollIntoView({ behavior: "smooth", block: "center" });
            }, 100);
        }
    }
    function toggleSection(id) {
        const content = document.getElementById("section-" + id);
        const btn = document.getElementById("btn-" + id);
        if (content.style.display === "none") {
            content.style.display = "block";
            btn.innerText = "▲ 접기";
        } else {
            content.style.display = "none";
            btn.innerText = "▼ 펼치기";
        }
    }
    function toggleAll(open) {
        const sections = document.querySelectorAll("[id^='section-']");
        const buttons = document.querySelectorAll("[id^='btn-']");
        sections.forEach(sec => sec.style.display = open ? "block" : "none");
        buttons.forEach(btn => btn.innerText = open ? "▲ 접기" : "▼ 펼치기");
    }
    </script>
</head>
<body class="bg-light">
<div class="container mt-4">
    <h4>📄 {{ filename }}</h4>
    <div class="d-flex gap-2 my-2">
        <input type="text" id="search" onkeyup="filterTables()" class="form-control" placeholder="IP, OS, Hostname 검색...">
        <button class="btn btn-outline-primary" onclick="toggleAll(true)">모두 펼치기</button>
        <button class="btn btn-outline-secondary" onclick="toggleAll(false)">모두 접기</button>
    </div>
    <div class="">
    {% for subnet, rows in grouped_rows.items() %}
    <div class="mb-4">
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0">🧭 {{ subnet }}.0/24</h5>
            <button class="btn btn-sm btn-outline-secondary" id="btn-{{ loop.index }}" onclick="toggleSection('{{ loop.index }}')">▼ 펼치기</button>
        </div>
        <div id="section-{{ loop.index }}" style="display: none;">
            <table class="table mt-2" style="border: 2px solid black; border-collapse: collapse;">
                <thead class="table-dark" style="border-bottom: 2px solid black;">
                    <tr style="border-bottom: 1px solid gray; background-color: #f2f2f2;"><th style="border-right: 1px solid gray;">IP</th><th style="border-right: 1px solid gray;">OS</th><th>Hostname</th></tr>
                </thead>
                <tbody>
                    {% for row, has_notuse in rows %}
                    <tr class="{% if has_notuse %}table-danger{% endif %}" style="border-bottom: 1px solid #ccc;">
                        <td style="border-right: 1px solid #ddd;">{{ row[0] }}</td>
                        <td style="border-right: 1px solid #ddd;">{{ row[1] }}</td>
                        <td>{{ row[2] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% endfor %}
</div>
    <a href="/" class="btn btn-secondary mt-3">⬅ 전체 목록</a>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    query = request.args.get("ip", "").strip()
    found_path = find_ip_folder(query) if query else None
    files = list_directory()
    return render_template_string(TEMPLATE_PAGE, query=query, found_path=found_path, files=files, current_path="", parent_path=None)

@app.route("/browse/<path:subpath>")
def browse(subpath):
    target_dir = os.path.join(BASE_DIR, subpath)
    if not os.path.isdir(target_dir):
        abort(404)
    files = list_directory(subpath)
    parent = os.path.dirname(subpath)
    query = request.args.get("ip", "").strip()
    found_path = find_ip_folder(query) if query else None
    return render_template_string(TEMPLATE_PAGE, query=query, found_path=found_path, files=files, current_path=subpath, parent_path=parent if parent != "." else "")

@app.route("/view/<path:relpath>")
def view_file(relpath):
    file_path = os.path.join(BASE_DIR, relpath)
    if not os.path.isfile(file_path):
        abort(404)

    grouped_rows = defaultdict(list)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 3:
                    ip = parts[0]
                    subnet = ".".join(ip.split(".")[:3])
                    has_notuse = "NOTuse" in line
                    grouped_rows[subnet].append((parts, has_notuse))
    except Exception as e:
        abort(500, description=f"파일 읽기 실패: {str(e)}")


    return render_template_string(TEMPLATE_VIEW, filename=relpath.replace("-", ".", 3).replace(".log", ""), grouped_rows=grouped_rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
