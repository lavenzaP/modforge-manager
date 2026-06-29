# ModForge Manager

[English README](README.md)

ModForge Manager는 Windows용 Unreal Engine 게임 모드 매니저입니다.

지금은 가장 기본적인 흐름에 집중합니다. 모드를 추가하고, 켜고 끄고,
순서를 바꾼 뒤 현재 목록을 게임 폴더에 적용하고, 가능하면 Steam으로
게임을 실행합니다.

## 현재 상태

이 저장소는 단순한 C# WinForms 런처 중심으로 다시 만들어지고 있습니다.

현재 작동하는 기능:

- `.pak`, `.ucas`, `.utoc` loose 파일 추가
- `.zip`, `.rar`, `.7z` 압축 파일을 게임별 ModForge 모드 폴더로 압축 해제
- 이미 압축을 푼 모드 폴더를 드래그 앤 드롭으로 추가
- 모드 켜기/끄기, 순서 변경, 검색
- `modforge-state.json`에 모드 On/Off와 우선순위 저장
- 게임 프로필별 모드 라이브러리 분리
- Unreal 패키지 모드를 `<Project>\Content\Paks\~mods`에 적용
- 게임별 PAK/UCAS/UTOC 설치 폴더 변경
- 간단한 UE4SS/runtime DLL 파일을 `<Project>\Binaries\Win64`에 적용
- 최신 ModForge 적용 파일이 그대로 있는지 확인
- manifest와 hash를 이용한 최신 적용 복원
- 적용 전 충돌 파일과 skipped 파일 확인
- Steam manifest를 찾을 수 있으면 `steam://rungameid/<appid>`로 게임 실행
- 휴대용 zip 패키지 생성

아직 없는 기능:

- Nexus 다운로드
- 시작 메뉴 바로가기와 제거 기능이 있는 네이티브 설치 프로그램
- 고급 충돌 해결 UI
- PAK 재패킹 또는 암호화된 PAK 수정
- 전체 번역 에디터
- VFS, hardlink, symlink 방식 배포

## 기본 경로

게임 프로필은 런처 실행 파일 옆에 저장됩니다.

```text
<ModForge 폴더>\games.json
```

게임별 기본 모드 폴더:

```text
<ModForge 폴더>\Games\<Game Name>\Mods
```

적용 manifest와 백업:

```text
<ModForge 폴더>\Games\<Game Name>\.modforge
```

## 빌드

필요한 것:

- Windows
- .NET 9 SDK

런처 빌드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_launcher.ps1
```

결과:

```text
dist\ModForge.Launcher\ModForge.Launcher.exe
```

## Smoke Test

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
```

smoke test는 런처를 빌드하고, 내장 self-test를 실행하고, 임시 ModForge
모드 폴더를 스캔합니다. 실제 게임 파일은 건드리지 않습니다.

## 휴대용 패키지

휴대용 zip 생성:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_launcher.ps1
```

결과:

```text
dist\ModForge.Launcher-win-x64.zip
```

zip을 원하는 폴더에 압축 해제한 뒤 `ModForge.Launcher.exe`를 실행하면 됩니다.
게임 프로필, ModForge 모드 폴더, manifest, 백업은 실행 파일 옆에 저장됩니다.

## 에이전트 작업 흐름

범위 지정, 초보 유저 리뷰, 안전 리뷰, 릴리스 확인은
[docs/agent-pipeline.md](docs/agent-pipeline.md)를 사용합니다.

## CLI 확인

모드 폴더 스캔:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --smoke --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

켜져 있는 모드 적용:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --apply --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

최신 적용 복원:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --undo --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

최신 적용 파일 확인:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --verify --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

## 안전 모델

`Apply Changes`는 이전 ModForge 적용 내역이 있으면 먼저 되돌린 뒤,
현재 On 상태인 모드만 다시 적용합니다. 파일 복원이나 삭제는 이전
ModForge manifest와 여전히 일치할 때만 진행합니다. 다른 프로그램이나
사용자가 게임 파일을 바꾼 경우에는 조용히 덮어쓰지 않고 중단합니다.

`Check Applied Mods`는 최신 ModForge 적용 파일이 아직 그대로 있는지
확인합니다. `Restore Last Apply`는 적용된 파일이 바뀌었거나 사라졌으면
복원을 막습니다.

## 저장소 구조

현재 활성 제품 경로는 작게 유지합니다.

```text
desktop/ModForge.Launcher/
scripts/build_launcher.ps1
scripts/package_launcher.ps1
scripts/smoke_launcher.ps1
```

이전 Python, WPF, WinUI 실험 코드는 현재 제품 경로에서 제거했습니다.

## 라이선스

MIT입니다. 자세한 내용은 [LICENSE](LICENSE)를 확인하세요.
