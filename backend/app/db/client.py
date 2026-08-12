import threading

from supabase import Client, create_client

from backend.app.core.config import get_settings

# One client per thread. The Supabase client wraps a single httpx connection that is not safe
# to share: FastAPI runs background analysis in a worker thread while request handlers use the
# same repository singleton, and the overlap produced intermittent "Server disconnected"
# failures that aborted analyses mid-run.
_local = threading.local()


def get_supabase_client() -> Client:
    client = getattr(_local, "client", None)
    if client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set to use the Supabase repository.")
        client = create_client(settings.supabase_url, settings.supabase_key)
        _local.client = client
    return client
