from flask import Flask, request, jsonify, session, redirect, url_for, render_template
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


@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('main.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = '비밀번호가 틀렸습니다.'
    return render_template('login.html', error=error)


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
    req   = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/xml,application/xml,*/*',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Connection': 'keep-alive'
    })
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
    return [
        {
            'hblNo':    get_text(vo, 'hblNo'),
            'cargMtNo': get_text(vo, 'cargMtNo'),
            'etprDt':   get_text(vo, 'etprDt'),
            'dsprNm':   get_text(vo, 'dsprNm'),
            'shcoFlco': get_text(vo, 'shcoFlco'),
        }
        for vo in root.findall('cargCsclPrgsInfoQryVo')
    ]


def fetch_detail(carg_mt_no):
    try:
        xml  = fetch_xml({'crkyCn': API_KEY, 'cargMtNo': carg_mt_no})
        root = ET.fromstring(xml)
        vo   = root.find('cargCsclPrgsInfoQryVo')
        if vo is None:
            return {}
        return {k: get_text(vo, k) for k in ['prnm', 'shprEnNm', 'cnsgnEnNm', 'csclPrgsStts', 'msrm', 'wght', 'lodCntyCd']}
    except Exception:
        return {}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
