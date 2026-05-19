"""手动登录验证脚本: Chrome 打开后由你完成登录并验证书架,
全部确认无误后,在终端按下 ENTER 让脚本保存 cookies"""
import json
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

COOKIE_FILE = "cookies.json"
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "chromedriver")
BOOK_ID = 30958860
READY_FLAG = "ready_to_save.flag"


def save_session(driver, file_path):
    session_data = {
        "local_storage": driver.execute_script("return JSON.stringify(localStorage);"),
        "session_storage": driver.execute_script("return JSON.stringify(sessionStorage);"),
        "cookies": driver.get_cookies(),
    }
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(session_data, file, ensure_ascii=False, indent=4)


def main():
    if os.path.exists(READY_FLAG):
        os.remove(READY_FLAG)

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    try:
        # 直接打开阅读器页面 (会被引导去登录)
        driver.get(f"https://ebooks.jd.com/reader/?ebookId={BOOK_ID}&index=4&from=3")

        print("=" * 60)
        print("📌 操作指引:")
        print("=" * 60)
        print("1. 在弹出的 Chrome 窗口中,点击「登录」按钮(如果还没登录)")
        print("2. 用拥有这本书的京东账号扫码/账密登录")
        print("3. 登录成功后,**打开新标签页**访问:")
        print("   https://ebooks.jd.com/user/bookshelf")
        print("   确认书架里能看到《即刻造梦》这本书,可以正常打开阅读")
        print("4. 确认无误后,回到此 Chrome 窗口,刷新阅读器页面让它真正显示书的内容")
        print("5. 完成所有操作后,在终端运行:")
        print(f"   touch {os.path.abspath(READY_FLAG)}")
        print("   (或者直接通知 AI 助手)")
        print("=" * 60)
        print("等待 ready_to_save.flag 文件出现... (最长 20 分钟)")

        for i in range(1200):
            # 每 30 秒打印一次实时状态
            if i % 30 == 0 and i > 0:
                try:
                    state = driver.execute_script(
                        """
                        try {
                            if (typeof Reader === 'undefined') return {note: 'Reader 未加载, 可能不在阅读器页'};
                            const s = Reader.$store.state;
                            return {
                              buyState: s.buyState,
                              isLogin: s.isLogin,
                              exception: s.exception,
                              ebookName: s.ebookName,
                              catalogLen: (s.catalogArr||[]).length,
                              enc_pin: s.enc_pin,
                            };
                        } catch(e) { return {error: e.toString()}; }
                        """
                    )
                    print(f"  [{i}s] 当前 Reader 状态: {state}")
                except Exception as e:
                    print(f"  [{i}s] 状态查询失败: {e}")

            if os.path.exists(READY_FLAG):
                print("\n✅ 检测到 ready 标志,正在保存 cookies...")
                save_session(driver, COOKIE_FILE)
                print(f"会话已保存到 {COOKIE_FILE}")
                os.remove(READY_FLAG)
                return
            time.sleep(1)

        print("❌ 超时未收到 ready 信号")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
