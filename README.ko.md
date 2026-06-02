# ModForge Manager

[English README](README.md)

ModForge Manager는 Windows 우선 데스크톱/CLI 모드 관리 도구입니다. 모드
프로젝트를 정리하고, 모드 폴더를 스캔하고, 적용 계획을 미리 확인하고, 안전한
충돌 리포트를 만드는 데 초점을 둡니다.

첫 버전은 Mod Organizer 2, Vortex, Nexus Mods를 대체하려는 프로젝트가
아닙니다. 현재 목표는 로컬 프로젝트 구조, dry-run 계획, 외부 도구 확인,
테스트용 fake fixture 기반의 안전한 core 동작입니다.

## 현재 상태

상태: MVP release candidate, staging-first public preview.

Python CLI/core가 테스트된 백엔드입니다. WinUI 3 셸은 현재 주 Windows
데스크톱 후보이며 실제 Python bridge로 프로젝트 생성/로드, 모드 스캔,
dry-run plan 생성, 모드 활성화/비활성화, 우선순위 변경, managed staging
폴더 적용을 실행합니다.

WinUI에서 게임 폴더에 직접 적용하는 기능은 아직 잠겨 있습니다. Python
CLI/core에는 game apply와 restore가 있지만, 공개 데스크톱 기준은 GUI workflow가
더 단단해질 때까지 staging-first입니다.

Python은 번들되지 않았고, 설치 프로그램도 아직 없습니다. Nexus Mods 다운로드,
암호화 PAK 처리, DRM/anti-tamper 우회, 에셋 편집, 아카이브 repack, virtual
filesystem 기능도 제공하지 않습니다.

라이선스 참고: 이 저장소는 소유자가 명시적으로 라이선스를 바꾸기 전까지
"All rights reserved" 상태입니다. public repository가 되었다고 해서 자동으로
오픈소스 라이선스가 부여되는 것은 아닙니다.

## 현재 범위

- 모딩 프로젝트 파일 생성 및 로드.
- 내장 게임 프로필 템플릿 선택.
- loose mod folder와 ZIP mod package 스캔.
- 설정된 외부 도구를 통한 PCK/PAK 패키지 추출 후 스캔 및 배포 계획 생성.
- 활성화된 모드 사이의 destination conflict 감지.
- dry-run deployment plan 생성.
- Markdown 리포트 생성.
- CLI 또는 GUI에서 외부 도구 경로 확인.
- 여러 mod set 생성, 전환, 모드 활성화/비활성화, set별 우선순위 지정.
- winning file을 staging directory로 복사하고 install manifest 작성.
- 백업을 만든 뒤 game root에 적용하고, manifest 기반 전체/선택 restore 실행.
- JSON/CSV/TXT 문자열을 translation CSV로 추출.
- 프로젝트 생성/열기, 스캔, 활성화 토글, 우선순위 변경, planning, reporting,
  applying, restoring을 위한 가벼운 desktop GUI 제공.
- GUI에서 외부 도구 경로 설정 및 확인.
- GUI mod table 정렬, scan warning 확인, 긴 작업의 progress/status 표시.
- CLI에서 manifest 확인, restore preview, project audit/export/import 실행.
- release-candidate 확인용 Windows smoke script 제공.

## Public Preview 범위

공개 데스크톱 preview는 staging-first입니다.

1. managed project를 만들거나 엽니다.
2. 모드를 스캔합니다.
3. dry-run deployment plan을 생성합니다.
4. conflict와 warning을 검토합니다.
5. winning plan을 project staging directory에 적용합니다.

Staging apply는 설정된 project staging directory에만 씁니다. 게임 설치 폴더에는
쓰지 않습니다. WinUI game-write 경로가 잠겨 있는 동안 game apply/restore가
필요하면 Python CLI를 사용해야 합니다.

## MVP RC 목표

MVP release-candidate baseline은 세 가지 핵심 mod family를 인증합니다.

- Monster Hunter Wilds 스타일 layout을 포함한 REFramework/nativePC 모드.
- `.pak`, `.ucas`, `.utoc` 파일을 포함한 Unreal `~mods` archive 모드.
- `.pck` 파일을 포함한 Godot/Slay the Spire 2 mods-folder workflow.

이 MVP에서 "완벽 지원"은 해당 family에 대해 safe local scan, plan, conflict
report, staging apply, game apply, manifest inspection, restore preview,
restore, doctor/audit check, synthetic fixture 문서화를 제공한다는 뜻입니다.
Nexus 다운로드, 암호화 PAK 지원, archive repacking, 임의 asset editing,
virtual filesystem, installer 생성을 뜻하지 않습니다.

현재 freeze 문서:

- [MVP status](docs/mvp-status.md)
- [Support matrix](docs/support-matrix.md)
- [Release checklist](docs/release-checklist.md)
- [Apply workflow certification](docs/apply-workflow-certification.md)
- [Changelog](CHANGELOG.md)
- [Architecture V2](docs/architecture-v2.md)
- [Windows shell plan](docs/windows-shell-plan.md)
- [Onboarding UX](docs/onboarding-ux.md)

## 빠른 시작

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

설치된 entrypoint 실행:

```powershell
modforge doctor
modforge profiles
modforge-gui
```

설치 없이 source tree에서 CLI를 직접 실행:

```powershell
$env:PYTHONPATH = "src"
python -m modforge doctor
python -m modforge --help
python -m modforge profiles
```

프로젝트 파일이 없으면 `doctor`는 runtime check와 project-file warning을 함께
출력합니다. warning도 자동화 실패로 처리해야 하면 `--strict`를 붙입니다.

Demo project 생성:

```powershell
$env:PYTHONPATH = "src"
python -m modforge project init --name Demo --game-root tests\fixtures\fake_game --mods-dir tests\fixtures\fake_mods
python -m modforge project init --name STS2 --game-root C:\Games\STS2 --mods-dir C:\Games\STS2\mods --profile sts2-mods
python -m modforge scan-mods
python -m modforge plan
python -m modforge plan --summary
python -m modforge report --output .modforge\conflict-report.md
python -m modforge profile disable betterui
python -m modforge profile create boss-run --name "Boss Run" --copy-from default
python -m modforge profile switch boss-run
python -m modforge profile list
python -m modforge tools check
python -m modforge tools set unreal_pak "C:\Tools\UnrealPak.exe {archive} -Extract {output}"
python -m modforge doctor
python -m modforge apply-staging --yes
python -m modforge apply-game --yes
python -m modforge manifests list
python -m modforge manifests latest
python -m modforge restore --manifest .modforge\manifests\<manifest-id>.json --preview
python -m modforge restore --manifest .modforge\manifests\<manifest-id>.json --yes
python -m modforge restore --manifest .modforge\manifests\<manifest-id>.json --path config\settings.json --yes
python -m modforge project audit
python -m modforge project export --out .modforge\project-export.json
python -m modforge translation extract --source tests\fixtures\fake_mods --output .modforge\strings.csv
```

임시 synthetic Monster Hunter Wilds / REFramework fixture로 안전 workflow 실행:

```powershell
$env:PYTHONPATH = "src"
$demo = Join-Path $env:TEMP ("modforge-safe-demo-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$game = Join-Path $demo "game"
$mods = Join-Path $demo "mods"
$project = Join-Path $demo "modforge.project.json"
$report = Join-Path $demo "conflict-report.md"

New-Item -ItemType Directory -Path $demo | Out-Null
Copy-Item -Recurse tests\fixtures\mhw_reframework_game $game
Copy-Item -Recurse tests\fixtures\mhw_reframework_mods $mods

python -m modforge doctor --project-file $project
python -m modforge project init --name "Wilds Demo" --game-root $game --mods-dir $mods --profile mhw-reframework --project-file $project
python -m modforge scan-mods --project-file $project
python -m modforge plan --project-file $project --summary
python -m modforge report --project-file $project --output $report

python -m modforge apply-staging --project-file $project
python -m modforge apply-staging --project-file $project --yes
python -m modforge apply-game --project-file $project
python -m modforge apply-game --project-file $project --yes

$manifest = Get-ChildItem (Join-Path $demo ".modforge\manifests") -Filter *.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python -m modforge restore --manifest $manifest.FullName --path nativePC/wp/swo/swo001/mod/swo001.mod3 --preview
python -m modforge restore --manifest $manifest.FullName --path nativePC/wp/swo/swo001/mod/swo001.mod3 --yes
```

가벼운 GUI 실행:

```powershell
.\run_gui.bat
```

비대화형 runtime check:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_gui.ps1 -Check
```

첫 usable GUI는 Python standard library의 `tkinter`를 사용합니다. Windows에서는
첫 Tk window 생성 전에 Tcl을 준비해서 embedded/local repaired Python 환경의
`init.tcl` lookup 문제를 피합니다.

실험적 Windows-first WPF shell 실행:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_shell.ps1
.\dist\ModForge.App\ModForge.App.exe
```

이 shell은 Windows-first 제품 방향 spike입니다. Python 없이 실행되고 guided
onboarding과 sample state data를 보여주지만, 실제 scan/plan/apply 작업은 WinUI
후보와 Python core 쪽으로 옮겨지고 있습니다.

.NET SDK 9 설치 후 WinUI 3 주 Windows shell 후보 실행:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_winui_shell.ps1
.\dist\ModForge.WinUI\ModForge.WinUI.exe
```

WinUI 3 결정과 WPF fallback 정책은 `docs\windows-shell-decision.md`와
`docs\winui3-comparison.md`를 참고하세요.

WinUI 3는 startup work를 피하도록 설계되어 있습니다. 사용자가 액션을 선택하기
전까지 startup scan, Python process, external tool probe를 실행하지 않습니다.
위 staging-first workflow는 Python core를 호출할 수 있습니다. WinUI public
preview에서는 staging output을 먼저 확인하도록 game apply가 잠겨 있습니다.

선택 사항인 PySide6 GUI 실행:

```powershell
pip install -e ".[gui]"
modforge-gui-qt --check-dependency
modforge-gui-qt modforge.project.json
```

## 내장 프로필

인증된 core profile:

- `reframework`
- `mhw-reframework`
- `unreal-pak`
- `godot-pck`
- `sts2-mods`

추가 template:

- `generic-folder`
- `mo2-mod`
- `unity-bepinex`
- `unity-melonloader`
- `bethesda-data`
- `cyberpunk-2077`

## 테스트

stdlib만으로 테스트 실행:

```powershell
python -m unittest discover -s tests
python -m modforge doctor --project-file modforge.project.json
.\scripts\release_smoke.ps1
.\scripts\release_smoke.ps1 -IncludeDesktop
.\scripts\public_staging_smoke.ps1
```

선택 dev tooling:

```powershell
.\scripts\dev_setup.ps1
pytest
python -m ruff check .
python -m ruff format --check .
.\scripts\lint.ps1
```

## 안전 기본값

- 기본은 dry-run입니다.
- Staging apply는 설정된 staging directory에만 씁니다.
- WinUI public preview에서는 game-folder apply가 잠겨 있습니다. 먼저 staging
  output을 확인해야 합니다.
- Game apply는 `--yes`가 필요하고, 덮어쓸 파일을 백업한 뒤
  `.modforge\manifests` 아래에 manifest를 씁니다.
- Restore는 `--yes`와 manifest path가 필요합니다. 특정 destination만 복원하려면
  `--path`를 하나 이상 추가합니다.
- Restore preview는 `--yes` 없이 동작하고, blocked action을 보고하며, 파일을
  쓰거나 manifest를 갱신하지 않습니다.
- 안전하지 않은 ZIP entry path는 무시되고 warning으로 보고됩니다.
- PCK/PAK extraction은 `.modforge\extracted` 아래에만 쓰며, 추출된 파일도 같은
  staging/game destination safety check를 거칩니다.
- 실제 게임 파일, 모드 아카이브, crash dump, DLL, executable을 commit하지
  마세요.
- synthetic fixture만 사용하세요.
- 지원하지 않는 container는 명확한 warning과 함께 실패합니다.
