"""
@Author: li
@Email: lijianqiao2906@live.com
@FileName: config.py
@DateTime: 2025/06/02 修订版本
@Docs: 改进的配置管理
"""

import logging
from functools import lru_cache
from typing import Any, ClassVar

from pydantic import BaseModel, Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# from app.utils.enum import Environment, LogLevel


# def parse_cors_origins(v: Any) -> list[str]:
#     """解析 CORS 配置"""
#     if v is None or v == "":
#         return []
#     if isinstance(v, str):
#         # 支持逗号分隔的字符串
#         return [origin.strip() for origin in v.split(",") if origin.strip()]
#     elif isinstance(v, list):
#         return [str(origin).strip() for origin in v if str(origin).strip()]
#     return []
#
#
# class DatabaseSettings(BaseModel):
#     """数据库配置"""
#
#     url: PostgresDsn = Field(description="数据库连接URL")
#     echo: bool = Field(default=False, description="是否输出SQL语句")
#     pool_size: int = Field(default=10, ge=1, le=50, description="连接池大小")
#     max_overflow: int = Field(default=20, ge=0, le=100, description="连接池最大溢出数量")
#     pool_timeout: int = Field(default=30, ge=5, le=300, description="连接池超时时间(秒)")
#     pool_recycle: int = Field(default=3600, ge=300, description="连接回收时间(秒)")
#
#
# class JWTSettings(BaseModel):
#     """JWT配置"""
#
#     secret_key: str = Field(min_length=32, description="JWT密钥，至少32位")
#     refresh_secret_key: str = Field(min_length=32, description="JWT刷新令牌密钥，至少32位")
#     algorithm: str = Field(default="HS256", description="JWT算法")
#     access_token_expire_minutes: int = Field(default=30, ge=5, le=1440, description="访问令牌过期时间(分钟)")
#     refresh_token_expire_days: int = Field(default=7, ge=1, le=30, description="刷新令牌过期时间(天)")
#
#
# class AdminSettings(BaseModel):
#     """初始管理员配置"""
#
#     username: str = Field(min_length=3, max_length=50, description="初始管理员用户名")
#     email: str = Field(description="初始管理员邮箱")
#     password: str = Field(min_length=8, description="初始管理员密码")
#     phone: str | None = Field(default=None, description="初始管理员手机号")
#     nickname: str | None = Field(default=None, description="初始管理员昵称")
#
#     @field_validator("email")
#     @classmethod
#     def validate_email(cls, v: str) -> str:
#         """验证邮箱格式"""
#         if "@" not in v or "." not in v.split("@")[-1]:
#             raise ValueError("无效的邮箱格式")
#         return v.lower()
#
#
# class CORSSettings(BaseModel):
#     """CORS配置"""
#
#     allow_credentials: bool = Field(default=True, description="是否允许携带凭证")
#     allow_origins: list[str] = Field(default=[], description="允许的来源")
#     allow_methods: list[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="允许的HTTP方法")
#     allow_headers: list[str] = Field(default=["*"], description="允许的HTTP头")


class Settings(BaseSettings):
    """
    应用配置类

    通过环境变量或 .env 文件加载配置。
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file="app/settings/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === 环境配置 ===
    # environment: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")
    DEBUG: bool = Field(default=False, description="是否启用调试模式")

    # === 应用核心配置 ===
    APP_TITLE: str = Field(default="FastAPI 后台管理系统", description="应用名称")
    PROJECT_NAME: str = Field(default="FastAPI 后台管理系统", description="应用名称")
    VERSION: str = Field(default="1.0.0", description="应用版本")
    APP_DESCRIPTION: str = Field(default="基于 FastAPI 构建的后台管理系统", description="应用描述")
    SECRET_KEY: str = Field(
        default="your_default_secret_key_please_change_me_in_production_at_least_32_chars",
        min_length=32,
        description="应用全局密钥，用于会话等敏感操作",
    )

    # === 服务器配置 ===
    # server_host: str = Field(default="127.0.0.1", description="服务器监听主机")
    # server_port: int = Field(default=8000, ge=1, le=65535, description="服务器监听端口")

    # === API 配置 ===
    # api_v1_prefix: str = Field(default="/api/v1", description="API v1 版本前缀")

    # === 数据库配置 ===
    SQLALCHEMY_DATABASE_URI: str = Field(default="", description="知识库信息数据库连接URI")
    DATABASE_HOST: str = Field(default="127.0.0.1", description="数据库主机")
    DATABASE_PORT: int = Field(default=3306, ge=1, le=65535, description="数据库端口")
    DATABASE_USER: str = Field(default="root", description="数据库用户名")
    DATABASE_PWD: str = Field(default="password", description="数据库密码")
    DATABASE: str = Field(default="langchain_rag", description="数据库名")

    # === ORM 配置（初始为空） ===
    TORTOISE_ORM: dict = {}

    @model_validator(mode="after")
    def build_tortoise_orm_config(self) -> "Settings":
        self.TORTOISE_ORM = {
            "connections": {
                "mysql": {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.DATABASE_HOST,
                        "port": self.DATABASE_PORT,
                        "user": self.DATABASE_USER,
                        "password": self.DATABASE_PWD,
                        "database": self.DATABASE,
                    },
                }
            },
            "apps": {
                "models": {
                    "models": ["app.models", "aerich.models", "app.rag.db.models"],
                    "default_connection": "mysql",
                }
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }
        return self

    # TORTOISE_ORM: dict = {
    #     "connections": {
    #         # MySQL/MariaDB configuration
    #         # Install with: tortoise-orm[asyncmy]
    #         "mysql": {
    #             "engine": "tortoise.backends.mysql",
    #             "credentials": {
    #                 "host": DATABASE_HOST,  # Database host address
    #                 "port": DATABASE_PORT,  # Database port
    #                 "user": DATABASE_USER,  # Database username
    #                 "password": DATABASE_PWD,  # Database password
    #                 "database": DATABASE,  # Database name
    #             },
    #         },
    #     },
    #     "apps": {
    #         "models": {
    #             "models": ["app.models", "aerich.models"],
    #             "default_connection": "mysql",
    #         },
    #     },
    #     "use_tz": False,  # Whether to use timezone-aware datetimes
    #     "timezone": "Asia/Shanghai",  # Timezone setting
    # }
    # database_url: PostgresDsn = Field(
    #     default=PostgresDsn("postgresql+asyncpg://user:password@localhost:5432/dbname"), description="数据库连接URL"
    # )
    # database_echo: bool = Field(default=False, description="是否输出SQL语句")
    # database_pool_size: int = Field(default=10, ge=1, le=50, description="连接池大小")
    # database_max_overflow: int = Field(default=20, ge=0, le=100, description="连接池最大溢出")
    # database_pool_timeout: int = Field(default=30, ge=5, le=300, description="连接池超时(秒)")
    # database_pool_recycle: int = Field(default=3600, ge=300, description="连接回收时间(秒)")

    # === JWT 配置 ===
    # jwt_secret_key: str = Field(
    #     default="your_super_secret_jwt_key_change_me_at_least_32_characters_long", min_length=32, description="JWT密钥"
    # )
    # jwt_refresh_secret_key: str = Field(
    #     default="your_super_secret_jwt_refresh_key_change_me_at_least_32_characters_long",
    #     min_length=32,
    #     description="JWT刷新令牌密钥",
    # )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=10080, description="访问令牌过期时间(分钟)")
    # jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=30, description="刷新令牌过期时间(天)")

    # === Redis 配置 ===
    # redis_url: RedisDsn | None = Field(default=None, description="Redis连接URL")

    # === 缓存配置 ===
    # cache_expire_minutes: int = Field(default=30, ge=5, le=1440, description="缓存过期时间(分钟)")
    # cache_key_prefix: str = Field(default="cache_T", description="缓存键前缀")

    # === 日志配置 ===
    # log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    # log_directory: str = Field(default="logs", description="日志文件存储目录")
    # log_backup_count: int = Field(default=30, ge=1, le=365, description="日志文件保留天数")

    # === 初始管理员配置 ===
    # admin_username: str = Field(default="admin", min_length=3, max_length=50, description="初始管理员用户名")
    # admin_email: str = Field(default="admin@example.com", description="初始管理员邮箱")
    # admin_password: str = Field(default="admin@123", min_length=8, description="初始管理员密码")
    # admin_phone: str | None = Field(default="13800000000", description="初始管理员手机号")
    # admin_nickname: str | None = Field(default="超级管理员", description="初始管理员昵称")

    # === CORS 配置 ===
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS允许凭证")
    # backend_cors_origins: str = Field(default="", description="后端CORS来源")
    # frontend_cors_origins: str = Field(default="", description="前端CORS来源")
    CORS_ALLOW_METHODS: str = Field(default="GET,POST,PUT,DELETE,OPTIONS", description="CORS允许方法")
    CORS_ALLOW_HEADERS: str = Field(default="*", description="CORS允许头")
    CORS_ORIGINS: str = Field(default="*", description="")

    # === MINIO 配置 ===
    MINIO_HOST: str = Field(default="localhost:9000", description="MINIO主机")
    MINIO_USER: str = Field(default="miniouser", description="用户名")
    MINIO_PASSWORD: str = Field(default="miniouser", description="密码")

    # === ES 配置 ===
    ES_HOST: str = Field(default="http://192.168.0.103:9200/", description="ES主机")
    ELASTIC_USER: str = Field(default="elastic", description="用户名")
    ELASTIC_PASSWORD: str = Field(default="elastic123.", description="密码")

    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    EXCLUDED_PATHS: list[str] = ["/api/v1/rag/knowledge_base/upload_and_parse", ]  # 添加其他需要跳过的路径


#     @field_validator("admin_email")
#     @classmethod
#     def validate_admin_email(cls, v: str) -> str:
#         """验证管理员邮箱"""
#         if "@" not in v or "." not in v.split("@")[-1]:
#             raise ValueError("无效的邮箱格式")
#         return v.lower()
#
#     @model_validator(mode="after")
#     def validate_environment_specific_settings(self) -> "Settings":
#         """根据环境验证特定设置"""
#         if self.environment == Environment.PRODUCTION:
#             # 生产环境安全检查
#             if self.debug:
#                 raise ValueError("生产环境不应启用调试模式")
#             if self.secret_key == "your_default_secret_key_please_change_me_in_production":
#                 raise ValueError("生产环境必须修改默认密钥")
#             if self.jwt_secret_key == "your_super_secret_jwt_key_change_me":
#                 raise ValueError("生产环境必须修改默认JWT密钥")
#
#         return self
#
#     # === 结构化配置属性 ===
#     @property
#     def database(self) -> DatabaseSettings:
#         """获取数据库配置"""
#         return DatabaseSettings(
#             url=self.database_url,
#             echo=self.database_echo,
#             pool_size=self.database_pool_size,
#             max_overflow=self.database_max_overflow,
#             pool_timeout=self.database_pool_timeout,
#             pool_recycle=self.database_pool_recycle,
#         )
#
#     @property
#     def jwt(self) -> JWTSettings:
#         """获取JWT配置"""
#         return JWTSettings(
#             secret_key=self.jwt_secret_key,
#             refresh_secret_key=self.jwt_refresh_secret_key,
#             algorithm=self.jwt_algorithm,
#             access_token_expire_minutes=self.jwt_access_token_expire_minutes,
#             refresh_token_expire_days=self.jwt_refresh_token_expire_days,
#         )
#
#     @property
#     def admin(self) -> AdminSettings:
#         """获取管理员配置"""
#         return AdminSettings(
#             username=self.admin_username,
#             email=self.admin_email,
#             password=self.admin_password,
#             phone=self.admin_phone,
#             nickname=self.admin_nickname,
#         )
#
#     @property
#     def cors(self) -> CORSSettings:
#         """获取CORS配置"""
#         # 合并所有CORS来源
#         all_origins = []
#         if self.backend_cors_origins:
#             all_origins.extend(parse_cors_origins(self.backend_cors_origins))
#         if self.frontend_cors_origins:
#             all_origins.extend(parse_cors_origins(self.frontend_cors_origins))
#
#         return CORSSettings(
#             allow_credentials=self.cors_allow_credentials,
#             allow_origins=list(set(all_origins)),  # 去重
#             allow_methods=parse_cors_origins(self.cors_allow_methods),
#             allow_headers=parse_cors_origins(self.cors_allow_headers),
#         )
#
#     @property
#     def is_development(self) -> bool:
#         """是否为开发环境"""
#         return self.environment == Environment.DEVELOPMENT
#
#     @property
#     def is_production(self) -> bool:
#         """是否为生产环境"""
#         return self.environment == Environment.PRODUCTION
#
#     @property
#     def log_level_int(self) -> int:
#         """获取日志级别对应的整数值"""
#         return getattr(logging, self.log_level.value)
#
#
@lru_cache
def get_settings() -> Settings:
    """
    获取应用配置的单例实例

    使用 lru_cache 确保配置只从环境变量或 .env 文件加载一次。
    """
    return Settings()


# 全局配置实例
settings: Settings = get_settings()

# print(settings)
# print(settings.APP_TITLE)
