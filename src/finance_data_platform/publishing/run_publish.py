"""CLI entrypoint for optional AWS report publishing."""

from __future__ import annotations

from finance_data_platform.publishing.s3_publisher import main

if __name__ == "__main__":
    raise SystemExit(main())
