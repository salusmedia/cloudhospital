"""业务表公共字段 Mixin（见 docs/08-数据库设计.md 第 3 节）。

所有业务表统一继承 CommonColumns，获得一致的主键/归属/审计/软删除/乐观锁字段：

    from py_common.db import Base
    from py_common.models import CommonColumns

    class FollowupPlan(Base, CommonColumns):
        __tablename__ = "followup_plan"
        __table_args__ = {"schema": "scenario_followup"}
        plan_name: Mapped[str] = mapped_column(String(100))

`org_id` + `dept_code` 是整套数据权限的支点（数据归属哪个机构/科室）。
不要在业务表里另造一套主键/时间戳/软删除字段。
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column


def uuid7() -> uuid.UUID:
    """生成时间有序的 UUIDv7（48bit 毫秒时间戳 + 随机）。

    时间有序对主键索引友好，又不像自增 ID 那样暴露业务量，且跨机构/场景不冲突。
    Python 3.11 标准库尚无 uuid7，这里零依赖自实现（符合 RFC 9562）。
    """
    ms = int(time.time() * 1000)
    rand = os.urandom(10)
    b = bytearray(ms.to_bytes(6, "big") + rand)
    b[6] = (b[6] & 0x0F) | 0x70  # version 7
    b[8] = (b[8] & 0x3F) | 0x80  # variant 10
    return uuid.UUID(bytes=bytes(b))


class CommonColumns:
    """所有业务表必带的公共列。用法：class Xxx(Base, CommonColumns)。"""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    # 数据归属机构（医共体多级：三级/二级/一级/社区），数据权限维度之一
    org_id: Mapped[str] = mapped_column(String(32), index=True)
    # 归属科室代码（ASCII，驱动数据权限，与 auth.py scopes 一致）
    dept_code: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(64), default="")
    updated_by: Mapped[str] = mapped_column(String(64), default="")
    # 软删除：医疗数据不物理删，留痕
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # 乐观锁
    row_version: Mapped[int] = mapped_column(Integer, default=0)
