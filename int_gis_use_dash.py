import dash
from dash_breakpoints import WindowBreakpoints # 斷點處理
from dash import dcc, html
from dash.dependencies import Input, Output, State
import folium
from folium import Marker
import os
import base64
import io
import dash_bootstrap_components as dbc
from geopy.geocoders import Nominatim
import geopandas as gpd
import pandas as pd
from userdefinefun import get_tourist_data, get_unique_zip_area_df
from userdefinefun import create_map1, create_map2
from userdefinefun import style_function
from userdefinefun import create_vp_dropdown_options
from userdefinefun import _load_layer_to_4326
from dash import no_update
from flask import request
from flask_cors import CORS
from flask import jsonify

# df = pd.read_csv('static/Scenic_Spot_C_f_filled1拷貝2_至3198.csv', encoding='utf-8')
# df = get_tourist_data()
# 移除重複的郵遞區號及區域名稱組合，並進行排序
# unique_zip_area = get_unique_zip_area_df()

# 將資料轉換為 Dash 下拉選單格式
# dropdown_options = [
#     {'label': f"{row['郵遞區號']} {row['區域名稱']}", 'value': row['郵遞區號']}
#     for _, row in unique_zip_area.iterrows()
# ]

# 將景點名稱資料轉換為 Dash 下拉選單格式
# 讀取 "新北市觀光旅遊景點(中文).csv" 檔案
global selected_df
#selected_df = pd.read_csv('newtpe_tourist_att.csv', encoding='utf-8')

#vp_dropdown_options = [
#    {'label': f"{idx+1} {row['Name']}", 'value': row['Name']}
#    for idx, row in selected_df.iterrows()
#]

# 建立 Dash 應用
app = dash.Dash(__name__, meta_tags=[
                {"name": "viewport", "content": "width=device-width, initial-scale=1"}
            ], external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server=app.server   # gunicorn int_gis_use_dash:server --bind 0.0.0.0:8799
# === Flask routes: CSV + upload/download (migrated from server.js) ===
import csv
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from flask import request, jsonify, send_file, Response

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# 你的 CSV 與 uploads 都在 2025_aut_Python_proj/static 下
CSV_FILE = Path(os.environ.get("CSV_FILE", str(STATIC_DIR / "Scenic_Spot_C_f_filled1拷貝2_至3814.csv")))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(STATIC_DIR / "uploads")))
MAX_FOLDER_SIZE_MB = float(os.environ.get("MAX_FOLDER_SIZE_MB", "400"))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 依 server.js 的 fieldMapping 直接搬過來（重複 key 在 Python dict 會以最後一次為準）
fieldMapping = {
    "Name": "景點名稱",
    "Zone": "景點所屬景區編號",
    "Toldescribe": "景點特色文字詳述",
    "Description": "景點特色文字簡述",
    "Tel": "景點服務電話",
    "Add": "景點地址",
    "Zipcode": "郵遞區號",
    "Region": "景點所屬行政區域",
    "Town": "景點所屬行政區域之鄉鎮市區",
    "Travellinginfo": "交通資訊描述",
    "Opentime": "開放時間",
    "Picture1": "景點圖片網址1",
    "Picdescribe1": "景點圖片說明1",
    "Picture2": "景點圖片網址2",
    "Picdescribe2": "景點圖片說明2",
    "Picture3": "景點圖片網址3",
    "Picdescribe3": "景點圖片說明3",
    "Map": "景點地圖介紹網址",
    "Gov": "景點管理權責單位代碼",
    "Px": "景點X座標",
    "Py": "景點Y座標",
    "Orgclass": "景點分類說明",
    "Class1": "景點分類代碼1",
    "Class2": "景點分類代碼2",
    "Class3": "景點分類代碼3",
    "Mapinfo": "景點地圖Y座標",
    "Level": "古蹟分級",
    "Website": "景點網址",
    "Parkinginfo": "停車資訊",
    "Parkinginfo_px": "主要停車場X座標",
    "Parkinginfo_py": "主要停車場Y座標",
    "Ticketinfo": "景點票價資訊",
    "Remarks": "警告及注意事項",
    "Keyword": "搜尋關鍵字",
    "Changetime": "資料異動時間",
}

def read_csv_dicts(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv_dicts(path: Path, rows: list[dict]):
    if not rows:
        raise ValueError("CSV is empty")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def getCurrentTimestamp_taipei():
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y/%m/%d %H:%M:%S")

def get_folder_size_mb(folder: Path) -> float:
    total = 0
    for p in folder.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total / (1024 * 1024)

def get_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".gif":
        return "image/gif"
    if ext == ".webp":
        return "image/webp"
    return "application/octet-stream"

# ---- CSV: get fields ----
@server.route("/api/get-fields", methods=["GET"])
def api_get_fields():
    place_id = request.args.get("PlaceID")
    if not place_id:
        return jsonify({"message": "Missing PlaceID"}), 400

    try:
        records = read_csv_dicts(CSV_FILE)
        record = next((r for r in records if r.get("Id") == place_id), None)
        if not record:
            return jsonify({"message": "未找到相關記錄"}), 404

        fields = []
        for key in record.keys():
            if key == "Id":
                continue
            fields.append({
                "key": key,
                "label": fieldMapping.get(key, key),
                "content": record.get(key, "")
            })

        return jsonify({"fields": fields})
    except Exception as e:
        print("讀取欄位時發生錯誤：", e)
        return jsonify({"message": "伺服器錯誤，請稍後再試。"}), 500

# ---- CSV: update ----
@server.route("/api/update-csv", methods=["POST"])
def api_update_csv():
    updates = request.get_json(silent=True)
    if not isinstance(updates, list) or len(updates) == 0:
        return jsonify({"message": "請提供有效的更新數據！"}), 400

    try:
        records = read_csv_dicts(CSV_FILE)
        now = getCurrentTimestamp_taipei()

        for u in updates:
            place_id = u.get("PlaceID")
            field = u.get("field")
            content = u.get("content", "")
            if not place_id or not field:
                continue

            record = next((r for r in records if r.get("Id") == place_id), None)
            if record is not None:
                if field in record:
                    record[field] = content
                record["Changetime"] = now

        write_csv_dicts(CSV_FILE, records)
        return jsonify({"message": "資料已成功更新！若更改景點X、Y座標，需重新繪製地圖。"})
    except Exception as e:
        print("更新 CSV 文件時發生錯誤：", e)
        return jsonify({"message": "更新失敗，請稍後再試。"}), 500

# ---- capacity limit ----
@server.route("/check_capacity_limit", methods=["POST"])
def check_capacity_limit():
    upload_chunks = float(request.form.get("uploadChunks", "0") or 0)
    folder_size = get_folder_size_mb(UPLOAD_DIR)

    if folder_size >= MAX_FOLDER_SIZE_MB:
        return jsonify({"error": "上傳空間已滿，請聯繫伺服器管理員。"}), 400

    if (folder_size + upload_chunks) > MAX_FOLDER_SIZE_MB:
        return jsonify({"error": "上傳大小及資料夾大小之總和超過容量上限，請刪除部分檔案後再嘗試。"}), 400

    return jsonify({"message": "空間充足，可以上傳。"})

# ---- chunk upload ----
@server.route("/2025_aut_Python_proj", methods=["POST"])
def upload_chunked_file():
    chunk = request.files.get("fileChunk")
    chunkIndex = request.form.get("chunkIndex")
    fileName = request.form.get("fileName")
    totalChunks = request.form.get("totalChunks")
    subid = request.form.get("subid")

    if chunk is None or fileName is None or chunkIndex is None or totalChunks is None:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        chunkIndex_i = int(chunkIndex)
        totalChunks_i = int(totalChunks)

        temp_dir = UPLOAD_DIR / f"{fileName}_tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        chunk_path = temp_dir / f"chunk_{chunkIndex_i}"
        chunk.save(chunk_path)

        if chunkIndex_i == (totalChunks_i - 1):
            if not subid:
                return jsonify({"error": "Missing subid"}), 400

            final_dir = UPLOAD_DIR / subid
            final_dir.mkdir(parents=True, exist_ok=True)
            final_path = final_dir / fileName

            with final_path.open("wb") as out:
                for i in range(totalChunks_i):
                    part = temp_dir / f"chunk_{i}"
                    with part.open("rb") as pf:
                        shutil.copyfileobj(pf, out)
                    part.unlink(missing_ok=True)

            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"message": "File upload complete!"})

        return jsonify({"message": f"Chunk {chunkIndex_i} uploaded successfully."})
    except Exception as e:
        print("upload chunk error:", e)
        return jsonify({"error": "Upload failed"}), 500

# ---- list files ----
@server.route("/uploads", methods=["GET"])
def list_uploads():
    subid = request.args.get("id")
    if not subid:
        return jsonify({"error": "缺少必要的id参数"}), 400

    folder = UPLOAD_DIR / subid
    if not folder.exists():
        return jsonify({"error": "照片目錄不存在"}), 404

    files = [p.name for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")]
    return jsonify(files)

# ---- preview ----
@server.route("/previewimage/<subid>/<filename>", methods=["GET"])
def preview_image(subid, filename):
    file_path = UPLOAD_DIR / subid / filename
    if not file_path.exists():
        return Response("檔案未找到", status=404)
    return send_file(str(file_path), mimetype=get_content_type(filename))

# ---- download ----
@server.route("/uploads/<subid>/<filename>", methods=["GET"])
def download_image(subid, filename):
    file_path = UPLOAD_DIR / subid / filename
    if not file_path.exists():
        return Response("檔案未找到", status=404)
    return send_file(str(file_path), as_attachment=True, download_name=filename)
# === End Flask routes ===

# C#app = dash.Dash(__name__, suppress_callback_exceptions=True)
###
import socket

def get_host_ip():
    """
    使用 socket 獲取主機的本地 IP 地址
    """
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("hostname = ", hostname)
    print("local_ip = ", local_ip)
    return local_ip

# 獲取主機 IP 地址
server_ip = get_host_ip()
###
# 初始化地圖函數
##
# 自定義樣式函數
def create_map(breakpoint_name,name,window_width):
    
    # 讀取讀取全國鄉鎮市區界圖shpe file
    # Big_Taipei_data = gpd.read_file('static/shapefiles/Taipei.shp', encoding='utf-8')
    # shapefile_path = os.path.join(os.path.dirname(__file__), 'static', 'shapefiles', 'Taipei.shp')
    #shapefile_path = os.path.join(os.path.dirname(__file__), 'static', 'shapefiles', 'TOWN_MOI_1140318.shp')
    # Big_Taipei_data = gpd.read_file(shapefile_path, encoding='utf-8')
    # Ｎew_Taipei_data = Big_Taipei_data[(Big_Taipei_data['COUNTYNAME']=='新北市')]
    #Domestic_data = gpd.read_file(shapefile_path, encoding='utf-8')
    # County_data = Domestic_data[(Domestic_data['COUNTYNAME']=='南投縣')]
    ##
    # 額外讀取屏東縣瑪家鄉三和村shape file
    shapefile_path = os.path.join(os.path.dirname(__file__), 'static', 'shapefiles', 'Town_Majia_Sanhe.shp')
    Sanhe_data = gpd.read_file(shapefile_path, encoding='utf-8')
     # 讀取全國鄉鎮市區界圖及屏東縣瑪家鄉三和村shape file
    base_dir = os.path.dirname(__file__)
    town_shp = os.path.join(base_dir, "static", "shapefiles", "TOWN_MOI_1140318.shp")
    sanhe_shp = os.path.join(base_dir, "static", "shapefiles", "Town_Majia_Sanhe.shp")

    # === 讀檔並確保是 WGS84 ===
    Domestic_gdf = _load_layer_to_4326(town_shp)      # 鄉鎮市區界
    Sanhe_gdf    = _load_layer_to_4326(sanhe_shp)     # 三和村（專屬 shapefile)
    # 設定地圖中心點和縮放級別，這裡以新北市的經緯度為例
    map_center = [24.989868, 121.656173]  # 新北市中心位置約在石碇區石碇里

    #mymap = folium.Map(location=map_center, zoom_start=12)

    # 將 Shapefile 轉為 GeoJSON 並添加到地圖
    #folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
    ##
    # calling the Nominatim tool
    loc = Nominatim(user_agent="Get NewTaipei", timeout=5)
    # entering the location name
    getLoc = loc.geocode(name, country_codes = "TW")
    #getLoc = loc.geocode(name)
    #getLoc = loc.geocode(name)
    #popup=getLoc.address + '\n' + str(getLoc.latitude) + '\n' + str(getLoc.longitude) 
    #
    if getLoc is not None:
        if name != "台灣地理中心碑":
           popup="<div style='font-size: 24px;'>" +getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude) + "</div>"
        else:
            popup="<div style='font-size: 24px;'>" + "台灣地理中心位置：" + "<br>" + getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude) + "</div>"

        mymap = folium.Map(location=[getLoc.latitude, getLoc.longitude], zoom_start=12)
        Marker([getLoc.latitude, getLoc.longitude], popup=popup, icon=folium.Icon(color="red")).add_to(mymap)
        # 將 Shapefile 轉為 GeoJSON 並添加到地圖
        #folium.GeoJson(Domestic_data, style_function=style_function).add_to(mymap)
        #folium.GeoJson(Sanhe_data, style_function=style_function).add_to(mymap)
        # === 疊鄉鎮界（灰線、很淡底色） ===
        # 欄位常見：COUNTYNAME / TOWNNAME
        # folium.GeoJson(
        #     Domestic_gdf[["COUNTYNAME","TOWNNAME","geometry"]],
        #     name="鄉鎮市區界",
        #     # style_function=lambda x: {"fillOpacity": 0.03, "color": "#666", "weight": 1},
        #     style_function=lambda x: {"fillOpacity": 0.00, "color": "#666", "weight": 0},
        #     tooltip=folium.GeoJsonTooltip(
        #         fields=["COUNTYNAME","TOWNNAME"], aliases=["縣市","鄉鎮市區"], sticky=False
        #     ),
        # ).add_to(mymap)

        # === 疊三和村（橘色高亮） ===
        # 村里欄位常見：VILLNAME（有就顯示，沒有就只顯示縣市/鄉鎮）
        vill_col = "VILLNAME" if "VILLNAME" in Sanhe_gdf.columns else None
        tooltip_fields = ["COUNTYNAME","TOWNNAME"] + ([vill_col] if vill_col else [])
        tooltip_alias  = ["縣市","鄉鎮市區"] + (["村里"] if vill_col else [])

        folium.GeoJson(
            Sanhe_gdf[tooltip_fields + ["geometry"]] if tooltip_fields else Sanhe_gdf,
            name="屏東縣瑪家鄉三和村",
            style_function=lambda x: {"fillColor": "#ffa500", "color": "#ffa500", "weight": 3, "fillOpacity": 0.5},
            tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_alias, sticky=False) if tooltip_fields else None,
        ).add_to(mymap)
        error_msg=""
    else:
        getLoc = loc.geocode(name)
        if getLoc is not None:
            # popup=getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude)
            popup="<div style='font-size: 24px;'>" +getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude) + "</div>"
            mymap = folium.Map(location=[getLoc.latitude, getLoc.longitude], zoom_start=12)
            # Marker([getLoc.latitude, getLoc.longitude], popup=popup).add_to(mymap)
            Marker([getLoc.latitude, getLoc.longitude], popup=popup, icon=folium.Icon(color="red")).add_to(mymap)
            # 將 Shapefile 轉為 GeoJSON 並添加到地圖
            #folium.GeoJson(Domestic_data, style_function=style_function).add_to(mymap)
            #folium.GeoJson(Sanhe_data, style_function=style_function).add_to(mymap)
            # === 疊鄉鎮界（灰線、很淡底色） ===
            # 欄位常見：COUNTYNAME / TOWNNAME
            # folium.GeoJson(
            #     Domestic_gdf[["COUNTYNAME","TOWNNAME","geometry"]],
            #     name="鄉鎮市區界",
            #     # style_function=lambda x: {"fillOpacity": 0.03, "color": "#666", "weight": 1},
            #     style_function=lambda x: {"fillOpacity": 0.00, "color": "#666", "weight": 0},
            #     tooltip=folium.GeoJsonTooltip(
            #         fields=["COUNTYNAME","TOWNNAME"], aliases=["縣市","鄉鎮市區"], sticky=False
            #     ),
            # ).add_to(mymap)

            # === 疊三和村（橘色高亮） ===
            # 村里欄位常見：VILLNAME（有就顯示，沒有就只顯示縣市/鄉鎮）
            vill_col = "VILLNAME" if "VILLNAME" in Sanhe_gdf.columns else None
            tooltip_fields = ["COUNTYNAME","TOWNNAME"] + ([vill_col] if vill_col else [])
            tooltip_alias  = ["縣市","鄉鎮市區"] + (["村里"] if vill_col else [])

            folium.GeoJson(
                Sanhe_gdf[tooltip_fields + ["geometry"]] if tooltip_fields else Sanhe_gdf,
                name="屏東縣瑪家鄉三和村",
                style_function=lambda x: {"fillColor": "#ffa500", "color": "#ffa500", "weight": 3, "fillOpacity": 0.5},
                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_alias, sticky=False) if tooltip_fields else None,
            ).add_to(mymap)
            error_msg=""
        else:
            mymap = folium.Map(location=map_center, zoom_start=12)
            error_msg="名稱:" + name + " 地理編碼錯誤致搜尋失敗"

    # 將 Shapefile 轉為 GeoJSON 並添加到地圖
    #folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
    ##   
    # 創建 Folium 地圖
    #folium_map = folium.Map(location=[lat, lon], zoom_start=12)

    #folium.Marker([getLoc.latitude, getLoc.longitude], popup=popup).add_to(mymap)

    mymap.save("static/mymap.html")
    #
    # 將地圖保存為 HTML 字串
    map_io = io.BytesIO()
    mymap.save(map_io, close_file=False)
    map_html = map_io.getvalue().decode()

    # return map_html, error_msg, []
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", map_html, error_msg 

# 全域變數
# g_width = 1000  # 預設寬度
# App Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div(id='window-size-display'),
            WindowBreakpoints(
                id="breakpoints",
                widthBreakpointThresholdsPx=[575, 767, 991, 1199],
                widthBreakpointNames=["xs", "sm", "md", "lg", "xl"],
            ),
            html.Div([
                dcc.Location(id='url', refresh=False),
                html.Div(id='page-content')
            ]),
            html.H4("互動式GIS系統3.0", className='text-center mb-4'),
            dbc.Label("請輸入世界各地任一地點名稱:"),
            dcc.Input(id='name-input', type='text', value=""),            
            html.Br(),
            dbc.Button("繪製地圖(世界範圍)", id="generate-map-btn1", color="primary", className="mt-2"),
            dbc.Label("-----------------------------------"),
            html.Br(),
            html.Div([
                html.Label("全國觀光旅遊景點位置查詢"),
                dcc.Dropdown(
                    options=[
                        {'label': '北部', 'value': '北部'},
                        {'label': '中部', 'value': '中部'},
                        {'label': '南部', 'value': '南部'},
                        {'label': '東部', 'value': '東部'},
                        {'label': '外島', 'value': '外島'},
                    ],
                    id='location-dropdown',
                    placeholder="點選任一位置別",
                ),
                html.Div(id='dd-output-container'),
                dcc.Dropdown(
                    id='city-dropdown',
                    placeholder="選擇縣市別",
                ),
                dcc.Dropdown(
                    id='district-dropdown',
                    placeholder="選擇鄉鎮市區別",
                ),
                dcc.Dropdown(
                    id='scenicspot-dropdown',
                    placeholder="選擇景點別",
                ),
                html.Br(),
                dbc.Button("繪製地圖(國內範圍)", id="generate-map-btn2", color="primary", className="mt-2"),
            ]),
            html.Div(id='error-message', style={'color': 'red', 'marginTop': '10px'}),
        ], width=3, className="dash-col-left"),
        dbc.Col([
            html.Iframe(id='map', width='100%', height='600'),
        ], width=9, className="dash-col-right"),
        dcc.Store(id='selected-location'),  # 儲存選擇的景點資訊
        dcc.Store(id='map-update-data'),  # 用于触发地图更新的存储组件
    ])
], fluid=True)

# const storeComponent = document.querySelector('#st-width');造成⚠️ 無法找到 st-width 元件
# 這樣不保證 Dash render 完會成功。
# 改用 Dash 官方支援的方式回傳 store 值，不要硬塞 DOM
# 非正規實作

# @app.callback(
    # Output("window-size-display", "children"),
    # Input("breakpoints", "widthBreakpoint"),
    # State("breakpoints", "width"),
# )
# def show_current_breakpoint(breakpoint_name: str, window_width: int):
    # return f"斷點名稱: {breakpoint_name}, 視窗寬度: {window_width}px"
###
@app.callback(
    # Output('dd-output-container', 'children'),
    Output('city-dropdown', 'options'),  # 輸出縣市選項
    Output('district-dropdown', 'options'),  # 輸出鄉鎮市區選項
    Output('scenicspot-dropdown', 'options'),  # 輸出景點選項
    Input('location-dropdown', 'value'),
    Input('city-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('scenicspot-dropdown', 'value'),

)
def update_output(location_value, city_value, district_value, scenicspot_value):
    city_options = []
    district_options = []
    scenicspot_options = []

    if location_value == '北部':
        city_options = [
            {'label': '基隆市', 'value': '基隆市'},
            {'label': '臺北市', 'value': '臺北市'},
            {'label': '新北市', 'value': '新北市'},
            {'label': '桃園市', 'value': '桃園市'},
            {'label': '新竹市', 'value': '新竹市'},
            {'label': '新竹縣', 'value': '新竹縣'},
            {'label': '苗栗縣', 'value': '苗栗縣'},
        ]
    elif location_value == '中部':
        city_options = [
            {'label': '臺中市', 'value': '臺中市'},
            {'label': '彰化縣', 'value': '彰化縣'},
            {'label': '南投縣', 'value': '南投縣'},
        ]
    elif location_value == '南部':
        city_options = [
            {'label': '雲林縣', 'value': '雲林縣'},
            {'label': '嘉義市', 'value': '嘉義市'},
            {'label': '嘉義縣', 'value': '嘉義縣'},
            {'label': '臺南市', 'value': '臺南市'},
            {'label': '高雄市', 'value': '高雄市'},
            {'label': '屏東縣', 'value': '屏東縣'},
        ]
    elif location_value == '東部':
        city_options = [
            {'label': '宜蘭縣', 'value': '宜蘭縣'},
            {'label': '花蓮縣', 'value': '花蓮縣'},
            {'label': '臺東縣', 'value': '臺東縣'},
        ]
    elif location_value == '外島':
        city_options = [
            {'label': '金門縣', 'value': '金門縣'},
            {'label': '連江縣', 'value': '連江縣'},
            {'label': '澎湖縣', 'value': '澎湖縣'},
        ]

    if city_value is not None and city_value != '':
        # 處理空白與格式
        # df['Region'] = df['Region'].astype(str).str.strip()
        # df['Town'] = df['Town'].astype(str).str.strip()
        
        df = get_tourist_data()  # 確保使用最新的資料
        # Debug 輸出
        print("選到的縣市:", city_value)
        print("Region 唯一值：", df['Region'].unique())

        # 過濾符合地區的鄉鎮市區
        filtered_df = df[df['Region'] == city_value]
        print("找到筆數：", len(filtered_df))

        if len(filtered_df) > 0:
            # selected_df = filtered_df[['Town']].dropna().drop_duplicates().reset_index(drop=True)
            selected_df = filtered_df[['Zipcode','Town']].dropna().drop_duplicates().reset_index(drop=True)
            options = [{'label': town, 'value': town} for town in selected_df['Town']]
        else:
            options = []  # 無符合資料

        selected_df = df[df['Region'] == city_value][['Zipcode','Town']].dropna().drop_duplicates().reset_index(drop=True)
        # 獲取選擇的縣市對應的鄉鎮市區選項
        district_options = [
            {'label': f"{idx+1} {row['Zipcode']} {row['Town']}", 'value': row['Zipcode']}
            for idx, row in selected_df.iterrows()
        ]
    else:
        district_options = []
        district_value = None  # 重置鄉鎮市區選擇
        scenicspot_options = []
        scenicspot_value = None  # 重置景點選擇

    if district_value is not None and district_value != '':
        print("選到的鄉鎮市區:", district_value)
        # print("Town 唯一值：", df['Town'].unique())

        # 過濾符合鄉鎮市區的景點
        # filtered_df = df[df['Zipcode'] == district_value]
        # print("找到筆數：", len(filtered_df))

        # if len(filtered_df) > 0:
        #     selected_df = filtered_df[['ScenicSpot']].dropna().drop_duplicates().reset_index(drop=True)
        #     scenicspot_options = [{'label': spot, 'value': spot} for spot in selected_df['ScenicSpot']]
        # else:
        #     scenicspot_options = []  # 無符合資料

        # 篩選對應的 Zipcode 資料，並依 Name 排序
        selected_df = (
            df[df['Zipcode'] == district_value][['Name']]
            .dropna()
            .drop_duplicates()
            .sort_values(by='Name')   # 依 Name 欄位排序
            .reset_index(drop=True)
        )

        print("找到筆數：", len(selected_df))

        # 建立景點下拉選項
        scenicspot_options = [
            {'label': f"{idx+1} {row['Name']}", 'value': row['Name']}
            for idx, row in selected_df.iterrows()
        ]
    else:
        scenicspot_options = []
        scenicspot_value = None  # 重置景點選擇

    if scenicspot_value is not None and scenicspot_value != '':
        print("選到的景點:", scenicspot_value)
        # 這裡可以根據需要進行進一步的處理
        #      
    return city_options, district_options, scenicspot_options

###
# Callback 更新地圖
@app.callback(
    Output("window-size-display", "children"),
    Output('map', 'srcDoc'), 
    Output('error-message', 'children'),
    # Output('viewpoint-dropdown', 'options'),  # 更新地圖和錯誤訊息
    #[Input('generate-map-btn', 'n_clicks')],
    #[Input('latitude-input', 'value'), Input('longitude-input', 'value')]
    Input("breakpoints", "widthBreakpoint"),
    #Input('width', 'children'),
    # Input('width', 'data'),
    Input('generate-map-btn1', 'n_clicks'),  # 按鈕點擊事件觸發
                                             # 使用 Input 監聽按鈕點擊事件：按鈕的點擊事件觸發地圖更新。
    Input('generate-map-btn2', 'n_clicks'), 
    # Input('zip-area-dropdown', 'value'),
    State('name-input', 'value'),   # 名稱或地址 # 使用 State 來儲存緯度和經度數值：避免在按鈕點擊之前緯度和經度變化時觸發回調。
    State('district-dropdown', 'value'),
    State('scenicspot-dropdown', 'value'),
    State("breakpoints", "width")

    # State('st-width', 'data')
    #state('viewpoint-dropdown', 'value')
)
##
def update_map_and_dropdown(breakpoint_name: str, map_clicks1, map_clicks2, name, district, scenicspot, window_width: int):
                           
    # ***** Initialize default values
    #map_html = "<p>No map data available.</p>"  # Default or empty map HTML
    #error_msg = ""  # No error initially
    #viewpoint_options = []  # Default empty options
    #
    ctx = dash.callback_context  # 用於判斷哪個輸入觸發了回調
    triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]
    # 如果是 zip-area-dropdown 觸發的回調，更新 viewpoint-dropdown 的選項
    # if triggered_input == 'zip-area-dropdown':
    #     return create_vp_dropdown_options(breakpoint_name,zipcode,window_width) 
    if triggered_input in ['generate-map-btn1', 'generate-map-btn2']:
    # 當按鈕點擊後，根據 name 和 zipcode 判斷要生成哪種地圖
        if name:
            if map_clicks1 is not None:
                return create_map(breakpoint_name,name,window_width)  # 優先使用 name
        elif district:
            if map_clicks2 is not None:
                if not scenicspot: 
                    return create_map1(breakpoint_name,district,server_ip,window_width)
                    print("trace 1 on create_map1")
                else:
                    return create_map2(breakpoint_name,district,scenicspot,server_ip,window_width)
                    # else:
                        # return no_update, no_update, no_update 
        else:
            return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)",no_update, no_update   # 必須
    else:
        # 初始狀態，當 n_clicks 為 None 時顯示默認地圖
        # name = name if name else "石碇區石碇里"  # 預設地點
        name = name if name else "台灣地理中心碑"  # 預設地點
        return create_map(breakpoint_name,name,window_width)
            
                
    #    else:
    #        if qry_clicks is not None:
    #            return create_qry(zipcode)
    #else:
        # 如果都沒有提供，顯示一個默認的地圖或錯誤訊息
        #return None, "Please provide either a name or a zipcode."
        #return None, "請輸入地點名稱或點選郵遞區號及區域名稱", [ ]
###
from dash import no_update

@app.callback(
    Output('map-update-data', 'data'),
    Input('map-update-data', 'data'),
    prevent_initial_call=True
)
def update_map_trigger(data):
    print('(update_map_trigger)被觸發,data: ', data)
    if data:
        return data
    return no_update


@app.callback(
    Output('map', 'srcDoc', allow_duplicate=True),
    Input('map-update-data', 'data'),  # 监听 Store 数据的变化
    prevent_initial_call=True
)
def refresh_map(data):
    print('(refresh_map)被觸發,data: ', data)
    if data:
        # 解析传递的 zip 和 id，这里假设 zip 是固定值
        zip_code = '999'  # 示例值
        location_id = data
        print('(rfresh_map) data = ', data)
        return create_map2(zip_code, location_id)[0]
    return no_update

##@app.server.route('/message', methods=['POST'])
##def receive_message():
##    message = request.json
##    if message.get('action') == 'updateMap':
##        location_id = message.get('id')
##        print('(receive_message) message.get("id") = ', location_id)
##        # 模擬觸發回調的行為
##        app.layout.children.append(html.Div(id='map-update-data', data=location_id))
##        # 更新地图触发数据
##        return jsonify({"status": "success", "data": location_id}), 200
##    return jsonify({"status": "ignored"}), 200
###
@app.server.route('/message', methods=['POST'])
def receive_message():
    try:
        message = request.json
        if message.get('action') == 'updateMap':
            location_id = message.get('id')
            print('(receive_message) message.get("id") = ', location_id)
            
             # 手動觸發 `map-update-data` 的變更
            with app.server.app_context():
                data_store = {'data': location_id}  # 包裝成符合 Dash Store 的格式

            # 模擬觸發回調的行為
            return jsonify({"status": "success", "data": location_id}), 200
        else:
            return jsonify({"status": "failed", "error": "Invalid action"}), 400
    except Exception as e:
        print("Error in /message:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

###
@app.server.route('/get_host', methods=['GET'])
def get_host():
    return request.host.split(':')[0]  # 返回伺服器的 IP 地址
###
#start
# 運行應用
if __name__ == '__main__':
    #app.run_server(debug=True)
    app.run_server(host='0.0.0.0', debug=True, port=8799, use_reloader=False)
    #app.run_server(mode="inline", port=8799, use_reloader=False)
    
# 將應用靜態導出為 HTML 文件
#app.run_server(export=True, directory='exported')

# === Resize 偵測用 clientside_callback ===


# === 顯示視窗寬度 callback ===
@app.callback(
    Output('width', 'children'),
    Input('st-width', 'data')
)
def update_width_display(data):
    if data and '目前視窗寬度' in data:
        return f"{data['目前視窗寬度']} px"
    return "尚未取得"