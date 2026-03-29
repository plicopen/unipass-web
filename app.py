from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import urllib.request
import urllib.parse
import ssl
import xml.etree.ElementTree as ET
import time
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'unipass-secret-2026')

API_KEY  = os.environ.get('UNIPASS_API_KEY', '')
PASSWORD = os.environ.get('APP_PASSWORD', 'unipass1234')
API_BASE = 'https://unipass.customs.go.kr:38010/ext/rest/cargCsclPrgsInfoQry/retrieveCargCsclPrgsInfo'

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unipass 통관 조회</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0e17;display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:sans-serif}
.card{background:#111827;border:1px solid #1e3a5f;border-radius:12px;padding:40px;width:320px}
.badge{color:#00d4ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;display:block}
h1{color:#fff;font-size:20px;margin-bottom:24px}
label{color:#94a3b8;font-size:12px;display:block;margin-bottom:6px}
input{width:100%;background:#1a2235;border:1px solid #1e3a5f;border-radius:6px;padding:10px 13px;color:#fff;font-size:14px;outline:none;margin-bottom:16px}
input:focus{border-color:#00d4ff}
button{width:100%;background:#00d4ff;color:#000;border:none;border-radius:6px;padding:11px;font-size:14px;font-weight:700;cursor:pointer}
button:hover{background:#fff}
.err{color:#ff4560;font-size:12px;margin-bottom:12px}
</style>
</head>
<body>
<div class="card">
  <span class="badge">관세청 UNIPASS</span>
  <h1>통관 조회 시스템</h1>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="post" action="/login">
    <label for="pw">비밀번호</label>
    <input type="password" id="pw" name="password" placeholder="비밀번호 입력" autofocus>
    <button type="submit">로그인</button>
  </form>
</div>
</body>
</html>"""

MAIN_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unipass M B/L 통관 조회</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0e17;color:#e2e8f0;font-family:sans-serif;min-height:100vh}
.wrap{max-width:960px;margin:0 auto;padding:36px 20px}
.top{text-align:center;margin-bottom:32px}
.badge{color:#00d4ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;display:block;margin-bottom:10px}
h1{font-size:24px;font-weight:700;color:#fff}
h1 span{color:#00d4ff}
.logout{display:block;text-align:right;color:#4a6080;font-size:12px;text-decoration:none;margin-bottom:16px}
.logout:hover{color:#00d4ff}
.card{background:#111827;border:1px solid #1e3a5f;border-radius:8px;padding:22px;margin-bottom:20px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
.f{flex:1;min-width:160px}
.f.sm{flex:0 0 100px;min-width:100px}
label{display:block;color:#00d4ff;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}
input[type=text]{width:100%;background:#1a2235;border:1px solid #1e3a5f;border-radius:4px;padding:9px 12px;color:#e2e8f0;font-size:13px;outline:none}
input[type=text]:focus{border-color:#00d4ff}
.btn{background:#00d4ff;color:#000;border:none;border-radius:4px;padding:9px 24px;font-size:13px;font-weight:700;cursor:pointer;height:38px;white-space:nowrap}
.btn:hover:not(:disabled){background:#fff}
.btn:disabled{opacity:.5;cursor:not-allowed}
.status{display:flex;align-items:center;gap:8px;font-size:12px;color:#94a3b8;margin-bottom:14px;min-height:18px;font-family:monospace}
.dot{width:8px;height:8px;border-radius:50%;background:#4a6080;flex-shrink:0}
.dot.spin{background:#ffd700;animation:blink 1s infinite}
.dot.ok{background:#00ff88}
.dot.err{background:#ff4560}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
.meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px}
.meta-t{font-size:12px;color:#00d4ff;text-transform:uppercase;letter-spacing:1px;font-family:monospace}
.meta-n{font-size:12px;color:#94a3b8;font-family:monospace}
.meta-n span{color:#00ff88;font-weight:700}
.tw{background:#111827;border:1px solid #1e3a5f;border-radius:8px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{background:#1a2235;color:#00d4ff;font-size:11px;letter-spacing:1px;text-transform:uppercase;padding:10px 13px;text-align:left;white-space:nowrap;border-bottom:1px solid #1e3a5f;font-family:monospace}
tbody tr{border-bottom:1px solid rgba(30,58,95,.4)}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:rgba(0,212,255,.03)}
tbody td{padding:10px 13px;vertical-align:middle;white-space:nowrap}
.m{font-family:monospace;font-size:12px;color:#94a3b8}
.bd{display:inline-block;padding:2px 8px;border-radius:2px;font-size:11px;font-family:monospace}
.g{background:rgba(0,255,136,.1);color:#00ff88;border:1px solid rgba(0,255,136,.2)}
.y{background:rgba(255,215,0,.1);color:#ffd700;border:1px solid rgba(255,215,0,.2)}
.w{background:rgba(148,163,184,.1);color:#94a3b8;border:1px solid rgba(148,163,184,.2)}
.btn-csv{background:transparent;border:1px solid #1e3a5f;color:#94a3b8;border-radius:4px;padding:4px 12px;font-size:12px;cursor:pointer}
.btn-csv:hover{border-color:#00d4ff;color:#00d4ff}
.empty{padding:48px 20px;text-align:center;color:#4a6080;font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <a href="/logout" class="logout">[ 로그아웃 ]</a>
  <div class="top">
    <span class="badge">관세청 UNIPASS</span>
    <h1>M B/L <span>통관 조회</span></h1>
  </div>
  <div class="card">
    <div class="row">
      <div class="f">
        <label for="mblNo">M B/L 번호</label>
        <input type="text" id="mblNo" placeholder="예: 88400026294">
      </div>
      <div class="f sm">
        <label for="blYy">B/L 년도</label>
        <input type="text" id="blYy" placeholder="2026" maxlength="4">
      </div>
      <div>
        <label>&nbsp;</label>
        <button class="btn" id="searchBtn" onclick="doSearch()">조회</button>
      </div>
    </div>
  </div>
  <div class="status">
    <div class="dot" id="dot"></div>
    <span id="stxt">M B/L 번호를 입력 후 조회하세요</span>
  </div>
  <div id="result"></div>
</div>
<script>
var currentData = [];

function setSt(type, text) {
  document.getElementById('dot').className = 'dot ' + type;
  document.getElementById('stxt').textContent = text;
}

function doSearch() {
  var mblNo = document.getElementById('mblNo').value.trim();
  var blYy = document.getElementById('blYy').value.trim() || String(new Date().getFullYear());
  if (!mblNo) { alert('M B/L 번호를 입력해주세요.'); return; }
  document.getElementById('searchBtn').disabled = true;
  document.getElementById('result').innerHTML = '';
  setSt('spin', '조회 중... ' + mblNo + ' (' + blYy + '년)');
  fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mblNo: mblNo, blYy: blYy })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    document.getElementById('searchBtn').disabled = false;
    if (data.error) {
      setSt('err', '오류: ' + data.error);
      document.getElementById('result').innerHTML = '<div class="empty">오류: ' + data.error + '</div>';
    } else {
      currentData = data.items;
      setSt('ok', '조회 완료 — ' + data.items.length + '건');
      renderTable(data.items, mblNo);
    }
  })
  .catch(function(e) {
    document.getElementById('searchBtn').disabled = false;
    setSt('err', '네트워크 오류: ' + e.message);
  });
}

function badge(s) {
  if (!s) return '<span class="bd w">-</span>';
  if (s.indexOf('수리') >= 0 || s.indexOf('완료') >= 0 || s.indexOf('반출') >= 0) return '<span class="bd g">' + s + '</span>';
  if (s.indexOf('검사') >= 0 || s.indexOf('심사') >= 0 || s.indexOf('신고') >= 0) return '<span class="bd y">' + s + '</span>';
  return '<span class="bd w">' + s + '</span>';
}

function renderTable(items, mblNo) {
  if (!items.length) {
    document.getElementById('result').innerHTML = '<div class="empty">조회된 결과가 없습니다.</div>';
    return;
  }
  var rows = items.map(function(r, i) {
    return '<tr>' +
      '<td class="m" style="color:#4a6080">' + (i+1) + '</td>' +
      '<td class="m">' + (r.hblNo||'-') + '</td>' +
      '<td class="m" style="font-size:11px">' + (r.cargMtNo||'-') + '</td>' +
      '<td>' + (r.shprEnNm||'-') + '</td>' +
      '<td>' + (r.cnsgnEnNm||'-') + '</td>' +
      '<td><strong>' + (r.prnm||'-') + '</strong></td>' +
      '<td>' + badge(r.csclPrgsStts) + '</td>' +
      '<td>' + (r.dsprNm||'-') + '</td>' +
      '<td class="m">' + (r.etprDt||'-') + '</td>' +
      '<td>' + (r.shcoFlco||'-') + '</td>' +
    '</tr>';
  }).join('');
  document.getElementById('result').innerHTML =
    '<div class="meta">' +
      '<span class="meta-t">조회 결과 — ' + mblNo + '</span>' +
      '<div style="display:flex;gap:8px;align-items:center">' +
        '<span class="meta-n">총 <span>' + items.length + '</span>건</span>' +
        '<button class="btn-csv" onclick="exportCSV()">CSV 다운로드</button>' +
      '</div>' +
    '</div>' +
    '<div class="tw"><table>' +
      '<thead><tr>' +
        '<th>#</th><th>H B/L 번호</th><th>화물관리번호</th>' +
        '<th>송하인</th><th>수하인</th><th>품명</th>' +
        '<th>통관진행상태</th><th>도착지</th><th>입항일</th><th>항공사</th>' +
      '</tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
    '</table></div>';
}

function exportCSV() {
  if (!currentData.length) return;
  var headers = ['H BL번호','화물관리번호','송하인','수하인','품명','통관진행상태','도착지','입항일','항공사'];
  var rows = currentData.map(function(r) {
    return [r.hblNo,r.cargMtNo,r.shprEnNm,r.cnsgnEnNm,r.prnm,r.csclPrgsStts,r.dsprNm,r.etprDt,r.shcoFlco]
      .map(function(v){ return '"' + (v||'') + '"'; }).join(',');
  });
  var csv = '\uFEFF' + [headers.join(',')].concat(rows).join('\n');
  var a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  a.download = 'unipass_' + document.getElementById('mblNo').value + '.csv';
  a.click();
}

document.addEventListener('keydown', function(e) { if (e.key === 'Enter') doSearch(); });
</script>
</body>
</html>"""

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string(MAIN_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = '비밀번호가 틀렸습니다.'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/search', methods=['POST'])
def api_search():
    if not session.get('logged_in'):
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    data   = request.get_json()
    mbl_no = data.get('mblNo', '').strip()
    bl_yy  = data.get('blYy', '').strip()
    if not mbl_no:
        return jsonify({'error': 'MBL 번호를 입력해주세요.'})
    try:
        items = fetch_mbl(mbl_no, bl_yy)
    except Exception as e:
        return jsonify({'error': str(e)})
    results = []
    for item in items:
        carg_mt_no = item.get('cargMtNo', '')
        detail = fetch_detail(carg_mt_no) if carg_mt_no else {}
        results.append({
            'hblNo':        item.get('hblNo', ''),
            'cargMtNo':     carg_mt_no,
            'shprEnNm':     detail.get('shprEnNm', ''),
            'cnsgnEnNm':    detail.get('cnsgnEnNm', ''),
            'prnm':         detail.get('prnm', ''),
            'csclPrgsStts': detail.get('csclPrgsStts', ''),
            'dsprNm':       item.get('dsprNm', ''),
            'etprDt':       fmt_date(item.get('etprDt', '')),
            'shcoFlco':     item.get('shcoFlco', ''),
        })
        time.sleep(0.2)
    return jsonify({'items': results})

def fetch_xml(params):
    query = '&'.join(k + '=' + urllib.parse.quote(str(v)) for k, v in params.items())
    url   = API_BASE + '?' + query
    req   = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as res:
        return res.read().decode('utf-8')

def get_text(el, tag):
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else ''

def fmt_date(d):
    if d and len(d) == 8:
        return d[:4] + '-' + d[4:6] + '-' + d[6:8]
    return d or ''

def fetch_mbl(mbl_no, bl_yy):
    xml  = fetch_xml({'crkyCn': API_KEY, 'mblNo': mbl_no, 'blYy': bl_yy})
    root = ET.fromstring(xml)
    code = get_text(root, 'returnCode')
    if code and code != '00':
        raise Exception(get_text(root, 'returnMessage'))
    return [{'hblNo': get_text(vo,'hblNo'), 'cargMtNo': get_text(vo,'cargMtNo'),
             'etprDt': get_text(vo,'etprDt'), 'dsprNm': get_text(vo,'dsprNm'),
             'shcoFlco': get_text(vo,'shcoFlco')}
            for vo in root.findall('cargCsclPrgsInfoQryVo')]

def fetch_detail(carg_mt_no):
    try:
        xml  = fetch_xml({'crkyCn': API_KEY, 'cargMtNo': carg_mt_no})
        root = ET.fromstring(xml)
        vo   = root.find('cargCsclPrgsInfoQryVo')
        if vo is None:
            return {}
        return {k: get_text(vo, k) for k in ['prnm','shprEnNm','cnsgnEnNm','csclPrgsStts','msrm','wght','lodCntyCd']}
    except:
        return {}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

