#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FEA Check - FEANX MECファイル チェックシステム
Streamlit Webアプリケーション
"""

import streamlit as st
from pathlib import Path
import sys

# srcモジュールをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.parser import parse_mec_file
from src.ui_components import (
    display_model_info,
    display_subcases,
    display_loads,
    display_properties,
    display_materials,
    display_analysis_settings,
    display_boundary_conditions
)


def main():
    # ページ設定
    st.set_page_config(
        page_title="MECファイル解析",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # タイトル
    st.title("🔍 FEANX MECファイル解析システム")
    st.markdown("---")
    
    # サイドバー
    with st.sidebar:
        st.header("📁 ファイル選択")
        
        # ファイルアップロード
        uploaded_file = st.file_uploader(
            "MECファイルをアップロード",
            type=['mec'],
            help="FEANXで出力されたMECファイルを選択してください"
        )
        
        # サンプルファイルの選択オプション
        st.markdown("---")
        use_sample = st.checkbox("サンプルファイルを使用", value=False)
        
        if use_sample:
            sample_path = Path(__file__).parent / "docs" / "NXGT1-15-17-19_解析ケース-1.mec"
            if sample_path.exists():
                st.success(f"サンプルファイル: {sample_path.name}")
            else:
                st.error("サンプルファイルが見つかりません")
                use_sample = False
    
    # メインコンテンツ
    if uploaded_file is not None or use_sample:
        try:
            # ファイル読み込み
            if uploaded_file is not None:
                file_content = uploaded_file.read().decode('utf-8', errors='ignore')
                file_name = uploaded_file.name
            else:
                sample_path = Path(__file__).parent / "docs" / "NXGT1-15-17-19_解析ケース-1.mec"
                with open(sample_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
                file_name = sample_path.name
            
            # パース処理
            with st.spinner("MECファイルを解析中..."):
                parsed_data = parse_mec_file(file_content)
            
            # ファイル情報表示
            file_info = f"📄 解析中のファイル: **{file_name}**"
            if parsed_data.get('title'):
                file_info += f" | 📋 タイトル: **{parsed_data['title']}**"
            st.info(file_info)
            
            st.success("✅ 解析完了!")
            
            # タブで情報を整理
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                "📊 モデル情報",
                "⚙️ 解析設定",
                "🔄 解析ステップ",
                "⚡ 荷重",
                "📐 プロパティ",
                "🧱 材料",
                "🔒 境界条件"
            ])
            
            with tab1:
                display_model_info(parsed_data['model_info'])
                
                # 統計情報
                st.markdown("---")
                st.subheader("📈 統計情報")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("材料数", len(parsed_data['materials']))
                with col2:
                    st.metric("プロパティ数", len(parsed_data['properties']))
                with col3:
                    st.metric("解析ステップ数", len(parsed_data['subcases']))
                with col4:
                    st.metric("SET定義数", len(parsed_data.get('sets', [])))
            
            with tab2:
                display_analysis_settings(
                    parsed_data.get('title', ''),
                    parsed_data.get('params', {}),
                    parsed_data.get('nlparams', [])
                )
            
            with tab3:
                display_subcases(
                    parsed_data['subcases'],
                    parsed_data.get('stage_configs', []),
                    parsed_data.get('geoparams', [])
                )
            
            with tab4:
                display_loads(parsed_data['loads'])
            
            with tab5:
                display_properties(parsed_data['properties'], parsed_data['materials'])
            
            with tab6:
                display_materials(parsed_data['materials'])
            
            with tab7:
                display_boundary_conditions(parsed_data.get('boundary_conditions', {}))
            
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            with st.expander("詳細情報"):
                st.exception(e)
    
    else:
        # 初期画面
        st.info("👈 左のサイドバーからMECファイルをアップロードするか、サンプルファイルを使用してください。")
        
        st.markdown("---")
        st.subheader("📖 使い方")
        st.markdown("""
        1. **ファイルアップロード**: 左のサイドバーからMECファイルをドラッグ&ドロップ
        2. **データ確認**: 各タブで解析設定を確認
        3. **視覚化**: 材料プロパティ、解析ステップ、荷重条件などを表形式で表示
        
        ### 対応している情報
        - ✅ モデル情報(節点数、要素数など)
        - ✅ 解析ステップ(SUBCASE、STGCONF、GEOPARM統合表示)
        - ✅ 荷重条件(GRAV, PLOAD4)
        - ✅ プロパティ(Shell, Solid)
        - ✅ 材料(弾性、D-min、Mohr-Coulomb)
        - ✅ 境界条件(SPC)
        - ✅ 非線形解析パラメータ(NLPARM)
        - ✅ PARAMパラメータ
        - ✅ SET定義(統計情報として表示)
        
        ### 今後の機能(予定)
        - 🔜 自動チェック機能
        - 🔜 PDF/Excelレポート出力
        - 🔜 設定値の比較機能
        """)


if __name__ == "__main__":
    main()
