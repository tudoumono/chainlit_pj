"""
チャート・グラフ可視化ヘルパー
統計データをHTML/CSS/JSで可視化
"""

from typing import List, Dict, Any
import json


class ChartHelper:
    """チャート生成の共通ヘルパークラス"""
    
    @staticmethod
    def create_usage_dashboard(summary_data: Dict[str, Any]) -> str:
        """使用量ダッシュボードのHTML生成"""
        api_summary = summary_data.get("api_summary", {})
        model_usage = summary_data.get("model_usage", [])
        persona_usage = summary_data.get("persona_usage", [])
        daily_usage = summary_data.get("daily_usage", [])
        period = summary_data.get("period", {})
        
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1200px;">
            <h2>📊 使用量ダッシュボード</h2>
            <p style="color: #666; margin-bottom: 24px;">
                期間: {period.get('start', '')[:10]} 〜 {period.get('end', '')[:10]} ({period.get('days', 0)}日間)
            </p>
            
            <!-- サマリーカード -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; margin-bottom: 8px;">{api_summary.get('request_count', 0):,}</div>
                    <div style="opacity: 0.9;">総リクエスト数</div>
                </div>
                
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; margin-bottom: 8px;">{api_summary.get('total_tokens', 0):,}</div>
                    <div style="opacity: 0.9;">総トークン数</div>
                </div>
                
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; margin-bottom: 8px;">${api_summary.get('total_cost', 0):.4f}</div>
                    <div style="opacity: 0.9;">推定コスト</div>
                </div>
                
                <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; margin-bottom: 8px;">${api_summary.get('avg_cost_per_request', 0):.6f}</div>
                    <div style="opacity: 0.9;">平均コスト/リクエスト</div>
                </div>
            </div>
        """
        
        # モデル別使用量チャート
        if model_usage:
            html += ChartHelper._create_model_usage_chart(model_usage)
        
        # ペルソナ別使用量チャート
        if persona_usage:
            html += ChartHelper._create_persona_usage_chart(persona_usage)
        
        # 日別使用量チャート
        if daily_usage:
            html += ChartHelper._create_daily_usage_chart(daily_usage)
        
        html += "</div>"
        return html
    
    @staticmethod
    def _create_model_usage_chart(model_usage: List[Dict]) -> str:
        """モデル別使用量チャート"""
        if not model_usage:
            return ""
        
        total_cost = sum(item["cost"] for item in model_usage)
        
        html = """
            <div style="background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">🤖 モデル別使用量</h3>
                <div style="display: grid; gap: 12px;">
        """
        
        colors = ["#4facfe", "#667eea", "#f093fb", "#fa709a", "#fee140"]
        
        for i, item in enumerate(model_usage[:5]):  # 上位5モデル
            percentage = (item["cost"] / total_cost * 100) if total_cost > 0 else 0
            color = colors[i % len(colors)]
            
            html += f"""
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="min-width: 120px; font-weight: 500;">{item['model']}</div>
                    <div style="flex: 1; background: #f0f0f0; border-radius: 8px; overflow: hidden;">
                        <div style="height: 24px; background: {color}; width: {percentage}%; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 12px; font-weight: 500;">
                            {percentage:.1f}%
                        </div>
                    </div>
                    <div style="min-width: 100px; text-align: right;">
                        <div style="font-weight: 500;">${item['cost']:.4f}</div>
                        <div style="font-size: 12px; color: #666;">{item['count']} requests</div>
                    </div>
                </div>
            """
        
        html += """
                </div>
            </div>
        """
        
        return html
    
    @staticmethod
    def _create_persona_usage_chart(persona_usage: List[Dict]) -> str:
        """ペルソナ別使用量チャート"""
        if not persona_usage:
            return ""
        
        total_cost = sum(item["cost"] for item in persona_usage)
        
        html = """
            <div style="background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">🎭 ペルソナ別使用量</h3>
                <div style="display: grid; gap: 12px;">
        """
        
        colors = ["#764ba2", "#f5576c", "#00f2fe", "#fee140", "#4facfe"]
        
        for i, item in enumerate(persona_usage[:5]):  # 上位5ペルソナ
            percentage = (item["cost"] / total_cost * 100) if total_cost > 0 else 0
            color = colors[i % len(colors)]
            
            html += f"""
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="min-width: 150px; font-weight: 500;">{item['persona']}</div>
                    <div style="flex: 1; background: #f0f0f0; border-radius: 8px; overflow: hidden;">
                        <div style="height: 24px; background: {color}; width: {percentage}%; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 12px; font-weight: 500;">
                            {percentage:.1f}%
                        </div>
                    </div>
                    <div style="min-width: 100px; text-align: right;">
                        <div style="font-weight: 500;">${item['cost']:.4f}</div>
                        <div style="font-size: 12px; color: #666;">{item['count']} requests</div>
                    </div>
                </div>
            """
        
        html += """
                </div>
            </div>
        """
        
        return html
    
    @staticmethod
    def _create_daily_usage_chart(daily_usage: List[Dict]) -> str:
        """日別使用量チャート"""
        if not daily_usage:
            return ""
        
        max_cost = max(item["cost"] for item in daily_usage) if daily_usage else 1
        max_requests = max(item["requests"] for item in daily_usage) if daily_usage else 1
        
        html = """
            <div style="background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">📈 日別使用量推移</h3>
                <div style="display: grid; gap: 8px; padding: 16px 0;">
        """
        
        for item in daily_usage[-14:]:  # 直近14日
            cost_height = (item["cost"] / max_cost * 60) if max_cost > 0 else 0
            requests_height = (item["requests"] / max_requests * 60) if max_requests > 0 else 0
            
            html += f"""
                <div style="display: flex; align-items: end; gap: 8px; min-height: 80px;">
                    <div style="min-width: 80px; font-size: 12px; color: #666;">{item['date'][5:]}</div>
                    <div style="flex: 1; display: flex; align-items: end; gap: 4px;">
                        <div style="background: linear-gradient(to top, #4facfe, #00f2fe); width: 40%; height: {cost_height}px; border-radius: 4px 4px 0 0; min-height: 4px;" title="コスト: ${item['cost']:.4f}"></div>
                        <div style="background: linear-gradient(to top, #667eea, #764ba2); width: 40%; height: {requests_height}px; border-radius: 4px 4px 0 0; min-height: 4px;" title="リクエスト数: {item['requests']}"></div>
                    </div>
                    <div style="min-width: 80px; text-align: right; font-size: 12px;">
                        <div style="color: #4facfe; font-weight: 500;">${item['cost']:.4f}</div>
                        <div style="color: #667eea;">{item['requests']} req</div>
                    </div>
                </div>
            """
        
        html += """
                </div>
                <div style="display: flex; gap: 20px; font-size: 12px; color: #666; margin-top: 16px;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <div style="width: 12px; height: 12px; background: linear-gradient(to right, #4facfe, #00f2fe); border-radius: 2px;"></div>
                        コスト
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <div style="width: 12px; height: 12px; background: linear-gradient(to right, #667eea, #764ba2); border-radius: 2px;"></div>
                        リクエスト数
                    </div>
                </div>
            </div>
        """
        
        return html
    
    @staticmethod
    def create_vector_store_dashboard(vs_summary: Dict[str, Any]) -> str:
        """ベクトルストア使用量ダッシュボード"""
        vs_usage = vs_summary.get("vs_usage", [])
        period = vs_summary.get("period", {})
        
        if not vs_usage:
            return f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                <h3>🗂️ ベクトルストア使用状況</h3>
                <p style="color: #666;">期間内のベクトルストア使用履歴はありません。</p>
            </div>
            """
        
        # 統計計算
        total_operations = sum(item["count"] for item in vs_usage)
        total_files = sum(item["total_files"] for item in vs_usage)
        total_size = sum(item["total_size_mb"] for item in vs_usage)
        
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
            <h3>🗂️ ベクトルストア使用状況</h3>
            <p style="color: #666; margin-bottom: 24px;">
                期間: {period.get('start', '')[:10]} 〜 {period.get('end', '')[:10]}
            </p>
            
            <!-- サマリーカード -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_operations}</div>
                    <div style="opacity: 0.9; font-size: 12px;">総操作数</div>
                </div>
                
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_files}</div>
                    <div style="opacity: 0.9; font-size: 12px;">処理ファイル数</div>
                </div>
                
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_size:.1f}</div>
                    <div style="opacity: 0.9; font-size: 12px;">総サイズ (MB)</div>
                </div>
            </div>
            
            <!-- 操作詳細 -->
            <div style="background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0;">操作詳細</h4>
                <div style="display: grid; gap: 8px;">
        """
        
        vs_type_colors = {
            "company": "#667eea",
            "personal": "#f5576c", 
            "session": "#4facfe"
        }
        
        for item in vs_usage:
            color = vs_type_colors.get(item["vs_type"], "#999")
            percentage = (item["count"] / total_operations * 100) if total_operations > 0 else 0
            
            html += f"""
                <div style="display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f0f0;">
                    <div style="min-width: 80px; font-size: 12px; color: {color}; font-weight: 500;">
                        {item['vs_type'].title()}
                    </div>
                    <div style="min-width: 80px; font-size: 12px;">
                        {item['operation']}
                    </div>
                    <div style="flex: 1; background: #f0f0f0; border-radius: 4px; overflow: hidden;">
                        <div style="height: 20px; background: {color}; width: {percentage}%; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 10px;">
                            {percentage:.1f}%
                        </div>
                    </div>
                    <div style="min-width: 120px; text-align: right; font-size: 12px;">
                        <div style="font-weight: 500;">{item['count']} 回</div>
                        <div style="color: #666;">{item['total_files']} files, {item['total_size_mb']:.1f}MB</div>
                    </div>
                </div>
            """
        
        html += """
                </div>
            </div>
        </div>
        """
        
        return html
    
    @staticmethod
    def create_simple_table(data: List[Dict], title: str = "") -> str:
        """シンプルなテーブル形式でのデータ表示"""
        if not data:
            return f"<p>{title}: データなし</p>"
        
        headers = list(data[0].keys()) if data else []
        
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
            {f'<h4>{title}</h4>' if title else ''}
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #f8f9fa;">
        """
        
        for header in headers:
            html += f'<th style="padding: 8px 12px; border: 1px solid #dee2e6; text-align: left;">{header}</th>'
        
        html += """
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in data:
            html += '<tr>'
            for header in headers:
                value = row.get(header, '')
                html += f'<td style="padding: 8px 12px; border: 1px solid #dee2e6;">{value}</td>'
            html += '</tr>'
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html