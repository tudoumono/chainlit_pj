"""
ペルソナ管理モジュール
Phase 6: システムプロンプト、モデル選択、ペルソナ機能
"""

import json
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import chainlit.data as cl_data

class PersonaManager:
    """ペルソナ管理クラス"""
    
    # 利用可能なモデルのリスト
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-4o-mini-2024-07-18",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-0125-preview",
        "gpt-4-1106-preview",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106"
    ]
    
    # デフォルトペルソナのテンプレート
    DEFAULT_PERSONAS = [
        {
            "name": "汎用アシスタント",
            "system_prompt": "あなたは親切で知識豊富なAIアシスタントです。ユーザーの質問に正確かつ分かりやすく回答してください。",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": None,
            "description": "一般的な質問に対応する標準的なアシスタント",
            "tags": ["general", "default"]
        },
        {
            "name": "プログラミング専門家",
            "system_prompt": "あなたは経験豊富なプログラマーです。コードの説明、バグ修正、最適化、新しい実装方法の提案などを行います。コード例を含めて具体的に説明してください。",
            "model": "gpt-4o",
            "temperature": 0.3,
            "max_tokens": None,
            "description": "プログラミングとコーディングに特化したアシスタント",
            "tags": ["programming", "code", "technical"]
        },
        {
            "name": "ビジネスアナリスト",
            "system_prompt": "あなたはビジネス戦略と分析の専門家です。市場分析、競合分析、ビジネスプランの作成、KPIの設定などについて専門的なアドバイスを提供します。",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": None,
            "description": "ビジネス分析と戦略立案に特化",
            "tags": ["business", "analysis", "strategy"]
        },
        {
            "name": "クリエイティブライター",
            "system_prompt": "あなたは創造的な文章を書くプロフェッショナルです。ストーリー、詩、マーケティングコピー、ブログ記事など、様々な形式の文章を魅力的に作成します。",
            "model": "gpt-4o",
            "temperature": 0.9,
            "max_tokens": None,
            "description": "創造的な文章作成に特化",
            "tags": ["creative", "writing", "content"]
        },
        {
            "name": "学習サポーター",
            "system_prompt": "あなたは優秀な教育者です。複雑な概念を分かりやすく説明し、段階的に学習を進められるようサポートします。具体例や図解を使って理解を深めます。",
            "model": "gpt-4o-mini",
            "temperature": 0.6,
            "max_tokens": None,
            "description": "学習と教育に特化したアシスタント",
            "tags": ["education", "learning", "teaching"]
        }
    ]
    
    def __init__(self):
        """初期化"""
        self.data_layer = None
        self._init_data_layer()
    
    def _init_data_layer(self):
        """データレイヤーを初期化"""
        if hasattr(cl_data, '_data_layer') and cl_data._data_layer:
            self.data_layer = cl_data._data_layer
    
    async def get_all_personas(self) -> List[Dict]:
        """すべてのペルソナを取得"""
        if self.data_layer and hasattr(self.data_layer, 'get_personas'):
            personas = await self.data_layer.get_personas()
            if personas:
                return personas
        
        # データレイヤーが利用できない場合はデフォルトペルソナを返す
        return self.DEFAULT_PERSONAS
    
    async def get_persona(self, persona_id: str) -> Optional[Dict]:
        """特定のペルソナを取得"""
        if self.data_layer and hasattr(self.data_layer, 'get_persona'):
            return await self.data_layer.get_persona(persona_id)
        
        # デフォルトペルソナから検索
        for persona in self.DEFAULT_PERSONAS:
            if persona.get("name") == persona_id:
                return persona
        return None
    
    async def get_active_persona(self) -> Optional[Dict]:
        """アクティブなペルソナを取得"""
        if self.data_layer and hasattr(self.data_layer, 'get_personas'):
            personas = await self.data_layer.get_personas()
            for persona in personas:
                if persona.get("is_active"):
                    return persona
        
        # デフォルトは最初のペルソナ
        return self.DEFAULT_PERSONAS[0]
    
    async def create_persona(self, persona_data: Dict) -> str:
        """新しいペルソナを作成"""
        if self.data_layer and hasattr(self.data_layer, 'create_persona'):
            # IDがない場合は生成
            if "id" not in persona_data:
                persona_data["id"] = str(uuid.uuid4())
            
            # デフォルト値を設定
            persona_data.setdefault("temperature", 0.7)
            persona_data.setdefault("model", "gpt-4o-mini")
            persona_data.setdefault("tags", [])
            persona_data.setdefault("is_active", False)
            
            return await self.data_layer.create_persona(persona_data)
        
        # データレイヤーが利用できない場合
        return str(uuid.uuid4())
    
    async def update_persona(self, persona_id: str, updates: Dict) -> bool:
        """ペルソナを更新"""
        if self.data_layer and hasattr(self.data_layer, 'update_persona'):
            await self.data_layer.update_persona(persona_id, updates)
            return True
        return False
    
    async def delete_persona(self, persona_id: str) -> bool:
        """ペルソナを削除"""
        if self.data_layer and hasattr(self.data_layer, 'delete_persona'):
            await self.data_layer.delete_persona(persona_id)
            return True
        return False
    
    async def set_active_persona(self, persona_id: str) -> bool:
        """ペルソナをアクティブに設定"""
        if self.data_layer and hasattr(self.data_layer, 'set_active_persona'):
            await self.data_layer.set_active_persona(persona_id)
            return True
        return False
    
    async def initialize_default_personas(self) -> None:
        """デフォルトペルソナを初期化（初回起動時）"""
        if self.data_layer and hasattr(self.data_layer, 'get_personas'):
            existing_personas = await self.data_layer.get_personas()
            
            # 既存のペルソナがない場合のみデフォルトを作成
            if not existing_personas:
                for persona in self.DEFAULT_PERSONAS:
                    await self.create_persona(persona)
                
                # 最初のペルソナをアクティブに
                if self.DEFAULT_PERSONAS:
                    first_persona = self.DEFAULT_PERSONAS[0]
                    await self.set_active_persona(first_persona.get("name"))
    
    def format_persona_info(self, persona: Dict) -> str:
        """ペルソナ情報を表示用にフォーマット"""
        if not persona:
            return "ペルソナが選択されていません"
        
        info = f"**{persona.get('name', 'Unknown')}**\n"
        info += f"📝 {persona.get('description', 'No description')}\n"
        info += f"🤖 Model: {persona.get('model', 'gpt-4o-mini')}\n"
        info += f"🌡️ Temperature: {persona.get('temperature', 0.7)}\n"
        
        if persona.get('max_tokens'):
            info += f"📊 Max Tokens: {persona.get('max_tokens')}\n"
        
        if persona.get('tags'):
            info += f"🏷️ Tags: {', '.join(persona.get('tags', []))}\n"
        
        return info

# シングルトンインスタンス
persona_manager = PersonaManager()
