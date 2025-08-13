@echo off
echo ========================================
echo Responses API + Tools機能のテスト
echo ========================================

echo.
echo Python環境をアクティベート中...
call .venv\Scripts\activate

echo.
echo テストを実行中...
python test_responses_api.py

echo.
echo ========================================
echo テスト完了
echo ========================================
echo.
echo Responses API版に切り替える場合:
echo   switch_to_responses_api.bat を実行
echo.
echo アプリケーションを起動する場合:
echo   start.bat を実行
echo.
pause
