"""
API 依赖注入
提供当前用户认证、数据库会话等
"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import decode_access_token
from app.crud.user import get_user_by_id

# OAuth2 密码流 Token 提取
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(default=None, alias="token", include_in_schema=False),
    db: Session = Depends(get_db),
):
    """
    获取当前认证用户
    支持两种 Token 传递方式：
      1. Authorization: Bearer <token> 请求头（标准方式）
      2. ?token=<token> URL 查询参数（用于 <img> 标签等无法设置请求头的场景）
    """
    # 优先使用 Header Token，其次使用 Query Token
    effective_token = token or token_query
    if not effective_token:
        return None

    payload = decode_access_token(effective_token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        return None

    return user


async def get_required_user(
    current_user=Depends(get_current_user),
):
    """
    获取当前认证用户（必须登录）
    未登录时抛出 401 错误
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或 Token 已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
