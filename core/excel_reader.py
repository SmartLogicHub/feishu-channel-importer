"""Excel 文件读取与预览"""
import pandas as pd


def read_excel_preview(
    file_path: str,
    preview_rows: int = 10,
    forward_fill: bool = False,
    sheet_name: str | None = None,
) -> dict:
    """
    读取 Excel 文件并返回预览信息
    返回: {
        "headers": ["列1", "列2", ...],
        "rows": [["值1", "值2"], ...],
        "total_rows": 1000,
        "sheet_names": ["Sheet1", ...]
    }
    """
    with pd.ExcelFile(file_path) as workbook:
        sheet_names = list(workbook.sheet_names)
        selected_sheet = sheet_name or sheet_names[0]
        if selected_sheet not in sheet_names:
            raise ValueError(f"Excel 中不存在工作表：{selected_sheet}")
        df = pd.read_excel(workbook, sheet_name=selected_sheet)

    # 自动填充合并单元格（仅填充品牌/第一列，避免污染其他列数据）
    if forward_fill:
        first_col = df.columns[0]
        df[first_col] = df[first_col].ffill()

    headers = df.columns.tolist()
    # 注意：不用 dtype=str，先用 fillna 再转字符串
    df_preview = df.head(preview_rows).fillna("")
    rows = df_preview.values.tolist()

    # 将 numpy 类型转为 Python 原生类型
    rows = [[str(cell) for cell in row] for row in rows]

    return {
        "headers": headers,
        "rows": rows,
        "total_rows": len(df),
        "sheet_names": sheet_names,
        "selected_sheet": selected_sheet,
    }


def read_excel_all(file_path: str, sheet_name: str = None, forward_fill: bool = False) -> list[dict]:
    """
    读取 Excel 全部数据，返回字典列表
    [{"列1": "值1", "列2": "值2"}, ...]

    forward_fill: 是否自动向下填充合并单元格的空值
    """
    if sheet_name:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    else:
        df = pd.read_excel(file_path)

    # 自动填充合并单元格（仅填充品牌/第一列，避免污染其他列数据）
    if forward_fill:
        first_col = df.columns[0]
        df[first_col] = df[first_col].ffill()

    # 注意：不用 dtype=str，否则 NaN 会变成字符串 "nan"，导致 fillna 失效
    df = df.fillna("")
    df = df.astype(str)
    df = df.replace("nan", "")  # 安全兜底
    return df.to_dict(orient="records")
