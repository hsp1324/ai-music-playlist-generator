# Suno Studio 획득과 일회성 v6 복구

2026-10-22 사용자 지시: Premier Studio 공식 다운로드를 사용한다. 이미 생성했지만 저장하지 못한 v6 곡을 한 번 복구해 먼저 playlist에 활용하고, 이후 새 v6 제작을 계속한다. 완료한 과거 미저장곡 탐색은 반복하지 않는다.

**같은 날 후속 지시가 우선한다:** 기존에도 Studio 경로로 받았음을 확인한 뒤 사용자가 과거 전수 탐색을 취소했다. 현재 장부는 `phase=cancelled`, `action=fresh_production`이며 완료로 위장하지 않는다. 과거 목록·미매칭 수를 다시 조사하지 말고, 현재 제작분의 ID가 알려진 누락 파일만 비용이 적을 때 확보한다. 음원이 충분한 HaruHaru 등의 기존 플레이리스트는 신곡 추가보다 완성·렌더·업로드를 우선한다.

- [화면별 상세 절차, 원본/파일 검증, 장부 명령, 완료 후 동작](../skills/suno-studio-acquisition/references/studio-download.md)
- [바로 설치 가능한 OpenClaw 스킬](../skills/suno-studio-acquisition/SKILL.md)

설치 및 확인은 runtime checkout에서 실행한다:

```bash
python3 scripts/install_suno_studio_skill.py
openclaw skills info suno-studio-acquisition
```

기본 설치 대상은 `~/.openclaw/workspace/skills/suno-studio-acquisition`이다. 다른 workspace는 `--workspace ABSOLUTE_WORKSPACE`로 지정한다. 설치는 실제 음악 복구 완료나 cron 재활성화를 뜻하지 않는다. 사용 중인 runner가 workspace skills를 읽도록 다음 turn에서 확인한다. 파일 권한/실행 환경이 차단하면 설치됐다고 보고하지 않는다.

기존 backlog/producer는 새 skill이 아직 로드되지 않았더라도 runtime checkout의 다음 명령으로 영구 장부를 확인할 수 있다:

```bash
python3 skills/suno-studio-acquisition/scripts/recovery_state.py \
  --state storage/suno-studio-recovery.json status
```

최초 discovery와 known-ID recovery 동안만 복구 상세 지침을 읽는다. 완료 후에는 compact status 한 번으로 일반 제작에 진입하며, 과거 Library 탐색·대량 다운로드 재검사를 하지 않는다. 기존 음악·승인·가사·원본 증거·이미지·release·서버의 공개 예약은 보존한다.
