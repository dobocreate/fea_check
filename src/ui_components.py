#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit UIコンポーネント
データ表示用の再利用可能なコンポーネント
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any


def format_scientific(val: float) -> str:
    """数値を適切な形式でフォーマット"""
    if val is None:
        return "-"
    try:
        num = float(val)
        if num == 0:
            return "0"
        if abs(num) >= 1000:
            exp = 0
            while abs(num) >= 10:
                num /= 10
                exp += 1
            return f"{num:.2f}×10^{exp}"
        elif abs(num) < 0.01 and num != 0:
            exp = 0
            while abs(num) < 1:
                num *= 10
                exp -= 1
            return f"{num:.2f}×10^{exp}"
        else:
            if num == int(num):
                return str(int(num))
            return f"{num:.3f}".rstrip('0').rstrip('.')
    except:
        return str(val)


def display_model_info(model_info: Dict[str, int]):
    """モデル情報を表示"""
    st.subheader("📊 モデル情報")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("節点数", f"{model_info['nodes']:,}")
    with col2:
        st.metric("要素数", f"{model_info['elements']:,}")
    with col3:
        st.metric("拘束条件数", f"{model_info['spc_count']:,}")


def display_subcases(subcases: List[Dict[str, Any]], stage_configs: List[Dict[str, Any]] = None, geoparams: List[Dict[str, Any]] = None):
    """解析ステップを表示（ステージ設定と地盤パラメータを統合）"""
    st.subheader("🔄 解析ステップ")
    
    if not subcases:
        st.info("解析ステップが見つかりませんでした。")
        return
    
    # ステージ設定とGEOPARMを辞書化
    stage_dict = {sc['id']: sc for sc in (stage_configs or [])}
    geoparm_dict = {gp['subcase_id']: gp['geoparm_id'] for gp in (geoparams or [])}
    
    df_data = []
    for sc in subcases:
        row = {
            'ステップ': sc['id'],
            'ラベル': sc['label'],
            'SOL': sc['sol'] if sc['sol'] else '-',
            '荷重ID': sc['load'] if sc['load'] else '-',
            '拘束ID': sc['spc'] if sc['spc'] else '-',
            '前ステップ': sc['use_stage'] if sc['use_stage'] else '-'
        }
        
        # GEOPARM IDを追加
        if sc['id'] in geoparm_dict:
            row['GEOPARM'] = geoparm_dict[sc['id']]
        else:
            row['GEOPARM'] = '-'
        
        # ステージ設定パラメータを追加（簡略化）
        if sc['id'] in stage_dict:
            stage = stage_dict[sc['id']]
            params = []
            if stage['param1'] is not None:
                params.append(f"P1:{stage['param1']}")
            if stage['param2'] is not None:
                params.append(f"P2:{stage['param2']}")
            if stage['param3'] is not None:
                params.append(f"P3:{stage['param3']}")
            if stage['param4'] is not None:
                params.append(f"P4:{stage['param4']}")
            row['STGCONF'] = ', '.join(params) if params else '-'
        else:
            row['STGCONF'] = '-'
        
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ステップ": st.column_config.NumberColumn("ステップ", width="small"),
            "ラベル": st.column_config.TextColumn("ラベル", width="large"),
            "SOL": st.column_config.TextColumn("SOL", width="small"),
            "荷重ID": st.column_config.NumberColumn("荷重ID", width="small"),
            "拘束ID": st.column_config.NumberColumn("拘束ID", width="small"),
            "前ステップ": st.column_config.NumberColumn("前ステップ", width="small"),
            "GEOPARM": st.column_config.NumberColumn("GEOPARM", width="small"),
            "STGCONF": st.column_config.TextColumn("STGCONF", width="medium"),
        }
    )
    
    # 補足説明
    with st.expander("📖 項目の説明"):
        st.markdown("""
        - **ステップ**: SUBCASE ID
        - **ラベル**: 解析ステップの名称
        - **SOL**: ソルバータイプ（106=非線形静解析）
        - **荷重ID**: 適用される荷重のID
        - **拘束ID**: 適用される境界条件(SPC)のID
        - **前ステップ**: 前のステップのID（ステージ解析）
        - **GEOPARM**: 地盤解析パラメータのID
        - **STGCONF**: ステージ設定パラメータ
        """)


def display_loads(loads: Dict[str, Any]):
    """荷重情報を表示"""
    st.subheader("⚡ 荷重情報")
    
    if not loads['grav'] and not loads['pload4']:
        st.info("荷重情報が見つかりませんでした。")
        return
    
    df_data = []
    
    # 重力荷重
    for grav in loads['grav']:
        df_data.append({
            '荷重タイプ': '重力荷重 (GRAV)',
            'ID': grav['id'],
            '値': f"{format_scientific(grav['value'])} (加速度)",
            '要素数': '-'
        })
    
    # 面圧荷重
    for pload_id, pload_data in sorted(loads['pload4'].items()):
        pressure_kn = pload_data['pressure'] / 1000
        df_data.append({
            '荷重タイプ': '面圧荷重 (PLOAD4)',
            'ID': pload_id,
            '値': f"{pressure_kn:.1f} kN/m²",
            '要素数': f"{pload_data['count']:,}"
        })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "荷重タイプ": st.column_config.TextColumn("荷重タイプ", width="medium"),
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "値": st.column_config.TextColumn("値", width="medium"),
                "要素数": st.column_config.TextColumn("要素数", width="small"),
            }
        )


def display_properties(properties: List[Dict[str, Any]], materials: List[Dict[str, Any]] = None):
    """プロパティ情報を表示"""
    st.subheader("📐 プロパティ")
    
    if not properties:
        st.info("プロパティが見つかりませんでした。")
        return
    
    # 材料IDから材料名を取得する関数
    def get_material_info(material_id):
        if not material_id or not materials:
            return '-'
        for mat in materials:
            if mat['id'] == material_id:
                return f"{material_id}: {mat['name']}"
        return str(material_id)
    
    # プロパティタイプ別に分類
    shell_props = [p for p in properties if p['type'] == 'Shell']
    solid_props = [p for p in properties if p['type'] == 'Solid']
    beam_props = [p for p in properties if p['type'] == 'Beam']
    truss_props = [p for p in properties if p['type'] == 'Embedded Truss']
    
    # タイプ別の統計（1次元 → 2次元 → 3次元の順）
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("ビーム (1次元)", len(beam_props))
    with col2:
        st.metric("埋込トラス (1次元)", len(truss_props))
    with col3:
        st.metric("シェル (2次元)", len(shell_props))
    with col4:
        st.metric("ソリッド (3次元)", len(solid_props))
    
    st.markdown("---")
    
    # ビームプロパティ（1次元）
    if beam_props:
        with st.expander(f"**ビームプロパティ (1次元)** ({len(beam_props)}件)", expanded=True):
            df_data = []
            for prop in beam_props:
                df_data.append({
                    'ID': prop['id'],
                    'プロパティ名': prop['name'],
                    '材料': get_material_info(prop['material_id'])
                })
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "プロパティ名": st.column_config.TextColumn("プロパティ名", width="large"),
                    "材料": st.column_config.TextColumn("材料", width="medium"),
                }
            )
    
    # 埋込トラスプロパティ（1次元）
    if truss_props:
        with st.expander(f"**埋込トラスプロパティ (1次元)** ({len(truss_props)}件)", expanded=True):
            df_data = []
            for prop in truss_props:
                df_data.append({
                    'ID': prop['id'],
                    'プロパティ名': prop['name'],
                    '材料': get_material_info(prop['material_id'])
                })
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "プロパティ名": st.column_config.TextColumn("プロパティ名", width="large"),
                    "材料": st.column_config.TextColumn("材料", width="medium"),
                }
            )
    
    # シェルプロパティ（2次元）
    if shell_props:
        with st.expander(f"**シェルプロパティ (2次元)** ({len(shell_props)}件)", expanded=True):
            df_data = []
            for prop in shell_props:
                df_data.append({
                    'ID': prop['id'],
                    'プロパティ名': prop['name'],
                    '厚さ (m)': prop['thickness'] if prop['thickness'] else '-',
                    '材料': get_material_info(prop['material_id'])
                })
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "プロパティ名": st.column_config.TextColumn("プロパティ名", width="large"),
                    "厚さ (m)": st.column_config.TextColumn("厚さ (m)", width="small"),
                    "材料": st.column_config.TextColumn("材料", width="medium"),
                }
            )
    
    # ソリッドプロパティ（3次元）
    if solid_props:
        with st.expander(f"**ソリッドプロパティ (3次元)** ({len(solid_props)}件)", expanded=True):
            df_data = []
            for prop in solid_props:
                df_data.append({
                    'ID': prop['id'],
                    'プロパティ名': prop['name'],
                    '材料': get_material_info(prop['material_id'])
                })
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "プロパティ名": st.column_config.TextColumn("プロパティ名", width="large"),
                    "材料": st.column_config.TextColumn("材料", width="medium"),
                }
            )


def display_materials(materials: List[Dict[str, Any]]):
    """材料情報を表示"""
    st.subheader("🧱 材料")
    
    if not materials:
        st.info("材料が見つかりませんでした。")
        return
    
    # 材料タイプ別にグループ化
    material_groups = {}
    for mat in materials:
        mat_type = mat['type']
        if mat_type not in material_groups:
            material_groups[mat_type] = []
        material_groups[mat_type].append(mat)
    
    # タイプごとに表示
    for mat_type, mats in material_groups.items():
        with st.expander(f"**{mat_type}** ({len(mats)}件)", expanded=True):
            if '弾性' in mat_type:
                _display_elastic_materials(mats)
            elif 'D-min' in mat_type:
                _display_dmin_materials(mats)
            elif 'Mohr-Coulomb' in mat_type:
                _display_mohr_coulomb_materials(mats)
            else:
                _display_generic_materials(mats)


def _display_elastic_materials(materials: List[Dict[str, Any]]):
    """弾性材料を表示"""
    df_data = []
    for mat in materials:
        gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
        df_data.append({
            'ID': mat['id'],
            '材料名': mat['name'],
            'E (変形係数)\n(kN/m²)': format_scientific(mat['E']) if mat['E'] else '-',
            'ν (ポアソン比)': mat['nu'] if mat['nu'] else '-',
            'γ (単位体積重量)\n(kN/m³)': gamma
        })
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "材料名": st.column_config.TextColumn("材料名", width="large"),
        }
    )


def _display_dmin_materials(materials: List[Dict[str, Any]]):
    """D-min材料を表示"""
    df_data = []
    for mat in materials:
        gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
        df_data.append({
            'ID': mat['id'],
            '材料名': mat['name'],
            'E₀ (初期変形係数)\n(kN/m²)': format_scientific(mat['E0']) if mat.get('E0') else '-',
            'E_cr (限界変形係数)\n(kN/m²)': format_scientific(mat['E_cr']) if mat.get('E_cr') else '-',
            'ν₀ (初期ポアソン比)': mat.get('nu0') if mat.get('nu0') else '-',
            'ν_cr (限界ポアソン比)': mat.get('nu_cr') if mat.get('nu_cr') else '-',
            'τ_f (せん断強度)\n(kN/m²)': format_scientific(mat['tau_f'] / 1000) if mat.get('tau_f') else '-',
            'σ_t (引張強度)\n(kN/m²)': format_scientific(mat['sigma_t'] / 1000) if mat.get('sigma_t') else '-',
            'φ (内部摩擦角)\n(°)': mat['phi'] if mat.get('phi') else '-',
            'γ (単位体積重量)\n(kN/m³)': gamma,
            'K₀ (静止土圧係数)': mat['K0'] if mat.get('K0') else '-'
        })
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "材料名": st.column_config.TextColumn("材料名", width="large"),
        }
    )


def _display_mohr_coulomb_materials(materials: List[Dict[str, Any]]):
    """Mohr-Coulomb材料を表示"""
    df_data = []
    for mat in materials:
        gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
        c_val = mat['c'] if mat['c'] else 0
        c_display = "0.001" if c_val < 0.01 and c_val > 0 else format_scientific(c_val) if c_val else '-'
        phi_val = mat['phi'] if mat['phi'] else 0
        phi_display = "0.001" if phi_val < 0.01 and phi_val > 0 else str(int(phi_val)) if phi_val and phi_val == int(phi_val) else str(phi_val) if phi_val else '-'
        
        df_data.append({
            'ID': mat['id'],
            '材料名': mat['name'],
            'E (変形係数)\n(kN/m²)': format_scientific(mat['E']) if mat['E'] else '-',
            'ν (ポアソン比)': mat['nu'] if mat['nu'] else '-',
            'c (粘着力)\n(kN/m²)': c_display,
            'φ (内部摩擦角)\n(°)': phi_display,
            'γ (単位体積重量)\n(kN/m³)': gamma,
            'K₀ (静止土圧係数)': mat['K0'] if mat.get('K0') else '-'
        })
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "材料名": st.column_config.TextColumn("材料名", width="large"),
        }
    )


def _display_generic_materials(materials: List[Dict[str, Any]]):
    """汎用材料を表示"""
    df_data = []
    for mat in materials:
        gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
        df_data.append({
            'ID': mat['id'],
            '材料名': mat['name'],
            'E (変形係数)\n(kN/m²)': format_scientific(mat['E']) if mat['E'] else '-',
            'ν (ポアソン比)': mat['nu'] if mat['nu'] else '-',
            'γ (単位体積重量)\n(kN/m³)': gamma,
            'K₀ (静止土圧係数)': mat['K0'] if mat.get('K0') else '-'
        })
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "材料名": st.column_config.TextColumn("材料名", width="large"),
        }
    )


def display_analysis_settings(title: str, params: Dict[str, Any], nlparams: List[Dict[str, Any]]):
    """解析設定を表示"""
    st.subheader("⚙️ 解析設定")
    
    # タイトル
    if title:
        st.markdown(f"**解析タイトル**: {title}")
        st.markdown("---")
    
    # PARAMパラメータ
    if params:
        st.markdown("**PARAMパラメータ**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'units' in params:
                st.metric("単位系", params['units'])
        
        with col2:
            if 'autospc' in params:
                st.metric("AUTOSPC", params['autospc'])
        
        with col3:
            if 'nlsequential' in params:
                st.metric("NLSEQUENTIAL", params['nlsequential'])
    
    # NLPARM設定
    if nlparams:
        st.markdown("---")
        st.markdown("**非線形解析パラメータ (NLPARM)**")
        
        df_data = []
        for nlp in nlparams:
            df_data.append({
                'ID': nlp['id'],
                '増分数': nlp['ninc'],
                '解法': nlp['method'],
                '最大反復回数': nlp['maxiter'],
                '収束判定': nlp['conv']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "増分数": st.column_config.NumberColumn("増分数", width="small"),
                    "解法": st.column_config.TextColumn("解法", width="medium"),
                    "最大反復回数": st.column_config.NumberColumn("最大反復回数", width="small"),
                    "収束判定": st.column_config.NumberColumn("収束判定", width="small"),
                }
            )


def display_sets(sets: List[Dict[str, Any]]):
    """SET定義を表示"""
    st.subheader("📦 SET定義")
    
    if not sets:
        st.info("SET定義が見つかりませんでした。")
        return
    
    df_data = []
    for s in sets:
        df_data.append({
            'SET ID': s['id'],
            'コメント': s['comment'] if s['comment'] else '-',
            '定義': s['definition']
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "SET ID": st.column_config.NumberColumn("SET ID", width="small"),
            "コメント": st.column_config.TextColumn("コメント", width="medium"),
            "定義": st.column_config.TextColumn("定義", width="large"),
        }
    )


def display_stage_configs(stage_configs: List[Dict[str, Any]]):
    """ステージ設定を表示"""
    st.subheader("🔧 ステージ設定 (STGCONF)")
    
    if not stage_configs:
        st.info("ステージ設定が見つかりませんでした。")
        return
    
    df_data = []
    for sc in stage_configs:
        df_data.append({
            'ステージID': sc['id'],
            'パラメータ1': sc['param1'] if sc['param1'] else '-',
            'パラメータ2': sc['param2'] if sc['param2'] else '-',
            'パラメータ3': sc['param3'] if sc['param3'] else '-',
            'パラメータ4': sc['param4'] if sc['param4'] else '-'
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ステージID": st.column_config.NumberColumn("ステージID", width="small"),
            "パラメータ1": st.column_config.TextColumn("パラメータ1", width="small"),
            "パラメータ2": st.column_config.TextColumn("パラメータ2", width="small"),
            "パラメータ3": st.column_config.TextColumn("パラメータ3", width="small"),
            "パラメータ4": st.column_config.TextColumn("パラメータ4", width="small"),
        }
    )


def display_geoparams(geoparams: List[Dict[str, Any]]):
    """地盤解析パラメータを表示"""
    st.subheader("🌍 地盤解析パラメータ (GEOPARM)")
    
    if not geoparams:
        st.info("地盤解析パラメータが見つかりませんでした。")
        return
    
    df_data = []
    for gp in geoparams:
        df_data.append({
            'SUBCASE ID': gp['subcase_id'],
            'GEOPARM ID': gp['geoparm_id']
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "SUBCASE ID": st.column_config.NumberColumn("SUBCASE ID", width="small"),
            "GEOPARM ID": st.column_config.NumberColumn("GEOPARM ID", width="small"),
        }
    )


def display_boundary_conditions(boundary_conditions: Dict[str, Any]):
    """境界条件を表示"""
    st.subheader("🔒 境界条件 (SPC)")
    
    if not boundary_conditions:
        st.info("境界条件が見つかりませんでした。")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("SPC1定義数", f"{boundary_conditions['spc_count']:,}")
    with col2:
        st.metric("使用されているSPC ID数", len(boundary_conditions['spc_ids']))
    
    if boundary_conditions['spc_ids']:
        st.markdown("---")
        st.markdown("**SUBCASEで使用されているSPC ID**")
        
        df_data = []
        for spc in boundary_conditions['spc_ids']:
            df_data.append({
                'SPC ID': spc['spc_id'],
                'SUBCASE ID': spc['subcase_id']
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "SPC ID": st.column_config.NumberColumn("SPC ID", width="small"),
                "SUBCASE ID": st.column_config.NumberColumn("SUBCASE ID", width="small"),
            }
        )

