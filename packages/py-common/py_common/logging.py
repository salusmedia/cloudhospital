"""结构化日志。内置敏感词兜底过滤，降低明文泄露风险。

注意：脱敏的第一责任在调用方（用 desensitize 处理后再记日志）。
此处的过滤器是"最后一道防线"，不可依赖它替代主动脱敏。
"""

from __future__ import annotations

import logging
import re

# 兜底：疑似身份证(18位)/手机号(11位连续数字) 直接打码。
_PATTERNS = [
    (re.compile(r"\b\d{17}[\dxX]\b"), "<ID>"),
    (re.compile(r"\b1\d{10}\b"), "<PHONE>"),
]


class _MaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat, repl in _PATTERNS:
            msg = pat.sub(repl, msg)
        record.msg = msg
        record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        handler.addFilter(_MaskFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
