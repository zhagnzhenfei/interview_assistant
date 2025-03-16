import aiohttp
import base64
import os
import requests

from dotenv import load_dotenv
load_dotenv()


def get_baidu_ocr_token():
    """
    获取百度OCR的访问token。
    """

    api_key = os.getenv("OCR_API_KEY")
    secret_key = os.getenv("OCR_SECRET_KEY")
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    payload = ""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)



def baidu_ocr_accurate_basic(image_path, access_token):
    """
    调用百度通用文字识别（高精度版）接口

    参数:
        image_path (str): 本地图片文件路径
        access_token (str): 调用鉴权接口获取的token

    返回:
        dict: 识别结果的JSON数据
    """
    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
    
    # 二进制方式打开图片文件
    with open(image_path, 'rb') as f:
        img = base64.b64encode(f.read())
    
    params = {"image": img}
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(request_url, data=params, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None

# 示例用法
if __name__ == "__main__":
    image_path = "/mnt/d/wsl/project/interview_assistant/test/0b575d36db614da2528a1c2e9306ea5.jpg"  # 替换为你的图片路径
    access_token = os.getenv("ACCESS_TOKEN")    # 替换为你的access_token
    result = baidu_ocr_accurate_basic(image_path, access_token)
    if result:
        print(result)
