import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return str(value).lower() in ("true", "1", "yes", "on")

    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    # YAML layer
    environment = os.getenv("APP_ENV", "development")
    yaml_file = Path(f"config.{environment}.yaml")

    if yaml_file.exists():
        with yaml_file.open(encoding="utf-8") as f:
            config.update(yaml.safe_load(f) or {})

    # .env layer
    env_file = dotenv_values(".env")

    for key, value in env_file.items():
        if value is None:
            continue

        normalized = key.lower()

        if key == "NUM_WORKERS":
            normalized = "workers"
        elif key.startswith("APP_"):
            normalized = key[4:].lower()

        if normalized in config:
            config[normalized] = coerce(normalized, value)

    # OS environment layer
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            normalized = key[4:].lower()

            if normalized in config:
                config[normalized] = coerce(normalized, value)

    # CLI query overrides
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip().lower()

        if key in config:
            config[key] = coerce(key, value)

    # Never reveal the secret
    config["api_key"] = "****"

    return config