import os

from src.server import build_config_from_env, create_app


def main() -> None:
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/db"
    print("Building config...")
    app = create_app(build_config_from_env())
    openapi = app.openapi()
    tags = {tag.get("name") for tag in openapi.get("tags", [])}
    paths = [p for p in openapi["paths"] if "/v2" in p]
    print("Success! Tags:", tags)
    print("V2 Paths:", len(paths))


if __name__ == "__main__":
    main()
