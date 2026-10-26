import time

import numpy as np
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="파동 반사: 물리 시뮬레이터",
    page_icon="〰️",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
      div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 12px;
        padding: 12px 14px;
      }
      .small-note { font-size: .9rem; opacity: .78; line-height: 1.6; }
      .formula-card {
        padding: 14px 16px; border-radius: 12px;
        background: rgba(128,128,128,.09); line-height: 1.7;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Session state and callbacks
# -----------------------------
DEFAULTS = {
    "boundary": "고정단",
    "tension": 40,
    "mu_g_m": 25,
    "time_ms": 0.0,
    "time_slider": 0.0,
    "playing": False,
    "speed_factor": 1.0,
    "last_tick": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def start_playback():
    st.session_state.playing = True
    st.session_state.last_tick = time.monotonic()


def pause_playback():
    st.session_state.playing = False
    st.session_state.last_tick = None


def reset_playback():
    st.session_state.playing = False
    st.session_state.last_tick = None
    st.session_state.time_ms = 0.0
    st.session_state.time_slider = 0.0


def set_speed(value: float):
    st.session_state.speed_factor = value


def on_time_slider_change():
    st.session_state.time_ms = float(st.session_state.time_slider)
    # Avoid a time jump after dragging the slider while playback is running.
    st.session_state.last_tick = time.monotonic() if st.session_state.playing else None


# -----------------------------
# Header and physics controls
# -----------------------------
st.title("〰️ 파동 반사: 물리 시뮬레이터")
st.write(
    "줄을 따라 이동하는 입사파와 끝점에서 반사된 파동을 계산해 "
    "두 파동이 중첩된 실제 줄의 변위를 관찰합니다."
)

st.subheader("① 줄의 끝 조건")
st.radio(
    "반사되는 줄의 끝을 선택하세요.",
    options=["고정단", "자유단"],
    horizontal=True,
    key="boundary",
    help="고정단은 끝점 변위가 0이고, 이상적인 자유단은 끝점 기울기가 0입니다.",
)

control1, control2 = st.columns(2)
with control1:
    st.slider("② 줄의 장력 (N)", min_value=10, max_value=80, step=1, key="tension")
with control2:
    st.slider("③ 줄의 선밀도 (g/m)", min_value=10, max_value=80, step=1, key="mu_g_m")

T = float(st.session_state.tension)
mu = float(st.session_state.mu_g_m) / 1000.0  # kg/m
wave_speed = float(np.sqrt(T / mu))

vcol, fcol = st.columns([1, 1.5])
with vcol:
    st.metric("이상적인 줄의 파동 속력", f"{wave_speed:.2f} m/s")
with fcol:
    st.markdown('<div class="formula-card">', unsafe_allow_html=True)
    st.latex(r"v=\sqrt{\frac{T}{\mu}}")
    st.caption("장력 T가 커지면 빨라지고, 선밀도 μ가 커지면 느려집니다.")
    st.markdown("</div>", unsafe_allow_html=True)

st.subheader("재생 속도")
st.caption("버튼을 눌러 애니메이션 속도를 바꾸세요. 0.25×가 가장 느립니다.")
speed_options = [
    (0.25, "🐢 0.25× 아주 느리게"),
    (0.5, "🐢 0.5× 느리게"),
    (1.0, "▶ 1× 보통"),
    (2.0, "⏩ 2× 빠르게"),
]
speed_cols = st.columns(4)
for col, (factor, label) in zip(speed_cols, speed_options):
    with col:
        st.button(
            label,
            key=f"speed_{factor}",
            type="primary" if st.session_state.speed_factor == factor else "secondary",
            use_container_width=True,
            on_click=set_speed,
            args=(factor,),
        )

play_cols = st.columns(3)
with play_cols[0]:
    st.button(
        "▶ 재생",
        key="play_button",
        disabled=st.session_state.playing,
        use_container_width=True,
        on_click=start_playback,
    )
with play_cols[1]:
    st.button(
        "Ⅱ 일시 정지",
        key="pause_button",
        disabled=not st.session_state.playing,
        use_container_width=True,
        on_click=pause_playback,
    )
with play_cols[2]:
    st.button(
        "↺ 초기화",
        key="reset_button",
        use_container_width=True,
        on_click=reset_playback,
    )

st.divider()

# The time window is long enough for the pulse to reach the right end, reflect,
# and travel out through the left end. It adapts to the wave speed.
L = 2.0
x0 = 0.5
A = 0.03  # 3 cm amplitude
sigma = 0.13
travel_across_and_back_ms = ((2.0 * L - x0) / wave_speed) * 1000.0
max_time_ms = max(20.0, min(350.0, travel_across_and_back_ms + 10.0))

# Clamp a stored time if changing tension/linear density shortens the timeline.
st.session_state.time_ms = min(float(st.session_state.time_ms), max_time_ms)

# Setting run_every dynamically starts/stops the live fragment. This means the
# page controls remain responsive while only the chart and readings refresh.
run_every = 0.1 if st.session_state.playing else None


@st.fragment(run_every=run_every)
def render_simulation():
    now = time.monotonic()
    if st.session_state.playing:
        previous = st.session_state.last_tick
        if previous is not None:
            elapsed = max(0.0, min(now - previous, 0.35))
            st.session_state.time_ms += elapsed * 1000.0 * float(st.session_state.speed_factor)
            if st.session_state.time_ms >= max_time_ms:
                st.session_state.time_ms = 0.0
        st.session_state.last_tick = now

    current_ms = max(0.0, min(float(st.session_state.time_ms), max_time_ms))
    # Sync the slider before it is created on each fragment refresh.
    st.session_state.time_slider = current_ms

    st.subheader("④ 시간에 따른 줄의 모양")
    st.slider(
        "시간 (ms)",
        min_value=0.0,
        max_value=float(max_time_ms),
        step=0.5,
        key="time_slider",
        on_change=on_time_slider_change,
        help="직접 끌어서 특정 순간의 파동 모양을 확인할 수도 있습니다.",
    )
    current_ms = float(st.session_state.time_ms)
    current_t = current_ms / 1000.0
    r = -1.0 if st.session_state.boundary == "고정단" else 1.0

    x = np.linspace(0.0, L, 600)
    incident = A * np.exp(-((x - x0 - wave_speed * current_t) ** 2) / (2.0 * sigma**2))
    reflected = r * A * np.exp(-((2.0 * L - x - x0 - wave_speed * current_t) ** 2) / (2.0 * sigma**2))
    total = incident + reflected

    fig = go.Figure()
    # Draw equilibrium and endpoint first so the wave remains visible on top.
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="gray")
    if st.session_state.boundary == "고정단":
        fig.add_vline(x=L, line_width=4, line_color="#d98225")
    else:
        fig.add_vline(x=L, line_width=2, line_dash="dash", line_color="#d98225")

    fig.add_trace(
        go.Scatter(
            x=x, y=total * 100, mode="lines", name="합성파",
            line=dict(color="#2587cc", width=3),
            hovertemplate="위치: %{x:.2f} m<br>변위: %{y:.2f} cm<extra>합성파</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=incident * 100, mode="lines", name="입사파",
            line=dict(color="#149688", width=2),
            hovertemplate="위치: %{x:.2f} m<br>변위: %{y:.2f} cm<extra>입사파</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=reflected * 100, mode="lines", name="반사파",
            line=dict(color="#d98225", width=2, dash="dash"),
            hovertemplate="위치: %{x:.2f} m<br>변위: %{y:.2f} cm<extra>반사파</extra>",
        )
    )
    fig.update_layout(
        height=390,
        margin=dict(l=12, r=12, t=18, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(title="줄의 위치 (m)", range=[0, L], dtick=0.5, showgrid=True, zeroline=False),
        yaxis=dict(title="변위 (cm)", range=[-6.5, 6.5], dtick=3, showgrid=True, zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    incident_center = x0 + wave_speed * current_t
    reflected_center = 2.0 * L - x0 - wave_speed * current_t
    end_value = (1.0 + r) * A * np.exp(-((L - x0 - wave_speed * current_t) ** 2) / (2.0 * sigma**2))

    st.markdown(f"**현재 시간:** {current_ms:.1f} ms　 ·　 **재생 속도:** {st.session_state.speed_factor:g}×")
    m1, m2 = st.columns(2)
    with m1:
        st.metric("입사파 중심 위치", f"{incident_center:.2f} m")
        st.metric("끝점 변위", f"{end_value * 100:.3f} cm")
    with m2:
        st.metric("반사파 중심 위치*", f"{reflected_center:.2f} m")
        st.metric("이상적 반사 계수", "+1" if r > 0 else "−1")

    if st.session_state.boundary == "고정단":
        st.info("고정단: 끝점의 변위가 항상 0이 되도록 반사파의 부호가 바뀝니다. (반사 계수 r = −1)")
    else:
        st.info("자유단: 끝점의 기울기가 0이 되도록 반사파가 같은 부호로 진행합니다. (반사 계수 r = +1)")
    st.caption("* 반사파 중심은 수학적으로 연장한 위치입니다. 줄의 실제 범위 밖으로 나올 수도 있습니다.")


render_simulation()

with st.expander("사용한 물리 모델과 가정"):
    st.latex(
        r"y(x,t)=A e^{-\frac{(x-x_0-vt)^2}{2\sigma^2}}"
        r"+rA e^{-\frac{(2L-x-x_0-vt)^2}{2\sigma^2}}"
    )
    st.markdown(
        "- 줄의 길이: **L = 2 m**\n"
        "- 초기 입사 펄스 중심: **x₀ = 0.5 m**\n"
        "- 진폭: **A = 0.03 m (3 cm)**\n"
        "- 펄스 폭 매개변수: **σ = 0.13 m**\n"
        "- 파동 속력: **v = √(T/μ)**, 여기서 μ는 kg/m 단위로 환산합니다.\n"
        "- 고정단은 **r = −1**, 이상적인 자유단은 **r = +1**로 계산합니다."
    )
    st.caption(
        "이 앱은 이상적인 줄에서 오른쪽 끝의 반사와 입사파·반사파의 중첩을 보여 주는 수학적 모델입니다. "
        "감쇠, 비선형 효과, 왼쪽 끝에서의 추가 반사는 반영하지 않습니다."
    )
