import os
import sys
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_734.settings')

from django.core.wsgi import get_wsgi_application


app = get_wsgi_application()
application = app