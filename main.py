from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import json

COOKIE_FILE = "cookies.json"
Data_Folder = "./output"
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "chromedriver")

# 需要下载电子书的id列表
Download_Book_List = [30959622]


def save_session(driver, file_path):
    """保存 Local Storage 和 Cookies"""
    session_data = {
        "local_storage": driver.execute_script("return JSON.stringify(localStorage);"),
        "session_storage": driver.execute_script(
            "return JSON.stringify(sessionStorage);"
        ),
        "cookies": driver.get_cookies(),
    }
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(session_data, file, ensure_ascii=False, indent=4)
    print(f"会话数据已保存到 {file_path}")


def load_session(driver, file_path):
    """加载 Local Storage 和 Cookies"""
    with open(file_path, "r", encoding="utf-8") as file:
        session_data = json.load(file)
        # 加载 Local Storage
        local_storage = json.loads(session_data["local_storage"])
        for key, value in local_storage.items():
            try:
                driver.execute_script(f"localStorage.setItem('{key}', '{value}');")
            except Exception:
                pass
        # 加载 Session Storage
        session_storage = json.loads(session_data["session_storage"])
        for key, value in session_storage.items():
            try:
                driver.execute_script(f"sessionStorage.setItem('{key}', '{value}');")
            except Exception:
                pass
        # 加载 Cookies (跳过域名不匹配的)
        skipped = 0
        added = 0
        for cookie in session_data["cookies"]:
            try:
                driver.add_cookie(cookie)
                added += 1
            except Exception:
                skipped += 1
        print(f"Cookies 加载: 成功 {added}, 跳过 {skipped} (域名不匹配)")
    print(f"会话数据已从 {file_path} 加载")


def save_catalog(driver: webdriver.Chrome, bookId, outputDir):

    # Reader.$children[0].$children[0].catalogArr是使用JS Digger查找出来的,后面可能失效,如果失效自己使用JS Digger重新查找
    json_data = driver.execute_script(
        """
                //获取层级
                function getLevel(obj) {
                    let level = 1;
                    if (!obj.root) return level;
                    if (obj.chapter_index === obj.root.chapter_index)
                        return level;
                    else
                        level += getLevel(obj.root);
                    return level;
                }
                //获取导航位置
                function getNavPoint(str) {
                    strs = str.split('#');
                    if (strs.length > 1)
                        return strs[1];
                    else
                        return "";
                }
                function getChapterItem(str) {
                    if (str.endsWith(".html"))
                        return str;
                    else
                        return str + ".html";
                }
                //获取目录
                function getCatalog() {
                    let obj = Reader.$children[0].$children[0].catalogArr;
                    let objNew = [];
                    for (let i = 0; i < obj.length; i++) {
                        let src = obj[i];
                        let dst = {};
                        dst.chapter_id = src.chapter_id;
                        dst.chapter_index = src.chapter_index;
                        dst.chapter_name = src.chapter_name;
                        dst.chapter_item = getChapterItem(src.chapter_item);
                        dst.nav_point = getNavPoint(src.chapter_uri);
                        dst.parent_index = src.root.chapter_index;
                        dst.level = getLevel(src)-1;
                        objNew.push(dst);
                    }
                    return objNew;
                }
                return getCatalog();                          
                """
    )

    lis = []
    for it in json_data:
        level = it["level"]
        navPoint = it["nav_point"]
        navPointHtml = "" if navPoint == "" else f"#{navPoint}"
        if level == 0:
            lis.append(
                f"""<li><a href="./Data/{it["chapter_item"]}{navPointHtml}">{it["chapter_name"]}</a></li>"""
            )
        else:
            lis.append(
                f"""<li style="text-indent: {level}em;"><a href="./Data/{it["chapter_item"]}{navPointHtml}">{it["chapter_name"]}</a></li>"""
            )

    html = f"""
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <link rel="stylesheet" type="text/css" href="http://storage.360buyimg.com/ebooks/9fd8bb77eb40456b746aaae41785499a_new_.css" />
            <title>目录</title>
        </head>
        <body>
            <ul>{ "".join(lis)}</ul>  
        </body>
        </html>
        """
    with open(f"{outputDir}/index.json", "w", encoding="utf-8") as file:
        file.write(json.dumps(json_data))
    with open(f"{outputDir}/index.html", "w", encoding="utf-8") as file:
        file.write(html)
    with open(f"{outputDir}/index.txt", "w", encoding="utf-8") as file:
        file.write(f"{bookId}")
    return json_data


def save_page(driver: webdriver.Chrome, filepath):
    # 京东读书 2026 版 UI:
    # - .chapter-page 仅显示页码进度 (如 "9.52%"),不含正文
    # - #horizontal-read-container 才包含整章正文(通过 CSS transform 横向偏移控制可见性)
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.ID, "horizontal-read-container"))
    )
    # 等待章节内容真正渲染 (innerHTML 体积足够)
    container = None
    for _ in range(120):
        container = driver.find_element(By.ID, "horizontal-read-container")
        html_now = container.get_attribute("innerHTML") or ""
        if len(html_now) > 300:
            break
        time.sleep(0.5)

    # 拼接章节标题 + 正文
    try:
        chapter_name_html = driver.find_element(By.CLASS_NAME, "chapter-name").get_attribute("outerHTML")
    except Exception:
        chapter_name_html = ""

    element_html = (chapter_name_html or "") + container.get_attribute("outerHTML")
    head_node = driver.find_element(By.TAG_NAME, "head")

    head_html = []
    for it_head_node in head_node.find_elements(By.XPATH, "./*"):
        tag_name = it_head_node.tag_name
        outer_html = it_head_node.get_attribute("outerHTML")
        if tag_name == "link":
            # linkHref = it_head_node.get_attribute("href")
            linkHref = it_head_node.get_dom_attribute("href")
            # linkHref = it_head_node.get_property("href")
            if not linkHref.startswith("https"):
                continue
            if not linkHref.endswith(".css"):
                continue
        if tag_name == "meta" or tag_name == "style" or tag_name == "link":
            head_html.append(outer_html)
            
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(
            # f"""<html><head><meta charset='UTF-8'></head><body>{element_html}</body></html>"""
            f"""<html><head>{"".join(head_html)}</head><body>{element_html}</body></html>"""
        )
        # file.write(element_html)


def checkLoginData():
    if not os.path.exists(COOKIE_FILE):
        print("无cookie文件存在,请手动登录")
        return False
    with open(COOKIE_FILE, "r", encoding="utf8") as f:
        try:
            text = f.read()
            return '"thor"' in text
        except Exception as e:
            print(str(e))
            return False
    return False


def saveLoginData(driver: webdriver.Chrome):
    # 直接打开目标书的阅读器, 让用户在 ebooks.jd.com 域名上登录
    driver.get(f"https://ebooks.jd.com/reader/?ebookId={Download_Book_List[0]}&index=0&from=3")
    print("请在弹出的 Chrome 窗口中登录京东账号...")
    print("(请用京东账号扫码或账密登录)")
    print("等待登录中... (检测到登录 cookie 后会自动保存)")
    # 轮询等待 thor cookie 出现 (登录成功标志), 最长等待 10 分钟
    for i in range(600):
        try:
            cookies = driver.get_cookies()
            if any(c.get("name") == "thor" for c in cookies):
                print("✅ 检测到登录成功，等待页面状态稳定...")
                # 多等几秒确保所有 cookies 写入, 并刷新一次让书本权限生效
                time.sleep(5)
                driver.refresh()
                time.sleep(3)
                save_session(driver, COOKIE_FILE)
                return
        except Exception as e:
            print(f"检测异常: {e}")
        time.sleep(1)
    raise TimeoutError("等待登录超时 (10 分钟)")


def loadLoginData(driver: webdriver.Chrome):
    # 先访问 e-m.jd.com 加载原域名 cookies
    driver.get(f"https://e-m.jd.com")
    time.sleep(1)
    if os.path.exists(COOKIE_FILE):
        load_session(driver, COOKIE_FILE)
    # 再访问 ebooks.jd.com (共享的 .jd.com cookies 自动可用)
    driver.get(f"https://ebooks.jd.com")
    time.sleep(2)


def downloadBook(bookIndex, bookCount, driver: webdriver.Chrome, bookId):
    # 打开目标网站
    url = f"https://ebooks.jd.com/reader/?ebookId={bookId}&index=0&from=3"
    print(f"打开 URL: {url}")
    driver.get(url)
    time.sleep(3)
    handles = driver.window_handles
    if len(handles) > 1:
        driver.switch_to.window(handles[-1])
    elif len(handles) == 0:
        raise RuntimeError("所有 Chrome 窗口都被关闭了！")

    # 等到正文容器渲染出来 (说明已通过授权)
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.ID, "horizontal-read-container"))
    )
    time.sleep(3)

    # 验证书的访问状态
    state = driver.execute_script(
        """
        try {
            const s = Reader.$store.state;
            return {buyState:s.buyState, isLogin:s.isLogin, exception:s.exception, ebookName:s.ebookName};
        } catch(e) { return {error: e.toString()}; }
        """
    )
    print(f"书籍状态: {state}")
    if state.get("buyState") is False or state.get("exception") not in (None, 0):
        raise RuntimeError(f"无权阅读此书: {state}")

    title = driver.title
    print(f"开始下载:{title}")

    outputDir = f"{Data_Folder}/{title}"
    outputDataDir = f"{Data_Folder}/{title}/Data"
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    if not os.path.exists(outputDataDir):
        os.makedirs(outputDataDir)

    catalog = save_catalog(driver, bookId, outputDir)

    last_chapter_item = ""
    for it in catalog:
        index = it["chapter_index"]
        id = it["chapter_id"]
        chapter_item = it["chapter_item"]
        if chapter_item != last_chapter_item:
            driver.get(
                f"https://ebooks.jd.com/reader/?ebookId={bookId}&index={index}&from=3"
            )
            savePath = f"{outputDataDir}/{chapter_item}"
            save_page(driver, savePath)
            last_chapter_item = chapter_item
        print(f"{bookIndex+1}/{bookCount} 保存:{index+1}/{len(catalog)}")
    print(f"下载成功:{title}")



def main():

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # 最大化窗口
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-features=SitePerProcess")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    try:
        if checkLoginData():
            loadLoginData(driver)
            for i, id in enumerate(Download_Book_List):
                downloadBook(i, len(Download_Book_List), driver, id)
        else:
            saveLoginData(driver)

    except Exception as e:
        import traceback
        print(f"❌ 出错: {e}")
        traceback.print_exc()
        print(f"当前 URL: {driver.current_url}")
        print(f"当前 Title: {driver.title}")
        print("Chrome 窗口将保持打开 5 分钟以便排查...")
        time.sleep(300)
    finally:
        # 关闭 WebDriver
        driver.quit()


if __name__ == "__main__":
    main()
