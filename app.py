from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import urllib.request
import urllib.parse
import ssl
import xml.etree.ElementTree as ET
import time
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'unipass-secret-2026')

# 환경변수에서 설정 읽기
API_KEY   = os.environ.get('UNIPASS_API_KEY', '')
PASSWORD  = os.environ.get('APP_PASSWORD', 'unipass1234')
API_BASE  = 'https://unipass.customs.go.kr:38010/ext/rest/cargCsclPrgsInfoQry/retrieveCargCsclPrgsInfo'

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ============================================================
#  HTML 템플릿
# ============================================================
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unipass 조회 — 로그인</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0a0e17; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: 'Apple SD Gothic Neo', sans-serif; }
  .card { background: #111827; border: 1px solid #1e3a5f; border-radius: 12px; padding: 40px; width: 340px; }
  .title { color: #00d4ff; font-size: 13px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }
  h1 { color: #fff; font-size: 22px; margin-bottom: 28px; }
  label { color: #94a3b8; font-size: 12px; display: block; margin-bottom: 6px; }
  input { width: 100%; background: #1a2235; border: 1px solid #1e3a5f; border-radius: 6px; padding: 10px 14px; color: #fff; font-size: 14px; outline: none; margin-bottom: 16px; }
  input:focus { border-color: #00d4ff; }
  button { width: 100%; background: #00d4ff; color: #000; border: none; border-radius: 6px; padding: 11px; font-size: 14px; font-weight: 700; cursor: pointer; }
  button:hover { background: #fff; }
  .error { color: #ff4560; font-size: 12px; margin-bottom: 12px; }
</style>
</head>
<body>
<div class="card">
  <div class="title">관세청 · UNIPASS</div>
  <h1>통관 조회 시스템</h1>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post" action="/login">
    <label>비밀번호</label>
    <input type="password" name="password" placeholder="비밀번호 입력" autofocus>
    <button type="submit">로그인</button>
  </form>
</div>
</body>
</html>'''

MAIN_HTML = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unipass M B/L 통관 조회</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
  :root { --bg:#0a0e17; --bg2:#111827; --bg3:#1a2235; --border:#1e3a5f; --accent:#00d4ff; --green:#00ff88; --yellow:#ffd700; --red:#ff4560; --text:#e2e8f0; --text2:#94a3b8; --text3:#4a6080; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Noto Sans KR', sans-serif; min-height: 100vh; }
  body::before { content:''; position:fixed; inset:0; background-image: linear-gradient(rgba(0,212,255,.03) 1px,transparent 1px), linear-gradient(90deg,rgba(0,212,255,.03) 1px,transparent 1px); background-size:40px 40px; pointer-events:none; z-index:0; }
  .container { max-width: 960px; margin: 0 auto; padding: 40px 24px; position: relative; z-index: 1; }
  .header { text-align: center; margin-bottom: 40px; }
  .badge { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--accent); border:1px solid var(--accent); padding:3px 10px; border-radius:2px; letter-spacing:2px; margin-bottom:14px; }
  h1 { font-size:26px; font-weight:700; color:#fff; margin-bottom:6px; }
  h1 span { color:var(--accent); }
  .logout { position:absolute; top:20px; right:24px; color:var(--text3); font-size:12px; text-decoration:none; font-family:'IBM Plex Mono',monospace; }
  .logout:hover { color:var(--accent); }
  .card { background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:24px; margin-bottom:24px; position:relative; overflow:hidden; }
  .card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,transparent,var(--accent),transparent); }
  .row { display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end; }
  .field { flex:1; min-width:180px; }
  .field.sm { flex:0 0 110px; min-width:110px; }
  label { display:block; font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--accent); letter-spacing:1px; text-transform:uppercase; margin-bottom:7px; }
  input[type=text] { width:100%; background:var(--bg3); border:1px solid var(--border); border-radius:4px; padding:10px 13px; color:var(--text); font-family:'IBM Plex Mono',monospace; font-size:13px; outline:none; transition:border-color .2s; }
  input[type=text]:focus { border-color:var(--accent); }
  input[type=text]::placeholder { color:var(--text3); }
  .btn { background:var(--accent); color:#000; border:none; border-radius:4px; padding:10px 26px; font-family:'IBM Plex Mono',monospace; font-size:13px; font-weight:600; cursor:pointer; letter-spacing:1px; height:40px; transition:all .2s; white-space:nowrap; }
  .btn:hover:not(:disabled) { background:#fff; }
  .btn:disabled { opacity:.5; cursor:not-allowed; }
  .status { display:flex; align-items:center; gap:8px; font-family:'IBM Plex Mono',monospace; font-size:12px; color:var(--text2); margin-bottom:16px; min-height:20px; }
  .dot { width:8px; height:8px; border-radius:50%; background:var(--text3); flex-shrink:0; }
  .dot.loading { background:var(--yellow); animation:pulse 1s infinite; }
  .dot.ok { background:var(--green); }
  .dot.err { background:var(--red); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .meta { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px; }
  .meta-title { font-family:'IBM Plex Mono',monospace; font-size:12px; color:var(--accent); text-transform:uppercase; letter-spacing:1px; }
  .meta-count { font-family:'IBM Plex Mono',monospace; font-size:12px; color:var(--text2); }
  .meta-count span { color:var(--green); font-weight:600; }
  .table-wrap { background:var(--bg2); border:1px solid var(--border); border-radius:8px; overflow:auto; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  thead th { background:var(--bg3); color:var(--accent); font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:500; letter-spacing:1px; text-transform:uppercase; padding:11px 14px; text-align:left; white-space:nowrap; border-bottom:1px solid var(--border); }
  tbody tr { border-bottom:1px solid rgba(30,58,95,.5); transition:background .15s; }
  tbody tr:last-child { border-bottom:none; }
  tbody tr:hover { background:rgba(0,212,255,.03); }
  tbody td { padding:11px 14px; vertical-align:middle; white-space:nowrap; }
  .mono { font-family:'IBM Plex Mono',monospace; font-size:12px; color:var(--text2); }
  .badge-done { display:inline-block; padding:2px 8px; border-radius:2px; font-family:'IBM Plex Mono',monospace; font-size:11px; background:rgba(0,255,136,.12); color:var(--green); border:1px solid rgba(0,255,136,.2); }
  .badge-ing  { display:inline-block; padding:2px 8px; border-radius:2px; font-family:'IBM Plex Mono',monospace; font-size:11px; background:rgba(255,215,0,.12);  color:var(--yellow); border:1px solid rgba(255,215,0,.2); }
  .badge-etc  { display:inline-block; padding:2px 8px; border-radius:2px; font-family:'IBM Plex Mono',monospace; font-size:11px; background:rgba(148,163,184,.12); color:var(--text2);  border:1px solid rgba(148,163,184,.2); }
  .btn-csv { background:transparent; border:1px solid var(--border); color:var(--text2); border-radius:4px; padding:5px 13px; font-size:12px; cursor:pointer; transition:all .2s; font-family:'IBM Plex Mono',monospace; }
  .btn-csv:hover { border-color:var(--accent); color:var(--accent); }
  .empty { padding:50px 20px; text-align:center; color:var(--text3); font-size:13px; }
  .progress { background:var(--bg3); border-radius:4px; height:4px; margin-top:12px; overflow:hidden; display:none; }
  .progress-bar { height:100%; background:var(--accent); width:0%; transition:width .3s; }
</style>
</head>
<body>
<div class="container">
  <a href="/logout" class="logout">[ 로그아웃 ]</a>
  <div class="header">
    <div class="badge">관세청 · UNIPASS</div>
    <h1>M B/L <span>통관 조회</span></h1>
  </div>

  <div class="card">
    <div class="row">
      <div class="field">
        <label>M B/L 번호</label>
        <input type="text" id="mblNo" placeholder="예: 88400026294" />
      </div>
      <div class="field sm">
        <label>B/L 년도</label>
        <input type="text" id="blYy" placeholder="2026" maxlength="4" />
      </div>
      <div style="flex:0 0 auto;">
        <label>&nbsp;</label>
        <button class="btn" id="searchBtn" onclick="doSearch()">조회</button>
      </div>
    </div>
    <div class="progress" id="progress"><div class="progress-bar" id="progressBar"></div></div>
  </div>

  <div class="status" id="status">
    <div class="dot" id="dot"></div>
    <span id="statusText">M B/L 번호를 입력 후 조회하세요</span>
  </div>

  <div id="result"></div>
</div>

<script>
let currentData = [];

function setStatus(type, text) {
  document.getElementById('dot').className = 'dot ' + type;
  document.getElementById('statusText').textContent = text;
}

async function doSearch() {
  const mblNo = document.getElementById('mblNo').value.trim();
  const blYy  = document.getElementById('blYy').value.trim() || new Date().getFullYear();
  if (!mblNo) { alert('M B/L 번호를 입력해주세요.'); return; }

  document.getElementById('searchBtn').disabled = true;
  document.getElementById('progress').style.display = 'block';
  document.getElementById('progressBar').style.width = '30%';
  setStatus('loading', `조회 중... ${mblNo} (${blYy}년)`);
  document.getElementById('result').innerHTML = '';

  try {
    const res  = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mblNo, blYy: String(blYy) })
    });
    document.getElementById('progressBar').style.width = '100%';
    const data = await res.json();

    if (data.error) {
      setStatus('err', '오류: ' + data.error);
      document.getElementById('result').innerHTML = `<div class="empty">⚠ ${data.error}</div>`;
    } else {
      currentData = data.items;
      setStatus('ok', `조회 완료 — ${data.items.length}건`);
      renderTable(data.items, mblNo);
    }
  } catch(e) {
    setStatus('err', '네트워크 오류');
  } finally {
    document.getElementById('searchBtn').disabled = false;
    setTimeout(() => { document.getElementById('progress').style.display = 'none'; }, 500);
  }
}

function statusBadge(s) {
  if (!s) return '<span class="badge-etc">-</span>';
  if (s.includes('수리')||s.includes('완료')||s.includes('반출')) return `<span class="badge-done">${s}</span>`;
  if (s.includes('검사')||s.includes('심사')||s.includes('신고')) return `<span class="badge-ing">${s}</span>`;
  return `<span class="badge-etc">${s}</span>`;
}

function renderTable(items, mblNo) {
  if (!items.length) {
    document.getElementById('result').innerHTML = '<div class="empty">조회된 결과가 없습니다.</div>';
    return;
  }
  document.getElementById('result').innerHTML = `
    <div class="meta">
      <span class="meta-title">📦 ${mblNo} 조회 결과</span>
      <div style="display:flex;gap:8px;align-items:center;">
        <span class="meta-count">총 <span>${items.length}</span>건</span>
        <button class="btn-csv" onclick="exportCSV()">CSV 다운로드</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th><th>H B/L 번호</th><th>화물관리번호</th>
            <th>송하인</th><th>수하인</th><th>품명</th>
            <th>통관진행상태</th><th>도착지</th><th>입항일</th><th>항공사</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((r,i) => `<tr>
            <td class="mono" style="color:var(--text3)">${i+1}</td>
            <td class="mono">${r.hblNo||'-'}</td>
            <td class="mono" style="font-size:11px">${r.cargMtNo||'-'}</td>
            <td>${r.shprEnNm||'-'}</td>
            <td>${r.cnsgnEnNm||'-'}</td>
            <td><strong>${r.prnm||'-'}</strong></td>
            <td>${statusBadge(r.csclPrgsStts)}</td>
            <td>${r.dsprNm||'-'}</td>
            <td class="mono">${r.etprDt||'-'}</td>
            <td>${r.shcoFlco||'-'}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function exportCSV() {
  if (!currentData.length) return;
  const headers = ['H BL번호','화물관리번호','송하인','수하인','품명','통관진행상태','도착지','입항일','항공사'];
  const rows = currentData.map(r => [r.hblNo,r.cargMtNo,r.shprEnNm,r.cnsgnEnNm,r.prnm,r.csclPrgsStts,r.dsprNm,r.etprDt,r.shcoFlco].map(v=>`"${v||''}"`).join(','));
  const csv = '\uFEFF' + [headers.join(','), ...rows].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  a.download = `unipass_${document.getElementById('mblNo').value}.csv`;
  a.click();
}

document.addEventListener('keydown', e => { if(e.key==='Enter') doSearch(); });
</script>
</body>
</html>'''

# ============================================================
#  라우팅
# ============================================================
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

# ============================================================
#  API 함수
# ============================================================
def fetch_xml(params):
    query = '&'.join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url   = f"{API_BASE}?{query}"
    req   = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as res:
        return res.read().decode('utf-8')

def get_text(el, tag):
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else ''

def fmt_date(d):
    if d and len(d) == 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
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
        if vo is None: return {}
        return {k: get_text(vo, k) for k in ['prnm','shprEnNm','cnsgnEnNm','csclPrgsStts','msrm','wght','lodCntyCd']}
    except:
        return {}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
