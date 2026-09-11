# 홍보 바다 — 업무 자동화 Streamlit

하나의 `task_id`를 중심으로 오늘 시간표, 전체 업무, 프로젝트, 콘텐츠 캘린더,
대기·회신, 유튜브 실적, AI 대본, 자료실을 연결하는 홍보 업무 관리 앱입니다.

## 이번 안정화 버전의 핵심

- 완료 직전 상태를 저장하고 언제든 `업무 다시 열기`로 복구
- 상태 변경 시각과 완료·재개 이력 기록
- 사이드바 메뉴 이동과 업무 상세 팝업 상태 분리
- 삭제 업무를 되살리지 않는 soft delete와 빈 초기 업무 저장소
- 일정별 시작·5분 전·10분 전·30분 전·1시간 전 알람
- 매일·평일·매주 특정 요일 반복과 날짜별 제외
- 자동 정렬과 드래그 가능한 `내 순서` 저장
- 프로젝트 등록·수정·삭제와 하위 업무 연결 관리
- 유튜브 실적 수정·삭제·관련 업무 열기·중복 등록 방지
- 업무 ID를 공유하는 시간표·긴급 업무·오늘 할 일·대기·회신·캘린더
- 저장된 병원 문서 양식 기반 AI 대본 작성과 Supabase 자료실
- 제공 사진을 활용한 서울남산체 계열의 반응형 홍보 전문가 UI
- 사진 파일이 없어도 내장 축소 이미지로 실행되는 안전장치

## GitHub 저장소 구조

폴더 누락으로 인한 `ModuleNotFoundError`를 막기 위해 실행 파일을 모두 저장소
최상단에 배치했습니다. ZIP을 압축 해제한 뒤 아래 12개 파일을 저장소 최상단에
그대로 업로드합니다.

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

별도의 `utils`, `services`, `assets` 폴더가 없어도 실행됩니다.

## 기존 Streamlit 연결을 유지한 업데이트 순서

저장소나 Streamlit 앱을 새로 만들 필요가 없습니다.

1. 이 ZIP의 12개 파일로 GitHub 저장소 최상단의 같은 이름 파일을 교체합니다.
2. GitHub에서 한 번에 Commit합니다.
3. Supabase SQL Editor에서 새 `schema.sql` 전체를 실행합니다. `IF NOT EXISTS`
   마이그레이션이므로 기존 업무는 유지됩니다.
4. Streamlit Community Cloud에서 **Manage app → Reboot app**을 한 번 누릅니다.

기존 GitHub 저장소, Streamlit 앱 URL, Main file path, Secrets 연결은 그대로 유지됩니다.

## Supabase 영구 저장 연결

Supabase 연결 전에는 체험 모드로 실행됩니다. 체험 모드의 입력은 현재 브라우저
세션에만 남으므로 실제 업무에는 Supabase 연결이 필요합니다.

1. Supabase 프로젝트를 준비합니다.
2. Supabase SQL Editor에서 `schema.sql` 전체를 실행합니다. 기존 설치도 최신 버전으로
   올릴 때 다시 실행합니다.
3. Streamlit 앱의 Secrets에 아래 값을 등록합니다.

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SERVICE-ROLE-KEY"
```

`service_role` 키는 Streamlit Secrets에만 보관하고 GitHub에는 올리지 마세요.
연결되면 업무, 단계, 상태 이력, 반복 규칙, 프로젝트, 대기·회신, 알람, 체크리스트,
실적과 문서가 PostgreSQL에 저장됩니다.

## 데이터 신뢰성 원칙

- 업무의 최종 기준은 Supabase `tasks` 테이블 하나입니다.
- `session_state`는 선택 메뉴와 열린 팝업 같은 화면 상태에만 사용합니다.
- 시간표는 `execution_date + start_time`, 오늘 마감은 `deadline`, 대기·회신은
  `followup_at`만 사용합니다.
- 반복 일정은 규칙 한 건으로 계산하며 화면 재실행 때 업무 행을 추가하지 않습니다.
- 일반 삭제는 `deleted_at`, 반복 일정의 오늘만 삭제는 `excluded_dates`에 기록합니다.
- 앱 시작, 메뉴 이동, `st.rerun()`은 샘플 업무를 생성하지 않습니다.
- 동일 업무가 여러 화면에 보여도 항상 같은 `task_id`를 참조합니다.

## 알람 범위

일정 알람은 앱이 브라우저에서 열려 있는 동안 30초마다 현재 시각을 확인해 Streamlit
알림으로 표시합니다. 같은 일정·같은 날짜의 알람은 `alarm_last_fired_at`에 기록되어
화면 재실행 때 반복 표시되지 않습니다. 브라우저가 완전히 종료된 상태의 푸시 알림은
별도의 푸시 서비스나 메시지 연동이 필요합니다.

## AI 대본 작성 연결

선택 기능입니다. Streamlit Secrets에 아래 값을 추가하면 활성화됩니다.

```toml
OPENAI_API_KEY = "YOUR-OPENAI-API-KEY"
OPENAI_MODEL = "gpt-5-mini"
```

## 서체와 사진

기기에 `SeoulNamsan`이 있으면 우선 사용하고, 없으면 `Pretendard`, `Noto Sans KR`,
시스템 한글 글꼴 순서로 표시합니다. 제공 사진은 낮은 대비 오버레이와 함께 사이드바와
마무리 카드에 사용됩니다. 공개 GitHub 저장소에 업로드하면 내장 사진도 공개될 수
있으므로 사진 공개를 원하지 않으면 비공개 저장소를 사용하세요.

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

- 9개 화면 전체 기동
- 업무 생성 → 캘린더 → 상세 수정 → 전체 업무 반영
- 완료 → 이전 단계 복구, 삭제 후 재생성 방지, 반복 규칙 계산
- `assets` 폴더 누락 시 내장 이미지 대체 실행
