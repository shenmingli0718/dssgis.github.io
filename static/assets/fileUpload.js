var ok = 0;
var filecount = 0;
var allChunks = 0;
const chunkSize = 1024 * 1024; // 每塊 1MB
const progressBar = document.getElementById('uploadProgress');

document.getElementById('fileInput').addEventListener('change', (event) => {
    const files = event.target.files;
    allChunks = 0;
    for (let i=0; i < files.length; i++) {
        if (files[i]) {
            allChunks = allChunks + Math.ceil(files[i].size / chunkSize);
        }
    }

    //檢查上傳資料夾空間大小限制
    try {
        check_capacitylimit(allChunks); // 檢查容量限制
    } catch (error) {
        console.error('上傳被阻止:', error.message);
        return; // 停止上傳
    }
    
    ok = 0;
    progressBar.value = 0;
    filecount = files.length;
    
    //解析 URL 查詢參數
    const params = getQueryParams();
    const subid = params.id.split('_').slice(-1)[0]; // 使用 slice(-1)[0] 取最後一部分
    
    for (let i=0; i < files.length; i++) {
        if (files[i]) {
            uploadFile(files[i],subid);
        }
    }
    //alert(`上傳 ${(files.length).toString()} 個 ${ok.toString()} 成功!`);
    //document.getElementById('label').innerHTML = '上傳 ' + filecount.toString() + ' 個檔, 其中 ' + ok.toString() + ' 個檔上傳成功！';
    });
//
// 解析 URL 查詢參數
        function getQueryParams() {
            const params = new URLSearchParams(window.location.search);
            return {
                id: params.get('id'),
                name: params.get('name'),
            };
        }
//
async function uploadFile(file,subid) {    
    //const chunkSize = 1024 * 1024; // 每塊 1MB
    const totalChunks = Math.ceil(file.size / chunkSize);
    //const progressBar = document.getElementById('uploadProgress');
    //progressBar.value = 0;

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start = chunkIndex * chunkSize;
        const chunk = file.slice(start, start + chunkSize);
        
        const formData = new FormData();
        formData.append('fileChunk', chunk);
        formData.append('chunkIndex', chunkIndex);
        formData.append('fileName', file.name);
        formData.append('totalChunks', totalChunks);
        formData.append('subid', subid);

        try {
            // const response = await fetch('http://localhost:3000/2025_aut_Python_proj', {
            const response = await fetch('/2025_aut_Python_proj', {    
            // const response = await fetch('https://ntgisapigithubio-production.up.railway.app/2024_aut_Python_proj', {
            // const response = await fetch('https://ntgisapi.zeabur.app/2024_aut_Python_proj', {
                method: 'POST',
                body: formData,
            });
            document.getElementById('label').innerHTML = file.name + ' 上傳中...';
            if (!response.ok) {
                throw new Error(`${file.name}: failed to upload chunk ${chunkIndex}`);
            }

            // 更新進度條
            progressBar.value = progressBar.value + ((chunkIndex + 1) / allChunks) * 100;
        } catch (error) {
            console.error(error);
            alert(`${file.name}: Chunk ${chunkIndex} upload failed. Retrying...${error}`);
            chunkIndex--; // 重試當前區塊
        }
    }

    //alert(`${file.name} 上傳成功!`);
    ++ok;
    document.getElementById('label').innerHTML = '上傳 ' + filecount.toString() + ' 個檔, 其中 ' + ok.toString() + ' 個檔上傳成功！';
}

async function check_capacitylimit(uploadChunks) {
    const formData = new FormData();
    formData.append('uploadChunks', uploadChunks);

    try {
        //  const response = await fetch('http://localhost:3000/check_capacity_limit', {
        const response = await fetch('/check_capacity_limit', {
        // 
        // const response = await fetch('https://ntgisapigithubio-production.up.railway.app/check_capacity_limit', {
        // const response = await fetch('https://ntgisapi.zeabur.app/check_capacity_limit', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error);
        }

        const data = await response.json();
        console.log(data.message); // 顯示成功訊息
    } catch (error) {
        console.error(error.message);
        alert(error.message); // 顯示具體錯誤提示
        throw error; // 終止後續上傳流程
    }
}
