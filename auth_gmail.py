import sys
from pathlib import Path

app_dir = Path(__file__).parent / 'app'
if app_dir.exists():
    sys.path.insert(0, str(Path(__file__).parent))

from app.services.gmail_service import get_gmail_service


if __name__ == '__main__':
    try:
        gmail_service = get_gmail_service()
        gmail_service.authenticate_with_installed_app_flow()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
