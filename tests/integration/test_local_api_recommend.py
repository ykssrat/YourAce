"""本地后端反向参数筛股脚本。"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.request import Request, urlopen

# 允许从 tests/integration 直接执行时导入仓库内模块。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.utils.asset_loader import load_assets

ANALYZE_REQUEST_TIMEOUT_SECONDS = 8
ANALYZE_RETRY_COUNT = 1
DEFAULT_CACHE_FILE = "configs/recommend_score_cache.json"
DEFAULT_CACHE_MAX_AGE_DAYS = 3
DEFAULT_STALE_REFRESH_BUDGET = 20


def run_recommend_scan(
    signal_filter: Dict[str, str],
    min_score: float = 80.0,
    universe_limit: int = 500,
    top_n: int = 20,
    include_news: bool = False,
    auto_bootstrap_stock_list: bool = True,
    round_size: int = 20,
    max_rounds: int = 2,
    cache_file: str = DEFAULT_CACHE_FILE,
    refresh_cache: bool = False,
    cache_max_age_days: int = DEFAULT_CACHE_MAX_AGE_DAYS,
    stale_refresh_budget: int = DEFAULT_STALE_REFRESH_BUDGET,
) -> List[Dict[str, Any]]:
    """按反向条件扫描候选资产并返回推荐列表。"""
    preferred_port = int(os.getenv("YOURACE_API_TEST_PORT", "8010"))
    port = _pick_available_port(preferred_port)
    if port != preferred_port:
        print(f"[YourAce] 端口 {preferred_port} 已被占用，自动切换到 {port}")

    base_url = f"http://127.0.0.1:{port}"
    project_root = PROJECT_ROOT
    cache_path = project_root / cache_file
    score_cache = _load_score_cache(cache_path)
    cache_hit = 0
    cache_miss = 0
    stale_refresh_used = 0
    score_pass_total = 0
    signal_miss_total = 0

    assets = load_assets(keyword="", limit=universe_limit)
    if auto_bootstrap_stock_list and _stock_list_missing(project_root):
        print("[YourAce] 未发现 stock_list 缓存，正在尝试自动构建...")
        _bootstrap_stock_list(project_root)
        assets = load_assets(keyword="", limit=universe_limit)

    print(f"[YourAce] 候选资产数量: {len(assets)}")
    if not assets:
        raise RuntimeError("未加载到可扫描资产，请先准备 stock_list 缓存")

    process = _start_server(project_root=project_root, port=port)
    try:
        _wait_for_health(
            health_url=f"{base_url}/health",
            timeout_seconds=30,
            process=process,
        )

        effective_round_size = max(1, round_size)
        effective_rounds = max(1, max_rounds)
        scan_pool = assets[: max(universe_limit, effective_round_size)]
        scanned_codes: set[str] = set()
        update_failed = False
        update_done = False
        all_matches: List[Dict[str, Any]] = []
        matched_codes: set[str] = set()

        for round_index in range(1, effective_rounds + 1):
            round_assets = _pick_unseen_assets(
                assets=scan_pool,
                seen_codes=scanned_codes,
                pick_size=effective_round_size,
            )
            if not round_assets:
                break

            print(f"[YourAce] 第{round_index}轮开始，试验股票数: {len(round_assets)}")
            round_matches = _scan_assets(
                assets=round_assets,
                base_url=base_url,
                signal_filter=signal_filter,
                min_score=min_score,
                include_news=include_news,
                score_cache=score_cache,
                refresh_cache=refresh_cache,
                cache_max_age_days=cache_max_age_days,
                stale_refresh_budget=stale_refresh_budget,
                stale_refresh_used=stale_refresh_used,
            )
            scanned_codes.update(_collect_codes(round_assets))
            cache_hit += round_matches["cache_hit"]
            cache_miss += round_matches["cache_miss"]
            stale_refresh_used = round_matches["stale_refresh_used"]
            score_pass_total += round_matches["score_pass_count"]
            signal_miss_total += round_matches["signal_miss_count"]
            _save_score_cache(cache_path, score_cache)

            if round_matches["matches"]:
                for item in round_matches["matches"]:
                    code = str(item.get("code", "")).strip()
                    if not code or code in matched_codes:
                        continue
                    matched_codes.add(code)
                    all_matches.append(item)

                if len(all_matches) >= top_n:
                    all_matches.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
                    print(f"[YourAce] 缓存命中: {cache_hit}, 新算代码: {cache_miss}, 过期刷新: {stale_refresh_used}")
                    print(f"[YourAce] 诊断: 评分达标={score_pass_total}, 信号不匹配={signal_miss_total}")
                    return all_matches[:top_n]

            if round_index < effective_rounds:
                print("命中数量: 0")
                if auto_bootstrap_stock_list:
                    if update_done:
                        print(f"无命中，stock_list 已更新过，继续下一轮（当前已尝试第{round_index}轮）")
                    else:
                        print(f"无命中，正在尝试更新stock_list（当前已尝试第{round_index}轮）")

                    if update_failed:
                        print("[YourAce] 已检测到更新源异常，跳过后续 stock_list 更新重试")
                    elif not update_done:
                        update_ok = _bootstrap_stock_list(project_root)
                        update_failed = not update_ok
                        update_done = update_ok
                else:
                    print(f"无命中，已跳过stock_list更新（当前已尝试第{round_index}轮）")
                expanded_limit = max(universe_limit + effective_round_size * effective_rounds, universe_limit * 2)
                scan_pool = load_assets(keyword="", limit=expanded_limit)

        print(f"[YourAce] 缓存命中: {cache_hit}, 新算代码: {cache_miss}, 过期刷新: {stale_refresh_used}")
        print(f"[YourAce] 诊断: 评分达标={score_pass_total}, 信号不匹配={signal_miss_total}")
        all_matches.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return all_matches[:top_n]
    finally:
        _save_score_cache(cache_path, score_cache)
        _stop_server(process)


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="反向参数筛股：按信号和最小分数扫描候选资产")
    parser.add_argument(
        "--signals",
        nargs="+",
        required=True,
        help="信号条件，例如: --signals short STRONG BUY 或 --signals mid SELL",
    )
    parser.add_argument("--min-score", type=float, default=80.0, help="最小分数阈值，默认 80")
    parser.add_argument("--universe-limit", type=int, default=500, help="扫描资产上限，默认 500")
    parser.add_argument("--top-n", type=int, default=20, help="返回结果数量上限，默认 20")
    parser.add_argument("--round-size", type=int, default=20, help="每轮试验股票数，默认 20")
    parser.add_argument("--max-rounds", type=int, default=2, help="最大轮次数，默认 2")
    parser.add_argument("--include-news", action="store_true", help="分析时是否开启新闻")
    parser.add_argument("--skip-stock-list-update", action="store_true", help="跳过自动更新 stock_list")
    parser.add_argument("--cache-file", default=DEFAULT_CACHE_FILE, help="评分缓存文件，默认 configs/recommend_score_cache.json")
    parser.add_argument("--refresh-cache", action="store_true", help="忽略缓存并重新计算评分")
    parser.add_argument("--cache-max-age-days", type=int, default=DEFAULT_CACHE_MAX_AGE_DAYS, help="缓存保鲜天数，默认 3")
    parser.add_argument("--stale-refresh-budget", type=int, default=DEFAULT_STALE_REFRESH_BUDGET, help="每次运行最多刷新多少个过期缓存，默认 20")
    parser.add_argument("--port", type=int, default=None, help="后端测试端口，默认 8010")
    return parser.parse_args()


def _build_signal_filter(tokens: List[str]) -> Dict[str, str]:
    """将命令行 token 转换为信号过滤条件。"""
    if len(tokens) == 1 and tokens[0].strip().upper() in {"ANY", "ALL", "NONE"}:
        return {}

    if len(tokens) < 2:
        raise ValueError("--signals 至少需要 2 个参数，例如: --signals short BUY；或使用 --signals ANY")

    horizon = tokens[0].strip().lower()
    if horizon not in {"short", "mid", "long"}:
        raise ValueError("horizon 必须是 short/mid/long")

    signal_phrase = " ".join(tokens[1:]).strip()
    signal = _normalize_signal(signal_phrase)
    return {horizon: signal}


def _normalize_signal(value: str) -> str:
    """归一化信号文本。"""
    normalized = value.strip().upper().replace("_", " ")
    compact = normalized.replace(" ", "")

    mapping = {
        "BUY": "BUY",
        "STRONGBUY": "BUY",
        "HOLD": "HOLD",
        "SELL": "SELL",
        "STRONGSELL": "SELL",
    }
    signal = mapping.get(compact)
    if signal is None:
        raise ValueError("信号仅支持 BUY/HOLD/SELL/STRONG BUY/STRONG SELL")
    return signal


def _match_signal_filter(horizon_signals: Dict[str, str], signal_filter: Dict[str, str]) -> bool:
    """判断单个标的是否满足信号过滤条件。"""
    if not signal_filter:
        return True

    for horizon, expected in signal_filter.items():
        actual = str(horizon_signals.get(horizon, "")).upper()
        if actual != expected:
            return False
    return True


def _start_server(project_root: Path, port: int) -> subprocess.Popen[str]:
    """启动 uvicorn 服务。"""
    env = os.environ.copy()
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing_path}" if existing_path else str(project_root)

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "scripts.api.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )


def _wait_for_health(health_url: str, timeout_seconds: int, process: subprocess.Popen[str]) -> None:
    """等待后端健康检查通过。"""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            output = _read_process_output(process)
            raise RuntimeError(f"后端进程已退出，无法启动服务。日志: {output}")

        try:
            body = _get_json(health_url)
            if body.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.4)

    output = _read_process_output(process)
    raise RuntimeError(f"后端启动超时: {health_url}。日志: {output}")


def _get_json(url: str) -> Dict[str, Any]:
    """发送 GET 并解析 JSON。"""
    request = Request(url=url, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"请求失败: {url}, error={exc}") from exc


def _post_json(
    url: str,
    payload: Dict[str, Any],
    timeout_seconds: int = ANALYZE_REQUEST_TIMEOUT_SECONDS,
    retry_count: int = ANALYZE_RETRY_COUNT,
) -> Dict[str, Any]:
    """发送 POST JSON 并解析响应。"""
    last_error: Exception | None = None
    for _ in range(retry_count + 1):
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    raise RuntimeError(f"请求失败: {url}, error={last_error}")


def _stop_server(process: subprocess.Popen[str]) -> None:
    """停止后端进程。"""
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=8)


def _print_results(matches: List[Dict[str, Any]], signal_filter: Dict[str, str], min_score: float) -> None:
    """打印筛选结果。"""
    if signal_filter:
        key = next(iter(signal_filter.keys()))
        value = signal_filter[key]
        condition_text = f"{key}={value}, score>={min_score}"
    else:
        condition_text = f"仅按分数筛选, score>={min_score}"

    print("[YourAce] 反向参数筛股完成")
    print(f"- 过滤条件: {condition_text}")
    print(f"- 命中数量: {len(matches)}")

    if not matches:
        print("- 无命中，请放宽条件或准备更完整的 stock_list 缓存")
        return

    print("\n推荐结果:")
    for item in matches:
        horizon = item.get("horizon_signals", {})
        print(
            f"{item.get('code')}  score={item.get('score')}  label={item.get('label')}  "
            f"short={horizon.get('short')} mid={horizon.get('mid')} long={horizon.get('long')}"
        )


def _scan_assets(
    assets: List[Dict[str, Any]],
    base_url: str,
    signal_filter: Dict[str, str],
    min_score: float,
    include_news: bool,
    score_cache: Dict[str, Dict[str, Any]],
    refresh_cache: bool,
    cache_max_age_days: int,
    stale_refresh_budget: int,
    stale_refresh_used: int,
) -> Dict[str, Any]:
    """扫描资产列表并返回命中结果。"""
    matches: List[Dict[str, Any]] = []
    cache_hit = 0
    cache_miss = 0
    score_pass_count = 0
    signal_miss_count = 0
    progress_step = 5 if len(assets) <= 50 else 20
    for index, asset in enumerate(assets, start=1):
        if index % progress_step == 0 or index == len(assets):
            print(f"[YourAce] 扫描进度: {index}/{len(assets)}")

        code = str(asset.get("code", "")).strip()
        if not code:
            continue

        payload = {
            "code": code,
            "long_fund_trend": 0,
            "include_news": include_news,
        }

        cache_item = score_cache.get(code)
        can_use_cache = (not refresh_cache) and _is_valid_cache_item(cache_item)
        cache_fresh = _is_cache_fresh(cache_item, max_age_days=cache_max_age_days)

        if can_use_cache and (cache_fresh or stale_refresh_used >= stale_refresh_budget):
            cached = score_cache[code]
            result = {
                "code": code,
                "score": cached["score"],
                "label": cached["label"],
                "horizon_signals": cached["horizon_signals"],
            }
            cache_hit += 1
        else:
            try:
                result = _post_json(
                    f"{base_url}/analyze",
                    payload,
                    timeout_seconds=ANALYZE_REQUEST_TIMEOUT_SECONDS,
                    retry_count=ANALYZE_RETRY_COUNT,
                )
            except Exception:
                if can_use_cache:
                    cached = score_cache[code]
                    result = {
                        "code": code,
                        "score": cached["score"],
                        "label": cached["label"],
                        "horizon_signals": cached["horizon_signals"],
                    }
                    cache_hit += 1
                else:
                    continue

            else:
                score_cache[code] = {
                    "score": result.get("score"),
                    "label": result.get("label"),
                    "horizon_signals": result.get("horizon_signals", {}),
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                cache_miss += 1
                if can_use_cache and (not cache_fresh):
                    stale_refresh_used += 1

        if "score" not in result:
                continue

        if float(result.get("score", 0.0)) < min_score:
            continue
        score_pass_count += 1

        if not _match_signal_filter(result.get("horizon_signals", {}), signal_filter):
            signal_miss_count += 1
            continue

        matches.append(
            {
                "code": code,
                "name": asset.get("name", ""),
                "score": result.get("score"),
                "label": result.get("label"),
                "horizon_signals": result.get("horizon_signals", {}),
            }
        )

    return {
        "matches": matches,
        "cache_hit": cache_hit,
        "cache_miss": cache_miss,
        "stale_refresh_used": stale_refresh_used,
        "score_pass_count": score_pass_count,
        "signal_miss_count": signal_miss_count,
    }


def _collect_codes(assets: List[Dict[str, Any]]) -> set[str]:
    """提取资产代码集合。"""
    result: set[str] = set()
    for item in assets:
        code = str(item.get("code", "")).strip()
        if code:
            result.add(code)
    return result


def _pick_unseen_assets(assets: List[Dict[str, Any]], seen_codes: set[str], pick_size: int) -> List[Dict[str, Any]]:
    """从候选池中挑选未扫描股票。"""
    result: List[Dict[str, Any]] = []
    for item in assets:
        code = str(item.get("code", "")).strip()
        if not code or code in seen_codes:
            continue
        result.append(item)
        if len(result) >= pick_size:
            break
    return result


def _stock_list_missing(project_root: Path) -> bool:
    """判断本地股票池缓存是否存在。"""
    raw_dir = project_root / "datas" / "raw"
    return not ((raw_dir / "stock_list.parquet").exists() or (raw_dir / "stock_list.csv").exists())


def _bootstrap_stock_list(project_root: Path) -> bool:
    """尝试生成 stock_list 缓存。"""
    command = [
        sys.executable,
        "scripts/processed/build_stock_list.py",
    ]
    result = subprocess.run(command, cwd=str(project_root), check=False, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        stderr_lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
        summary = stderr_lines[-1] if stderr_lines else "未知错误"
        print(f"[YourAce] 自动构建 stock_list 失败，继续使用现有候选池: {summary}")
        return False
    return True


def _load_score_cache(cache_path: Path) -> Dict[str, Dict[str, Any]]:
    """读取本地评分缓存。"""
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        for code, item in data.items():
            if isinstance(code, str) and isinstance(item, dict):
                result[code] = item
        return result
    except Exception:
        return {}


def _save_score_cache(cache_path: Path, score_cache: Dict[str, Dict[str, Any]]) -> None:
    """保存本地评分缓存。"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(score_cache, f, ensure_ascii=False, indent=2)


def _is_valid_cache_item(item: Any) -> bool:
    """判断缓存记录是否可用于筛选。"""
    if not isinstance(item, dict):
        return False
    if "score" not in item or "label" not in item or "horizon_signals" not in item:
        return False
    return isinstance(item.get("horizon_signals"), dict)


def _is_cache_fresh(item: Any, max_age_days: int) -> bool:
    """判断缓存是否在保鲜期内。"""
    if not _is_valid_cache_item(item):
        return False
    if max_age_days < 0:
        return False
    if max_age_days == 0:
        return True

    updated_at = str(item.get("updated_at", "")).strip()
    if not updated_at:
        return False
    try:
        timestamp = datetime.fromisoformat(updated_at)
    except ValueError:
        return False

    age = datetime.now() - timestamp
    return age.days <= max_age_days


def _pick_available_port(preferred_port: int) -> int:
    """优先使用指定端口，冲突时自动寻找可用端口。"""
    if _is_port_available(preferred_port):
        return preferred_port

    for candidate in range(preferred_port + 1, preferred_port + 101):
        if _is_port_available(candidate):
            return candidate
    return preferred_port


def _is_port_available(port: int) -> bool:
    """检测本机端口是否可绑定。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _read_process_output(process: subprocess.Popen[str]) -> str:
    """读取后端子进程输出，避免报错上下文缺失。"""
    if process.stdout is None:
        return "<no stdout>"
    try:
        content = process.stdout.read() or ""
    except Exception:  # noqa: BLE001
        return "<read stdout failed>"

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return "<empty output>"
    tail = lines[-10:]
    return " | ".join(tail)


if __name__ == "__main__":
    args = _parse_args()
    if args.port is not None:
        os.environ["YOURACE_API_TEST_PORT"] = str(args.port)

    filter_config = _build_signal_filter(args.signals)
    results = run_recommend_scan(
        signal_filter=filter_config,
        min_score=args.min_score,
        universe_limit=args.universe_limit,
        top_n=args.top_n,
        include_news=args.include_news,
        auto_bootstrap_stock_list=not args.skip_stock_list_update,
        round_size=args.round_size,
        max_rounds=args.max_rounds,
        cache_file=args.cache_file,
        refresh_cache=args.refresh_cache,
        cache_max_age_days=args.cache_max_age_days,
        stale_refresh_budget=args.stale_refresh_budget,
    )
    _print_results(results, signal_filter=filter_config, min_score=args.min_score)
