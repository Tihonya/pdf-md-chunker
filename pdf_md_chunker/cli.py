from pathlib import Path

try:
    import typer
except ImportError:
    raise ImportError(
        "Typer is required but not installed. "
        "Please install it with: pip install typer"
    )

app = typer.Typer(add_completion=False, help="PDF → Markdown-Chunks CLI")

@app.command()
def split(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    book_slug: str = typer.Option(..., "--book-slug", "-s", help="Slug for the book"),
    out_dir: Path = typer.Option(
        Path("./exports"), "--out-dir", "-o", dir_okay=True, help="Output directory"
    ),
    chunk_tokens: int = typer.Option(1500, "--chunk-tokens", help="Target chunk size (tokens)"),
    chunk_max: int = typer.Option(3200, "--chunk-max", help="Hard token limit per chunk"),
    lang: str = typer.Option("auto", "--lang", help="Language: en / uk / auto"),
):
    """Split a PDF book into Markdown chunks according to the technical specification."""
    from datetime import datetime, timezone
    import json
    import os
    from .extract import extract_blocks
    from .chunker import Chunker
    from .utils import sha256sum, slugify

    book_slug = slugify(book_slug)
    out_dir = out_dir / book_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo("👉 Витягаю текст з PDF…")
    blocks = extract_blocks(pdf_path)
    typer.echo(f"   Отримано {len(blocks)} блоків")

    typer.echo("👉 Розбиваю на chunks…")
    chunker = Chunker(target_tokens=chunk_tokens, max_tokens=chunk_max)
    chunks = chunker.split_blocks(blocks)
    typer.echo(f"   Згенеровано {len(chunks)} частин")

    # write chunks
    for idx, chunk in enumerate(chunks, 1):
        part_id = f"part-{idx:04d}_{book_slug}"
        part_dir = out_dir / part_id
        part_dir.mkdir(parents=True, exist_ok=True)
        md_path = part_dir / f"{book_slug}_{part_id}_text.md"
        md_path.write_text(chunk.text, encoding="utf-8")

        meta = {
            "part_id": f"{book_slug}_{part_id}",
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "tokens": chunk.tokens,
            "images": [],  # TODO: image support
            "source_pdf": pdf_path.name,
            "checksum": f"sha256:{sha256sum(md_path)}",
            "created": datetime.now(timezone.utc).isoformat(),
        }
        (part_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    # manifest
    manifest = {
        "book_id": book_slug,
        "title": book_slug.replace("-", " ").title(),
        "author": "",  # unknown
        "language": lang,
        "parts": len(chunks),
        "chunk_token_target": chunk_tokens,
        "chunk_token_max": chunk_max,
        "generated": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "book_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    typer.echo("✅ Готово!")


@app.command()
def validate(book_dir: Path = typer.Argument(..., exists=True, dir_okay=True)):
    """Validate the exported book directory structure and metadata."""
    typer.echo(f"[stub] Validating export at '{book_dir}'…")
    # TODO: Implement validation logic


if __name__ == "__main__":
    app() 