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
            image_note = ""
            if result.screenshot_path:
                if getattr(result, 'is_shared_image', False):
                    image_note = "分享图片"
                else:
                    image_note = "页面截图（可手动替换）"
            
            data.append({
                "问题ID": result.question_id,
                "平台": result.platform_name,
                "问题": result.question_text,
                "回答": result.answer,
                "状态": result.status,
                "匹配规则": ", ".join(result.matched_rules) if result.matched_rules else "",
                "错误信息": result.error_message or "",
                "时间": result.timestamp.strftime("%Y-%m-%d %H:%M:%S") if result.timestamp else "",
                "截图类型": image_note,
                "截图路径": result.screenshot_path or "",
                "分享链接": result.share_link or "",
                "分享链接失败原因": result.share_link_error or ""
            })
        
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')
        
        self._format_excel(filepath, results)
        
        # 导出分享链接到文本文件
        self._export_share_links(results)
        
        logger.info(f"Excel报告已导出: {filepath}")
        return str(filepath)
    
    def _export_share_links(self, results: List[Result]):
        """将分享链接追加到文本文件，保持和图片名称一致性"""
        links_filepath = self.output_dir / "share_links.txt"
        
        try:
            from datetime import datetime
            
            file_exists = links_filepath.exists()
            
            with open(links_filepath, 'a', encoding='utf-8') as f:
                if not file_exists:
                    f.write("=" * 80 + "\n")
                    f.write("AI 问答评测工具 - 分享链接汇总\n")
                    f.write("=" * 80 + "\n\n")
                
                for result in results:
                    if result.share_link:
                        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S") if result.timestamp else datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_name = f"{result.platform_name}_{result.question_id}_{timestamp}"
                        
                        f.write(f"[{result.platform_name}] 问题 {result.question_id} | 文件名: {screenshot_name}\n")
                        f.write(f"  问题: {result.question_text}\n")
                        f.write(f"  链接: {result.share_link}\n")
                        f.write("-" * 80 + "\n")
            
            logger.info(f"分享链接已追加到: {links_filepath}")
        except Exception as e:
            logger.error(f"导出分享链接失败: {str(e)}")
    
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
        ws.column_dimensions['I'].width = 20
        ws.column_dimensions['J'].width = 40
        ws.column_dimensions['K'].width = 50
        ws.column_dimensions['L'].width = 50
        
        for idx, result in enumerate(results, start=2):
            if result.screenshot_path:
                # 确保使用绝对路径
                screenshot_path = Path(result.screenshot_path)
                if not screenshot_path.is_absolute():
                    screenshot_path = Path.cwd() / result.screenshot_path
                
                logger.info(f"处理截图: {screenshot_path}, 存在: {screenshot_path.exists()}")
                
                if screenshot_path.exists():
                    try:
                        img = OpenpyxlImage(str(screenshot_path))
                        img.width = 200
                        img.height = 150
                        
                        img_cell = f'J{idx}'
                        ws.add_image(img, img_cell)
                        
                        ws.row_dimensions[idx].height = 120
                        logger.info(f"截图成功插入到单元格 {img_cell}")
                    except Exception as e:
                        logger.error(f"无法插入截图 {screenshot_path}: {str(e)}")
                else:
                    logger.warning(f"截图文件不存在: {screenshot_path}")
            else:
                logger.info(f"结果 {result.question_id} 没有截图路径")
        
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
