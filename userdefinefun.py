## user define function
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
        API_URL = "https://ntgisapi.zeabur.app"


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
        print("Failed to fetch 新北觀光旅遊檔")
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
    #data['Zipcode'] = data['Zipcode'].astype(int)

    # 篩選出指定Zipcode的資料
    selected_data = data[data['Zipcode'] == selected_zipcode]

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
    import branca
    import io
    import math
    
    # 讀取大台北鄉鎮市區界圖shpe file(含台北市、新北市)
    Big_Taipei_data = gpd.read_file('static/shapefiles/Taipei.shp', encoding='utf-8')
    Ｎew_Taipei_data = Big_Taipei_data[(Big_Taipei_data['COUNTYNAME']=='新北市')]
    #
    # 讀取 "新北市觀光旅遊景點(中文).csv" 檔案
    # df = pd.read_csv('./static/newtpe_tourist_att.csv', encoding='utf-8')
    df = get_tourist_data()

    ##計算出某區所有景點之中心點
    selected_center=calculate_center_point(df,zipcode)
    mymap = Map(location=selected_center, zoom_start=12)
    # 將 Shapefile 轉為 GeoJSON 並添加到地圖
    folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
    
    # Add 新北市觀光旅遊景點標記 to the map
    #selected_df = df[df['Zipcode'] == zipcode]
    #for idx, row in selected_df.iterrows():
    #    Marker(location = [row['Py'], row['Px']], popup = row['Name'], icon=folium.Icon(color="green")).add_to(mymap)

    #id及name兩個欄位中，只要任一欄位缺資料，則直接自原始DataFrame刪除該筆資料，不需要新變數。
    #inplace=True:直接修改原始DataFrame，不需要新變數。
    #inplace=False（預設）:原始DataFrame 不受影響，必須用一個新變數來保存結果。
    #df_cleaned = df.dropna(subset=['id', 'name'], inplace=False)
    df.dropna(subset=['Id', 'Name'], inplace=True)
    
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
                <div id="popup-content" style="max-width: 98vw; max-height: 98vh; font-size: 14px;">        
                    <b>{name}</b><br>
                    <b>{row['Opentime']}</b><br>
                    <b>{row['Add']}</b><br>
                    <b>{row['Tel']}</b><br><br>
                    <button style="width: 100%;" onclick="openWindow('upload', '{id_}', '{name}', '{server_ip}')">上傳照片</button><br><br>
                    <button style="width: 100%;" onclick="openWindow('download', '{id_}', '{name}', '{server_ip}')">下載照片</button><br><br>
                    <!-- <button onclick="openWindow('edit', '{id_}', '{name}')">填寫相關資訊</button> -->
                    <script>
                        function openWindow(action, locationId, name, server_ip) {{
                            // server_ip :取自Dash 的 index_string 模板定義
                            let url = '';
                            // let customedomain='https://ntgisgithubio-production.up.railway.app';
                            let customedomain='https://ntgis.zeabur.app';
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
                </div>
            """


            ##
            #marker_cluster.add_child(Marker([row['Py'], row['Px']]))
            ##
            #print("(create_map1) popup_html= ", popup_html)
            #iframe = folium.IFrame(popup_html, width=150, height=150)
            # iframe = branca.element.IFrame(popup_html, width=200, height=180)
            iframe = branca.element.IFrame(popup_html, width=window_width*0.25, height=180)
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
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", map_html, error_msg, vp_dropdown_options
# 斷點處理
def create_map2(breakpoint_name, zipcode, viewpoint, server_ip, window_width):
    import pandas as pd
    import geopandas as gpd
    import folium
    from folium import Marker
    #from folium.plugins import MarkerCluster
    import branca
    import io
    import math
    from dash import no_update
    
    # 讀取大台北鄉鎮市區界圖shpe file(含台北市、新北市)
    Big_Taipei_data = gpd.read_file('static/shapefiles/Taipei.shp', encoding='utf-8')
    Ｎew_Taipei_data = Big_Taipei_data[(Big_Taipei_data['COUNTYNAME']=='新北市')]
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
    folium.GeoJson(New_Taipei_data, style_function=style_function).add_to(mymap)
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
                <!-- <style> 
                /* 手機:地圖標記popup縮小比例 */
                /* @media (min-width: 150px) {{
                    #popup-content {{
                        transform: scale(0.6, 0.6);
                        background: red;
                    }}
                }} */
                /* 平板:地圖標記popup縮小比例 */
                /* @media (min-width: 768px) {{
                    #popup-content {{
                        transform: scale(0.8, 0.8);
                        background: orange;
                    }}
                }} */
                /* 電腦螢幕:地圖標記popup縮小比例 */
                /* @media (min-width: 992px) {{
                    #popup-content {{
                        transform: scale(1.0, 1.0);
                        background: green;
                    }}
                }} */
                 </style> -->
                <div id="popup-content" style="max-width: 98vw; max-height: 98vh; font-size: 14px; position: relative;">
                    <b>{name}</b><br>
                    <b>{row['Opentime']}</b><br>
                    <b>{row['Add']}</b><br>
                    <b>{row['Tel']}</b><br>
                    <b>{row['Px']}(景點X座標)</b><br>
                    <b>{row['Py']}(景點Y座標)</b><br>
                    <b>{row['Changetime']}(資料異動時間)</b><br><br>
                    <button style="width: 100%;" onclick="openWindow('upload', '{id_}', '{name}', '{server_ip}')">上傳照片</button><br><br>
                    <button style="width: 100%;" onclick="openWindow('download', '{id_}', '{name}', '{server_ip}')">下載照片</button><br><br>
                    <button style="width: 100%;" onclick="openWindow('edit', '{id_}', '{name}', '{server_ip}')">填寫相關資訊</button>
                <script>
                        function openWindow(action, locationId, name, server_ip) {{
                            let url = '';
                            // let customedomain='https://ntgisgithubio-production.up.railway.app';  //114/01/21 modified
                            let customedomain='https://ntgis.zeabur.app';
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
            </div>
            """
            ##
            #marker_cluster.add_child(Marker([row['Py'], row['Px']]))
            ##
            #print("(create_map1) popup_html= ", popup_html)
            #iframe = folium.IFrame(popup_html, width=150, height=150)
            #iframe = branca.element.IFrame(popup_html, width="100%", height="100%")
            #iframe = branca.element.IFrame(popup_html)
            # iframe = branca.element.IFrame(popup_html, width=200, height=180)
            # iframe = branca.element.IFrame(popup_html, width=200, height=220)
            iframe = branca.element.IFrame(popup_html, width=window_width*0.25, height=220)
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
    return f"(斷點名稱: {breakpoint_name} 視窗寬度: {window_width} px)", map_html, error_msg, no_update     # vp_dropdown_options 保持現值，不改變
    # return map_html, error_msg, vp_dropdown_options
    #return map_html, error_msg 
    

# 運行應用
#if __name__ == '__main__':
#    exit
