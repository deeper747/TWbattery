# config.py — HS Code definitions for Taiwan Battery Supply Chain Dashboard
# 台灣電池供應鏈進出口追蹤設定檔

# Taiwan 6-digit HS codes (Taiwan Customs uses 6-digit as base; 10-digit for full spec)
# Groups follow the U.S. Energy Trade Dashboard categorisation logic

HS_CODES = {
    "電池成品 (Batteries)": {
        "850760": {
            "tw_name": "鋰離子蓄電池",
            "en_name": "Lithium-Ion Batteries (incl. EV)",
            "tw_10digit": "8507.60.00.00-5",
            "note": "Includes both automotive and non-automotive; Taiwan does not sub-divide at 10-digit level",
        },
        "850790": {
            "tw_name": "蓄電池零件",
            "en_name": "Storage Battery Parts (non-lead-acid)",
            "tw_10digit": "8507.90.00.00-8",
            "note": "Modules, housings, terminals, etc.",
        },
    },
    "正極材料 (Cathode Materials)": {
        "283324": {
            "tw_name": "硫酸鎳",
            "en_name": "Nickel Sulphate",
            "tw_10digit": "2833.24.00.00",
            "note": "Key NMC/NCA precursor; NiSO4",
        },
        "283329": {
            "tw_name": "其他硫酸鹽（鈷／錳）",
            "en_name": "Other Sulphates (Co/Mn)",
            "tw_10digit": "2833.29.xx",
            "note": "Covers CoSO4 and MnSO4; Ni now tracked separately under 2833.24",
        },
        "282520": {
            "tw_name": "氧化鋰及氫氧化鋰",
            "en_name": "Lithium Oxides & Hydroxides",
            "tw_10digit": "2825.20.xx",
            "note": "Critical lithium compound",
        },
        "283691": {
            "tw_name": "碳酸鋰",
            "en_name": "Lithium Carbonate",
            "tw_10digit": "2836.91.xx",
            "note": "Used in LFP and NMC cathode",
        },
    },
    "負極材料 (Anode Materials)": {
        "250410": {
            "tw_name": "天然石墨（粉末）",
            "en_name": "Natural Graphite (powder/flakes)",
            "tw_10digit": "2504.10.xx",
            "note": "",
        },
        "380110": {
            "tw_name": "人造石墨",
            "en_name": "Artificial Graphite",
            "tw_10digit": "3801.10.00.00-1",
            "note": "Primary anode material",
        },
        "280300": {
            "tw_name": "炭黑",
            "en_name": "Carbon Black",
            "tw_10digit": "2803.00.00.00-9",
            "note": "Conductive additive",
        },
    },
    "電解液與功能化學品 (Electrolyte & Functional Chemicals)": {
        "382499": {
            "tw_name": "其他未列名化學品",
            "en_name": "Other Chemical Products (electrolyte precursors)",
            "tw_10digit": "3824.99.90.00-7",
            "note": "Broadest category; includes LiPF6 precursors and inorganic mixtures",
        },
    },
    "金屬原料 (Metals & Minerals)": {
        "750210": {
            "tw_name": "未合金鎳（未加工）",
            "en_name": "Nickel, Unwrought, Not Alloyed",
            "tw_10digit": "7502.10.00.00-3",
            "note": "",
        },
        "281820": {
            "tw_name": "氧化鋁（非人工剛玉）",
            "en_name": "Aluminum Oxide (excl. artificial corundum)",
            "tw_10digit": "2818.20.00.00-2",
            "note": "Separator coating and ceramics",
        },
        "810520": {
            "tw_name": "鈷粉",
            "en_name": "Cobalt Powders",
            "tw_10digit": "8105.20.xx",
            "note": "Also appears in recycling streams",
        },
    },
    "封裝材料 (Packaging Materials)": {
        "390120": {
            "tw_name": "高密度聚乙烯 (HDPE)",
            "en_name": "Polyethylene (spec. gravity ≥ 0.94)",
            "tw_10digit": "3901.20.00.00-4",
            "note": "Separator and packaging material",
        },
        "390210": {
            "tw_name": "聚丙烯 (PP)",
            "en_name": "Polypropylene",
            "tw_10digit": "3902.10.00.00-3",
            "note": "Separator and packaging material",
        },
    },
}

# Flat lookup: hs_6digit -> display info
HS_FLAT = {}
for category, codes in HS_CODES.items():
    for hs6, info in codes.items():
        HS_FLAT[hs6] = {**info, "category": category}

# All 6-digit codes as a list (for portal queries)
ALL_HS6 = list(HS_FLAT.keys())

# Countries of interest for China-dependency analysis
COUNTRIES_OF_INTEREST = {
    "中國大陸": "China (Mainland)",
    "香港": "Hong Kong",
    "日本": "Japan",
    "韓國": "South Korea",
    "美國": "United States",
    "德國": "Germany",
    "印尼": "Indonesia",
    "澳大利亞": "Australia",
}

CHINA_LABELS = {"中國大陸", "中国大陆", "China", "CHN"}
