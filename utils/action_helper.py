"""
Chainlit Action ヘルパーモジュール
Action APIの正しい使用を保証するためのヘルパー関数
"""

from typing import Dict, Any, List, Optional
import chainlit as cl


class ActionHelper:
    """Chainlit Action APIのヘルパークラス"""
    
    # よく使うアクション定数
    CONFIRM_ACTIONS = {
        "YES": {"action": "yes"},
        "NO": {"action": "no"},
        "CANCEL": {"action": "cancel"}
    }
    
    CRUD_ACTIONS = {
        "CREATE": {"action": "create"},
        "READ": {"action": "read"},
        "UPDATE": {"action": "update"},
        "DELETE": {"action": "delete"}
    }
    
    @staticmethod
    def create_action(name: str, action_type: str, label: str, **kwargs) -> cl.Action:
        """
        安全なActionオブジェクトを作成
        
        Args:
            name: アクション名
            action_type: アクションタイプ
            label: 表示ラベル
            **kwargs: 追加のペイロードデータ
        
        Returns:
            cl.Action: Actionオブジェクト
        
        Example:
            action = ActionHelper.create_action("confirm", "yes", "はい")
        """
        payload = {"action": action_type}
        payload.update(kwargs)
        return cl.Action(name=name, payload=payload, label=label)
    
    @staticmethod
    def create_confirm_actions(
        yes_label: str = "はい",
        no_label: str = "いいえ",
        cancel_label: Optional[str] = None
    ) -> List[cl.Action]:
        """
        確認ダイアログ用のアクションを作成
        
        Args:
            yes_label: はいボタンのラベル
            no_label: いいえボタンのラベル
            cancel_label: キャンセルボタンのラベル（Noneの場合は作成しない）
        
        Returns:
            List[cl.Action]: アクションのリスト
        """
        actions = [
            cl.Action(name="yes", payload=ActionHelper.CONFIRM_ACTIONS["YES"], label=yes_label),
            cl.Action(name="no", payload=ActionHelper.CONFIRM_ACTIONS["NO"], label=no_label)
        ]
        
        if cancel_label:
            actions.append(
                cl.Action(name="cancel", payload=ActionHelper.CONFIRM_ACTIONS["CANCEL"], label=cancel_label)
            )
        
        return actions
    
    @staticmethod
    def create_menu_actions(options: Dict[str, str]) -> List[cl.Action]:
        """
        メニュー用のアクションを作成
        
        Args:
            options: {値: ラベル}の辞書
        
        Returns:
            List[cl.Action]: アクションのリスト
        
        Example:
            options = {
                "create": "新規作成",
                "edit": "編集",
                "delete": "削除"
            }
            actions = ActionHelper.create_menu_actions(options)
        """
        return [
            cl.Action(
                name=f"menu_{value}",
                payload={"action": value},
                label=label
            )
            for value, label in options.items()
        ]
    
    @staticmethod
    def get_action_value(response: Optional[Dict], key: str = "action", default: Any = None) -> Any:
        """
        レスポンスからアクション値を安全に取得
        
        Args:
            response: AskActionMessageのレスポンス
            key: 取得するキー
            default: デフォルト値
        
        Returns:
            アクション値またはデフォルト値
        """
        if not response:
            return default
        
        payload = response.get("payload", {})
        if not isinstance(payload, dict):
            return default
        
        return payload.get(key, default)
    
    @staticmethod
    async def ask_confirmation(
        message: str,
        yes_label: str = "はい",
        no_label: str = "いいえ",
        timeout: int = 60
    ) -> bool:
        """
        確認ダイアログを表示して結果を取得
        
        Args:
            message: 確認メッセージ
            yes_label: はいボタンのラベル
            no_label: いいえボタンのラベル
            timeout: タイムアウト秒数
        
        Returns:
            bool: はいが選択された場合True
        """
        res = await cl.AskActionMessage(
            content=message,
            actions=ActionHelper.create_confirm_actions(yes_label, no_label),
            timeout=timeout
        ).send()
        
        return ActionHelper.get_action_value(res) == "yes"
    
    @staticmethod
    async def ask_choice(
        message: str,
        options: Dict[str, str],
        timeout: int = 60
    ) -> Optional[str]:
        """
        選択メニューを表示して結果を取得
        
        Args:
            message: メッセージ
            options: {値: ラベル}の辞書
            timeout: タイムアウト秒数
        
        Returns:
            選択された値またはNone
        """
        res = await cl.AskActionMessage(
            content=message,
            actions=ActionHelper.create_menu_actions(options),
            timeout=timeout
        ).send()
        
        return ActionHelper.get_action_value(res)
    
    @staticmethod
    def validate_payload(payload: Any) -> bool:
        """
        ペイロードが正しい形式かチェック
        
        Args:
            payload: チェックするペイロード
        
        Returns:
            bool: 辞書型の場合True
        """
        return isinstance(payload, dict)


# グローバルインスタンス
action_helper = ActionHelper()


# 便利な関数をエクスポート
create_action = action_helper.create_action
create_confirm_actions = action_helper.create_confirm_actions
create_menu_actions = action_helper.create_menu_actions
get_action_value = action_helper.get_action_value
ask_confirmation = action_helper.ask_confirmation
ask_choice = action_helper.ask_choice
validate_payload = action_helper.validate_payload


# 使用例
"""
# 1. 確認ダイアログ
if await ask_confirmation("削除してもよろしいですか？"):
    # 削除処理
    pass

# 2. 選択メニュー
choice = await ask_choice(
    "アクションを選択してください",
    {
        "create": "新規作成",
        "edit": "編集",
        "delete": "削除"
    }
)
if choice == "create":
    # 作成処理
    pass

# 3. カスタムアクション
action = create_action("custom", "process", "処理", data="additional_data")
"""
