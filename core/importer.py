"""导入编排器"""
from .excel_reader import read_excel_all
from .feishu_client import FeishuClient
from .value_normalizer import normalize_for_target


def run_import(
    file_path: str,
    sheet_name: str,
    app_id: str,
    app_secret: str,
    app_token: str,
    table_id: str,
    field_mapping: dict,
    forward_fill: bool = False,
    field_types: dict = None,
    progress_callback=None,
) -> int:
    """
    执行完整导入流程，返回成功导入的记录数

    Args:
        file_path: Excel 文件路径
        sheet_name: 工作表名称
        app_id: 飞书应用 App ID
        app_secret: 飞书应用 App Secret
        app_token: 多维表格 token
        table_id: 数据表 ID
        field_mapping: {"excel列名": "飞书字段名"}
        forward_fill: 是否自动向下填充合并单元格
        field_types: {"飞书字段名": 字段类型值, ...}
        progress_callback: def callback(current: int, total: int, message: str)
    """
    # 1. 读取 Excel 数据
    if progress_callback:
        progress_callback(0, 0, "正在读取 Excel 文件...")
    raw_data = read_excel_all(file_path, sheet_name, forward_fill=forward_fill)

    if not raw_data:
        raise Exception("Excel 文件中没有数据")

    # 2. 字段映射
    if progress_callback:
        progress_callback(0, len(raw_data), "正在转换数据格式...")
    records = []
    for row in raw_data:
        mapped = {}
        for excel_col, feishu_field_name in field_mapping.items():
            if excel_col in row:
                value = row[excel_col]
                target_type = (field_types or {}).get(feishu_field_name)
                if target_type is not None:
                    value = normalize_for_target(value, int(target_type))
                mapped[feishu_field_name] = value
        records.append(mapped)

    # 3. 初始化飞书客户端并批量写入
    client = FeishuClient(app_id, app_secret)

    if progress_callback:
        progress_callback(0, len(records), "正在写入飞书多维表格...")

    total = client.batch_create_records(app_token, table_id, records)

    if progress_callback:
        progress_callback(total, len(records),
                          f"导入完成！成功写入 {total} 条记录")

    return total
