from .config import settings

if settings.DEBUG:
    from .local import *
else:
    from .production import *
