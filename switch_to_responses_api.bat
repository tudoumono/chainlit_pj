@echo off
echo ========================================
echo OpenAI Responses API + Tools機能への切り替え
echo ========================================

echo.
echo 1. 既存のapp.pyをバックアップ中...
if exist app.py (
    copy /Y app.py app_old_completions.py > nul
    echo    ✅ app.py → app_old_completions.py にバックアップしました
)

echo.
echo 2. Responses API版に切り替え中...
copy /Y app_responses_api.py app.py > nul
echo    ✅ app_responses_api.py → app.py にコピーしました

echo.
echo 3. Tools設定ファイルを作成中...
if not exist .chainlit\tools_config.json (
    mkdir .chainlit 2>nul
    echo    ✅ Tools設定ファイルが自動作成されます
)

echo.
echo ========================================
echo 切り替え完了！
echo ========================================
echo.
echo 【新機能】
echo - OpenAI Responses APIを使用
echo - Web検索機能（/tools enable web_search）
echo - ファイル検索機能（/tools enable file_search）
echo - Tools機能の有効/無効を設定可能
echo.
echo アプリケーションを起動するには start.bat を実行してください
echo.
pause
