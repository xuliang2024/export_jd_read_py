导出京东阅读已购买的电子书

## 快速使用 (推荐, 命令行版)

> 完成 [macOS 实战指南](#macos-实战指南2026-版) 的第 1-3 步（环境准备、装 chromedriver、登录保存 cookies）后，直接用下面的命令下书：

```bash
# 单本 (传 ID)
./jdread 30958860

# 单本 (粘 URL 也行, 自动从中抽 ebookId)
./jdread "https://ebooks.jd.com/reader/?ebookId=30958860&index=4&from=3"

# 一次下多本
./jdread 30958860 30959622 30960000

# cookies 失效了就重新登录
./jdread --login

# 强制重新登录,登录完接着下载
./jdread --login 30958860

# 查看完整帮助
./jdread --help
```

下载的 HTML 自动落到 `output/<书名>/Data/chapter*.html`。

## 如何使用

### 下载代码, 并安装依赖

1. 克隆 repo
2. 安装 Python 虚拟环境
3. 安装 requirements.txt 中的依赖

**示例脚本：**

```
git clone https://github.com/dyfllll/export_jd_read_py.git
cd export_jd_read_py
python -m venv venv
CALL venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 登录保存cookies

第一次需要，之后就直接使用，有可能cookies会失效，失效就删掉重新生成

1. 运行main.py
2. 在弹出的网页中登录
3. 打开书架中的一本书，将翻页方式改为**上下翻页**
4. 在命令行中按回车，生成cookies.json

### 导出html版本

1. 将要下载的`bookId`添加到main.py中Download_Book_List中，[bookId获取方法](https://github.com/goodwjf/export_jd_read)
2. 运行main.py，会自动下载书籍到`output` 目录

### 缓存图片资源

因为html里面图片是url链接形式，必须在线使用，所以可以把图片资源缓存在本地：

1. 运行downloadHtmlAsset.py，输入1，导出所有要下载的图片到`output/download.json`，并自动替换html里面图片地址
2. 运行downloadHtmlAsset.py，输入2，下载所有图片到本地

### 生成PDF

生成pdf需要安装[wkhtmltopdf.exe](https://wkhtmltopdf.org/downloads.html)，安装后替换html2pdf.py中wkhtmltopdf.exe安装地址

```python
config = pdfkit.configuration(
    wkhtmltopdf="D:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
)
```

运行html2pdf.py生成pdf

最后生成PDF是否带书签目录根据wkhtmltopdf.exe生成的单个PDF是否带书签目录决定的

### 其他

`main.py`中`save_catalog`函数是根据`Reader.$children[0].$children[0].catalogArr`获取目录数据结构，这段代码是使用`JS Digger`查找出来的，后面可能失效,如果失效自己使用`JS Digger`重新查找

---

## macOS 实战指南（2026 版）

> 原 README 的步骤是 Windows 思路，2026 年京东读书 Web 端 UI 已更新，本节是基于实际验证后的完整流程。

### 1. 环境准备

```bash
git clone https://github.com/dyfllll/export_jd_read_py.git
cd export_jd_read_py
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 安装 ChromeDriver（macOS）

Selenium 4 自带的 Selenium Manager 在国内下载 ChromeDriver 经常卡住，建议用 npm 镜像手动下载与本地 Chrome **同主版本号**的 chromedriver：

```bash
# 1) 查询本地 Chrome 版本
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version
# 例如输出: Google Chrome 148.0.7778.168 -> 主版本号 148

# 2) 找 chrome-for-testing 里相同主版本号的 chromedriver 链接
curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['channels']['Stable']['version'])"

# 3) 从 npm 镜像下载 (Google CDN 在国内速度只有 3KB/s, npm 镜像可达 10MB/s)
DRIVER_VER=148.0.7778.167  # 替换成上一步打印的版本
curl -L -o /tmp/chromedriver.zip \
  "https://registry.npmmirror.com/-/binary/chrome-for-testing/${DRIVER_VER}/mac-arm64/chromedriver-mac-arm64.zip"

# 4) 安装到项目 bin 目录, 去掉 macOS 隔离标记
mkdir -p bin
cd /tmp && unzip -o chromedriver.zip
cp chromedriver-mac-arm64/chromedriver /路径/export_jd_read_py/bin/chromedriver
chmod +x /路径/export_jd_read_py/bin/chromedriver
xattr -dr com.apple.quarantine /路径/export_jd_read_py/bin/chromedriver
```

代码里通过 `Service(executable_path=CHROMEDRIVER_PATH)` 显式指定本地 chromedriver，**避免 Selenium Manager 卡住**：

```python
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "chromedriver")
service = Service(executable_path=CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)
```

### 3. 登录保存 cookies（关键改动）

**⚠️ 注意：仅检测 `thor` cookie 出现就保存 cookies 是不够的**——必须确认页面 Reader Vue store 中的 `buyState: True` 才说明书的购买权限真正生效（否则保存的 cookies 加载书时 `exception: 3` 无权阅读）。

使用 `verify_login.py` 走交互式确认流程：

```bash
source venv/bin/activate
python -u verify_login.py
```

1. 弹出的 Chrome 会自动打开 `https://ebooks.jd.com/reader/?ebookId=<目标书id>`
2. 在 Chrome 里**手动登录**京东账号（扫码或账密都行）
3. 登录后 Chrome **不要关闭**，让脚本继续每 30 秒打印一次 Reader 状态
4. 等出现下面这样的状态再保存 cookies：
   ```
   {'buyState': True, 'catalogLen': 0, 'ebookName': '<书名>',
    'enc_pin': '<非空>', 'exception': None, 'isLogin': True}
   ```
5. 确认 `buyState: True` 后，在另一个终端执行 `touch ready_to_save.flag`，脚本会自动保存 cookies 退出

### 4. 下载电子书

把书的 ebookId（从 URL 提取，例如 `https://ebooks.jd.com/reader/?ebookId=30958860` 里的 `30958860`）加到 `main.py`：

```python
Download_Book_List = [30958860, 30959622]  # 可一次填多本
```

然后跑：

```bash
source venv/bin/activate
python -u main.py
```

输出到 `output/<书名>/`：

```
output/<书名>/
├── index.html      # 带超链接的目录, 浏览器打开就能跳转
├── index.json      # 章节元数据
├── index.txt       # bookId
└── Data/
    ├── Copyright.html
    ├── chapter00.html
    ├── chapter1.html
    └── ...         # 每个 html 是一整章的完整正文 + 图片 URL
```

### 5. 重要 UI 适配（2026 版必读）

京东读书 Web 端 UI 已重写，原 README 里的 CSS 选择器 `reader-chapter-content` **已不存在**。新的容器关系：

| 元素 | 作用 | 是否含正文 |
|------|------|----------|
| `.chapter-page` | 仅显示页码进度（如 "9.52%"） | ❌ 否 |
| `#horizontal-read-container` | 整章正文 + 图片，通过 CSS `transform` 横向偏移控制可见性 | ✅ 是 |
| `.chapter-name` | 章节标题 | ✅ 是 |

代码里 `save_page()` 已改为提取 `#horizontal-read-container` 的 outerHTML。

> ⚠️ Web 端的阅读方式现在是**左右键翻页**（横向分页），但完整章节内容已经全部渲染到 `#horizontal-read-container` 里，只是用 `translate3d(-Xpx, 0px, 0px)` 横向偏移隐藏。所以**无需模拟左右键翻页**，直接读 DOM 即可拿到整章。

### 6. session 完整恢复

cookies、localStorage、sessionStorage 三者**缺一不可**：

| 数据 | 关键字段 | 缺失后果 |
|------|---------|---------|
| cookies | `thor`、`pin`、`flash` | 完全未登录 |
| localStorage | `cur_chapter_*`、`device_id`、各种 WQ_* 反爬 token | `exception:3` 无权阅读 |
| sessionStorage | `vuex`（Vue store 镜像） | `buyState:false` 即使购买了也读不了 |

`save_session` / `load_session` 函数已经完整持久化这三类数据。

### 7. 常见问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `selenium-manager` 进程一直跑 | Google CDN 慢，自动下载 chromedriver 卡住 | 用第 2 步手动下载并指定 `Service(executable_path=...)` |
| `no such window: target window already closed` | 阅读页 JS 检测 Selenium 关闭了窗口 | 加 `options.add_experimental_option("excludeSwitches", ["enable-automation"])` 并执行 `Page.addScriptToEvaluateOnNewDocument` 去掉 `navigator.webdriver` |
| `chapter-page` 元素只有 "0.04%" 这种百分比文字 | 选错容器了 | 改用 `#horizontal-read-container` |
| `buyState: False, exception: 3` | session 没完整恢复 / 用了不拥有该书的账号 | 重新跑 `verify_login.py`，确认状态完美再保存 |
| `InvalidCookieDomainException` | cookies 域名跟当前页面域名不匹配 | `load_session` 已加 try/except 跳过不匹配的 cookies |

### 8. 缓存图片到本地

下载下来的 HTML 里图片是 `https://img30.360buyimg.com/...` 这种 CDN 链接，离线打开看不到图。要离线化：

```bash
python downloadHtmlAsset.py
# 提示输入 1 → 扫描所有 HTML, 把图片 URL 收集到 output/download.json, 同时替换 HTML 里的 URL 为本地路径
python downloadHtmlAsset.py
# 提示输入 2 → 根据 download.json 下载所有图片到本地
```

### 9. 生成 PDF（可选）

macOS 安装 wkhtmltopdf：

```bash
brew install --cask wkhtmltopdf
which wkhtmltopdf  # 例如 /usr/local/bin/wkhtmltopdf
```

然后改 `html2pdf.py` 里：

```python
config = pdfkit.configuration(wkhtmltopdf="/usr/local/bin/wkhtmltopdf")
```

再 `python html2pdf.py` 即可。

