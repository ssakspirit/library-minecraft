"""
Minecraft Education 리소스 대시보드
Streamlit 기반 시각화 대시보드 + AI 챗봇
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import MinecraftEducationDB
import json
from pathlib import Path
import google.generativeai as genai

# 페이지 설정
st.set_page_config(
    page_title="minecraft library",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E7D32;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .resource-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
    .resource-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1976D2;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        margin: 0.25rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .badge-world { background: #E3F2FD; color: #1976D2; }
    .badge-lesson { background: #F3E5F5; color: #7B1FA2; }
    .badge-challenge { background: #FFF3E0; color: #E65100; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """데이터 로드 (캐시됨)"""
    json_path = Path('data/resources.json')

    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)

    # DB에서 로드
    with MinecraftEducationDB() as db:
        resources = db.get_all_resources()
        return pd.DataFrame(resources)


@st.cache_data
def get_statistics(df):
    """통계 계산"""
    stats = {
        'total': len(df),
        'by_type': df['type'].value_counts().to_dict(),
        'by_subject': {}
    }

    # 과목별 통계 (subjects는 쉼표로 구분된 문자열)
    all_subjects = []
    for subjects_str in df['subjects'].dropna():
        if subjects_str:
            all_subjects.extend(subjects_str.split(','))

    subject_counts = pd.Series(all_subjects).value_counts()
    stats['by_subject'] = subject_counts.to_dict()

    return stats


def create_type_chart(stats):
    """타입별 차트 생성"""
    fig = go.Figure(data=[go.Pie(
        labels=list(stats['by_type'].keys()),
        values=list(stats['by_type'].values()),
        hole=0.4,
        marker=dict(colors=['#1976D2', '#7B1FA2', '#E65100']),
        textinfo='label+percent',
        textfont=dict(size=14)
    )])

    fig.update_layout(
        title="리소스 타입 분포",
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )

    return fig


def create_subject_chart(stats, top_n=10):
    """과목별 차트 생성"""
    subjects = list(stats['by_subject'].items())
    subjects.sort(key=lambda x: x[1], reverse=True)
    subjects = subjects[:top_n]

    fig = go.Figure(data=[go.Bar(
        x=[s[1] for s in subjects],
        y=[s[0] for s in subjects],
        orientation='h',
        marker=dict(
            color=[s[1] for s in subjects],
            colorscale='Viridis'
        ),
        text=[s[1] for s in subjects],
        textposition='outside'
    )])

    fig.update_layout(
        title=f"과목별 리소스 (상위 {top_n}개)",
        xaxis_title="리소스 수",
        yaxis_title="과목",
        height=500,
        yaxis={'categoryorder': 'total ascending'}
    )

    return fig


def display_resource_card(resource):
    """리소스 카드 표시"""
    type_badge_class = f"badge badge-{resource['type'].lower()}"

    subjects = resource.get('subjects', '')
    subject_badges = ""
    if subjects:
        for subject in subjects.split(',')[:3]:  # 최대 3개만 표시
            subject_badges += f'<span class="badge" style="background: #E8F5E9; color: #2E7D32;">{subject.strip()}</span>'

    card_html = f"""
    <div class="resource-card">
        <div class="resource-title">
            <span class="{type_badge_class}">{resource['type']}</span>
            {resource['title']}
        </div>
        <p style="color: #666; margin: 0.5rem 0;">{resource.get('description', '')[:200]}...</p>
        <div style="margin-top: 0.5rem;">
            {subject_badges}
        </div>
        <a href="{resource['url']}" target="_blank" style="color: #1976D2; text-decoration: none;">
            🔗 View Resource
        </a>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


def init_gemini():
    """Gemini API 초기화"""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", None)
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        st.error(f"Gemini API 초기화 실패: {e}")
        return None


def create_prompt(user_query, resources_df):
    """리소스 데이터를 포함한 프롬프트 생성"""
    # 리소스 샘플 (최대 50개)
    sample_resources = resources_df.head(50).to_dict('records')

    resources_text = ""
    for idx, res in enumerate(sample_resources[:20], 1):
        subjects = res.get('subjects', 'N/A')
        resources_text += f"{idx}. [{res['type']}] {res['title']}\n   과목: {subjects}\n   설명: {res.get('description', 'N/A')[:100]}\n   링크: {res['url']}\n\n"

    prompt = f"""당신은 Minecraft Education 리소스 추천 전문가입니다.
사용자의 질문을 바탕으로 가장 적합한 리소스를 추천해주세요.

현재 데이터베이스에는 {len(resources_df)}개의 리소스가 있습니다:
- World: {len(resources_df[resources_df['type'] == 'World'])}개
- Lesson: {len(resources_df[resources_df['type'] == 'Lesson'])}개
- Challenge: {len(resources_df[resources_df['type'] == 'Challenge'])}개

주요 과목: Computer Science, Math, Science, Arts, Language Arts, Social Studies 등

리소스 샘플 (상위 20개):
{resources_text}

사용자 질문: {user_query}

답변 형식:
1. 질문 이해 및 요약
2. 추천 리소스 (3-5개, 제목, 타입, 과목, 링크 포함)
3. 추천 이유
4. 추가 조언

답변은 한국어로 작성하고, 친절하고 상세하게 설명해주세요."""

    return prompt


def chatbot_tab(df):
    """AI 챗봇 탭"""
    st.header("🤖 AI 리소스 추천 챗봇")

    st.markdown("""
    무엇을 찾고 계신가요? 자연어로 질문하시면 AI가 최적의 리소스를 추천해드립니다!

    **예시 질문:**
    - "초등학생용 코딩 수업 자료 추천해줘"
    - "수학과 과학을 융합한 Challenge 찾아줘"
    - "아트와 역사를 배울 수 있는 World 추천"
    """)

    # Gemini 모델 초기화
    model = init_gemini()

    if model is None:
        st.warning("⚠️ Gemini API 키가 설정되지 않았습니다.")
        st.info("""
        **API 키 설정 방법:**

        1. Google AI Studio에서 API 키 발급: https://makersuite.google.com/app/apikey
        2. Streamlit Cloud Secrets에 추가:
           - 대시보드 설정 → Secrets
           - `GEMINI_API_KEY = "your-api-key"` 추가

        로컬 테스트 시: `.streamlit/secrets.toml` 파일에 추가
        """)
        return

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 채팅 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                try:
                    full_prompt = create_prompt(prompt, df)
                    response = model.generate_content(full_prompt)
                    ai_response = response.text
                    st.markdown(ai_response)

                    # 응답 저장
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

                except Exception as e:
                    error_msg = f"❌ 오류가 발생했습니다: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # 대화 초기화 버튼
    if st.session_state.messages:
        if st.button("🔄 대화 초기화"):
            st.session_state.messages = []
            st.rerun()


def main():
    # 세션 상태 초기화
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # 헤더
    st.markdown('<div class="main-header">🎮 Minecraft Education 리소스 대시보드</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 데이터 로드
    with st.spinner("데이터를 불러오는 중..."):
        df = load_data()
        stats = get_statistics(df)

    # 탭 생성
    tab1, tab2 = st.tabs(["📚 리소스 탐색", "🤖 AI 추천"])

    with tab2:
        # AI 챗봇 탭
        chatbot_tab(df)

    with tab1:
        # 기존 대시보드 코드 (리소스 탐색 탭)

        # KPI 메트릭
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="📚 총 리소스",
                value=f"{stats['total']:,}",
                delta="1,123개"
            )

        with col2:
            st.metric(
                label="🌍 Worlds",
                value=stats['by_type'].get('World', 0),
                delta=f"{stats['by_type'].get('World', 0)/stats['total']*100:.1f}%"
            )

        with col3:
            st.metric(
                label="📖 Lessons",
                value=stats['by_type'].get('Lesson', 0),
                delta=f"{stats['by_type'].get('Lesson', 0)/stats['total']*100:.1f}%"
            )

        with col4:
            st.metric(
                label="🏆 Challenges",
                value=stats['by_type'].get('Challenge', 0),
                delta=f"{stats['by_type'].get('Challenge', 0)/stats['total']*100:.1f}%"
            )

        st.markdown("---")

        # 차트 섹션
        st.header("📊 통계 및 분석")

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(create_type_chart(stats), width='stretch')

        with col2:
            st.plotly_chart(create_subject_chart(stats), width='stretch')

        st.markdown("---")

        # 사이드바 - 필터
        st.sidebar.header("🔍 검색 및 필터")

        # 검색
        search_query = st.sidebar.text_input("키워드 검색", placeholder="예: coding, math, science...")

        # 타입 필터
        type_filter = st.sidebar.multiselect(
            "타입 선택",
            options=list(stats['by_type'].keys()),
            default=list(stats['by_type'].keys())
        )

        # 과목 필터
        all_subjects = sorted(list(stats['by_subject'].keys()))
        subject_filter = st.sidebar.multiselect(
            "과목 선택",
            options=all_subjects,
            default=[]
        )

        # 정렬
        sort_by = st.sidebar.selectbox(
            "정렬 기준",
            options=["최신순", "제목순", "타입순"]
        )

        # 데이터 필터링
        filtered_df = df.copy()

        # 타입 필터 적용
        if type_filter:
            filtered_df = filtered_df[filtered_df['type'].isin(type_filter)]

        # 과목 필터 적용
        if subject_filter:
            mask = filtered_df['subjects'].apply(
                lambda x: any(subj in str(x) for subj in subject_filter) if pd.notna(x) else False
            )
            filtered_df = filtered_df[mask]

        # 검색 필터 적용
        if search_query:
            search_lower = search_query.lower()
            mask = (
                filtered_df['title'].str.lower().str.contains(search_lower, na=False) |
                filtered_df['description'].str.lower().str.contains(search_lower, na=False) |
                filtered_df['subjects'].str.lower().str.contains(search_lower, na=False)
            )
            filtered_df = filtered_df[mask]

        # 정렬
        if sort_by == "제목순":
            filtered_df = filtered_df.sort_values('title')
        elif sort_by == "타입순":
            filtered_df = filtered_df.sort_values('type')
        else:  # 최신순
            filtered_df = filtered_df.sort_values('crawled_at', ascending=False)

        # 리소스 목록
        st.header(f"📚 리소스 목록 ({len(filtered_df)}개)")

        # 페이지네이션 설정
        items_per_page = st.sidebar.slider("페이지당 항목 수", 5, 50, 10)
        total_pages = max(1, (len(filtered_df) - 1) // items_per_page + 1) if len(filtered_df) > 0 else 1

        # 현재 페이지 범위 확인
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = 1

        if len(filtered_df) > 0:
            start_idx = (st.session_state.current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page

            # 리소스 표시
            for idx, resource in filtered_df.iloc[start_idx:end_idx].iterrows():
                display_resource_card(resource.to_dict())

            # 페이지네이션 UI (화면 하단)
            st.markdown("---")

            # 페이지네이션 컨테이너
            pagination_container = st.container()

            with pagination_container:
                # 페이지 정보 표시
                st.markdown(f"""
                    <div style="text-align: center; color: #666; margin-bottom: 1rem;">
                        페이지 {st.session_state.current_page} / {total_pages} (총 {len(filtered_df)}개 리소스)
                    </div>
                """, unsafe_allow_html=True)

                # 페이지 버튼들
                max_buttons = 10  # 최대 표시할 페이지 번호

                # 페이지 범위 계산
                if total_pages <= max_buttons:
                    start_page = 1
                    end_page = total_pages
                else:
                    # 현재 페이지를 중심으로
                    half = max_buttons // 2
                    start_page = max(1, st.session_state.current_page - half)
                    end_page = min(total_pages, start_page + max_buttons - 1)

                    # 끝에 도달하면 시작점 조정
                    if end_page - start_page < max_buttons - 1:
                        start_page = max(1, end_page - max_buttons + 1)

                # 버튼 레이아웃
                cols = st.columns([1, 1, 10, 1, 1])

                # 처음으로 버튼
                with cols[0]:
                    if st.button("⏮️ 처음", disabled=(st.session_state.current_page == 1), key="first"):
                        st.session_state.current_page = 1
                        st.rerun()

                # 이전 버튼
                with cols[1]:
                    if st.button("◀️ 이전", disabled=(st.session_state.current_page == 1), key="prev"):
                        st.session_state.current_page -= 1
                        st.rerun()

                # 페이지 번호 버튼들
                with cols[2]:
                    page_cols = st.columns(min(max_buttons, end_page - start_page + 1))

                    for i, page_num in enumerate(range(start_page, end_page + 1)):
                        with page_cols[i]:
                            button_type = "primary" if page_num == st.session_state.current_page else "secondary"
                            if st.button(
                                str(page_num),
                                key=f"page_{page_num}",
                                type=button_type,
                                use_container_width=True
                            ):
                                st.session_state.current_page = page_num
                                st.rerun()

                # 다음 버튼
                with cols[3]:
                    if st.button("다음 ▶️", disabled=(st.session_state.current_page == total_pages), key="next"):
                        st.session_state.current_page += 1
                        st.rerun()

                # 마지막으로 버튼
                with cols[4]:
                    if st.button("마지막 ⏭️", disabled=(st.session_state.current_page == total_pages), key="last"):
                        st.session_state.current_page = total_pages
                        st.rerun()
        else:
            st.info("검색 결과가 없습니다.")

        # 푸터
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; padding: 2rem;">
            Made with ❤️ for Minecraft Education Community<br>
            Data source: <a href="https://education.minecraft.net" target="_blank">education.minecraft.net</a>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
