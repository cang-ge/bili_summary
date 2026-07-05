"""
bili_summary · Streamlit UI

启动方式：
    streamlit run app.py

打开浏览器访问 http://localhost:8501

功能：
1. 输入 B 站 / YouTube / X 视频 URL
2. 一键运行完整流水线（带实时进度）
3. 在页面内预览封面 / 信息图 / 表格
4. 一键下载生成的 PDF / DOCX
"""
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

# ============ Styles ============
st.markdown("""
<style>
    .main-header {
        font-family: 'Georgia', serif;
        font-size: 3.5rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
        color: #0F172A;
    }
    .sub-header {
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #B8860B;
    }
    .stat-card {
        background: #FAF8F5;
        border-left: 4px solid #B8860B;
        padding: 1rem 1.2rem;
        border-radius: 4px;
        margin-bottom: 0.5rem;
    }
    .stat-num {
        font-family: 'Georgia', serif;
        font-size: 1.8rem;
        font-weight: 900;
        color: #0F172A;
    }
    .stat-label {
        color: #B8860B;
        font-size: 0.85rem;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# ============ Header ============
st.markdown('<div class="main-header">视频一键总结</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">B 站 · YouTube · X &nbsp;·&nbsp; '
    'Whisper 转录 + 编辑级排版 + PDF / DOCX 导出</div>',
    unsafe_allow_html=True,
)

# ============ Layout ============
col_left, col_right = st.columns([1, 1.6], gap='large')

# ---------- LEFT: Input panel ----------
with col_left:
    st.subheader('① 输入')

    url = st.text_input(
        '视频 URL',
        placeholder='https://www.bilibili.com/video/BV1cyDKBLEXY',
        help='粘贴 B 站 / YouTube / X 视频链接',
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
        disabled=not url or detect_url_platform(url) == 'unknown',
    )

    # ---------- Recent / preset ----------
    st.divider()
    st.subheader('② 试试这个示例')
    if st.button(
        '📺 Kasa_ZYY · 雅思自学流程介绍（66 分钟）',
        use_container_width=True,
    ):
        st.session_state['preset_url'] = 'https://www.bilibili.com/video/BV1cyDKBLEXY'
        st.rerun()

    if 'preset_url' in st.session_state:
        st.info(f"已填入：{st.session_state['preset_url']}")
        if st.button('使用此 URL', use_container_width=True):
            url = st.session_state['preset_url']
            st.rerun()

# ---------- RIGHT: Output panel ----------
with col_right:
    st.subheader('③ 结果')

    output_dir = Path(__file__).parent / 'output'
    assets_dir = output_dir / 'assets'

    # ===== Existing files preview (always show) =====
    pdf_path = output_dir / 'summary.pdf'
    docx_path = output_dir / 'summary.docx'
    cover_path = assets_dir / 'cover.png'
    info_path = assets_dir / 'infographic.png'
    sched_path = assets_dir / 'daily-schedule.png'
    listen_path = assets_dir / 'intensive-listening-flow.png'

    if run_btn:
        progress_bar = st.progress(0.0, text='准备中...')
        log_box = st.empty()
        messages = []

        def update_progress(msg, pct):
            messages.append(msg)
            progress_bar.progress(min(pct, 1.0), text=msg)
            # Show last 8 log lines
            log_box.markdown(
                '\n'.join(f'· {m}' for m in messages[-8:])
            )

        try:
            with st.spinner('正在处理...'):
                result = run_pipeline(
                    url=url,
                    out_dir=output_dir,
                    on_progress=update_progress,
                    skip_transcribe=skip_transcribe,
                    use_cache=use_cache,
                )
            st.success(f"✓ 完成！文件已写入 {output_dir}/")
            st.balloons()
        except Exception as e:
            st.error(f"❌ 错误：{e}")
            st.stop()

    # ===== Show all assets (after generation or cached) =====
    if cover_path.exists():
        st.markdown("##### 🎨 封面")
        st.image(str(cover_path), use_container_width=True)

    if info_path.exists():
        st.markdown("##### 📊 七条核心结论")
        st.image(str(info_path), use_container_width=True)

    if sched_path.exists():
        with st.expander("📅 每日作息", expanded=False):
            st.image(str(sched_path), use_container_width=True)

    if listen_path.exists():
        with st.expander("🎧 精听 5 步流程", expanded=False):
            st.image(str(listen_path), use_container_width=True)

    # ===== Downloads =====
    st.markdown("##### ⬇️ 下载")

    dl_cols = st.columns(2)
    with dl_cols[0]:
        if pdf_path.exists():
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

# ============ Sidebar ============
with st.sidebar:
    st.markdown("### 🛠 工具说明")
    st.markdown("""
**bili_summary** 把任意视频一键转成编辑级 PDF / Word 文档：

1. **抓取**：yt-dlp 下载元数据 + 音频
2. **转录**：Whisper GPU（首次下载模型 ~500MB）
3. **总结**：结构化 12 个章节 + 关键金句
4. **生成**：PIL 渲染编辑级 PNG（封面 / 信息图 / 表格）
5. **导出**：reportlab + python-docx 输出 PDF / DOCX

---
**支持的平台**

| 平台 | 状态 |
|------|------|
| B 站  | ✅ 已实现 |
| YouTube | 🟡 计划中 |
| X / Twitter | 🟡 计划中 |

详见 `docs/multi-platform.md`

---
**环境要求**

- Python ≥ 3.11
- CUDA GPU（推荐）· RTX 5060 Ti 实测 18× 实时
- ffmpeg（自动检测 imageio-ffmpeg）
- 系统字体：Noto Serif / Sans SC
""")

    st.divider()

    st.markdown("### 📂 当前输出")
    if output_dir.exists():
        for p in sorted(output_dir.glob('**/*')):
            if p.is_file():
                rel = p.relative_to(output_dir)
                size_kb = p.stat().st_size / 1024
                st.markdown(f"📄 `{rel}` · {size_kb:.0f} KB")
    else:
        st.info("output/ 目录尚未生成")

    st.divider()

    if st.button('🧹 清理缓存', use_container_width=True):
        import shutil
        cache = Path.home() / '.cache' / 'ielts-tool'
        if cache.exists():
            shutil.rmtree(cache)
            st.success("✓ 缓存已清理")
        else:
            st.info("无缓存可清理")