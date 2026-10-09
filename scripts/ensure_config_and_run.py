#!/usr/bin/env python3
"""
CPG-Hub 配置自检与一键打开注册页

- 读取 .env 与 ~/.openclaw/openclaw.json，判断缺失的 API Key
- 未配置的项用 wateryu2030@gmail.com 打开注册/获取 Key 页面（无法自动过验证时需人工完成）
- 执行健康检查，确保服务能正常启动与响应

用法: python scripts/ensure_config_and_run.py [--open-pages] [--health-only]
  --open-pages  打开所有未配置项的注册/获取 Key 页面（默认打开）
  --health-only 仅做健康检查，不打开浏览器
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"

# 未配置时打开的链接（注册或获取 Key，优先可预填邮箱的）
MISSING_LINKS = {
    "OMKAR_CLOUD_API_KEY": [
        ("注册", "https://omkar.cloud/auth/sign-up"),
        ("获取 Key", "https://omkar.cloud/api-key"),
    ],
    "OPENROUTER_API_KEY": [
        ("注册", "https://openrouter.ai/sign-up"),
        ("获取 Key", "https://openrouter.ai/keys"),
    ],
    "PERPLEXITY_API_KEY": [
        ("获取 Key", "https://perplexity.ai/account/api"),
    ],
    "OPENCLAW_API_KEY": [
        ("申请", "https://www.clawhub.com/"),
    ],
    "LLM": [
        ("智谱", "https://open.bigmodel.cn/"),
        ("百度千帆", "https://console.bce.baidu.com/"),
        ("OpenAI", "https://platform.openai.com/api-keys"),
    ],
}


def load_dotenv() -> dict:
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1].replace('\\"', '"')
                env[k] = v
    return env


def load_openclaw_json() -> dict:
    if not OPENCLAW_JSON.exists():
        return {}
    try:
        with open(OPENCLAW_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def effective_keys(env: dict, oc: dict) -> dict:
    """结合 .env 与 openclaw.json 判断“有效”已配置的 Key（与 config 逻辑一致）。"""
    out = {
        "omkar_cloud_api_key": bool(env.get("OMKAR_CLOUD_API_KEY") and env.get("OMKAR_CLOUD_API_KEY") not in ("", "your_omkar_cloud_api_key_here")),
        "openrouter_api_key": bool(env.get("OPENROUTER_API_KEY") and env.get("OPENROUTER_API_KEY").startswith("sk-or-")),
        "perplexity_api_key": bool(env.get("PERPLEXITY_API_KEY")),
        "openclaw_api_key": bool(env.get("OPENCLAW_API_KEY") and env.get("OPENCLAW_API_KEY") not in ("", "your_openclaw_api_key_here")),
        "llm": bool(
            (env.get("ZHIPU_API_KEY") and "your_" not in (env.get("ZHIPU_API_KEY") or ""))
            or (env.get("BAIDU_API_KEY") and "your_" not in (env.get("BAIDU_API_KEY") or ""))
            or (env.get("OPENAI_API_KEY") and (env.get("OPENAI_API_KEY") or "").startswith("sk-"))
        ),
    }
    # 从 openclaw.json 补充
    if not out["openrouter_api_key"] and oc.get("models", {}).get("providers"):
        for pcfg in oc["models"]["providers"].values():
            if "openrouter" in str(pcfg.get("baseUrl", "")).lower() and pcfg.get("apiKey"):
                out["openrouter_api_key"] = True
                break
    if not out["perplexity_api_key"] and oc.get("tools", {}).get("web", {}).get("search", {}).get("perplexity", {}).get("apiKey"):
        out["perplexity_api_key"] = True
    if not out["openclaw_api_key"] and oc.get("skills", {}).get("entries"):
        for name in ("baidu-preferred", "baidu_preferred"):
            ent = oc["skills"]["entries"].get(name, {})
            if isinstance(ent, dict) and ent.get("apiKey"):
                out["openclaw_api_key"] = True
                break
    return out


def missing_list(eff: dict) -> list[str]:
    missing = []
    if not eff["omkar_cloud_api_key"]:
        missing.append("OMKAR_CLOUD_API_KEY")
    if not eff["openrouter_api_key"] and not eff["perplexity_api_key"]:
        missing.append("OPENROUTER_API_KEY")  # 或 PERPLEXITY，只提示一个
    if not eff["openclaw_api_key"]:
        missing.append("OPENCLAW_API_KEY")
    if not eff["llm"]:
        missing.append("LLM")
    return missing


def open_urls(urls: list[tuple[str, str]]) -> None:
    for _label, url in urls:
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False, capture_output=True)
        elif sys.platform == "linux":
            subprocess.run(["xdg-open", url], check=False, capture_output=True)
        else:
            import webbrowser
            webbrowser.open(url)
        time.sleep(1.5)


def check_server(port: int = 8000) -> bool:
    """检测指定端口的服务是否已就绪（不启动新进程）。"""
    try:
        import urllib.request
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=3)
        return r.status == 200
    except Exception:
        return False


def run_self_improve(open_pages: bool = False, verbose: bool = True) -> bool:
    """
    自我完善一轮：配置自检 + 可选打开注册页 + 健康检查。
    可被 openclaw_control 循环调用。返回 True 表示服务就绪或自检通过。
    """
    os.chdir(ROOT)
    env = load_dotenv()
    oc = load_openclaw_json()
    eff = effective_keys(env, oc)
    missing = missing_list(eff)

    if verbose:
        print("==========================================")
        print("CPG-Hub 配置自检（wateryu2030@gmail.com）")
        print("==========================================")
        if eff["openrouter_api_key"] or eff["perplexity_api_key"]:
            print("[已配置] 政策自动搜索（OpenRouter/Perplexity）")
        if eff["llm"]:
            print("[已配置] LLM（智谱/百度/OpenAI）")
        if eff["omkar_cloud_api_key"]:
            print("[已配置] OMKAR_CLOUD_API_KEY")
        if eff["openclaw_api_key"]:
            print("[已配置] OPENCLAW_API_KEY")
        if missing:
            print("\n未配置项:", ", ".join(missing))
            if open_pages:
                print("正在打开注册/获取 Key 页面…")
                for key in missing:
                    links = MISSING_LINKS.get(key)
                    if links:
                        open_urls(links)
                print("请将 Key 填入 .env 后保存，下一轮将重新检测。")
        else:
            print("\n[OK] 所有推荐 Key 已配置（或已由 ~/.openclaw 补充）")

    # 先检测已在运行的服务（端口 8000）
    if check_server(8000):
        if verbose:
            print("\n[OK] 服务已在运行 http://localhost:8000")
        return True
    # 再通过临时进程做健康检查
    if verbose:
        print("\n执行健康检查…")
    ok = health_check()
    return ok


def health_check() -> bool:
    """启动服务并请求 /api/v1/health、/api/v1/，确认正常后结束进程。使用 18080 避免与已有 8000 冲突。"""
    port = "18080"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError:
        print("[WARN] 未找到 uvicorn，请先安装依赖: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"[WARN] 启动失败: {e}")
        return False

    try:
        for _ in range(30):
            time.sleep(0.5)
            try:
                import urllib.request
                r = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=2)
                if r.status == 200:
                    r2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
                    if r2.status == 200:
                        print("[OK] 服务已启动，/ 与 /api/v1/health 正常")
                        return True
            except OSError:
                continue
            except Exception:
                continue
        err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        print("[WARN] 服务 15 秒内未就绪。若在沙箱/无网络环境，请在终端执行下方命令验证。")
        if err:
            print("stderr:", err[:500])
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def get_status() -> tuple[dict, list[str]]:
    """返回 (effective_keys, missing_list)，供 openclaw_control status 等使用。"""
    os.chdir(ROOT)
    env = load_dotenv()
    oc = load_openclaw_json()
    eff = effective_keys(env, oc)
    missing = missing_list(eff)
    return eff, missing


def main():
    ap = argparse.ArgumentParser(description="配置自检并可选打开注册页、执行健康检查")
    ap.add_argument("--open-pages", action="store_true", help="明确打开未配置项的注册/获取 Key 页面")
    ap.add_argument("--no-open-pages", action="store_true", help="不打开浏览器，仅检测与健康检查")
    ap.add_argument("--health-only", action="store_true", help="仅健康检查")
    args = ap.parse_args()

    open_pages = (args.open_pages or not args.no_open_pages) and not args.health_only
    if args.health_only:
        ok = check_server(8000) or health_check()
        sys.exit(0 if ok else 1)
    ok = run_self_improve(open_pages=open_pages, verbose=True)
    if not ok:
        print("\n--- 请在终端执行以下命令查看效果 ---")
        print("  cd", str(ROOT))
        print("  python3 -m venv .venv && source .venv/bin/activate")
        print("  pip install -q -r requirements.txt")
        print("  python3 scripts/ensure_config_and_run.py --no-open-pages")
        print("  # 或 OpenClaw 控制: python3 scripts/openclaw_control.py self-improve --loop")
        print("---")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
