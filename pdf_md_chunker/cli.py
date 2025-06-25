from pathlib import Path


import typer


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
    from .extract import extract_content
    from .outline import parse_outline
    from .chunker import Chunker
    from .utils import sha256sum, slugify

    book_slug = slugify(book_slug)
    out_dir = out_dir / book_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo("👉 Витягаю текст та зображення з PDF…")
    blocks, img_bytes = extract_content(pdf_path)
    typer.echo(f"   Блоків тексту: {len(blocks)}, вбудованих зображень: {len(img_bytes)}")

    outline_pages = {p for _, p in parse_outline(pdf_path)}

    typer.echo("👉 Розбиваю на chunks…")
    chunker = Chunker(target_tokens=chunk_tokens, max_tokens=chunk_max, outline_pages=outline_pages)
    chunks = chunker.split_blocks(blocks)
    typer.echo(f"   Згенеровано {len(chunks)} частин")

    # ---- Зберігаємо частини та зображення ----
    # build page→images mapping
    images_map: dict[int, list[bytes]] = {}
    for bts, pg in img_bytes:
        images_map.setdefault(pg, []).append(bts)

    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        convert_from_path = None  # type: ignore

    for idx, chunk in enumerate(chunks, 1):
        part_suffix = f"part-{idx:04d}"
        part_dir = out_dir / f"{part_suffix}_{book_slug}"
        part_dir.mkdir(parents=True, exist_ok=True)

        # 1. Markdown текст
        md_path = part_dir / f"{book_slug}_{part_suffix}_text.md"
        md_path.write_text(chunk.text, encoding="utf-8")

        # 2. Зображення (за наявності pdf2image)
        images: list[str] = []
        # save embedded images first
        seq = 1
        for pg in range(chunk.page_start, chunk.page_end + 1):
            for data in images_map.get(pg, []):
                img_name = f"{book_slug}_{part_suffix}_img-{seq:04d}.png"
                (part_dir / img_name).write_bytes(data)
                images.append(img_name)
                seq += 1

        # fallback: snapshot page if no embedded images & pdf2image available
        if not images and convert_from_path is not None:
            try:
                pages_imgs = convert_from_path(
                    str(pdf_path),
                    fmt="png",
                    first_page=chunk.page_start,
                    last_page=chunk.page_end,
                    thread_count=2,
                    output_folder=str(part_dir),
                    paths_only=True,
                    output_file=f"{book_slug}_{part_suffix}_snap",
                )
                images = [Path(p).name for p in pages_imgs if isinstance(p, str)]
            except Exception as e:
                typer.echo(f"⚠️  Помилка конвертації snapshot-зображень: {e}")

        # 3. meta.json
        meta = {
            "part_id": f"{book_slug}_{part_suffix}",
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "tokens": chunk.tokens,
            "images": images,
            "source_pdf": pdf_path.name,
            "checksum": f"sha256:{sha256sum(md_path)}",
            "created": datetime.now(timezone.utc).isoformat(),
        }
        (part_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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

    # README
    readme_path = out_dir / "README.md"
    if not readme_path.exists():
        readme_content = f"""# {manifest['title']}

Цей набір файлів згенеровано утилітою **pdf-md-chunker** та придатний для імпорту у *NotebookLM*.

Запустіть команду імпорту, обравши каталог `{out_dir.name}`. Кожний підкаталог *part-XXXX* містить Markdown текст та пов'язані зображення.
"""
        readme_path.write_text(readme_content, encoding="utf-8")

    typer.echo("✅ Готово!")


@app.command()
def validate(book_dir: Path = typer.Argument(..., exists=True, dir_okay=True)):
    """Validate the exported book directory structure and metadata."""
    import json
    from .utils import token_count

    manifest_path = book_dir / "book_manifest.json"
    if not manifest_path.exists():
        typer.secho("❌ Не знайдено book_manifest.json", fg=typer.colors.RED)
        raise typer.Abort()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk_max = int(manifest.get("chunk_token_max", 3200))

    part_dirs = sorted(p for p in book_dir.iterdir() if p.is_dir())
    errors = 0
    for part in part_dirs:
        md_files = list(part.glob("*_text.md"))
        if len(md_files) != 1:
            typer.secho(f"❌ {part.name}: очікується один *_text.md, знайдено {len(md_files)}", fg=typer.colors.RED)
            errors += 1
            continue
        md_path = md_files[0]
        meta_path = part / "meta.json"
        if not meta_path.exists():
            typer.secho(f"❌ {part.name}: meta.json відсутній", fg=typer.colors.RED)
            errors += 1
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        # tokens check
        real_tokens = token_count(md_path.read_text(encoding="utf-8"))
        if real_tokens != meta["tokens"]:
            typer.secho(f"⚠️  {part.name}: tokens у meta={meta['tokens']}, по факту={real_tokens}", fg=typer.colors.YELLOW)

        if real_tokens > chunk_max:
            typer.secho(f"❌ {part.name}: {real_tokens}>{chunk_max} токенів", fg=typer.colors.RED)
            errors += 1

        # images existence
        for img in meta.get("images", []):
            if not (part / img).exists():
                typer.secho(f"❌ {part.name}: відсутнє зображення {img}", fg=typer.colors.RED)
                errors += 1

    if errors == 0:
        typer.secho("✅ Валідно", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ Знайдено {errors} помилок", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app() 