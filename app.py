# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import math, datetime, os, requests

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════
# SERVE STATIC FILES
# ═══════════════════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'tool.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)

# ═══════════════════════════════════════════════════════════
# HẰNG SỐ
# ═══════════════════════════════════════════════════════════
DIA_CHI   = ["Tý","Sửu","Dần","Mão","Thìn","Tỵ","Ngọ","Mùi","Thân","Dậu","Tuất","Hợi"]
THIEN_CAN = ["Giáp","Ất","Bính","Đinh","Mậu","Kỷ","Canh","Tân","Nhâm","Quý"]

NGU_HANH_CUC = {2:"Thủy nhị cục", 3:"Mộc tam cục",
                4:"Kim tứ cục",  5:"Thổ ngũ cục", 6:"Hỏa lục cục"}

BANG_CUC = {
    0: {0:2, 1:6, 2:5, 3:3, 4:4},
    1: {0:6, 1:5, 2:3, 3:4, 4:2},
    2: {0:3, 1:4, 2:2, 3:6, 4:5},
    3: {0:5, 1:3, 2:4, 3:2, 4:6},
    4: {0:4, 1:2, 2:6, 3:5, 4:3},
}

CAN_NHOM = [0,1,2,3,4,0,1,2,3,4]

def chi_nhom(chi):
    if chi in [0,1]:       return 0
    if chi in [2,3,10,11]: return 1
    if chi in [4,5]:       return 2
    if chi in [6,7]:       return 3
    if chi in [8,9]:       return 4
    return 0

# ═══════════════════════════════════════════════════════════
# CHUYỂN ĐỔI DƯƠNG LỊCH → ÂM LỊCH
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
# CHUYỂN ĐỔI DƯƠNG LỊCH → ÂM LỊCH
# Thuật toán: Hồ Ngọc Đức (lichviet.net) — chuẩn lịch VN
# Không dùng ephem, dùng công thức thiên văn thuần toán
# Timezone: UTC+7 (Việt Nam), kinh tuyến 105°E
# ═══════════════════════════════════════════════════════════

def _jd_from_date(Y, M, D):
    if M <= 2:
        Y -= 1; M += 12
    A = int(Y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (Y + 4716)) + int(30.6001 * (M + 1)) + D + B - 1524

def _new_moon(k, tz=7):
    """Tính JD nguyên của trăng mới thứ k theo giờ địa phương.
    Công thức Hồ Ngọc Đức — chuẩn lịch VN.
    """
    T  = k / 1236.85
    T2 = T * T
    T3 = T2 * T
    dr = math.pi / 180
    jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    jd1 += 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    M1  = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F   = 21.2964  + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
    C1  = (0.1734 - 0.000393 * T) * math.sin(M1 * dr)
    C1 += 0.0021 * math.sin(2 * dr * M1)
    C1 -= 0.4068 * math.sin(Mpr * dr)
    C1 += 0.0161 * math.sin(2 * dr * Mpr)
    C1 -= 0.0004 * math.sin(3 * dr * Mpr)
    C1 += 0.0104 * math.sin(2 * dr * F)
    C1 -= 0.0051 * math.sin((M1 + Mpr) * dr)
    C1 -= 0.0074 * math.sin((M1 - Mpr) * dr)
    C1 += 0.0004 * math.sin((2 * F + M1) * dr)
    C1 -= 0.0004 * math.sin((2 * F - M1) * dr)
    C1 -= 0.0006 * math.sin((2 * F + Mpr) * dr)
    C1 += 0.0010 * math.sin((2 * F - Mpr) * dr)
    C1 += 0.0005 * math.sin((M1 + 2 * Mpr) * dr)
    deltat = 65.0 / 86400 if T < -11 else (-0.000278 + 0.000265 * T + 0.000262 * T2)
    jdNew  = jd1 + C1 - deltat
    return math.floor(jdNew + tz / 24.0 + 0.5)

def _sun_longitude(jdn, tz=7):
    """Trả về cung hoàng đạo (0-11) của mặt trời tại JD.
    Mỗi cung 30°. Dùng để xác định tháng nhuận (tháng không chứa trung khí).
    """
    T  = (jdn - tz / 24.0 - 2451545.0) / 36525.0
    dr = math.pi / 180
    M  = 357.52910 + 35999.05030 * T - 0.0001559 * T * T - 0.00000048 * T * T * T
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    DL = (1.914600 - 0.004817 * T - 0.000014 * T * T) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(2 * dr * M)
    DL += 0.000290 * math.sin(3 * dr * M)
    L  = L0 + DL
    omega = 125.04 - 1934.136 * T
    L     = L - 0.00569 - 0.00478 * math.sin(omega * dr)
    L     = L * dr
    L     = L - math.pi * 2 * math.floor(L / (math.pi * 2))
    return int(L / math.pi * 6)

def _get_lunar_month11(yy, tz=7):
    """JD của mùng 1 tháng 11 âm lịch năm yy (tháng chứa Đông chí, sun_lon=9).
    Đây là điểm neo để đánh số tháng âm lịch.
    """
    off = _jd_from_date(yy, 12, 31) - 2415021
    k   = int(off / 29.530588853)
    nm  = _new_moon(k, tz)
    if _sun_longitude(nm, tz) >= 9:
        nm = _new_moon(k - 1, tz)
    return nm

def _find_leap_month(k_start, n_months, tz=7):
    """Tìm vị trí tháng nhuận (0-based) trong chuỗi n_months tháng từ k_start.
    Tháng nhuận = tháng đầu tiên trong cặp liên tiếp cùng sun_longitude.
    Trả về -1 nếu không có.
    """
    for i in range(n_months):
        nm_cur  = _new_moon(k_start + i,     tz)
        nm_next = _new_moon(k_start + i + 1, tz)
        if _sun_longitude(nm_cur, tz) == _sun_longitude(nm_next, tz):
            return i
    return -1

def duong_sang_am(sy, sm, sd, tz=7):
    """Chuyển đổi ngày dương lịch sang âm lịch Việt Nam.
    Thuật toán Hồ Ngọc Đức — chuẩn lịch VN.
    Trả về: (am_year, lunar_month, am_day, is_leap_month)
    """
    jd  = _jd_from_date(sy, sm, sd)
    a11 = _get_lunar_month11(sy - 1, tz)
    b11 = _get_lunar_month11(sy,     tz)
    leap_year = (b11 - a11) > 365

    # Tìm k và nm của tháng chứa ngày jd
    k  = int((jd - 2415021.076998695) / 29.530588853)
    nm = _new_moon(k, tz)
    if nm > jd:
        nm = _new_moon(k - 1, tz); k -= 1
    elif jd - nm >= 29:
        nm_next = _new_moon(k + 1, tz)
        if nm_next <= jd:
            nm = nm_next; k += 1

    am_day = int(jd - nm + 1)

    # Tìm k_a11 chính xác
    k_a11 = int((a11 - 2415021.076998695) / 29.530588853)
    if   _new_moon(k_a11 - 1, tz) == a11: k_a11 -= 1
    elif _new_moon(k_a11 + 1, tz) == a11: k_a11 += 1
    elif _new_moon(k_a11 + 2, tz) == a11: k_a11 += 2
    elif _new_moon(k_a11 - 2, tz) == a11: k_a11 -= 2

    month_offset = k - k_a11

    is_leap_month = False
    if leap_year:
        leap_idx = _find_leap_month(k_a11, 13, tz)
        if leap_idx >= 0:
            if month_offset == leap_idx:
                is_leap_month = True
                month_offset -= 1
            elif month_offset > leap_idx:
                month_offset -= 1

    lunar_month = (month_offset + 11 - 1) % 12 + 1
    am_year = sy - 1 if month_offset <= 1 else sy

    return int(am_year), int(lunar_month), int(am_day), is_leap_month

# ═══════════════════════════════════════════════════════════
# HÀM TIỆN ÍCH TỬ VI
# ═══════════════════════════════════════════════════════════
def can_nam(y):    return (y + 6) % 10
def chi_nam(y):    return (y + 8) % 12

def gio_to_chi(h):
    return ((h + 1) % 24) // 2

def ngay_am_lich_cho_gio(sy, sm, sd, gio_h, tz=7):
    if gio_h >= 23:
        ngay_dt = datetime.date(sy, sm, sd) + datetime.timedelta(days=1)
        return duong_sang_am(ngay_dt.year, ngay_dt.month, ngay_dt.day, tz)
    else:
        return duong_sang_am(sy, sm, sd, tz)

def tinh_cuc(can_n, chi_menh):
    nc   = CAN_NHOM[can_n]
    nchi = chi_nhom(chi_menh)
    return BANG_CUC[nchi][nc]

def vi_tri_menh(thang, chi_gio):
    return (2 + (thang - 1) - chi_gio + 24) % 12

def vi_tri_than(thang, chi_gio):
    return (2 + (thang - 1) + chi_gio) % 12

def can_thang_dan(cn):
    return [2, 4, 6, 8, 0, 2, 4, 6, 8, 0][cn]

def can_cung(can_dan, buoc):
    return (can_dan + buoc) % 10

def ten_can_chi_cung(can_dan, vi_tri):
    buoc = (vi_tri - 2 + 12) % 12
    return f"{THIEN_CAN[can_cung(can_dan, buoc)]} {DIA_CHI[vi_tri]}"

# ═══════════════════════════════════════════════════════════
# AN TỬ VI
# ═══════════════════════════════════════════════════════════
def an_tu_vi(ngay, cuc_val):
    d, c = ngay, cuc_val
    bu = 0
    while (d + bu) % c != 0:
        bu += 1
    thuong = (d + bu) // c
    vt = (2 + thuong - 1) % 12
    if bu % 2 != 0:
        vt = (vt - bu + 120) % 12
    else:
        vt = (vt + bu) % 12
    return vt

def an_14_chinh_tinh(vt_tuvi, vt_thienphy, sc):
    for off, ten in [(0,"Tử Vi"),(-1,"Thiên Cơ"),(-3,"Thái Dương"),
                     (-4,"Vũ Khúc"),(-5,"Thiên Đồng"),(-8,"Liêm Trinh")]:
        sc[(vt_tuvi + off + 120) % 12].append({"ten": ten, "loai": "chinh"})
    for off, ten in [(0,"Thiên Phủ"),(1,"Thái Âm"),(2,"Tham Lang"),
                     (3,"Cự Môn"),(4,"Thiên Tướng"),(5,"Thiên Lương"),
                     (6,"Thất Sát"),(10,"Phá Quân")]:
        sc[(vt_thienphy + off) % 12].append({"ten": ten, "loai": "chinh"})

def an_phu_tinh(thang, chi_gio, sc):
    ta_phu    = (4  + thang - 1) % 12
    huu_bat   = (10 - thang + 1 + 120) % 12
    van_xuong = (10 - chi_gio + 120) % 12
    van_khuc  = (4  + chi_gio) % 12
    sc[ta_phu].append({"ten":"Tả Phụ",      "loai":"phu"})
    sc[huu_bat].append({"ten":"Hữu Bật",    "loai":"phu"})
    sc[van_xuong].append({"ten":"Văn Xương", "loai":"phu"})
    sc[van_khuc].append({"ten":"Văn Khúc",  "loai":"phu"})

# ═══════════════════════════════════════════════════════════
# ĐẠI HẠN & TIỂU HẠN
# ═══════════════════════════════════════════════════════════
def tinh_dai_han(vi_menh, cn, gioi_tinh, cuc_val, nam_sinh):
    can_duong = (cn % 2 == 0)
    nam = gioi_tinh.lower() in ["nam","male","m"]
    thuan = (nam and can_duong) or (not nam and not can_duong)
    dai_han = []
    for i in range(12):
        cung = (vi_menh + (i if thuan else -i) + 120) % 12
        tb = cuc_val + i * 10
        dai_han.append({
            "thu": i+1, "cung": cung, "diaChi": DIA_CHI[cung],
            "tuoiBatDau": tb, "tuoiKetThuc": tb+9,
            "namBatDau": nam_sinh+tb, "namKetThuc": nam_sinh+tb+9,
        })
    return dai_han, thuan

def tinh_tieu_han(gioi_tinh, nam_sinh, so_nam=30):
    nam = gioi_tinh.lower() in ["nam","male","m"]
    khoi = 2 if nam else 8
    return [{"nam": nam_sinh+i, "tuoi": i, "cung": (khoi+i)%12,
             "diaChi": DIA_CHI[(khoi+i)%12]} for i in range(so_nam)]

# ═══════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════
@app.route('/api/lap-laso', methods=['POST'])
def lap_laso():
    data      = request.json or {}
    ho_ten    = data.get('hoTen', '')
    gioi_tinh = data.get('gioiTinh', 'nam')
    gio_str   = data.get('gioSinh', '00:30')
    lich_loai = data.get('lichLoai', 'duong')
    ngay_sinh = data.get('ngaySinh', '')
    mui_gio   = float(data.get('muiGio', 7))
    thanh_pho = data.get('thanhPho', '')
    quoc_gia  = data.get('quocGia', '')

    if not ngay_sinh:
        return jsonify({"status":"error","message":"Vui lòng nhập ngày sinh!"})
    try:
        sy, sm, sd = map(int, ngay_sinh.split('-'))
        gio_h = int(gio_str.split(':')[0])
    except:
        return jsonify({"status":"error","message":"Định dạng ngày/giờ không hợp lệ."})

    if lich_loai == 'duong':
        ay, am, ad, is_leap = ngay_am_lich_cho_gio(sy, sm, sd, gio_h, tz=int(mui_gio))
        duong_str = f"{sd:02d}/{sm:02d}/{sy}"
        am_str    = f"{ad:02d}/{am:02d}/{ay}" + (" (nhuận)" if is_leap else "")
    else:
        ay, am, ad = sy, sm, sd
        is_leap   = bool(data.get('thangNhuan', False))
        am_str    = f"{ad:02d}/{am:02d}/{ay}" + (" (nhuận)" if is_leap else "")
        duong_str = "(nhập âm lịch)"

    if not (1 <= am <= 12) or not (1 <= ad <= 30):
        return jsonify({"status":"error",
                        "message":f"Âm lịch không hợp lệ: {ad}/{am}/{ay}"})

    chi_gio  = gio_to_chi(gio_h)
    cn       = can_nam(ay)
    ch       = chi_nam(ay)
    can_dan  = can_thang_dan(cn)
    vi_menh  = vi_tri_menh(am, chi_gio)
    vi_than  = vi_tri_than(am, chi_gio)
    buoc_m   = (vi_menh - 2 + 12) % 12
    can_m    = can_cung(can_dan, buoc_m)
    cuc_val  = tinh_cuc(cn, vi_menh)
    ten_cuc  = NGU_HANH_CUC[cuc_val]
    vt_tuvi     = an_tu_vi(ad, cuc_val)
    vt_thienphy = (16 - vt_tuvi + 120) % 12
    sc = {i: [] for i in range(12)}
    an_14_chinh_tinh(vt_tuvi, vt_thienphy, sc)
    an_phu_tinh(am, chi_gio, sc)
    ten_cung = {i: ten_can_chi_cung(can_dan, i) for i in range(12)}
    dai_han, thuan = tinh_dai_han(vi_menh, cn, gioi_tinh, cuc_val, ay)
    tieu_han       = tinh_tieu_han(gioi_tinh, ay, 30)
    tz_sign = "+" if mui_gio >= 0 else ""
    return jsonify({
        "status":  "success",
        "message": f"Lập lá số thành công! {ten_cuc}.",
        "thongTin": {
            "hoTen":      ho_ten,
            "gioiTinh":   gioi_tinh,
            "ngayAm":     am_str,
            "ngayDuong":  duong_str,
            "thangNhuan": is_leap,
            "gioSinh":    f"{DIA_CHI[chi_gio]} thời ({gio_str})",
            "canChiNam":  f"{THIEN_CAN[cn]} {DIA_CHI[ch]}",
            "thanhPho":   thanh_pho,
            "quocGia":    quoc_gia,
            "muiGio":     f"UTC{tz_sign}{mui_gio}",
        },
        "nguHanhCuc": {
            "tenCuc":  ten_cuc,
            "soCuc":   cuc_val,
            "canMenh": THIEN_CAN[can_m],
            "chiMenh": DIA_CHI[vi_menh],
        },
        "cung": {
            "menh": {"viTri": vi_menh, "tenCung": ten_cung[vi_menh], "diaChi": DIA_CHI[vi_menh]},
            "than": {"viTri": vi_than, "tenCung": ten_cung[vi_than], "diaChi": DIA_CHI[vi_than]},
        },
        "tuvi":     {"viTri": vt_tuvi,     "diaChi": DIA_CHI[vt_tuvi]},
        "thienPhu": {"viTri": vt_thienphy, "diaChi": DIA_CHI[vt_thienphy]},
        "saoCung":  {str(k): v for k, v in sc.items()},
        "tenCung":  {str(k): v for k, v in ten_cung.items()},
        "diaChi":   {str(i): DIA_CHI[i] for i in range(12)},
        "daiHan":   dai_han,
        "tieuHan":  tieu_han,
        "chieuDaiHan": "thuận" if thuan else "nghịch",
    })


@app.route('/api/chuyen-lich', methods=['POST'])
def chuyen_lich():
    data      = request.json or {}
    ngay      = data.get('ngay', '')
    lich_loai = data.get('lichLoai', 'duong')
    tz        = int(data.get('muiGio', 7))
    try:
        y, m, d = map(int, ngay.split('-'))
    except:
        return jsonify({"status":"error","message":"Định dạng YYYY-MM-DD."})
    if lich_loai == 'duong':
        ay, am, ad, leap = duong_sang_am(y, m, d, tz)
        return jsonify({"status":"success",
                        "duongLich":  f"{d:02d}/{m:02d}/{y}",
                        "amLich":     f"{ad:02d}/{am:02d}/{ay}",
                        "thangNhuan": leap})
    return jsonify({"status":"success","amLich": f"{d:02d}/{m:02d}/{y}"})


@app.route('/api/openrouter', methods=['POST'])
def openrouter_proxy():
    data     = request.json or {}
    key      = data.get('key', '')
    messages = data.get('messages', [])
    model    = data.get('model', 'deepseek/deepseek-r1:free')
    if not key or not messages:
        return jsonify({"error": "Thiếu key hoặc messages"}), 400
    try:
        res = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': 'Bearer ' + key,
                'Content-Type': 'application/json',
                'HTTP-Referer': 'http://localhost:5000',
                'X-Title': 'Tu Vi AI'
            },
            json={
                'model': model,
                'messages': messages,
                'max_tokens': 1200,
                'temperature': 0.65
            },
            timeout=60
        )
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/gemini', methods=['POST'])
def gemini_proxy():
    data   = request.json or {}
    key    = data.get('key', '')
    prompt = data.get('prompt', '')
    model  = data.get('model', 'gemini-2.0-flash')
    if not key or not prompt:
        return jsonify({"error": "Thiếu key hoặc prompt"}), 400
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    res = requests.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
    })
    return jsonify(res.json())


# ═══════════════════════════════════════════════════════════
# QUICK TEST — chạy: python app.py test
# ═══════════════════════════════════════════════════════════
def _run_tests():
    print("=" * 65)
    print("TEST CHUYỂN DƯƠNG → ÂM LỊCH")
    print("=" * 65)
    tests = [
        # (sy, sm, sd, gio_h, exp_d, exp_m, exp_y, mô tả)
        # --- cases cũ ---
        (1993, 10, 17, 23,  4,  9, 1993, "17/10/1993 23h → 4/9/1993 âm (giờ Tý sang ngày mới)"),
        (1993, 10, 17, 22,  3,  9, 1993, "17/10/1993 22h → 3/9/1993 âm"),
        (1993, 10, 17,  0,  3,  9, 1993, "17/10/1993 00h → 3/9/1993 âm"),
        (1993, 10, 18,  0,  4,  9, 1993, "18/10/1993 00h → 4/9/1993 âm"),
        # --- case bug: ngày trùng trăng mới ---
        (2003, 12, 23, 17,  1, 12, 2003, "23/12/2003 17h → 1/12/2003 âm (mùng 1 tháng mới)"),
        (2003, 12, 22, 12, 29, 11, 2003, "22/12/2003 12h → 29/11/2003 âm (tháng 11 âm 2003 chỉ có 29 ngày)"),
        # --- REGRESSION: tháng nhuận ---
        # Năm 1979 nhuận tháng 6
        (1979,  7, 24,  0,  1,  6, 1979, "24/07/1979 → 1/6n/1979 (mùng 1 tháng nhuận 6)"),
        (1979,  7, 25,  0,  2,  6, 1979, "25/07/1979 → 2/6n/1979 (ngày 2 tháng nhuận 6)"),
        (1979,  8, 15,  0, 23,  6, 1979, "15/08/1979 → 23/6n/1979 (case bug gốc)"),
        (1979,  8, 22,  0, 30,  6, 1979, "22/08/1979 → 30/6n/1979 (ngày cuối tháng nhuận 6)"),
        (1979,  8, 23,  0,  1,  7, 1979, "23/08/1979 → 1/7/1979 (mùng 1 tháng 7 thường)"),
        (1979,  7, 23,  0, 30,  6, 1979, "23/07/1979 → 30/6/1979 (ngày cuối tháng 6 thường, trước nhuận 6)"),
        # Năm 1990 nhuận tháng 5
        (1990,  5, 10,  0, 16,  4, 1990, "10/05/1990 → 16/4/1990 (tháng 4 thường)"),
        # Năm 2001 nhuận tháng 4 (theo chuẩn lịch VN / lichviet)
        (2001,  4, 23,  0,  1,  4, 2001, "23/04/2001 → 1/4/2001 (mùng 1 tháng 4 thường)"),
        (2001,  5, 23,  0,  1,  4, 2001, "23/05/2001 → 1/4n/2001 (mùng 1 tháng nhuận 4)"),
        (2001,  6, 21,  0,  1,  5, 2001, "21/06/2001 → 1/5/2001 (mùng 1 tháng 5 thường)"),
        # Không năm nhuận
        (2000,  1,  1,  0, 25, 11, 1999, "01/01/2000 → 25/11/1999 (không nhuận)"),
        (2024,  2, 10,  0,  1,  1, 2024, "10/02/2024 → mùng 1 Tết Giáp Thìn"),
    ]
    pass_count = 0
    for row in tests:
        sy, sm, sd, gio_h, exp_d, exp_m, exp_y, mo_ta = row
        ay, am, ad, leap = ngay_am_lich_cho_gio(sy, sm, sd, gio_h)
        if exp_y == 999:
            ok = (ad == exp_d and am == exp_m)
        else:
            ok = (ad == exp_d and am == exp_m and ay == exp_y)
        icon = "✅" if ok else "❌"
        if ok: pass_count += 1
        leap_str = "(nhuận)" if leap else ""
        got = f"→ ra {ad}/{am}{leap_str}/{ay}"
        print(f"{icon} {mo_ta}  {got}")
    print("=" * 65)
    print(f"Kết quả: {pass_count}/{len(tests)} passed")
    print("=" * 65)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        _run_tests()
    else:
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=False, host='0.0.0.0', port=port)