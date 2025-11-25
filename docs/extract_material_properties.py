#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mecファイルから物性値を抽出してPDFを生成するスクリプト
"""

import re
import sys
import os
import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

def format_scientific(val):
    """数値を指数表記でフォーマット"""
    try:
        num = float(val)
        if num == 0:
            return "0"
        if abs(num) >= 1000:
            exp = 0
            while abs(num) >= 10:
                num /= 10
                exp += 1
            return f"{num:.2f}×10<sup>{exp}</sup>"
        elif abs(num) < 0.01 and num != 0:
            exp = 0
            while abs(num) < 1:
                num *= 10
                exp -= 1
            return f"{num:.2f}×10<sup>{exp}</sup>"
        else:
            if num == int(num):
                return str(int(num))
            return f"{num:.3f}".rstrip('0').rstrip('.')
    except:
        return str(val)

def parse_mec_file(mec_path):
    """mecファイルから材料データを抽出"""
    with open(mec_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    materials = []
    properties = []
    subcases = []
    model_info = {
        'nodes': len(re.findall(r'^GRID\s', content, re.MULTILINE)),
        'elements': len(re.findall(r'^(?:CHEXA|CPENTA|CPYRAM|CTETRA|CQUAD4|CTRIA3)\s', content, re.MULTILINE)),
        'spc_count': len(re.findall(r'^SPC1\s', content, re.MULTILINE)),
    }

    # 解析ステップ（SUBCASE）を抽出
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

    # 荷重情報を抽出
    loads = {
        'grav': [],
        'pload4': {},
        'load_combinations': []
    }

    # 重力荷重（GRAV）
    grav_pattern = r'GRAV\s*,\s*(\d+)\s*,\s*\d+\s*,\s*[\d.eE+-]+\s*,\s*[\d.eE+-]+\s*,\s*[\d.eE+-]+\s*,\s*([\d.eE+-]+)'
    for match in re.finditer(grav_pattern, content):
        grav_id = int(match.group(1))
        grav_value = abs(float(match.group(2)))
        loads['grav'].append({'id': grav_id, 'value': grav_value})

    # 面圧荷重（PLOAD4）- IDごとに集計
    pload4_pattern = r'PLOAD4\s*,\s*(\d+)\s*,\s*\d+\s*,\s*([\d.eE+-]+)'
    for match in re.finditer(pload4_pattern, content):
        pload_id = int(match.group(1))
        pressure = float(match.group(2))
        if pload_id not in loads['pload4']:
            loads['pload4'][pload_id] = {'pressure': pressure, 'count': 0}
        loads['pload4'][pload_id]['count'] += 1

    # 荷重組合せ（LOAD）
    load_comb_pattern = r'LOAD\s*,\s*(\d+)\s*,([^$\n]+)'
    for match in re.finditer(load_comb_pattern, content):
        load_id = int(match.group(1))
        components = match.group(2).strip()
        loads['load_combinations'].append({'id': load_id, 'components': components})

    # プロパティ定義を抽出
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

    # 材料定義ブロックを検索
    pattern = r'\$\$ Name of Material \[ID:(\d+)\] <([^>]+)>\s*\n\$\$ Type of Material <([^>]+)>'
    matches = list(re.finditer(pattern, content))

    for i, match in enumerate(matches):
        mat_id = int(match.group(1))
        mat_name = match.group(2)
        mat_type = match.group(3)

        # このマッチから次のマッチまでの範囲を取得
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
            'E0': None,  # 初期変形係数
            'E_cr': None,  # 限界変形係数
            'nu0': None,  # 初期ポアソン比
            'nu_cr': None,  # 限界ポアソン比
            'tau_f': None,  # せん断強度
            'sigma_t': None,  # 引張強度
        }

        # コメントから値を抽出
        e_match = re.search(r'\$\$ Elastic Modulus <([^>]+)>', block)
        if e_match:
            material['E'] = float(e_match.group(1))

        nu_match = re.search(r"\$\$ Poisson's ratio <([^>]+)>", block)
        if nu_match:
            material['nu'] = float(nu_match.group(1))

        # 質量密度から単位体積重量を計算（コメントから直接取得）
        # γの値はコメントには直接ないので、property.xlsの値を使用するか、
        # 密度から計算する必要がある

        # 質量密度からγを計算
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
            # 初期変形係数
            e0_match = re.search(r'\$\$ Initial Modulus of deformability <([^>]+)>', block)
            if e0_match:
                material['E0'] = float(e0_match.group(1))
                material['E'] = material['E0']  # 弾性係数としても設定

            # 限界変形係数
            ecr_match = re.search(r'\$\$ Critical Modulus of deformability <([^>]+)>', block)
            if ecr_match:
                material['E_cr'] = float(ecr_match.group(1))

            # 初期ポアソン比
            nu0_match = re.search(r"\$\$ Initial Poisson's Ratio <([^>]+)>", block)
            if nu0_match:
                material['nu0'] = float(nu0_match.group(1))
                material['nu'] = material['nu0']

            # 限界ポアソン比
            nucr_match = re.search(r"\$\$ Critical Poisson's Ratio <([^>]+)>", block)
            if nucr_match:
                material['nu_cr'] = float(nucr_match.group(1))

            # せん断強度
            tau_match = re.search(r'\$\$ Shear Strength <([^>]+)>', block)
            if tau_match:
                material['tau_f'] = float(tau_match.group(1))

            # 引張強度
            sigma_match = re.search(r'\$\$ Tensile Strength <([^>]+)>', block)
            if sigma_match:
                material['sigma_t'] = float(sigma_match.group(1))

            # 内部摩擦角
            phi_match = re.search(r'\$\$ Frictional Angle <([^>]+)>', block)
            if phi_match:
                material['phi'] = float(phi_match.group(1))

        # Mohr-Coulomb材料の場合
        if 'Mohr-Coulomb' in mat_type:
            c_match = re.search(r'\$\$ Cohesion <([^>]+)>', block)
            if c_match:
                c_val = float(c_match.group(1))
                # 単位変換: N/m² → kN/m²
                material['c'] = c_val / 1000 if c_val > 100 else c_val

            phi_match = re.search(r'\$\$ Frictional Angle <([^>]+)>', block)
            if phi_match:
                material['phi'] = float(phi_match.group(1))

        # MAT1行からも値を取得（より正確）
        mat1_match = re.search(r'MAT1\s*,\s*' + str(mat_id) + r'\s*,\s*([^,]+)\s*,\s*[^,]*\s*,\s*([^,]+)\s*,\s*([^,]+)', block)
        if mat1_match:
            material['E'] = float(mat1_match.group(1).strip())
            material['nu'] = float(mat1_match.group(2).strip())
            # 密度から単位体積重量を推定（近似値）
            density = float(mat1_match.group(3).strip())
            # 単位系による変換が必要な場合がある

        # MATEP2H行からMohr-Coulombパラメータを取得
        matep_match = re.search(r'MATEP2H\s*,\s*' + str(mat_id) + r'[^$]+', block)
        if matep_match:
            matep_block = matep_match.group(0)
            # PERFECT, φ, PERFECT, c, PERFECT, dilatancy の形式
            values = re.findall(r'PERFECT\s*,\s*([\d.eE+-]+)', matep_block)
            if len(values) >= 2:
                material['phi'] = float(values[0])
                c_val = float(values[1])
                material['c'] = c_val / 1000 if c_val > 100 else c_val

        # MATGEO行からK0を取得
        matgeo_match = re.search(r'MATGEO\s*,\s*' + str(mat_id) + r'[^$]+', block)
        if matgeo_match:
            matgeo_block = matgeo_match.group(0)
            # K0値を探す（複数行にまたがる場合がある）
            k0_values = re.findall(r',\s*(0\.\d+)\s*,\s*\1\s*,\s*\1', matgeo_block)
            if k0_values:
                material['K0'] = float(k0_values[0])

        materials.append(material)

    return materials, properties, model_info, subcases, loads

def get_gamma_from_density(density):
    """質量密度から単位体積重量を計算（単位系に依存）"""
    # mecファイルの密度値から直接γを計算するのは単位系の問題で困難
    # 必要に応じてproperty.xlsなど別ソースから取得する必要がある
    return None

def generate_html(materials, properties, model_info, subcases, loads, title):
    """HTMLテーブルを生成"""

    # 材料をタイプ別にグループ化
    material_groups = {}
    for mat in materials:
        mat_type = mat['type']
        if mat_type not in material_groups:
            material_groups[mat_type] = []
        material_groups[mat_type].append(mat)

    # プロパティを分類
    shell_props = [p for p in properties if p['type'] == 'Shell']
    solid_props = [p for p in properties if p['type'] == 'Solid']

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>物性値一覧表</title>
    <style>
        @page {{ size: A4 landscape; margin: 15mm; }}
        body {{ font-family: 'Meiryo', 'MS Gothic', sans-serif; font-size: 10pt; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; font-size: 16pt; margin-bottom: 5px; }}
        h2 {{ text-align: center; font-size: 11pt; font-weight: normal; margin-bottom: 20px; color: #555; }}
        h3 {{ font-size: 12pt; margin: 15px 0 8px 0; color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 9pt; }}
        th, td {{ border: 1px solid #333; padding: 6px 8px; text-align: center; vertical-align: middle; }}
        th {{ background-color: #3a4f6f; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f5f5f5; }}
        .note {{ font-size: 8pt; color: #666; margin-top: 10px; }}
    </style>
</head>
<body>
    <h1>物性値一覧表</h1>
    <h2>{title}</h2>
'''

    # モデル情報（最初に表示）
    html += f'''
    <h3>■ モデル情報</h3>
    <table>
        <tr>
            <th>項目</th>
            <th>値</th>
        </tr>
        <tr>
            <td>節点数</td>
            <td>{model_info['nodes']:,}</td>
        </tr>
        <tr>
            <td>要素数</td>
            <td>{model_info['elements']:,}</td>
        </tr>
        <tr>
            <td>荷重ケース数</td>
            <td>{len(subcases)}</td>
        </tr>
        <tr>
            <td>拘束条件数</td>
            <td>{model_info['spc_count']:,}</td>
        </tr>
        <tr>
            <td>解析ステップ数</td>
            <td>{len(subcases)}</td>
        </tr>
    </table>
'''

    # 解析ステップテーブル
    if subcases:
        html += '''
    <h3>■ 解析ステップ</h3>
    <table>
        <tr>
            <th>ステップ</th>
            <th>ラベル</th>
            <th>荷重ID</th>
            <th>拘束ID</th>
            <th>前ステップ</th>
        </tr>
'''
        for sc in subcases:
            load_display = sc['load'] if sc['load'] else '-'
            spc_display = sc['spc'] if sc['spc'] else '-'
            use_stage_display = sc['use_stage'] if sc['use_stage'] else '-'
            html += f'''        <tr>
            <td>{sc['id']}</td>
            <td style="text-align: left;">{sc['label']}</td>
            <td>{load_display}</td>
            <td>{spc_display}</td>
            <td>{use_stage_display}</td>
        </tr>
'''
        html += '    </table>\n'

    # 荷重情報テーブル
    if loads['grav'] or loads['pload4']:
        html += '''
    <h3>■ 荷重情報</h3>
    <table>
        <tr>
            <th>荷重タイプ</th>
            <th>ID</th>
            <th>値</th>
            <th>要素数</th>
        </tr>
'''
        # 重力荷重
        for grav in loads['grav']:
            html += f'''        <tr>
            <td>重力荷重 (GRAV)</td>
            <td>{grav['id']}</td>
            <td>{format_scientific(grav['value'])} (加速度)</td>
            <td>-</td>
        </tr>
'''
        # 面圧荷重
        for pload_id, pload_data in sorted(loads['pload4'].items()):
            pressure_kn = pload_data['pressure'] / 1000  # N/m² → kN/m²
            html += f'''        <tr>
            <td>面圧荷重 (PLOAD4)</td>
            <td>{pload_id}</td>
            <td>{pressure_kn:.1f} kN/m²</td>
            <td>{pload_data['count']:,}</td>
        </tr>
'''
        html += '    </table>\n'

    # シェルプロパティテーブル
    if shell_props:
        html += '''
    <h3>■ シェルプロパティ</h3>
    <table>
        <tr>
            <th>プロパティ名</th>
            <th>ID</th>
            <th>タイプ</th>
            <th>厚さ (m)</th>
            <th>材料ID</th>
        </tr>
'''
        for prop in shell_props:
            thickness = prop['thickness'] if prop['thickness'] else '-'
            mat_id = prop['material_id'] if prop['material_id'] else '-'
            html += f'''        <tr>
            <td>{prop['name']}</td>
            <td>{prop['id']}</td>
            <td>{prop['type']}</td>
            <td>{thickness}</td>
            <td>{mat_id}</td>
        </tr>
'''
        html += '    </table>\n'

    # ソリッドプロパティテーブル
    if solid_props:
        html += '''
    <h3>■ ソリッドプロパティ</h3>
    <table>
        <tr>
            <th>プロパティ名</th>
            <th>ID</th>
            <th>タイプ</th>
            <th>材料ID</th>
        </tr>
'''
        for prop in solid_props:
            mat_id = prop['material_id'] if prop['material_id'] else '-'
            html += f'''        <tr>
            <td>{prop['name']}</td>
            <td>{prop['id']}</td>
            <td>{prop['type']}</td>
            <td>{mat_id}</td>
        </tr>
'''
        html += '    </table>\n'

    # 材料テーブル（タイプ別に異なる構造）
    for mat_type, mats in material_groups.items():
        if '弾性' in mat_type:
            # 弾性材料テーブル
            html += f'''
    <h3>■ 材料（{mat_type}）</h3>
    <table>
        <tr>
            <th>材料名</th>
            <th>ID</th>
            <th>弾性係数 E<br>(kN/m²)</th>
            <th>ポアソン比<br>ν</th>
            <th>単位体積重量<br>γ (kN/m³)</th>
        </tr>
'''
            for mat in mats:
                gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
                e_display = format_scientific(mat['E']) if mat['E'] else '-'
                nu_display = mat['nu'] if mat['nu'] else '-'
                html += f'''        <tr>
            <td>{mat['name']}</td>
            <td>{mat['id']}</td>
            <td>{e_display}</td>
            <td>{nu_display}</td>
            <td>{gamma}</td>
        </tr>
'''
            html += '    </table>\n'

        elif 'D-min' in mat_type:
            # D-min材料テーブル
            html += f'''
    <h3>■ 材料（{mat_type}）</h3>
    <table>
        <tr>
            <th>材料名</th>
            <th>ID</th>
            <th>初期変形係数<br>E₀ (kN/m²)</th>
            <th>限界変形係数<br>E_cr (kN/m²)</th>
            <th>初期ν₀</th>
            <th>限界ν_cr</th>
            <th>せん断強度<br>τ_f (kN/m²)</th>
            <th>引張強度<br>σ_t (kN/m²)</th>
            <th>φ (°)</th>
            <th>γ (kN/m³)</th>
            <th>K₀</th>
        </tr>
'''
            for mat in mats:
                gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
                e0_display = format_scientific(mat['E0']) if mat.get('E0') else '-'
                ecr_display = format_scientific(mat['E_cr']) if mat.get('E_cr') else '-'
                nu0_display = mat.get('nu0') if mat.get('nu0') else '-'
                nucr_display = mat.get('nu_cr') if mat.get('nu_cr') else '-'
                tau_display = format_scientific(mat['tau_f'] / 1000) if mat.get('tau_f') else '-'
                sigma_display = format_scientific(mat['sigma_t'] / 1000) if mat.get('sigma_t') else '-'
                phi_display = mat['phi'] if mat.get('phi') else '-'
                k0_display = mat['K0'] if mat.get('K0') else '-'
                html += f'''        <tr>
            <td>{mat['name']}</td>
            <td>{mat['id']}</td>
            <td>{e0_display}</td>
            <td>{ecr_display}</td>
            <td>{nu0_display}</td>
            <td>{nucr_display}</td>
            <td>{tau_display}</td>
            <td>{sigma_display}</td>
            <td>{phi_display}</td>
            <td>{gamma}</td>
            <td>{k0_display}</td>
        </tr>
'''
            html += '    </table>\n'

        elif 'Mohr-Coulomb' in mat_type:
            # Mohr-Coulomb材料テーブル
            html += f'''
    <h3>■ 材料（{mat_type}）</h3>
    <table>
        <tr>
            <th>材料名</th>
            <th>ID</th>
            <th>弾性係数 E<br>(kN/m²)</th>
            <th>ポアソン比<br>ν</th>
            <th>粘着力 c<br>(kN/m²)</th>
            <th>内部摩擦角<br>φ (°)</th>
            <th>単位体積重量<br>γ (kN/m³)</th>
            <th>K₀</th>
        </tr>
'''
            for mat in mats:
                gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
                c_val = mat['c'] if mat['c'] else 0
                c_display = "0.001" if c_val < 0.01 and c_val > 0 else format_scientific(c_val) if c_val else '-'
                phi_val = mat['phi'] if mat['phi'] else 0
                phi_display = "0.001" if phi_val < 0.01 and phi_val > 0 else str(int(phi_val)) if phi_val and phi_val == int(phi_val) else str(phi_val) if phi_val else '-'
                k0_display = mat['K0'] if mat['K0'] else '-'
                e_display = format_scientific(mat['E']) if mat['E'] else '-'
                nu_display = mat['nu'] if mat['nu'] else '-'
                html += f'''        <tr>
            <td>{mat['name']}</td>
            <td>{mat['id']}</td>
            <td>{e_display}</td>
            <td>{nu_display}</td>
            <td>{c_display}</td>
            <td>{phi_display}</td>
            <td>{gamma}</td>
            <td>{k0_display}</td>
        </tr>
'''
            html += '    </table>\n'

        else:
            # その他の材料タイプ（汎用テーブル）
            html += f'''
    <h3>■ 材料（{mat_type}）</h3>
    <table>
        <tr>
            <th>材料名</th>
            <th>ID</th>
            <th>弾性係数 E<br>(kN/m²)</th>
            <th>ポアソン比<br>ν</th>
            <th>単位体積重量<br>γ (kN/m³)</th>
            <th>K₀</th>
        </tr>
'''
            for mat in mats:
                gamma = round(mat['gamma'], 1) if mat.get('gamma') else '-'
                e_display = format_scientific(mat['E']) if mat['E'] else '-'
                nu_display = mat['nu'] if mat['nu'] else '-'
                k0_display = mat['K0'] if mat.get('K0') else '-'
                html += f'''        <tr>
            <td>{mat['name']}</td>
            <td>{mat['id']}</td>
            <td>{e_display}</td>
            <td>{nu_display}</td>
            <td>{gamma}</td>
            <td>{k0_display}</td>
        </tr>
'''
            html += '    </table>\n'

    html += '''
    <p class="note">※ D-min: 電力中央研究所法による非線形弾性モデル</p>
</body>
</html>
'''
    return html

def select_file_dialog():
    """ファイル選択ダイアログを表示"""
    try:
        root = tk.Tk()
        root.withdraw()  # メインウィンドウを非表示
        root.attributes('-topmost', True)  # ダイアログを最前面に

        file_path = filedialog.askopenfilename(
            title='mecファイルを選択',
            filetypes=[
                ('MECファイル', '*.mec'),
                ('すべてのファイル', '*.*')
            ]
        )

        root.destroy()
        return file_path
    except Exception as e:
        print(f"ダイアログ表示エラー: {e}")
        print("ファイルパスを直接入力してください:")
        return input().strip()

def main():
    parser = argparse.ArgumentParser(description='mecファイルから物性値を抽出してPDFを生成')
    parser.add_argument('mec_file', nargs='?', help='入力mecファイルのパス（省略時はダイアログ表示）')
    parser.add_argument('-o', '--output', help='出力PDFファイルのパス（省略時は自動生成）')
    parser.add_argument('--html-only', action='store_true', help='HTMLのみ生成（PDF変換しない）')

    args = parser.parse_args()

    # ファイルが指定されていない場合はダイアログを表示
    if args.mec_file:
        mec_path = Path(args.mec_file)
    else:
        selected_file = select_file_dialog()
        if not selected_file:
            print("ファイルが選択されませんでした")
            sys.exit(0)
        mec_path = Path(selected_file)

    if not mec_path.exists():
        print(f"エラー: ファイルが見つかりません: {mec_path}")
        sys.exit(1)

    # 出力パスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = mec_path.parent / 'PDF'
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f'物性値一覧_{mec_path.stem}.pdf'

    html_path = output_path.with_suffix('.html')

    # タイトルを生成
    title = mec_path.stem

    print(f"処理中: {mec_path}")

    # データを抽出
    materials, properties, model_info, subcases, loads = parse_mec_file(mec_path)
    print(f"抽出した材料数: {len(materials)}")
    print(f"抽出したプロパティ数: {len(properties)}")
    print(f"解析ステップ数: {len(subcases)}")
    print(f"荷重タイプ数: {len(loads['grav']) + len(loads['pload4'])}")
    print(f"節点数: {model_info['nodes']:,}, 要素数: {model_info['elements']:,}")

    # HTMLを生成
    html_content = generate_html(materials, properties, model_info, subcases, loads, title)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML生成完了: {html_path}")

    if args.html_only:
        print("HTMLのみ生成モード - PDF変換をスキップ")
        return

    # PDFに変換（Playwrightを使用）
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f'file://{html_path.absolute()}')
            page.pdf(
                path=str(output_path),
                format='A4',
                landscape=True,
                margin={'top': '15mm', 'right': '15mm', 'bottom': '15mm', 'left': '15mm'},
                print_background=True
            )
            browser.close()

        print(f"PDF生成完了: {output_path}")
    except ImportError:
        print("警告: Playwrightがインストールされていません")
        print("HTMLファイルをブラウザで開いてPDFに印刷してください")
        print(f"HTMLファイル: {html_path}")

if __name__ == '__main__':
    main()
