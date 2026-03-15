# YourAce 云服务器更新操作手册

- 电脑的终端执行的命令：主要是 scp、ssh（把文件传上去，以及远程下发命令）
- 需要在服务器 Ubuntu 终端执行的命令：主要是重启后端、查看日志、验证接口

二选一：

- 方式 A：全在你电脑 PowerShell 执行（推荐，省事）
- 方式 B：先 ssh 登陆后，在 Ubuntu 里逐条执行

## 二、前置条件

请先确认：

- 你的电脑能 ssh 到云服务器
- 云服务器上项目目录存在（示例用 ~/YourAce）
- 云服务器上的后端是监听 8000，并由 Nginx 反代 80

## 三、方式 A（推荐）：在你电脑 PowerShell 全部执行

### 1) 设置变量（本机执行）

    $SERVER="ubuntu@43.138.223.57"
    $REMOTE_DIR="~/YourAce"
    $KEY="D:\QMT\secret_key\yourace_secret_key.pem"

通用一键执行（推荐，支持你每次传任意文件，不固定 server.py）：

先复制下面这段函数到 PowerShell（只需执行一次）：

        function Sync-YourAce {
            param(
                [Parameter(Mandatory = $true)][string[]]$Files,
                [string]$Server = "ubuntu@43.138.223.57",
                [string]$RemoteDir = "~/YourAce",
                [string]$Key = "D:\QMT\secret_key\yourace_secret_key.pem"
            )

            foreach ($f in $Files) {
                if (-not (Test-Path $f)) { throw "本地文件不存在: $f" }
                $remote = "$Server`:$RemoteDir/$($f -replace '\\','/')"
                scp -i "$Key" -o IdentitiesOnly=yes "$f" "$remote"
            }

            # 自动杀死旧进程并用 nohup 重启
            ssh -i "$Key" -o IdentitiesOnly=yes $Server "
                set -e
                pkill -f 'uvicorn scripts.api.server:app' || true
                mkdir -p $RemoteDir/logs
                cd $RemoteDir
                nohup .venv/bin/python -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
                sleep 3
                curl -s http://127.0.0.1:8000/health
            "
        }

然后每次只用这一条（把你改过的文件路径放进去）：

        Sync-YourAce -Files @("scripts/api/server.py","scripts/strategy/scoring.py")

### 2) 如果不使用一键脚本，手动操作步骤（本机执行）

**上传文件：**
    scp -i "$KEY" -o IdentitiesOnly=yes scripts/api/server.py "${SERVER}:$REMOTE_DIR/scripts/api/server.py"

**重启服务（nohup 方式）：**
    ssh -i "$KEY" -o IdentitiesOnly=yes $SERVER "pkill -f 'uvicorn scripts.api.server:app'"
    ssh -i "$KEY" -o IdentitiesOnly=yes $SERVER "mkdir -p $REMOTE_DIR/logs; cd $REMOTE_DIR; nohup .venv/bin/python -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &"

### 3) 健康检查与功能检查（本机执行）

    ssh -i "$KEY" -o IdentitiesOnly=yes $SERVER "curl -s http://127.0.0.1:8000/health"
    ssh -i "$KEY" -o IdentitiesOnly=yes $SERVER "curl -s -X POST http://127.0.0.1:8000/analyze -H 'Content-Type: application/json' -d '{\"code\":\"161725\",\"include_news\":false}'"
    ssh -i "$KEY" -o IdentitiesOnly=yes $SERVER "curl -s -X POST http://127.0.0.1:8000/screen -H 'Content-Type: application/json' -d '{\"asset_type\":\"fund\",\"horizon\":\"\",\"score_operator\":\"gte\",\"score_threshold\":0,\"opinion\":\"\",\"round_size\":20,\"offset\":0}'"

你应该重点看：
- /analyze 响应是否有 horizon_strengths
- /screen fund 是否返回 items 非空

## 四、方式 B：先进入 Ubuntu 再执行

### 1) 进入服务器（本机执行）

    ssh ubuntu@43.138.223.57

### 2) 在服务器里重启后端（服务器执行）

清理旧进程并用 nohup 重新启动：

    # 杀掉旧进程（如果有）
    pkill -f "uvicorn scripts.api.server:app"
    
    # 进入项目目录并确保 logs 文件夹存在
    cd ~/YourAce
    mkdir -p logs

    # 后台启动服务
    nohup .venv/bin/python -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &

### 3) 在服务器里验证（服务器执行）

    curl -s http://127.0.0.1:8000/health

## 五、常见问题

1. 我改了代码但 App 没变化
- 原因：没重启云端后端进程，或者上传到了错误目录
- 处理：先看 `cat logs/api.log` 是否报错，再看 /analyze 是否出现新字段。

2. scp 提示路径不存在
- 原因：REMOTE_DIR 写错
- 处理：先 ssh 上去执行 pwd 和 ls，确认项目根目录

3. /health 正常但 /screen fund 仍为空
- 原因：云端还没拿到新的 asset_loader.py 或 server.py
- 处理：重新上传这两个文件并按上述流程重启

## 六、推荐日常流程（最省心）

每次后端改动后固定执行 4 步（方式 B）：

1. 本地 scp 上传改动文件
2. 服务器上 `pkill -f "uvicorn" && cd ~/YourAce && nohup .venv/bin/python -m uvicorn scripts.api.server:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &`
3. 服务器上 `curl http://127.0.0.1:8000/health`
4. 本地请求 `/analyze` 与 `/screen fund` 做冒烟验证
