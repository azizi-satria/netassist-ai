import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

APP_NAME = "NetAssist AI"
APP_SUBTITLE = "Network Troubleshooting Assistant"
WELCOME_MESSAGE = (
    "Halo, saya NetAssist AI. Saya dapat membantu troubleshooting jaringan, "
    "Mikrotik, routing, VLAN, server, wireless, dan CCTV."
)
SYSTEM_PROMPT = (
    "Anda adalah Senior Network Engineer dengan pengalaman lebih dari 15 tahun. "
    "Berikan jawaban teknis yang akurat, langkah troubleshooting yang sistematis, "
    "dan contoh konfigurasi jika diperlukan."
)
ANALYSIS_PROMPT = """Analisis konfigurasi jaringan berikut dan berikan:

1. Ringkasan konfigurasi
2. Potensi masalah
3. Risiko keamanan
4. Rekomendasi perbaikan"""

UPLOAD_DIR = Path("uploads")
SUPPORTED_UPLOAD_TYPES = ("rsc", "txt")


def configure_page() -> None:
    """Configure Streamlit page metadata and base layout."""
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="🛜",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_custom_css() -> None:
    """Add custom CSS for a modern dashboard feel."""
    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --surface-soft: #f6f8fb;
            --line: #dbe2ea;
            --ink: #17202a;
            --muted: #657386;
            --accent: #0f766e;
            --accent-strong: #155e75;
            --ok: #16a34a;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 32rem),
                linear-gradient(180deg, #f8fbfd 0%, #eef3f7 100%);
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background: #0d1720;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] * {
            color: #eef6f8;
        }

        [data-testid="stSidebar"] .stButton button {
            width: 100%;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            background: #ef4444;
            color: #ffffff;
            font-weight: 700;
        }

        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }

        .app-title {
            font-size: 2.4rem;
            font-weight: 800;
            letter-spacing: 0;
            margin-bottom: 0.15rem;
            color: #10202d;
        }

        .app-subtitle {
            color: var(--muted);
            font-size: 1.05rem;
            margin-bottom: 1.25rem;
        }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin: 1.25rem 0 1.5rem;
        }

        .kpi-card {
            min-height: 112px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.86);
            padding: 1rem;
            box-shadow: 0 10px 25px rgba(30, 41, 59, 0.06);
        }

        .kpi-label {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .kpi-value {
            color: var(--ink);
            font-size: 1.05rem;
            font-weight: 750;
            line-height: 1.35;
        }

        .status-dot {
            display: inline-block;
            width: 0.7rem;
            height: 0.7rem;
            border-radius: 999px;
            background: var(--ok);
            box-shadow: 0 0 0 5px rgba(22, 163, 74, 0.12);
            margin-right: 0.5rem;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.35rem 0 1.15rem;
        }

        .brand-icon {
            display: grid;
            place-items: center;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 8px;
            background: linear-gradient(135deg, #14b8a6, #38bdf8);
            color: #03131a;
            font-size: 1.35rem;
            font-weight: 900;
        }

        .brand-text {
            font-size: 1.08rem;
            font-weight: 800;
            line-height: 1.1;
        }

        .brand-subtext {
            color: #a8bbc9;
            font-size: 0.78rem;
            margin-top: 0.15rem;
        }

        .analysis-box {
            border: 1px solid var(--line);
            border-left: 4px solid var(--accent);
            border-radius: 8px;
            background: #ffffff;
            padding: 1rem 1.15rem;
            margin-bottom: 1rem;
        }

        @media (max-width: 780px) {
            .kpi-grid {
                grid-template-columns: 1fr;
            }

            .app-title {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_api_key() -> str | None:
    """Return Gemini API key from environment variables."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


@st.cache_resource(show_spinner=False)
def get_client(api_key: str):
    """Create a cached Gemini client."""
    return genai.Client(api_key=api_key)


def initialize_session_state() -> None:
    """Initialize chat history with welcome message."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]
    if "config_analysis" not in st.session_state:
        st.session_state.config_analysis = None
    if "last_upload_signature" not in st.session_state:
        st.session_state.last_upload_signature = None


def level_instruction(user_level: str) -> str:
    """Return response style instruction based on selected user level."""
    instructions = {
        "Beginner": "Jelaskan dengan bahasa sederhana.",
        "Intermediate": "Jelaskan teknis secukupnya.",
        "Expert": "Berikan analisis teknis mendalam.",
    }
    return instructions.get(user_level, instructions["Intermediate"])


def build_chat_prompt(user_message: str, user_level: str) -> str:
    """Build full prompt for the Gemini chat request."""
    history = "\n".join(
        f"{message['role'].capitalize()}: {message['content']}"
        for message in st.session_state.messages[-8:]
    )
    return f"""
{SYSTEM_PROMPT}

Level pengguna: {user_level}
Instruksi gaya jawaban: {level_instruction(user_level)}

Riwayat percakapan terbaru:
{history}

Pertanyaan pengguna:
{user_message}
"""


def generate_response(client, prompt: str, temperature: float) -> str:
    """Generate a Gemini response with configurable temperature."""
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return response.text if response and response.text else "Maaf, Gemini tidak mengembalikan jawaban."


def render_sidebar() -> tuple[str, float, object]:
    """Render sidebar controls and return selected settings."""
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="brand-icon">N</div>
                <div>
                    <div class="brand-text">NetAssist AI</div>
                    <div class="brand-subtext">Network Consultant</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        user_level = st.selectbox(
            "User Level",
            ["Beginner", "Intermediate", "Expert"],
            index=1,
        )
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.4,
            step=0.1,
        )
        uploaded_file = st.file_uploader(
            "Upload Config",
            type=SUPPORTED_UPLOAD_TYPES,
            help="Upload file konfigurasi Mikrotik .rsc atau .txt",
        )

        st.divider()
        if st.button("Clear Chat", type="primary"):
            st.session_state.messages = [
                {"role": "assistant", "content": WELCOME_MESSAGE}
            ]
            st.session_state.config_analysis = None
            st.rerun()

    return user_level, temperature, uploaded_file


def render_header() -> None:
    """Render main dashboard header and KPI cards."""
    st.markdown(f'<div class="app-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitle">{APP_SUBTITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Supported Topics</div>
                <div class="kpi-value">Mikrotik, Routing, VLAN, Server</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">AI Model</div>
                <div class="kpi-value">Gemini</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Status</div>
                <div class="kpi-value"><span class="status-dot"></span>Online</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_history() -> None:
    """Render all messages stored in the current Streamlit session."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def save_uploaded_file(uploaded_file) -> Path:
    """Persist uploaded config file to uploads directory."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    destination = UPLOAD_DIR / safe_name
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


def read_uploaded_config(uploaded_file) -> str:
    """Read uploaded text configuration with UTF-8 fallback."""
    raw_content = uploaded_file.getvalue()
    try:
        return raw_content.decode("utf-8")
    except UnicodeDecodeError:
        return raw_content.decode("latin-1")


def analyze_uploaded_config(client, uploaded_file, temperature: float) -> None:
    """Analyze uploaded Mikrotik configuration with Gemini."""
    if uploaded_file is None:
        return

    upload_signature = (uploaded_file.name, uploaded_file.size)
    if st.session_state.last_upload_signature == upload_signature:
        return

    try:
        config_text = read_uploaded_config(uploaded_file)
        if not config_text.strip():
            st.warning("File konfigurasi kosong. Upload file .rsc atau .txt yang berisi konfigurasi.")
            return

        saved_path = save_uploaded_file(uploaded_file)
        prompt = f"""{SYSTEM_PROMPT}

{ANALYSIS_PROMPT}

Konfigurasi:
```text
{config_text}
```
        """
        with st.spinner("Menganalisis konfigurasi jaringan..."):
            analysis = generate_response(client, prompt, temperature)

        st.session_state.config_analysis = {
            "filename": uploaded_file.name,
            "saved_path": str(saved_path),
            "analysis": analysis,
        }
        st.session_state.last_upload_signature = upload_signature
    except Exception as exc:
        st.error(f"Gagal memproses file konfigurasi: {exc}")


def render_config_analysis() -> None:
    """Render latest configuration analysis result."""
    result = st.session_state.get("config_analysis")
    if not result:
        return

    st.markdown('<div class="analysis-box">', unsafe_allow_html=True)
    st.subheader(f"Analisis Konfigurasi: {result['filename']}")
    st.caption(f"Disimpan di: {result['saved_path']}")
    st.markdown(result["analysis"])
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    configure_page()
    inject_custom_css()
    initialize_session_state()

    api_key = get_api_key()
    user_level, temperature, uploaded_file = render_sidebar()

    render_header()

    if not api_key:
        st.error(
            "Gemini API Key belum ditemukan. Buat file .env dari .env.example, "
            "lalu isi GEMINI_API_KEY."
        )
        render_chat_history()
        return

    try:
        client = get_client(api_key)
    except Exception as exc:
        st.error(f"Gagal menginisialisasi Gemini API: {exc}")
        render_chat_history()
        return

    analyze_uploaded_config(client, uploaded_file, temperature)
    render_config_analysis()

    render_chat_history()

    if user_message := st.chat_input("Tulis pertanyaan troubleshooting jaringan..."):
        st.session_state.messages.append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        prompt = build_chat_prompt(user_message, user_level)
        with st.chat_message("assistant"):
            with st.spinner("NetAssist AI sedang menganalisis..."):
                try:
                    answer = generate_response(client, prompt, temperature)
                    st.markdown(answer)
                except Exception as exc:
                    answer = f"Terjadi error saat menghubungi Gemini API: {exc}"
                    st.error(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
