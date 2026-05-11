# CloudFront OAC Notes

Use Origin Access Control (OAC), not a public S3 bucket, for this project.

Checklist:
- origin is the private S3 bucket
- OAC is enabled on the CloudFront origin
- the bucket policy allows only the specific CloudFront distribution ARN to read objects
- direct S3 public access remains blocked

This keeps the bucket private while still allowing a shareable CloudFront URL for viewers.
