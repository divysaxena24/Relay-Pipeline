
import csv
import json
from pathlib import Path

from app.retrieval.chunking import chunk_pages
from app.retrieval.bm25_retriever import BM25Retriever


PAGES_PATH = Path("data/pages.json")
QUESTIONS_PATH = Path("evaluation/questions.json")
OUTPUT_PATH = Path("results/retrieval_eval.csv")

CONFIGURATIONS = [
    {"setting_id": "A", "chunk_size": 250, "overlap": 50, "top_k": 3},
    {"setting_id": "B", "chunk_size": 500, "overlap": 50, "top_k": 5},
    {"setting_id": "C", "chunk_size": 800, "overlap": 50, "top_k": 5},
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_term_coverage(results, expected_terms):
    """Fraction of expected terms found in the retrieved passages."""
    if not expected_terms:
        return 0.0

    retrieved_text = " ".join(
        result["text"].lower() for result in results
    )

    matched = sum(
        1 for term in expected_terms
        if term.lower() in retrieved_text
    )

    return round(matched / len(expected_terms), 3)


def evaluate():
    pages = load_json(PAGES_PATH)
    questions = load_json(QUESTIONS_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []

    print(f"Loaded {len(pages)} pages.")
    print(f"Loaded {len(questions)} questions.")

    for config in CONFIGURATIONS:
        setting_id = config["setting_id"]

        print(f"\n{'=' * 55}")
        print(f"Evaluating setting {setting_id}")
        print(f"Chunk size: {config['chunk_size']} words")
        print(f"Top-K: {config['top_k']}")
        print(f"{'=' * 55}")

        chunks = chunk_pages(
            pages,
            chunk_size=config["chunk_size"],
            overlap=config["overlap"],
        )

        print(f"Generated chunks: {len(chunks)}")

        retriever = BM25Retriever(chunks)

        for question in questions:
            results = retriever.search(
                question["question"],
                top_k=config["top_k"],
            )

            expected_papers = set(question["expected_papers"])
            retrieved_papers = {
                result["paper_id"] for result in results
            }

            if expected_papers:
                matched_papers = expected_papers & retrieved_papers
                paper_coverage = round(
                    len(matched_papers) / len(expected_papers), 3
                )
                all_expected_papers_found = (
                    expected_papers.issubset(retrieved_papers)
                )
            else:
                matched_papers = set()
                paper_coverage = 0.0
                all_expected_papers_found = False

            term_coverage = calculate_term_coverage(
                results,
                question["expected_terms"],
            )

            top_score = results[0]["score"] if results else 0.0

            row = {
                "setting_id": setting_id,
                "chunk_size_words": config["chunk_size"],
                "overlap_words": config["overlap"],
                "top_k": config["top_k"],
                "question_id": question["id"],
                "category": question["category"],
                "answerable": question["answerable"],
                "expected_papers": ";".join(
                    sorted(expected_papers)
                ),
                "retrieved_papers": ";".join(
                    sorted(retrieved_papers)
                ),
                "retrieved_chunks": len(results),
                "top_score": top_score,
                "paper_coverage": paper_coverage,
                "all_expected_papers_found": (
                    all_expected_papers_found
                    if question["answerable"] else ""
                ),
                "expected_term_coverage": term_coverage,
                "retrieval_empty": len(results) == 0,
            }

            all_rows.append(row)

            print(
                f"{question['id']} | "
                f"Retrieved: {len(results)} | "
                f"Papers: {','.join(sorted(retrieved_papers)) or 'None'} | "
                f"Paper coverage: {paper_coverage}"
            )

    fieldnames = list(all_rows[0].keys())

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{'=' * 55}")
    print("RETRIEVAL EVALUATION SUMMARY")
    print(f"{'=' * 55}")

    for config in CONFIGURATIONS:
        setting_id = config["setting_id"]

        rows = [
            row for row in all_rows
            if row["setting_id"] == setting_id
        ]

        answerable_rows = [
            row for row in rows if row["answerable"]
        ]

        unanswerable_rows = [
            row for row in rows if not row["answerable"]
        ]

        paper_hits = sum(
            bool(row["all_expected_papers_found"])
            for row in answerable_rows
        )

        empty_unanswerable = sum(
            row["retrieval_empty"]
            for row in unanswerable_rows
        )

        avg_term_coverage = (
            sum(row["expected_term_coverage"] for row in answerable_rows)
            / len(answerable_rows)
            if answerable_rows else 0
        )

        print(f"\nSetting {setting_id}")
        print(
            f"All expected papers retrieved: "
            f"{paper_hits}/{len(answerable_rows)}"
        )
        print(
            f"Average expected-term coverage: "
            f"{avg_term_coverage:.2%}"
        )
        print(
            f"Unanswerable questions with empty retrieval: "
            f"{empty_unanswerable}/{len(unanswerable_rows)}"
        )

    print(f"\nSaved detailed results to: {OUTPUT_PATH}")


if __name__ == "__main__":
    evaluate()
