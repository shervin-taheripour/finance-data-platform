# AWS Setup for Cloud-Published Reports

This project can optionally publish generated HTML reports to a private S3 bucket fronted by CloudFront. The bucket is not public; viewers access reports only through the CloudFront distribution.

## 1. Create the S3 bucket
- Create an S3 bucket in your chosen region.
- Leave **Block all public access** enabled.
- Do not enable static website hosting.
- Decide on a prefix such as `reports/` for uploaded artifacts.

## 2. Create the CloudFront distribution
- Create a CloudFront distribution with the S3 bucket as the origin.
- Use **Origin Access Control (OAC)** so CloudFront, not the public internet, can read the bucket.
- Keep the default `*.cloudfront.net` hostname; custom domains are deferred.
- Record the distribution ID and distribution URL for `config.yaml`.

See [cloudfront_oac_notes.md](cloudfront_oac_notes.md) for the minimal OAC-specific checklist.

## 3. Attach the bucket policy
- Update [bucket_policy.json](bucket_policy.json) with your bucket name, AWS account ID, and CloudFront distribution ARN.
- Attach the policy to the bucket.
- This policy allows only the specific CloudFront distribution to read objects from the bucket.

## 4. Create a least-privilege IAM user for publishing
- Create an IAM user or access key pair used only for report publishing.
- Attach a policy based on [iam_policy.json](iam_policy.json).
- Scope the bucket ARN, prefix, and CloudFront distribution ARN to your resources only.

Required permissions:
- `s3:ListBucket`
- `s3:GetObject`
- `s3:PutObject`
- `s3:DeleteObject`
- `cloudfront:CreateInvalidation`
- `cloudfront:GetInvalidation`

## 5. Configure local AWS credentials
Use the standard AWS credential chain. Examples:
- `aws configure`
- environment variables such as `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
- an IAM role if you are running this from an AWS host

Do **not** put AWS keys in `config.yaml`.

## 6. Update project config
Fill in the `publishing` section in `config.yaml`:

```yaml
publishing:
  enabled: true
  s3:
    bucket: "your-report-bucket"
    region: "eu-west-1"
    prefix: "reports/"
  cloudfront:
    distribution_id: "E1234567890ABC"
    distribution_url: "https://d123example.cloudfront.net"
```

## 7. Run publish
Dry run first:

```bash
PYTHONPATH=src .venv/bin/python3 -m finance_data_platform.publishing.run_publish --dry-run
```

Then publish:

```bash
make publish
```

## HTTPS note
The default `*.cloudfront.net` hostname already serves over AWS-managed HTTPS. Custom domain and ACM certificate setup are deferred.

## Cost note
Typical costs for this project are very small. S3 storage is usually well under $0.10/month for report-sized artifacts. CloudFront includes a 1 TB free tier for egress; beyond that, pricing is roughly $0.085/GB in many regions. The first 1,000 invalidation paths per month are free, then about $0.005 per path. For the traffic volume expected here, total monthly cost is typically in the $0-1 range.

## Operational notes
If a publish appears to succeed but you do not see the updated report:
- check that the changed object reached the expected S3 prefix
- check the CloudFront invalidation status in the AWS console
- confirm the invalidation path matches the changed object key
- allow a few minutes for CloudFront propagation after invalidation
- confirm the report HTML points to `assets/report_styles.css` and that the CSS object was uploaded
