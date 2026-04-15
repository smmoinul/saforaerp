# SaforaERP Database Connection - Supabase
from supabase import create_client, Client
from config import settings
from functools import lru_cache

@lru_cache()
def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@lru_cache()
def get_supabase_admin() -> Client:
    """Service role client - bypasses RLS for admin operations"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# Dependency
def get_db() -> Client:
    return get_supabase()

def get_db_admin() -> Client:
    return get_supabase_admin()
