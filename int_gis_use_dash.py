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
from userdefinefun import get_unique_zip_area_df
from userdefinefun import create_map1, create_map2
from userdefinefun import style_function
from userdefinefun import create_vp_dropdown_options
from dash import no_update
from flask import request
from flask_cors import CORS
from flask import jsonify

# 移除重複的郵遞區號及區域名稱組合，並進行排序
unique_zip_area = get_unique_zip_area_df()

# 將資料轉換為 Dash 下拉選單格式
dropdown_options = [
    {'label': f"{row['郵遞區號']} {row['區域名稱']}", 'value': row['郵遞區號']}
    for _, row in unique_zip_area.iterrows()
]

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
    
    # 讀取大台北鄉鎮市區界圖shpe file(含台北市、新北市)
    # Big_Taipei_data = gpd.read_file('static/shapefiles/Taipei.shp', encoding='utf-8')
    shapefile_path = os.path.join(os.path.dirname(__file__), 'static', 'shapefiles', 'Taipei.shp')
    Big_Taipei_data = gpd.read_file(shapefile_path, encoding='utf-8')
    Ｎew_Taipei_data = Big_Taipei_data[(Big_Taipei_data['COUNTYNAME']=='新北市')]
    
    ##
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
        if name != "石碇區石碇里":
           popup="<div style='font-size: 24px;'>" +getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude) + "</div>"
        else:
            popup="<div style='font-size: 24px;'>" + "新北市中心位置：" + "<br>" + getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude) + "</div>"

        mymap = folium.Map(location=[getLoc.latitude, getLoc.longitude], zoom_start=12)
        Marker([getLoc.latitude, getLoc.longitude], popup=popup, icon=folium.Icon(color="red")).add_to(mymap)
        # 將 Shapefile 轉為 GeoJSON 並添加到地圖
        folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
        error_msg=""
    else:
        getLoc = loc.geocode(name)
        if getLoc is not None:
            popup=getLoc.address + "<br>" + str(getLoc.latitude) + "<br>" + str(getLoc.longitude)
            mymap = folium.Map(location=[getLoc.latitude, getLoc.longitude], zoom_start=12)
            Marker([getLoc.latitude, getLoc.longitude], popup=popup).add_to(mymap)
            # 將 Shapefile 轉為 GeoJSON 並添加到地圖
            folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
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
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", map_html, error_msg, no_update 

# 全域變數
# g_width = 1000  # 預設寬度
# App Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div(id='window-size-display'),
            WindowBreakpoints(
                id="breakpoints",
                # Define the breakpoint thresholds
                # widthBreakpointThresholdsPx=[800, 1200],
                widthBreakpointThresholdsPx=[575, 767, 991, 1199],
                # And their name, note that there is one more name than breakpoint thresholds
                widthBreakpointNames=["xs", "sm", "md", "lg", "xl"],
            ),
            # html.Div([
            #     html.Span("目前視窗寬度: "),
            #     html.Span(id='width-display')
            # ]),
            #  dcc.Interval(id="init-load-trigger", interval=100, n_intervals=0, max_intervals=1),
            #  dcc.Interval(id="init-load-trigger", interval=1000, n_intervals=0, max_intervals=1),
            # dcc.Interval(id='interval', interval=1000, n_intervals=0)  # 為了觸發第一次 clientside callback
            # dcc.Interval(id='interval', interval=1000, n_intervals=0, max_intervals=1),  # 為了觸發第一次 clientside callback
            # html.Div(id='dummy-trigger', style={'display': 'none'}),
            # html.Div([
            #     html.Span("目前視窗寬度: "),
            #    fun html.Span(id='width',value=0)   
            # ]),
            html.Div([
                dcc.Location(id='url', refresh=False),
                html.Div(id='page-content')
            ]),
            html.H4("互動式GIS系統2.0", className='text-center mb-4'),
            dbc.Label("請輸入世界各地任一地點名稱:"),
            dcc.Input(id='name-input', type='text', value=""),            
            html.Br(),
            dbc.Button("繪製地圖(世界範圍)", id="generate-map-btn1", color="primary", className="mt-2"),
            dbc.Label("-----------------------------------"),
            html.Br(),
            html.Div([
                html.Label("新北市觀光旅遊景點位置查詢"),
                html.Label("點選新北市郵遞區號及區域名稱"),
                html.Br(),
                dcc.Dropdown(
                    id='zip-area-dropdown',
                    options=dropdown_options,
                    placeholder="選擇新北市郵遞區號及區域名稱",
                ),
            ]),
            dbc.Button("繪製地圖(新北市範圍)", id="generate-map-btn2", color="primary", className="mt-2"),
            #dbc.Button("區景點瀏覽", id="viewpoint-qry-btn", color="primary", className="mt-2"),
            html.Br(),
            html.Br(),
            dcc.Dropdown(
                id='viewpoint-dropdown',
                #   options=vp_dropdown_options,
                placeholder="選擇區內景點名稱",
            ),
            html.Br(),
            #html.Div(id='error-message', style={'color': 'red', 'margin-top': '10px'}),
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

# Callback 更新地圖
@app.callback(
    Output("window-size-display", "children"),
    Output('map', 'srcDoc'), 
    Output('error-message', 'children'),
    Output('viewpoint-dropdown', 'options'),  # 更新地圖和錯誤訊息
    #[Input('generate-map-btn', 'n_clicks')],
    #[Input('latitude-input', 'value'), Input('longitude-input', 'value')]
    Input("breakpoints", "widthBreakpoint"),
    #Input('width', 'children'),
    # Input('width', 'data'),
    Input('generate-map-btn1', 'n_clicks'),  # 按鈕點擊事件觸發
                                             # 使用 Input 監聽按鈕點擊事件：按鈕的點擊事件觸發地圖更新。
    Input('generate-map-btn2', 'n_clicks'), 
    Input('zip-area-dropdown', 'value'),
    State('name-input', 'value'),   # 名稱或地址 # 使用 State 來儲存緯度和經度數值：避免在按鈕點擊之前緯度和經度變化時觸發回調。
    State('viewpoint-dropdown', 'value'),
    State("breakpoints", "width")

    # State('st-width', 'data')
    #state('viewpoint-dropdown', 'value')
)
##
def update_map_and_dropdown(breakpoint_name: str, map_clicks1, map_clicks2, zipcode, name, viewpoint, window_width: int):
                           
    # ***** Initialize default values
    #map_html = "<p>No map data available.</p>"  # Default or empty map HTML
    #error_msg = ""  # No error initially
    #viewpoint_options = []  # Default empty options
    #
    ctx = dash.callback_context  # 用於判斷哪個輸入觸發了回調
    triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]
    # 如果是 zip-area-dropdown 觸發的回調，更新 viewpoint-dropdown 的選項
    if triggered_input == 'zip-area-dropdown':
        return create_vp_dropdown_options(breakpoint_name,zipcode,window_width) 
    elif triggered_input in ['generate-map-btn1', 'generate-map-btn2']:
    # 當按鈕點擊後，根據 name 和 zipcode 判斷要生成哪種地圖
        if name:
            if map_clicks1 is not None:
                return create_map(breakpoint_name,name,window_width)  # 優先使用 name
        elif zipcode:
            if map_clicks2 is not None:
                if not viewpoint: 
                    return create_map1(breakpoint_name,zipcode,server_ip,window_width)
                    print("trace 1 on create_map1")
                else:
                    return create_map2(breakpoint_name,zipcode,viewpoint,server_ip,window_width)
                    # else:
                        # return no_update, no_update, no_update 
        else:
            return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)",no_update, no_update, no_update   # 必須
    else:
        # 初始狀態，當 n_clicks 為 None 時顯示默認地圖
        name = name if name else "石碇區石碇里"  # 預設地點
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