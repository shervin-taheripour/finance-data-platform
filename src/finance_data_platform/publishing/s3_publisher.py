"""Publish generated HTML reports to S3 and invalidate CloudFront paths."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".html", ".css"}
DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_ASSETS_PATH = Path("assets")


@dataclass(frozen=True)
class PublishConfig:
    enabled: bool
    bucket: str
    region: str
    prefix: str
    distribution_id: str
    distribution_url: str
    output_path: Path
    assets_path: Path


@dataclass(frozen=True)
class PublishResult:
    uploaded_keys: list[str]
    invalidated_paths: list[str]
    skipped_keys: list[str]
    dry_run: bool
    enabled: bool


class PublishConfigurationError(ValueError):
    """Raised when publishing is enabled but configuration is incomplete."""


class PublishDependencyError(RuntimeError):
    """Raised when optional publishing dependencies are missing."""


class PublishRuntimeError(RuntimeError):
    """Raised when publish actions cannot be completed."""


def load_publish_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> PublishConfig:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    publishing = payload.get("publishing", {})
    s3_config = publishing.get("s3", {})
    cloudfront = publishing.get("cloudfront", {})
    reporting = payload.get("reporting", {})

    return PublishConfig(
        enabled=bool(publishing.get("enabled", False)),
        bucket=str(s3_config.get("bucket", "")).strip(),
        region=str(s3_config.get("region", "eu-west-1")).strip(),
        prefix=_normalize_prefix(str(s3_config.get("prefix", "reports/")).strip()),
        distribution_id=str(cloudfront.get("distribution_id", "")).strip(),
        distribution_url=str(cloudfront.get("distribution_url", "")).strip(),
        output_path=Path(str(reporting.get("output_path", "output"))),
        assets_path=Path(str(publishing.get("assets_path", DEFAULT_ASSETS_PATH))),
    )


def publish_reports(
    config: PublishConfig,
    *,
    dry_run: bool = False,
    session_factory: Any | None = None,
) -> PublishResult:
    if not config.enabled:
        LOGGER.info("Publishing disabled in config; nothing to do.")
        return PublishResult([], [], [], dry_run=dry_run, enabled=False)

    _validate_config(config)
    if session_factory is None:
        boto3 = _require_boto3()
        session_factory = boto3.Session

    publishable_files = collect_publishable_files(config.output_path, config.assets_path)
    if not publishable_files:
        LOGGER.info(
            "No publishable files found in %s or %s.",
            config.output_path,
            config.assets_path,
        )
        return PublishResult([], [], [], dry_run=dry_run, enabled=True)

    session = session_factory()
    s3_client = session.client("s3", region_name=config.region)

    changed: dict[str, Path] = {}
    skipped: list[str] = []
    for relative_key, local_path in sorted(publishable_files.items()):
        object_key = _prefixed_key(config.prefix, relative_key)
        if _remote_matches_local(s3_client, config.bucket, object_key, local_path):
            skipped.append(object_key)
        else:
            changed[object_key] = local_path

    invalidation_paths = [f"/{key}" for key in changed]
    if dry_run:
        LOGGER.info("Dry run: %d files would be uploaded.", len(changed))
        if invalidation_paths:
            LOGGER.info("Dry run: CloudFront invalidation would include %s", invalidation_paths)
        return PublishResult(
            uploaded_keys=sorted(changed),
            invalidated_paths=invalidation_paths,
            skipped_keys=skipped,
            dry_run=True,
            enabled=True,
        )

    uploaded: list[str] = []
    for object_key, local_path in sorted(changed.items()):
        s3_client.upload_file(
            str(local_path),
            config.bucket,
            object_key,
            ExtraArgs=_upload_extra_args(local_path),
        )
        uploaded.append(object_key)

    invalidated: list[str] = []
    if uploaded:
        cloudfront_client = session.client("cloudfront")
        cloudfront_client.create_invalidation(
            DistributionId=config.distribution_id,
            InvalidationBatch={
                "Paths": {
                    "Quantity": len(invalidation_paths),
                    "Items": invalidation_paths,
                },
                "CallerReference": _caller_reference(invalidation_paths),
            },
        )
        invalidated = invalidation_paths

    return PublishResult(
        uploaded_keys=uploaded,
        invalidated_paths=invalidated,
        skipped_keys=skipped,
        dry_run=False,
        enabled=True,
    )


def collect_publishable_files(output_path: Path, assets_path: Path) -> dict[str, Path]:
    publishable: dict[str, Path] = {}

    if output_path.exists():
        for path in sorted(output_path.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                publishable[path.relative_to(output_path).as_posix()] = path

    if assets_path.exists():
        for path in sorted(assets_path.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                publishable.setdefault(f"assets/{path.relative_to(assets_path).as_posix()}", path)

    return publishable


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish generated HTML reports to S3 and CloudFront."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to config YAML.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without uploading or invalidating.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    config = load_publish_config(args.config)
    result = publish_reports(config, dry_run=args.dry_run)

    if not result.enabled:
        print("Publishing disabled: no-op")
        return 0

    status = "would upload" if result.dry_run else "uploaded"
    print(
        f"Publish complete: {status}={len(result.uploaded_keys)}, "
        f"skipped={len(result.skipped_keys)}"
    )
    if result.invalidated_paths:
        prefix = "would invalidate" if result.dry_run else "invalidated"
        print(f"CloudFront {prefix}: {', '.join(result.invalidated_paths)}")
    return 0


def _validate_config(config: PublishConfig) -> None:
    if not config.bucket:
        raise PublishConfigurationError(
            "Publishing is enabled but publishing.s3.bucket is empty in config.yaml."
        )
    if not config.distribution_id:
        raise PublishConfigurationError(
            "Publishing is enabled but "
            "publishing.cloudfront.distribution_id is empty in config.yaml."
        )


def _require_boto3() -> Any:
    try:
        return importlib.import_module("boto3")
    except ModuleNotFoundError as exc:
        raise PublishDependencyError(
            "Publishing requires boto3. Install it with "
            "`python -m pip install -e \".[publishing]\"`."
        ) from exc


def _normalize_prefix(prefix: str) -> str:
    normalized = prefix.strip("/")
    if not normalized:
        return ""
    return f"{normalized}/"


def _prefixed_key(prefix: str, relative_key: str) -> str:
    return f"{prefix}{relative_key}" if prefix else relative_key


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _remote_matches_local(s3_client: Any, bucket: str, object_key: str, local_path: Path) -> bool:
    try:
        response = s3_client.head_object(Bucket=bucket, Key=object_key)
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise PublishRuntimeError(f"Failed to inspect s3://{bucket}/{object_key}: {exc}") from exc

    remote_etag = str(response.get("ETag", "")).strip('"')
    if not remote_etag or "-" in remote_etag:
        return False
    return remote_etag == _md5(local_path)


def _upload_extra_args(path: Path) -> dict[str, str]:
    content_type, _ = mimetypes.guess_type(str(path))
    args: dict[str, str] = {}
    if content_type:
        args["ContentType"] = content_type
    if path.suffix.lower() == ".html":
        args["CacheControl"] = "public, max-age=300"
    elif path.suffix.lower() == ".css":
        args["CacheControl"] = "public, max-age=86400"
    return args


def _caller_reference(paths: list[str]) -> str:
    digest = hashlib.md5("\n".join(paths).encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"finance-data-platform-{digest}"


__all__ = [
    "PublishConfig",
    "PublishConfigurationError",
    "PublishDependencyError",
    "PublishResult",
    "collect_publishable_files",
    "load_publish_config",
    "main",
    "publish_reports",
]
