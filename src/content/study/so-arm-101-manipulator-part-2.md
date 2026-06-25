---
title: "[SO-ARM 101 Manipulator Project Part 2] 학습 데이터 수집, Behavior Cloning 1차 테스트"
date: 2026-06-25
category: "Manipulator Project"
summary: "SO-ARM101으로 100개 시연을 수집하고 97 episode·72,643 frame의 clean dataset을 만든 뒤, ACT를 20,000 step 학습해 실제 Pick-and-Place를 실행한 첫 행동복제 실험"
tags:
  - "SO-ARM 101"
  - "LeRobot"
  - "Behavior Cloning"
  - "Imitation Learning"
  - "ACT"
  - "Pick and Place"
thumbnail: ""
---

LeRobot 기반 데이터 수집, 데이터 클리닝, ACT 학습, 실제 로봇 시연까지

> 요약: SO-ARM101 리더-팔로워 시스템과 USB 카메라를 이용해 '3개 큐브 중 가장 가까운 큐브를 집어 박스에 넣는' 행동복제 데이터를 수집했다. 총 100 episode를 촬영한 뒤 품질이 나쁜 10, 11, 32번 episode를 제거했고, 97 episode / 72,643 frame으로 ACT policy를 학습했다. 20,000 step 학습은 약 31분 56초가 걸렸고, 학습한 1차 policy가 실제 로봇에서 Pick-and-Place를 수행하는 것까지 확인했다.

<video controls preload="metadata" playsinline>
  <source src="/study-media/so-arm-101-manipulator-part-2/image.mov" type="video/quicktime" />
</video>

## 글의 목적

이 글은 SO-ARM101과 LeRobot을 이용해 실제 로봇팔 행동복제 실험을 처음부터 끝까지 진행한 기록이다. 단순히 명령어를 나열하기보다, 어떤 문제를 만났고 어떤 기준으로 데이터를 정리했으며 실제 시연까지 어떻게 연결했는지를 중심으로 정리했다.

[Part 1](/study/so-arm-101-manipulator-part-1/)에서 리더 암과 팔로워 암의 조립, 캘리브레이션, 텔레오퍼레이션을 완료했다. 이번 Part 2에서는 그 구성을 학습 파이프라인으로 확장했다. 사람이 리더 암으로 보여준 동작을 카메라 영상과 관절 데이터로 기록하고, 잘못된 시연을 제거한 뒤 ACT policy를 학습해 팔로워 암에서 실행했다.

```text
리더 암으로 성공 동작 시연
  -> 카메라 이미지 + 팔로워 관절 상태 + action 기록
  -> episode 단위 검수 및 불량 데이터 제거
  -> ACT policy 학습
  -> 실제 팔로워 암에서 rollout
```

### 실험 결과 한눈에 보기

| 항목 | 결과 |
|---|---:|
| 수집한 episode | 100 |
| 제거한 episode | 3 (10, 11, 32번) |
| 학습에 사용한 episode | 97 |
| 전체 frame | 72,643 |
| 카메라 | 전면 USB 카메라 1대, 640×480, 30 fps |
| policy | ACT |
| 학습 step | 20,000 |
| 학습 시간 | 31분 56초 |
| 실제 로봇 확인 | 가까운 큐브 Pick-and-Place 시연 성공 |

여기서 마지막 항목은 **파이프라인이 실제 로봇에서 작동한다는 1차 확인**이다. 아직 조건별 반복 실험으로 성공률을 계산한 결과는 아니므로, 일반화 성능이 검증됐다고 해석하지는 않았다.

## 목차

1. 실험 목표와 시스템 구성
2. 데이터 수집: 100 episode 촬영
3. 데이터 검증과 품질 관리
4. 나쁜 episode 삭제 및 clean dataset 생성
5. ACT policy 학습
6. 실제 로봇 rollout 및 시연
7. 시행착오와 배운 점
8. 다음 개선 방향
9. 참고 자료

## 1. 실험 목표와 시스템 구성

이번 실험의 목표는 SO-ARM101 로봇팔이 사람의 조작 시연을 따라 배워, 책상 위 큐브를 집고 박스에 넣는 동작을 스스로 수행하도록 만드는 것이었다. 작업은 너무 어렵게 시작하지 않기 위해 '한 episode에서 하나의 큐브만 집기'로 제한했다.

### Task 정의

- 입력: 전면 카메라 이미지, SO-ARM101 현재 관절 상태
- 출력: SO-ARM101 follower의 6개 관절 action
- 작업: 3개 큐브 중 로봇에 가장 가까운 큐브를 집어 박스에 넣기
- episode 기준: 큐브 하나를 집고 박스에 넣으면 성공으로 저장

이 task에서 '가장 가까운 큐브'는 별도의 거리 센서나 명시적인 3D 좌표 계산으로 선택한 것이 아니다. policy는 전면 카메라 이미지와 현재 관절 상태에서 사람이 반복한 행동 패턴을 학습한다. 따라서 이번 결과는 제한된 카메라 위치와 큐브 배치 범위 안에서 시각적 단서와 action의 관계를 학습한 것으로 보는 편이 정확하다.

### 사용 장비 및 환경

- SO-ARM101 leader arm: 사람이 직접 조작하는 teleoperation 장치
- SO-ARM101 follower arm: 실제 데이터를 기록하고 policy를 실행하는 로봇
- USB 카메라: OpenCV camera index 0, 640x480, 30 fps
- Ubuntu + conda 환경 + LeRobot
- 학습 policy: ACT(Action Chunking Transformer)

> 초기 데이터셋은 100 episode로 시작했다. 이후 카메라가 가려졌거나 물체가 떨어진 episode 10, 11, 32를 제거해서 최종 clean dataset은 97 episode가 되었다.

## 2. 데이터 수집: 100 episode 촬영

<video controls preload="metadata" playsinline>
  <source src="/study-media/so-arm-101-manipulator-part-2/image-2.mov" type="video/quicktime" />
</video>

행동복제에서 가장 중요한 것은 데이터 품질이다. policy는 사람이 수행한 행동을 그대로 따라 배우기 때문에, 실패한 행동이나 애매한 행동이 섞이면 나중에 로봇도 그 애매함을 학습한다. 그래서 이번 수집에서는 '성공하면 오른쪽 방향키, 실패하면 왼쪽 방향키' 규칙을 엄격하게 적용했다.

강화학습처럼 보상 함수를 통해 시행착오를 반복하는 대신, 행동복제는 시연에서 관측한 `observation -> action` 대응을 지도학습한다. 이 때문에 수집 단계에서 잘못 저장한 action은 단순한 노이즈가 아니라 학습 목표 자체의 오류가 된다. 모델이나 학습 step을 늘리기 전에 시연의 일관성과 성공 기준을 먼저 관리해야 하는 이유다.

### 데이터 수집 명령어

```bash
conda activate lerobot
cd /home/fugu/robot_ws/lerobot

mkdir -p /home/fugu/lerobot_datasets

lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480,
    fps: 30}}" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM0 \
  --teleop.id=my_so101_leader \
  --display_data=true \
  --dataset.root=/home/fugu/lerobot_datasets/so101_cube3_pick_place_v1 \
  --dataset.repo_id=seongmin/so101_cube3_pick_place_v1 \
  --dataset.num_episodes=100 \
  --dataset.episode_time_s=25 \
  --dataset.reset_time_s=10 \
  --dataset.single_task="Pick the closest wooden cube among three cubes and place it
    into the box." \
  --dataset.push_to_hub=false \
  --dataset.camera_encoder.vcodec=h264 \
  --dataset.camera_encoder.pix_fmt=yuv420p
```

### 수집 중 적용한 규칙

- episode 시작 직후 0.5-1.5초 정도의 짧은 안정화 대기는 허용했다.
- 잡고 넣는 본 동작 중에는 멈추지 않도록 했다.
- 큐브를 놓쳤거나 박스 밖으로 떨어뜨린 경우는 저장하지 않았다.
- 카메라가 가려진 경우는 학습 데이터로 부적합하므로 삭제 대상으로 기록했다.
- reset 시간에는 다음 episode를 위해 큐브와 로봇 시작 자세를 다시 맞췄다.

> 중요한 점은 '성공 데이터만 저장한다'가 아니라, 나중에 policy가 보고 따라 해도 괜찮은 행동만 저장한다는 것이다. 행동복제에서 데이터는 곧 정답지다.

## 3. 데이터 검증과 품질 체크

수집 후에는 실제 데이터셋이 제대로 저장됐는지 확인했다. LeRobot v3 포맷에서는 meta/info.json, data parquet, video mp4, episode metadata가 생성된다.

LeRobotDataset v3는 저차원 state와 action을 Parquet에, 카메라 영상을 MP4에, episode 경계와 feature schema를 metadata에 저장한다. 여러 episode가 같은 shard 파일에 들어갈 수 있으므로 파일 개수만 세는 방식으로 데이터 수를 판단하면 안 되고, `meta/info.json`과 episode metadata를 함께 확인해야 한다.

### 데이터셋 기본 정보 확인

```bash
python - <<'PYCHECK'
import json
from pathlib import Path

root = Path("/home/fugu/lerobot_datasets/so101_cube3_pick_place_v1")
info = json.load(open(root / "meta" / "info.json"))

print("total_episodes:", info["total_episodes"])
print("total_frames:", info["total_frames"])
print("fps:", info["fps"])
print("features:", info["features"].keys())
PYCHECK
```

## 4. 나쁜 episode 삭제 및 clean dataset 생성

100개를 모두 수집한 뒤 전체를 확인해보니 10번, 11번, 32번 episode의 품질이 좋지 않았다. 카메라가 가려졌거나 물체가 떨어진 경우였다. 이런 episode는 단순한 노이즈가 아니라 policy가 잘못된 행동을 배울 수 있는 정답 오류에 가깝기 때문에 삭제했다.

### 삭제 대상

- episode 10: 카메라 시야가 가려져 관측 품질 저하
- episode 11: 카메라 시야 또는 조작 품질 문제
- episode 32: 물체가 떨어져 성공 행동으로 보기 어려움

### clean dataset 생성 명령어

```bash
HF_LEROBOT_HOME=/home/fugu/lerobot_datasets lerobot-edit-dataset \
  --repo_id=so101_cube3_pick_place_v1 \
  --new_repo_id=so101_cube3_pick_place_v1_clean \
  --operation.type=delete_episodes \
  --operation.episode_indices="[10, 11, 32]" \
  --push_to_hub=false
```

### 결과

```text
Created new dataset with 97 episodes
Dataset saved to /home/fugu/lerobot_datasets/so101_cube3_pick_place_v1_clean
Episodes: 97, Frames: 72643
```

최종적으로 학습에는 원본 v1이 아니라 clean 버전인 `/home/fugu/lerobot_datasets/so101_cube3_pick_place_v1_clean` 을 사용했다.

100개 중 3개를 제거했기 때문에 단순 제거율은 3%다. 비율만 보면 작지만, 행동복제에서는 실패 장면 하나가 특정 시각 조건과 잘못된 action을 강하게 연결할 수 있다. 특히 데이터 규모가 크지 않은 첫 실험에서는 episode 수를 유지하는 것보다 명확한 오류를 제거하는 편이 낫다고 판단했다.

## 5. ACT policy 학습

학습은 LeRobot의 ACT policy로 진행했다. 처음 학습을 실행했을 때 accelerate 패키지가 없어서 멈췄고, training extra를 설치한 뒤 다시 실행했다.

### 첫 policy로 ACT를 선택한 이유

일반적인 한 시점 행동 예측은 작은 오차가 다음 관측을 바꾸고, 바뀐 관측에서 다시 오차가 발생하면서 trajectory 전체가 흔들릴 수 있다. ACT(Action Chunking with Transformers)는 한 번에 하나의 action만 예측하는 대신 여러 미래 action으로 구성된 chunk를 예측한다.

```text
현재 관측 o_t
  -> ACT policy
  -> [a_t, a_(t+1), ..., a_(t+k-1)]
```

카메라 특징과 현재 관절 상태를 함께 사용해 연속된 action sequence를 만들기 때문에 Pick-and-Place처럼 접근, 파지, 이동, 놓기가 이어지는 manipulation task의 첫 baseline으로 적합하다. LeRobot 공식 문서도 ACT를 빠르게 학습할 수 있는 입문용 imitation learning policy로 안내하고 있다.

### 학습 의존성 설치

```bash
conda activate lerobot
cd /home/fugu/robot_ws/lerobot
python -m pip install -e ".[training]"
```

### CUDA 확인

```bash
python - <<'PYCHECK'
import torch
print("cuda available:", torch.cuda.is_available())
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
PYCHECK
```

### ACT 학습 명령어

```bash
HF_LEROBOT_HOME=/home/fugu/lerobot_datasets lerobot-train \
  --dataset.root=/home/fugu/lerobot_datasets/so101_cube3_pick_place_v1_clean \
  --dataset.repo_id=so101_cube3_pick_place_v1_clean \
  --policy.type=act \
  --output_dir=outputs/train/act_so101_cube3_pick_place_v1_clean \
  --job_name=act_so101_cube3_pick_place_v1_clean \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=false \
  --steps=20000
```

### 학습 결과

```text
Checkpoint policy after step 20000
Training: 100%|                       | 20000/20000 [31:56<00:00, 10.44step/s]
End of training
```

> 이번 실험에서는 20,000 step 학습에 약 31분 56초가 걸렸다. 97 episode 규모의 첫 번째 policy 학습으로는 충분히 빠르게 실험 사이클을 돌릴 수 있는 수준이었다.

## 6. 실제 로봇 rollout 및 시연

학습이 끝난 뒤에는 checkpoint를 이용해 실제 SO-ARM101 follower에서 policy를 실행했다. 처음에는 lerobot-record에 --policy.path를 넣어 평가 데이터를 저장하려 했지만, 현재 환경의 lerobot-record는 policy.path 인자를 지원하지 않았다. 그래서 실제 policy 실행은 lerobot-rollout으로 진행했다.

### checkpoint 경로

```bash
POLICY=outputs/train/act_so101_cube3_pick_place_v1_clean/checkpoints/020000/pretrained_model
```

### 실제 로봇 rollout 명령어

```bash
HF_LEROBOT_HOME=/home/fugu/lerobot_datasets lerobot-rollout \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.id=my_so101_follower \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480,
    fps: 30}}" \
  --display_data=true \
  --policy.path="$POLICY"
```

### 시연 결과

학습한 1차 policy는 실제 로봇에서 실행됐고, 3개 큐브 중 가까운 큐브를 집어 박스에 넣는 시연에 성공했다. 첫 행동복제 실험에서 데이터 수집, 클리닝, 학습, 실제 policy 실행까지 한 사이클을 완주했다는 점에서 의미가 있었다.

### 이번 결과의 해석과 한계

이번 시연으로 확인한 것은 아래 두 가지다.

- 학습 checkpoint를 실제 SO-ARM101 follower에서 불러와 inference할 수 있다.
- 학습 데이터와 유사한 조건에서 Pick-and-Place 성공 사례가 나왔다.

반면 아직 성공률을 말할 단계는 아니다. 큐브 위치, 선택된 큐브, 조명, 시작 자세를 바꾸어 여러 번 반복한 평가 기록이 없기 때문이다. 한 번의 성공 영상은 end-to-end 파이프라인 검증에는 충분하지만 policy의 재현성과 일반화 성능을 증명하지는 않는다.

다음 실험에서는 최소한 아래 형식으로 rollout 결과를 분리해 기록할 계획이다.

| 평가 항목 | 기록 내용 |
|---|---|
| trial 조건 | 큐브 위치, 박스 위치, 조명, 시작 자세 |
| 성공 기준 | 큐브를 집어 제한 시간 안에 박스 내부에 놓음 |
| 실패 유형 | 미검출, 잘못된 큐브 선택, grasp 실패, 이동 중 낙하, 박스 밖 release |
| 정량 지표 | 전체 성공률, 조건별 성공률, 평균 완료 시간 |

## 7. 시행착오와 배운 점

### 1) 좋은 데이터가 모델 성능보다 먼저다

행동복제는 모델이 똑똑해서 문제를 푸는 구조라기보다, 사람이 남긴 좋은 시연을 따라 하는 구조에 가깝다. 카메라가 가려지거나 물체가 떨어진 episode는 반드시 제거하는 편이 좋다.

### 2) 시작 자세와 카메라 위치는 최대한 고정해야 한다

이번 데이터는 카메라 위치, 박스 위치, 로봇 시작 자세, 큐브 배치 범위를 최대한 일정하게 유지했다. 첫 policy는 일반화보다 재현성을 우선으로 두는 편이 좋다.

### 3) 초반 대기는 짧고 일정하면 괜찮다

episode 시작 직후 짧은 안정화 대기는 피하기 어려웠다. 다만 본 동작 중에는 멈추지 않았고, 초반 대기 시간을 비슷하게 유지했다. 이 정도는 초기 실험에서 큰 문제로 보이지 않았다.

### 4) LeRobot 버전별 명령어 차이에 주의해야 한다

record 명령에서 policy.path가 먹지 않거나, codec 이름이 libx264가 아니라 h264여야 하는 등 버전별 차이가 있었다. 에러 메시지를 보고 실제 지원되는 인자명에 맞춰 수정하는 과정이 필요했다.

이 글의 명령어는 이번 실험 환경에서 실제 사용한 형태다. LeRobot은 CLI와 dataset 포맷이 빠르게 바뀌고 있으므로 재현할 때는 `lerobot --version`, 설치 commit, GPU·PyTorch·CUDA 버전을 함께 남기고 현재 설치본의 `--help`를 기준으로 인자를 확인하는 편이 안전하다. 최신 공식 문서에서는 policy 배포용 `lerobot-rollout`도 별도 CLI로 안내하고 있다.

## 8. 다음 개선 방향

이번 실험은 '작동하는 첫 행동복제 파이프라인'을 만드는 것이 목표였다. 다음 단계에서는 더 다양한 상황에서도 안정적으로 성공하도록 데이터와 평가 방식을 확장할 수 있다.

- episode 수를 200-300개 이상으로 늘려 더 안정적인 policy 만들기
- 큐브 위치, 박스 위치, 조명 조건을 조금씩 다양화해 일반화 성능 확인하기
- 성공/실패 평가 표를 만들어 policy별 성공률 기록하기
- 잡기는 되지만 놓치는 경우를 줄이기 위해 gripper close timing 데이터를 보강하기
- 학습 데이터와 평가 데이터를 분리해 같은 episode를 보고 성능을 판단하는 문제 피하기
- 카메라 위치를 고정한 baseline과 위치·조명을 바꾼 generalization 평가를 구분하기
- 장기적으로 소프트 그리퍼 또는 촉각 센서 데이터를 추가해 파지 안정성 개선하기

> 이번 프로젝트의 핵심 성과는 SO-ARM101에서 데이터 수집 -> 데이터 정제 -> ACT 학습 -> 실제 로봇 시연까지 하나의 closed loop를 완성했다는 점이다. 이제부터는 같은 파이프라인 위에서 데이터 품질과 task 난이도를 점진적으로 올리면 된다.

## 9. 참고 자료

- [Hugging Face LeRobot: ACT](https://huggingface.co/docs/lerobot/act)
- [Hugging Face LeRobot: LeRobotDataset v3.0](https://huggingface.co/docs/lerobot/lerobot-dataset-v3)
- [Hugging Face LeRobot: Using Dataset Tools](https://huggingface.co/docs/lerobot/en/using_dataset_tools)
- [Hugging Face LeRobot: Policy Deployment (`lerobot-rollout`)](https://huggingface.co/docs/lerobot/main/inference)
- [Zhao et al., Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware](https://arxiv.org/abs/2304.13705)

## 부록: 핵심 명령어 요약

```bash
# 1. 데이터 수집
lerobot-record ... \
  --dataset.root=/home/fugu/lerobot_datasets/so101_cube3_pick_place_v1 \
  --dataset.num_episodes=100 \
  --dataset.camera_encoder.vcodec=h264

# 2. 나쁜 episode 삭제
HF_LEROBOT_HOME=/home/fugu/lerobot_datasets lerobot-edit-dataset \
  --repo_id=so101_cube3_pick_place_v1 \
  --new_repo_id=so101_cube3_pick_place_v1_clean \
  --operation.type=delete_episodes \
  --operation.episode_indices="[10, 11, 32]" \
  --push_to_hub=false

# 3. ACT 학습
HF_LEROBOT_HOME=/home/fugu/lerobot_datasets lerobot-train \
  --dataset.root=/home/fugu/lerobot_datasets/so101_cube3_pick_place_v1_clean \
  --policy.type=act \
  --policy.device=cuda \
  --steps=20000

# 4. 실제 policy rollout
POLICY=outputs/train/act_so101_cube3_pick_place_v1_clean/checkpoints/020000/pretrained_model
HF_LEROBOT_HOME=/home/fugu/lerobot_datasets lerobot-rollout \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM1 \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480,
    fps: 30}}" \
  --display_data=true \
  --policy.path="$POLICY"
```
