# ModForge Manager

[English README](README.md)

ModForge Manager는 Unreal Engine 게임을 위한 작은 Windows 모드 매니저입니다.

지금은 가장 중요한 기본 흐름에 집중합니다. 모드를 추가하고, 켜고 끄고, 현재 목록을 게임 폴더에 적용하고, 가능하면 Steam으로 게임을 실행합니다.

## 빠른 시작

일반 사용자는 이렇게 쓰면 됩니다.

1. [Releases](https://github.com/lavenzaP/modforge-manager/releases)에서 `ModForge.Manager-v0.1.2-preview.1-win-x64.zip`을 다운로드합니다.
   직접 빌드하려는 경우가 아니라면 `Source code`는 받지 마세요.
2. 원하는 폴더에 압축을 풉니다.
3. `ModForge.Launcher.exe`를 실행합니다.
4. `More` -> `Add Steam Game`을 쓰거나 Unreal 게임 폴더를 직접 선택합니다.
5. 모드 압축 파일, 모드 폴더, 또는 `.pak/.ucas/.utoc` 파일을 앱에 드래그합니다.
6. 모드를 켜거나 끈 뒤 `Apply Changes`를 누릅니다.

릴리스 zip은 self-contained입니다. Visual Studio, .NET SDK, 빌드 과정 없이 실행해서 써볼 수 있습니다.

아직 설치 프로그램은 없습니다. 앱이 서명되어 있지 않아서 Windows SmartScreen 경고가 뜰 수 있습니다. 일반 실행에는 관리자 권한이 필요하지 않지만, 게임 폴더가 쓰기를 막는 위치라면 권한 문제가 날 수 있습니다.

안전 기본값:

- ModForge는 자체 모드 라이브러리를 실행 파일 옆에 저장합니다.
- `Apply Changes`는 현재 켜진 모드만 적용합니다.
- `Check Applied Mods`는 최신 ModForge 적용 파일이 그대로 있는지 확인합니다.
- `Restore Last Apply`는 ModForge 밖에서 파일이 바뀐 경우 복원을 막습니다.

## 현재 상태

이 저장소는 단순한 C# WinForms 런처 중심으로 다시 만들어지고 있습니다.

현재 작동하는 기능:

- `.pak`, `.ucas`, `.utoc` loose 파일 추가
- `.zip`, `.rar`, `.7z` 압축 파일을 선택된 게임의 ModForge 모드 폴더로 압축 해제
- 이미 압축을 푼 모드 폴더를 드래그 앤 드롭으로 추가
- 게임 파일이나 모드 라이브러리를 바꾸지 않고 모드 압축 파일 검사
- 가져온 압축 파일/폴더의 README 또는 설치 안내 보존
- wrapper 폴더가 하나만 있는 압축 파일의 최종 모드 폴더 이름 정리
- 모드 켜기/끄기, 순서 변경, 검색
- `modforge-state.json`에 모드 On/Off와 우선순위 저장
- 게임 프로필별 모드 라이브러리 분리
- 감지 가능한 Steam Unreal 게임 추가
- 게임 파일이나 모드 폴더를 지우지 않고 게임 프로필 이름 변경/삭제
- Unreal 패키지 모드를 `<Project>\Content\Paks\~mods`에 적용
- 게임별 PAK/UCAS/UTOC 설치 폴더 변경
- 간단한 UE4SS/runtime DLL 파일을 `<Project>\Binaries\Win64`에 적용
- 최신 ModForge 적용 파일이 그대로 있는지 확인
- manifest와 hash를 이용한 최신 적용 복원
- 적용 전 충돌 파일과 skipped 파일 확인
- 문제 해결용 redacted diagnostic report 내보내기
- Steam manifest를 찾을 수 있으면 `steam://rungameid/<appid>`로 게임 실행
- self-contained portable release zip 생성

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

## 개발자용 빌드

필요한 것:

- Windows
- .NET 9 SDK

개발용 런처 빌드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_launcher.ps1
```

결과:

```text
dist\ModForge.Launcher\ModForge.Launcher.exe
```

## 개발자용 Smoke Test

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
```

smoke test는 런처를 빌드하고, 내장 self-test를 실행하고, 임시 ModForge 모드 폴더를 검사합니다. 실제 게임 파일은 건드리지 않습니다.

## Portable Package

self-contained portable zip 생성:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_launcher.ps1
```

결과:

```text
dist\ModForge.Manager-v0.1.2-preview.1-win-x64.zip
```

zip을 원하는 폴더에 압축 해제한 뒤 `ModForge.Launcher.exe`를 실행하면 됩니다. 게임 프로필, ModForge 모드 폴더, manifest, 백업은 실행 파일 옆에 저장됩니다.

## 에이전트 작업 흐름

작업 범위 지정, 초보자 관점 리뷰, 안전 리뷰, 릴리스 검증에는 [docs/agent-pipeline.md](docs/agent-pipeline.md)를 사용합니다.

## 개발자용 CLI 확인

모드 폴더 스캔:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --smoke --mods "dist\ModForge.Launcher\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

켜진 모드 적용:

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

`Apply Changes`는 이전 ModForge 적용 내역이 있으면 먼저 되돌린 뒤, 현재 On 상태인 모드만 다시 적용합니다. 파일 복원이나 삭제는 이전 ModForge manifest와 실제 파일이 일치할 때만 진행합니다. 다른 프로그램이나 사용자가 게임 파일을 바꾼 경우에는 조용히 덮어쓰지 않고 중단합니다.

`Check Applied Mods`는 최신 ModForge 적용 파일이 아직 그대로 있는지 확인합니다. `Restore Last Apply`는 적용 파일이 바뀌었거나 사라졌으면 복원을 막습니다.

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
