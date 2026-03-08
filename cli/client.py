import json
import asyncio
from typing import AsyncGenerator

import httpx

from .config import API_BASE, MAX_RETRIES, RETRY_DELAY


class APIClient:
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def close(self):
        await self.client.aclose()

    async def get_status(self) -> dict:
        res = await self.client.get(f"{self.base_url}/status")
        res.raise_for_status()
        return res.json()

    async def get_metrics(self) -> dict:
        res = await self.client.get(f"{self.base_url}/benchmark/metrics")
        res.raise_for_status()
        return res.json()

    async def chat_stream(self, query: str) -> AsyncGenerator[dict, None]:
        for attempt in range(MAX_RETRIES):
            try:
                async with self.client.stream(
                    "POST",
                    f"{self.base_url}/chat/stream",
                    json={"query": query},
                ) as res:
                    res.raise_for_status()
                    async for line in res.aiter_lines():
                        if line.strip():
                            yield json.loads(line)
                return
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                yield {"type": "error", "error": str(e)}
                return

    async def upload_files(self, files: list[str]) -> dict:
        form_data = []
        for f in files:
            with open(f, "rb") as fp:
                form_data.append(("files", (f.split("/")[-1], fp.read())))
        res = await self.client.post(f"{self.base_url}/ingest", files=form_data)
        res.raise_for_status()
        return res.json()


async def check_api_status() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{API_BASE}/status")
            return res.status_code == 200
    except Exception:
        return False
