#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   spider_Nexus_file
@Time    :   2020/02/23 18:14:01
@Author  :   Recluse Xu
@Version :   1.0
@Contact :   444640050@qq.com
@License :   (C)Copyright 2017-2022, Recluse
@Desc    :   None
'''

# here put the import lib
import requests
from fake_useragent import UserAgent
import datetime
import time
from lxml import etree
import re
from utils.util import Util
from utils.ini import Conf_ini
from utils.nexus_cookies import get_cookies_by_selenium_login, get_cookies_from_file, get_cookies_by_input, set_cookies_json_location
from utils.location_helper import Location
import json


my_session = requests.session()
ua = UserAgent()
headers = {
    "Connection": "keep-alive",
    "DNT": "1",
    "Host": "www.nexusmods.com",
    "Referer": "https://www.nexusmods.com",
    "TE": "Trailers",
    "Upgrade-Insecure-Requests": "1",
    'User-Agent': ua.firefox,
    }
locate = None

def is_login(my_cookies):
    '''
    @summary: 通过检验cookies,得知是否已经成功登录N网
    '''
    global headers
    response = my_session.get(
        url="https://www.nexusmods.com/monsterhunterworld/mods/1982?tab=images",
        headers=headers,
        cookies=my_cookies
        )
    file_page_html = response.content.decode()

    location = locate.get_resources_folder()+ 'is_login.html'
    with open(location, 'w', encoding='utf-8')as f:
        f.write(file_page_html)
    xpath_data = etree.HTML(file_page_html)
    a = xpath_data.xpath('//*[@id="login"]')
    if len(a) == 0:
        return True
    return False


def get_cookies_info(user_name: str, user_pwd: str):
    '''
    @summary: 获取cookies信息
    @return: cookies:dict
    '''
    
    nexus_cookies_location = locate.get_cookies_txt_file()
    if Util.is_file_exists(nexus_cookies_location):
        Util.info_print('Nexus_Cookies.json存在', 2)
        Util.info_print('尝试通过Nexus_Cookies.json获取Cookies信息', 3)
        my_cookies = get_cookies_from_file()
        # print(my_cookies)
        if is_login(my_cookies):
            Util.info_print('Cookies信息验证成功，', 4)
            return
        else:
            Util.info_print('Cookies信息验证失败，', 4)

    Util.info_print('尝试通过登录N网记录Cookies信息', 2)
    my_cookies = get_cookies_by_selenium_login(user_name, user_pwd)
    if my_cookies is not None:
        return my_cookies

    Util.info_print('尝试通过手动输入, 获知Cookies信息', 2)
    my_cookies = get_cookies_by_input()
    if is_login(my_cookies):
        Util.info_print('Cookies信息验证成功，', 4)
    else:
        Util.info_print('Cookies信息验证失败，', 4)
        Util.warning_and_exit(1)
    return my_cookies


def spider_mod_file_page():
    '''
    @summary: 爬虫得到 MOD 的文件页
    @return: session
    '''
    try:
        response = my_session.get(
            url="https://www.nexusmods.com/monsterhunterworld/mods/1982?tab=files",
            headers=headers)
        file_page_html = response.content.decode()
        # print(file_page_html)
        location = locate.get_resources_folder() + 'mod_file_page.html'
        with open(location, 'w', encoding='utf-8')as f:
            f.write(file_page_html)
        headers['Referer'] = "https://www.nexusmods.com/monsterhunterworld/mods/1982?tab=files"
        return file_page_html
    except Exception as e:
        print("失败", e)
        Util.warning_and_exit(1)


def get_mod_file_page(is_safe_to_spide: bool):
    '''
    @summary: 获取 Stracker\'s Loader 的文件页
    @return: 网页:str, 使用了爬虫:bool
    '''
    if is_safe_to_spide:
        Util.info_print('通过爬虫得到 "Stracker\'s Loader" 文件页', 2)
        page_html = spider_mod_file_page()
        is_spider = True
    else:
        Util.info_print('由于爬虫等待时间未过，从本地记录中获取', 2)
        location = locate.get_resources_folder() + 'mod_file_page.html'
        with open(location, 'r')as f:
            page_html = f.read()
            is_spider = False
    Util.info_print('获取成功', 3)
    return page_html, is_spider


def analyze_mod_file_page(html: str):
    '''
    @summary: 解析得到 MOD 的文件页,得到一些数据保存到配置中，并返回下载页数据
    @return: 最新版发布的时间, 最新版下载的URL
    '''
    try:
        xpath_data = etree.HTML(html)
        a = xpath_data.xpath('//*[@id="file-expander-header-9908"]//div[@class="stat"]/text()')
        a = a[0].strip()
        last_publish_date = datetime.datetime.strptime(a, r"%d %b %Y, %I:%M%p")

        a = xpath_data.xpath('//*[@id="file-expander-header-9908"]')[0]
        last_download_url = a.xpath('..//a[@class="btn inline-flex"]/@href')[1]

        return last_publish_date, last_download_url
    except Exception as e:
        print("失败", e)
        Util.warning_and_exit(1)


def spider_download_file_page(download_page_url):
    '''
    @summary: 爬虫得到 MOD 的文件页
    @return: 下载页html:str
    '''
    try:
        response = my_session.get(url=download_page_url, headers=headers)
        download_page_html = response.content.decode()

        location = locate.get_resources_folder() + "mod_download_page.html"
        with open(location, 'w', encoding='utf-8')as f:
            f.write(download_page_html)
        headers['Referer'] = download_page_url
        return download_page_html
    except Exception as e:
        print("失败", e)
        Util.warning_and_exit(1)


def analyze_download_file_page(html: str):
    '''
    @summary: 解析 MOD 的下载页
    @return: file_id, game_id
    '''
    try:
        file_id = re.search(r"const file_id = \d+", html).group()[16:]
        game_id = re.search(r"const game_id = \d+", html).group()[16:]
        return file_id, game_id

    except Exception as e:
        print("失败", e)
        Util.warning_and_exit(1)


def spider_download_file(file_id, game_id):
    '''
    @summary: 根据留在页面上的ajax信息,向N网服务器提交请求得到下载链接
    @return: 下载用的url:str , 文件类型:str
    '''
    data = {
            "fid": file_id,
            "game_id": game_id,
        }
    ajax_head = headers.copy()
    ajax_head['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
    ajax_head['Origin'] = 'https://www.nexusmods.com'
    try:
        url = "https://www.nexusmods.com/Core/Libs/Common/Managers/Downloads?GenerateDownloadUrl"
        response = my_session.post(url=url, headers=ajax_head, data=data, cookies=get_cookies_from_file())
        download_url_str = response.content.decode("utf-8")
        download_url = json.loads(download_url_str)['url']
        file_type = re.search(r'\.[a-z]+\?', download_url).group()[1:-1]

        location = locate.get_resources_folder() + "download_file_url.json"
        with open(location, 'w', encoding='utf-8')as f:
            f.write(file_type+"="+download_url)

        return download_url, file_type
    except Exception as e:
        print("失败", e)


def downloadFile(url, location, dl_host):
    '''
    @summary: 下载MOD文件
    '''
    Util.info_print("开始下载\t", 2)

    def formatFloat(num):
        return '{:.2f}'.format(num)

    download_head = headers.copy()
    download_head['Host'] = dl_host

    with open(location, 'wb')as f:
        count = 0
        count_tmp = 0
        time_1 = time.time()
        response = my_session.get(url, stream=True, headers=download_head, cookies=get_cookies_from_file())
        content_length = float(response.headers['content-length'])
        for chunk in response.iter_content(chunk_size=1):
            if chunk:
                f.write(chunk)
                count += len(chunk)
                if time.time() - time_1 > 2:
                    p = count / content_length * 100
                    speed = (count - count_tmp) / 1024 /2
                    count_tmp = count
                    Util.info_print(formatFloat(p) + '%' + ' Speed: ' + formatFloat(speed) + 'KB/S', 3)
                    time_1 = time.time()

    Util.info_print("文件已保存为\t" + location, 3)
    time.sleep(1)


def first_time_run():
    '''
    @summary: 第一次运行的工作
    '''
    Util.info_print('初始化')
    Util.info_print('创建resources目录', 1)
    location = locate.get_resources_folder()[:-1]
    Util.creat_a_folder(location)

    Util.info_print('创建lib目录', 1)
    location = locate.get_lib_folder()[:-1]
    Util.creat_a_folder(location)

    if Util.is_file_exists(locate.get_mhw_dinput8_file()):
        Util.info_print('尝试获取 StrackerLoader-dinput8.dll 的 MD5', 2)
        dinput8_dll_md5 = Util.get_file_MD5(locate.get_mhw_dinput8_file()) 
    else:
        dinput8_dll_md5 = ""

    to_install_VC()

    Util.info_print('创建conf.ini', 1)
    print('这次输入的信息会记录在conf.ini中，如果需要更改，用记事本修改conf.ini的内容即可')
    N_name = input('请输入N网账号或邮箱:')
    N_pwd = input('请输N网密码:')
    Conf_ini.creat_new_conf_ini(locate.get_conf_file(), dinput8_dll_md5, N_name, N_pwd)


def is_first_time_run():
    '''
    @summary: 根据conf.ini文件是否存在,判断是否是第一次运行
    @return: bool
    '''
    return not Util.is_file_exists(locate.get_run_folder()+'conf.ini')


def to_install_VC():
    '''
    @summary: 询问安装VC
    '''
    Util.info_print('需要安装VC吗？', 1)
    Util.info_print('这个是StrackerLoade的运行库。没有安装这个,但安装了StrackerLoade，会进不了游戏。', 2)
    Util.info_print('要是你不确定是否已经安装，那么建议安装.', 2)
    Util.info_print('输入y开始下载安装，输入其他跳过', 2)
    a = input('->')
    if a == "y":
        vc_x64_url = "https://download.visualstudio.microsoft.com/download/pr/3b070396-b7fb-4eee-aa8b-102a23c3e4f4/40EA2955391C9EAE3E35619C4C24B5AAF3D17AEAA6D09424EE9672AA9372AEED/VC_redist.x64.exe"
        vc_location = locate.get_resources_folder() + 'VCx64.exe'
        downloadFile(vc_x64_url, vc_location, "download.visualstudio.microsoft.com")
        Util.run_a_exe(vc_location)


def init_locate():
    '''
    @summary: 初始化路径信息
    '''
    global locate
    locate = Location()
    set_cookies_json_location(locate.get_resources_folder()+'Nexus_Cookies.txt')


def run():
    print("本程序由Recluse制作")
    print("本程序用于一键更新前置MOD-StrackerLoader")
    print("本程序不会用于盗号, 偷取信息 等非法操作")
    print("但由于源码是公开的, 可能存在被魔改成盗号程序的可能。故建议从github获取本程序。")
    print("github地址：https://github.com/RecluseXU/CheckStrackerLoader")
    print("B站联系地址：https://www.bilibili.com/video/av91993651")
    print("输入回车键开始")
    input('->')

    init_locate()

    # 信息获取
    if is_first_time_run():
        first_time_run()

    Util.info_print('检查StrackerLoader安装状态', 1)
    is_installed = Util.is_file_exists(locate.get_mhw_dinput8_file())
    Util.info_print('安装状态:\t'+str(is_installed), 2)

    Util.info_print('尝试获取 conf.ini信息', 1)
    Util.info_print('读取conf.ini', 2)
    conf_ini = Conf_ini(locate.get_run_folder())

    Util.info_print('尝试获取 Cookies 信息', 1)
    username, userpwd = conf_ini.get_nexus_account_info()
    get_cookies_info(username, userpwd)

    Util.info_print("获取MOD信息")
    Util.info_print('尝试获取N网 "Stracker\'s Loader" 文件信息页', 1)
    file_page_html, is_spider = get_mod_file_page(conf_ini.is_safe_to_spide())
    if is_spider:  # 更新最后一次爬虫的时间信息
        conf_ini.set_new_last_spide_time()

    Util.info_print(r'尝试分析文件页，得到 "Stracker\'s Loader" 最新版信息', 1)
    last_publish_date, last_download_url = analyze_mod_file_page(file_page_html)
    Util.info_print("最新版本上传日期\t" + str(last_publish_date), 2)
    Util.info_print("最新版本下载地址\t" + last_download_url, 2)
    last_publish_timeStamp = Util.transform_datetime_to_timeStamp(last_publish_date)
    installed_version_timeStamp = conf_ini.get_installed_SL_upload_date()
    if is_installed and last_publish_timeStamp == installed_version_timeStamp:
        Util.info_print("已安装的版本与最新版发布时间一致，无需更新")
        Util.warning_and_exit()

    Util.info_print('尝试获取N网 "Stracker\'s Loader" 最新版文件下载页', 1)
    download_page_html = spider_download_file_page(last_download_url)
    Util.info_print('尝试分析N网 "Stracker\'s Loader" 最新版文件下载页', 1)
    file_id, game_id = analyze_download_file_page(download_page_html)
    Util.info_print('game_id\t'+game_id, 2)
    Util.info_print('file id\t'+file_id, 2)

    Util.info_print('尝试获取N网 "Stracker\'s Loader" 最新版文件下载url', 1)
    download_url, file_type = spider_download_file(file_id, game_id)
    Util.info_print("最新版文件下载url\t" + download_url, 2)
    Util.info_print("最新版文件类型\t" + file_type, 2)

    Util.info_print('尝试下载"Stracker\'s Loader" 最新版文件', 1)
    dl_loader_location = locate.get_resources_folder() + 'StrackerLoader.' + file_type
    downloadFile(download_url, dl_loader_location, 'cf-files.nexusmods.com')

    Util.info_print("信息处理")
    Util.info_print('尝试解压"Stracker\'s Loader" 文件', 1)
    if file_type == 'zip':
        Util.unzip_all(dl_loader_location, locate.get_dl_loader_folder(), '')

    Util.info_print('尝试获取刚下载的"Stracker\'s Loader" 文件MD5', 1)
    dl_dll_location = locate.get_dl_loader_folder() + 'dinput8.dll'
    download_dll_md5 = Util.get_file_MD5(dl_dll_location)
    Util.info_print('刚下载的"Stracker\'s Loader" dll-MD5:\t'+download_dll_md5, 2)
    if is_installed and conf_ini.get_installed_mod_ddl_md5() == download_dll_md5:
        Util.info_print('刚下载的文件MD5 与 已安装的文件MD5一致, 无需更新', 2)
    else:
        Util.info_print('尝试覆盖安装', 1)
        Util.info_print('覆盖安装dinput8.dll', 2)
        Util.copy_file(dl_dll_location, locate.get_mhw_dinput8_file())
        Util.info_print('覆盖安装dinput-config.json', 2)
        dl_dinputconfig_location = locate.get_dl_loader_folder() + 'dinput-config.json'
        mhw_dinputconfig_location = locate.get_mhw_folder() + 'dinput-config.json'
        Util.copy_file(dl_dinputconfig_location, mhw_dinputconfig_location)
    Util.info_print('更新安装信息', 2)
    Util.info_print('更新 已安装版本N网作者上传时间信息', 3)
    conf_ini.set_installed_SL_upload_date(last_publish_date)
    Util.info_print('更新 已安装版本DLL的MD5 信息', 3)
    conf_ini.set_installed_mod_ddl_md5(download_dll_md5)

    locate.save_to_conf_ini_file()
    print('程序运行完毕\n3DM biss\n')
    Util.warning_and_exit(0)


# def init_webbrowser_driver(): 
#     # chrome 尝试
    # import requests
    # from lxml import etree
    # url_base = "http://npm.taobao.org"

    # r = requests.get("http://npm.taobao.org/mirrors/chromedriver/")
    # html = r.content.decode()
    # xpath_data = etree.HTML(html)
    # a = xpath_data.xpath('///html/body/div[1]/pre/a')[2:]

    # download_page_url_list = list()
    # for i in a:
    #     if i.xpath('./text()')[0].find("icon") != -1:
    #         break
    #     download_page_url_list.append(url_base + i.xpath('./@href')[0] + "chromedriver_win32.zip")
    
#     for i in download_page_url_list:
#         print(i)

#     Util.creat_a_folder(Util.get_lib_folder()+'chromedriver')
#     i = 0
#     Util.creat_a_folder(Util.get_lib_folder()+'chromedriver\\buffer')
#     for url in download_page_url_list:
#         location = Util.get_lib_folder()+'chromedriver\\buffer\\' + str(i) + '.zip'
#         t_headers = {g
#             'Host': "cdn.npm.taobao.org",
#             'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}
#         response = requests.get(url, stream=True, headers=t_headers)
#         with open(location, 'wb')as f:
#             f.write(response.content)
#         i = i+1

#         unzip_location = Util.get_lib_folder()+'chromedriver\\' + str(i) + '.zip'
#         Util.unzip_all(location, unzip_location, '')   

        
if __name__ == "__main__":
    run()
    
    # is_login(get_cookies_from_file())
    # print()
    # init_webbrowser_driver()
    # spider_download_file(9908, 2531)
    
    # run_folder_location = Util.get_run_folder()
    # downloaded_mod_location = run_folder_location+'\\resources\\StrackerLoader.' + "zip"
    # downloaded_mod_unpack_location = run_folder_location+'\\resources\\StrackerLoade\\'
    # Util.unzip_all(downloaded_mod_location, downloaded_mod_unpack_location, '')
    # a = is_first_time_run()
    # print(a)
    # print('3DM Biss')