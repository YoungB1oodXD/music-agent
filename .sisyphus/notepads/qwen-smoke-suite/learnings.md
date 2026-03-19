## Qwen Real-Mode Smoke Suite
- Successfully implemented a real-mode smoke suite that verifies the entire pipeline (Qwen + Chroma + CF/Hybrid + /chat).
- Used `fastapi.testclient.TestClient` to test the API without starting a separate server process.
- Implemented a redacting logging handler to prevent API key leakage in reports and stdout.
- Handled `UnicodeEncodeError` for Windows console by replacing unencodable characters in the logging handler.
