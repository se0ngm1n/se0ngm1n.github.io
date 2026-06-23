---
title: "[Isaac Lab Part 5] Mimic과 Robomimic으로 Franka Cube Stacking BC 학습하기"
date: 2026-06-02
category: "Isaac Lab"
summary: "Isaac Lab 공식 Franka cube stacking demonstration을 사용해 Mimic annotation, 추가 demonstration 생성, Robomimic BC-RNN 학습, checkpoint 확인까지 이어지는 흐름을 정리한다."
tags:
  - "Isaac Sim"
  - "Isaac Lab"
  - "Imitation Learning"
  - "Behavior Cloning"
  - "Robomimic"
  - "Franka"
thumbnail: "/study-media/isaaclab-bc-franka/franka-stack-official.jpg"
---

## 들어가며

![ Isaac Lab Part 5  Mimic과 Robomimic으로 Franka Cube Stacking BC 학습하기](/study-media/isaaclab-part-5-mimic-robomimic-bc-franka-stack/1.png)

로봇에게 작업을 학습시키는 방법은 보상 기반 강화학습만 있는 것이 아니다. 사람이 성공적으로 수행한 시연을 데이터로 삼아, 같은 상황에서 비슷한 행동을 내도록 policy를 학습시키는 **모방 학습(Imitation Learning)**도 중요한 접근이다.

이번 글에서는 NVIDIA Isaac Lab의 공식 Franka cube stacking 예제를 기준으로, 행동 복제(Behavior Cloning, BC) 파이프라인을 직접 실행한 과정을 정리한다. Isaac Sim과 Isaac Lab 설치 과정은 제외하고, 아래 순서에 집중했다.

```text
공식 demonstration dataset 준비
→ Isaac Lab Mimic subtask annotation
→ Mimic 기반 추가 demonstration 생성
→ Robomimic Behavior Cloning 학습
→ epoch별 policy checkpoint 확인
```

> 이 글은 자체 task나 자체 dataset을 설계한 프로젝트가 아니라, 공식 예제를 실행하며 imitation learning 파이프라인의 구성 요소를 확인한 실습 기록이다.

---

## 1. 실습 대상: Franka Cube Stacking

사용한 환경은 다음 task다.

```text
Isaac-Stack-Cube-Franka-IK-Rel-v0
```

Franka Panda 로봇팔은 세 개의 큐브를 순서대로 쌓는다. 목표는 파란 큐브를 바닥 기준으로 두고, 그 위에 빨간 큐브와 초록 큐브를 차례로 올리는 것이다.

![Isaac Lab Franka cube stacking 공식 예제 이미지](/study-media/isaaclab-bc-franka/franka-stack-official.jpg)

*그림 1. Isaac Lab 공식 문서에 제시된 Franka cube stacking 환경. 출처: NVIDIA Isaac Lab Documentation, “Available Environments”.*

이 task는 단순 위치 제어가 아니라 아래 동작이 순서대로 이어지는 manipulation 문제다.

```text
1. 빨간 큐브에 접근
2. 그리퍼로 빨간 큐브 집기
3. 파란 큐브 위로 이동
4. 빨간 큐브 내려놓기
5. 초록 큐브 집기
6. 빨간 큐브 위에 올려놓기
```

접근, grasp, transport, release가 모두 포함되어 있어 demonstration 기반 학습 흐름을 확인하기에 적합하다.

---

## 2. Behavior Cloning의 기본 아이디어

Behavior Cloning은 전문가 시연에서 관측값과 행동의 대응 관계를 지도학습처럼 학습한다. 데이터는 보통 시간 순서의 observation-action 쌍으로 저장된다.

```text
D = {(o_t, a_t)}
```

- `o_t`: 시점 `t`에서 로봇과 물체의 상태
- `a_t`: 같은 시점에서 전문가가 수행한 행동

예를 들어 빨간 큐브를 집어 파란 큐브 위에 올리는 과정에서는 다음과 같은 대응이 데이터에 담긴다.

| 시점 | Observation 예시 | Expert Action 예시 |
|---|---|---|
| t=0 | 그리퍼가 빨간 큐브 왼쪽에 있음 | 오른쪽으로 이동 |
| t=1 | 그리퍼가 큐브 위에 있음 | 아래로 접근 |
| t=2 | grasp 가능한 위치에 도달 | 그리퍼 닫기 |
| t=3 | 큐브를 잡은 상태 | 파란 큐브 위로 이동 |
| t=4 | 목표 위치에 도달 | 그리퍼 열기 |

BC policy는 이 데이터를 이용해 “이 관측값에서는 어떤 action을 내야 하는가”를 학습한다.

![Behavior Cloning 학습 흐름](/study-media/isaaclab-bc-franka/bc-workflow.svg)

*그림 2. 이번 실습에서 확인한 Behavior Cloning 파이프라인. 시연 데이터에서 Mimic 증강을 거쳐 BC-RNN checkpoint를 만든다.*

정책을 \(\pi_\theta(a \mid o)\)라고 하면, BC는 demonstration에 기록된 action이 높은 확률로 나오도록 파라미터 \(\theta\)를 조정한다.

\[
\mathcal{L}_{BC}(\theta)
=
- \mathbb{E}_{(o,a) \sim D}
\left[
\log \pi_\theta(a \mid o)
\right]
\]

직관적으로는 다음 흐름이다.

```text
현재 observation 입력
→ policy가 action 예측
→ expert action과 비교
→ expert action에 가까워지도록 policy 업데이트
```

BC는 성공 시연이 충분히 좋으면 빠르게 policy를 만들 수 있다. 대신 시연에서 보지 못한 상태에 약하고, 작은 오차가 누적되면 복구하지 못할 수 있다. 그래서 demonstration의 다양성과 품질이 매우 중요하다.

---

## 3. Isaac Lab Mimic의 역할

BC를 학습하려면 성공 demonstration이 필요하다. 하지만 사람이 직접 많은 시연을 수집하는 것은 비용이 크다. Isaac Lab Mimic은 적은 수의 demonstration을 task의 의미 있는 구간으로 나누고, 새로운 물체 배치에 맞춰 변형해 추가 demonstration을 만드는 도구다.

역할을 나누면 다음과 같다.

```text
Isaac Lab Mimic = 학습용 demonstration을 늘리는 데이터 생성 단계
Robomimic BC    = 생성된 demonstration으로 policy를 학습하는 단계
```

Franka cube stacking은 하나의 긴 trajectory를 다음 subtask로 나눌 수 있다.

```text
빨간 큐브 grasp
→ 빨간 큐브 placement
→ 초록 큐브 grasp
→ 초록 큐브 placement
```

Mimic은 각 subtask의 완료 시점을 기준으로 trajectory를 재조합하고, 다른 초기 큐브 배치에서도 성공 demonstration이 되도록 변형한다.

---

## 4. 공식 Demonstration Dataset 준비

이번 실습에서는 teleoperation으로 직접 시연을 수집하지 않고, Isaac Lab 공식 튜토리얼에서 제공하는 Franka cube stacking demonstration dataset을 사용했다. 공식 dataset은 `Isaac-Stack-Cube-Franka-IK-Rel-v0` task의 human demonstration 10개를 포함한다.

```bash
cd ~/IsaacLab
mkdir -p datasets

wget -O ./datasets/dataset.hdf5 \
"https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/IsaacLab/Mimic/franka_stack_datasets/dataset.hdf5"

ls -lh ./datasets/dataset.hdf5
```

이 파일은 이후 subtask annotation과 Mimic 기반 dataset 생성의 입력으로 사용된다.

---

## 5. Mimic Subtask Annotation

Mimic이 trajectory를 재사용하려면 demonstration 안에서 각 subtask가 끝나는 시점을 알아야 한다. 공식 Franka 예제에는 자동 annotation heuristic이 제공되므로 `--auto` 옵션을 사용했다.

```bash
cd ~/IsaacLab
conda activate env_isaaclab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/annotate_demos.py \
  --headless \
  --device cpu \
  --task Isaac-Stack-Cube-Franka-IK-Rel-Mimic-v0 \
  --auto \
  --input_file ./datasets/dataset.hdf5 \
  --output_file ./datasets/annotated_dataset.hdf5
```

실행 결과, 10개의 공식 demonstration이 모두 annotation되어 export되었고 successful task completion도 10개로 확인되었다.

![Isaac Lab Mimic annotation 결과](/study-media/isaaclab-bc-franka/mimic-annotation-complete.png)

*그림 3. `annotate_demos.py` 실행 결과. 10개의 episode가 annotation되었고, successful completion 역시 10개로 출력되었다.*

---

## 6. Mimic 기반 Demonstration 생성

Annotation된 dataset을 입력으로 추가 demonstration을 생성했다. 이번 실습은 고성능 policy를 만드는 것이 아니라 전체 pipeline을 끝까지 연결해보는 목적이었기 때문에 trial 수를 작게 잡았다.

```bash
cd ~/IsaacLab
conda activate env_isaaclab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/generate_dataset.py \
  --headless \
  --device cpu \
  --num_envs 1 \
  --generation_num_trials 5 \
  --input_file ./datasets/annotated_dataset.hdf5 \
  --output_file ./datasets/generated_dataset_test.hdf5
```

| 인자 | 설정값 | 의미 |
|---|---:|---|
| `--device` | `cpu` | 소규모 데이터 생성 확인용으로 CPU 실행 |
| `--num_envs` | `1` | 동시에 실행할 환경 수 제한 |
| `--generation_num_trials` | `5` | pipeline 확인 목적의 소량 trial |
| `--input_file` | `annotated_dataset.hdf5` | subtask annotation이 반영된 입력 데이터 |
| `--output_file` | `generated_dataset_test.hdf5` | BC 학습에 사용할 생성 데이터 |

대규모 학습을 목표로 한다면 더 많은 demonstration을 생성해야 하지만, 여기서는 annotation에서 학습까지 이어지는 연결을 확인하는 데 초점을 맞췄다.

---

## 7. Robomimic Behavior Cloning 학습

생성된 demonstration dataset으로 Robomimic의 BC agent를 학습했다.

```bash
cd ~/IsaacLab
conda activate env_isaaclab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py \
  --task Isaac-Stack-Cube-Franka-IK-Rel-v0 \
  --algo bc \
  --dataset ./datasets/generated_dataset_test.hdf5
```

학습 경로명은 다음 설정을 보여준다.

```text
bc_rnn_low_dim_franka_stack
```

- `bc`: Behavior Cloning
- `rnn`: 이전 시점의 정보를 내부 상태에 반영하는 recurrent policy
- `low_dim`: camera image가 아닌 저차원 상태 관측값 기반 policy
- `franka_stack`: Franka cube stacking task

### 7.1 왜 RNN policy인가?

큐브 쌓기는 접근, 집기, 운반, 배치가 순서대로 이어지는 manipulation task다. 비슷한 observation처럼 보여도 이미 큐브를 집은 상태인지, 놓기 직전인지에 따라 필요한 action이 다르다. RNN policy는 이전 시점의 흐름을 내부 상태에 담을 수 있어 이런 sequential task에 적합하다.

### 7.2 학습 로그 확인

학습 중에는 loss, log likelihood, learning rate, gradient norm, epoch 시간, memory usage가 출력된다.

![Robomimic BC-RNN 학습 로그](/study-media/isaaclab-bc-franka/bc-training-epoch-log.png)

*그림 4. `robomimic/train.py` 실행 중 출력된 BC-RNN 학습 로그. epoch별 loss와 memory usage를 확인할 수 있다.*

---

## 8. Checkpoint 생성 확인

학습 과정에서 일정 epoch마다 policy checkpoint가 `.pth` 파일로 저장되었다.

```bash
cd ~/IsaacLab
find logs/robomimic -name "*.pth" | sort
```

확인된 checkpoint는 다음과 같다.

```text
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_100.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_200.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_300.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_400.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_500.pth
logs/robomimic/Isaac-Stack-Cube-Franka-IK-Rel-v0/bc_rnn_low_dim_franka_stack/20260602212019/models/model_epoch_600.pth
```

Checkpoint는 특정 epoch까지 학습된 policy parameter다. epoch가 커질수록 항상 성능이 좋아진다고 볼 수는 없다. 데이터가 적거나 초기 상태 다양성이 부족하면 특정 demonstration에 과하게 맞춰질 수 있으므로, 실제 평가에서는 여러 checkpoint를 같은 조건에서 비교해야 한다.

---

## 9. 정리

이번 실습에서는 Isaac Lab 공식 Franka cube stacking demonstration을 입력으로 사용해 Mimic annotation, 추가 demonstration 생성, Robomimic BC-RNN 학습, checkpoint 확인까지 연결했다.

핵심은 다음과 같다.

- BC는 reward가 아니라 demonstration action을 정답으로 사용하는 policy 학습이다.
- Mimic은 policy를 직접 학습하는 단계가 아니라, 학습용 demonstration을 늘리는 데이터 생성 단계다.
- 소량 dataset 실습은 높은 성공률 검증보다 전체 pipeline 이해에 적합하다.
- 최종 산출물은 epoch별 `.pth` policy checkpoint이며, 실제 성능은 별도 평가로 확인해야 한다.

---

## 실행 명령 모음

### 공식 demonstration dataset 다운로드

```bash
cd ~/IsaacLab
mkdir -p datasets

wget -O ./datasets/dataset.hdf5 \
"https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/IsaacLab/Mimic/franka_stack_datasets/dataset.hdf5"
```

### Subtask annotation

```bash
conda activate env_isaaclab
cd ~/IsaacLab

export OMNI_KIT_ACCEPT_EULA=YES
export CUDA_VISIBLE_DEVICES=0

./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/annotate_demos.py \
  --headless \
  --device cpu \
  --task Isaac-Stack-Cube-Franka-IK-Rel-Mimic-v0 \
  --auto \
  --input_file ./datasets/dataset.hdf5 \
  --output_file ./datasets/annotated_dataset.hdf5
```

### Mimic 기반 demonstration 생성

```bash
./isaaclab.sh -p scripts/imitation_learning/isaaclab_mimic/generate_dataset.py \
  --headless \
  --device cpu \
  --num_envs 1 \
  --generation_num_trials 5 \
  --input_file ./datasets/annotated_dataset.hdf5 \
  --output_file ./datasets/generated_dataset_test.hdf5
```

### Robomimic BC 학습

```bash
./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py \
  --task Isaac-Stack-Cube-Franka-IK-Rel-v0 \
  --algo bc \
  --dataset ./datasets/generated_dataset_test.hdf5
```

### checkpoint 확인

```bash
find logs/robomimic -name "*.pth" | sort
```

---

## 참고 자료

- [Isaac Lab Documentation — Teleoperation and Imitation Learning with Isaac Lab Mimic](https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/teleop_imitation.html)
- [Isaac Lab Documentation — Available Environments](https://isaac-sim.github.io/IsaacLab/main/source/overview/environments.html)
- [Isaac Lab GitHub Repository](https://github.com/isaac-sim/IsaacLab)
- [Robomimic Documentation](https://robomimic.github.io/)
