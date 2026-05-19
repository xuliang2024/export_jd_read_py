#!/usr/bin/env python3
"""京东读书电子书 HTML 导出 - 命令行工具

用法:
  python jdread.py 30958860                          # 下载单本
  python jdread.py 30958860 30959622                 # 一次下多本
  python jdread.py "https://ebooks.jd.com/reader/?ebookId=30958860&..."   # 直接粘 URL
  python jdread.py --login                           # 重新登录(cookies 失效时)
  python jdread.py --login 30958860                  # 强制登录后下载
"""
import argparse
import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# 复用 main.py 中的全部函数
import main as jd


def extract_book_id(s: str) -> int:
    """从 URL 或纯数字字符串里抽出 ebookId"""
    s = s.strip()
    m = re.search(r"ebookId=(\d+)", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    raise ValueError(f"无法识别 book ID 或 URL: {s!r}")


def build_driver() -> webdriver.Chrome:
    """统一构造一个反自动化检测的 Chrome driver"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-features=SitePerProcess")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(executable_path=jd.CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def do_interactive_login(driver: webdriver.Chrome, book_id_hint: int | None) -> None:
    """交互式登录: 打开阅读器, 用户登录, 检测 buyState=True 后自动保存 cookies

    book_id_hint: 用一本你确认拥有的书做登录入口, 方便验证权限是否真的拿到
    """
    target = book_id_hint or 30958860  # 默认拿一本任意书做登录入口
    driver.get(f"https://ebooks.jd.com/reader/?ebookId={target}&index=0&from=3")

    print("=" * 60)
    print("📌 请在弹出的 Chrome 窗口里完成下面操作:")
    print("=" * 60)
    print("1. 点「登录」按钮, 用拥有这本书的京东账号扫码/账密登录")
    print("2. 登录完成后, 等待阅读器自动加载(不要关闭窗口)")
    print("3. 脚本会自动检测 Reader 的 buyState=True 后保存 cookies")
    print(f"4. 如果这本书你没有, 请先把 jdread.py 第 {66} 行的默认 ID 改成你购买的任意一本")
    print("=" * 60)
    print("等待登录中... (最长 10 分钟)")

    last_state_str = ""
    for i in range(600):
        try:
            state = driver.execute_script(
                """
                try {
                    if (typeof Reader === 'undefined') return {note:'Reader 未加载'};
                    const s = Reader.$store.state;
                    return {buyState:s.buyState, isLogin:s.isLogin, exception:s.exception,
                            ebookName:s.ebookName, enc_pin:s.enc_pin};
                } catch(e) { return {error:e.toString()}; }
                """
            )
            cur_str = str(state)
            if cur_str != last_state_str and i > 0:
                print(f"  [{i}s] {state}")
                last_state_str = cur_str

            if state.get("buyState") is True and state.get("isLogin") is True:
                print("✅ 检测到登录成功且有书的阅读权限,正在保存 cookies...")
                time.sleep(2)
                jd.save_session(driver, jd.COOKIE_FILE)
                print(f"已保存到 {jd.COOKIE_FILE}")
                return
        except Exception as e:
            print(f"  [{i}s] 状态查询异常: {e}")
        time.sleep(1)

    raise TimeoutError("等待登录超时 (10 分钟未检测到 buyState=True)")


def do_download(driver: webdriver.Chrome, book_ids: list[int]) -> None:
    """加载已保存的 session, 依次下载所有书"""
    if not os.path.exists(jd.COOKIE_FILE):
        raise RuntimeError(f"找不到 {jd.COOKIE_FILE},请先运行: python jdread.py --login")
    jd.loadLoginData(driver)
    for i, bid in enumerate(book_ids):
        try:
            jd.downloadBook(i, len(book_ids), driver, bid)
        except Exception as e:
            print(f"❌ 下载书 {bid} 失败: {e}")
            print("如果是登录态失效, 请重新运行: python jdread.py --login")
            raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="京东读书电子书 HTML 导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
  python jdread.py 30958860
  python jdread.py 30958860 30959622
  python jdread.py "https://ebooks.jd.com/reader/?ebookId=30958860&..."
  python jdread.py --login
  python jdread.py --login 30958860
""",
    )
    parser.add_argument(
        "book_ids",
        nargs="*",
        help="电子书 ID(纯数字)或包含 ebookId 参数的 URL,可填多个",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="进入交互式登录流程,登录成功后保存 cookies",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="出错时保持 Chrome 窗口打开 5 分钟以便排查",
    )
    args = parser.parse_args()

    if not args.login and not args.book_ids:
        parser.print_help()
        return 1

    try:
        book_ids = [extract_book_id(s) for s in args.book_ids]
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    driver = build_driver()
    try:
        if args.login:
            do_interactive_login(driver, book_ids[0] if book_ids else None)

        if book_ids:
            do_download(driver, book_ids)

        print("\n🎉 全部完成")
        return 0
    except Exception as e:
        print(f"❌ 出错: {e}")
        if args.keep_open:
            print("Chrome 保持 5 分钟以便排查...")
            time.sleep(300)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
