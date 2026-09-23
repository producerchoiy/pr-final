# 홍보의 바다 · chopd 배포본

홍보 기획·운영·일정·회신·콘텐츠 실적을 한곳에서 관리하는 Cloudflare Workers + D1 웹앱입니다. GitHub `producerchoiy/chopd` 저장소에 그대로 올린 뒤 기존 `chopd` Worker에 배포할 수 있습니다.

> 이 버전은 Streamlit 앱을 Cloudflare용으로 다시 구성한 프로젝트입니다. Cloudflare Workers에서는 Streamlit 서버를 직접 실행하지 않으므로 `streamlit_app.py`를 배포하는 방식과 섞지 마세요.

## 주요 기능

- 완료 업무를 이전 상태로 되돌리는 `업무 다시 열기`
- 같은 `task_id`를 오늘·긴급·대기·캘린더·프로젝트 화면에서 공동 사용
- 실행일·마감일·회신일을 구분하여 유령 일정 방지
- 매일·평일·매주 반복 일정과 특정 날짜만 제외
- 30초 간격 일정 알림, 브라우저 알림 권한 지원
- 이전 날·다음 날·날짜 선택으로 과거 시간표와 완료 기록 확인
- 월간 스케줄표 날짜 칸에서 해당 날짜 일정 즉시 추가
- 월간 스케줄표의 날짜 칸 전체를 클릭하거나 키보드 Enter로 일정 추가
- 새 탭 첫 접속 시 비밀번호 인증, 인증 전 D1 API 접근 차단
- 사이트가 열려 있을 때 30분 전 알림음·화면 알림·브라우저 알림
- 자동 정렬과 내 순서(드래그, 모바일 위·아래 버튼)
- 프로젝트, 콘텐츠 실적, 자료 수정·삭제
- CSV 실적 다운로드
- 접속 잠금과 비밀번호 해제(기본값 `0915`)
- 휴대폰·태블릿·데스크톱 반응형 화면
- 사용자가 제공한 사진을 글자와 겹치지 않는 독립 액자로 배치
- D1만 실제 업무 데이터의 단일 출처로 사용하며, 화면 재실행 시 샘플 데이터를 자동 생성하지 않음

## 1. GitHub에 올리기

ZIP을 푼 뒤 `PR-Flow-Cloudflare-D1` 폴더 안의 파일 전체를 새 GitHub 저장소 루트에 올립니다. `src`, `public`, `migrations`, `scripts` 폴더 구조를 그대로 유지하세요.

기존 저장소를 완전히 교체하려면 GitHub 웹에서 이전 파일을 지운 커밋을 만든 뒤 이 폴더의 전체 파일을 업로드할 수 있습니다. Cloudflare 연결은 같은 저장소와 같은 브랜치를 유지하면 다시 만들 필요가 없습니다.

## 2. D1 데이터베이스 만들기

Node.js 20 이상이 설치된 컴퓨터에서 저장소 폴더를 열고 다음 명령을 순서대로 실행합니다.

```bash
npm install
npx wrangler login
npx wrangler d1 create pr-flow-db
```

마지막 명령의 출력에 있는 `database_id`를 복사하여 다음과 같이 설정합니다.

```bash
node scripts/configure-d1.mjs 여기에_DATABASE_ID_붙여넣기
npm run db:migrate:remote
```

마이그레이션은 최초 1회 적용하고, 이후 `migrations`에 새 파일이 생겼을 때 다시 실행합니다. 로컬 테스트 DB는 아래 명령으로 준비합니다.

```bash
npm run db:migrate:local
```

## 3. 처음 접속 비밀번호 설정

화면 잠금 비밀번호를 Cloudflare의 암호화된 Secret으로 저장합니다.

```bash
npx wrangler secret put APP_LOCK_PASSWORD
```

질문이 나오면 `0915`를 입력합니다. Secret이 없을 때도 기본값은 `0915`이지만, 실제 배포에서는 반드시 Secret 설정을 권장합니다.

이번 버전은 화면만 가리지 않고 서명된 보안 쿠키가 없는 요청의 D1 API 접근도 차단합니다. 새 브라우저 탭의 첫 접속에서는 비밀번호를 다시 확인하고, 잠금 버튼을 누르면 서버 세션도 즉시 해제됩니다. 조직 전체의 계정 기반 접근 제어가 필요하면 Cloudflare Access를 추가로 사용할 수 있습니다.

명령 프롬프트 로그인 문제를 피하려면 Cloudflare 대시보드의 **Workers & Pages → chopd → Settings → Variables and Secrets**에서도 `APP_LOCK_PASSWORD`를 Secret으로 만들고 값 `0915`를 저장할 수 있습니다.

사이트 내부 알림은 사이트가 열려 있을 때 30초마다 확인하며, 알림 시각이 되면 알림음과 화면 상단 알림창이 함께 나타납니다. 브라우저의 자동 재생 정책에 맞춰 비밀번호 해제 시 알림음을 준비합니다. **설정 → 사이트 알림 테스트**를 눌러 현재 기기의 소리 크기와 무음 모드를 확인하세요.

## 4. 먼저 직접 배포해 보기

```bash
npm run deploy
```

표시된 `workers.dev` 주소를 열어 확인합니다. 데이터가 비어 있는 것이 정상이며, 앱에서 등록한 업무만 D1에 저장됩니다.

## 5. GitHub와 Cloudflare 자동 배포 연결

Cloudflare 대시보드에서 다음 순서로 연결합니다.

1. **Workers & Pages → Create application → Import a repository**로 이동합니다.
2. 이 프로젝트를 올린 GitHub 저장소와 배포 브랜치를 선택합니다.
3. 루트 디렉터리는 `/`로 둡니다.
4. 빌드 명령은 비워 두거나 `npm run check`를 사용합니다.
5. 배포 명령은 `npx wrangler deploy`로 설정합니다.
6. 저장 후 배포합니다.

이 배포본의 `wrangler.jsonc`에는 `chopd` Worker 이름과 연결된 D1 ID가 반영되어 있습니다. `APP_LOCK_PASSWORD`는 GitHub 파일에 쓰지 말고 Cloudflare Secret으로 설정하세요.

## 모바일·태블릿 사용

- 820px 이하에서는 왼쪽 메뉴가 하단 가로 메뉴로 바뀝니다.
- 카드와 입력 폼은 한 열로 바뀌고, 표는 가로 스크롤됩니다.
- 사진 액자는 별도 가로 갤러리가 되어 글자와 겹치지 않습니다.
- 휴대폰에서는 드래그 대신 카드의 위·아래 이동 버튼으로 순서를 바꿀 수 있습니다.
- 가로 화면 높이가 낮을 때는 업무 공간을 넓히기 위해 상단 액자만 숨깁니다.

## 데이터 원칙

- 실제 업무 정보는 D1에만 저장합니다.
- `sessionStorage`는 현재 탭의 잠금 해제 여부만 관리하고 실제 API 인증은 서명된 HttpOnly 쿠키로 확인합니다.
- 완료는 삭제가 아니라 상태 변경이며, 완료 직전 상태를 `previous_status`에 보관합니다.
- 삭제는 `deleted_at`을 기록하는 소프트 삭제입니다.
- 반복 일정은 원본 규칙 하나로 계산하고, 오늘만 삭제하면 `excluded_dates`에 기록합니다.
- 샘플 데이터 자동 삽입 코드가 없으므로 삭제한 일정이 새로고침 후 다시 생기지 않습니다.

## 프로젝트 구조

```text
PR-Flow-Cloudflare-D1/
├── migrations/0001_initial.sql   # D1 기본 테이블과 인덱스
├── public/                        # 반응형 화면과 사진
├── scripts/configure-d1.mjs       # D1 ID 설정 도우미
├── src/index.js                   # Worker API
├── package.json
└── wrangler.jsonc
```

## 점검 명령

```bash
npm run check
npx wrangler dev
```

로컬 주소에서 업무 등록 → 수정 → 완료 → 다시 열기 → 삭제 → 새로고침 순서로 확인하세요.

## 참고

- 기존 Streamlit/Supabase 데이터는 자동으로 D1에 복사되지 않습니다.
- 사이트 알림은 사이트가 열려 있고 기기가 음소거 상태가 아닐 때 동작합니다.
- 사진은 `public/assets`의 동일한 파일명으로 교체할 수 있습니다.

공식 문서: [Cloudflare Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/), [Cloudflare D1 Migrations](https://developers.cloudflare.com/d1/reference/migrations/)
