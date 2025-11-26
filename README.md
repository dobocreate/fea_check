# FEA Check - FEANX MECファイル解析システム

FEANX で設定された解析条件(MECファイル)を視覚化し、設定内容を確認するためのWebアプリケーションです。

## 機能

- ✅ MECファイルのアップロードと解析
- ✅ モデル情報の表示(節点数、要素数、拘束条件数など)
- ✅ 解析設定の表示(PARAM、NLPARM)
- ✅ 解析ステップの統合表示(SUBCASE、STGCONF、GEOPARM)
- ✅ 荷重条件の表示(重力荷重、面圧荷重)
- ✅ プロパティの表示(Shell、Solid、Beam、Embedded Truss)
- ✅ 材料情報の表示(弾性、D-min、Mohr-Coulomb)
- ✅ 境界条件の表示(SPC)

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. アプリケーションの起動

```bash
streamlit run app.py
```

ブラウザが自動的に開き、`http://localhost:8501` でアプリケーションにアクセスできます。

## 使い方

1. **ファイルアップロード**: 左のサイドバーからMECファイルをドラッグ&ドロップ
2. **データ確認**: 各タブで解析設定を確認
   - 📊 モデル情報
   - ⚙️ 解析設定
   - 🔄 解析ステップ
   - ⚡ 荷重
   - 📐 プロパティ
   - 🧱 材料
   - 🔒 境界条件
3. **視覚化**: 材料プロパティ、解析ステップ、荷重条件などを表形式で表示

## プロジェクト構成

```
fea_check/
├── app.py                  # Streamlitアプリケーションのエントリーポイント
├── src/                    # ソースコードディレクトリ
│   ├── __init__.py
│   ├── parser.py           # MECファイル解析ロジック
│   └── ui_components.py    # Streamlit用UIコンポーネント
├── docs/                   # ドキュメントとサンプルファイル
│   ├── NXGT1-15-17-19_解析ケース-1.mec
│   ├── NXGT1-3-4-1-10-1_施工方向_No1からNo2.mec
│   └── extract_material_properties.py
├── test/                   # テストファイル
├── requirements.txt        # Python依存関係
└── README.md               # このファイル
```

## 今後の機能(予定)

- 🔜 自動チェック機能(設定値の検証)
- 🔜 PDF/Excelレポート出力
- 🔜 設定値の比較機能
- 🔜 履歴管理

## ライセンス

社内利用のみ
