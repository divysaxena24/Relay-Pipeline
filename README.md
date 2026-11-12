# Relay: Resilient RAG and LLM Control Pipeline

Relay is a production-grade, fault-tolerant Retrieval-Augmented Generation (RAG) pipeline designed for academic literature question answering. It integrates document ingestion, BM25-based information retrieval, two-stage evidence verification with generation, and resilient traffic control mechanisms (rate limiting, bounded concurrency, and exponential backoff retry policies).

---

## Architectural Overview

Relay decouples retrieval, traffic control, and model invocation. The system routes incoming queries through an indexed corpus of research papers, validates retrieval relevance through an evidence filter, and coordinates LLM calls through a centralized request controller.

```mermaid
flowchart TD
    User([User Query]) --> RP[ResearchPipeline]
    
    subgraph RetrievalStage [Retrieval Stage]
        RP --> BM25[BM25 Retriever]
        BM25 --> Corpus[(Indexed Document Chunks)]
        Corpus --> Context[Top-K Passage Aggregator]
    end

    subgraph ControlPlane [Request Controller & Resiliency Layer]
        Context --> RC[RequestController]
        RC --> RL[RateLimiter - Sliding Window]
        RL --> CL[ConcurrencyLimiter - Semaphore]
        CL --> RB[Retry Mechanism - Exponential Backoff]
    end

    subgraph ExecutionPlane [Model Execution Layer]
        RB --> Provider{Model Provider}
        Provider -->|Live API| Groq[GroqClient Llama-3.3 / GPT-OSS]
        Provider -->|Offline / Testing| StandIn[StandInModel Mock Provider]
    end

    subgraph EvaluationStage [Validation & Grounding]
        Groq --> Decision{Evidence Sufficient?}
        StandIn --> Decision
        Decision -->|No| Refusal[Refusal Response Status: refused]
        Decision -->|Yes| AnswerGen[Answer Generation with Source Citations]
        AnswerGen --> CitationValidation[Citation & Hallucination Validator]
        CitationValidation --> Output([Structured JSON Output])
    end
```

---

## System Component Breakdown

### 1. Document Ingestion and Chunking (`app/retrieval/`)
- **Ingestion (`ingestion.py`)**: Parses PDF research papers (such as Attention Is All You Need, Moshi, and Dynamic Chunking) and extracts raw text page-by-page.
- **Chunking (`chunking.py`)**: Divides document text into overlapping token windows to preserve inter-sentence context across segment boundaries.
- **Retriever (`bm25_retriever.py`)**: Builds an in-memory Okapi BM25 inverted index across chunks for fast lexical retrieval.

### 2. Traffic Control and Resiliency (`app/control/`)
- **Request Controller (`request_controller.py`)**: Unified entrypoint wrapping remote model invocations.
- **Rate Limiter (`rate_limiter.py`)**: Thread-safe sliding-window limiter enforcing client-side maximum request frequencies (e.g., 25 requests per 60 seconds).
- **Concurrency Limiter (`concurrency.py`)**: Thread-safe bounded semaphore restricting parallel in-flight network requests to upstream endpoints.
- **Retry Logic (`retry.py`)**: Exponential backoff algorithm capturing transient network failures (`429`, `500`, `502`, `503`, `504`, timeouts, connection drops) with configurable maximum attempts and jitter delays.

### 3. Model Providers (`app/providers/` and `standin/`)
- **Model Provider Interface (`base.py`)**: Abstract `runtime_checkable` protocol establishing standardized contracts for `generate()` and `check_evidence()`.
- **Groq Client (`groq_client.py`)**: Integration client interfacing with the Groq Chat Completions API.
- **Stand-In Simulator (`standin/model.py`)**: Standalone deterministic simulator capable of mimicking model response latencies, synthetic rate limits (429 errors), intermittent server errors (500 errors), and query refusal decisions without incurring external API costs.

### 4. End-to-End Orchestrator (`app/pipeline/`)
- **Research Pipeline (`research_pipeline.py`)**: Orchestrates the multi-step lifecycle:
  1. Lexical retrieval of top-K chunks.
  2. Synthesizing context with unique citation tags (`[S1]`, `[S2]`, ...).
  3. Evidence verification gate through `check_evidence()`.
  4. Answer generation with citation constraints.
  5. Deterministic validation verifying all cited source keys exist in retrieved context.

---

## Pipeline Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Pipeline as ResearchPipeline
    participant BM25 as BM25Retriever
    participant RC as RequestController
    participant Provider as ModelProvider

    Client->>Pipeline: run(question)
    Pipeline->>BM25: search(query, top_k)
    BM25-->>Pipeline: passages

    alt No Passages Found
        Pipeline-->>Client: status: "refused" (No relevant passages)
    else Passages Found
        Pipeline->>Pipeline: build_context(passages)
        Pipeline->>RC: execute(check_evidence, question, context)
        RC->>Provider: check_evidence(...)
        Provider-->>RC: evidence_result
        RC-->>Pipeline: evidence_result, retries

        alt Insufficient Evidence
            Pipeline-->>Client: status: "refused" (Insufficient evidence)
        else Evidence Confirmed
            Pipeline->>RC: execute(generate, question, context)
            RC->>Provider: generate(...)
            Provider-->>RC: answer_payload
            RC-->>Pipeline: answer_payload, retries
            Pipeline->>Pipeline: validate_citations(answer)
            Pipeline-->>Client: status: "answered", citations, metrics
        end
    end
```

---

## Project Structure

```
Relay/
├── app/
│   ├── control/
│   │   ├── concurrency.py         # Thread-safe concurrency semaphore
│   │   ├── rate_limiter.py        # Sliding-window rate limiter
│   │   ├── request_controller.py  # Central resilient execution coordinator
│   │   └── retry.py               # Exponential backoff retry handler
│   ├── pipeline/
│   │   └── research_pipeline.py   # Complete multi-stage RAG orchestrator
│   ├── providers/
│   │   ├── base.py                # ModelProvider typing protocol
│   │   └── groq_client.py         # Production Groq API implementation
│   └── retrieval/
│       ├── bm25_retriever.py      # Okapi BM25 search engine
│       ├── chunking.py            # Overlapping chunk generator
│       └── ingestion.py           # Document extraction loader
├── data/
│   ├── chunks.json                # Pre-built indexed corpus chunks
│   └── pages.json                 # Ingested PDF page documents
├── evaluation/
│   └── questions.json             # Benchmark questions (factual, multi-passage, cross-paper, unanswerable)
├── papers/
│   ├── attention_v7.pdf           # Attention Is All You Need (Vaswani et al.)
│   ├── dynamic_chunking_v2.pdf    # Dynamic Chunking for RAG
│   └── moshi_v1.pdf               # Moshi: Real-Time Audio Language Model
├── results/
│   ├── results.csv                # Baseline pipeline latency benchmark results
│   └── retrieval_eval.csv         # Comparative chunking configuration benchmarks
├── scripts/
│   ├── build_chunks.py            # Utility to build chunk datasets
│   ├── evaluate_retrieval.py      # Benchmark script comparing chunk parameters
│   ├── ingest.py                  # Utility to extract pages from papers
│   ├── inspect_scores.py          # Diagnostic query score inspector
│   ├── measure_groq.py            # Latency benchmark tool for Groq API
│   ├── search_chunks.py           # Interactive CLI query testing tool
│   ├── test_concurrency.py        # Unit test for parallel concurrency locks
│   ├── test_groq.py               # Integration test for Groq API
│   ├── test_pipeline.py           # End-to-end integration test
│   ├── test_pipeline_retries.py   # Resiliency test with simulated flaky provider
│   ├── test_provider_interface.py # Protocol compatibility tests
│   ├── test_rate_limiter.py       # Sliding-window rate limit test
│   ├── test_request_controller.py # Combined controller test
│   ├── test_retry.py              # Unit tests for exponential backoff
│   └── test_standin.py            # Unit tests for stand-in simulator
├── standin/
│   └── model.py                   # Offline fault-injection mock LLM provider
├── requirements.txt               # Project dependencies
└── README.md
```

---

## Installation and Setup

### 1. Prerequisites
- Python 3.12+
- Virtual environment support

### 2. Environment Configuration
Clone the repository and set up a virtual environment:

```bash
python -m venv .venv

# On Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# On Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. API Key Setup
Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

---

## Verification and Test Execution Outputs

The suite includes verification scripts testing offline simulator components, concurrency boundaries, rate limit enforcement, retry mechanisms, and full-pipeline fault tolerance.

### 1. Overall Test Suite Results

| Test Script | Test ID / Case Description | Conditions / Parameters | Observed Output / Metrics | Status |
|---|---|---|---|---|
| `scripts/test_standin.py` | TEST 1: Normal request | Default latency (~100 ms) | Latency: 100.68 ms | PASS |
| `scripts/test_standin.py` | TEST 2: Simulated failure | `failure_rate = 1.0` | Raised `StandInError` as expected | PASS |
| `scripts/test_standin.py` | TEST 3: Simulated rate limit | `rate_limit_every = 2` | Raised `StandInRateLimitError` (HTTP 429) | PASS |
| `scripts/test_standin.py` | TEST 4: Slow response | `latency_ms = 500` | Measured latency: 500.62 ms | PASS |
| `scripts/test_standin.py` | TEST 5: Refusal | `refusal_rate = 1.0` | "I cannot answer this reliably..." | PASS |
| `scripts/test_standin.py` | TEST 6: Streaming response | Stream generator | Complete response tokens streamed | PASS |
| `scripts/test_rate_limiter.py` | TEST 1: Burst allowance | 3 requests, window 1.0s | All 3 dispatched immediately | PASS |
| `scripts/test_rate_limiter.py` | TEST 2: Excess request waits | 4th request exceeds quota | Thread blocked until quota cleared | PASS |
| `scripts/test_rate_limiter.py` | TEST 3: Window refresh | Wait > window duration | Capacity restored; request allowed | PASS |
| `scripts/test_concurrency.py` | TEST: Concurrency ceiling | `max_concurrent = 2`, 4 tasks | Peak concurrent tasks observed: 2 | PASS |
| `scripts/test_retry.py` | TEST 1: Transient recovery | Fails 1st attempt, succeeds 2nd | Successfully returned result | PASS |
| `scripts/test_retry.py` | TEST 2: Exponential backoff | `base_delay = 0.25s`, 2 retries | Backoff delay observed (0.25s -> 0.50s) | PASS |
| `scripts/test_retry.py` | TEST 3: Max retries limit | Continuous failure, `max_retries = 2` | Re-raised exception after 2 retries | PASS |
| `scripts/test_retry.py` | TEST 4: Non-retryable error | `ValueError` | Immediate failure without retry | PASS |
| `scripts/test_request_controller.py` | TEST 1: Controller retry loop | Temporary fault in upstream | Caught, retried, and recovered | PASS |
| `scripts/test_request_controller.py` | TEST 2: Normal request execution | Successful invocation | Result returned with retry count = 0 | PASS |
| `scripts/test_provider_interface.py` | TEST 1: GroqClient interface | Subclass/protocol check | Implements ModelProvider protocol | PASS |
| `scripts/test_provider_interface.py` | TEST 2: StandInModel interface | Subclass/protocol check | Implements ModelProvider protocol | PASS |
| `scripts/test_provider_interface.py` | TEST 3: Stand-in generate schema | Output schema verification | Valid response with tokens and latency | PASS |
| `scripts/test_provider_interface.py` | TEST 4: Stand-in evidence schema | Output schema verification | Valid evidence decision dictionary | PASS |
| `scripts/test_pipeline_retries.py` | End-to-end pipeline resiliency | Simulated flaky evidence & generation | Evidence retries: 1, Generation retries: 1 | PASS |

---

### 2. End-to-End Pipeline Fault Tolerance Output

Tested via `scripts/test_pipeline_retries.py` against a flaky provider simulating independent transient errors during evidence verification and answer generation:

| Pipeline Stage | Injected Failure | Total Provider Invocations | Retries Consumed | Final Stage Status |
|---|---|---|---|---|
| Index Initialization | None | N/A | 0 | BM25 index built with 315 chunks |
| Evidence Checking | Simulated `StandInError` on attempt 1 | 2 | 1 | Verified evidence: sufficient |
| Answer Generation | Simulated `StandInError` on attempt 1 | 2 | 1 | Complete generated answer |
| Overall Pipeline Run | None | 4 | 2 | Status: `answered` |

---

### 3. BM25 Query Relevance Diagnostics

Extracted from `scripts/inspect_scores.py` comparing lexical retrieval scores on answerable research queries versus out-of-domain unanswerable queries:

| Query Type | Query Text | Rank | Target Paper | Page Number | BM25 Score |
|---|---|---|---|---|---|
| Answerable | How does scaled dot-product attention work? | 1 | attention | Page 4 | 26.4676 |
| Answerable | How does scaled dot-product attention work? | 2 | attention | Page 4 | 17.6409 |
| Answerable | How does scaled dot-product attention work? | 3 | attention | Page 1 | 17.3404 |
| Answerable | How does Moshi enable real-time speech dialogue? | 1 | moshi | Page 7 | 11.8901 |
| Answerable | How does Moshi enable real-time speech dialogue? | 2 | moshi | Page 62 | 10.5020 |
| Answerable | How does Moshi enable real-time speech dialogue? | 3 | moshi | Page 1 | 10.3981 |
| Unanswerable | What is the current NVIDIA stock price? | 1 | attention | Page 15 | 10.2110 |
| Unanswerable | What is the current NVIDIA stock price? | 2 | attention | Page 14 | 10.0834 |
| Unanswerable | What is the current NVIDIA stock price? | 3 | dynamic_chunking | Page 9 | 9.4590 |
| Unanswerable | What is the best Java programming course? | 1 | moshi | Page 63 | 13.0191 |
| Unanswerable | What is the best Java programming course? | 2 | moshi | Page 65 | 10.5204 |
| Unanswerable | What is the best Java programming course? | 3 | moshi | Page 30 | 10.4746 |

---

## Retrieval Evaluation Benchmarks

The retrieval module was benchmarked across three chunking and search configurations using the 15-question evaluation suite (`evaluation/questions.json`):

| Metric | Setting A (250 words, Overlap 50, Top-3) | Setting B (500 words, Overlap 50, Top-5) | Setting C (800 words, Overlap 50, Top-5) |
|---|---|---|---|
| Generated Chunks | 315 | 184 | 122 |
| Expected Papers Found | 11 / 13 | 11 / 13 | 12 / 13 |
| Average Expected-Term Coverage | 92.31% | 98.08% | 100.00% |
| Out-of-Domain Refusal Gate | Filtered at Evidence Check | Filtered at Evidence Check | Filtered at Evidence Check |

### Benchmark Execution Output
```text
Loaded 120 pages.
Loaded 15 questions.

Evaluating setting A (Chunk size: 250 words, Top-K: 3):
- Generated chunks: 315
- All expected papers retrieved: 11/13
- Average expected-term coverage: 92.31%

Evaluating setting B (Chunk size: 500 words, Top-K: 5):
- Generated chunks: 184
- All expected papers retrieved: 11/13
- Average expected-term coverage: 98.08%

Evaluating setting C (Chunk size: 800 words, Top-K: 5):
- Generated chunks: 122
- All expected papers retrieved: 12/13
- Average expected-term coverage: 100.00%

Saved detailed results to: results/retrieval_eval.csv
```

---

## Production Execution Baseline Latency

Measurements recorded during sequential execution against live endpoints (`results/results.csv`):

| Request ID | Scenario | Status | Retries | Total Latency (ms) | Tokens In | Tokens Out |
|---|---|---|---|---|---|---|
| `real-baseline-01` | baseline_sequential | ok | 0 | 2432.77 | 189 | 353 |
| `real-baseline-02` | baseline_sequential | ok | 0 | 572.59 | 189 | 354 |
| `real-baseline-03` | baseline_sequential | ok | 0 | 298.23 | 189 | 174 |
| `real-baseline-04` | baseline_sequential | ok | 0 | 523.03 | 189 | 255 |
| `real-baseline-05` | baseline_sequential | ok | 0 | 702.36 | 189 | 188 |

