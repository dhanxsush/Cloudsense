"""
Core module exports

Provides easy access to core functionality.
"""

from core.auth import (
    hash_password,
    verify_password,
    create_jwt_token,
    verify_jwt_token
)

from core.database import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_analysis,
    update_analysis_status,
    get_analysis,
    get_recent_analyses,
    save_analysis_results,
    get_analysis_results,
    save_analysis_metadata,
    get_analysis_metadata
)

from core.dependencies import (
    get_current_user,
    verify_token
)

__all__ = [
    # Auth
    "hash_password",
    "verify_password",
    "create_jwt_token",
    "verify_jwt_token",
    
    # Database
    "init_db",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "create_analysis",
    "update_analysis_status",
    "get_analysis",
    "get_recent_analyses",
    "save_analysis_results",
    "get_analysis_results",
    "save_analysis_metadata",
    "get_analysis_metadata",
    
    # Dependencies
    "get_current_user",
    "verify_token",
]
