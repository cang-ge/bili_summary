"""
bili_summary · Streamlit UI

启动方式：
    streamlit run app.py

打开浏览器访问 http://localhost:8501

功能：
1. 输入 B 站视频 URL
2. 一键运行完整流水线（带实时进度）
3. 在页面内预览封面 / 信息图 / 表格
4. 一键下载生成的 PDF / DOCX
"""
import json as _json
import os as _os
import subprocess as _sp
import threading as _th
import time as _time
from pathlib import Path
import streamlit as st

# Make src/ importable
import sys
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from pipeline import run_pipeline, detect_url_platform


# ============ Page Config ============
st.set_page_config(
    page_title='bili_summary · 视频一键总结',
    page_icon='🎬',
    layout='wide',
    initial_sidebar_state='expanded',
)
# Note: all theme colors are set via .streamlit/config.toml
# (primaryColor / backgroundColor / textColor / font).
# We deliberately avoid inline CSS injection — Streamlit 1.58+ changed
# many data-testid attributes which made our old CSS selectors stale and
# caused button/checkbox/heading text to lose contrast against the
# background. config.toml is the supported, future-proof way to theme.

# ============ Header ============
st.title('视频一键总结')
st.caption('B 站视频 · Whisper 转录 + 编辑级排版 + PDF / DOCX 导出')

# ============ Layout ============
col_left, col_right = st.columns([1, 1.6], gap='large')

# ---------- LEFT: Input panel ----------
with col_left:
    st.subheader('① 输入')

    url = st.text_input(
        '视频 URL',
        key='url_input',
        placeholder='https://www.bilibili.com/video/BVxxxxxxxxxx',
        help='粘贴 B 站视频链接',
    )

    if url:
        platform = detect_url_platform(url)
        if platform != 'unknown':
            st.success(f"✓ 已识别平台：**{platform}**")
        else:
            st.error("✗ 不支持的 URL 格式")

    use_cache = st.checkbox(
        '复用本地缓存',
        value=True,
        help='已下载 / 已转录过的视频会直接跳过对应步骤',
    )

    skip_transcribe = st.checkbox(
        '跳过 Whisper 转录',
        value=False,
        help='如已有官方字幕 / 之前转录过，可省时间',
    )

    run_btn = st.button(
        '🚀 开始生成',
        type='primary',
        use_container_width=True,
        disabled=not st.session_state.get('url_input', '')
                or detect_url_platform(st.session_state.get('url_input', '')) == 'unknown',
    )

# ---------- RIGHT: Output panel ----------
with col_right:
    st.subheader('② 输出')

    output_dir = Path(__file__).parent / 'output'
    assets_dir = output_dir / 'assets'

    # ===== File paths =====
    pdf_path = output_dir / 'summary.pdf'
    docx_path = output_dir / 'summary.docx'
    cover_path = assets_dir / 'cover.png'
    info_path = assets_dir / 'infographic.png'

    # ====== State machine (on first load, init) ======
    if 'pipeline_state' not in st.session_state:
        st.session_state.pipeline_state = None
        st.session_state.pipeline_messages = []
        st.session_state.pipeline_error = None
        st.session_state.pipeline_cancel_requested = False
        st.session_state.pipeline_done_signal = False

    state = st.session_state.pipeline_state

    # ================================================================
    #  START PIPELINE
    # ================================================================
    if run_btn and state is None:
        st.session_state.pipeline_state = 'running'
        st.session_state.pipeline_messages = []
        st.session_state.pipeline_error = None
        st.session_state.pipeline_raw_output = []
        st.session_state.pipeline_cancel_requested = False
        st.session_state.pipeline_done_signal = False

        cli_script = Path(__file__).parent / 'src' / 'run_pipeline_cli.py'
        cmd = [
            sys.executable, str(cli_script), url,
            '--out', str(output_dir),
        ]
        if not use_cache:
            cmd.append('--no-cache')
        if skip_transcribe:
            cmd.append('--skip-transcribe')

        # PYTHONIOENCODING=utf-8 ensures the subprocess can print emoji /
        # Chinese progress without UnicodeEncodeError on Windows (default gbk).
        proc_env = {**_os.environ, 'PYTHONIOENCODING': 'utf-8'}
        proc = _sp.Popen(
            cmd,
            stdout=_sp.PIPE, stderr=_sp.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            env=proc_env,
            bufsize=1,
        )
        st.session_state.pipeline_proc = proc

        stop_flag = {'stop': False}

        def reader_thread():
            try:
                for line in proc.stdout:
                    if stop_flag['stop']:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = _json.loads(line)
                    except _json.JSONDecodeError:
                        # Capture non-JSON output (traceback, etc.) for debugging
                        raw = st.session_state.pipeline_raw_output
                        raw.append(line)
                        if len(raw) > 20:
                            raw.pop(0)
                        continue
                    pct = ev.get('pct', 0)
                    msg = ev.get('msg', '')
                    if msg == '__DONE__':
                        st.session_state.pipeline_done_signal = True
                        break
                    if msg.startswith('__ERROR__:'):
                        st.session_state.pipeline_error = msg[len('__ERROR__:'):]
                        break
                    msgs = st.session_state.pipeline_messages
                    msgs.append({'pct': float(pct), 'msg': msg})
            except Exception as e:
                st.session_state.pipeline_error = f'reader thread error: {e}'

        t = _th.Thread(target=reader_thread, daemon=True)
        t.start()
        st.session_state.pipeline_thread = t
        st.rerun()

    # ================================================================
    #  RUNNING — poll subprocess and show progress
    # ================================================================
    if state == 'running':
        proc = st.session_state.get('pipeline_proc')
        messages = st.session_state.pipeline_messages
        cancel_requested = st.session_state.pipeline_cancel_requested
        error_msg = st.session_state.pipeline_error

        if proc and proc.poll() is None and not cancel_requested and not error_msg:
            # Still running — show progress
            progress_bar = st.progress(0.0, text='运行中...')
            log_box = st.empty()
            cancel_col = st.empty()

            if messages:
                last = messages[-1]
                pct = min(max(float(last.get('pct', 0)), 0.0), 1.0)
                progress_bar.progress(pct, text=last.get('msg', ''))
                log_box.markdown(
                    '\n'.join(f'· {m["msg"]}' for m in messages[-8:])
                )

            with cancel_col.container():
                if st.button('⏹ 取消生成', use_container_width=True, key='cancel_btn'):
                    st.session_state.pipeline_cancel_requested = True
                    try:
                        proc.terminate()
                        # Give the subprocess a brief grace period, then SIGKILL
                        # to avoid leaving zombie/handles around.
                        try:
                            proc.wait(timeout=5)
                        except Exception:
                            try:
                                proc.kill()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    st.rerun()

            _time.sleep(0.4)
            st.rerun()

        else:
            # Process has exited
            thread = st.session_state.get('pipeline_thread')
            if thread:
                thread.join(timeout=2)

            if hasattr(proc, 'returncode'):
                rc = proc.returncode
            else:
                rc = -1

            # Safety net: if the subprocess died without ever emitting
            # __ERROR__, surface the last raw stdout/stderr lines so the user
            # sees *something* instead of an opaque "退出码 1".
            if (
                not cancel_requested
                and not st.session_state.get('pipeline_error')
                and rc != 0
            ):
                raw_tail = list(st.session_state.get('pipeline_raw_output') or [])
                if raw_tail:
                    st.session_state.pipeline_error = (
                        f'子进程退出码 {rc} · 末尾输出:\n'
                        + '\n'.join(raw_tail[-6:])
                    )
                else:
                    st.session_state.pipeline_error = (
                        f'子进程退出码 {rc} · 未输出任何进度消息 '
                        '(常见原因：Windows 编码崩溃、模型不可用、网络中断)'
                    )

            if cancel_requested:
                # Reap any lingering child before declaring cancelled.
                try:
                    if rc == -1:
                        proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                st.session_state.pipeline_state = 'cancelled'
            elif error_msg:
                st.session_state.pipeline_state = 'error'
            elif rc == 0 or st.session_state.get('pipeline_done_signal'):
                # If the reader thread captured __DONE__, trust it even if
                # Windows process termination took a beat longer than
                # the exit code probe.
                st.session_state.pipeline_state = 'done'
            else:
                st.session_state.pipeline_error = f'进程退出码 {rc}'
                st.session_state.pipeline_state = 'error'

            st.session_state.pop('pipeline_proc', None)
            st.session_state.pop('pipeline_thread', None)
            st.rerun()

    # ================================================================
    #  DONE — show results with preview + download
    # ================================================================
    if state == 'done':
        st.success('✓ 生成完成！', icon='🎉')
        st.balloons()

        # Try to load summary JSON for preview
        summary_data = None
        for p in [output_dir / 'transcripts', Path(__file__).parent / 'transcripts']:
            cands = list(p.glob('*_summary.json'))
            if cands:
                summary_json_path = max(cands, key=lambda x: x.stat().st_mtime)
                try:
                    summary_data = _json.loads(summary_json_path.read_text(encoding='utf-8'))
                except Exception:
                    pass
                break

        # ---- Preview: stat cards ----
        if summary_data:
            meta = summary_data.get('meta') or {}
            sections = summary_data.get('sections') or []
            quotes = summary_data.get('quotes') or []
            infographic = summary_data.get('infographic') or {}
            cards = infographic.get('cards') or []

            stat_cols = st.columns(4)
            stat_items = [
                ('📖', f'{len(sections)}', '章节'),
                ('💬', f'{len(quotes)}', '金句'),
                ('🃏', f'{len(cards)}', '信息卡'),
                ('⏱', meta.get('duration_label') or '—', '时长'),
            ]
            for col, (icon, num, label) in zip(stat_cols, stat_items):
                with col:
                    st.markdown(
                        f'<div style="background:white;border:1px solid #E8E2D5;'
                        f'border-radius:8px;padding:0.8rem;text-align:center;">'
                        f'<div style="font-size:1.8rem;font-weight:900;color:#0F172A;">{icon} {num}</div>'
                        f'<div style="font-size:0.8rem;color:#64748B;">{label}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # ---- Expandable chapter preview ----
            with st.expander('📑 查看章节内容预览', expanded=False):
                for i, sec in enumerate(sections):
                    sec_title = sec.get('title') or f'章节 {i+1}'
                    sec_body = sec.get('body') or ''
                    sec_bullets = sec.get('bullets') or []
                    st.markdown(
                        f'<div style="font-family:Noto Serif SC,serif;font-size:1.1rem;'
                        f'font-weight:700;color:#0F172A;margin-top:0.8rem;">'
                        f'<span style="color:#B8860B;">{i+2:02d}</span>  {sec_title}</div>',
                        unsafe_allow_html=True,
                    )
                    if sec_body:
                        st.markdown(
                            f'<div style="font-size:0.9rem;color:#64748B;margin-left:1.2rem;">'
                            f'{sec_body[:150]}{"…" if len(sec_body) > 150 else ""}</div>',
                            unsafe_allow_html=True,
                        )
                    if sec_bullets:
                        for b in sec_bullets[:4]:
                            st.markdown(
                                f'<div style="font-size:0.85rem;color:#0F172A;'
                                f'margin-left:1.2rem;">· {str(b)[:60]}</div>',
                                unsafe_allow_html=True,
                            )
                    if sec.get('pull_quote'):
                        st.markdown(
                            f'<div style="font-size:0.85rem;color:#B8860B;font-style:italic;'
                            f'margin-left:1.2rem;border-left:2px solid #B8860B;padding-left:0.5rem;">'
                            f'❝ {sec["pull_quote"][:100]}❞</div>',
                            unsafe_allow_html=True,
                        )

            # ---- Key quotes preview ----
            if quotes:
                with st.expander('💬 关键金句预览', expanded=False):
                    for q in quotes[:6]:
                        st.markdown(
                            f'<div style="font-size:0.85rem;color:#64748B;font-style:italic;'
                            f'border-left:2px solid #B8860B;padding-left:0.6rem;margin:0.3rem 0;">'
                            f'❝ {str(q)[:120]}❞</div>',
                            unsafe_allow_html=True,
                        )

        # ---- Visual assets ----
        if cover_path.exists():
            st.markdown("##### 🎨 封面")
            st.image(str(cover_path), use_container_width=True)

        if info_path.exists():
            st.markdown("##### 📊 核心结论")
            st.image(str(info_path), use_container_width=True)

        # ---- Download cards ----
        st.markdown("##### ⬇️ 下载文件")
        dl_cols = st.columns(2)

        def _file_size(p):
            if not p.exists():
                return ''
            size = p.stat().st_size
            if size < 1024:
                return f'{size} B'
            elif size < 1024 * 1024:
                return f'{size / 1024:.0f} KB'
            else:
                return f'{size / 1024 / 1024:.1f} MB'

        with dl_cols[0]:
            if pdf_path.exists():
                size_str = _file_size(pdf_path)
                st.markdown(
                    f'<div style="background:white;border:1px solid #E8E2D5;'
                    f'border-radius:8px;padding:1rem;margin-bottom:0.5rem;">'
                    f'<div style="font-size:1.2rem;font-weight:700;color:#0F172A;">📄 PDF</div>'
                    f'<div style="font-size:0.8rem;color:#64748B;">{size_str} · 适合打印/分享</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                with open(pdf_path, 'rb') as f:
                    st.download_button(
                        label='📄 下载 PDF',
                        data=f.read(),
                        file_name='summary.pdf',
                        mime='application/pdf',
                        use_container_width=True,
                        type='primary',
                    )
        with dl_cols[1]:
            if docx_path.exists():
                size_str = _file_size(docx_path)
                st.markdown(
                    f'<div style="background:white;border:1px solid #E8E2D5;'
                    f'border-radius:8px;padding:1rem;margin-bottom:0.5rem;">'
                    f'<div style="font-size:1.2rem;font-weight:700;color:#0F172A;">📝 DOCX</div>'
                    f'<div style="font-size:0.8rem;color:#64748B;">{size_str} · 适合编辑/修改</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                with open(docx_path, 'rb') as f:
                    st.download_button(
                        label='📝 下载 DOCX',
                        data=f.read(),
                        file_name='summary.docx',
                        mime=(
                            'application/vnd.openxmlformats-'
                            'officedocument.wordprocessingml.document'
                        ),
                        use_container_width=True,
                    )

        # Re-run button
        if st.button('🔄 重新生成', use_container_width=True):
            st.session_state.pipeline_state = None
            st.rerun()

    # ================================================================
    #  ERROR
    # ================================================================
    if state == 'error':
        err = st.session_state.get('pipeline_error') or '未知错误'
        st.error(f'❌ {err}')
        # Show raw non-JSON output (traceback etc.) if available
        raw = st.session_state.get('pipeline_raw_output') or []
        if raw:
            with st.expander('🔍 查看详细错误输出', expanded=True):
                st.code('\n'.join(raw), language='text')
        if st.button('🔄 重新运行', use_container_width=True):
            st.session_state.pipeline_state = None
            st.rerun()

    # ================================================================
    #  CANCELLED
    # ================================================================
    if state == 'cancelled':
        st.warning('⏹ 已取消。当前步骤已中断，已生成的部分文件保留在 output/')
        if st.button('🔄 重新运行', use_container_width=True):
            st.session_state.pipeline_state = None
            st.rerun()

    # ================================================================
    #  EMPTY (no run yet this session)
    # ================================================================
    if state is None:
        has_prev = pdf_path.exists() or docx_path.exists()
        if has_prev:
            st.info('👈 在左侧输入新的视频 URL 或点击「🚀 开始生成」重新运行')
            if cover_path.exists():
                st.markdown("##### 🎨 封面 (上次生成)")
                st.image(str(cover_path), use_container_width=True)
            if info_path.exists():
                st.markdown("##### 📊 核心结论 (上次生成)")
                st.image(str(info_path), use_container_width=True)
            dl_cols = st.columns(2)
            with dl_cols[0]:
                if pdf_path.exists():
                    with open(pdf_path, 'rb') as f:
                        st.download_button('📄 下载 PDF', f.read(), 'summary.pdf',
                                           'application/pdf', use_container_width=True)
            with dl_cols[1]:
                if docx_path.exists():
                    with open(docx_path, 'rb') as f:
                        st.download_button('📝 下载 DOCX', f.read(), 'summary.docx',
                                           use_container_width=True)
        else:
            st.info(
                '👈 在左侧输入 B 站视频 URL，点击「🚀 开始生成」'
                '\n\n'
                '完成后此处会显示：'
                '\n'
                '- 实时进度 + 取消按钮'
                '\n'
                '- 封面 / 信息图预览'
                '\n'
                '- 内容预览（章节 / 金句）'
                '\n'
                '- PDF / DOCX 下载'
            )

# ============ Sidebar ============
with st.sidebar:
    st.markdown("### 🛠 工具说明")
    st.markdown("""
**bili_summary** 把任意 B 站视频一键转成编辑级 PDF / Word 文档：

1. **抓取**：调用 B 站 API 下载元数据 + 音频
2. **转录**：Whisper GPU（首次下载模型 ~500MB）
3. **总结**：由 LLM 根据视频内容自适应决定章节结构与重点
4. **生成**：PIL 渲染编辑级 PNG（封面 / 信息图 / 表格）
5. **导出**：reportlab + python-docx 输出 PDF / DOCX

---

**支持的平台**

| 平台 | 状态 |
|------|------|
| B 站  | ✅ 已实现 |

---

**环境要求**

- Python ≥ 3.11
- CUDA GPU（推荐）· RTX 5060 Ti 实测 18× 实时
- ffmpeg（自动检测 imageio-ffmpeg）
- 系统字体：Noto Serif / Sans SC
- B 站 SESSDATA cookie（见 README）
""")

    st.divider()

    # ---- LLM settings expander ----
    with st.expander('🧠 LLM 设置', expanded=False):
        import os, json

        def _read_cfg(key):
            cf = Path(__file__).parent / 'llm_config.json'
            if cf.exists():
                try:
                    return json.loads(cf.read_text(encoding='utf-8')).get(key)
                except Exception:
                    pass
            return None

        base = (os.environ.get('OPENCODE_BASE_URL')
                or _read_cfg('base_url') or '（未设置）')
        key_val = (os.environ.get('OPENCODE_API_KEY')
                   or _read_cfg('api_key') or '')
        model = (os.environ.get('LLM_MODEL')
                 or _read_cfg('model') or 'gpt-4o-mini')
        source = '（环境变量）' if (
            os.environ.get('OPENCODE_BASE_URL') or os.environ.get('OPENCODE_API_KEY')
        ) else '（llm_config.json）' if (Path(__file__).parent / 'llm_config.json').exists() else '（未配置）'

        st.caption(f'来源: {source}')
        st.markdown(f'**Base URL:** `{base}`')
        if key_val:
            masked = key_val[:4] + '***' + key_val[-4:] if len(key_val) > 12 else '***'
            st.markdown(f'**API Key:** `{masked}`')
        else:
            st.markdown('**API Key:** （未设置）')
        st.markdown(f'**Model:** `{model}`')
        if base in ('（未设置）',) or not key_val:
            st.warning(
                '⚠ 请设置 `llm_config.json` 或环境变量 '
                '`OPENCODE_BASE_URL` + `OPENCODE_API_KEY`。'
            )
        st.caption('修改后需重启 Streamlit 进程才能生效。')

    st.divider()

    # ---- Sticky cleanup panel at the bottom of the sidebar ----
    # Use Streamlit's container as the wrapper. No custom CSS needed —
    # the cleanup panel sits naturally below other sidebar content.
    with st.container():
        st.markdown('### 🧹 清理中间产物')
        with st.expander('会清理什么？', expanded=False):
            st.markdown(
                """
将被永久删除：

- `output/transcripts/` 下所有文件
  - `*.mp3` — 下载的音频（最大头，通常 30+ MB / 分钟视频）
  - `*_transcript.json` — Whisper 原始转录（含时间戳）
  - `*_transcript.txt` — 转录纯文本
- 根目录 `transcripts/` 下本次运行新增的 `BV*.mp3` / `BV*_transcript.*`
  - （`bili_*` 示例文件保留，不删）

**保留**：

- `output/summary.pdf` — 最终 PDF
- `output/summary.docx` — 最终 DOCX
- `output/assets/*.png` — 封面 / 信息图 / 表格

如果想再次生成 PDF/DOCX，只需重新点击「🚀 开始生成」，会自动复用现有缓存。
"""
            )

        # Two-step confirm: first click flips a flag, second click inside
        # the same session actually runs the cleanup.
        if 'cleanup_armed' not in st.session_state:
            st.session_state['cleanup_armed'] = False

        if not st.session_state['cleanup_armed']:
            if st.button('🧹 清理中间产物', use_container_width=True, key='cleanup_arm'):
                st.session_state['cleanup_armed'] = True
                st.rerun()
        else:
            st.warning('⚠ 确认删除？此操作不可撤销。')
            c1, c2 = st.columns(2)
            with c1:
                if st.button('✓ 确认清理', use_container_width=True,
                             key='cleanup_confirm'):
                    import shutil
                    removed = []
                    out_tr = output_dir / 'transcripts'
                    if out_tr.exists():
                        shutil.rmtree(out_tr)
                        removed.append('output/transcripts/')
                    root_tr = Path(__file__).parent / 'transcripts'
                    if root_tr.exists():
                        for p in root_tr.iterdir():
                            if p.is_file() and not p.name.startswith('bili_'):
                                p.unlink()
                                removed.append(f'transcripts/{p.name}')
                    st.session_state['cleanup_armed'] = False
                    if removed:
                        st.success('✓ 已清理: ' + ', '.join(removed))
                    else:
                        st.info('无中间产物可清理')
                    # No rerun() needed: st.success / st.info show in this same render.
            with c2:
                if st.button('✗ 取消', use_container_width=True, key='cleanup_cancel'):
                    st.session_state['cleanup_armed'] = False
                    st.rerun()