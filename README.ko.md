# ModForge Manager

[English README](README.md)

ModForge Manager는 Windows 우선 데스크톱/CLI 모드 관리 도구입니다. 현재
방향은 "처음부터 모든 게임을 완벽히 지원"이 아니라, Unreal Engine 계열의
`~mods` staging 워크플로를 먼저 제대로 만드는 것입니다.

## 현재 상태

상태: Unreal-first workbench preview, staging-first public baseline.

Python CLI/core가 테스트된 백엔드입니다. WinUI 3 셸은 현재 주 Windows GUI
후보이며, Python bridge를 통해 프로젝트 생성/열기, 모드 스캔, dry-run plan,
모드 활성화/비활성화, 우선순위 변경, doctor/tools check, staging apply를
실행합니다.

WinUI에서 game folder에 직접 쓰는 기능은 아직 잠겨 있습니다. Python CLI/core에는
`apply-game`과 `restore`가 있지만, 공개 데스크톱 기준은 안전하게 staging-first로
유지합니다.

## 제품 방향

현재 우선순위는 Unreal-first Workbench v0입니다.

- 일반 Unreal `~mods` archive staging: `.pak`, `.ucas`, `.utoc`.
- Stellar Blade / CNS experimental profile: `SB/**`, `~mods`, JSON sidecar,
  UE4SS/runtime 경로처럼 실제 Unreal 게임에서 흔한 복잡한 경로를 실험.
- staging 이후 localization inventory: JSON/CSV/TXT는 즉시 추출 후보로,
  Unreal `.locres/.locmeta`는 향후 extractor가 필요한 리소스로,
  `.pak/.ucas/.utoc`는 내부 미검사 archive로, `.uasset/.uexp/.ubulk`는 편집하지
  않는 binary asset으로 표시.

REFramework/nativePC와 Godot/Slay the Spire 2 지원은 테스트 fixture로 계속
유지하지만, 새 기능 설계의 첫 제품 표면은 Unreal 쪽입니다.

## 할 수 있는 일

- 프로젝트 파일 생성/열기.
- built-in game profile 선택.
- loose folder, ZIP, PCK/PAK 계열 모드 스캔.
- 외부 도구가 설정된 경우 PCK/PAK 추출 후 plan 생성.
- destination conflict 감지.
- dry-run deployment plan 생성.
- staging directory에 winning files 복사 및 staging manifest 생성.
- CLI에서 game apply/restore 및 manifest inspection 실행.
- WinUI에서 staging manifest와 staged records 확인.
- JSON/CSV/TXT 기본 문자열 추출.
- staging output에 대한 localization inventory 실행.

## 아직 하지 않는 일

- Nexus Mods 로그인/다운로드.
- encrypted PAK 처리.
- archive repacking.
- `.uasset` 임의 편집.
- virtual filesystem.
- installer/signing/auto-update.
- WinUI에서 game folder 직접 apply/restore.

## 빠른 시작

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

소스 트리에서 바로 실행:

```powershell
$env:PYTHONPATH = "src"
python -m modforge doctor
python -m modforge profiles
python -m modforge --help
```

Unreal staging 예시:

```powershell
$env:PYTHONPATH = "src"
python -m modforge project init --name "Unreal Demo" --game-root C:\Games\Example --mods-dir C:\ModForge\Example\Mods --profile unreal-pak
python -m modforge scan-mods
python -m modforge plan --summary
python -m modforge apply-staging --yes
python -m modforge translation inventory --target staging --json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_real_unreal_intake.ps1 -Source C:\ModForge\SampleUnrealMod
```

실제 모드 intake helper는 read-only로 동작하며 기본 보고서 JSON을
`Documents\ModForge Manager\Reports` 아래에 저장합니다. `-Output`을 직접
지정할 경우 검사 중인 모드 폴더나 압축 파일 안쪽이 아닌 별도 위치를
사용하세요.

WinUI 3 셸 빌드/실행:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_winui_shell.ps1
.\dist\ModForge.WinUI\ModForge.WinUI.exe
```
