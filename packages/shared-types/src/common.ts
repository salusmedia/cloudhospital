// 全场景通用的契约类型（手写）。各场景专属接口类型由 gen:types 生成到 ./generated/。

/** 统一 API 响应包装 */
export interface ApiResponse<T> {
  data: T;
  traceId?: string;
}

/** 统一分页结构 */
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** 网关注入的登录用户身份（前后端一致） */
export interface AuthUser {
  userId: string;
  name: string;
  roles: string[];
  /** 该用户有权访问的科室/范围，用于数据权限 */
  scopes: string[];
}

/** 患者引用：场景内只持有引用，主数据在 platform-patient */
export interface PatientRef {
  patientId: string;
}

/** 统一错误体 */
export interface ApiError {
  code: string;
  message: string;
  traceId?: string;
}
