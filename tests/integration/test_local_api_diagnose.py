"""本地后端拉起与 diagnose 接口诊股测试。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

# 看法取值映射（用于中文展示）
_OPINION_LABEL = {
    "STRONG_BUY": "强烈看多 ▲▲",
    "BUY":         "看多      ▲",
    "HOLD":        "中性      —",
    "SELL":        "看空      ▼",
    "STRONG_SELL": "强烈看空 ▼▼",
}


def test_local_api_diagnose() -> None:
    """自动启动本地后端并验证 diagnose 最小闭环。"""
    result = run_local_api_diagnose(code="000001", include_news=False)

    assert result["code"] == "000001"
    assert isinstance(result["score"], (int, float))
    assert result["label"] in {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}
    assert set(result["horizon_signals"].keys()) == {"short", "mid", "long"}
    assert set(result["matrix"].keys()) == {"short", "mid", "long"}
    valid_opinions = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}
    for v in result["matrix"].values():
        assert v in valid_opinions
    assert result.get("news_enabled") is False


def run_local_api_diagnose(code: str = "000001", include_news: bool = False) -> dict[str, Any]:
    """启动临时后端进程后请求 diagnose，并返回响应体。"""
    project_root = Path(__file__).resolve().parents[2]
    port = int(os.getenv("YOURACE_API_TEST_PORT", "8010"))
    base_url = f"http://127.0.0.1:{port}"

    process = _start_server(project_root, port)
    try:
        _wait_for_health(f"{base_url}/health", timeout_seconds=30)
        payload = {"code": code, "include_news": include_news}
        response = _post_json(f"{base_url}/diagnose", payload)
        return response
    finally:
        _stop_server(process)


def _start_server(project_root: Path, port: int) -> subprocess.Popen[str]:
    """以子进程方式启动 uvicorn 服务。"""
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
    )


def _wait_for_health(health_url: str, timeout_seconds: int) -> None:
    """轮询健康检查接口，直到服务可用。"""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = _get_json(health_url)
            if response.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"后端启动超时，未就绪: {health_url}")


def _get_json(url: str) -> dict[str, Any]:
    """发送 GET 并解析 JSON。"""
    request = Request(url=url, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except URLError as exc:
        raise RuntimeError(f"请求失败: {url}, error={exc}") from exc


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """发送 POST JSON 并解析 JSON。"""
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url=url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except URLError as exc:
        raise RuntimeError(f"请求失败: {url}, error={exc}") from exc


def _stop_server(process: subprocess.Popen[str]) -> None:
    """停止后端子进程并尽量清理输出。"""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=8)


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="本地后端诊股接口验证")
    parser.add_argument("--code", default="000001", help="股票/ETF/基金代码，例如 600519")
    parser.add_argument("--include-news", action="store_true", help="是否开启新闻抓取")
    parser.add_argument("--port", type=int, default=None, help="测试端口，默认读取 YOURACE_API_TEST_PORT 或 8010")
    return parser.parse_args()


def _print_result(result: dict[str, Any], port: int, include_news: bool) -> None:
    """打印可读的诊股结果摘要。"""
    print("[YourAce] 诊股结果")
    print(f"  接口地址: http://127.0.0.1:{port}/diagnose")
    print(f"  代码:     {result.get('code')}")
    print(f"  日期:     {result.get('as_of_date')}")
    print(f"  综合评分: {result.get('score')}")
    print(f"  综合标签: {result.get('label')}")

    horizon = result.get("horizon_signals", {})
    print("\n  三维信号:")
    for dim in ("short", "mid", "long"):
        sig = horizon.get(dim, {})
        print(f"    {dim:5s}: direction={sig.get('direction')}  strength={sig.get('strength')}")

    matrix = result.get("matrix", {})
    dim_names = {"short": "短线", "mid": "中线", "long": "长线"}
    print("\n  看法矩阵:")
    for dim in ("short", "mid", "long"):
        opinion = matrix.get(dim, "—")
        label = _OPINION_LABEL.get(opinion, opinion)
        print(f"    {dim_names[dim]}({dim:5s}): {label}")

    selected_features = result.get("selected_features", [])
    print(f"\n  选中特征({len(selected_features)}): {selected_features}")

    if include_news:
        latest_news = result.get("latest_news", [])
        print(f"\n  最新资讯({len(latest_news)} 条):")
        for item in latest_news:
            print(f"    - {item}")

    print("\n原始响应 JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = _parse_args()
    if args.port is not None:
        os.environ["YOURACE_API_TEST_PORT"] = str(args.port)
    current_port = int(os.getenv("YOURACE_API_TEST_PORT", "8010"))
    output = run_local_api_diagnose(code=args.code, include_news=args.include_news)
    _print_result(output, port=current_port, include_news=args.include_news)
