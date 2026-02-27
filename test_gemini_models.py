"""
Gemini API 사용 가능한 모델 확인 스크립트
"""
import google.generativeai as genai
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# API 키 설정 (.streamlit/secrets.toml에서 읽기)
try:
    import tomllib
    with open('.streamlit/secrets.toml', 'rb') as f:
        secrets = tomllib.load(f)
        api_key = secrets['GEMINI_API_KEY']
except Exception as e:
    print(f"API 키를 읽을 수 없습니다: {e}")
    print("직접 API 키를 입력하세요:")
    api_key = input("GEMINI_API_KEY: ")

genai.configure(api_key=api_key)

print("=" * 60)
print("🔍 Gemini API 사용 가능한 모델 목록")
print("=" * 60)
print()

try:
    models = genai.list_models()

    generate_content_models = []

    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            generate_content_models.append(model)
            print(f"✅ {model.name}")
            print(f"   설명: {model.display_name}")
            print(f"   지원 메서드: {', '.join(model.supported_generation_methods)}")
            print()

    print("=" * 60)
    print(f"📊 총 {len(generate_content_models)}개의 generateContent 지원 모델")
    print("=" * 60)
    print()

    if generate_content_models:
        print("🎯 추천 모델:")
        for model in generate_content_models[:3]:
            print(f"   - {model.name}")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    print()
    print("해결 방법:")
    print("1. API 키가 올바른지 확인")
    print("2. google-generativeai 패키지 최신 버전 설치:")
    print("   pip install google-generativeai --upgrade")
