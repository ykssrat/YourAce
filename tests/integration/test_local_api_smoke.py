"""本地后端拉起与 analyze 接口烟雾测试。"""

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

import pytest

from scripts.utils.asset_loader import detect_asset_type, load_assets

PYTHON_CANDIDATES = [
    sys.executable,
    r"C:\Users\Public\.codegeex\mamba\envs\codegeex-agent\python.exe",
    r"D:\conda\python.exe",
    r"D:\git_project\venv\Scripts\python.exe",
]


def test_local_api_smoke() -> None:
    """自动启动本地后端并验证 analyze 最小闭环。"""
    if not _server_smoke_supported():
        pytest.skip("当前测试解释器缺少 FastAPI/uvicorn 依赖，跳过本地 API 冒烟测试")

    result = run_local_api_smoke(code="000001", include_news=False)

    assert result["code"] == "000001"
    assert result["label"] in {"BUY", "HOLD", "SELL"}
    assert set(result["horizon_signals"].keys()) == {"short", "mid", "long"}
    assert result.get("news_enabled") is False
    assert result.get("latest_news") == []


def test_screen_universe_contains_enough_etfs_and_funds() -> None:
    assets = load_assets(keyword="", limit=10000)
    etf_assets = [item for item in assets if detect_asset_type(item["code"], item["name"]) == "etf"]
    fund_assets = [item for item in assets if detect_asset_type(item["code"], item["name"]) == "fund"]

    assert len(etf_assets) >= 100
    assert len(fund_assets) >= 100
    assert any("ETF" in item["name"].upper() for item in etf_assets[:20])
    assert any("基金" in item["name"] or "混合" in item["name"] or "债" in item["name"] or "FOF" in item["name"].upper() for item in fund_assets[:20])


def run_local_api_smoke(code: str = "000001", include_news: bool = False) -> dict[str, Any]:
    """启动临时后端进程后请求 analyze，并返回响应体。"""
    project_root = Path(__file__).resolve().parents[2]
    port = int(os.getenv("YOURACE_API_TEST_PORT", "8010"))
    base_url = f"http://127.0.0.1:{port}"

    process = _start_server(project_root, port)
    try:
        _wait_for_health(f"{base_url}/health", timeout_seconds=30)
        payload = {
            "code": code,
            "long_fund_trend": 0,
            "include_news": include_news,
        }
        response = _post_json(f"{base_url}/analyze", payload)
        return response
    finally:
        _stop_server(process)


def _server_smoke_supported() -> bool:
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except Exception:
        return False
    return True


def _start_server(project_root: Path, port: int) -> subprocess.Popen[str]:
    """以子进程方式启动 uvicorn 服务。"""
    last_error: Exception | None = None
    for python_executable in _iter_python_candidates():
        try:
            process = subprocess.Popen(
                [
                    python_executable,
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
            time.sleep(1)
            if process.poll() is None:
                return process

            output = _read_process_output(process)
            last_error = RuntimeError(f"uvicorn failed with {python_executable}: {output}")
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"无法启动测试服务: {last_error}")


def _iter_python_candidates() -> list[str]:
    unique_candidates: list[str] = []
    for candidate in PYTHON_CANDIDATES:
        if candidate and Path(candidate).exists() and candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


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


def _read_process_output(process: subprocess.Popen[str]) -> str:
    if process.stdout is None:
        return ""
    try:
        return process.stdout.read()
    except Exception:
        return ""


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="本地后端评分链路烟雾测试")
    parser.add_argument("--code", default="000001", help="股票/ETF/基金代码，例如 000001")
    parser.add_argument("--include-news", action="store_true", help="是否开启新闻抓取")
    parser.add_argument("--port", type=int, default=None, help="测试端口，默认读取 YOURACE_API_TEST_PORT 或 8010")
    return parser.parse_args()


def _print_result(result: dict[str, Any], port: int, include_news: bool) -> None:
    """打印可读的输入输出摘要。"""
    print("[YourAce] 本地看法矩阵链路验证完成")
    print(f"- 接口地址: http://127.0.0.1:{port}/analyze")
    print(f"- 代码: {result.get('code')}")
    print(f"- 新闻开关: {'开启' if include_news else '关闭'}")
    print(f"- 标签: {result.get('label')}")
    horizon = result.get("horizon_signals", {})
    print(
        "- 三维信号: "
        f"short={horizon.get('short')}, "
        f"mid={horizon.get('mid')}, "
        f"long={horizon.get('long')}"
    )
    selected_features = result.get("selected_features", [])
    print(f"- 选中特征数: {len(selected_features)}")
    print(f"- 选中特征: {selected_features}")
    latest_news = result.get("latest_news", [])
    print(f"- 新闻条数: {len(latest_news)}")
    print("\n原始响应 JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = _parse_args()
    if args.port is not None:
        os.environ["YOURACE_API_TEST_PORT"] = str(args.port)
    current_port = int(os.getenv("YOURACE_API_TEST_PORT", "8010"))
    output = run_local_api_smoke(code=args.code, include_news=args.include_news)
    _print_result(output, port=current_port, include_news=args.include_news)
