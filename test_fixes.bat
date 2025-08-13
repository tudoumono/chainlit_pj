@echo off
echo ========================================
echo エラー修正のテスト
echo ========================================

echo.
echo Python環境をアクティベート中...
call .venv\Scripts\activate

echo.
echo テストを実行中...
python test_fixes.py

echo.
echo ========================================
echo テスト完了
echo ========================================
echo.
echo アプリケーションを起動する場合は start.bat を実行してください
echo.
pause
