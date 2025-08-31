"""
統計・分析ハンドラー
使用量ダッシュボード、コスト分析、効率性分析を提供
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import chainlit as cl
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.logger import app_logger
from utils.analytics_logger import analytics_logger
from utils.chart_helper import ChartHelper


class AnalyticsHandler:
    """統計・分析機能を統括するクラス"""
    
    def __init__(self):
        """統計ハンドラーを初期化"""
        self.chart_helper = ChartHelper()
    
    async def show_usage_dashboard(self, user_id: str = None, days: int = 30):
        """使用量ダッシュボードを表示"""
        try:
            loading_msg = await ui.show_loading_message("使用量データを分析中...")
            
            # 使用量データの取得
            summary_data = analytics_logger.get_usage_summary(user_id, days)
            
            if not summary_data:
                await ui.update_loading_message(
                    loading_msg,
                    "📊 統計データがありません。\n\n"
                    "AIとの会話やファイルアップロードを行うと、使用量データが蓄積されます。"
                )
                return
            
            # ダッシュボードHTML生成
            dashboard_html = self.chart_helper.create_usage_dashboard(summary_data)
            
            # HTMLメッセージを直接送信
            await cl.Message(
                content=dashboard_html,
                author="📊 Analytics"
            ).send()
            
            # ベクトルストア使用状況も表示
            vs_summary = analytics_logger.get_vector_store_summary(user_id, days)
            if vs_summary and vs_summary.get("vs_usage"):
                vs_dashboard_html = self.chart_helper.create_vector_store_dashboard(vs_summary)
                await cl.Message(
                    content=vs_dashboard_html,
                    author="📊 Vector Store Analytics"
                ).send()
            
            app_logger.info("使用量ダッシュボード表示完了", user_id=user_id, days=days)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "使用量ダッシュボード表示")
    
    async def show_cost_analysis(self, user_id: str = None, days: int = 30):
        """詳細なコスト分析を表示"""
        try:
            loading_msg = await ui.show_loading_message("コスト分析を実行中...")
            
            summary_data = analytics_logger.get_usage_summary(user_id, days)
            
            if not summary_data or not summary_data.get("api_summary"):
                await ui.update_loading_message(
                    loading_msg,
                    "💰 コスト分析データがありません。"
                )
                return
            
            api_summary = summary_data["api_summary"]
            model_usage = summary_data["model_usage"]
            daily_usage = summary_data["daily_usage"]
            period = summary_data["period"]
            
            # 予測コストの計算
            if daily_usage:
                recent_days = daily_usage[-7:]  # 直近7日
                avg_daily_cost = sum(day["cost"] for day in recent_days) / len(recent_days)
                projected_monthly_cost = avg_daily_cost * 30
            else:
                avg_daily_cost = 0
                projected_monthly_cost = 0
            
            # コスト効率性の分析
            efficiency_score = self._calculate_efficiency_score(summary_data)
            
            cost_analysis = f"""
# 💰 詳細コスト分析

## 📊 期間サマリー ({period.get('days', 0)}日間)
- **総コスト**: ${api_summary.get('total_cost', 0):.4f}
- **平均日次コスト**: ${api_summary.get('total_cost', 0) / max(period.get('days', 1), 1):.4f}
- **リクエスト単価**: ${api_summary.get('avg_cost_per_request', 0):.6f}
- **総リクエスト数**: {api_summary.get('request_count', 0):,}

## 📈 コスト予測
- **直近7日間の平均日次コスト**: ${avg_daily_cost:.4f}
- **月間予測コスト**: ${projected_monthly_cost:.2f}

## ⚡ 効率性スコア
**{efficiency_score}/10** - {self._get_efficiency_comment(efficiency_score)}

## 🤖 モデル別コスト効率
"""
            
            # モデル別の詳細分析
            for model in model_usage[:3]:  # 上位3モデル
                cost_per_token = (model["cost"] / model["tokens"]) if model["tokens"] > 0 else 0
                cost_analysis += f"""
### {model['model']}
- **総コスト**: ${model['cost']:.4f} ({model['cost']/api_summary.get('total_cost', 1)*100:.1f}%)
- **リクエスト数**: {model['count']:,}
- **トークン数**: {model['tokens']:,}
- **コスト/トークン**: ${cost_per_token:.8f}
"""
            
            # コスト最適化提案
            cost_analysis += "\n## 💡 コスト最適化提案\n"
            cost_analysis += self._generate_cost_optimization_tips(summary_data)
            
            await ui.update_loading_message(loading_msg, cost_analysis)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "コスト分析")
    
    async def show_persona_efficiency(self, user_id: str = None, days: int = 30):
        """ペルソナ効率性分析を表示"""
        try:
            loading_msg = await ui.show_loading_message("ペルソナ効率性を分析中...")
            
            summary_data = analytics_logger.get_usage_summary(user_id, days)
            persona_usage = summary_data.get("persona_usage", [])
            
            if not persona_usage:
                await ui.update_loading_message(
                    loading_msg,
                    "🎭 ペルソナ効率性データがありません。\n\n"
                    "異なるペルソナを使用すると、効率性比較データが蓄積されます。"
                )
                return
            
            total_cost = sum(p["cost"] for p in persona_usage)
            total_requests = sum(p["count"] for p in persona_usage)
            
            efficiency_analysis = f"""
# 🎭 ペルソナ効率性分析

## 📊 全体サマリー ({days}日間)
- **分析対象ペルソナ数**: {len(persona_usage)}
- **総コスト**: ${total_cost:.4f}
- **総リクエスト数**: {total_requests:,}

## 🏆 ペルソナランキング

"""
            
            # ペルソナ別効率性計算と表示
            for i, persona in enumerate(persona_usage, 1):
                cost_per_request = persona["cost"] / persona["count"] if persona["count"] > 0 else 0
                usage_ratio = (persona["count"] / total_requests * 100) if total_requests > 0 else 0
                efficiency_rating = self._rate_persona_efficiency(cost_per_request, usage_ratio)
                
                efficiency_analysis += f"""
### {i}. {persona['persona']}
- **使用回数**: {persona['count']:,} ({usage_ratio:.1f}%)
- **総コスト**: ${persona['cost']:.4f}
- **平均コスト/リクエスト**: ${cost_per_request:.6f}
- **効率性レーティング**: {efficiency_rating}

"""
            
            # 最適化提案
            efficiency_analysis += self._generate_persona_optimization_tips(persona_usage)
            
            await ui.update_loading_message(loading_msg, efficiency_analysis)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ効率性分析")
    
    async def show_usage_trends(self, user_id: str = None, days: int = 30):
        """使用量トレンド分析を表示"""
        try:
            loading_msg = await ui.show_loading_message("トレンド分析中...")
            
            summary_data = analytics_logger.get_usage_summary(user_id, days)
            daily_usage = summary_data.get("daily_usage", [])
            
            if len(daily_usage) < 3:
                await ui.update_loading_message(
                    loading_msg,
                    "📈 トレンド分析には最低3日間のデータが必要です。"
                )
                return
            
            # トレンド計算
            recent_period = daily_usage[-7:]  # 直近1週間
            previous_period = daily_usage[-14:-7] if len(daily_usage) >= 14 else daily_usage[:-7]
            
            recent_avg_cost = sum(day["cost"] for day in recent_period) / len(recent_period)
            recent_avg_requests = sum(day["requests"] for day in recent_period) / len(recent_period)
            
            if previous_period:
                prev_avg_cost = sum(day["cost"] for day in previous_period) / len(previous_period)
                prev_avg_requests = sum(day["requests"] for day in previous_period) / len(previous_period)
                
                cost_change = ((recent_avg_cost - prev_avg_cost) / prev_avg_cost * 100) if prev_avg_cost > 0 else 0
                requests_change = ((recent_avg_requests - prev_avg_requests) / prev_avg_requests * 100) if prev_avg_requests > 0 else 0
            else:
                cost_change = 0
                requests_change = 0
            
            # 使用パターン分析
            usage_pattern = self._analyze_usage_pattern(daily_usage)
            
            trend_analysis = f"""
# 📈 使用量トレンド分析

## 🔄 変化率 (直近7日 vs 前週)
- **コスト変化**: {cost_change:+.1f}% ({self._get_trend_indicator(cost_change)})
- **リクエスト数変化**: {requests_change:+.1f}% ({self._get_trend_indicator(requests_change)})

## 📊 直近の使用状況
- **平均日次コスト**: ${recent_avg_cost:.4f}
- **平均日次リクエスト**: {recent_avg_requests:.1f}

## 🔍 使用パターン分析
{usage_pattern}

## 📅 週間予測
- **予測週次コスト**: ${recent_avg_cost * 7:.4f}
- **予測週次リクエスト**: {recent_avg_requests * 7:.0f}

"""
            
            await ui.update_loading_message(loading_msg, trend_analysis)
            
            # 詳細な日別データも表示
            if len(daily_usage) > 10:
                detailed_chart = self._create_detailed_trend_chart(daily_usage[-14:])
                await ui.send_system_message(detailed_chart)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "トレンド分析")
    
    def _calculate_efficiency_score(self, summary_data: Dict) -> int:
        """効率性スコアを計算 (1-10)"""
        try:
            api_summary = summary_data.get("api_summary", {})
            model_usage = summary_data.get("model_usage", [])
            
            score = 5  # ベーススコア
            
            # コスト効率の評価
            avg_cost = api_summary.get("avg_cost_per_request", 0)
            if avg_cost < 0.001:
                score += 2
            elif avg_cost < 0.01:
                score += 1
            elif avg_cost > 0.1:
                score -= 2
            elif avg_cost > 0.05:
                score -= 1
            
            # モデル選択の多様性
            if len(model_usage) > 2:
                score += 1
            
            # 高コストモデル使用の適切性チェック
            expensive_models = [m for m in model_usage if m["model"] in ["gpt-4o", "gpt-4-turbo"]]
            if expensive_models:
                expensive_ratio = sum(m["cost"] for m in expensive_models) / api_summary.get("total_cost", 1)
                if expensive_ratio < 0.3:  # 高コストモデルの使用が30%未満
                    score += 1
                elif expensive_ratio > 0.8:  # 高コストモデルが80%以上
                    score -= 1
            
            return max(1, min(10, score))
            
        except Exception:
            return 5
    
    def _get_efficiency_comment(self, score: int) -> str:
        """効率性スコアのコメント"""
        if score >= 9:
            return "非常に効率的な使用です！"
        elif score >= 7:
            return "効率的な使用ができています"
        elif score >= 5:
            return "標準的な効率性です"
        elif score >= 3:
            return "改善の余地があります"
        else:
            return "大幅な最適化が必要です"
    
    def _generate_cost_optimization_tips(self, summary_data: Dict) -> str:
        """コスト最適化提案を生成"""
        tips = []
        
        model_usage = summary_data.get("model_usage", [])
        api_summary = summary_data.get("api_summary", {})
        
        # 高コストモデルの最適化提案
        expensive_models = [m for m in model_usage if m["model"] in ["gpt-4o", "gpt-4-turbo"]]
        if expensive_models:
            total_expensive_cost = sum(m["cost"] for m in expensive_models)
            if total_expensive_cost / api_summary.get("total_cost", 1) > 0.5:
                tips.append("• 簡単なタスクにはgpt-4o-miniの使用を検討してください")
        
        # 平均コストが高い場合
        avg_cost = api_summary.get("avg_cost_per_request", 0)
        if avg_cost > 0.05:
            tips.append("• リクエスト単価が高めです。プロンプトの最適化を検討してください")
        
        # 使用量が多い場合
        if api_summary.get("request_count", 0) > 1000:
            tips.append("• 頻繁な質問はテンプレート化やFAQの活用を検討してください")
        
        if not tips:
            tips.append("• 現在の使用パターンは効率的です。このまま継続してください")
        
        return "\n".join(tips)
    
    def _rate_persona_efficiency(self, cost_per_request: float, usage_ratio: float) -> str:
        """ペルソナ効率性レーティング"""
        if cost_per_request < 0.005 and usage_ratio > 10:
            return "⭐⭐⭐ 最高効率"
        elif cost_per_request < 0.01:
            return "⭐⭐ 高効率"
        elif cost_per_request < 0.05:
            return "⭐ 標準"
        else:
            return "❌ 要改善"
    
    def _generate_persona_optimization_tips(self, persona_usage: List[Dict]) -> str:
        """ペルソナ最適化提案"""
        tips = "\n## 💡 最適化提案\n\n"
        
        if len(persona_usage) == 1:
            tips += "• 複数のペルソナを活用することで、タスクに応じた最適化が可能です\n"
        
        # 最も効率的なペルソナ
        best_persona = min(persona_usage, key=lambda p: p["cost"] / p["count"])
        tips += f"• 最もコスト効率が良いペルソナ: **{best_persona['persona']}**\n"
        
        # 使用頻度の低いペルソナ
        low_usage = [p for p in persona_usage if p["count"] < 5]
        if low_usage:
            tips += f"• 使用頻度の低いペルソナ ({len(low_usage)}個) の見直しを検討してください\n"
        
        return tips
    
    def _analyze_usage_pattern(self, daily_usage: List[Dict]) -> str:
        """使用パターン分析"""
        if not daily_usage:
            return "データ不足のため分析できません"
        
        # 曜日別分析のためのデータ準備
        weekday_usage = {}
        for day in daily_usage:
            date = datetime.fromisoformat(day["date"])
            weekday = date.weekday()  # 0=月曜日
            
            if weekday not in weekday_usage:
                weekday_usage[weekday] = {"requests": 0, "cost": 0, "count": 0}
            
            weekday_usage[weekday]["requests"] += day["requests"]
            weekday_usage[weekday]["cost"] += day["cost"]
            weekday_usage[weekday]["count"] += 1
        
        # 最も活発な曜日
        if weekday_usage:
            avg_by_weekday = {
                day: {
                    "requests": data["requests"] / data["count"],
                    "cost": data["cost"] / data["count"]
                }
                for day, data in weekday_usage.items()
            }
            
            most_active_day = max(avg_by_weekday.items(), key=lambda x: x[1]["requests"])
            weekdays = ["月", "火", "水", "木", "金", "土", "日"]
            
            pattern = f"最も活発な曜日: {weekdays[most_active_day[0]]}曜日 "
            pattern += f"(平均{most_active_day[1]['requests']:.1f}リクエスト)"
        else:
            pattern = "パターン分析データが不足しています"
        
        return pattern
    
    def _get_trend_indicator(self, change_percent: float) -> str:
        """トレンド指標"""
        if change_percent > 20:
            return "📈 急増"
        elif change_percent > 5:
            return "↗️ 増加"
        elif change_percent > -5:
            return "➡️ 安定"
        elif change_percent > -20:
            return "↘️ 減少"
        else:
            return "📉 急減"
    
    def _create_detailed_trend_chart(self, daily_data: List[Dict]) -> str:
        """詳細なトレンドチャート"""
        return f"""
## 📊 詳細トレンド (直近{len(daily_data)}日間)

{self.chart_helper._create_daily_usage_chart(daily_data)}

**トレンドの読み方:**
- 青: コスト推移
- 紫: リクエスト数推移
- 右肩上がりは使用量増加、右肩下がりは減少を示します
"""


# グローバルインスタンス  
analytics_handler = AnalyticsHandler()