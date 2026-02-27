"""
Minecraft Education 리소스 대시보드
Streamlit 기반 시각화 대시보드
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import MinecraftEducationDB
import json
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="Minecraft Education 대시보드",
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


def main():
    # 헤더
    st.markdown('<div class="main-header">🎮 Minecraft Education 리소스 대시보드</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 데이터 로드
    with st.spinner("데이터를 불러오는 중..."):
        df = load_data()
        stats = get_statistics(df)

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
        st.plotly_chart(create_type_chart(stats), use_container_width=True)

    with col2:
        st.plotly_chart(create_subject_chart(stats), use_container_width=True)

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

    # 페이지네이션
    items_per_page = st.sidebar.slider("페이지당 항목 수", 5, 50, 10)
    total_pages = (len(filtered_df) - 1) // items_per_page + 1

    if total_pages > 0:
        page = st.sidebar.number_input(
            "페이지",
            min_value=1,
            max_value=total_pages,
            value=1
        )

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        # 리소스 표시
        for idx, resource in filtered_df.iloc[start_idx:end_idx].iterrows():
            display_resource_card(resource.to_dict())

        # 페이지 정보
        st.sidebar.info(f"📄 페이지 {page} / {total_pages}")
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
