#!/usr/bin/env python3
"""
OpenClaw 控制 CPG-Hub：启动/停止/状态/自我迭代完善

终端执行后可由 OpenClaw 或 cron 调用，实现自我迭代、自我完善（配置自检 → 打开注册页 → 健康检查 → 循环直到就绪）。

用法:
  python3 scripts/openclaw_control.py start          # 后台启动服务
  python3 scripts/openclaw_control.py stop           # 停止服务
  python3 scripts/openclaw_control.py status         # 配置与运行状态
  python3 scripts/openclaw_control.py self-improve   # 自检 + 健康检查一轮
  python3 scripts/openclaw_control.py self-improve --loop --interval 60  # 自我迭代直到就绪（每 60 秒重试）
  python3 scripts/openclaw_control.py self-improve --loop --then-start   # 就绪后自动后台启动服务
  python3 scripts/openclaw_control.py iterate-now                        # 立即执行一轮后续工作（积累+爬虫），终端可见
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PID_FILE = ROOT / ".cpg-hub.pid"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "cpg-hub.log"
PORT = int(os.environ.get("PORT", "8000"))


def _which(name: str) -> bool:
    try:
        import shutil
        return shutil.which(name) is not None
    except Exception:
        return False


def _ensure_venv_and_deps() -> bool:
    venv = ROOT / ".venv"
    if not venv.is_dir():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], cwd=str(ROOT), check=True)
    pip = venv / "bin" / "pip"
    if not pip.exists():
        pip = venv / "Scripts" / "pip.exe"
    if pip.exists():
        subprocess.run([str(pip), "install", "-q", "-r", "requirements.txt"], cwd=str(ROOT), timeout=120, check=False)
    return True


def _python_bin() -> str:
    venv_py = ROOT / ".venv" / "bin" / "python3"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def _server_running() -> bool:
    """检测当前端口是否已有服务。"""
    mod = _load_ensure_module()
    return mod.check_server(PORT)


def cmd_start() -> int:
    """后台启动服务（等价 run_daemon.sh）。"""
    if _server_running():
        print(f"服务已在运行 http://localhost:{PORT}，无需重复启动。停止请用: python3 scripts/openclaw_control.py stop")
        return 0
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_venv_and_deps()
    # 政策库
    policy_script = ROOT / "scripts" / "ensure_policy_library.py"
    if policy_script.exists():
        subprocess.run([_python_bin(), str(policy_script)], cwd=str(ROOT), capture_output=True, timeout=60)
    # 启动 uvicorn
    py = _python_bin()
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    cmd = [py, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(PORT)]
    if sys.platform == "darwin" and _which("caffeinate"):
        cmd = ["caffeinate", "-i"] + cmd
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    PID_FILE.write_text(str(proc.pid))
    print(f"CPG-Hub 后台启动中... 日志: {LOG_FILE}")
    print(f"停止: kill $(cat {PID_FILE})")
    time.sleep(2)
    if proc.poll() is not None:
        print("启动失败，请查看日志:", LOG_FILE)
        print("若端口已被占用，请先执行: python3 scripts/openclaw_control.py stop")
        PID_FILE.unlink(missing_ok=True)
        return 1
    print(f"已启动 PID {proc.pid}，访问 http://localhost:{PORT}")
    return 0


def cmd_stop() -> int:
    """停止服务。"""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"已停止 CPG-Hub (PID {pid})")
        except ProcessLookupError:
            print("进程已不存在")
        except Exception as e:
            print(f"停止失败: {e}")
        PID_FILE.unlink(missing_ok=True)
        return 0
    # 按端口杀进程
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{PORT}"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            for p in out.stdout.strip().split():
                try:
                    os.kill(int(p), signal.SIGTERM)
                    print(f"已停止占用 {PORT} 端口的进程 {p}")
                except Exception:
                    pass
            return 0
    except FileNotFoundError:
        pass
    print("未发现运行中的服务")
    return 0


def _load_ensure_module():
    """按路径加载 ensure_config_and_run，不依赖 scripts 包。"""
    import importlib.util
    path = ROOT / "scripts" / "ensure_config_and_run.py"
    spec = importlib.util.spec_from_file_location("ensure_config_and_run", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_status() -> int:
    """输出配置与运行状态。"""
    mod = _load_ensure_module()
    eff, missing = mod.get_status()
    print("==========================================")
    print("CPG-Hub 状态（OpenClaw 控制）")
    print("==========================================")
    print("配置:")
    if eff.get("openrouter_api_key") or eff.get("perplexity_api_key"):
        print("  [已配置] 政策自动搜索（OpenRouter/Perplexity）")
    if eff.get("llm"):
        print("  [已配置] LLM（智谱/百度/OpenAI）")
    if eff.get("omkar_cloud_api_key"):
        print("  [已配置] OMKAR_CLOUD_API_KEY")
    if eff.get("openclaw_api_key"):
        print("  [已配置] OPENCLAW_API_KEY")
    if missing:
        print("  未配置项:", ", ".join(missing))
    print()
    if mod.check_server(PORT):
        print(f"服务: 运行中 http://localhost:{PORT}")
    else:
        print("服务: 未运行（可执行 start 或 self-improve）")
    return 0


def cmd_self_improve(
    loop: bool = False,
    interval: int = 60,
    max_rounds: int = 0,
    open_pages: bool = False,
    then_start: bool = False,
) -> int:
    """自我完善：配置自检 + 可选打开注册页 + 健康检查；--loop 时循环直到就绪。"""
    mod = _load_ensure_module()
    round_n = 0
    while True:
        round_n += 1
        if loop and round_n > 1:
            print(f"\n--- 第 {round_n} 轮自我完善（每 {interval}s 重试）---")
        ok = mod.run_self_improve(open_pages=open_pages and round_n == 1, verbose=True)
        if ok:
            if loop and round_n > 1:
                print("\n[OK] 自我迭代完成，服务已就绪。")
            if then_start and not mod.check_server(PORT):
                print("\n正在后台启动服务（--then-start）…")
                return cmd_start()
            return 0
        if not loop:
            return 1
        if max_rounds > 0 and round_n >= max_rounds:
            print(f"\n已达最大轮数 {max_rounds}，退出。")
            return 1
        print(f"\n{interval} 秒后重新检测（可 Ctrl+C 退出）…")
        time.sleep(interval)


def cmd_iterate_now() -> int:
    """立即执行一轮「后续工作」：持续积累（政策+热销+关键词）+ 可选政策/媒体爬虫，便于在终端看到自我迭代。"""
    import asyncio
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))

    async def _run():
        from jobs.sync_jobs import run_accumulate_content
        from crawler.policy_crawler import run_policy_crawl
        from crawler.media_crawler import run_media_crawl
        print("==========================================")
        print("OpenClaw 自我迭代：执行一轮后续工作")
        print("==========================================")
        try:
            result = await asyncio.wait_for(run_accumulate_content(), timeout=180.0)
            print("[积累] 政策+热销+关键词轮询:", result)
        except asyncio.TimeoutError:
            print("[积累] 超时 (180s)")
        except Exception as e:
            print("[积累] 错误:", e)
        try:
            n = await run_policy_crawl()
            print("[爬虫] 政策抓取:", n, "条")
        except Exception as e:
            print("[爬虫] 政策:", e)
        try:
            n = await run_media_crawl()
            print("[爬虫] 媒体热点:", n, "条")
        except Exception as e:
            print("[爬虫] 媒体:", e)
        print("------------------------------------------")
        print("本轮完成。服务运行时会每 15 分钟自动执行「持续积累」，每周/每日执行爬虫。")

    asyncio.run(_run())
    return 0


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="OpenClaw 控制 CPG-Hub：start | stop | status | self-improve | iterate-now")
    ap.add_argument("command", choices=["start", "stop", "status", "self-improve", "iterate-now"], help="子命令")
    ap.add_argument("--loop", action="store_true", help="self-improve 时循环直到服务就绪")
    ap.add_argument("--interval", type=int, default=60, help="--loop 时重试间隔（秒），默认 60")
    ap.add_argument("--max-rounds", type=int, default=0, help="--loop 时最大轮数，0 表示不限制")
    ap.add_argument("--open-pages", action="store_true", help="self-improve 时对未配置项打开注册页（仅第一轮）")
    ap.add_argument("--then-start", action="store_true", help="self-improve 就绪后自动执行 start 启动后台服务")
    args = ap.parse_args()

    os.chdir(ROOT)

    if args.command == "start":
        return cmd_start()
    if args.command == "stop":
        return cmd_stop()
    if args.command == "status":
        return cmd_status()
    if args.command == "self-improve":
        return cmd_self_improve(
            loop=args.loop,
            interval=args.interval,
            max_rounds=args.max_rounds,
            open_pages=args.open_pages,
            then_start=args.then_start,
        )
    if args.command == "iterate-now":
        return cmd_iterate_now()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
