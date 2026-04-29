#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
███████╗██╗  ██╗ █████╗ ██╗  ██╗██╗██████╗     ██████╗ ██╗   ██╗ ██████╗
██╔════╝██║  ██║██╔══██╗██║  ██║██║██╔══██╗    ██╔══██╗██║   ██║██╔════╝
███████╗███████║███████║███████║██║██║  ██║    ██████╔╝██║   ██║██║  ███╗
╚════██║██╔══██║██╔══██║██╔══██║██║██║  ██║    ██╔══██╗██║   ██║██║   ██║
███████║██║  ██║██║  ██║██║  ██║██║██████╔╝    ██████╔╝╚██████╔╝╚██████╔╝
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═════╝     ╚═════╝  ╚═════╝  ╚═════╝
        Advanced All-in-One SNI / HTTP Bug Host Finder for Termux
                         Version 1.0 — T-REX DEV
"""
import os, sys, ssl, socket, json, csv, re, time, signal, subprocess, ipaddress, threading, queue, glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ---------------- AUTO-INSTALL DEPENDENCIES ----------------
REQUIRED = ["requests", "colorama", "pyfiglet", "dnspython", "tqdm", "beautifulsoup4"]
def _install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
for pkg in REQUIRED:
    mod = "dns" if pkg == "dnspython" else ("bs4" if pkg == "beautifulsoup4" else pkg)
    try:
        __import__(mod)
    except ImportError:
        print(f"[*] Installing {pkg} ...")
        try: _install(pkg)
        except Exception as e: print(f"[!] Could not install {pkg}: {e}")

import requests
from colorama import Fore, Back, Style, init as colorama_init
import pyfiglet
import dns.resolver
from tqdm import tqdm
from bs4 import BeautifulSoup

colorama_init(autoreset=True)
requests.packages.urllib3.disable_warnings()

# ---------------- THEME ----------------
C = Fore.CYAN; M = Fore.MAGENTA; Y = Fore.YELLOW; G = Fore.GREEN
R = Fore.RED; W = Fore.WHITE; B = Fore.BLUE; D = Style.DIM; BR = Style.BRIGHT; RS = Style.RESET_ALL

# ---------------- CONFIG ----------------
HOME = os.path.expanduser("~")
BASE_DIR = os.path.join(HOME, "trexdev")
RES_DIR  = os.path.join(BASE_DIR, "results")
os.makedirs(RES_DIR, exist_ok=True)

CONFIG = {"threads": 50, "timeout": 5, "user_agent": "Mozilla/5.0 (T-REX-DEV/1.0)"}

# ---------------- UTILS ----------------
def banner():
    os.system("clear" if os.name != "nt" else "cls")
    art = pyfiglet.figlet_format("T-REX DEV", font="slant")
    print(M + BR + art + RS)
    print(C + "  ╔══════════════════════════════════════════════════════════════╗")
    print(C + "  ║ " + Y + "Advanced SNI / HTTP Bug Host Finder — All-in-One Toolkit " + C + "║")
    print(C + "  ║ " + G + "Termux ✓  Linux ✓  Windows ✓   v1.0   © T-REX DEV       " + C + "║")
    print(C + "  ╚══════════════════════════════════════════════════════════════╝" + RS)

def stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def ask(prompt, default=None):
    txt = f"{Y}[?] {prompt}"
    if default is not None: txt += f" {D}({default}){RS}"
    txt += f"{Y} >>> {RS}"
    v = input(txt).strip()
    return v if v else (default if default is not None else "")

def info(msg):  print(f"{C}[i] {msg}{RS}")
def ok(msg):    print(f"{G}[+] {msg}{RS}")
def warn(msg):  print(f"{Y}[!] {msg}{RS}")
def err(msg):   print(f"{R}[x] {msg}{RS}")
def pause():    input(f"\n{D}Press ENTER to return to menu...{RS}")

def load_input(path):
    """Load hosts from file or directory of .txt files (bulk)."""
    hosts = []
    if not path: return hosts
    if os.path.isdir(path):
        for f in glob.glob(os.path.join(path, "*.txt")):
            hosts += load_input(f)
        return hosts
    if not os.path.isfile(path):
        err(f"File not found: {path}"); return hosts
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                hosts.append(line)
    return list(dict.fromkeys(hosts))  # dedupe, keep order

def save_results(rows, mode, headers=None):
    if not rows: warn("Nothing to save."); return
    base = os.path.join(RES_DIR, f"{stamp()}_{mode}")
    # txt
    with open(base + ".txt", "w", encoding="utf-8") as f:
        for r in rows:
            f.write((r if isinstance(r, str) else " | ".join(map(str, r.values()))) + "\n")
    # csv + json (only if dict rows)
    if rows and isinstance(rows[0], dict):
        with open(base + ".csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        # html
        html = ["<html><head><style>",
                "body{background:#0b0b1a;color:#0ff;font-family:monospace;padding:20px}",
                "table{border-collapse:collapse;width:100%}",
                "th,td{border:1px solid #555;padding:6px}",
                "th{background:#222;color:#ff0}tr:nth-child(even){background:#111}",
                "</style></head><body><h1>T-REX DEV — Report</h1><table><tr>"]
        for k in rows[0].keys(): html.append(f"<th>{k}</th>")
        html.append("</tr>")
        for r in rows:
            html.append("<tr>" + "".join(f"<td>{r[k]}</td>" for k in rows[0].keys()) + "</tr>")
        html.append("</table></body></html>")
        with open(base + ".html", "w", encoding="utf-8") as f: f.write("".join(html))
    ok(f"Saved → {base}.[txt|csv|json|html]")

# ---------------- 1. HOST SCANNER ----------------
def scan_direct(host, port=80, method="HEAD", scheme="http"):
    try:
        url = f"{scheme}://{host}:{port}"
        r = requests.request(method, url, timeout=CONFIG["timeout"],
                             allow_redirects=False, verify=False,
                             headers={"User-Agent": CONFIG["user_agent"]})
        return {"host": host, "port": port, "code": r.status_code,
                "server": r.headers.get("Server", "-"),
                "location": r.headers.get("Location", "-")}
    except Exception:
        return None

def scan_ssl(host, port=443):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=CONFIG["timeout"]) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert(binary_form=False) or {}
                proto = ss.version()
                cn = "-"
                try:
                    der = ss.getpeercert(True)
                    import ssl as _s
                    pem = _s.DER_cert_to_PEM_cert(der)
                    m = re.search(r"CN=([^,/\n]+)", pem)
                    if m: cn = m.group(1)
                except: pass
                return {"host": host, "port": port, "tls": proto, "cn": cn, "status": "OK"}
    except Exception as e:
        return None

def scan_proxy(host, proxy, port=80):
    try:
        ph, pp = proxy.split(":")
        s = socket.socket(); s.settimeout(CONFIG["timeout"])
        s.connect((ph, int(pp)))
        req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}\r\n\r\n"
        s.sendall(req.encode())
        data = s.recv(1024).decode(errors="ignore")
        s.close()
        first = data.split("\r\n")[0] if data else ""
        return {"host": host, "proxy": proxy, "response": first}
    except Exception:
        return None

def tcp_ping(host, port=443):
    try:
        t = time.time()
        s = socket.create_connection((host, port), timeout=CONFIG["timeout"])
        ms = int((time.time()-t)*1000); s.close()
        return {"host": host, "port": port, "ping_ms": ms}
    except Exception:
        return None

def menu_host_scanner():
    banner()
    print(f"{Y}{BR}>> Host Scanner Modes{RS}")
    print(f"{C}  [1] Direct (HTTP)\n  [2] DirectNon-302\n  [3] SSL / SNI\n  [4] Proxy CONNECT\n  [5] TCP / Ping{RS}")
    mode = ask("Select mode", "1")
    path = ask("Path to host file or folder")
    hosts = load_input(path)
    if not hosts: err("No hosts loaded."); pause(); return
    port = int(ask("Port", "443" if mode=="3" else "80"))
    proxy = ask("Proxy host:port", "0.0.0.0:8080") if mode == "4" else None
    method = ask("HTTP method", "HEAD") if mode in ("1","2") else "HEAD"
    scheme = "https" if port == 443 else "http"

    info(f"Loaded {len(hosts)} hosts | mode={mode} | port={port} | threads={CONFIG['threads']}")
    rows = []
    def task(h):
        if mode in ("1","2"):
            r = scan_direct(h, port, method, scheme)
            if r and (mode=="1" or r["code"] != 302): return r
        elif mode == "3":
            return scan_ssl(h, port)
        elif mode == "4":
            return scan_proxy(h, proxy, port)
        elif mode == "5":
            return tcp_ping(h, port)
        return None

    with ThreadPoolExecutor(max_workers=CONFIG["threads"]) as ex:
        futs = {ex.submit(task, h): h for h in hosts}
        for f in tqdm(as_completed(futs), total=len(futs), desc=f"{M}Scanning{RS}", ncols=80):
            r = f.result()
            if r:
                rows.append(r)
                tqdm.write(f"{G}[+] {r}{RS}")
    ok(f"Done. Found {len(rows)} working hosts.")
    save_results(rows, f"hostscan_mode{mode}")
    pause()

# ---------------- 2. SUBDOMAIN FINDER ----------------
def sub_crtsh(d):
    try:
        r = requests.get(f"https://crt.sh/?q=%25.{d}&output=json", timeout=15)
        return [n.strip() for x in r.json() for n in x["name_value"].split("\n")]
    except: return []
def sub_hackertarget(d):
    try:
        r = requests.get(f"https://api.hackertarget.com/hostsearch/?q={d}", timeout=15)
        return [l.split(",")[0] for l in r.text.splitlines() if "," in l]
    except: return []
def sub_rapiddns(d):
    try:
        r = requests.get(f"https://rapiddns.io/subdomain/{d}?full=1", timeout=15,
                         headers={"User-Agent": CONFIG["user_agent"]})
        soup = BeautifulSoup(r.text, "html.parser")
        return [td.text.strip() for td in soup.select("td") if "."+d in td.text]
    except: return []
def sub_otx(d):
    try:
        r = requests.get(f"https://otx.alienvault.com/api/v1/indicators/domain/{d}/passive_dns", timeout=15)
        return [x["hostname"] for x in r.json().get("passive_dns", [])]
    except: return []
def sub_anubis(d):
    try:
        r = requests.get(f"https://jonlu.ca/anubis/subdomains/{d}", timeout=15)
        return r.json() if isinstance(r.json(), list) else []
    except: return []

def menu_subfinder():
    banner()
    print(f"{Y}{BR}>> Subdomain Finder (Passive, Multi-Source){RS}")
    domain = ask("Target domain (or path to domains.txt)")
    if not domain: pause(); return
    domains = load_input(domain) if os.path.exists(domain) else [domain]
    all_subs = set()
    for d in domains:
        info(f"Searching subdomains for: {d}")
        sources = [("crt.sh", sub_crtsh), ("HackerTarget", sub_hackertarget),
                   ("RapidDNS", sub_rapiddns), ("AlienVault", sub_otx), ("Anubis", sub_anubis)]
        for name, fn in sources:
            res = fn(d)
            ok(f"  {name}: {len(res)} found")
            for s in res:
                s = s.lower().lstrip("*.").strip()
                if s.endswith(d): all_subs.add(s)
    subs = sorted(all_subs)
    ok(f"Total unique subdomains: {len(subs)}")
    for s in subs[:50]: print(f"  {C}{s}{RS}")
    if len(subs) > 50: info(f"... and {len(subs)-50} more (saved to file)")
    save_results(subs, "subdomains")
    pause()

# ---------------- 3. REVERSE IP ----------------
def reverse_ip(ip):
    out = set()
    try:
        r = requests.get(f"https://api.hackertarget.com/reverseiplookup/?q={ip}", timeout=15)
        for l in r.text.splitlines():
            if l and not l.startswith("error"): out.add(l.strip())
    except: pass
    try:
        r = requests.get(f"https://rapiddns.io/sameip/{ip}?full=1", timeout=15,
                         headers={"User-Agent": CONFIG["user_agent"]})
        soup = BeautifulSoup(r.text, "html.parser")
        for td in soup.select("td"):
            t = td.text.strip()
            if "." in t and " " not in t: out.add(t)
    except: pass
    return out

def menu_reverse_ip():
    banner()
    print(f"{Y}{BR}>> Reverse IP / Same-Host Lookup{RS}")
    target = ask("IP, CIDR, or path to ips.txt")
    targets = []
    if os.path.exists(target): targets = load_input(target)
    elif "/" in target:
        try: targets = [str(x) for x in ipaddress.ip_network(target, strict=False)]
        except: err("Bad CIDR"); pause(); return
    else: targets = [target]
    info(f"Resolving {len(targets)} target(s)...")
    rows = []
    for ip in tqdm(targets, desc="ReverseIP", ncols=80):
        for d in reverse_ip(ip):
            rows.append({"ip": ip, "domain": d})
    ok(f"Total domains found: {len(rows)}")
    save_results(rows, "reverseip")
    pause()

# ---------------- 4. IP / CIDR SCANNER ----------------
def menu_ip_scanner():
    banner()
    print(f"{Y}{BR}>> IP / CIDR Scanner{RS}")
    target = ask("IP, CIDR, or ips.txt path")
    if os.path.exists(target): ips = load_input(target)
    elif "/" in target:
        try: ips = [str(x) for x in ipaddress.ip_network(target, strict=False)]
        except: err("Bad CIDR"); pause(); return
    else: ips = [target]
    port = int(ask("Port", "443"))
    rows = []
    with ThreadPoolExecutor(max_workers=CONFIG["threads"]) as ex:
        futs = {ex.submit(scan_ssl if port==443 else scan_direct, ip, port): ip for ip in ips}
        for f in tqdm(as_completed(futs), total=len(futs), desc="IP-Scan", ncols=80):
            r = f.result()
            if r: rows.append(r); tqdm.write(f"{G}[+] {r}{RS}")
    save_results(rows, "ipscan"); pause()

# ---------------- 5. DNS RECORDS ----------------
def menu_dns():
    banner()
    print(f"{Y}{BR}>> DNS Records Toolkit{RS}")
    d = ask("Domain")
    if not d: pause(); return
    rows = []
    for rt in ["A","AAAA","MX","NS","TXT","CNAME","SOA"]:
        try:
            ans = dns.resolver.resolve(d, rt, lifetime=8)
            for a in ans:
                v = str(a)
                print(f"  {C}{rt:<6}{RS} {Y}{v}{RS}")
                rows.append({"type": rt, "value": v})
        except Exception:
            print(f"  {D}{rt:<6} —{RS}")
    save_results(rows, f"dns_{d}"); pause()

# ---------------- 6. PORT SCANNER ----------------
def menu_ports():
    banner()
    print(f"{Y}{BR}>> Open Port Scanner{RS}")
    target = ask("IP / domain")
    custom = ask("Ports (comma) or 'common'", "common")
    ports = [80,443,8080,8443,53,22,8000,2052,2053,2082,2083,2086,2087,2095,2096] \
        if custom == "common" else [int(p) for p in custom.split(",") if p.strip().isdigit()]
    rows = []
    def chk(p):
        try:
            s = socket.create_connection((target, p), timeout=2); s.close()
            return p
        except: return None
    with ThreadPoolExecutor(max_workers=100) as ex:
        for r in tqdm(ex.map(chk, ports), total=len(ports), desc="Ports", ncols=80):
            if r:
                ok(f"  Open: {r}")
                rows.append({"host": target, "port": r, "state": "open"})
    save_results(rows, f"ports_{target}"); pause()

# ---------------- 7. HOST OSINT ----------------
def menu_osint():
    banner()
    print(f"{Y}{BR}>> Host OSINT & CDN Detect{RS}")
    h = ask("Host")
    if not h: pause(); return
    row = {"host": h}
    try:
        ip = socket.gethostbyname(h); row["ip"] = ip; ok(f"IP: {ip}")
    except: row["ip"] = "-"
    try:
        r = requests.get(f"http://{h}", timeout=8, allow_redirects=False, verify=False,
                         headers={"User-Agent": CONFIG["user_agent"]})
        srv = r.headers.get("Server","-"); row["server"] = srv
        ok(f"Server: {srv}")
        cdn = "Unknown"
        s = srv.lower()
        if "cloudflare" in s: cdn = "Cloudflare"
        elif "akamai" in s: cdn = "Akamai"
        elif "fastly" in s: cdn = "Fastly"
        elif "google" in s or "gws" in s: cdn = "Google"
        elif "amazon" in s or "aws" in s: cdn = "AWS"
        row["cdn"] = cdn; ok(f"CDN: {cdn}")
    except Exception as e: warn(str(e))
    ssl_info = scan_ssl(h, 443)
    if ssl_info:
        row.update({"tls": ssl_info["tls"], "cn": ssl_info["cn"]})
        ok(f"TLS: {ssl_info['tls']} | CN: {ssl_info['cn']}")
    save_results([row], f"osint_{h}"); pause()

# ---------------- 8. SNI TLS PING ----------------
def menu_tlsping():
    banner()
    print(f"{Y}{BR}>> SNI TLS-Ping Tester{RS}")
    path = ask("Path to sni.txt")
    hosts = load_input(path)
    if not hosts: pause(); return
    rows = []
    def ping(h):
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
            t = time.time()
            with socket.create_connection((h, 443), timeout=CONFIG["timeout"]) as sock:
                with ctx.wrap_socket(sock, server_hostname=h) as ss:
                    ms = int((time.time()-t)*1000)
                    return {"host": h, "tls_ping_ms": ms, "tls": ss.version()}
        except: return None
    with ThreadPoolExecutor(max_workers=CONFIG["threads"]) as ex:
        for r in tqdm(ex.map(ping, hosts), total=len(hosts), desc="TLS-Ping", ncols=80):
            if r: rows.append(r)
    rows.sort(key=lambda x: x["tls_ping_ms"])
    print(f"\n{Y}{'Host':<40}{'TLS':<10}{'Ping (ms)':<10}{RS}")
    print(C + "-"*60 + RS)
    for r in rows[:30]:
        print(f"{G}{r['host']:<40}{C}{str(r['tls']):<10}{Y}{r['tls_ping_ms']:<10}{RS}")
    save_results(rows, "tlsping"); pause()

# ---------------- 9. FILE TOOLS ----------------
def menu_filetools():
    banner()
    print(f"{Y}{BR}>> File Tools{RS}")
    print(f"{C}  [1] Split file\n  [2] Merge files\n  [3] Deduplicate\n  [4] Sort\n  [5] Filter by keyword/regex\n  [6] Remove blanks{RS}")
    op = ask("Choose", "3")
    if op == "1":
        f = ask("File"); n = int(ask("Lines per chunk", "1000"))
        lines = open(f, encoding="utf-8", errors="ignore").read().splitlines()
        for i in range(0, len(lines), n):
            out = f"{f}.part{i//n+1}.txt"
            open(out, "w").write("\n".join(lines[i:i+n]))
            ok(f"Wrote {out}")
    elif op == "2":
        folder = ask("Folder of .txt files"); merged = []
        for x in glob.glob(os.path.join(folder, "*.txt")):
            merged += open(x, encoding="utf-8", errors="ignore").read().splitlines()
        out = os.path.join(RES_DIR, f"merged_{stamp()}.txt")
        open(out, "w").write("\n".join(merged)); ok(f"Saved {out}")
    elif op == "3":
        f = ask("File"); lines = list(dict.fromkeys(open(f, encoding="utf-8", errors="ignore").read().splitlines()))
        out = f + ".dedup.txt"; open(out,"w").write("\n".join(lines)); ok(f"Saved {out} ({len(lines)} unique)")
    elif op == "4":
        f = ask("File"); lines = sorted(set(open(f, encoding="utf-8", errors="ignore").read().splitlines()))
        out = f + ".sorted.txt"; open(out,"w").write("\n".join(lines)); ok(f"Saved {out}")
    elif op == "5":
        f = ask("File"); pat = ask("Keyword or regex")
        lines = [l for l in open(f, encoding="utf-8", errors="ignore").read().splitlines() if re.search(pat, l)]
        out = f + ".filtered.txt"; open(out,"w").write("\n".join(lines)); ok(f"Saved {out} ({len(lines)} matches)")
    elif op == "6":
        f = ask("File"); lines = [l for l in open(f, encoding="utf-8", errors="ignore").read().splitlines() if l.strip()]
        out = f + ".clean.txt"; open(out,"w").write("\n".join(lines)); ok(f"Saved {out}")
    pause()

# ---------------- 10. IMPORT / EXPORT ----------------
def menu_io():
    banner()
    print(f"{Y}{BR}>> Import / Export Manager{RS}")
    print(f"{C}  [1] CSV → TXT\n  [2] TXT → CSV\n  [3] JSON → TXT\n  [4] List results folder{RS}")
    op = ask("Choose", "4")
    if op == "1":
        f = ask("CSV file"); col = ask("Column name", "host")
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        out = f + ".txt"; open(out,"w").write("\n".join(r[col] 
