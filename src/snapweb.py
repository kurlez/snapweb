import re
import argparse
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

def load_page(url):
    """
    加载指定 URL 的页面，等待网络空闲、触发懒加载并等待所有图片加载完成，
    返回 playwright 对象、浏览器、页面对象、页面标题、安全的标题（用于文件名）和页面 HTML 内容。
    """
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 访问网页并等待网络空闲状态
    page.goto(url, wait_until="networkidle")

    # 模拟页面滚动以触发懒加载图片
    page.evaluate("""
        async () => {
            const distance = 100;
            const delay = 100;
            while (document.scrollingElement.scrollTop + window.innerHeight < document.scrollingElement.scrollHeight) {
                document.scrollingElement.scrollBy(0, distance);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    """)

    # 等待页面中所有图片加载完成（可根据需要调整超时）
    page.wait_for_function("""
        () => {
            const imgs = Array.from(document.images);
            return imgs.every(img => img.complete);
        }
    """, timeout=10000)

    # 获取页面标题，并生成安全的文件名（过滤非法字符）
    title = page.title()
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)

    # 获取渲染后的 HTML 内容
    html_content = page.content()

    return p, browser, page, title, safe_title, html_content

def save_webpage_as_pdf(url, output_pdf=None):
    """
    使用 Playwright 渲染网页并保存为 PDF，
    PDF 页面采用 Letter 大小，使用页面 <title> 作为页眉，
    底部显示页码（格式：当前页/总页数）。
    """
    p, browser, page, title, safe_title, html_content = load_page(url)

    if output_pdf is None:
        output_pdf = f"{safe_title}.pdf"

    # 设置页眉模板（调整样式避免与正文重叠）
    header_template = f"""
        <div style="font-size:10px; width:100%; text-align:center; margin-top:5px;">
            {title}
        </div>
    """
    # 设置页脚模板，使用内置占位符显示页码（格式：当前页/总页数）
    footer_template = """
        <div style="font-size:10px; width:100%; text-align:center; margin:0 auto;">
            <span class="pageNumber"></span>/<span class="totalPages"></span>
        </div>
    """

    # 保存为 PDF，设置页面格式为 Letter，并调整边距以避免页眉/页脚与正文重叠
    page.pdf(
        path=output_pdf,
        format="Letter",
        display_header_footer=True,
        header_template=header_template,
        footer_template=footer_template,
        margin={
            "top": "1.5in",    # 顶部边距预留页眉区域
            "bottom": "1in",   # 底部边距预留页脚区域
            "left": "1in",
            "right": "1in"
        },
        print_background=True
    )

    browser.close()
    p.stop()
    return output_pdf

def main(url, output_format):
    fmt = output_format.lower()
    if fmt == "pdf":
        output_file = save_webpage_as_pdf(url)
        print(f"PDF saved as {output_file}")
    elif fmt == "markdown":
        output_file = save_webpage_as_markdown(url)
        print(f"Markdown saved as {output_file}")
    elif fmt == "epub":
        output_file = save_webpage_as_epub(url)
        print(f"EPUB saved as {output_file}")
    else:
        print(f"Unsupported output format: {output_format}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a webpage to a specified output format (pdf for now, more will be added)."
    )
    parser.add_argument("url", help="The URL of the webpage to convert.")
    parser.add_argument("-t", "--type", default="pdf", help="Output format: 'pdf'.")
    args = parser.parse_args()

    main(args.url, args.type)
