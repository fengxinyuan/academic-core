# -*- coding: utf-8 -*-
"""
Mock 视觉 OCR 引擎 (MockVisionEngine)
专为离线自测、CI/CD 自动化流水线及无 Token 消耗回归验证设计。
"""

from academic_core.vision_ocr.base import BaseVisionEngine

class MockVisionEngine(BaseVisionEngine):
    def __init__(self, cache_dir: str = "cache_ocr", mock_text: str = None):
        super().__init__(cache_dir=cache_dir)
        self.mock_text = mock_text

    def extract_page_latex(self, image_bytes: bytes, page_num: int = 1, total_pages: int = 1) -> str:
        if self.mock_text:
            return self.mock_text

        # 生成标准且包含数学公式的学术内容测试样本
        content = (
            f"### 第 {page_num} 节 线性空间的基与维数 (Page {page_num}/{total_pages})\n\n"
            f"**定义 1** 设 $V$ 是数域 $\\mathbb{{F}}$ 上的线性空间，若向量组 $\\alpha_1, \\dots, \\alpha_n$ 线性无关，\n"
            f"且 $V$ 中任一向量均可由其线性表出，则称其为 $V$ 的一组基。\n\n"
            f"任一向量 $x \\in V$ 的坐标表示满足矩阵方程：\n"
            f"$$\n"
            f"x = \\sum_{{i=1}}^{{n}} c_i \\alpha_i = (\\alpha_1, \\dots, \\alpha_n) \\begin{{pmatrix}} c_1 \\\\ \\vdots \\\\ c_n \\end{{pmatrix}}\n"
            f"$$\n"
        )
        return self._clean_repetitive_lines(content)

