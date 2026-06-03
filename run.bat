@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo [1/2] 获取 GitHub 高星新项目...
uv run python fetch_github_stars.py
echo [2/2] 运行 TrendRadar 推送...
uv run python -m trendradar %*
pause
