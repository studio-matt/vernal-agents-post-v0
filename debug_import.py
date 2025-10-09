"""
Debug import test - this will help identify the exact import error
"""

print("DEBUG: Starting debug_import.py")

try:
    print("DEBUG: Importing FastAPI...")
    from fastapi import APIRouter
    print("DEBUG: FastAPI imported successfully")
    
    print("DEBUG: Creating router...")
    router = APIRouter(prefix="/debug", tags=["Debug"])
    print("DEBUG: Router created successfully")
    
    print("DEBUG: Creating endpoint...")
    @router.get("/health")
    def debug_health():
        print("DEBUG: debug_health endpoint called")
        return {"status": "debug working", "message": "Import test successful"}
    
    print("DEBUG: Endpoint created successfully")
    print("DEBUG: debug_import.py loaded successfully")
    
except Exception as e:
    print(f"DEBUG: ERROR in debug_import.py: {e}")
    import traceback
    traceback.print_exc()
