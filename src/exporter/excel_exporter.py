from pathlib import Path
from typing import List
import pandas as pd
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from src.models.result import Result
from src.utils.logger import logger


class ExcelExporter:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self, results: List[Result], filename: str = "evaluation_results.xlsx") -> str:
        if not results:
            logger.warning("没有结果可导出")
            return ""
        
        filepath = self.output_dir / filename
        
        data = []
        for result in results:
            data.append({
                "问题ID": result.question_id,
                "平台": result.platform_name,
                "问题": result.question_text,
                "回答": result.answer,
                "状态": result.status,
                "匹配规则": ", ".join(result.matched_rules) if result.matched_rules else "",
                "错误信息": result.error_message or "",
                "时间": result.timestamp.strftime("%Y-%m-%d %H:%M:%S") if result.timestamp else "",
                "截图路径": result.screenshot_path or ""
            })
        
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')
        
        self._format_excel(filepath, results)
        
        logger.info(f"Excel报告已导出: {filepath}")
        return str(filepath)
    
    def _format_excel(self, filepath: Path, results: List[Result]):
        wb = load_workbook(filepath)
        ws = wb.active
        
        header_fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row in ws.iter_rows():
            for cell in row:
                cell.border = thin_border
        
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 40
        ws.column_dimensions['D'].width = 60
        ws.column_dimensions['E'].width = 10
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 30
        ws.column_dimensions['H'].width = 20
        ws.column_dimensions['I'].width = 40
        
        for idx, result in enumerate(results, start=2):
            if result.screenshot_path and Path(result.screenshot_path).exists():
                try:
                    img = OpenpyxlImage(result.screenshot_path)
                    img.width = 200
                    img.height = 150
                    
                    img_cell = f'I{idx}'
                    ws.add_image(img, img_cell)
                    
                    ws.row_dimensions[idx].height = 120
                except Exception as e:
                    logger.warning(f"无法插入截图 {result.screenshot_path}: {str(e)}")
        
        wb.save(filepath)
    
    def export_summary(self, results: List[Result], filename: str = "summary.xlsx") -> str:
        if not results:
            logger.warning("没有结果可导出")
            return ""
        
        filepath = self.output_dir / filename
        
        summary_data = {
            "总结果数": len(results),
            "成功数": sum(1 for r in results if r.status == "success"),
            "失败数": sum(1 for r in results if r.status == "error"),
            "成功率": f"{sum(1 for r in results if r.status == 'success') / len(results) * 100:.2f}%"
        }
        
        platforms = set(r.platform_name for r in results)
        platform_stats = {}
        
        for platform in platforms:
            platform_results = [r for r in results if r.platform_name == platform]
            platform_stats[platform] = {
                "总数": len(platform_results),
                "成功": sum(1 for r in platform_results if r.status == "success"),
                "失败": sum(1 for r in platform_results if r.status == "error"),
                "成功率": f"{sum(1 for r in platform_results if r.status == 'success') / len(platform_results) * 100:.2f}%"
            }
        
        df_summary = pd.DataFrame([summary_data])
        df_platforms = pd.DataFrame(platform_stats).T
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='总览', index=False)
            df_platforms.to_excel(writer, sheet_name='平台统计')
        
        logger.info(f"汇总报告已导出: {filepath}")
        return str(filepath)