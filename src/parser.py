#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MECファイルパーサー
FEANXのMECファイルから解析設定を抽出する
"""

import re
from typing import Dict, List, Any, Tuple


def parse_mec_file(file_content: str) -> Dict[str, Any]:
    """
    MECファイルの内容を解析して構造化データを返す
    
    Args:
        file_content: MECファイルの内容(文字列)
    
    Returns:
        解析結果を含む辞書
    """
    materials = _extract_materials(file_content)
    properties = _extract_properties(file_content)
    subcases = _extract_subcases(file_content)
    loads = _extract_loads(file_content)
    model_info = _extract_model_info(file_content)
    title = _extract_title(file_content)
    params = _extract_params(file_content)
    nlparams = _extract_nlparams(file_content)
    
    return {
        'materials': materials,
        'properties': properties,
        'subcases': subcases,
        'loads': loads,
        'model_info': model_info,
        'title': title,
        'params': params,
        'nlparams': nlparams
    }


def _extract_model_info(content: str) -> Dict[str, int]:
    """モデル情報を抽出"""
    return {
        'nodes': len(re.findall(r'^GRID\s', content, re.MULTILINE)),
        'elements': len(re.findall(r'^(?:CHEXA|CPENTA|CPYRAM|CTETRA|CQUAD4|CTRIA3)\s', content, re.MULTILINE)),
        'spc_count': len(re.findall(r'^SPC1\s', content, re.MULTILINE)),
    }


def _extract_subcases(content: str) -> List[Dict[str, Any]]:
    """解析ステップ(SUBCASE)を抽出"""
    subcases = []
    subcase_pattern = r'SUBCASE\s+(\d+)\s*\n((?:\s+[^\n]+\n)+)'
    
    for match in re.finditer(subcase_pattern, content):
        block = match.group(2)
        subcase = {
            'id': int(match.group(1)),
            'sol': None,
            'label': '',
            'load': None,
            'spc': None,
            'use_stage': None
        }
        
        sol_match = re.search(r'SOL\s+(\d+)', block)
        if sol_match:
            subcase['sol'] = int(sol_match.group(1))
        
        label_match = re.search(r'LABEL\s*=\s*([^\n]+)', block)
        if label_match:
            subcase['label'] = label_match.group(1).strip()
        
        load_match = re.search(r'LOAD\s*=\s*(\d+)', block)
        if load_match:
            subcase['load'] = int(load_match.group(1))
        
        spc_match = re.search(r'SPC\s*=\s*(\d+)', block)
        if spc_match:
            subcase['spc'] = int(spc_match.group(1))
        
        use_stage_match = re.search(r'USE\(STAGE\)\s*=\s*(\d+)', block)
        if use_stage_match:
            subcase['use_stage'] = int(use_stage_match.group(1))
        
        subcases.append(subcase)
    
    return subcases


def _extract_loads(content: str) -> Dict[str, Any]:
    """荷重情報を抽出"""
    loads = {
        'grav': [],
        'pload4': {},
        'load_combinations': []
    }
    
    # 重力荷重(GRAV)
    grav_pattern = r'GRAV\s*,\s*(\d+)\s*,\s*\d+\s*,\s*[\d.eE+-]+\s*,\s*[\d.eE+-]+\s*,\s*[\d.eE+-]+\s*,\s*([\d.eE+-]+)'
    for match in re.finditer(grav_pattern, content):
        grav_id = int(match.group(1))
        grav_value = abs(float(match.group(2)))
        loads['grav'].append({'id': grav_id, 'value': grav_value})
    
    # 面圧荷重(PLOAD4)
    pload4_pattern = r'PLOAD4\s*,\s*(\d+)\s*,\s*\d+\s*,\s*([\d.eE+-]+)'
    for match in re.finditer(pload4_pattern, content):
        pload_id = int(match.group(1))
        pressure = float(match.group(2))
        if pload_id not in loads['pload4']:
            loads['pload4'][pload_id] = {'pressure': pressure, 'count': 0}
        loads['pload4'][pload_id]['count'] += 1
    
    # 荷重組合せ(LOAD)
    load_comb_pattern = r'LOAD\s*,\s*(\d+)\s*,([^$\n]+)'
    for match in re.finditer(load_comb_pattern, content):
        load_id = int(match.group(1))
        components = match.group(2).strip()
        loads['load_combinations'].append({'id': load_id, 'components': components})
    
    return loads


def _extract_properties(content: str) -> List[Dict[str, Any]]:
    """プロパティ定義を抽出"""
    properties = []
    prop_pattern = r'\$\$ Name of Property \[ID:(\d+)\] <([^>]+)>\s*\n\$\$ Type of Property <([^>]+)>'
    prop_matches = list(re.finditer(prop_pattern, content))
    
    for i, match in enumerate(prop_matches):
        prop_id = int(match.group(1))
        prop_name = match.group(2)
        prop_type = match.group(3)
        
        start_pos = match.start()
        end_pos = prop_matches[i + 1].start() if i + 1 < len(prop_matches) else len(content)
        block = content[start_pos:end_pos]
        
        prop = {
            'id': prop_id,
            'name': prop_name,
            'type': prop_type,
            'thickness': None,
            'material_id': None
        }
        
        # シェル厚さを抽出
        thickness_match = re.search(r'\$\$ Thickness <([^>]+)>', block)
        if thickness_match:
            prop['thickness'] = float(thickness_match.group(1))
        
        # 材料IDを抽出
        mat_id_match = re.search(r'\$\$ Material ID <([^>]+)>', block)
        if mat_id_match:
            prop['material_id'] = int(mat_id_match.group(1))
        
        properties.append(prop)
    
    return properties


def _extract_materials(content: str) -> List[Dict[str, Any]]:
    """材料定義を抽出"""
    materials = []
    pattern = r'\$\$ Name of Material \[ID:(\d+)\] <([^>]+)>\s*\n\$\$ Type of Material <([^>]+)>'
    matches = list(re.finditer(pattern, content))
    
    for i, match in enumerate(matches):
        mat_id = int(match.group(1))
        mat_name = match.group(2)
        mat_type = match.group(3)
        
        start_pos = match.start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[start_pos:end_pos]
        
        material = {
            'id': mat_id,
            'name': mat_name,
            'type': mat_type,
            'E': None,
            'nu': None,
            'gamma': None,
            'c': None,
            'phi': None,
            'K0': None,
            # D-min用パラメータ
            'E0': None,
            'E_cr': None,
            'nu0': None,
            'nu_cr': None,
            'tau_f': None,
            'sigma_t': None,
        }
        
        # 弾性係数
        e_match = re.search(r'\$\$ Elastic Modulus <([^>]+)>', block)
        if e_match:
            material['E'] = float(e_match.group(1))
        
        # ポアソン比
        nu_match = re.search(r"\$\$ Poisson's ratio <([^>]+)>", block)
        if nu_match:
            material['nu'] = float(nu_match.group(1))
        
        # 質量密度から単位体積重量を計算
        density_match = re.search(r'\$\$ Mass density <([^>]+)>', block)
        if density_match:
            mass_density = float(density_match.group(1))
            # γ = ρ × g × 10¹⁵ (単位系: M-N-J-SEC)
            material['gamma'] = mass_density * 9.80665e15
        
        # K0
        k0_match = re.search(r'\$\$ K0 <([^>]+)>', block)
        if k0_match:
            material['K0'] = float(k0_match.group(1))
        
        # D-min材料の場合
        if 'D-min' in mat_type:
            e0_match = re.search(r'\$\$ Initial Modulus of deformability <([^>]+)>', block)
            if e0_match:
                material['E0'] = float(e0_match.group(1))
                material['E'] = material['E0']
            
            ecr_match = re.search(r'\$\$ Critical Modulus of deformability <([^>]+)>', block)
            if ecr_match:
                material['E_cr'] = float(ecr_match.group(1))
            
            nu0_match = re.search(r"\$\$ Initial Poisson's Ratio <([^>]+)>", block)
            if nu0_match:
                material['nu0'] = float(nu0_match.group(1))
                material['nu'] = material['nu0']
            
            nucr_match = re.search(r"\$\$ Critical Poisson's Ratio <([^>]+)>", block)
            if nucr_match:
                material['nu_cr'] = float(nucr_match.group(1))
            
            tau_match = re.search(r'\$\$ Shear Strength <([^>]+)>', block)
            if tau_match:
                material['tau_f'] = float(tau_match.group(1))
            
            sigma_match = re.search(r'\$\$ Tensile Strength <([^>]+)>', block)
            if sigma_match:
                material['sigma_t'] = float(sigma_match.group(1))
            
            phi_match = re.search(r'\$\$ Frictional Angle <([^>]+)>', block)
            if phi_match:
                material['phi'] = float(phi_match.group(1))
        
        # Mohr-Coulomb材料の場合
        if 'Mohr-Coulomb' in mat_type:
            c_match = re.search(r'\$\$ Cohesion <([^>]+)>', block)
            if c_match:
                c_val = float(c_match.group(1))
                material['c'] = c_val / 1000 if c_val > 100 else c_val
            
            phi_match = re.search(r'\$\$ Frictional Angle <([^>]+)>', block)
            if phi_match:
                material['phi'] = float(phi_match.group(1))
        
        # MAT1行からも値を取得
        mat1_match = re.search(r'MAT1\s*,\s*' + str(mat_id) + r'\s*,\s*([^,]+)\s*,\s*[^,]*\s*,\s*([^,]+)\s*,\s*([^,]+)', block)
        if mat1_match:
            material['E'] = float(mat1_match.group(1).strip())
            material['nu'] = float(mat1_match.group(2).strip())
        
        # MATEP2H行からMohr-Coulombパラメータを取得
        matep_match = re.search(r'MATEP2H\s*,\s*' + str(mat_id) + r'[^$]+', block)
        if matep_match:
            matep_block = matep_match.group(0)
            values = re.findall(r'PERFECT\s*,\s*([\d.eE+-]+)', matep_block)
            if len(values) >= 2:
                material['phi'] = float(values[0])
                c_val = float(values[1])
                material['c'] = c_val / 1000 if c_val > 100 else c_val
        
        # MATGEO行からK0を取得
        matgeo_match = re.search(r'MATGEO\s*,\s*' + str(mat_id) + r'[^$]+', block)
        if matgeo_match:
            matgeo_block = matgeo_match.group(0)
            k0_values = re.findall(r',\s*(0\.\d+)\s*,\s*\1\s*,\s*\1', matgeo_block)
            if k0_values:
                material['K0'] = float(k0_values[0])
        
        materials.append(material)
    
    return materials


def _extract_title(content: str) -> str:
    """解析タイトルを抽出"""
    title_match = re.search(r'TITLE\s*=\s*([^\n]+)', content)
    if title_match:
        return title_match.group(1).strip()
    return ""


def _extract_params(content: str) -> Dict[str, Any]:
    """PARAMパラメータを抽出"""
    params = {}
    
    # 単位系
    units_match = re.search(r'PARAM,\s*UNITS,\s*([^\n,]+)', content)
    if units_match:
        params['units'] = units_match.group(1).strip()
    
    # その他の重要なパラメータ
    param_patterns = {
        'autospc': r'PARAM,\s*AUTOSPC,\s*([^\n,]+)',
        'adjustelemshape': r'PARAM,\s*ADJUSTELEMSHAPE,\s*([^\n,]+)',
        'nlsequential': r'PARAM,\s*NLSEQUENTIAL,\s*([^\n,]+)',
    }
    
    for key, pattern in param_patterns.items():
        match = re.search(pattern, content)
        if match:
            params[key] = match.group(1).strip()
    
    return params


def _extract_nlparams(content: str) -> List[Dict[str, Any]]:
    """NLPARM(非線形解析パラメータ)を抽出"""
    nlparams = []
    
    # NLPARM行を検索
    nlparm_pattern = r'NLPARM\s*,\s*(\d+)\s*,\s*(\d+)\s*,[^,]*,\s*([^,\s]+)\s*,\s*(\d+)\s*,\s*(\d+)'
    
    for match in re.finditer(nlparm_pattern, content):
        nlparam = {
            'id': int(match.group(1)),
            'ninc': int(match.group(2)),  # 増分数
            'method': match.group(3).strip(),  # 解法(SEMI, AUTO等)
            'maxiter': int(match.group(4)),  # 最大反復回数
            'conv': int(match.group(5))  # 収束判定
        }
        nlparams.append(nlparam)
    
    return nlparams

