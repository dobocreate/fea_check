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


def display_subcases(subcases: List[Dict[str, Any]]):
    """解析ステップを表示"""
    st.subheader("🔄 解析ステップ")
    
    if not subcases:
        st.info("解析ステップが見つかりませんでした。")
        return
    
    df_data = []
    for sc in subcases:
        df_data.append({
            'ステップ': sc['id'],
            'ラベル': sc['label'],
            'SOL': sc['sol'] if sc['sol'] else '-',
            '荷重ID': sc['load'] if sc['load'] else '-',
            '拘束ID': sc['spc'] if sc['spc'] else '-',
            '前ステップ': sc['use_stage'] if sc['use_stage'] else '-'
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


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
        st.dataframe(df, use_container_width=True, hide_index=True)


def display_properties(properties: List[Dict[str, Any]]):
    """プロパティ情報を表示"""
    st.subheader("📐 プロパティ")
    
    if not properties:
        st.info("プロパティが見つかりませんでした。")
        return
    
    # シェルとソリッドに分類
    shell_props = [p for p in properties if p['type'] == 'Shell']
    solid_props = [p for p in properties if p['type'] == 'Solid']
    
    if shell_props:
        st.markdown("**シェルプロパティ**")
        df_data = []
        for prop in shell_props:
            df_data.append({
                'ID': prop['id'],
                'プロパティ名': prop['name'],
                'タイプ': prop['type'],
                '厚さ (m)': prop['thickness'] if prop['thickness'] else '-',
                '材料ID': prop['material_id'] if prop['material_id'] else '-'
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    if solid_props:
        st.markdown("**ソリッドプロパティ**")
        df_data = []
        for prop in solid_props:
            df_data.append({
                'ID': prop['id'],
                'プロパティ名': prop['name'],
                'タイプ': prop['type'],
                '材料ID': prop['material_id'] if prop['material_id'] else '-'
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


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
    st.dataframe(df, use_container_width=True, hide_index=True)


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
    st.dataframe(df, use_container_width=True, hide_index=True)


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
    st.dataframe(df, use_container_width=True, hide_index=True)


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
    st.dataframe(df, use_container_width=True, hide_index=True)


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
            st.dataframe(df, use_container_width=True, hide_index=True)

