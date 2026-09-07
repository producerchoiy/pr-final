# 홍보 바다 — 업무 자동화 Streamlit

하나의 `task_id`를 중심으로 오늘 시간표, 전체 업무, 월간 콘텐츠 캘린더,
대기·회신, 순차 단계, 유튜브 실적, AI 대본, 자료실을 연결하는 홍보 업무 관리 앱입니다.

## 이번 버전의 핵심

- 접속 즉시 오늘 업무와 시간표가 보이는 실무형 첫 화면
- 클릭 가능한 `오늘 할 일 / 오늘 마감 / 대기·회신 / 이번 주 마감`
- `TASK-YYYYMMDD-001` 형식의 업무 ID와 모든 화면의 실시간 연동
- 마감일과 실행 예정일·시작시간·종료시간 분리
- 업무 수정·완료·삭제 및 긴급 업무 즉시 반영
- 프로젝트 → 업무 → 순차 단계 구조
- 행사 촬영·유튜브 인터뷰 업무 세트
- 월간 캘린더와 ⭐ 우선 표시
- 요청일·재확인일을 포함한 대기·회신 관리
- 평일·매일·1회 알람과 퇴근 전 점검 항목 관리
- 유튜브 업무 완료 후 실적 입력 팝업과 Excel 다운로드
- 저장된 병원 문서 양식 기반 AI 대본 작성
- Supabase DB·Storage 기반 자료실
- 업무 유형·프로젝트·알람·체크리스트·업무 세트·문서 양식 설정
- 사진 파일이 누락되어도 내장 축소 이미지로 실행되는 안전장치
- 서울남산체 계열의 단정한 한글 UI와 전문 홍보실 색상 체계
- PC·태블릿·모바일에서 읽기 편한 간격, 줄바꿈, 반응형 화면

## 서체와 화면 디자인

화면은 서울남산체의 단정한 인상과 가까운 한글 서체 체계로 구성했습니다.
사용 기기에 `SeoulNamsan`이 설치되어 있으면 먼저 사용하고, 그렇지 않으면 웹 폰트
`Pretendard`와 시스템 한글 글꼴 순서로 자동 적용됩니다. 네트워크에서 웹 폰트를
불러오지 못해도 시스템 글꼴로 안전하게 표시됩니다.

제공한 그림과 사진은 사이드바와 마무리 카드의 배경으로 사용하되, 업무 정보의
가독성을 해치지 않도록 어두운 오버레이와 낮은 대비를 적용했습니다.

## GitHub 저장소 구조

폴더 누락으로 인한 `ModuleNotFoundError`를 막기 위해 실행 파일을 모두 GitHub
저장소 최상단에 배치했습니다. 압축을 푼 **파일 전체**를 최상단에 업로드합니다.

```text
PR-Flow-Streamlit/
├── streamlit_app.py
├── app_data.py
├── app_styles.py
├── embedded_assets.py
├── database.py
├── repository.py
├── llm_service.py
├── date_utils.py
├── export_utils.py
├── schema.sql
├── requirements.txt
└── README.md
```

사진은 `embedded_assets.py`에도 내장되어 있으므로 별도의 `assets` 폴더가 없어도
디자인과 앱 실행에 문제가 없습니다.

## Streamlit Community Cloud 배포

1. GitHub 저장소에 위 파일을 전부 업로드하고 Commit합니다.
2. Streamlit Community Cloud에서 해당 저장소와 `main` 브랜치를 선택합니다.
3. Main file path는 `streamlit_app.py`로 지정합니다.
4. Deploy를 실행합니다.

GitHub `main` 브랜치에 새 Commit을 올리면 Streamlit 앱도 자동 재배포됩니다.

## Supabase 영구 저장 연결

Supabase 연결 전에는 **체험 모드**로 실행됩니다. 체험 모드의 입력은 현재 브라우저
세션에만 남고 GitHub 파일에는 기록되지 않습니다.

1. Supabase 프로젝트를 생성합니다.
2. Supabase SQL Editor에서 `schema.sql` 전체를 한 번 실행합니다.
3. Streamlit 앱의 Secrets에 아래 값을 등록합니다.

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SERVICE-ROLE-KEY"
```

`service_role` 키는 Streamlit 서버의 Secrets에만 저장하고 GitHub 코드·README·화면에
절대 입력하지 마세요. 연결되면 업무, 단계, 대기·회신, 알람, 체크리스트, 실적,
문서 양식은 PostgreSQL에 저장되고 첨부 파일은 비공개 Storage 버킷에 저장됩니다.

## AI 대본 작성 연결

선택 기능입니다. Streamlit Secrets에 아래 값을 추가하면 활성화됩니다.

```toml
OPENAI_API_KEY = "YOUR-OPENAI-API-KEY"
OPENAI_MODEL = "gpt-5-mini"
```

AI는 설정 페이지에 저장된 실제 문서 양식과 사용자가 입력한 참고자료를 함께 전달받습니다.
API 키가 없으면 AI 호출만 비활성화되고 나머지 업무 관리 기능은 정상 작동합니다.

## 데이터 저장 원칙

- GitHub: 프로그램 소스와 디자인 이미지
- Supabase PostgreSQL: 업무·단계·대기·회신·실적·체크리스트·문서 양식
- Supabase Storage: 사용자가 등록한 첨부 파일
- Streamlit Session: Supabase 미연결 상태의 임시 체험 데이터

앱에서 등록한 업무나 자료를 저장소 내부 JSON·CSV에 기록하지 않습니다.

## 사진 공개 범위 주의

제공한 가족사진과 그림은 `assets`와 `embedded_assets.py`에 포함되어 있습니다.
GitHub 저장소가 공개 상태라면 사진 원본과 내장 이미지도 공개될 수 있으므로,
외부 공개를 원하지 않으면 반드시 **비공개 저장소**를 사용하세요.

## 로컬 실행

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 자동 검사

GitHub Actions가 다음을 확인합니다.

- 8개 화면 전체 기동
- 업무 생성 → 캘린더 → 상세 수정 → 전체 업무 반영
- `assets` 폴더 누락 시 내장 이미지 대체 실행
