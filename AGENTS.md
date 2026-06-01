# Repository Instructions

기본 응답은 한국어로 하고, 변경점과 검증 결과를 먼저 짧게 말한다.

이 저장소는 Windows-first modding workflow tool이다. 실제 게임 파일, 실제 모드
아카이브, crash dump, DLL, EXE를 커밋하지 않는다. 테스트는 `tests/fixtures` 아래의
합성 fixture만 사용한다.

구현 원칙:

- Core 로직은 GUI 없이 동작해야 한다.
- GUI는 얇게 유지하고 `src/modforge/core`를 호출한다.
- 기본 동작은 dry-run이다.
- 실제 게임 폴더에 쓰는 기능은 manifest, backup, restore 테스트가 갖춰지기 전까지
  구현하지 않는다.
- Windows 경로를 우선 고려하되 `pathlib.Path`를 사용해 테스트 가능하게 작성한다.

검증 기본값:

```powershell
python -m unittest discover -s tests
```

선택 도구가 설치되어 있으면:

```powershell
pytest
ruff check .
```
