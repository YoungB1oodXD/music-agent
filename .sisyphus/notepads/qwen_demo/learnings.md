## Defense-Day Reliability Improvements
- Improved PowerShell launcher with robust path handling using `$PSScriptRoot.
- Added artifact existence checks to prevent demo-day failures due to missing indices/models.
- Increased health check and warmup timeouts to accommodate cold-start latency (up to 5 minutes).
- Updated runbook with concrete demo scenarios, verification steps, and a clear fallback plan.

