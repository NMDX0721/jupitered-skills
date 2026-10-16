"""
JupiterEd Unified Automation CLI Tool (Release Edition)
Created by: NMDX0721
GitHub: https://github.com/NMDX0721/jupitered-skills

Features:
  - Viewing dashboard & To Do list (todo)
  - Fetching grades & assignment IDs for courses (grades)
  - Inspecting assignment details & listing attachments (detail)
  - Downloading all attachments inside an assignment or across an entire course (download-assign)
  - Downloading all shared teacher folders & handouts from Materials section (materials)
  - Scanning and downloading attachments from Messages inbox (messages)
  - Turning in / submitting homework files for assignments (turnin)
  - Interactive/automated setup check (setup)
"""

import os
import sys
import time
import json
import argparse
import re
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

ATTRIBUTION_SIGNATURE = "[Skill: jupiter-ed | The Skill is made by NMDX0721]"
DEFAULT_GITHUB_REPO = "https://github.com/NMDX0721/jupitered-skills"

def print_attribution():
    print(f"\n>>> {ATTRIBUTION_SIGNATURE}")
    print(f">>> GitHub: {DEFAULT_GITHUB_REPO}\n")

def get_base_dir():
    # scripts/ -> skill root directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_config_path(custom_path=None):
    if custom_path and os.path.exists(custom_path):
        return os.path.abspath(custom_path)
    base_dir = get_base_dir()
    candidate_1 = os.path.join(base_dir, "config.json")
    if os.path.exists(candidate_1):
        return candidate_1
    candidate_2 = os.path.join(os.getcwd(), "config.json")
    if os.path.exists(candidate_2):
        return candidate_2
    return candidate_1

def load_config(config_path=None):
    path = find_config_path(config_path)
    if not os.path.exists(path):
        print(f"!! Error: Configuration file not found at: {path}")
        print("!! Please copy 'config.example.json' to 'config.json' and fill in your credentials.")
        print(f"!! Or run: python \"{__file__}\" setup")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"!! Error reading {path}: {e}")
        sys.exit(1)

    return cfg, path

def check_first_run_notice(base_dir, github_url):
    marker_file = os.path.join(base_dir, ".first_run_done")
    if not os.path.exists(marker_file):
        print("=" * 68)
        print("🎉 恭喜配置完成！返回项目 GitHub 仓库链接获取更多内容与更新:")
        print(f"👉 {github_url}")
        print("=" * 68 + "\n")
        try:
            with open(marker_file, "w", encoding="utf-8") as f:
                f.write("configured=true\n")
        except Exception:
            pass

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name).strip()

def download_s3_file(url, filename, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    clean_fn = sanitize_filename(filename)
    if not any(clean_fn.lower().endswith(ext) for ext in ['.pdf', '.pptx', '.docx', '.xlsx', '.zip', '.png', '.jpg', '.mp4']):
        low_url = url.lower().split('?')[0]
        for ext in ['.pdf', '.pptx', '.docx', '.xlsx', '.zip', '.png', '.jpg', '.mp4']:
            if low_url.endswith(ext):
                clean_fn += ext
                break

    target_path = os.path.join(out_dir, clean_fn)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        sz = os.path.getsize(target_path)
        print(f"    [Cached] {clean_fn} ({sz:,} bytes)")
        return target_path

    print(f"    [Downloading] {clean_fn} <- {url[:65]}...")
    subprocess.run([
        "curl.exe", "-L", "-o", target_path,
        "-s", "--connect-timeout", "30", "--max-time", "300", url
    ])
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        sz = os.path.getsize(target_path)
        print(f"    [SUCCESS] {clean_fn} ({sz:,} bytes)")
        return target_path
    else:
        print(f"    [FAILED] {clean_fn}")
        return None

def create_context(playwright, cfg, headless=True, auto_login=True):
    chrome_exe = cfg.get("chrome_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    profile_dir = cfg.get("profile_dir", "./jupiter_profile")
    login_url = cfg.get("login_url", "https://login.jupitered.com/login/index.php")
    username = cfg.get("username", "").strip()
    password = cfg.get("password", "").strip()

    abs_profile = os.path.abspath(os.path.expanduser(profile_dir))
    os.makedirs(abs_profile, exist_ok=True)

    launch_kwargs = {
        "user_data_dir": abs_profile,
        "headless": headless,
        "viewport": {"width": 1280, "height": 900},
        "accept_downloads": True
    }

    if chrome_exe and os.path.exists(chrome_exe):
        launch_kwargs["executable_path"] = chrome_exe

    ctx = playwright.chromium.launch_persistent_context(**launch_kwargs)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(login_url, wait_until="domcontentloaded", timeout=45000)
    time.sleep(3)

    if not auto_login:
        return ctx, page

    # Check session expiry / login needed
    pwd_field = page.query_selector("#text_password1")
    if pwd_field:
        if not username or not password or username == "YOUR_STUDENT_ID_OR_NAME":
            print("\n" + "=" * 68)
            print("!! 当前 JupiterEd 会话未登录或已过期。")
            print("👉 推荐免密方式：运行以下命令在浏览器中一键登录（无需保存明文密码）：")
            print("   python scripts/jup_cli.py login")
            print("👉 或者运行配置命令写入账号密码：")
            print("   python scripts/jup_cli.py setup --username <USER> --password <PASS>")
            print("=" * 68 + "\n")
            ctx.close()
            sys.exit(1)

        print("[*] Session expired or unauthenticated. Attempting auto-login with stored credentials...")
        stud_field = page.query_selector("#text_studid1")
        if stud_field:
            stud_field.fill("")
            stud_field.type(username, delay=20)
        pwd_field.fill(password)
        login_btn = page.query_selector("#loginbtn")
        if login_btn:
            login_btn.click()
            time.sleep(5)
        if page.query_selector("#text_password1"):
            print("!! ERROR: Auto-login failed. Please verify credentials in config.json or run 'login' action.")
            ctx.close()
            sys.exit(1)
        print("[+] Login succeeded.")

    return ctx, page

def wait_for_loading(page, timeout_sec=15):
    for _ in range(timeout_sec):
        time.sleep(1)
        body = page.inner_text("body")
        if "Loading" not in body and len(body) > 200:
            break
    time.sleep(1)

def extract_matview_url(page):
    return page.evaluate("""() => {
        const a = document.querySelector('a[href*="s3.us-west"], a[href*="ufile"], a[href*="jupiter"]');
        if (a) return a.getAttribute('href');
        const ifr = document.querySelector('iframe');
        if (ifr) return ifr.getAttribute('src');
        return null;
    }""")

def close_matview(page, fallback_cid=None, fallback_aid=None):
    try:
        close_btn = page.locator("text=Close").first
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(2.5)
            return True
    except Exception:
        pass
    if fallback_cid and fallback_aid:
        page.evaluate(f"postval('class1', {fallback_cid}); go('grades');")
        time.sleep(2.5)
        page.evaluate(f"goassign({fallback_aid});")
        time.sleep(3)
    return False

def resolve_course_id(val, cfg):
    if not val:
        return None
    val_str = str(val).strip().lower()
    if val_str.isdigit():
        return int(val_str)
    course_map = cfg.get("course_ids", {})
    lower_map = {k.lower(): v for k, v in course_map.items()}
    return lower_map.get(val_str, None)

def action_todo(args, cfg):
    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            page.evaluate("go('todo')")
            wait_for_loading(page)
            body = page.inner_text("body")
            print("=== JUPITER ED: TO DO LIST ===")
            print(body)
            if args.screenshot:
                page.screenshot(path=args.screenshot)
                print(f"Screenshot saved to: {args.screenshot}")
        finally:
            ctx.close()

def discover_course_assignments(page):
    return page.evaluate("""() => {
        const list = [];
        const seen = new Set();
        document.querySelectorAll('[click*="goassign"]').forEach(el => {
            const c = el.getAttribute('click') || '';
            const m = c.match(/goassign\\((\\d+)\\)/);
            if (m && !seen.has(m[1])) {
                seen.add(m[1]);
                list.push({
                    id: m[1],
                    title: el.innerText.trim().replace(/\\s+/g, ' ')
                });
            }
        });
        return list;
    }""")

def action_grades(args, cfg):
    cid = resolve_course_id(args.course, cfg)
    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            if cid:
                print(f"[*] Navigating to Course ID: {cid}...")
                page.evaluate(f"postval('class1', {cid}); go('grades');")
            else:
                page.evaluate("go('grades')")
            wait_for_loading(page)
            print("=== JUPITER ED: GRADES & ASSIGNMENTS ===")
            print(page.inner_text("body"))

            assigns = discover_course_assignments(page)
            if assigns:
                print("\n=== DISCOVERED ASSIGNMENT IDs (`goassign`) ===")
                for a in assigns:
                    print(f"  [{a['id']}] {a['title']}")

            if args.screenshot:
                page.screenshot(path=args.screenshot)
                print(f"Screenshot saved to: {args.screenshot}")
        finally:
            ctx.close()

def discover_openmat_items(page):
    return page.evaluate("""() => {
        const list = [];
        const seen = new Set();
        document.querySelectorAll('[click*="openmat"]').forEach(el => {
            const c = el.getAttribute('click') || '';
            const m = c.match(/openmat\\((\\d+)\\)/);
            if (m && !seen.has(m[1])) {
                seen.add(m[1]);
                list.push({
                    id: m[1],
                    text: el.innerText.trim(),
                    click: c
                });
            }
        });
        return list;
    }""")

def download_openmat_items_on_page(page, items, out_dir, cid=None, aid=None):
    downloaded = []
    for item in items:
        mid = item['id']
        mname = item['text']
        print(f"  -> Opening attachment: {mname} (openmat ID: {mid})...")

        clicked = False
        try:
            loc = page.locator(f'[click*="openmat({mid})"]').first
            if loc.is_visible():
                loc.click()
                clicked = True
        except Exception:
            pass

        if not clicked:
            try:
                page.click(f'text="{mname}"')
                clicked = True
            except Exception as e:
                print(f"    [!] Click failed for {mname}: {e}")
                continue

        time.sleep(3.5)
        url = extract_matview_url(page)
        if url:
            saved = download_s3_file(url, mname, out_dir)
            if saved:
                downloaded.append(saved)
        else:
            print(f"    [!] No S3 URL found on matview for {mname} (may be a Juno Pod or online quiz)")

        close_matview(page, fallback_cid=cid, fallback_aid=aid)
    return downloaded

def action_detail(args, cfg):
    cid = resolve_course_id(args.course, cfg)
    aid = args.assign
    if not aid:
        print("!! Error: --assign <id> is required for detail action.")
        return

    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            if cid:
                page.evaluate(f"postval('class1', {cid}); go('grades');")
                time.sleep(3)
            page.evaluate(f"goassign({aid});")
            wait_for_loading(page)
            print(f"=== ASSIGNMENT DETAIL ({aid}) ===")
            print(page.inner_text("body"))

            mats = discover_openmat_items(page)
            if mats:
                print(f"\n=== ATTACHMENTS FOUND ({len(mats)}) ===")
                for m in mats:
                    print(f"  - {m['text']} (openmat ID: {m['id']})")
                if args.out:
                    print(f"\n[*] Downloading attachments to: {args.out}")
                    download_openmat_items_on_page(page, mats, args.out, cid=cid, aid=aid)

            if args.screenshot:
                page.screenshot(path=args.screenshot)
                print(f"Screenshot saved to: {args.screenshot}")
        finally:
            ctx.close()

def action_download_assign(args, cfg):
    cid = resolve_course_id(args.course, cfg)
    if not cid:
        print("!! Error: --course <name|id> is required for download-assign.")
        return
    out_dir = args.out or os.path.abspath("./jupiter_downloads")

    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            page.evaluate(f"postval('class1', {cid}); go('grades');")
            wait_for_loading(page)

            if args.assign and args.assign.lower() != "all":
                target_assigns = [{"id": str(args.assign), "title": f"Assignment {args.assign}"}]
            else:
                target_assigns = discover_course_assignments(page)
                print(f"[*] Found {len(target_assigns)} assignments in Course {cid}. Scanning for attachments...")

            total_files = 0
            for a in target_assigns:
                aid = a['id']
                atitle = a['title']
                page.evaluate(f"postval('class1', {cid}); go('grades');")
                time.sleep(2.5)
                page.evaluate(f"goassign({aid});")
                time.sleep(3.5)

                mats = discover_openmat_items(page)
                if not mats:
                    print(f"[-] [{aid}] {atitle}: No openmat attachments.")
                    continue

                print(f"\n[+] [{aid}] {atitle}: Found {len(mats)} attachment(s)!")
                saved = download_openmat_items_on_page(page, mats, out_dir, cid=cid, aid=aid)
                total_files += len(saved)

            print(f"\n=== COMPLETED: {total_files} file(s) saved to {out_dir} ===")
        finally:
            ctx.close()

def action_materials(args, cfg):
    cid = resolve_course_id(args.course, cfg)
    out_dir = args.out or os.path.abspath("./jupiter_materials")

    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            if cid:
                page.evaluate(f"postval('class1', {cid}); go('grades');")
                wait_for_loading(page)

            page.evaluate("go('downloads');")
            wait_for_loading(page)

            print("=== JUPITER ED: MATERIALS & TEACHER DOWNLOADS ===")
            print(page.inner_text("body")[:1200])

            direct_links = page.evaluate("""() => {
                const list = [];
                const seen = new Set();
                document.querySelectorAll('a[href*="s3"], a[href*="ufile"]').forEach(a => {
                    const txt = a.innerText.trim();
                    const href = a.getAttribute('href');
                    if (href && !seen.has(href)) {
                        seen.add(href);
                        list.push({text: txt, href: href});
                    }
                });
                return list;
            }""")

            if direct_links:
                print(f"\n[*] Found {len(direct_links)} direct material download link(s):")
                for item in direct_links:
                    print(f"  - {item['text']:<45} -> {item['href'][:65]}...")
                    if args.out:
                        download_s3_file(item['href'], item['text'], out_dir)

            mats = discover_openmat_items(page)
            if mats and args.out:
                print(f"\n[*] Downloading {len(mats)} openmat material item(s)...")
                download_openmat_items_on_page(page, mats, out_dir)

            folders = page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('[click*="filemenu"], [click*="togglefolder"]').forEach(el => {
                    const c = el.getAttribute('click') || '';
                    list.push({text: el.innerText.trim(), click: c});
                });
                return list;
            }""")

            if folders and args.out:
                print(f"\n[*] Found {len(folders)} folder(s). Traversing...")
                for f in folders:
                    print(f"\n[*] Expanding folder: {f['text']} ({f['click']})...")
                    page.evaluate(f['click'])
                    time.sleep(3.5)
                    sub_links = page.evaluate("""() => {
                        const list = [];
                        const seen = new Set();
                        document.querySelectorAll('a[href*="s3"], a[href*="ufile"]').forEach(a => {
                            const txt = a.innerText.trim();
                            const href = a.getAttribute('href');
                            if (href && !seen.has(href)) {
                                seen.add(href);
                                list.push({text: txt, href: href});
                            }
                        });
                        return list;
                    }""")
                    for sl in sub_links:
                        download_s3_file(sl['href'], sl['text'], out_dir)

            if args.screenshot:
                page.screenshot(path=args.screenshot)
                print(f"Screenshot saved to: {args.screenshot}")
        finally:
            ctx.close()

def action_messages(args, cfg):
    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            page.evaluate("go('messages');")
            wait_for_loading(page)
            print("=== JUPITER ED: MESSAGES INBOX ===")

            blocks = page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('[click*="clickblock"]').forEach(el => {
                    list.push({
                        text: el.innerText.trim(),
                        click: el.getAttribute('click')
                    });
                });
                return list;
            }""")

            filter_kw = (args.teacher or args.course or "").lower()
            matching_blocks = []
            for b in blocks:
                if not filter_kw or filter_kw in b['text'].lower():
                    matching_blocks.append(b)

            print(f"[*] Found {len(matching_blocks)} message thread(s)" + (f" matching '{filter_kw}'" if filter_kw else "") + ":")

            for idx, b in enumerate(matching_blocks):
                print(f"\n{'='*50}\n--- Message Thread {idx + 1}/{len(matching_blocks)} ---")
                try:
                    page.evaluate(b['click'])
                except Exception as e:
                    print(f"  [!] Failed to open thread: {e}")
                    continue
                time.sleep(3.5)
                wait_for_loading(page)

                body_text = page.inner_text("body")
                lines = [l.strip() for l in body_text.splitlines() if l.strip()]
                print("\n".join(lines[:16]))

                attachments = page.evaluate("""() => {
                    const list = [];
                    const seen = new Set();
                    document.querySelectorAll('a[href*="s3"], a[href*="post.jupitered.com"], a[href*="ufile"]').forEach(el => {
                        const href = el.getAttribute('href');
                        const txt = el.innerText.trim();
                        if (href && !seen.has(href)) {
                            seen.add(href);
                            list.push({text: txt, href: href});
                        }
                    });
                    return list;
                }""")

                if attachments:
                    print(f"\n  [+] Found {len(attachments)} attachment(s):")
                    for att in attachments:
                        print(f"      - {att['text']} -> {att['href'][:65]}...")
                        if args.out:
                            download_s3_file(att['href'], att['text'], args.out)

                page.evaluate("go('messages');")
                time.sleep(2.5)

            if args.screenshot:
                page.screenshot(path=args.screenshot)
                print(f"Screenshot saved to: {args.screenshot}")
        finally:
            ctx.close()

def action_turnin(args, cfg):
    cid = resolve_course_id(args.course, cfg)
    aid = args.assign
    file_path = args.file

    if not aid or not file_path:
        print("!! Error: both --assign <id> and --file <path> are required for turnin.")
        return

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        print(f"!! Error: file not found: {abs_path}")
        return

    print(f"[*] Submitting {abs_path} to assignment {aid}...")
    with sync_playwright() as p:
        ctx, page = create_context(p, cfg)
        try:
            if cid:
                page.evaluate(f"postval('class1', {cid}); go('grades');")
                time.sleep(3)
            page.evaluate(f"goassign({aid});")
            time.sleep(4)

            file_input = page.locator("input[name='upload']").first
            file_input.set_input_files(abs_path)

            print("[*] Uploading...")
            for i in range(15):
                time.sleep(1)
                body = page.inner_text("body")
                if "Done" in body or os.path.basename(abs_path) in body:
                    print(f"[+] Upload processed in ~{i+1}s")
                    break

            time.sleep(2)
            body = page.inner_text("body")
            if "Done" in body or os.path.basename(abs_path) in body:
                print("[+] SUCCESS: Assignment turned in successfully!")
            else:
                print("[!] Warning: Could not confirm 'Done' status on page.")

            print("\n=== PAGE STATUS ===")
            print(body[:600])

            if args.screenshot:
                page.screenshot(path=args.screenshot)
                print(f"Screenshot saved to: {args.screenshot}")
        finally:
            ctx.close()

def action_setup(args):
    base_dir = get_base_dir()
    cfg_file = os.path.join(base_dir, "config.json")
    example_file = os.path.join(base_dir, "config.example.json")

    cfg = {}
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    elif os.path.exists(example_file):
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    username = args.username
    password = args.password

    # Interactive prompt if running in an interactive terminal and credentials not given
    if (not username or not password) and sys.stdin.isatty():
        curr_u = cfg.get("username", "")
        if not curr_u or curr_u == "YOUR_STUDENT_ID_OR_NAME":
            try:
                import getpass
                print("\n=== JupiterEd 交互式配置向导 ===")
                if not username:
                    username = input("请输入 JupiterEd 登录账号/学号: ").strip()
                if not password:
                    password = getpass.getpass("请输入 JupiterEd 登录密码: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n[!] Setup aborted.")
                return

    if username:
        cfg["username"] = username
    if password:
        cfg["password"] = password

    # Save to config.json
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved credentials to: {cfg_file}")
    except Exception as e:
        print(f"!! Failed to write {cfg_file}: {e}")
        return

    print("\n--- JupiterEd Skill Setup Verification ---")
    u = cfg.get("username", "")
    p = cfg.get("password", "")
    if not u or u == "YOUR_STUDENT_ID_OR_NAME" or not p:
        print(f"[!] Please provide valid credentials using:")
        print(f"    python scripts/jup_cli.py setup --username <USER> --password <PASS>")
        print(f"[!] Or edit '{cfg_file}' directly.")
        return

    github_url = cfg.get("github_repo", DEFAULT_GITHUB_REPO)
    check_first_run_notice(base_dir, github_url)

def discover_courses_from_page(page):
    return page.evaluate("""() => {
        const map = {};
        document.querySelectorAll('[click]').forEach(el => {
            const c = el.getAttribute('click') || '';
            const m = c.match(/postval\\('class1',\\s*(\\d+)\\)/);
            if (m) {
                const txt = el.innerText.trim();
                if (txt && !txt.includes('\\n')) {
                    const cleanName = txt.toLowerCase().replace(/[^a-z0-9]/g, '');
                    if (cleanName && cleanName.length > 1) {
                        map[cleanName] = parseInt(m[1]);
                        map[txt] = parseInt(m[1]);
                    }
                }
            }
        });
        return map;
    }""")

def action_login(args):
    if args.cdp:
        action_attach(args)
        return

    base_dir = get_base_dir()
    cfg_file = os.path.join(base_dir, "config.json")
    example_file = os.path.join(base_dir, "config.example.json")

    cfg = {}
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    elif os.path.exists(example_file):
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    print("=" * 68)
    print("🌟 JupiterEd 一键可视化免密登录 (One-Click Session Capture)")
    print("=" * 68)
    print("[*] 正在打开 Chrome 浏览器窗口...")
    print("[*] 说明：本脚本完全不会获取或记录您的登录密码。")
    print("[*] 请在弹出的官方登录页面中完成登录（支持浏览器自动填充/记住密码/SSO）。")
    print("[*] 登录完成后，脚本将自动捕获会话 Cookie、探测所选课程并自动关闭窗口...\n")

    with sync_playwright() as p:
        ctx, page = create_context(p, cfg, headless=False, auto_login=False)
        try:
            logged_in = False
            for _ in range(180):  # Wait up to 3 minutes
                time.sleep(1.5)
                try:
                    if not ctx.pages:
                        break
                    pwd_field = page.query_selector("#text_password1")
                    cookies = ctx.cookies()
                    has_jup = any(c.get('name') == 'jupiter' for c in cookies)
                    if not pwd_field and has_jup:
                        wait_for_loading(page)
                        logged_in = True
                        break
                except Exception:
                    break

            if not logged_in:
                print("!! 未检测到登录完成或浏览器窗口已关闭。")
                return

            print("\n[+] 🎉 登录成功！已安全捕获并持久化存储会话 Cookie。")

            print("[*] 正在自动探测你本学期的课程列表与 Course ID...")
            time.sleep(2)
            course_map = discover_courses_from_page(page)
            if course_map:
                print(f"[+] 成功识别 {len(course_map)//2} 门选修课程！已自动生成映射表。")
                cfg["course_ids"] = course_map

            # Save configuration
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            print(f"[+] 配置与课程映射表已更新至: {cfg_file}")

            github_url = cfg.get("github_repo", DEFAULT_GITHUB_REPO)
            check_first_run_notice(base_dir, github_url)
        finally:
            ctx.close()

def action_attach(args):
    cdp_input = args.cdp or "http://localhost:9222"
    if cdp_input.isdigit():
        cdp_url = f"http://localhost:{cdp_input}"
    elif not cdp_input.startswith("http://") and not cdp_input.startswith("ws://"):
        cdp_url = f"http://{cdp_input}"
    else:
        cdp_url = cdp_input

    base_dir = get_base_dir()
    cfg_file = os.path.join(base_dir, "config.json")
    example_file = os.path.join(base_dir, "config.example.json")

    cfg = {}
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    elif os.path.exists(example_file):
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    print("=" * 68)
    print("🔗 JupiterEd 浏览器 CDP 直连同步 (Chrome DevTools Protocol)")
    print("=" * 68)
    print(f"[*] 正在尝试连接本地已运行的 Chrome 实例: {cdp_url}")
    print("[*] 提示：需先以调试端口启动 Chrome（例如：chrome.exe --remote-debugging-port=9222）\n")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            print(f"!! 无法连接至 {cdp_url}: {e}")
            print("!! 请确认 Chrome 是否已启用远程调试端口，或直接运行推荐的一键免密登录：")
            print("   python scripts/jup_cli.py login")
            return

        try:
            if not browser.contexts:
                print("!! 未发现活动的浏览器上下文。")
                return

            ctx = browser.contexts[0]
            cookies = ctx.cookies(["https://login.jupitered.com"])
            jup_cookies = [c for c in cookies if c.get("name") == "jupiter"]
            if not jup_cookies:
                print("[!] 连接成功，但未在该 Chrome 实例中找到 JupiterEd 的已登录会话。")
                print("[!] 请确保你在该 Chrome 中打开并登录了 login.jupitered.com。")
                return

            print(f"[+] 成功捕获到 {len(cookies)} 个 Jupiter 会话 Cookie！")

            jupiter_page = None
            for page in ctx.pages:
                if "jupiter" in page.url.lower():
                    jupiter_page = page
                    break

            if jupiter_page:
                print("[*] 检测到已打开的 JupiterEd 页面，正在自动提取选课列表...")
                course_map = discover_courses_from_page(jupiter_page)
                if course_map:
                    print(f"[+] 成功识别 {len(course_map)//2} 门选修课程！")
                    cfg["course_ids"] = course_map

            profile_dir = cfg.get("profile_dir", "./jupiter_profile")
            abs_profile = os.path.abspath(os.path.expanduser(profile_dir))
            os.makedirs(abs_profile, exist_ok=True)

            chrome_exe = cfg.get("chrome_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            launch_kwargs = {"user_data_dir": abs_profile, "headless": True}
            if chrome_exe and os.path.exists(chrome_exe):
                launch_kwargs["executable_path"] = chrome_exe

            p_ctx = p.chromium.launch_persistent_context(**launch_kwargs)
            p_ctx.add_cookies(cookies)
            p_ctx.close()

            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            print(f"[+] 会话 Cookie 与配置已无缝同步保存至: {cfg_file}")

            github_url = cfg.get("github_repo", DEFAULT_GITHUB_REPO)
            check_first_run_notice(base_dir, github_url)
        finally:
            browser.close()

def main():
    parser = argparse.ArgumentParser(description=f"JupiterEd Automation CLI (Release Edition) - {ATTRIBUTION_SIGNATURE}")
    parser.add_argument(
        "action",
        choices=["todo", "grades", "detail", "download-assign", "materials", "messages", "turnin", "setup", "login", "attach"],
        help="Action to perform"
    )
    parser.add_argument("--course", help="Course name or Course ID (e.g. psych, ushist, 6298933)")
    parser.add_argument("--teacher", help="Teacher name filter for messages (e.g. 'Jay', 'Smith')")
    parser.add_argument("--assign", help="Assignment ID for goassign(id), or 'all' for download-assign")
    parser.add_argument("--file", help="File path to submit (for turnin)")
    parser.add_argument("--out", help="Output directory to automatically download attachments into")
    parser.add_argument("--screenshot", help="Path to save screenshot")
    parser.add_argument("--config", help="Path to custom config.json")
    parser.add_argument("--username", help="Student username/ID (for setup)")
    parser.add_argument("--password", help="Student password (for setup)")
    parser.add_argument("--cdp", help="Remote debugging port or URL (e.g. 9222 or http://localhost:9222) for attach")

    args = parser.parse_args()

    # Always output attribution signature
    print_attribution()

    if args.action == "setup":
        action_setup(args)
        return
    elif args.action == "login":
        action_login(args)
        return
    elif args.action == "attach":
        action_attach(args)
        return

    cfg, _ = load_config(args.config)
    github_url = cfg.get("github_repo", DEFAULT_GITHUB_REPO)
    check_first_run_notice(get_base_dir(), github_url)

    if args.action == "todo":
        action_todo(args, cfg)
    elif args.action == "grades":
        action_grades(args, cfg)
    elif args.action == "detail":
        action_detail(args, cfg)
    elif args.action == "download-assign":
        action_download_assign(args, cfg)
    elif args.action == "materials":
        action_materials(args, cfg)
    elif args.action == "messages":
        action_messages(args, cfg)
    elif args.action == "turnin":
        action_turnin(args, cfg)

if __name__ == "__main__":
    main()
