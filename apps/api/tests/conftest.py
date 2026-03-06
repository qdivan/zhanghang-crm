import os


os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test.db")
os.environ.setdefault("BOOTSTRAP_DEMO_DATA", "true")
os.environ.setdefault("BOOTSTRAP_DEMO_PASSWORD", "Daizhang#2026!")
os.environ.setdefault("RESET_DB_ON_STARTUP", "true")
os.environ.setdefault("JWT_SECRET", "test-secret")
