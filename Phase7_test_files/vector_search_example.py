import asyncio
from typing import List, Dict, Optional
import openai

class VectorSearchExample:
    """
    ベクトル検索の実装例
    このクラスはOpenAI Embeddings APIを使用して
    セマンティック検索を実装します。
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = openai.Client(api_key=api_key)
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        テキストから埋め込みベクトルを生成
        
        Args:
            text: 埋め込み対象のテキスト
        
        Returns:
            埋め込みベクトル（float配列）
        """
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        コサイン類似度を計算
        
        Args:
            vec1: ベクトル1
            vec2: ベクトル2
        
        Returns:
            類似度（0-1の範囲）
        """
        import numpy as np
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        return dot_product / (norm1 * norm2)
    
    async def search(self, 
                     query: str, 
                     documents: List[Dict[str, str]],
                     top_k: int = 5) -> List[Dict]:
        """
        セマンティック検索を実行
        
        Args:
            query: 検索クエリ
            documents: 検索対象ドキュメントのリスト
            top_k: 返す結果の数
        
        Returns:
            類似度順にソートされた結果
        """
        # クエリの埋め込みを生成
        query_embedding = await self.create_embedding(query)
        
        # 各ドキュメントとの類似度を計算
        results = []
        for doc in documents:
            doc_embedding = await self.create_embedding(doc['content'])
            similarity = self.cosine_similarity(query_embedding, doc_embedding)
            
            results.append({
                'document': doc,
                'similarity': similarity
            })
        
        # 類似度でソート
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:top_k]


# 使用例
async def main():
    # 初期化
    searcher = VectorSearchExample(api_key="your-api-key")
    
    # サンプルドキュメント
    documents = [
        {"id": "1", "content": "Pythonは汎用プログラミング言語です"},
        {"id": "2", "content": "機械学習はAIの一分野です"},
        {"id": "3", "content": "ベクトル検索は意味的な類似性を見つけます"},
    ]
    
    # 検索実行
    results = await searcher.search(
        query="プログラミングについて教えて",
        documents=documents,
        top_k=2
    )
    
    # 結果表示
    for result in results:
        print(f"ID: {result['document']['id']}")
        print(f"類似度: {result['similarity']:.3f}")
        print(f"内容: {result['document']['content']}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
