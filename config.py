import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


@dataclass(frozen=True)
class SqlConfig:
    server: str
    port: int
    user: str
    password: str


@dataclass(frozen=True)
class Config:
    ollama_host: str
    ollama_api_key: str
    ollama_model: str

    source: SqlConfig
    dest: SqlConfig

    backup_path_host: str
    backup_path_container: str

    jira_url: str | None
    jira_email: str | None
    jira_api_token: str | None
    jira_project_key: str
    jira_poll_interval_sec: int

    teams_webhook_url: str | None

    region: str
    sqlite_path: str
    disk_threshold_percent: int
    log_level: str

    @property
    def jira_enabled(self) -> bool:
        return bool(self.jira_url and self.jira_email and self.jira_api_token)

    @property
    def teams_enabled(self) -> bool:
        return bool(self.teams_webhook_url)


def load() -> Config:
    return Config(
        ollama_host=os.getenv("OLLAMA_HOST", "https://ollama.com"),
        ollama_api_key=_req("OLLAMA_API_KEY"),
        ollama_model=os.getenv("OLLAMA_MODEL", "kimi-k2.6"),
        source=SqlConfig(
            server=os.getenv("MSSQL_SOURCE_SERVER", "localhost"),
            port=int(os.getenv("MSSQL_SOURCE_PORT", "1433")),
            user=os.getenv("MSSQL_SOURCE_USER", "sa"),
            password=_req("MSSQL_SOURCE_PASSWORD"),
        ),
        dest=SqlConfig(
            server=os.getenv("MSSQL_DEST_SERVER", "localhost"),
            port=int(os.getenv("MSSQL_DEST_PORT", "1434")),
            user=os.getenv("MSSQL_DEST_USER", "sa"),
            password=_req("MSSQL_DEST_PASSWORD"),
        ),
        backup_path_host=os.getenv("BACKUP_PATH_HOST", "./backups"),
        backup_path_container=os.getenv("BACKUP_PATH_CONTAINER", "/var/opt/mssql/backups"),
        jira_url=os.getenv("JIRA_URL") or None,
        jira_email=os.getenv("JIRA_EMAIL") or None,
        jira_api_token=os.getenv("JIRA_API_TOKEN") or None,
        jira_project_key=os.getenv("JIRA_PROJECT_KEY", "DBSUP"),
        jira_poll_interval_sec=int(os.getenv("JIRA_POLL_INTERVAL_SEC", "30")),
        teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL") or None,
        region=os.getenv("REGION", "APAC"),
        sqlite_path=os.getenv("DB_AGENTS_SQLITE", "./db_agents.db"),
        disk_threshold_percent=int(os.getenv("DISK_THRESHOLD_PERCENT", "85")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


CFG = load() if os.getenv("DB_AGENTS_SKIP_CONFIG") != "1" else None
