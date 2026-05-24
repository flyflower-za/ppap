import pytest
import asyncio
from app.checkers.sig_verifier import verify_pdf_signatures


@pytest.mark.asyncio
async def test_sig_verifier_empty_pdf():
    """Test signature verifier handles empty/invalid input gracefully."""
    results = await verify_pdf_signatures(b"")
    assert results["signed"] is False
    assert results["signatures"] == []

    results2 = await verify_pdf_signatures(b"not a pdf at all")
    assert results2["signed"] is False
    assert results2["signatures"] == []
