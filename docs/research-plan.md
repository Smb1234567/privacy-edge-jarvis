# Research Plan (Draft)

## Candidate Research Question
How effectively can a 4B local LLM on 6GB VRAM perform multi-tool privacy-preserving agentic RAG compared to single-tool and non-agentic baselines, under strict edge constraints?

## Primary Hypotheses
1. Multi-tool orchestration improves task completion on mixed queries over single-tool execution.
2. Retrieval quality and tool-call precision trade off against latency on edge hardware.
3. An offline-first stack can remain practically usable for live demos with <=100 documents.

## Core Metrics
- Tool-call success rate
- Retrieval accuracy@k
- Faithfulness
- Hallucination rate
- End-to-end latency
- Resource usage (VRAM proxy/RAM/CPU)
