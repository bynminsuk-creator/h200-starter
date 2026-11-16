# H200 Starter

사업단 H200 서버의 GitHub 이슈 실행 방식에 맞춘 기본 프로젝트입니다.
실제 연구 모델 학습 코드는 아직 포함하지 않습니다. 첫 요청은 작은 GPU 테스트부터 실행합니다.

## 첫 실행 요청

사업단에서 승인된 사용 기간 안에 `Aerodrone-H200/gpu-request`의
**컨테이너 생성 및 코드 실행 요청** 양식을 엽니다.

| 항목 | 입력값 |
| --- | --- |
| 사용자 ID | `bynminsuk-creator` |
| 코드 GitHub 링크 | `https://github.com/bynminsuk-creator/h200-starter.git` |
| 코드 실행 명령어 | `bash run.sh smoke` |
| 이미지 | `pytorch/pytorch:latest` (실제 제공 이미지 확인) |
| 언어 | Bash (선택지에 Bash가 없으면 담당자에게 확인) |
| GPU 할당량 | 소속 그룹에서 허용하는 범위의 `1` |

`latest`의 Python/PyTorch/CUDA 버전은 고정하지 않습니다. 실제 버전은 실행 로그와 결과에 기록합니다.
등록과 GitHub 조직 초대 수락을 먼저 완료해야 합니다. 제출한 요청은 자동 실행될 수 있습니다.

테스트는 CUDA 접근, 작은 행렬곱, 역전파와 유한한 결과를 확인합니다.
GPU가 없으면 실패를 반환하므로 서버 설정 문제를 CPU 실행으로 숨기지 않습니다.
실제 데이터셋이나 모델 파일을 내려받지 않으며 새 패키지도 설치하지 않습니다.

## 결과 받기

종료 댓글에서 `[summary]`와 `[result]`를 확인합니다.
관리자에게 **이슈 번호 + 로그에 표시된 `/app/output/h200-starter/<실행ID>/results.zip` 경로**를 전달합니다.

- `summary.json`: 성공/실패, 종료 코드, 실행 시간
- `smoke.json`: 성공한 GPU 테스트의 환경 및 측정값
- `run.log`: 전체 실행 로그 (최대 8 MiB)
- `results.zip`: 위 결과 파일 묶음 (원본 파일 합계 100 MiB 이하일 때 생성)

화면 출력은 약 12,000바이트로 제한해 이슈 댓글이 너무 길어지는 것을 줄였습니다.
결과가 큰 학습 작업은 관리자에게 개별 파일을 요청할 수 있습니다.
서버 안내의 output 100 GB 제한과 이 프로젝트의 ZIP 생성 제한 100 MiB는 서로 다릅니다.

## 프로젝트 코드 추가 후 실행

코드와 필요한 작은 설정 파일을 이 저장소에 추가한 뒤 다음 형태로 요청합니다.

```bash
bash run.sh run python -u train.py
```

`run` 모드는 임의 명령을 감시합니다. 모델 의존성 설치와 데이터 준비 코드는 프로젝트에 맞춰 추가해야 합니다.
필요한 결과 경로는 자식 프로세스의 `RUN_OUTPUT_DIR` 환경변수로 전달합니다.

```python
import os
from pathlib import Path
result_dir = Path(os.environ["RUN_OUTPUT_DIR"])
# 결과 지표, 로그, 수령할 모델 등을 result_dir 아래에 저장
```

로그가 40분 동안 없으면 종료 코드 124로 중단합니다. 총 실행 시간 기본값은 1시간입니다.
이것은 이 프로젝트의 보호 설정이며 서버 운영 정책의 최대 실행 시간이 아닙니다.
긴 학습은 명시적으로 시간을 조정하고, 진행 로그를 출력합니다.

```bash
WATCHDOG_SECONDS=2400 MAX_SECONDS=21600 bash run.sh run python -u train.py
```

Linux에서는 제한 초과 시 자식 프로세스 그룹을 종료합니다.
Windows 로컬 테스트에서는 직접 실행한 프로세스만 종료하므로 하위 프로세스 정리는 Linux에서 확인해야 합니다.
학습 중 체크포인트를 주기적으로 저장하고, 무응답 종료 시 저장되지 않은 진행 상황은 유실될 수 있습니다.

## 데이터와 경로

| 경로 | 용도 |
| --- | --- |
| `/app/data` | 관리자가 제공한 데이터·가중치, 읽기 전용 |
| `/app/scratch/h200-starter` | 캐시·임시 파일·압축 해제 작업 공간 |
| `/app/output/h200-starter/<실행ID>` | 수령할 결과 |

작업별 컨테이너는 종료 후 삭제되며 다음 작업에 파일이 자동으로 이어지지 않습니다.
큰 데이터는 공개 배포본에서 작업 중 받거나 관리자에게 ZIP과 SHA-256을 전달합니다.
GitHub에 데이터·가중치·토큰·실험 결과를 올리지 않습니다.
비공개 저장소를 사용하려면 서버가 복제할 수 있도록 담당자와 접근 권한을 별도로 확인해야 합니다.

## 로컬에서 실행기 확인

Python 표준 라이브러리만으로 실행기의 결과 저장을 확인할 수 있습니다.

```bash
OUTPUT_ROOT=./output python scripts/runner.py -- python -c "print('runner OK')"
```

GPU 테스트에는 PyTorch가 필요합니다. CPU 테스트를 원하면 `bash run.sh smoke --allow-cpu`를 사용합니다.
서버 요청에서는 기본 `bash run.sh smoke`를 사용합니다.

## 참고 자료

- 제공받은 `H200 사용 등록.pptx`, `H200 사용법 _이슈작성.pptx`, `H200_사용설명서.pdf`를 바탕으로 요청 흐름을 정리했습니다.
- [conantong1110/trimodal-uav-det-h200](https://github.com/conantong1110/trimodal-uav-det-h200)의 실행 스크립트와 로그 감시 방식을 참고했습니다.
  이 프로젝트의 코드는 독립적으로 작성했습니다. 해당 저장소의 모델이나 데이터 로더를 복사하지 않았습니다.
- PDF에는 `KAU-H200`이라는 조직명이 있고 PPT에는 `Aerodrone-H200/gpu-request`가 나옵니다.
  실제 초대받은 조직과 현재 사업단 안내를 우선 확인하세요.
- 결과 전달도 PDF의 다운로드 링크 설명과 PPT의 관리자 요청 설명이 다르므로, 관리자 요청 경로를 준비하고 실제 댓글 안내를 따릅니다.
