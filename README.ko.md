# ModForge Manager

[English README](README.md)

ModForge Manager는 Windows용 Unreal Engine 게임 모드 매니저입니다.

지금은 가장 기본적인 흐름에 집중합니다. 모드를 추가하고, 켜고 끄고,
순서를 바꾸고, 현재 상태를 게임 폴더에 적용한 다음 Steam으로 게임을
실행합니다.

## 현재 상태

이 저장소는 C# WinForms 런처 중심으로 다시 만들고 있습니다.

현재 작동하는 것:

- `.pak`, `.ucas`, `.utoc` 단일 파일 추가
- `.zip`, `.rar`, `.7z` 압축 파일 자동 해제 후 추가
- 이미 압축을 푼 폴더 드래그 앤 드롭 추가
- 모드 활성화, 비활성화, 순서 변경, 검색
- `modforge-state.json`에 모드 On/Off와 우선순위 저장
- 게임 프로필별 독립 모드 폴더 관리
- Unreal 패키지 모드를 `<Project>\Content\Paks\~mods`에 적용
- UE4SS/runtime DLL 계열 파일을 `<Project>\Binaries\Win64`에 적용
- 최신 ModForge 적용 내역을 manifest/hash 기준으로 되돌리기
- Steam manifest를 찾을 수 있으면 `steam://rungameid/<appid>`로 게임 실행

아직 안 되는 것:

- Nexus 다운로드
- 설치 프로그램 패키징
- 자세한 충돌 검토 UI
- PAK 리패킹 또는 암호화된 PAK 수정
- 완전한 번역 에디터
- VFS, hardlink, symlink 방식 배포

## 기본 경로

게임 프로필 저장 위치:

```text
%APPDATA%\ModForge Manager\games.json
```

게임별 기본 모드 폴더:

```text
%USERPROFILE%\Documents\ModForge Manager\Games\<게임 이름>\Mods
```

적용 manifest와 백업 위치:

```text
%USERPROFILE%\Documents\ModForge Manager\Games\<게임 이름>\.modforge
```

## 빌드

필요한 것:

- Windows
- .NET 9 SDK

런처 빌드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_launcher.ps1
```

결과물:

```text
dist\ModForge.Launcher\ModForge.Launcher.exe
```

## Smoke Test

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
```

이 테스트는 런처를 빌드하고, 내장 self-test를 실행하고, 임시 ModForge 모드
폴더를 스캔합니다. 실제 게임 파일은 건드리지 않습니다.

## CLI 확인

모드 폴더 스캔:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --smoke --mods "%USERPROFILE%\Documents\ModForge Manager\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

활성화된 모드 적용:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --apply --mods "%USERPROFILE%\Documents\ModForge Manager\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

최신 적용 되돌리기:

```powershell
dist\ModForge.Launcher\ModForge.Launcher.exe --undo --mods "%USERPROFILE%\Documents\ModForge Manager\Games\Palworld\Mods" --game "C:\Program Files (x86)\Steam\steamapps\common\Palworld"
```

## 안전 모델

`Apply Changes`는 이전 ModForge 적용 내역이 있으면 먼저 되돌린 뒤, 현재 On
상태인 모드만 다시 씁니다. 이전에 쓴 파일이 다른 프로그램이나 사용자의
수정으로 바뀐 경우에는 조용히 덮어쓰지 않고 중단합니다.

## 저장소 구조

현재 활성 앱은 작게 유지합니다.

```text
desktop/ModForge.Launcher/
scripts/build_launcher.ps1
scripts/smoke_launcher.ps1
```

이전 Python, WPF, WinUI 실험 코드는 현재 제품 경로에서 제거했습니다.
