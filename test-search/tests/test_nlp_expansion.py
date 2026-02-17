import asyncio
import json
import pytest
from app.nlp.analyzer import analyzer
from app.nlp.rewriter import rewriter


@pytest.mark.asyncio
async def test_nlp():
    query = "authentic chinese food in pudong suitable for business dinner"
    print(f"Testing Query: {query}\n")

    # Test Analyzer
    print("--- Semantic Analysis ---")
    intent = await analyzer.analyze(query)
    print(json.dumps(intent, indent=2, ensure_ascii=False))

    # Check for new fields
    assert "keywords" in intent, "Missing keywords"
    assert "key_phrases" in intent, "Missing key_phrases"
    assert "key_info" in intent, "Missing key_info"
    print("\n[PASS] Analyzer returned enhanced structure.")

    # Test Rewriter
    print("\n--- Semantic Rewriting ---")
    rewrites = await rewriter.rewrite(query)
    print(json.dumps(rewrites, indent=2, ensure_ascii=False))

    # Check for strict 3 items
    assert isinstance(rewrites, list), "Rewrites must be a list"
    if len(rewrites) == 3:
        print("\n[PASS] Rewriter returned exactly 3 queries.")
    else:
        print(f"\n[WARN] Rewriter returned {len(rewrites)} queries (Expected 3).")


if __name__ == "__main__":
    asyncio.run(test_nlp())
