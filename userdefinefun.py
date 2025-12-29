## user define function
#
# import os
import geopandas as gpd
# import folium

def _load_layer_to_4326(shp_path: str) -> gpd.GeoDataFrame:
    """讀 shapefile；若非 WGS84 則轉 EPSG:4326。"""
    gdf = gpd.read_file(shp_path, encoding="utf-8")
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    # 清一下字串空白（常見全形/半形）
    for c in gdf.columns:
        if gdf[c].dtype == object:
            gdf[c] = gdf[c].astype(str).str.replace("　","").str.replace(" ","").str.strip()
    return gdf

#
def style_function(feature):
    return {
        'fillColor': 'lightgreen',
        'color': 'black',
        'weight': 2.5,
        'fillOpacity': 0.5,
    }
##
def get_tourist_data():
    import requests
    import pandas as pd
    import os

    API_URL = os.getenv("API_URL")
    if API_URL is None or API_URL.strip() == "":
##      API_URL = "https://ntgisapigithubio-production.up.railway.app"
        # API_URL = "https://ntgisapi.zeabur.app"
        # API_URL = "http://localhost:3000"
        API_URL = "https://dssgisapi-github-io.onrender.com"


    API_URL = API_URL + "/get_tourist_data"
    print(f"Fetching data from: {API_URL}")  # Debugging output

    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)  # Normal case
        # print("DataFrame Columns:", df.columns)  # Debugging output
        # print("First few rows:\n", df.head())  # Debugging output
        
##        print("Raw API Response:", data[:3])  # Debugging output

##        # If the first row is a list of column names, set it explicitly
##        if isinstance(data, list) and isinstance(data[0], list):
##            headers = data[0]  # First row is column headers
##            body = data[1:]    # Actual data
##            
##            # 🔹 Ensure headers match row length by truncating or padding
##            max_columns = max(len(row) for row in body)  # Get the longest row
##            headers = headers[:max_columns]  # Truncate headers if they exceed row length
##            
##            # 🔹 Trim extra columns in data rows
##            fixed_body = [row[:max_columns] for row in body]  # Ensure all rows match max_columns
##            
##            df = pd.DataFrame(fixed_body, columns=headers)  # Assign cleaned headers
##        else:
##            df = pd.DataFrame(data)  # Normal case
        
        # Ensure column names are strings
##        df.columns = df.columns.astype(str)
##        df.columns = df.columns.str.strip()

##        print("DataFrame Columns:", df.columns)  # Debugging output
##        print("First few rows:\n", df.head())  # Debugging output
        
        if 'Zipcode' not in df.columns:
            raise KeyError("Missing 'Zipcode' column in API response")

        return df
    else:
        print("Failed to fetch 全國觀光旅遊景點檔")
        return pd.DataFrame()

def create_vp_dropdown_options(breakpoint_name, zipcode,window_width):
    import pandas as pd
    from dash import no_update
#
    # df = pd.read_csv('./static/newtpe_tourist_att.csv', encoding='utf-8')
    df = get_tourist_data()
    selected_df = df[df['Zipcode'] == zipcode].reset_index(drop=True)
    vp_dropdown_options = [
    {'label': f"{idx+1} {row['Name']}", 'value': row['Name']}
    for idx, row in selected_df.iterrows()
    ]
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", no_update, no_update, vp_dropdown_options
    #
##
def get_unique_zip_area_df():
#
    import pandas as pd
    import re
    from dash import Dash, dcc, html, Output, Input

    # 讀取 "新北市觀光旅遊景點(中文).csv" 檔案
    # df = pd.read_csv('./static/newtpe_tourist_att.csv', encoding='utf-8')
    df = get_tourist_data()

    # 定義從 Add 欄位擷取區域名稱的函數（取兩到三個中文字，結尾為「區」）
    def extract_area_name(address):
        match = re.search(r'新北市\d{3}(.{2,3}區)', address)
        if match:
            return match.group(1)  # 僅提取區域名稱（如「萬里區」）
        return None

    # 創建新的 DataFrame，包含郵遞區號和區域名稱
    zip_area_df = pd.DataFrame({
        '郵遞區號': df['Zipcode'],
        '區域名稱': df['Add'].apply(extract_area_name)
    })

    # 移除重複的郵遞區號及區域名稱組合，並進行排序
    unique_zip_area = zip_area_df.drop_duplicates().dropna().sort_values(by=['郵遞區號', '區域名稱']).reset_index(drop=True)
    return unique_zip_area

### 計算出所選擇區之地理中心點以利定位
def calculate_center_point(data,selected_zipcode):
    # 刪除缺失的Zipcode行
    data = data.dropna(subset=['Zipcode'])

    # 將Zipcode轉換為整數
    # data['Zipcode'] = data['Zipcode'].astype(int)
    print("data['Zipccode']:",type(data['Zipcode'].iloc[0]))
    print("selected_zipcode",type(selected_zipcode))
    # 篩選出指定Zipcode的資料
    selected_data = data[data['Zipcode'] == selected_zipcode]
    print("計算地理中心:",selected_zipcode,"找到筆數：", len(selected_data))

    # 計算該 Zipcode 的地理中心點
    # center_px = selected_data['Px'].mean()
    # center_py = selected_data['Py'].mean()
    center_px = selected_data['Px'].astype(float).mean()
    center_py = selected_data['Py'].astype(float).mean()
    selected_center = [center_py, center_px]
    return selected_center
    
###
def create_map1(breakpoint_name, zipcode, server_ip, window_width):
    import pandas as pd
    import geopandas as gpd
    import folium
    from folium import Map, Marker, Popup
    from folium.plugins import MarkerCluster
    from folium import Element
    import branca
    import io
    import math
    import os
    
    # 讀取大台北鄉鎮市區界圖shpe file(含台北市、新北市)
    # Big_Taipei_data = gpd.read_file('static/shapefiles/Taipei.shp', encoding='utf-8')
    # Ｎew_Taipei_data = Big_Taipei_data[(Big_Taipei_data['COUNTYNAME']=='新北市')]
    # 讀取全國鄉鎮市區界圖及屏東縣瑪家鄉三和村sshpe file
    base_dir = os.path.dirname(__file__)
    town_shp = os.path.join(base_dir, "static", "shapefiles", "TOWN_MOI_1140318.shp")
    sanhe_shp = os.path.join(base_dir, "static", "shapefiles", "Town_Majia_Sanhe.shp")

    # === 讀檔並確保是 WGS84 ===
    Domestic_gdf = _load_layer_to_4326(town_shp)      # 鄉鎮市區界
    Sanhe_gdf    = _load_layer_to_4326(sanhe_shp)     # 三和村（專屬 shapefile）
    
    # 讀取 "新北市觀光旅遊景點(中文).csv" 檔案
    # df = pd.read_csv('./static/newtpe_tourist_att.csv', encoding='utf-8')
    df = get_tourist_data()

    ##計算出某區所有景點之中心點
    selected_center=calculate_center_point(df,zipcode)
    mymap = Map(location=selected_center, zoom_start=12)
    # 將 Shapefile 轉為 GeoJSON 並添加到地圖
    # folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
    # folium.GeoJson(Domestic_data, style_function=style_function).add_to(mymap)
    # folium.GeoJson(Sanhe_data, style_function=style_function).add_to(mymap)
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

    # Add 新北市觀光旅遊景點標記 to the map
    #selected_df = df[df['Zipcode'] == zipcode]
    #for idx, row in selected_df.iterrows():
    #    Marker(location = [row['Py'], row['Px']], popup = row['Name'], icon=folium.Icon(color="green")).add_to(mymap)

    #id及name兩個欄位中，只要任一欄位缺資料，則直接自原始DataFrame刪除該筆資料，不需要新變數。
    #inplace=True:直接修改原始DataFrame，不需要新變數。
    #inplace=False（預設）:原始DataFrame 不受影響，必須用一個新變數來保存結果。
    #df_cleaned = df.dropna(subset=['id', 'name'], inplace=False)
    df.dropna(subset=['Id', 'Name'], inplace=True)
    
    ##
    # 將Zipcode轉換為整數
    # df['Zipcode'] = df['Zipcode'].astype(int)
    ##
    # Add Marker Cluster(地圖上的相鄰觀光旅遊景點標記點(Markers)群組在一起) to the map
    selected_df = df[df['Zipcode'] == zipcode].reset_index(drop=True)
    marker_cluster = MarkerCluster()
    ##
    for idx, row in selected_df.iterrows():
        #if not math.isnan(row['Py'].astype(float)) and not math.isnan(row['Px'].astype(float)):
        if row['Py'] is not None and row['Px'] is not None:
            ##
             # 確保 Name 和 Id 是字符串，並移除特殊字符
            name = str(row['Name']).replace("{", "").replace("}", "")
            id_ = str(row['Id']).replace("{", "").replace("}", "")
            ## 使用 f-string 替代 .format()
            ## popup_html = f"""
            ##    <div id="popup-content" style="width: auto; max-width: 60vx; max-height: 60vh; overflow-y: auto;">
            popup_html = f"""
                <html><body>
                <style> 
                /* popup 內所有按鈕（含 Bootstrap .btn） */
                button, .btn {{
                  /* 透明底但看得見：淡白底 + 清楚邊框 */
                  background: rgba(255,255,255,0.1) !important;   /* 基本透明度 */
                  /* border: 2px solid rgba(0,0,0,0.6) !important; */
                  color: #003366 !important;       /* 深藍，穩重、易讀 */
                  border: 1.5px solid #003366 !important;

                  /* 輕微毛玻璃，讓地圖紋理不搶眼（支援瀏覽器才會生效） */
                  -webkit-backdrop-filter: blur(2px);
                  backdrop-filter: blur(2px);

                  /* 形狀與間距 */
                  border-radius: 10px !important;
                  padding: 6px 12px !important;
                  font-weight: 600;

                  /* 移除瀏覽器/Bootstrap 遺留外觀 */
                  background-image: none !important;
                  box-shadow: 0 1px 2px rgba(0,0,0,0.15) !important;
                  outline: none !important;
                  -webkit-appearance: none !important;
                  -moz-appearance: none !important;
                  appearance: none !important;

                  /* 動畫回饋 */
                  transition: background .15s ease, box-shadow .15s ease, transform .05s ease;
                }}

                /* 滑過更清楚一點 */
                button:hover, .btn:hover {{
                  background: rgba(255,255,255,0.30) !important;
                  box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
                }}

                /* 點下去有壓下感 */
                button:active, .btn:active {{
                  transform: translateY(1px);
                }}

                /* 鍵盤可及性：聚焦外框（不會改變透明感） */
                button:focus-visible, .btn:focus-visible {{
                  box-shadow: 0 0 0 3px rgba(0,123,255,0.35) !important;
                }}
                </style>
                <div>        
                    <b>{name}</b><br>
                    <b>{row['Opentime']}</b><br>
                    <b>{row['Add']}</b><br>
                    <b>{row['Tel']}</b><br><br>
                    <button onclick="openWindow('upload', '{id_}', '{name}', '{server_ip}')">上傳照片</button><br><br>
                    <button onclick="openWindow('download', '{id_}', '{name}', '{server_ip}')">下載照片</button><br><br>
                    <!-- <button onclick="openWindow('edit', '{id_}', '{name}')">填寫相關資訊</button> -->
                </div>
                <script>
                    function openWindow(action, locationId, name, server_ip) {{
                        // server_ip :取自Dash 的 index_string 模板定義
                        let url = '';
                        // let customedomain='https://ntgisgithubio-production.up.railway.app';
                        // let customedomain='https://ntgis.zeabur.app';
                        // let customedomain=`http://${{server_ip}}:8799`;
                        let customedomain='https://dssgis-github-io.onrender.com';
                        if (action === "upload") {{
                            // url = `http://${{server_ip}}:8799/static/upload.html?id=${{locationId}}&name=${{name}}`;
                            url = `${{customedomain}}/static/upload.html?id=${{locationId}}&name=${{name}}`;
                            window.open(url, '上傳照片', 'width=600, height=400');
                        }} else if (action === "download") {{
                            // url = `http://${{server_ip}}:8799/static/download.html?id=${{locationId}}&name=${{name}}`;
                            url = `${{customedomain}}/static/download.html?id=${{locationId}}&name=${{name}}`;
                            window.open(url, '下載照片', 'scrollbars=yes, resizable=yes, width=600, height=400');
                        }} else if (action === "edit") {{
                            // url = `http://${{server_ip}}:8799/static/edit.html?id=${{locationId}}&name=${{name}}`;
                                url = `${{customedomain}}/static/edit.html?id=${{locationId}}&name=${{name}}`;
                                window.open(url, '填寫相關資訊', 'scrollbars=yes, resizable=yes, width=600, height=400');
                        }}   
                        }}
                        // 使標記的Popup跟隨地圖縮放(視窗內)
                        // function updatePopupSize() {{
                        //    let zoom = mymap.getZoom();
                        //    let scaleFactor = Math.min(1.5, Math.max(0.5, zoom / 12));  // 控制 Popup 縮放比例
                        //    document.querySelectorAll(".leaflet-popup-content-wrapper").forEach(popup => {{
                        //        popup.style.transform = `scale(${{scaleFactor}})`;
                        //        popup.style.transformOrigin = "center";
                        //    }});
                        // }}
                        // mymap.on("zoomend", updatePopupSize);

                   // function openWindow(action, locationId, name) {{
                   //     fetch('/get_host')
                   //     .then(response => response.text())
                   //     .then(serverHost => {{
                        //    let url = `http://${{serverHost}}:8799/static/upload.html?id=${{locationId}}&name=${{name}}`;
                        //    window.open(url, '上傳照片', 'width=600, height=400');
                   //           let serverip=`${{serverHost}}`;
                   //     }});
                        //
                   //       let url = '';
                   //       if (action === "upload") {{
                        //      url = `http://0.0.0.0:8799/static/upload.html?id=${{locationId}}&name=${{name}}`;
                   //           url = `http://${{serverip}}:8799/static/upload.html?id=${{locationId}}&name=${{name}}`;
                   //           const newWindow = window.open(url, '上傳照片', 'width=600, height=400');
                   //     }} else if (action === "download") {{
                   //           url = `http://${{serverip}}:8799/static/download.html?id=${{locationId}}&name=${{name}}`;
                   //           const newWindow = window.open(url, '下載照片', 'scrollbars=yes, resizable=yes, width=600, height=400');
                              //const newWindow = window.open(url, '下載照片', 'scrollbars=yes, resizable=yes, width=800, height=600');
                   //     }} else if (action === "edit") {{
                   //           url = `http://localhost:8799/static/edit.html?id=${{locationId}}&name=${{name}}`;
                   //           const newWindow = window.open(url, '填寫相關資訊', 'scrollbars=yes, resizable=yes, width=600, height=400');
                   //           // newWindow.document.write(`<h3>填寫相關資訊 for 景點 ${{locationId}}(${{name}})</h3><button onclick="window.close()">關閉視窗</button>`);
                        // }} else {{
                        //    newWindow.document.write("<h3>404 Page Not Found</h3>");
                        // }}
                        // 確保子視窗加載完成後，綁定 close-window 事件
                        // newWindow.onload = function() {{
                        //    const closeButton = newWindow.document.getElementById('close-window');
                        //    if (closeButton) {{
                        //        closeButton.onclick = function() {{
                        //            newWindow.close();
                        //        }};
                        //    }}
                        //   }};
                    // }}
                    </script>
                </body></html>
            """

            ###
            # 注入 CSS
            css = """
            <style>
            .leaflet-popup-content-wrapper {
                background: rgba(255,255,255,0.6) !important; /* 半透明白底 */
                color: #000 !important; /* 黑色字 */
                font-weight: 500;       /* 稍微加粗，增強對比 */
            }
            .leaflet-popup-content,
            .leaflet-popup-content * {
                color: #000 !important;
                text-shadow: 0px 0px 3px rgba(255, 255, 255, 0.8);
            }
            .leaflet-popup-tip {
                background: rgba(255,255,255,0.6) !important;
            }
            /* 強制覆蓋 Bootstrap 的 .btn */
            /* .leaflet-popup-content button,
            .leaflet-popup-content .btn {
                background-color: transparent !important;
                color: red !important;
                border: 1px solid black !important;
                box-shadow: none !important;
            } */
            </style>
            """
            mymap.get_root().html.add_child(Element(css))
            ###
            ##
            #marker_cluster.add_child(Marker([row['Py'], row['Px']]))
            ##
            #print("(create_map1) popup_html= ", popup_html)
            #iframe = folium.IFrame(popup_html, width=150, height=150)
            # iframe = branca.element.IFrame(popup_html, width=200, height=180)
            # iframe = branca.element.IFrame(popup_html, width=window_width*0.25, height=180)
            iframe = branca.element.IFrame(popup_html, width=window_width*0.25, height=240)
            # popup = folium.Popup(iframe, max_width=200, max_height=180)
            # popup = folium.Popup(iframe, max_width='auto')
            popup = folium.Popup(iframe, max_width=window_width*0.25)
            ##popup = folium.Popup(popup_html, max_width=300)
            ##
            marker_cluster.add_child(Marker(location = [row['Py'], row['Px']], popup = popup, icon=folium.Icon(color="red")))
            mymap.add_child(marker_cluster)
    #
    print("trace 1 on create_map1")
    #
    vp_dropdown_options = [
    #{'label': f"{x+1} {row['Name']}", 'value': row['Name']}
    {'label': f"{idx+1} {row['Name']}", 'value': row['Name']}
    for idx, row in selected_df.iterrows()
    ]
    #
    error_msg=""

    #將地圖保存為 HTML 字串
    mymap.save("static/mymap.html")
    #
    map_io = io.BytesIO()
    mymap.save(map_io, close_file=False)
    map_html = map_io.getvalue().decode()
    #
    print("trace 2 on create_map1")
    #
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", map_html, error_msg
# 斷點處理
def create_map2(breakpoint_name, zipcode, viewpoint, server_ip, window_width):
    import pandas as pd
    import geopandas as gpd
    import folium
    from folium import Marker
    from folium import Element
    #from folium.plugins import MarkerCluster
    import branca
    import io
    import os
    import math
    from dash import no_update
    
    # 讀取大台北鄉鎮市區界圖shpe file(含台北市、新北市)
    # Big_Taipei_data = gpd.read_file('static/shapefiles/Taipei.shp', encoding='utf-8')
    # Ｎew_Taipei_data = Big_Taipei_data[(Big_Taipei_data['COUNTYNAME']=='新北市')]
    
    # 讀取全國鄉鎮市區界圖及屏東縣瑪家鄉三和村sshpe file
    base_dir = os.path.dirname(__file__)
    town_shp = os.path.join(base_dir, "static", "shapefiles", "TOWN_MOI_1140318.shp")
    sanhe_shp = os.path.join(base_dir, "static", "shapefiles", "Town_Majia_Sanhe.shp")

    # === 讀檔並確保是 WGS84 ===
    Domestic_gdf = _load_layer_to_4326(town_shp)      # 鄉鎮市區界
    Sanhe_gdf    = _load_layer_to_4326(sanhe_shp)     # 三和村（專屬 shapefile)
    
    #
    # 讀取 "新北市觀光旅遊景點(中文).csv" 檔案
    # df = pd.read_csv('./static/newtpe_tourist_att.csv', encoding='utf-8')
    df = get_tourist_data()
    
    # Add 新北市觀光旅遊景點標記 to the map
    #selected_df = df[df['Zipcode'] == zipcode]
    #for idx, row in selected_df.iterrows():
    #    Marker(location = [row['Py'], row['Px']], popup = row['Name'], icon=folium.Icon(color="green")).add_to(mymap)

    # Add Marker Cluster(地圖上的相鄰觀光旅遊景點標記點(Markers)群組在一起) to the map
    #selected_df = df[df['Zipcode'] == zipcode and df['Name'] == viewpoint].drop_duplicates()
    # selected_df = df[(df['Zipcode'] == zipcode) & (df['Name'] == viewpoint)].drop_duplicates()
    ##
    print("Debug: Zipcode param =", zipcode, type(zipcode))
    print("Debug: Viewpoint param =", viewpoint, type(viewpoint))
    print("Debug: Sample df Zipcode =", df['Zipcode'].iloc[0], type(df['Zipcode'].iloc[0]))
    print("Debug: Sample df Name =", df['Name'].iloc[0])
    print("Unique Zipcodes in df:", df['Zipcode'].unique())
    print("Unique Names (filtered by zipcode):", df[df['Zipcode']==str(zipcode)]['Name'].unique())
    ##
    # 確保欄位為字串並去除多餘空白
    df['Zipcode'] = df['Zipcode'].astype(str).str.strip()
    df['Name'] = df['Name'].astype(str).str.strip()

    zipcode = str(zipcode).strip()
    viewpoint = str(viewpoint).strip()
    ##
    selected_df = df[((df['Zipcode'] == zipcode) & (df['Name'] == viewpoint)) | (df['Id'] == viewpoint)].drop_duplicates()
    #
    # 確保 selected_df 非空
    if not selected_df.empty:
    # 提取經緯度的單一值
        latitude = selected_df.iloc[0]['Py']
        longitude = selected_df.iloc[0]['Px']
    # 建立地圖min-width: 30vw; 
        mymap = folium.Map(location=[latitude, longitude], zoom_start=12)
    else:
    # 當 selected_df 為空時的處理
        #raise ValueError("selected_df is empty. Cannot determine map location.")
        error_msg="selected_df is empty. Cannot determine map location."

    #mymap = folium.Map(location=[selected_df['Py'], selected_df['Px']], zoom_start=12)
    #
    # 將 Shapefile 轉為 GeoJSON 並添加到地圖
    # folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
    # folium.GeoJson(Domestic_data, style_function=style_function).add_to(mymap)
    # folium.GeoJson(Sanhe_data, style_function=style_function).add_to(mymap)
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
    #
    for idx, row in selected_df.iterrows():
        # if not math.isnan(row['Py']) and not math.isnan(row['Px']):
        if row['Py'] is not None and row['Px'] is not None:
            ###
            ##
             # 確保 Name 和 Id 是字符串，並移除特殊字符
            name = str(row['Name']).replace("{", "").replace("}", "")
            id_ = str(row['Id']).replace("{", "").replace("}", "")
            ## 使用 f-string 替代 .format()
            ## popup_html = f"""
            ##    <div id="popup-content" style="width: auto; max-width: 60vx; max-height: 60vh; overflow-y: auto;">
            # popup_html = f"""
            popup_html = f"""
                <html><body>
                <style> 
                /* popup 內所有按鈕（含 Bootstrap .btn） */
                button, .btn {{
                  /* 透明底但看得見：淡白底 + 清楚邊框 */
                  background: rgba(255,255,255,0.1) !important;   /* 基本透明度 */
                  /* border: 2px solid rgba(0,0,0,0.6) !important; */
                  color: #003366 !important;       /* 深藍，穩重、易讀 */
                  border: 1.5px solid #003366 !important;

                  /* 輕微毛玻璃，讓地圖紋理不搶眼（支援瀏覽器才會生效） */
                  -webkit-backdrop-filter: blur(2px);
                  backdrop-filter: blur(2px);

                  /* 形狀與間距 */
                  border-radius: 10px !important;
                  padding: 6px 12px !important;
                  font-weight: 600;

                  /* 移除瀏覽器/Bootstrap 遺留外觀 */
                  background-image: none !important;
                  box-shadow: 0 1px 2px rgba(0,0,0,0.15) !important;
                  outline: none !important;
                  -webkit-appearance: none !important;
                  -moz-appearance: none !important;
                  appearance: none !important;

                  /* 動畫回饋 */
                  transition: background .15s ease, box-shadow .15s ease, transform .05s ease;
                }}

                /* 滑過更清楚一點 */
                button:hover, .btn:hover {{
                  background: rgba(255,255,255,0.30) !important;
                  box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
                }}

                /* 點下去有壓下感 */
                button:active, .btn:active {{
                  transform: translateY(1px);
                }}

                /* 鍵盤可及性：聚焦外框（不會改變透明感） */
                button:focus-visible, .btn:focus-visible {{
                  box-shadow: 0 0 0 3px rgba(0,123,255,0.35) !important;
                }}
                </style>
                <div>
                    <b>{name}</b><br>
                    <b>{row['Opentime']}</b><br>
                    <b>{row['Add']}</b><br>
                    <b>{row['Tel']}</b><br>
                    <b>{row['Px']}(景點X座標)</b><br>
                    <b>{row['Py']}(景點Y座標)</b><br>
                    <b>{row['Changetime']}(資料異動時間)</b><br><br>
                    <button onclick="openWindow('upload', '{id_}', '{name}', '{server_ip}')">上傳照片</button><br><br>
                    <button onclick="openWindow('download', '{id_}', '{name}', '{server_ip}')">下載照片</button><br><br>
                    <button onclick="openWindow('edit', '{id_}', '{name}', '{server_ip}')">填寫相關資訊</button>
                </div>
                <script>
                        function openWindow(action, locationId, name, server_ip) {{
                            let url = '';
                            // let customedomain='https://ntgisgithubio-production.up.railway.app';  //114/01/21 modified
                            // let customedomain='https://ntgis.zeabur.app';
                            // let customedomain=`http://${{server_ip}}:8799`;
                            let customedomain='https://dssgis-github-io.onrender.com';
                            if (action === "upload") {{
                              // url = `http://${{server_ip}}:8799/static/upload.html?id=${{locationId}}&name=${{name}}`;
                                url = `${{customedomain}}/static/upload.html?id=${{locationId}}&name=${{name}}`;
                                const newWindow = window.open(url, '上傳照片', 'width=600, height=400');
                            }} else if (action === "download") {{
                              // url = `http://${{server_ip}}:8799/static/download.html?id=${{locationId}}&name=${{name}}`;
                                    url = `${{customedomain}}/static/download.html?id=${{locationId}}&name=${{name}}`;
                                    const newWindow = window.open(url, '下載照片', 'scrollbars=yes, resizable=yes, width=600, height=400');
                              //const newWindow = window.open(url, '下載照片', 'scrollbars=yes, resizable=yes, width=800, height=600');
                            }} else if (action === "edit") {{
                              // url = `http://${{server_ip}}:8799/static/edit.html?id=${{locationId}}&name=${{name}}`;
                                    url = `${{customedomain}}/static/edit.html?id=${{locationId}}&name=${{name}}`;
                              // const newWindow = window.open(url, '填寫相關資訊', 'scrollbars=yes, resizable=yes, width=600, height=400, noopener, noreferrer');
                                    const newWindow = window.open(url, '填寫相關資訊', 'scrollbars=yes, resizable=yes, width=600, height=400');
                              if (!newWindow) {{
                                  console.error('子窗口打開失敗，請檢查瀏覽器設置是否阻止彈出窗口。');
                              }}  
                              // newWindow.document.write(`<h3>填寫相關資訊 for 景點 ${{locationId}}(${{name}})</h3><button onclick="window.close()">關閉視窗</button>`);
                            }};
                        }}

                    // 父窗口監聽消息
                    // window.addEventListener('message', function (event) {{
                        // 检查消息来源（可选，确保安全性）
                        // if (event.origin !== 'http://localhost:8799/static/edit.html') return;
                    //    if (event.data && event.data.action === 'updateMap') {{
                    //        console.log(`收到更新地margin-top: 5px圖请求，景點ID: ${{event.data.id}}`);
                            // 向 Dash 發送更新事件
                            // DashRenderer.dispatchEvent({{
                            //    type: 'updateMap',
                            //    payload: event.data.id
                            // }});
                            // 在此處調用刷新邏輯
                            // fetch('/message', {{
                    //        fetch('http://localhost:8799/message', {{
                    //            method: 'POST',
                    //            headers: {{ 'Content-Type': 'application/json' }},
                    //            body: JSON.stringify({{ action: 'updateMap', id: event.data.id }})
                            // }}).then(() => {{
                            //    console.log('地圖刷新請求已發送到後端');
                            //
                    //        }})
                    //        .then(response => {{
                    //            if (!response.ok) {{
                    //                throw new Error(`HTTP error! status: ${{response.status}}`);
                    //            }}
                    //            return response.json();
                    //        }})
                    //        .then(data => console.log('後端響應:', data))
                    //        .catch(error => console.error('後端請求失敗:', error));
                    //     }}
                    // }});
                    // 使標記的Popup跟隨地圖縮放(視窗內)
                    // function updatePopupSize() {{
                    //    let zoom = mymap.getZoom();
                    //    let scaleFactor = Math.min(1.5, Math.max(0.5, zoom / 12));  // 控制 Popup 縮放比例
                    //    document.querySelectorAll(".leaflet-popup-content-wrapper").forEach(popup => {{
                    //        popup.style.transform = `scale(${{scaleFactor}})`;
                    //        popup.style.transformOrigin = "center";
                    //    }});
                    //}}
                    //mymap.on("zoomend", updatePopupSize);
                </script>
                </body></html>
            """
            ##
            ###
            # 注入 CSS
            css = """
            <style>
            .leaflet-popup-content-wrapper {
                background: rgba(255,255,255,0.6) !important; /* 半透明白底 */
                color: #000 !important; /* 黑色字 */
                font-weight: 500;       /* 稍微加粗，增強對比 */
            }
            .leaflet-popup-content,
            .leaflet-popup-content * {
                color: #000 !important;
                text-shadow: 0px 0px 3px rgba(255, 255, 255, 0.8);
            }
            .leaflet-popup-tip {
                background: rgba(255,255,255,0.6) !important;
            }
            /* 強制覆蓋 Bootstrap 的 .btn */
            /* .leaflet-popup-content button,
            .leaflet-popup-content .btn {
                background-color: transparent !important;
                color: red !important;
                border: 1px solid black !important;
                box-shadow: none !important;
            } */
            </style>
            """
            mymap.get_root().html.add_child(Element(css))
            ###
            #marker_cluster.add_child(Marker([row['Py'], row['Px']]))
            ##
            #print("(create_map1) popup_html= ", popup_html)
            #iframe = folium.IFrame(popup_html, width=150, height=150)
            #iframe = branca.element.IFrame(popup_html, width="100%", height="100%")
            #iframe = branca.element.IFrame(popup_html)
            # iframe = branca.element.IFrame(popup_html, width=200, height=180)
            # iframe = branca.element.IFrame(popup_html, width=200, height=220)
            # iframe = branca.element.IFrame(popup_html, width=window_width*0.25, height=220)
            iframe = branca.element.IFrame(popup_html, width=window_width*0.25, height=280)
            # popup = folium.Popup(iframe, max_width="auto")
            # popup = folium.Popup(iframe, max_width=200)
            popup = folium.Popup(iframe, max_width=window_width*0.25)
            # popup = folium.Popup(iframe, max_width=300)
            #popup = folium.Popup(iframe, max_width=200, max_height=180)
            #popup = folium.Popup(popup_html, max_width='auto')
            #popup = folium.Popup(popup_html, max_width=300)
            ##
            ## marker_cluster.add_child(Marker(location = [row['Py'], row['Px']], popup = popup, icon=folium.Icon(color="green")))
            ## mymap.add_child(marker_cluster)
            ###
            ## Marker(location = [row['Py'], row['Px']], popup = row['Name'], icon=folium.Icon(color="green")).add_to(mymap)
            Marker(location = [row['Py'], row['Px']], popup =popup, icon=folium.Icon(color="red")).add_to(mymap)
            # Marker(location = [row['Py'], row['Px']], popup =popup_html, icon=folium.Icon(color="red")).add_to(mymap)
    #
    #vp_dropdown_options = [
    #{'label': f"{x+1} {row['Name']}", 'value': row['Name']}
    #{'label': f"{idx+1} {row['Name']}", 'value': row['Name']}
    #for idx, row in selected_df.iterrows()
    #]
    #
    error_msg=""
    #
    #selected_df = df[df['Zipcode'] == zipcode].reset_index(drop=True)
    #
    #vp_dropdown_options = [
    #{'label': f"{x+1} {row['Name']}", 'value': row['Name']}
    #{'label': f"{idx+1} {row['Name']}", 'value': row['Name']}
    #for idx, row in selected_df.iterrows()
    #]
    #
    #mymap.save("mymap.html")
    #
    # 將地圖保存為 HTML 字串
    map_io = io.BytesIO()
    mymap.save(map_io, close_file=False)
    map_html = map_io.getvalue().decode()

    # ⭐⭐ 最小改動：避免 options 出錯
    # if vp_dropdown_options is no_update:
        # vp_dropdown_options = []

    #return map_html, error_msg, vp_dropdown_options
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", map_html, error_msg
    # return map_html, error_msg, vp_dropdown_options
    #return map_html, error_msg 
    

# 運行應用
#if __name__ == '__main__':
#    exit
