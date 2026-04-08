"""Typer CLI app for cliptrans."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from cliptrans.adapters.persistence.database import create_tables
from cliptrans.config import get_config
from cliptrans.di import make_job_repository, make_pipeline
from cliptrans.domain.enums import ExportFormat, JobStatus
from cliptrans.domain.models import Job, JobConfig

cli_app = typer.Typer(
    name="cliptrans",
    help="翻訳付き切り抜き動画制作ツール",
    no_args_is_help=True,
)

console = Console()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


# run


@cli_app.command()
def run(
    url: Annotated[
        str | None, typer.Argument(help="Source video URL (omit if using --local-file)")
    ] = None,
    start: Annotated[
        float | None, typer.Option("--start", "-s", help="Start time in seconds")
    ] = None,
    end: Annotated[float | None, typer.Option("--end", "-e", help="End time in seconds")] = None,
    source_lang: Annotated[str, typer.Option("--source-lang")] = "ja",
    target_lang: Annotated[str, typer.Option("--target-lang")] = "en",
    asr_model: Annotated[str, typer.Option("--asr-model")] = "large-v3",
    export_formats: Annotated[list[ExportFormat] | None, typer.Option("--format", "-f")] = None,
    no_translate: Annotated[
        bool, typer.Option("--no-translate", help="Skip translation step")
    ] = False,
    local_file: Annotated[
        Path | None,
        typer.Option("--local-file", help="Use a local video/audio file instead of downloading"),
    ] = None,
    resume: Annotated[
        UUID | None, typer.Option("--resume", help="Resume an existing job by ID")
    ] = None,
) -> None:
    """Run the full pipeline: download → transcribe → translate → export.

    Examples:

      # YouTube URL の区間を切り抜いて翻訳
      cliptrans run 'https://youtu.be/XXXX' --start 3600 --end 3900

      # ローカルファイルを使う (ダウンロードをスキップ)
      cliptrans run --local-file video.mp4

    # Kdenlive に読み込みやすい bilingual SRT を出力
    cliptrans run --local-file video.mp4 --format kdenlive

      # 翻訳なしで字幕のみ生成
      cliptrans run --local-file video.mp4 --no-translate

      # 中断したジョブを再開
      cliptrans run --resume <job-id>
    """
    if export_formats is None:
        export_formats = [ExportFormat.SRT]
    if url is None and local_file is None and resume is None:
        console.print("[red]URL か --local-file か --resume のいずれかを指定してください。[/red]")
        raise typer.Exit(1)
    asyncio.run(
        _run_pipeline(
            url=url,
            start=start,
            end=end,
            source_lang=source_lang,
            target_lang=target_lang,
            asr_model=asr_model,
            export_formats=export_formats,
            no_translate=no_translate,
            local_file=local_file,
            resume_id=resume,
        )
    )


async def _run_pipeline(
    *,
    url: str | None,
    start: float | None,
    end: float | None,
    source_lang: str,
    target_lang: str,
    asr_model: str,
    export_formats: list[ExportFormat],
    no_translate: bool,
    local_file: Path | None,
    resume_id: UUID | None,
) -> None:
    cfg = get_config()
    await create_tables(cfg.database_url)

    repo = make_job_repository(cfg)
    pipeline = make_pipeline(cfg)

    effective_target = source_lang if no_translate else target_lang

    if resume_id is not None:
        job = await repo.get(resume_id)
        if job is None:
            console.print(f"[red]Job {resume_id} not found.[/red]")
            raise typer.Exit(1)
        console.print(f"Resuming job [bold]{job.id}[/bold] from stage {job.current_stage}")
    else:
        source_url = url or (f"file://{local_file.resolve()}" if local_file else "")
        now = datetime.now(UTC)
        job = Job(
            config=JobConfig(
                source_url=source_url,
                start_time=start,
                end_time=end,
                source_language=source_lang,
                target_language=effective_target,
                asr_model=asr_model,
                export_formats=export_formats,
            ),
            created_at=now,
            updated_at=now,
        )
        await repo.save(job)
        console.print(f"Created job [bold]{job.id}[/bold]")

    try:
        job = await pipeline.run(job, local_file=local_file)
    except Exception as exc:
        console.print(f"[red]Pipeline failed: {exc}[/red]")
        raise typer.Exit(1) from None

    console.print(f"[green]Job {job.id} completed.[/green]")
    if job.data_dir:
        console.print(f"Output: {job.data_dir / 'output'}")


# jobs


@cli_app.command("jobs")
def list_jobs(
    status: Annotated[JobStatus | None, typer.Option("--status")] = None,
) -> None:
    """List all jobs."""
    asyncio.run(_list_jobs(status))


async def _list_jobs(status: JobStatus | None) -> None:
    cfg = get_config()
    await create_tables(cfg.database_url)
    repo = make_job_repository(cfg)
    jobs = await repo.list_jobs(status=status)

    if not jobs:
        console.print("No jobs found.")
        return

    table = Table("ID", "Status", "Stage", "URL", "Created")
    for j in jobs:
        table.add_row(
            str(j.id),
            j.status,
            j.current_stage or "-",
            j.config.source_url[:60],
            j.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


# show


@cli_app.command("show")
def show_job(
    job_id: Annotated[UUID, typer.Argument(help="Job ID")],
) -> None:
    """Show details of a specific job."""
    asyncio.run(_show_job(job_id))


async def _show_job(job_id: UUID) -> None:
    cfg = get_config()
    await create_tables(cfg.database_url)
    repo = make_job_repository(cfg)
    job = await repo.get(job_id)
    if job is None:
        console.print(f"[red]Job {job_id} not found.[/red]")
        raise typer.Exit(1)

    console.print(job.model_dump_json(indent=2))
