# Suno Premier Studio 다운로드와 기존 v6 곡의 일회성 복구

2026-10-22 확인. 이 문서는 OpenClaw가 소유 계정에서 이미 만든 곡을 공식 UI로 저장하고 제작을 이어 가는 절차다. 실제 계정의 Premier/Studio 접근 가능 여부는 로그인된 화면에서 확인한다.

## 공식 근거와 자동화에서 정한 규칙

- [다운로드 한도 안내](https://help.suno.com/en/articles/13926209): Premier의 일반 다운로드는 월 60곡이고, Studio 작업은 이 일반 한도의 적용 대상이 아니다. 생성 크레딧과 파일 다운로드 한도는 별개다. 일반 다운로드 잔여량이 0이라는 이유만으로 Studio 획득이나 v6 제작 전체를 중단하지 않는다.
- [Studio 2.0 소개](https://help.suno.com/en/articles/13670529): Premier에서 Studio를 이용할 수 있으며, Library의 곡 메뉴에서 `… → Edit → Open in Studio`로 기존 곡을 연다.
- [Studio 라이브러리](https://help.suno.com/en/articles/13670849): Studio 오른쪽 Library에서 곡을 찾아 타임라인으로 가져올 수 있다.
- [Studio 내보내기](https://help.suno.com/en/articles/13925249): 타임라인 위쪽 오른쪽 `Export`에는 `Full Song`, `Selected Time Range`, `Multitrack`이 있고, 오디오 클립 우클릭 메뉴에는 `Download .WAV`가 있다.

위 내용은 공식 기능이다. 아래의 복구 우선순위, 원본 보존, 파일 검증, 완료 장부와 재탐색 금지는 이 프로젝트의 운영 규칙이다. UI의 버튼 위치·번역·다운로드 전달 방식은 바뀔 수 있으므로 현재 화면을 읽는다. 특정 좌표나 과거 스냅샷 selector를 그대로 재사용하지 않는다. 공식 Export 문서는 WAV를 설명하고 Studio 2.0 소개는 WAV/MP3를 설명하므로, 특정 형식을 가정하지 말고 실제 받은 파일을 검사한다.

## 1. 진행 중인 작업과 원본 식별

1. runtime checkout에서 기존 `openclaw-status`, backlog, release 상태를 확인한다. 기존 공유 app-side lock을 획득하고 작업 중 heartbeat를 유지한다. 다른 실행의 live lock을 가져오지 않는다. 파일 장부의 잠금은 이 브라우저 잠금을 대신하지 않는다.
2. 아래 장부의 `status`를 먼저 읽는다. `fresh_production`이면 **과거 라이브러리를 열지 않는다**. 이 문서의 기존 곡 탐색 부분도 다시 읽을 필요가 없다. 현재 생성한 source ID에 대한 다운로드 단계만 사용한다.
3. 원본 곡의 `https://suno.com/song/ORIGINAL_ID`, 제목, 원본 모델 `v6` 증거, 표시된 전체 길이, 원래 release/channel, 가사·style·exclude-style을 기록한다. 모델은 제목이나 생성 날짜로 추정하지 않는다. Studio에서 파생된 export ID도 원본 ID를 대신하지 못한다.
4. 이미 app에 올라간 source ID/manifest/receipt가 있으면 연결된 실제 파일과 승인된 app track을 재사용한다. 제목이 같다는 이유만으로 동일 곡으로 판단하지 않는다. 이미 렌더·업로드 중이거나 공개된 release의 첨부곡을 바꾸지 않는다.

## 2. 원본 곡에서 Studio 열기

1. 기존 로그인 프로필의 Suno에서 지정 workspace `playlist_openclaw_desktop`을 확인한다. 새 계정·다른 프로필로 옮기지 않는다.
2. 다운로드할 **해당 곡 한 개**의 행/카드를 찾고 `…` 메뉴를 연다.
3. `Edit` 하위 메뉴를 펼치고 필요하면 메뉴 안을 스크롤해 `Open in Studio`를 누른다. 일반 Library의 `Download` 버튼으로 되돌아가지 않는다.
4. Studio가 로딩되고 곡이 배치될 때까지 기다린다. 같은 source ID로 이미 만든 Studio 프로젝트가 있으면 그 프로젝트를 다시 연다. 타임아웃마다 프로젝트를 새로 만들지 않는다.
5. 곡이 타임라인에 없으면 Studio의 오른쪽 Library를 열어 **동일 source ID**의 곡을 찾아 오디오 트랙에 한 번만 가져온다. 기본적으로 원본 full mix 한 클립만 둔다. 다른 곡, 중복 클립, 추가 stem, 재생 중인 Library 미리듣기가 export에 섞이지 않게 확인한다.
6. 원본 클립이 잘리지 않았고 곡 시작이 타임라인 처음에 있으며, 전체 길이와 끝부분이 보존됐는지 확인한다. 템포/피치/속도/볼륨/이펙트를 변경하거나 Remix/새 generation을 누르지 않는다. 이 작업은 다운로드이며 새 음악 생성으로 집계하지 않는다.

## 3. 전체 오디오 획득

먼저 **원본 full-mix 오디오 클립**을 우클릭해 `Download .WAV`를 사용한다. 우클릭 대상이 개별 stem, 짧은 region 또는 다른 클립이 아닌지 확인한다. 여러 region으로 나뉜 프로젝트는 이 방법으로 전체 곡을 받았다고 간주하지 않는다.

그 방법이 보이지 않거나 프로젝트 전체가 필요하면 오른쪽 위 `Export → Full Song`을 사용한다. `Selected Time Range`, `Multitrack`, `Split Stems`, `Get MIDI`를 선택하지 않는다. 선택 구간만 저장하거나 유료 stem/MIDI 작업으로 우회하지 않는다.

브라우저 다운로드 수신을 **클릭 전에** 준비한다. 실제 download event/브라우저의 정상 다운로드 UI를 사용하고, 완료된 파일을 영구적인 source-ID 기반 경로로 보관한다. 예: `storage/suno-studio-audio/ORIGINAL_ID/original.wav`. Studio가 먼저 새 library export를 만들면 그 export URL을 원본과 연결해 기록하고, 그 결과 화면의 공식 다운로드를 사용한다. export에 보이는 정상 다운로드도 한도/결제를 요구하면 거기서 멈추고 실제 UI 차단을 기록한다.

`Export 완료`, Library 저장, `unlocked`, HTTP 200, 곡 미리듣기 성공은 **로컬 파일 수신 완료가 아니다**. `.crdownload`/`.part`, 빈 파일, HTML 응답을 오디오로 취급하지 않는다. 원본 source URL, Studio project URL, 파생 export URL이 있으면 별도 필드로 모두 남긴다.

## 4. 파일 검증과 app 반영

1. 파일이 실제 존재하고 0바이트가 아닌지 확인한다. helper의 `record`는 ffprobe로 오디오/길이를 검사하고 ffmpeg로 전체를 decode한 뒤 SHA-256을 남긴다. 원본 화면에서 기록한 전체 길이와 비교한다. 허용 오차(2초 또는 1% 중 큰 값)를 벗어나면 원인을 확인한다. 임의의 기대 길이를 넣어 잘린 파일을 통과시키지 않는다.
2. 이 검증은 듣기 평가가 아니다. 인간의 standing pre-approval에 따라 별도 청취 QC/평점/곡별 승인 요청 없이 진행한다. 모델 불명 곡을 v6로 태깅하거나 `user_rating=like`를 부여하지 않는다.
3. 기존 source ID의 승인된 app track이 있으면 해당 receipt를 연결한다. 없으면 기존 release에 `scripts/openclaw-release upload-audio`로 한 번 올린다. `--pending-review`는 사용하지 않는다. CLI의 실제 도움말에 있는 `--audio`, `--title`, `--release-id`, `--lyrics-file`, `--style`, `--exclude-style`, `--tags`만 사용한다. 증거가 있는 곡에만 private tag `suno_model:v6`를 넣는다. source ID와 model evidence는 run manifest와 `--prompt`에 보존한다; 없는 `--suno-model`/`--source-url` 옵션을 만들지 않는다.
4. 응답의 `ok=true`, `auto_approved=true`, `track.status=approved`, 실제 app track ID를 확인한다. 파일 수신은 성공했지만 app가 불통이면 상태를 `saved`로 남기고 **같은 로컬 파일**의 ingestion만 재개한다. 다시 Studio에서 받지 않는다.
5. 제목만으로 재업로드 여부를 판단하지 않는다. API 응답을 잃었으면 원래 release/source ID/업로드 receipt를 대조한 뒤 연결한다. 현재 스크립트의 receipt 기록은 로컬 장부이며 서버 ingestion을 대신 수행하지 않는다.

## 5. 한 번만 기존 미저장곡을 찾는 장부

명령은 runtime checkout에서 실행한다. 설치된 스킬에서는 `TOOL`에 해당 스킬 폴더의 script 경로를 쓴다. `RECOVERY_STATE`는 실행마다 바꾸지 않는다.

```bash
TOOL=skills/suno-studio-acquisition/scripts/recovery_state.py
RECOVERY_STATE=storage/suno-studio-recovery.json
python3 "$TOOL" --state "$RECOVERY_STATE" status
```

최초 복구에만 현재 workspace의 최신 원본 ID/시각을 cutoff로 고정하고 초기화한다. scope는 이 계정의 기존 자동 제작 workspace와 그 run manifest에 연결된 원본 곡이다. 계정 전체의 무관한 개인곡·추천곡·파생 export까지 훑지 않는다. 장부가 없다면 이동된 장부/백업을 먼저 확인하고, 이미 완료한 복구를 새 batch로 반복하지 않는다.

```bash
python3 "$TOOL" --state "$RECOVERY_STATE" init \
  --batch-id existing-v6-recovery-20261022 \
  --workspace playlist_openclaw_desktop \
  --cutoff 'ACTUAL_NEWEST_ORIGINAL_ID_AND_UI_TIME'
```

페이지별로 원본 모델 증거를 확인하고 local/app manifests와 한 번 대조한다. `model=v6`로 확인한 곡은 기존 파일이 있든 없든 목록에 넣고, 기존 파일이 있으면 즉시 검증/receipt 연결한다. v5.5/v5/unknown은 증거와 제외 이유를 남겨 재검사하지 않는다. Library의 일반 다운로드 badge만으로 Studio 파일 저장 여부를 추정하지 않는다.

페이지 파일은 JSON 배열이다. 아래 UUID는 예시이며 실제 source ID와 증거로 바꾼다. 필요하면 `release_id`, `lyrics_file`, `style`, `exclude_style`, `expected_seconds`도 기록한다.

```json
[
  {
    "source_id": "11111111-1111-4111-8111-111111111111",
    "source_url": "https://suno.com/song/11111111-1111-4111-8111-111111111111",
    "title": "실제 원본 제목",
    "model": "v6",
    "model_evidence": "원본 상세 v6 label screenshot/manifest 경로",
    "channel_title": "HaruHaru",
    "expected_seconds": 240
  }
]
```

```bash
python3 "$TOOL" --state "$RECOVERY_STATE" inventory \
  --manifest PAGE_JSON --cursor 'LAST_VISITED_ORIGINAL_ID_AND_PAGE_ANCHOR'
python3 "$TOOL" --state "$RECOVERY_STATE" pending --limit 5
```

페이지를 처리할 때마다 cursor와 항목을 저장한다. 같은 원본 ID는 중복 등록되지 않는다. 중단되면 저장된 anchor부터 이어서 진행하며 Library를 처음부터 다시 스캔하지 않는다. 전체 cutoff 범위의 끝에 도달한 증거(범위·마지막 원본 ID·UI 확인)를 기록했을 때만 `seal`한다. 필터로 일부만 본 상태, CAPTCHA, 페이지 오류, timeout, "다음이 안 보임"은 완료 증거가 아니다.

```bash
python3 "$TOOL" --state "$RECOVERY_STATE" seal --evidence 'ACTUAL_SCOPE_AND_END_OF_LIST_EVIDENCE'
python3 "$TOOL" --state "$RECOVERY_STATE" record \
  --source-id ORIGINAL_ID --audio ABSOLUTE_AUDIO_PATH \
  --expected-seconds ACTUAL_ORIGINAL_DURATION --studio-url ACTUAL_STUDIO_URL
python3 "$TOOL" --state "$RECOVERY_STATE" accept \
  --source-id ORIGINAL_ID --receipt APPROVED_UPLOAD_OR_EXISTING_TRACK_RECEIPT_JSON
```

receipt는 `{"ok":true,"track":{"id":"실제 app track ID","status":"approved"}}` 형식의 실제 응답이다. 기존 track 조회 응답을 감쌀 때도 실제 조회 결과를 사용한다. 실패한 파일은 `block --source-id ORIGINAL_ID --reason ACTUAL_ERROR`로 남기고 알려진 ID만 재시도한다. `saved`이면 다운로드는 반복하지 않고 app 반영만 한다. `blocked`/`pending`이 하나라도 남으면 완료 처리하지 않는다. 특정 곡이 막혀도 다른 알려진 곡은 저장할 수 있다.

확인한 v6 곡이 모두 로컬 검증과 app 반영을 마치면:

```bash
python3 "$TOOL" --state "$RECOVERY_STATE" complete
python3 "$TOOL" --state "$RECOVERY_STATE" status
```

완료 시 `phase=complete`, `action=fresh_production`, `scan_library=false`가 남는다. 다음 pass에서는 이 작은 응답만 읽고 즉시 일반 제작으로 간다. helper는 브라우저를 열지 않으며 완료 장부를 자동으로 재개/초기화하지 않는다. 장부·원본·receipt를 삭제하지 않는다. 활성 run 계획의 "과거 미저장곡 탐색" TODO만 제거한다. 스킬/cron에 매번 Library 재탐색 지시를 추가하지 않는다. state는 skill 업데이트와 무관한 영구 storage에 보관한다.

## 6. 복구된 곡으로 플레이리스트를 먼저 만들고 새 제작 지속

- 이번 초기 복구에서는 이미 만든 verified-v6 곡을 먼저 저장·업로드하고, 원래 진행 중인 release와 같은 channel/lane/가사/arrangement에 맞게 활용한다. 복구를 위해 같은 노래를 다시 생성하지 않는다. 최신 지시가 기존의 "새 곡 opener를 먼저 생성"보다 우선한다.
- 채널별 자료를 섞어서 한 시간을 채우지 않는다. Scripture는 원래 passage/release 관계를 유지하고 다른 구절용 filler로 재사용하지 않는다. 새로 구성하는 playlist는 v6-only이며 v5.5/unknown/Good legacy를 섞지 않는다.
- 다운로드 복구가 끝나면 호환되는 저장곡으로 playlist를 먼저 완성한다. 일부 곡만으로 한 시간이 안 되면 그 곡들은 보존하고 같은 lane의 **부족분만** 새 v6로 만든다. 회복 장부가 `complete`인 뒤에도 기존 catalog 검색은 정상 playlist 조립 범위에서만 가능하다; 과거 Suno의 미저장곡 전수 탐색으로 돌아가지 않는다.
- 정상 제작은 `Create v6 → 현재 batch의 원본 IDs 기록 → Studio 획득 → 검증 → quiet upload → 같은 lane으로 한 시간 조립 → 기존 app render/publish`로 이어진다. 현재 batch의 실패 ID는 그 batch manifest로 재개한다.
- 이미 렌더된 영상의 app upload lane은 별도로 계속 진행할 수 있다. 브라우저/release mutation은 공유 lock으로 직렬화한다. 서버가 공개 예약을 관리하므로 OpenClaw cron이나 YouTube Studio에서 수요일 예약을 다시 구현/수정하지 않는다.

## 7. 다운로드가 멈췄을 때

한 파일의 공식 획득을 한 번 재시도한 뒤 실제 download event, 완료 파일/바이트, 오류를 확인한다. 로그인/CAPTCHA/수동 검증은 유지하고 사람에게 알린다. 결제·추가 다운로드·계정 전환·비공개 API·raw CDN/cache 추출로 해결하지 않는다.

공식 export가 이미 만들어졌지만 수신이 timeout/0바이트인 경우에는 같은 export를 다시 연다. active generation, 미저장 Studio 편집, CAPTCHA가 없고 관리 브라우저를 재시작할 권한이 있을 때만 기존 프로필을 보존해 한 번 stop/start한다. 다른 Chrome 세션을 강제 종료하지 않는다. 복구가 안 되면 해당 ID만 blocked로 남긴다. 2026-10-06의 로컬 진단에서는 같은 공식 export의 다운로드 수신을 이 방법으로 복구했지만, 그것이 모든 오류의 원인/해법이라는 뜻은 아니다.
