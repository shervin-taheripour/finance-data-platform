"""Unit tests for optional AWS publishing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from finance_data_platform.publishing.s3_publisher import (
    PublishConfig,
    PublishConfigurationError,
    collect_publishable_files,
    publish_reports,
)


class FakeAwsError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


@dataclass
class FakeS3Client:
    remote_objects: dict[str, str] = field(default_factory=dict)
    uploads: list[dict[str, Any]] = field(default_factory=list)
    head_calls: list[tuple[str, str]] = field(default_factory=list)

    def head_object(self, **kwargs: Any) -> dict[str, str]:
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        self.head_calls.append((bucket, key))
        if key not in self.remote_objects:
            raise FakeAwsError("404")
        return {"ETag": f'"{self.remote_objects[key]}"'}

    def upload_file(self, *args: Any, **kwargs: Any) -> None:
        filename, bucket, key = args[:3]
        extra_args = kwargs["ExtraArgs"]
        digest = hashlib.md5(Path(filename).read_bytes(), usedforsecurity=False).hexdigest()
        self.remote_objects[key] = digest
        self.uploads.append(
            {
                "filename": filename,
                "bucket": bucket,
                "key": key,
                "extra_args": extra_args,
            }
        )


@dataclass
class FakeCloudFrontClient:
    invalidations: list[dict[str, Any]] = field(default_factory=list)

    def create_invalidation(self, **kwargs: Any) -> None:
        self.invalidations.append(kwargs)


@dataclass
class FakeSession:
    s3_client: FakeS3Client
    cloudfront_client: FakeCloudFrontClient

    def client(self, service_name: str, region_name: str | None = None) -> Any:
        if service_name == "s3":
            return self.s3_client
        if service_name == "cloudfront":
            return self.cloudfront_client
        raise AssertionError(f"Unexpected service {service_name}")


@dataclass
class SessionFactory:
    session: FakeSession

    def __call__(self) -> FakeSession:
        return self.session


@pytest.fixture
def publish_config(tmp_path: Path) -> PublishConfig:
    output_root = tmp_path / "output"
    assets_root = tmp_path / "assets"
    output_root.mkdir()
    assets_root.mkdir()

    (output_root / "aapl_report.html").write_text("<html>AAPL</html>", encoding="utf-8")
    (output_root / "notes.txt").write_text("ignore me", encoding="utf-8")
    (assets_root / "report_styles.css").write_text("body { color: #111; }", encoding="utf-8")

    return PublishConfig(
        enabled=True,
        bucket="demo-bucket",
        region="eu-west-1",
        prefix="reports/",
        distribution_id="E123ABC456",
        distribution_url="https://d123.cloudfront.net",
        output_path=output_root,
        assets_path=assets_root,
    )


@pytest.fixture
def fake_clients() -> tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory]:
    s3 = FakeS3Client()
    cloudfront = FakeCloudFrontClient()
    session_factory = SessionFactory(FakeSession(s3, cloudfront))
    return s3, cloudfront, session_factory


def test_publish_disabled_is_noop(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    s3, cloudfront, session_factory = fake_clients
    result = publish_reports(
        PublishConfig(**{**publish_config.__dict__, "enabled": False}),
        session_factory=session_factory,
    )

    assert result.enabled is False
    assert result.uploaded_keys == []
    assert s3.uploads == []
    assert cloudfront.invalidations == []


def test_publish_uploads_html_files(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    s3, cloudfront, session_factory = fake_clients
    result = publish_reports(publish_config, session_factory=session_factory)

    assert result.uploaded_keys == [
        "reports/aapl_report.html",
        "reports/assets/report_styles.css",
    ]
    assert result.invalidated_paths == [
        "/reports/aapl_report.html",
        "/reports/assets/report_styles.css",
    ]
    assert len(s3.uploads) == 2
    assert len(cloudfront.invalidations) == 1


def test_publish_skips_unchanged_files(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    s3, cloudfront, session_factory = fake_clients
    first = publish_reports(publish_config, session_factory=session_factory)
    second = publish_reports(publish_config, session_factory=session_factory)

    assert len(first.uploaded_keys) == 2
    assert second.uploaded_keys == []
    assert second.invalidated_paths == []
    assert len(s3.uploads) == 2
    assert len(cloudfront.invalidations) == 1


def test_publish_creates_invalidation_on_change(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    s3, cloudfront, session_factory = fake_clients
    publish_reports(publish_config, session_factory=session_factory)
    report_path = publish_config.output_path / "aapl_report.html"
    report_path.write_text("<html>updated</html>", encoding="utf-8")

    result = publish_reports(publish_config, session_factory=session_factory)

    assert result.uploaded_keys == ["reports/aapl_report.html"]
    assert result.invalidated_paths == ["/reports/aapl_report.html"]
    assert len(cloudfront.invalidations) == 2


def test_publish_skips_invalidation_when_no_changes(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    _, cloudfront, session_factory = fake_clients
    publish_reports(publish_config, session_factory=session_factory)
    cloudfront.invalidations.clear()

    result = publish_reports(publish_config, session_factory=session_factory)

    assert result.uploaded_keys == []
    assert result.invalidated_paths == []
    assert cloudfront.invalidations == []


def test_publish_respects_prefix(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    _, _, session_factory = fake_clients
    config = PublishConfig(**{**publish_config.__dict__, "prefix": "custom-prefix/"})

    result = publish_reports(config, session_factory=session_factory)

    assert all(key.startswith("custom-prefix/") for key in result.uploaded_keys)


def test_publish_handles_missing_bucket_config(publish_config: PublishConfig) -> None:
    config = PublishConfig(**{**publish_config.__dict__, "bucket": ""})
    with pytest.raises(PublishConfigurationError, match="publishing.s3.bucket"):
        publish_reports(config, session_factory=lambda: None)


def test_publish_handles_missing_distribution_id(publish_config: PublishConfig) -> None:
    config = PublishConfig(**{**publish_config.__dict__, "distribution_id": ""})
    with pytest.raises(PublishConfigurationError, match="distribution_id"):
        publish_reports(config, session_factory=lambda: None)


def test_publish_does_not_upload_unsupported_files(publish_config: PublishConfig) -> None:
    files = collect_publishable_files(publish_config.output_path, publish_config.assets_path)
    assert "notes.txt" not in files
    assert sorted(files) == ["aapl_report.html", "assets/report_styles.css"]


def test_publish_dry_run_makes_no_aws_calls(
    publish_config: PublishConfig,
    fake_clients: tuple[FakeS3Client, FakeCloudFrontClient, SessionFactory],
) -> None:
    s3, cloudfront, session_factory = fake_clients

    result = publish_reports(publish_config, dry_run=True, session_factory=session_factory)

    assert result.dry_run is True
    assert sorted(result.uploaded_keys) == [
        "reports/aapl_report.html",
        "reports/assets/report_styles.css",
    ]
    assert s3.uploads == []
    assert cloudfront.invalidations == []
    assert len(s3.head_calls) == 2
